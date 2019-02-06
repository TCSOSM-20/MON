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
import unittest
from unittest import mock

from osm_common import dbmongo

from osm_mon.core.common_db import CommonDbClient
from osm_mon.core.config import Config


class CommonDbClientTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.config = Config()

    @mock.patch.object(dbmongo.DbMongo, "db_connect", mock.Mock())
    @mock.patch.object(CommonDbClient, "get_vnfr")
    def test_get_vim_id(self, get_vnfr):
        get_vnfr.return_value = {'_id': 'a314c865-aee7-4d9b-9c9d-079d7f857f01',
                                 '_admin': {
                                     'projects_read': ['admin'], 'created': 1526044312.102287,
                                     'modified': 1526044312.102287, 'projects_write': ['admin']
                                 },
                                 'vim-account-id': 'c1740601-7287-48c8-a2c9-bce8fee459eb',
                                 'nsr-id-ref': '5ec3f571-d540-4cb0-9992-971d1b08312e',
                                 'vdur': [
                                     {
                                         'internal-connection-point': [],
                                         'vdu-id-ref': 'ubuntuvnf_vnfd-VM',
                                         'id': 'ffd73f33-c8bb-4541-a977-44dcc3cbe28d',
                                         'vim-id': '27042672-5190-4209-b844-95bbaeea7ea7',
                                         'name': 'ubuntuvnf_vnfd-VM'
                                     }
                                 ],
                                 'vnfd-ref': 'ubuntuvnf_vnfd',
                                 'member-vnf-index-ref': '1',
                                 'created-time': 1526044312.0999322,
                                 'vnfd-id': 'a314c865-aee7-4d9b-9c9d-079d7f857f01',
                                 'id': 'a314c865-aee7-4d9b-9c9d-079d7f857f01'}
        common_db_client = CommonDbClient(self.config)
        vim_account_id = common_db_client.get_vim_account_id('5ec3f571-d540-4cb0-9992-971d1b08312e', 1)
        self.assertEqual(vim_account_id, 'c1740601-7287-48c8-a2c9-bce8fee459eb')

    @mock.patch.object(dbmongo.DbMongo, "db_connect", mock.Mock())
    @mock.patch.object(dbmongo.DbMongo, "get_one")
    def test_get_vdur(self, get_one):
        get_one.return_value = {'_id': 'a314c865-aee7-4d9b-9c9d-079d7f857f01',
                                '_admin': {
                                    'projects_read': ['admin'], 'created': 1526044312.102287,
                                    'modified': 1526044312.102287, 'projects_write': ['admin']
                                },
                                'vim-account-id': 'c1740601-7287-48c8-a2c9-bce8fee459eb',
                                'nsr-id-ref': '5ec3f571-d540-4cb0-9992-971d1b08312e',
                                'vdur': [
                                    {
                                        'internal-connection-point': [],
                                        'vdu-id-ref': 'ubuntuvnf_vnfd-VM',
                                        'id': 'ffd73f33-c8bb-4541-a977-44dcc3cbe28d',
                                        'vim-id': '27042672-5190-4209-b844-95bbaeea7ea7',
                                        'name': 'ubuntuvnf_vnfd-VM'
                                    }
                                ],
                                'vnfd-ref': 'ubuntuvnf_vnfd',
                                'member-vnf-index-ref': '1',
                                'created-time': 1526044312.0999322,
                                'vnfd-id': 'a314c865-aee7-4d9b-9c9d-079d7f857f01',
                                'id': 'a314c865-aee7-4d9b-9c9d-079d7f857f01'}
        common_db_client = CommonDbClient(self.config)
        vdur = common_db_client.get_vdur('5ec3f571-d540-4cb0-9992-971d1b08312e', '1', 'ubuntuvnf_vnfd-VM')
        expected_vdur = {
            'internal-connection-point': [],
            'vdu-id-ref': 'ubuntuvnf_vnfd-VM',
            'id': 'ffd73f33-c8bb-4541-a977-44dcc3cbe28d',
            'vim-id': '27042672-5190-4209-b844-95bbaeea7ea7',
            'name': 'ubuntuvnf_vnfd-VM'
        }

        self.assertDictEqual(vdur, expected_vdur)
