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
from multiprocessing import Queue

from n2vc.vnf import N2VC

from osm_mon.collector.collectors.base import BaseCollector
from osm_mon.collector.metric import Metric
from osm_mon.common.common_db_client import CommonDbClient
from osm_mon.core.settings import Config

log = logging.getLogger(__name__)


class VCACollector(BaseCollector):
    def __init__(self):
        cfg = Config.instance()
        self.common_db = CommonDbClient()
        self.loop = asyncio.get_event_loop()
        self.n2vc = N2VC(server=cfg.OSMMON_VCA_HOST, user=cfg.OSMMON_VCA_USER, secret=cfg.OSMMON_VCA_SECRET)

    def collect(self, vnfr: dict, queue: Queue):
        vca_model_name = 'default'
        nsr_id = vnfr['nsr-id-ref']
        vnf_member_index = vnfr['member-vnf-index-ref']
        vnfd = self.common_db.get_vnfd(vnfr['vnfd-id'])
        for vdur in vnfr['vdur']:
            nsr = self.common_db.get_nsr(nsr_id)
            vdu = next(
                filter(lambda vdu: vdu['id'] == vdur['vdu-id-ref'], vnfd['vdu'])
            )
            if 'vdu-configuration' in vdu and 'metrics' in vdu['vdu-configuration']:
                vnf_name_vca = self.n2vc.FormatApplicationName(nsr['name'], vnf_member_index, vdur['vdu-id-ref'])
                metrics = self.loop.run_until_complete(self.n2vc.GetMetrics(vca_model_name, vnf_name_vca))
                log.debug('Metrics: %s', metrics)
                for metric_list in metrics.values():
                    for metric in metric_list:
                        log.debug("Metric: %s", metric)
                        metric = Metric(nsr_id, vnf_member_index, vdur['name'], metric['key'], float(metric['value']))
                        queue.put(metric)
            if 'vnf-configuration' in vnfr and 'metrics' in vnfr['vnf-configuration']:
                vnf_name_vca = self.n2vc.FormatApplicationName(nsr['name'], vnf_member_index, vdur['vdu-id-ref'])
                metrics = self.loop.run_until_complete(self.n2vc.GetMetrics(vca_model_name, vnf_name_vca))
                log.debug('Metrics: %s', metrics)
                for metric_list in metrics.values():
                    for metric in metric_list:
                        log.debug("Metric: %s", metric)
                        metric = Metric(nsr_id, vnf_member_index, vdur['name'], metric['key'], float(metric['value']))
                        queue.put(metric)
            # TODO (diazb): Implement vnf-configuration config
