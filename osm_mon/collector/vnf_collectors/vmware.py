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
import time
import traceback
from xml.etree import ElementTree as XmlElementTree

import requests
import six
from pyvcloud.vcd.client import BasicLoginCredentials
from pyvcloud.vcd.client import Client

from osm_mon.collector.utils import CollectorUtils
from osm_mon.collector.vnf_collectors.base_vim import BaseVimCollector
from osm_mon.collector.vnf_metric import VnfMetric
from osm_mon.core.common_db import CommonDbClient
from osm_mon.core.config import Config

log = logging.getLogger(__name__)

API_VERSION = '5.9'

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


class VMwareCollector(BaseVimCollector):
    def __init__(self, config: Config, vim_account_id: str):
        super().__init__(config, vim_account_id)
        self.common_db = CommonDbClient(config)
        vim_account = self.get_vim_account(vim_account_id)
        self.vrops_site = vim_account['vrops_site']
        self.vrops_user = vim_account['vrops_user']
        self.vrops_password = vim_account['vrops_password']
        self.vcloud_site = vim_account['vim_url']
        self.admin_username = vim_account['admin_username']
        self.admin_password = vim_account['admin_password']
        self.vim_uuid = vim_account['vim_uuid']

    def connect_as_admin(self):
        """ Method connect as pvdc admin user to vCloud director.
            There are certain action that can be done only by provider vdc admin user.
            Organization creation / provider network creation etc.

            Returns:
                The return client object that letter can be used to connect to vcloud direct as admin for provider vdc
        """

        log.info("Logging into vCD org as admin.")

        admin_user = None
        try:
            host = self.vcloud_site
            admin_user = self.admin_username
            admin_passwd = self.admin_password
            org = 'System'
            client = Client(host, verify_ssl_certs=False)
            client.set_credentials(BasicLoginCredentials(admin_user, org,
                                                         admin_passwd))
            return client

        except Exception as e:
            log.info("Can't connect to a vCloud director as: {} with exception {}".format(admin_user, e))

    def _get_resource_uuid(self, nsr_id, vnf_member_index, vdur_name) -> str:
        vdur = self.common_db.get_vdur(nsr_id, vnf_member_index, vdur_name)
        return vdur['vim-id']

    def get_vim_account(self, vim_account_id: str):
        """
           Method to get VIM account details by its ID
           arg - VIM ID
           return - dict with vim account details
        """
        vim_account = {}
        vim_account_info = CollectorUtils.get_credentials(vim_account_id)

        vim_account['name'] = vim_account_info.name
        vim_account['vim_tenant_name'] = vim_account_info.tenant_name
        vim_account['vim_type'] = vim_account_info.type
        vim_account['vim_url'] = vim_account_info.url
        vim_account['org_user'] = vim_account_info.user
        vim_account['org_password'] = vim_account_info.password
        vim_account['vim_uuid'] = vim_account_info.uuid

        vim_config = json.loads(vim_account_info.config)
        vim_account['admin_username'] = vim_config['admin_username']
        vim_account['admin_password'] = vim_config['admin_password']
        vim_account['vrops_site'] = vim_config['vrops_site']
        vim_account['vrops_user'] = vim_config['vrops_user']
        vim_account['vrops_password'] = vim_config['vrops_password']
        vim_account['vcenter_ip'] = vim_config['vcenter_ip']
        vim_account['vcenter_port'] = vim_config['vcenter_port']
        vim_account['vcenter_user'] = vim_config['vcenter_user']
        vim_account['vcenter_password'] = vim_config['vcenter_password']

        if vim_config['nsx_manager'] is not None:
            vim_account['nsx_manager'] = vim_config['nsx_manager']

        if vim_config['nsx_user'] is not None:
            vim_account['nsx_user'] = vim_config['nsx_user']

        if vim_config['nsx_password'] is not None:
            vim_account['nsx_password'] = vim_config['nsx_password']

        if vim_config['orgname'] is not None:
            vim_account['orgname'] = vim_config['orgname']

        return vim_account

    def get_vm_moref_id(self, vapp_uuid):
        """
           Method to get the moref_id of given VM
           arg - vapp_uuid
           return - VM mored_id
        """
        vm_moref_id = None
        try:
            if vapp_uuid:
                vm_details = self.get_vapp_details_rest(vapp_uuid)

                if vm_details and "vm_vcenter_info" in vm_details:
                    vm_moref_id = vm_details["vm_vcenter_info"].get("vm_moref_id", None)

            log.info("Found vm_moref_id: {} for vApp UUID: {}".format(vm_moref_id, vapp_uuid))
            return vm_moref_id

        except Exception as exp:
            log.info("Error occurred while getting VM moref ID for VM : {}\n{}".format(exp, traceback.format_exc()))

    def get_vapp_details_rest(self, vapp_uuid=None):
        """
        Method retrieve vapp detail from vCloud director
        vapp_uuid - is vapp identifier.
        Returns - VM MOref ID or return None
        """
        parsed_respond = {}
        vca = None

        if vapp_uuid is None:
            return parsed_respond

        vca = self.connect_as_admin()

        if not vca:
            log.error("Failed to connect to vCD")
            return parsed_respond

        url_list = [self.vcloud_site, '/api/vApp/vapp-', vapp_uuid]
        get_vapp_restcall = ''.join(url_list)

        if vca._session:
            headers = {'Accept': 'application/*+xml;version=' + API_VERSION,
                       'x-vcloud-authorization': vca._session.headers['x-vcloud-authorization']}
            response = requests.get(get_vapp_restcall,
                                    headers=headers,
                                    verify=False)

            if response.status_code != 200:
                log.error("REST API call {} failed. Return status code {}".format(get_vapp_restcall,
                                                                                  response.content))
                return parsed_respond

            try:
                xmlroot_respond = XmlElementTree.fromstring(response.content)

                namespaces = {'vm': 'http://www.vmware.com/vcloud/v1.5',
                              "vmext": "http://www.vmware.com/vcloud/extension/v1.5",
                              "xmlns": "http://www.vmware.com/vcloud/v1.5"}

                # parse children section for other attrib
                children_section = xmlroot_respond.find('vm:Children/', namespaces)
                if children_section is not None:
                    vCloud_extension_section = children_section.find('xmlns:VCloudExtension', namespaces)
                    if vCloud_extension_section is not None:
                        vm_vcenter_info = {}
                        vim_info = vCloud_extension_section.find('vmext:VmVimInfo', namespaces)
                        vmext = vim_info.find('vmext:VmVimObjectRef', namespaces)
                        if vmext is not None:
                            vm_vcenter_info["vm_moref_id"] = vmext.find('vmext:MoRef', namespaces).text
                        parsed_respond["vm_vcenter_info"] = vm_vcenter_info

            except Exception as exp:
                log.info("Error occurred for getting vApp details: {}\n{}".format(exp,
                                                                                  traceback.format_exc())
                         )

        return parsed_respond

    def get_vm_resource_id(self, vm_moref_id):
        """ Find resource ID in vROPs using vm_moref_id
        """
        if vm_moref_id is None:
            return None

        api_url = '/suite-api/api/resources?resourceKind=VirtualMachine'
        headers = {'Accept': 'application/json'}

        resp = requests.get(self.vrops_site + api_url,
                            auth=(self.vrops_user, self.vrops_password),
                            verify=False, headers=headers)

        if resp.status_code != 200:
            log.error("Failed to get resource details for{} {} {}".format(vm_moref_id,
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
                        resource_details = resource['resourceKey']
                        if resource_details.get('resourceIdentifiers') is not None:
                            resource_identifiers = resource_details['resourceIdentifiers']
                            for resource_identifier in resource_identifiers:
                                if resource_identifier['identifierType']['name'] == 'VMEntityObjectID':
                                    if resource_identifier.get('value') is not None and \
                                            resource_identifier['value'] == vm_moref_id:
                                        vm_resource_id = resource['identifier']
                                        log.info("Found VM resource ID: {} for vm_moref_id: {}".format(vm_resource_id,
                                                                                                       vm_moref_id))

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

                    # Find vm_moref_id from vApp uuid in vCD
                    vm_moref_id = self.get_vm_moref_id(resource_uuid)
                    if vm_moref_id is None:
                        log.debug("Failed to find vm morefid for vApp in vCD: {}".format(resource_uuid))
                        return

                    # Based on vm_moref_id, find VM's corresponding resource_id in vROPs
                    resource_id = self.get_vm_resource_id(vm_moref_id)
                    if resource_id is None:
                        log.debug("Failed to find resource in vROPs: {}".format(resource_uuid))
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
