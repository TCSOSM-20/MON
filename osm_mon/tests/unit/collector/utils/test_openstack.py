# -*- coding: utf-8 -*-

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
# #
from unittest import TestCase, mock

from osm_mon.collector.utils.openstack import OpenstackUtils


@mock.patch('osm_mon.collector.utils.openstack.session')
class OpenstackUtilsTest(TestCase):

    def setUp(self):
        super().setUp()

    def test_session_without_insecure(self, mock_session):
        creds = {
            'config': {
            },
            'vim_url': 'url',
            'vim_user': 'user',
            'vim_password': 'password',
            'vim_tenant_name': 'tenant_name'
        }
        OpenstackUtils.get_session(creds)

        mock_session.Session.assert_called_once_with(
            auth=mock.ANY, verify=True, timeout=10)

    def test_session_with_insecure(self, mock_session):
        creds = {
            'config': {
                'insecure': True
            },
            'vim_url': 'url',
            'vim_user': 'user',
            'vim_password': 'password',
            'vim_tenant_name': 'tenant_name'
        }
        OpenstackUtils.get_session(creds)

        mock_session.Session.assert_called_once_with(
            auth=mock.ANY, verify=False, timeout=10)

    def test_session_with_insecure_false(self, mock_session):
        creds = {
            'config': {
                'insecure': False
            },
            'vim_url': 'url',
            'vim_user': 'user',
            'vim_password': 'password',
            'vim_tenant_name': 'tenant_name'
        }
        OpenstackUtils.get_session(creds)
        mock_session.Session.assert_called_once_with(
            auth=mock.ANY, verify=True, timeout=10)
