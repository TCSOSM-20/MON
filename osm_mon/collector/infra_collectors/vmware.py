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

import logging
from typing import List

from xml.etree import ElementTree as XmlElementTree
from pyvcloud.vcd.client import BasicLoginCredentials
from pyvcloud.vcd.client import Client

from osm_mon.collector.utils import CollectorUtils
from osm_mon.collector.infra_collectors.base_vim import BaseVimInfraCollector
from osm_mon.collector.metric import Metric
from osm_mon.core.common_db import CommonDbClient
from osm_mon.core.config import Config
import requests
import json

log = logging.getLogger(__name__)
API_VERSION = '27.0'


class VMwareInfraCollector(BaseVimInfraCollector):
    def __init__(self, config: Config, vim_account_id: str):
        super().__init__(config, vim_account_id)
        self.vim_account_id = vim_account_id
        self.common_db = CommonDbClient(config)
        vim_account = self.get_vim_account(vim_account_id)
        self.vcloud_site = vim_account['vim_url']
        self.admin_username = vim_account['admin_username']
        self.admin_password = vim_account['admin_password']
        self.vim_uuid = vim_account['vim_uuid']
        self.org_name = vim_account['orgname']

    def connect_vim_as_admin(self):
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

        if vim_config['orgname'] is not None:
            vim_account['orgname'] = vim_config['orgname']

        return vim_account

    def check_vim_status(self):
        try:
            client = self.connect_vim_as_admin()
            if client._session:
                org_list = client.get_org_list()
                for org in org_list.Org:
                    if org.get('name') == self.org_name:
                        org_uuid = org.get('href').split('/')[-1]

                url = '{}/api/org/{}'.format(self.vcloud_site, org_uuid)

                headers = {'Accept': 'application/*+xml;version=' + API_VERSION,
                           'x-vcloud-authorization': client._session.headers['x-vcloud-authorization']}

                response = requests.get(url=url,
                                        headers=headers,
                                        verify=False)

                if response.status_code != requests.codes.ok:  # pylint: disable=no-member
                    log.info("check_vim_status(): failed to get org details")
                else:
                    org_details = XmlElementTree.fromstring(response.content)
                    vdc_list = {}
                    for child in org_details:
                        if 'type' in child.attrib:
                            if child.attrib['type'] == 'application/vnd.vmware.vcloud.vdc+xml':
                                vdc_list[child.attrib['href'].split("/")[-1:][0]] = child.attrib['name']

                if vdc_list:
                    return True
                else:
                    return False
        except Exception as e:
            log.info("Exception occured while checking vim status {}".format(str(e)))

    def check_vm_status(self, vapp_id):
        try:
            client = self.connect_vim_as_admin()
            if client._session:
                url = '{}/api/vApp/vapp-{}'.format(self.vcloud_site, vapp_id)

                headers = {'Accept': 'application/*+xml;version=' + API_VERSION,
                           'x-vcloud-authorization': client._session.headers['x-vcloud-authorization']}

                response = requests.get(url=url,
                                        headers=headers,
                                        verify=False)

                if response.status_code != requests.codes.ok:  # pylint: disable=no-member
                    log.info("check_vm_status(): failed to get vApp details")
                else:
                    vapp_details = XmlElementTree.fromstring(response.content)
                    vm_list = []
                    for child in vapp_details:
                        if child.tag.split("}")[1] == 'Children':
                            for item in child.getchildren():
                                vm_list.append(item.attrib)
                return vm_list
        except Exception as e:
            log.info("Exception occured while checking vim status {}".format(str(e)))

    def collect(self) -> List[Metric]:
        metrics = []
        vim_status = self.check_vim_status()
        vim_status_metric = Metric({'vim_account_id': self.vim_account_id}, 'vim_status', vim_status)
        metrics.append(vim_status_metric)
        vnfrs = self.common_db.get_vnfrs(vim_account_id=self.vim_account_id)
        for vnfr in vnfrs:
            nsr_id = vnfr['nsr-id-ref']
            vnf_member_index = vnfr['member-vnf-index-ref']
            for vdur in vnfr['vdur']:
                resource_uuid = vdur['vim-id']
                tags = {
                    'vim_account_id': self.vim_account_id,
                    'resource_uuid': resource_uuid,
                    'nsr_id': nsr_id,
                    'vnf_member_index': vnf_member_index,
                    'vdur_name': vdur['name']
                }
                try:
                    vm_list = self.check_vm_status(resource_uuid)
                    for vm in vm_list:
                        if vm['status'] == '4' and vm['deployed'] == 'true':
                            vm_status = 1
                        else:
                            vm_status = 0
                        vm_status_metric = Metric(tags, 'vm_status', vm_status)
                except Exception:
                    log.exception("VM status is not OK!")
                    vm_status_metric = Metric(tags, 'vm_status', 0)
                metrics.append(vm_status_metric)
        return metrics
