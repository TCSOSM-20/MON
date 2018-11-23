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

from osm_mon.collector.collectors.base import BaseCollector
from osm_mon.collector.metric import Metric
from osm_mon.core.common_db import CommonDbClient
from osm_mon.core.settings import Config

log = logging.getLogger(__name__)


class VCACollector(BaseCollector):
    def __init__(self):
        cfg = Config.instance()
        self.common_db = CommonDbClient()
        self.loop = asyncio.get_event_loop()
        self.n2vc = N2VC(server=cfg.OSMMON_VCA_HOST, user=cfg.OSMMON_VCA_USER, secret=cfg.OSMMON_VCA_SECRET)

    def collect(self, vnfr: dict) -> List[Metric]:
        vca_model_name = 'default'
        nsr_id = vnfr['nsr-id-ref']
        vnf_member_index = vnfr['member-vnf-index-ref']
        vnfd = self.common_db.get_vnfd(vnfr['vnfd-id'])
        metrics = []
        nsr = self.common_db.get_nsr(nsr_id)
        for vdur in vnfr['vdur']:
            vdu = next(
                filter(lambda vdu: vdu['id'] == vdur['vdu-id-ref'], vnfd['vdu'])
            )
            if 'vdu-configuration' in vdu and 'metrics' in vdu['vdu-configuration']:
                vnf_name_vca = self.n2vc.FormatApplicationName(nsr['name'], vnf_member_index, vdur['vdu-id-ref'])
                measures = self.loop.run_until_complete(self.n2vc.GetMetrics(vca_model_name, vnf_name_vca))
                log.debug('Metrics: %s', metrics)
                for measure_list in measures.values():
                    for measure in measure_list:
                        log.debug("Metric: %s", measure)
                        metric = Metric(nsr_id, vnf_member_index, vdur['name'], measure['key'], float(measure['value']))
                        metrics.append(metric)
        if 'vnf-configuration' in vnfd and 'metrics' in vnfd['vnf-configuration']:
            vnf_name_vca = self.n2vc.FormatApplicationName(nsr['name'], vnf_member_index, 'vnfd')
            measures = self.loop.run_until_complete(self.n2vc.GetMetrics(vca_model_name, vnf_name_vca))
            log.debug('Metrics: %s', metrics)
            for measure_list in measures.values():
                for measure in measure_list:
                    log.debug("Metric: %s", measure)
                    metric = Metric(nsr_id, vnf_member_index, '', measure['key'], float(measure['value']))
                    metrics.append(metric)
        return metrics
