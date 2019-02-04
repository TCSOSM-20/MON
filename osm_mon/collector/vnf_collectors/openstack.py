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
import datetime
import json
import logging
from typing import List

import gnocchiclient.exceptions
from gnocchiclient.v1 import client as gnocchi_client
from keystoneauth1 import session
from keystoneauth1.identity import v3

from osm_mon.collector.metric import Metric
from osm_mon.collector.vnf_collectors.base_vim import BaseVimCollector
from osm_mon.collector.vnf_metric import VnfMetric
from osm_mon.core.auth import AuthManager
from osm_mon.core.common_db import CommonDbClient
from osm_mon.core.settings import Config

log = logging.getLogger(__name__)

METRIC_MAPPINGS = {
    "average_memory_utilization": "memory.usage",
    "disk_read_ops": "disk.read.requests",
    "disk_write_ops": "disk.write.requests",
    "disk_read_bytes": "disk.read.bytes",
    "disk_write_bytes": "disk.write.bytes",
    "packets_dropped": "interface.if_dropped",
    "packets_received": "interface.if_packets",
    "packets_sent": "interface.if_packets",
    "cpu_utilization": "cpu_util",
}


class OpenstackCollector(BaseVimCollector):
    def __init__(self, vim_account_id: str):
        super().__init__(vim_account_id)
        self.common_db = CommonDbClient()
        self.auth_manager = AuthManager()
        self.granularity = self._get_granularity(vim_account_id)
        self.gnocchi_client = self._build_gnocchi_client(vim_account_id)

    def _get_resource_uuid(self, nsr_id, vnf_member_index, vdur_name) -> str:
        vdur = self.common_db.get_vdur(nsr_id, vnf_member_index, vdur_name)
        return vdur['vim-id']

    def _build_gnocchi_client(self, vim_account_id: str) -> gnocchi_client.Client:
        creds = self.auth_manager.get_credentials(vim_account_id)
        verify_ssl = self.auth_manager.is_verify_ssl(vim_account_id)
        auth = v3.Password(auth_url=creds.url,
                           username=creds.user,
                           password=creds.password,
                           project_name=creds.tenant_name,
                           project_domain_id='default',
                           user_domain_id='default')
        sess = session.Session(auth=auth, verify=verify_ssl)
        return gnocchi_client.Client(session=sess)

    def _get_granularity(self, vim_account_id: str):
        creds = self.auth_manager.get_credentials(vim_account_id)
        vim_config = json.loads(creds.config)
        if 'granularity' in vim_config:
            return int(vim_config['granularity'])
        else:
            cfg = Config.instance()
            return cfg.OS_DEFAULT_GRANULARITY

    def collect(self, vnfr: dict) -> List[Metric]:
        nsr_id = vnfr['nsr-id-ref']
        vnf_member_index = vnfr['member-vnf-index-ref']
        vnfd = self.common_db.get_vnfd(vnfr['vnfd-id'])
        metrics = []
        for vdur in vnfr['vdur']:
            # This avoids errors when vdur records have not been completely filled
            if 'name' not in vdur:
                continue
            vdu = next(
                filter(lambda vdu: vdu['id'] == vdur['vdu-id-ref'], vnfd['vdu'])
            )
            if 'monitoring-param' in vdu:
                for param in vdu['monitoring-param']:
                    metric_name = param['nfvi-metric']
                    gnocchi_metric_name = METRIC_MAPPINGS[metric_name]
                    delta = 10 * self.granularity
                    start_date = datetime.datetime.now() - datetime.timedelta(seconds=delta)
                    resource_id = self._get_resource_uuid(nsr_id, vnf_member_index, vdur['name'])
                    try:
                        measures = self.gnocchi_client.metric.get_measures(gnocchi_metric_name,
                                                                           start=start_date,
                                                                           resource_id=resource_id,
                                                                           granularity=self.granularity)
                        if len(measures):
                            metric = VnfMetric(nsr_id, vnf_member_index, vdur['name'], metric_name, measures[-1][2])
                            metrics.append(metric)
                    except gnocchiclient.exceptions.NotFound as e:
                        log.debug("No metric found: %s", e)
                        pass
        return metrics
