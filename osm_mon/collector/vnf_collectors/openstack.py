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
from enum import Enum
from typing import List

import gnocchiclient.exceptions
from ceilometerclient.v2 import client as ceilometer_client
from gnocchiclient.v1 import client as gnocchi_client
from keystoneauth1 import session
from keystoneauth1.exceptions.catalog import EndpointNotFound
from keystoneauth1.identity import v3
from keystoneclient.v3 import client as keystone_client
from neutronclient.v2_0 import client as neutron_client

from osm_mon.collector.metric import Metric
from osm_mon.collector.utils import CollectorUtils
from osm_mon.collector.vnf_collectors.base_vim import BaseVimCollector
from osm_mon.collector.vnf_metric import VnfMetric
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


class MetricType(Enum):
    INSTANCE = 'instance'
    INTERFACE_ALL = 'interface_all'
    INTERFACE_ONE = 'interface_one'


class OpenstackCollector(BaseVimCollector):
    def __init__(self, config: Config, vim_account_id: str):
        super().__init__(config, vim_account_id)
        self.conf = config
        self.common_db = CommonDbClient(config)
        self.backend = self._get_backend(vim_account_id)

    def _build_keystone_client(self, vim_account_id: str) -> keystone_client.Client:
        sess = OpenstackBackend.get_session(vim_account_id)
        return keystone_client.Client(session=sess)

    def _get_resource_uuid(self, nsr_id: str, vnf_member_index: str, vdur_name: str) -> str:
        vdur = self.common_db.get_vdur(nsr_id, vnf_member_index, vdur_name)
        return vdur['vim-id']

    def _get_granularity(self, vim_account_id: str):
        creds = CollectorUtils.get_credentials(vim_account_id)
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
                    interface_name = param['interface-name-ref'] if 'interface-name-ref' in param else None
                    openstack_metric_name = METRIC_MAPPINGS[metric_name]
                    metric_type = self._get_metric_type(metric_name, interface_name)
                    try:
                        resource_id = self._get_resource_uuid(nsr_id, vnf_member_index, vdur['name'])
                    except ValueError:
                        log.warning(
                            "Could not find resource_uuid for vdur %s, vnf_member_index %s, nsr_id %s. "
                            "Was it recently deleted?",
                            vdur['name'], vnf_member_index, nsr_id)
                        continue
                    try:
                        value = self.backend.collect_metric(metric_type, openstack_metric_name, resource_id,
                                                            interface_name)
                        if value is not None:
                            tags = {}
                            if interface_name:
                                tags['interface'] = interface_name
                            metric = VnfMetric(nsr_id, vnf_member_index, vdur['name'], metric_name, value, tags)
                            metrics.append(metric)
                    except Exception:
                        log.exception("Error collecting metric %s for vdu %s" % (metric_name, vdur['name']))
        return metrics

    def _get_backend(self, vim_account_id: str):
        try:
            ceilometer = CeilometerBackend(vim_account_id)
            ceilometer.client.capabilities.get()
            return ceilometer
        except EndpointNotFound:
            granularity = self._get_granularity(vim_account_id)
            gnocchi = GnocchiBackend(vim_account_id, granularity)
            gnocchi.client.status.get()
            return gnocchi

    def _get_metric_type(self, metric_name: str, interface_name: str) -> MetricType:
        if metric_name not in INTERFACE_METRICS:
            return MetricType.INSTANCE
        else:
            if interface_name:
                return MetricType.INTERFACE_ONE
            return MetricType.INTERFACE_ALL


class OpenstackBackend:
    def collect_metric(self, metric_type: MetricType, metric_name: str, resource_id: str, interface_name: str):
        pass

    @staticmethod
    def get_session(vim_account_id: str):
        creds = CollectorUtils.get_credentials(vim_account_id)
        verify_ssl = CollectorUtils.is_verify_ssl(creds)
        auth = v3.Password(auth_url=creds.url,
                           username=creds.user,
                           password=creds.password,
                           project_name=creds.tenant_name,
                           project_domain_id='default',
                           user_domain_id='default')
        return session.Session(auth=auth, verify=verify_ssl)


