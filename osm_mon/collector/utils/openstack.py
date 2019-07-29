# -*- coding: utf-8 -*-

# Copyright 2019 Whitestack, LLC
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

from keystoneauth1 import session
from keystoneauth1.identity import v3


class OpenstackUtils:

    @staticmethod
    def get_session(creds: dict):
        verify_ssl = False if 'insecure' in creds['config'] and creds['config']['insecure'] else True
        vim_config = creds['config']
        project_domain_name = 'Default'
        user_domain_name = 'Default'
        if 'project_domain_name' in vim_config:
            project_domain_name = vim_config['project_domain_name']
        if 'user_domain_name' in vim_config:
            user_domain_name = vim_config['user_domain_name']
        auth = v3.Password(auth_url=creds['vim_url'],
                           username=creds['vim_user'],
                           password=creds['vim_password'],
                           project_name=creds['vim_tenant_name'],
                           project_domain_name=project_domain_name,
                           user_domain_name=user_domain_name)
        return session.Session(auth=auth, verify=verify_ssl)
