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

from keystoneauth1 import session
from keystoneauth1.identity import v3
from keystoneclient.v3 import client

from osm_mon.collector.infra_collectors.base_vim import BaseVimInfraCollector
from osm_mon.core.auth import AuthManager

log = logging.getLogger(__name__)


class OpenstackInfraCollector(BaseVimInfraCollector):
    def __init__(self, vim_account_id: str):
        super().__init__(vim_account_id)
        self.auth_manager = AuthManager()
        self.keystone_client = self._build_keystone_client(vim_account_id)

    def is_vim_ok(self) -> bool:
        try:
            self.keystone_client.projects.list()
            return True
        except Exception:
            log.exception("VIM status is not OK!")
            return False

    def _build_keystone_client(self, vim_account_id):
        creds = self.auth_manager.get_credentials(vim_account_id)
        verify_ssl = self.auth_manager.is_verify_ssl(vim_account_id)
        auth = v3.Password(auth_url=creds.url,
                           username=creds.user,
                           password=creds.password,
                           project_name=creds.tenant_name,
                           project_domain_id='default',
                           user_domain_id='default')
        sess = session.Session(auth=auth, verify=verify_ssl)
        return client.Client(session=sess)