class GnocchiBackend(OpenstackBackend):

    def __init__(self, vim_account_id: str, granularity: int):
        self.client = self._build_gnocchi_client(vim_account_id)
        self.neutron = self._build_neutron_client(vim_account_id)
        self.granularity = granularity

    def _build_gnocchi_client(self, vim_account_id: str) -> gnocchi_client.Client:
        sess = OpenstackBackend.get_session(vim_account_id)
        return gnocchi_client.Client(session=sess)

    def _build_neutron_client(self, vim_account_id: str) -> neutron_client.Client:
        sess = OpenstackBackend.get_session(vim_account_id)
        return neutron_client.Client(session=sess)

    def collect_metric(self, metric_type: MetricType, metric_name: str, resource_id: str, interface_name: str):
        if metric_type == MetricType.INTERFACE_ONE:
            return self._collect_interface_one_metric(metric_name, resource_id, interface_name)

        if metric_type == MetricType.INTERFACE_ALL:
            return self._collect_interface_all_metric(metric_name, resource_id)

        elif metric_type == MetricType.INSTANCE:
            return self._collect_instance_metric(metric_name, resource_id)

        else:
            raise Exception('Unknown metric type %s' % metric_type.value)

    def _collect_interface_one_metric(self, metric_name, resource_id, interface_name):
        delta = 10 * self.granularity
        start_date = datetime.datetime.now() - datetime.timedelta(seconds=delta)
        ports = self.neutron.list_ports(name=interface_name, device_id=resource_id)
        if not ports or not ports['ports']:
            raise Exception(
                'Port not found for interface %s on instance %s' % (interface_name, resource_id))
        port = ports['ports'][0]
        port_uuid = port['id'][:11]
        tap_name = 'tap' + port_uuid
        interfaces = self.client.resource.search(resource_type='instance_network_interface',
                                                 query={'=': {'name': tap_name}})
        measures = self.client.metric.get_measures(metric_name,
                                                   start=start_date,
                                                   resource_id=interfaces[0]['id'],
                                                   granularity=self.granularity)
        return measures[-1][2] if measures else None

    def _collect_interface_all_metric(self, openstack_metric_name, resource_id):
        delta = 10 * self.granularity
        start_date = datetime.datetime.now() - datetime.timedelta(seconds=delta)
        total_measure = None
        interfaces = self.client.resource.search(resource_type='instance_network_interface',
                                                 query={'=': {'instance_id': resource_id}})
        for interface in interfaces:
            try:
                measures = self.client.metric.get_measures(openstack_metric_name,
                                                           start=start_date,
                                                           resource_id=interface['id'],
                                                           granularity=self.granularity)
                if measures:
                    if not total_measure:
                        total_measure = 0.0
                    total_measure += measures[-1][2]

            except gnocchiclient.exceptions.NotFound as e:
                log.debug("No metric %s found for interface %s: %s", openstack_metric_name,
                          interface['id'], e)
        return total_measure

    def _collect_instance_metric(self, openstack_metric_name, resource_id):
        delta = 10 * self.granularity
        start_date = datetime.datetime.now() - datetime.timedelta(seconds=delta)
        value = None
        try:
            measures = self.client.metric.get_measures(openstack_metric_name,
                                                       start=start_date,
                                                       resource_id=resource_id,
                                                       granularity=self.granularity)
            if measures:
                value = measures[-1][2]
        except gnocchiclient.exceptions.NotFound as e:
            log.debug("No metric %s found for instance %s: %s", openstack_metric_name, resource_id,
                      e)
        return value


class CeilometerBackend(OpenstackBackend):
    def __init__(self, vim_account_id: str):
        self.client = self._build_ceilometer_client(vim_account_id)

    def _build_ceilometer_client(self, vim_account_id: str) -> ceilometer_client.Client:
        sess = OpenstackBackend.get_session(vim_account_id)
        return ceilometer_client.Client(session=sess)

    def collect_metric(self, metric_type: MetricType, metric_name: str, resource_id: str, interface_name: str):
        if metric_type != MetricType.INSTANCE:
            raise NotImplementedError('Ceilometer backend only support instance metrics')
        measures = self.client.samples.list(meter_name=metric_name, limit=1, q=[
            {'field': 'resource_id', 'op': 'eq', 'value': resource_id}])
        return measures[0].counter_volume if measures else None
