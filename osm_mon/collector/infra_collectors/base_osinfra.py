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
import logging
from typing import List

from keystoneauth1 import session
from keystoneauth1.identity import v3
from keystoneclient.v3 import client as keystone_client
from novaclient import client as nova_client
from novaclient import v2 as nova_client_v2

from osm_mon.collector.infra_collectors.base_vim import BaseVimInfraCollector
from osm_mon.collector.metric import Metric
from osm_mon.collector.utils import CollectorUtils
from osm_mon.core.common_db import CommonDbClient
from osm_mon.core.config import Config

log = logging.getLogger(__name__)


class BaseOpenStackInfraCollector(BaseVimInfraCollector):
    def __init__(self, config: Config, vim_account_id: str):
        super().__init__(config, vim_account_id)
        self.keystone = self._build_keystone_client(vim_account_id)
        self.nova = self._build_nova_client(vim_account_id)
        self.vim_account_id = vim_account_id
        self.common_db = CommonDbClient(config)

    def collect(self) -> List[Metric]:
        metrics = []
        vim_status = self.is_vim_ok()
        vim_status_metric = Metric({'vim_account_id': self.vim_account_id}, 'vim_status', vim_status)
        metrics.append(vim_status_metric)
        vnfrs = self.common_db.get_vnfrs(vim_account_id=self.vim_account_id)
        for vnfr in vnfrs:
            nsr_id = vnfr['nsr-id-ref']
            vnf_member_index = vnfr['member-vnf-index-ref']
            for vdur in vnfr['vdur']:
                if 'vim-id' not in vdur:
                    log.debug("Field vim-id is not present in vdur")
                    continue
                resource_uuid = vdur['vim-id']
                tags = {
                    'vim_account_id': self.vim_account_id,
                    'resource_uuid': resource_uuid,
                    'nsr_id': nsr_id,
                    'vnf_member_index': vnf_member_index,
                    'vdur_name': vdur['name']
                }
                try:
                    vm = self.nova.servers.get(resource_uuid)
                    vm_status = (1 if vm.status == 'ACTIVE' else 0)
                    vm_status_metric = Metric(tags, 'vm_status', vm_status)
                except Exception as e:
                    log.warning("VM status is not OK: %s" % e)
                    vm_status_metric = Metric(tags, 'vm_status', 0)
                metrics.append(vm_status_metric)

        return metrics

    def is_vim_ok(self) -> bool:
        try:
            self.nova.servers.list()
            return True
        except Exception as e:
            log.warning("VIM status is not OK: %s" % e)
            return False

    def _build_keystone_client(self, vim_account_id) -> keystone_client.Client:
        sess = self._get_session(vim_account_id)
        return keystone_client.Client(session=sess)

    def _build_nova_client(self, vim_account_id) -> nova_client_v2.Client:
        sess = self._get_session(vim_account_id)
        return nova_client.Client("2", session=sess)

    def _get_session(self, vim_account_id: str):
        creds = CollectorUtils.get_credentials(vim_account_id)
        verify_ssl = CollectorUtils.is_verify_ssl(creds)
        auth = v3.Password(auth_url=creds.url,
                           username=creds.user,
                           password=creds.password,
                           project_name=creds.tenant_name,
                           project_domain_id='default',
                           user_domain_id='default')
        return session.Session(auth=auth, verify=verify_ssl)
