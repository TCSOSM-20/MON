# Copyright 2018 Whitestack, LLC
# *************************************************************

# This file is part of OSM Monitoring module
# All Rights Reserved to Whitestack, LLC

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at

#         http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# For those usages not covered by the Apache License, Version 2.0 please
# contact: bdiaz@whitestack.com or glavado@whitestack.com
##
import asyncio
import logging
from typing import List

from n2vc.vnf import N2VC

from osm_mon.collector.metric import Metric
from osm_mon.collector.vnf_collectors.base import BaseCollector
from osm_mon.collector.vnf_metric import VnfMetric
from osm_mon.core.common_db import CommonDbClient
from osm_mon.core.config import Config
from osm_mon.core.exceptions import VcaDeploymentInfoNotFound

log = logging.getLogger(__name__)


class VCACollector(BaseCollector):
    def __init__(self, config: Config):
        super().__init__(config)
        self.common_db = CommonDbClient(config)
        self.loop = asyncio.get_event_loop()
        self.n2vc = N2VC(server=config.get('vca', 'host'),
                         user=config.get('vca', 'user'),
                         secret=config.get('vca', 'secret'),
                         ca_cert=config.get('vca', 'cacert'))

    def collect(self, vnfr: dict) -> List[Metric]:
        nsr_id = vnfr['nsr-id-ref']
        vnf_member_index = vnfr['member-vnf-index-ref']
        vnfd = self.common_db.get_vnfd(vnfr['vnfd-id'])

        # Populate extra tags for metrics
        tags = {}
        tags['ns_name'] = self.common_db.get_nsr(nsr_id)['name']
        if vnfr['_admin']['projects_read']:
            tags['project_id'] = vnfr['_admin']['projects_read'][0]
        else:
            tags['project_id'] = None

        metrics = []
        for vdur in vnfr['vdur']:
            # This avoids errors when vdur records have not been completely filled
            if 'name' not in vdur:
                continue
            vdu = next(
                filter(lambda vdu: vdu['id'] == vdur['vdu-id-ref'], vnfd['vdu'])
            )
            if 'vdu-configuration' in vdu and 'metrics' in vdu['vdu-configuration']:
                try:
                    vca_deployment_info = self.get_vca_deployment_info(nsr_id, vnf_member_index, vdur['vdu-id-ref'],
                                                                       vdur['count-index'])
                except VcaDeploymentInfoNotFound as e:
                    log.warning(repr(e))
                    continue
                measures = self.loop.run_until_complete(self.n2vc.GetMetrics(vca_deployment_info['model'],
                                                                             vca_deployment_info['application']))
                log.debug('Measures: %s', measures)
                for measure_list in measures.values():
                    for measure in measure_list:
                        log.debug("Measure: %s", measure)
                        metric = VnfMetric(nsr_id, vnf_member_index, vdur['name'], measure['key'],
                                           float(measure['value']), tags)
                        metrics.append(metric)
        if 'vnf-configuration' in vnfd and 'metrics' in vnfd['vnf-configuration']:
            try:
                vca_deployment_info = self.get_vca_deployment_info(nsr_id, vnf_member_index)
            except VcaDeploymentInfoNotFound as e:
                log.warning(repr(e))
                return metrics
            measures = self.loop.run_until_complete(self.n2vc.GetMetrics(vca_deployment_info['model'],
                                                                         vca_deployment_info['application']))
            log.debug('Measures: %s', measures)
            for measure_list in measures.values():
                for measure in measure_list:
                    log.debug("Measure: %s", measure)
                    metric = VnfMetric(nsr_id, vnf_member_index, '', measure['key'], float(measure['value']), tags)
                    metrics.append(metric)
        return metrics

    def get_vca_deployment_info(self, nsr_id, vnf_member_index, vdu_id=None, vdu_count=0):
        nsr = self.common_db.get_nsr(nsr_id)
        for vca_deployment in nsr["_admin"]["deployed"]["VCA"]:
            if vca_deployment:
                if vdu_id is None:
                    if vca_deployment['member-vnf-index'] == vnf_member_index and vca_deployment['vdu_id'] is None:
                        return vca_deployment
                else:
                    if vca_deployment['member-vnf-index'] == vnf_member_index and \
                            vca_deployment['vdu_id'] == vdu_id and vca_deployment['vdu_count_index'] == vdu_count:
                        return vca_deployment
        raise VcaDeploymentInfoNotFound(
            "VCA deployment info for nsr_id {}, index {}, vdu_id {} and vdu_count_index {} not found.".format(
                nsr_id,
                vnf_member_index,
                vdu_id,
                vdu_count))
