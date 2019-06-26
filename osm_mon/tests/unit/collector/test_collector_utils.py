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
##
from unittest import TestCase, mock

from osm_mon.collector.utils.collector import CollectorUtils
from osm_mon.core.config import Config
from osm_mon.core.database import VimCredentialsRepository, VimCredentials


class CollectorServiceTest(TestCase):
    def setUp(self):
        super().setUp()
        self.config = Config()

    @mock.patch.object(VimCredentialsRepository, "get")
    @mock.patch('osm_mon.core.database.db')
    def test_get_vim_type(self, db, get_credentials):
        mock_creds = VimCredentials()
        mock_creds.id = 'test_id'
        mock_creds.user = 'user'
        mock_creds.url = 'url'
        mock_creds.password = 'password'
        mock_creds.tenant_name = 'tenant_name'
        mock_creds.type = 'openstack'
        mock_creds.config = '{}'

        get_credentials.return_value = mock_creds
        vim_type = CollectorUtils.get_vim_type('test_id')
        self.assertEqual(vim_type, 'openstack')
