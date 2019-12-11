# -*- coding: utf-8 -*-

##
# Copyright 2016-2019 VMware Inc.
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

import logging
import traceback
from xml.etree import ElementTree as XmlElementTree

import requests
from pyvcloud.vcd.client import BasicLoginCredentials
from pyvcloud.vcd.client import Client

from osm_mon.collector.vnf_collectors.base_vim import BaseVimCollector
from osm_mon.collector.vnf_collectors.vrops.vrops_helper import vROPS_Helper
from osm_mon.core.common_db import CommonDbClient
from osm_mon.core.config import Config

log = logging.getLogger(__name__)

API_VERSION = '27.0'


class VMwareCollector(BaseVimCollector):
    def __init__(self, config: Config, vim_account_id: str):
        super().__init__(config, vim_account_id)
        self.common_db = CommonDbClient(config)
        vim_account = self.get_vim_account(vim_account_id)
        self.vcloud_site = vim_account['vim_url']
        self.admin_username = vim_account['admin_username']
        self.admin_password = vim_account['admin_password']
        self.vrops = vROPS_Helper(vrops_site=vim_account['vrops_site'],
                                  vrops_user=vim_account['vrops_user'],
                                  vrops_password=vim_account['vrops_password'])

    def connect_as_admin(self):
        """ Method connect as pvdc admin user to vCloud director.
            There are certain action that can be done only by provider vdc admin user.
            Organization creation / provider network creation etc.

            Returns:
                The return client object that letter can be used to connect to vcloud direct as admin for provider vdc
        """

        log.debug("Logging into vCD org as admin.")

        admin_user = None
        try:
            host = self.vcloud_site
            admin_user = self.admin_username
            admin_passwd = self.admin_password
            org = 'System'
            client = Client(host, verify_ssl_certs=False)
            client.set_highest_supported_version()
            client.set_credentials(BasicLoginCredentials(admin_user, org,
                                                         admin_passwd))
            return client

        except Exception as e:
            log.error("Can't connect to a vCloud director as: {} with exception {}".format(admin_user, e))

    def get_vim_account(self, vim_account_id: str):
        """
           Method to get VIM account details by its ID
           arg - VIM ID
           return - dict with vim account details
        """
        vim_account = {}
        vim_account_info = self.common_db.get_vim_account(vim_account_id)

        vim_account['vim_url'] = vim_account_info['vim_url']

        vim_config = vim_account_info['config']
        vim_account['admin_username'] = vim_config['admin_username']
        vim_account['admin_password'] = vim_config['admin_password']
        vim_account['vrops_site'] = vim_config['vrops_site']
        vim_account['vrops_user'] = vim_config['vrops_user']
        vim_account['vrops_password'] = vim_config['vrops_password']

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
                    log.debug("Found vm_moref_id: {} for vApp UUID: {}".format(vm_moref_id, vapp_uuid))
                else:
                    log.error("Failed to find vm_moref_id from vApp UUID: {}".format(vapp_uuid))

        except Exception as exp:
            log.warning("Error occurred while getting VM moref ID for VM: {}\n{}".format(exp, traceback.format_exc()))

        return vm_moref_id

    def get_vapp_details_rest(self, vapp_uuid=None):
        """
        Method retrieve vapp detail from vCloud director
        vapp_uuid - is vapp identifier.
        Returns - VM MOref ID or return None
        """
        parsed_respond = {}

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
                log.warning("Error occurred for getting vApp details: {}\n{}".format(exp,
                                                                                     traceback.format_exc()))

        return parsed_respond

    def collect(self, vnfr: dict):
        vnfd = self.common_db.get_vnfd(vnfr['vnfd-id'])
        vdu_mappings = {}

        # Populate extra tags for metrics
        nsr_id = vnfr['nsr-id-ref']
        tags = {}
        tags['ns_name'] = self.common_db.get_nsr(nsr_id)['name']
        if vnfr['_admin']['projects_read']:
            tags['project_id'] = vnfr['_admin']['projects_read'][0]
        else:
            tags['project_id'] = ''

        # Fetch the list of all known resources from vROPS.
        resource_list = self.vrops.get_vm_resource_list_from_vrops()

        for vdur in vnfr['vdur']:
            # This avoids errors when vdur records have not been completely filled
            if 'name' not in vdur:
                continue
            vdu = next(
                filter(lambda vdu: vdu['id'] == vdur['vdu-id-ref'], vnfd['vdu'])
            )

            if 'monitoring-param' not in vdu:
                continue

            resource_uuid = vdur['vim-id']
            # Find vm_moref_id from vApp uuid in vCD
            vim_id = self.get_vm_moref_id(resource_uuid)
            if vim_id is None:
                log.debug("Failed to find vROPS ID for vApp in vCD: {}".format(resource_uuid))
                continue

            vdu_mappings[vim_id] = {'name': vdur['name']}

            # Map the vROPS instance id to the vim-id so we can look it up.
            for resource in resource_list:
                for resourceIdentifier in resource['resourceKey']['resourceIdentifiers']:
                    if resourceIdentifier['identifierType']['name'] == 'VMEntityObjectID':
                        if resourceIdentifier['value'] != vim_id:
                            continue
                        vdu_mappings[vim_id]['vrops_id'] = resource['identifier']

        if len(vdu_mappings) != 0:
            return self.vrops.get_metrics(vdu_mappings=vdu_mappings,
                                          monitoring_params=vdu['monitoring-param'],
                                          vnfr=vnfr,
                                          tags=tags
                                          )
        else:
            return []
