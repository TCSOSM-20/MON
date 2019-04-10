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
from ceilometerclient.v2 import client as ceilometer_client
from keystoneauth1 import session
from keystoneauth1.exceptions import EndpointNotFound
from keystoneauth1.identity import v3

from osm_mon.collector.metric import Metric
from osm_mon.collector.vnf_collectors.base_vim import BaseVimCollector
from osm_mon.collector.vnf_metric import VnfMetric
from osm_mon.core.auth import AuthManager
from osm_mon.core.common_db import CommonDbClient
from osm_mon.core.config import Config

log = logging.getLogger(__name__)

METRIC_MAPPINGS = {
    "average_memory_utilization": "memory.usage",
    "disk_read_ops": "disk.read.requests.rate",
    "disk_write_ops": "disk.write.requests.rate",
    "disk_read_bytes": "disk.read.bytes.rate",
    "disk_write_bytes": "disk.write.bytes.rate",
    "packets_in_dropped": "network.outgoing.packets.drop",
    "packets_out_dropped": "network.incoming.packets.drop",
    "packets_received": "network.incoming.packets.rate",
    "packets_sent": "network.outgoing.packets.rate",
    "cpu_utilization": "cpu_util",
}

INTERFACE_METRICS = ['packets_in_dropped', 'packets_out_dropped', 'packets_received', 'packets_sent']


class OpenstackCollector(BaseVimCollector):
    def __init__(self, config: Config, vim_account_id: str):
        super().__init__(config, vim_account_id)
        self.conf = config
        self.common_db = CommonDbClient(config)
        self.auth_manager = AuthManager(config)
        self.granularity = self._get_granularity(vim_account_id)
        self.backend = self._get_backend(vim_account_id)
        self.client = self._build_client(vim_account_id)

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

    def _build_ceilometer_client(self, vim_account_id: str) -> ceilometer_client.Client:
        creds = self.auth_manager.get_credentials(vim_account_id)
        verify_ssl = self.auth_manager.is_verify_ssl(vim_account_id)
        auth = v3.Password(auth_url=creds.url,
                           username=creds.user,
                           password=creds.password,
                           project_name=creds.tenant_name,
                           project_domain_id='default',
                           user_domain_id='default')
        sess = session.Session(auth=auth, verify=verify_ssl)
        return ceilometer_client.Client(session=sess)

    def _get_granularity(self, vim_account_id: str):
        creds = self.auth_manager.get_credentials(vim_account_id)
        vim_config = json.loads(creds.config)
        if 'granularity' in vim_config:
            return int(vim_config['granularity'])
        else:
            return int(self.conf.get('openstack', 'default_granularity'))

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
                    openstack_metric_name = METRIC_MAPPINGS[metric_name]
                    try:
                        resource_id = self._get_resource_uuid(nsr_id, vnf_member_index, vdur['name'])
                    except ValueError:
                        log.warning(
                            "Could not find resource_uuid for vdur %s, vnf_member_index %s, nsr_id %s. "
                            "Was it recently deleted?",
                            vdur['name'], vnf_member_index, nsr_id)
                        continue
                    if self.backend == 'ceilometer':
                        measures = self.client.samples.list(meter_name=openstack_metric_name, limit=1, q=[
                            {'field': 'resource_id', 'op': 'eq', 'value': resource_id}])
                        if measures:
                            metric = VnfMetric(nsr_id, vnf_member_index, vdur['name'], metric_name,
                                               measures[0].counter_volume)
                            metrics.append(metric)
                    elif self.backend == 'gnocchi':
                        delta = 10 * self.granularity
                        start_date = datetime.datetime.now() - datetime.timedelta(seconds=delta)
                        if metric_name in INTERFACE_METRICS:
                            total_measure = 0.0
                            interfaces = self.client.resource.search(resource_type='instance_network_interface',
                                                                     query={'=': {'instance_id': resource_id}})
                            for interface in interfaces:
                                try:
                                    measures = self.client.metric.get_measures(openstack_metric_name,
                                                                               start=start_date,
                                                                               resource_id=interface['id'],
                                                                               granularity=self.granularity)
                                    if measures:
                                        total_measure += measures[-1][2]

                                except gnocchiclient.exceptions.NotFound as e:
                                    log.debug("No metric %s found for interface %s: %s", openstack_metric_name,
                                              interface['id'], e)
                            metric = VnfMetric(nsr_id, vnf_member_index, vdur['name'], metric_name,
                                               total_measure)
                            metrics.append(metric)
                        else:
                            try:
                                measures = self.client.metric.get_measures(openstack_metric_name,
                                                                           start=start_date,
                                                                           resource_id=resource_id,
                                                                           granularity=self.granularity)
                                if measures:
                                    metric = VnfMetric(nsr_id, vnf_member_index, vdur['name'], metric_name,
                                                       measures[-1][2])
                                    metrics.append(metric)
                            except gnocchiclient.exceptions.NotFound as e:
                                log.debug("No metric %s found for instance %s: %s", openstack_metric_name, resource_id,
                                          e)

                    else:
                        raise Exception('Unknown metric backend: %s', self.backend)
        return metrics

    def _build_client(self, vim_account_id):
        if self.backend == 'ceilometer':
            return self._build_ceilometer_client(vim_account_id)
        elif self.backend == 'gnocchi':
            return self._build_gnocchi_client(vim_account_id)
        else:
            raise Exception('Unknown metric backend: %s', self.backend)

    def _get_backend(self, vim_account_id):
        try:
            gnocchi = self._build_gnocchi_client(vim_account_id)
            gnocchi.resource.list(limit=1)
            return 'gnocchi'
        except EndpointNotFound:
            try:
                ceilometer = self._build_ceilometer_client(vim_account_id)
                ceilometer.resources.list(limit=1)
                return 'ceilometer'
            except Exception:
                log.exception('Error trying to determine metric backend')
                raise Exception('Could not determine metric backend')
