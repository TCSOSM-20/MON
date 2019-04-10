# -*- coding: utf-8 -*-

##
# Copyright 2016-2017 VMware Inc.
# This file is part of ETSI OSM
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# For those usages not covered by the Apache License, Version 2.0 please
# contact:  osslegalrouting@vmware.com
##

import json
import logging

from keystoneauth1 import session
from keystoneauth1.identity import v3
from novaclient import client as nClient
import re
import requests
import time
import traceback
import six

from osm_mon.collector.vnf_collectors.base_vim import BaseVimCollector
from osm_mon.collector.vnf_metric import VnfMetric
from osm_mon.core.auth import AuthManager
from osm_mon.core.common_db import CommonDbClient
from osm_mon.core.config import Config

log = logging.getLogger(__name__)

PERIOD_MSEC = {'HR': 3600000,
               'DAY': 86400000,
               'WEEK': 604800000,
               'MONTH': 2678400000,
               'YEAR': 31536000000}

METRIC_MAPPINGS = {
    "average_memory_utilization": "mem|usage_average",
    "cpu_utilization": "cpu|usage_average",
    "read_latency_0": "virtualDisk:scsi0:0|totalReadLatency_average",
    "write_latency_0": "virtualDisk:scsi0:0|totalWriteLatency_average",
    "read_latency_1": "virtualDisk:scsi0:1|totalReadLatency_average",
    "write_latency_1": "virtualDisk:scsi0:1|totalWriteLatency_average",
    "packets_dropped_0": "net:4000|dropped",
    "packets_dropped_1": "net:4001|dropped",
    "packets_dropped_2": "net:4002|dropped",
    "packets_received": "net:Aggregate of all instances|packetsRxPerSec",
    "packets_sent": "net:Aggregate of all instances|packetsTxPerSec",
}


class VIOCollector(BaseVimCollector):
    def __init__(self, config: Config, vim_account_id: str):
        super().__init__(config, vim_account_id)
        self.common_db = CommonDbClient(config)
        self.auth_manager = AuthManager(config)
        vim_account_info = self.auth_manager.get_credentials(vim_account_id)
        cfg = json.loads(vim_account_info.config)
        self.vrops_site = cfg['vrops_site']
        self.vrops_user = cfg['vrops_user']
        self.vrops_password = cfg['vrops_password']
        self.client = self.connect_client(vim_account_id)

    def connect_client(self, vim_account_id: str):
        vim_account_details = self.auth_manager.get_credentials(vim_account_id)
        verify_ssl = self.auth_manager.is_verify_ssl(vim_account_id)
        auth = v3.Password(auth_url=vim_account_details.url,
                           username=vim_account_details.user,
                           password=vim_account_details.password,
                           project_name=vim_account_details.tenant_name,
                           project_domain_id='default',
                           user_domain_id='default')
        sess = session.Session(auth=auth, verify=verify_ssl)
        client = nClient.Client('2.1', session=sess, endpoint_type=None)
        return client

    def _get_resource_uuid(self, nsr_id, vnf_member_index, vdur_name) -> str:
        vdur = self.common_db.get_vdur(nsr_id, vnf_member_index, vdur_name)
        return vdur['vim-id']

    def get_vm_name_and_id(self, resource_uuid):
        """ Method to find vm name and id using resource_uuid
        """
        server = self.client.servers.find(id=resource_uuid)
        name = server.to_dict()['name']
        _id = server.to_dict()['id']
        return name, _id

    def get_vm_resource_id(self, name, _id):
        """ Find resource ID in vROPs
        """
        api_url = '/suite-api/api/resources?resourceKind=VirtualMachine'
        headers = {'Accept': 'application/json'}

        resp = requests.get(self.vrops_site + api_url,
                            auth=(self.vrops_user, self.vrops_password),
                            verify=False, headers=headers)

        if resp.status_code != 200:
            log.error("Failed to get resource details for{} {} {}".format(name,
                                                                          resp.status_code,
                                                                          resp.content))
            return None

        vm_resource_id = None
        try:
            resp_data = json.loads(resp.content.decode('utf-8'))
            if resp_data.get('resourceList') is not None:
                resource_list = resp_data.get('resourceList')
                for resource in resource_list:
                    if resource.get('resourceKey') is not None:
                        m = re.match(r"(.*?)\s\((.*?)\)", resource['resourceKey']['name'])
                        if m:
                            v_name = m.group(1)
                            v_id = m.group(2)
                        if name == v_name and _id == v_id:
                            vm_resource_id = resource['identifier']
                            log.info("Found VM resource ID: {} for vm: {}".format(vm_resource_id,
                                                                                  v_name))

        except Exception as exp:
            log.info("get_vm_resource_id: Error in parsing {}\n{}".format(exp, traceback.format_exc()))

        return vm_resource_id

    def collect(self, vnfr: dict):
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
                    vrops_metric_name = METRIC_MAPPINGS[metric_name]
                    resource_uuid = self._get_resource_uuid(nsr_id, vnf_member_index, vdur['name'])

                    name, _id = self.get_vm_name_and_id(resource_uuid)
                    if name and _id is not None:
                        resource_id = self.get_vm_resource_id(name, _id)
                    else:
                        return
                    try:
                        end_time = int(round(time.time() * 1000))
                        time_diff = PERIOD_MSEC['YEAR']
                        begin_time = end_time - time_diff

                        api_url = "/suite-api/api/resources/{}/stats?statKey={}&begin={}&end={}".format(
                                  resource_id, vrops_metric_name, str(begin_time), str(end_time))

                        headers = {'Accept': 'application/json'}

                        resp = requests.get(self.vrops_site + api_url,
                                            auth=(self.vrops_user, self.vrops_password), verify=False, headers=headers
                                            )

                        if resp.status_code != 200:
                            log.info("Failed to get Metrics data from vROPS for {} {} {}".format(vrops_metric_name,
                                                                                                 resp.status_code,
                                                                                                 resp.content))
                            return

                        metrics_data = {}
                        m_data = json.loads(resp.content.decode('utf-8'))

                        for resp_key, resp_val in six.iteritems(m_data):
                            if resp_key == 'values':
                                data = m_data['values'][0]
                                for data_k, data_v in six.iteritems(data):
                                    if data_k == 'stat-list':
                                        stat_list = data_v
                                        for stat_list_k, stat_list_v in six.iteritems(stat_list):
                                            for stat_keys, stat_vals in six.iteritems(stat_list_v[0]):
                                                if stat_keys == 'timestamps':
                                                    metrics_data['time_series'] = stat_list_v[0]['timestamps']
                                                if stat_keys == 'data':
                                                    metrics_data['metrics_series'] = stat_list_v[0]['data']

                        if metrics_data:
                            metric = VnfMetric(nsr_id,
                                               vnf_member_index,
                                               vdur['name'],
                                               metric_name,
                                               metrics_data['metrics_series'][-1])

                            metrics.append(metric)

                    except Exception as e:
                        log.debug("No metric found: %s", e)
                        pass

        return metrics
