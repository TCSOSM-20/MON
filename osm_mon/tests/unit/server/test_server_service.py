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
import json
from unittest import TestCase, mock

from osm_mon.core.common_db import CommonDbClient
from osm_mon.core.config import Config
from osm_mon.core.database import VimCredentialsRepository, VimCredentials
from osm_mon.server.service import ServerService


@mock.patch.object(CommonDbClient, "__init__", lambda *args, **kwargs: None)
class ServerServiceTest(TestCase):
    def setUp(self):
        super().setUp()
        self.config = Config()

    @mock.patch.object(CommonDbClient, "decrypt_vim_password")
    @mock.patch.object(VimCredentialsRepository, "upsert")
    @mock.patch('osm_mon.core.database.db')
    def test_upsert_vim_account(self, db, upsert_credentials, decrypt_vim_password):
        def _mock_decrypt_vim_password(password: str, schema_version: str, vim_uuid: str):
            return password.replace('encrypted', 'decrypted')

        decrypt_vim_password.side_effect = _mock_decrypt_vim_password

        mock_config = {
            'admin_password': 'encrypted_admin_password',
            'nsx_password': 'encrypted_nsx_password',
            'vcenter_password': 'encrypted_vcenter_password'
        }

        mock_expected_config = {
            'admin_password': 'decrypted_admin_password',
            'nsx_password': 'decrypted_nsx_password',
            'vcenter_password': 'decrypted_vcenter_password'
        }

        service = ServerService(self.config)
        service.upsert_vim_account('test_uuid', 'test_name', 'test_type', 'test_url', 'test_user', 'encrypted_password',
                                   'test_tenant_name', '1.1', mock_config)

        upsert_credentials.assert_called_with(
            uuid=mock.ANY,
            name='test_name',
            type='test_type',
            url='test_url',
            user='test_user',
            password='decrypted_password',
            tenant_name='test_tenant_name',
            config=json.dumps(mock_expected_config)
        )

    @mock.patch.object(VimCredentialsRepository, "get")
    @mock.patch('osm_mon.core.database.db')
    def test_delete_vim_account(self, db, get_credentials):
        mock_creds = mock.Mock()
        get_credentials.return_value = mock_creds

        service = ServerService(self.config)
        service.delete_vim_account('test_uuid')

        get_credentials.assert_called_with(VimCredentials.uuid == 'test_uuid')
        mock_creds.delete_instance.assert_called_with()
