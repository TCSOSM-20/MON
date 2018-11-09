# -*- coding: utf-8 -*-

# Copyright 2018 Whitestack, LLC
# *************************************************************

# This file is part of OSM Monitoring module
# All Rights Reserved to Whitestack, LLC

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at

#         http://www.apache.org/licenses/LICENSE-2.0

import multiprocessing
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

from osm_mon.collector.collector import Collector
from osm_mon.collector.collectors.juju import VCACollector
from osm_mon.collector.collectors.openstack import OpenstackCollector
from osm_mon.core.database import VimCredentials


class CollectorTest(unittest.TestCase):
    def setUp(self):
        super().setUp()

    @mock.patch("osm_mon.collector.collector.CommonDbClient", autospec=True)
    def test_get_vim_id(self, common_db):
        common_db.return_value.get_vnfr.return_value = {'_id': 'a314c865-aee7-4d9b-9c9d-079d7f857f01',
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
        collector = Collector()
        vim_account_id = collector._get_vim_account_id('5ec3f571-d540-4cb0-9992-971d1b08312e', 1)
        self.assertEqual(vim_account_id, 'c1740601-7287-48c8-a2c9-bce8fee459eb')

    @mock.patch("osm_mon.collector.collector.CommonDbClient", mock.Mock())
    @mock.patch("osm_mon.collector.collector.DatabaseManager", autospec=True)
    def test_get_vim_type(self, database_manager):
        mock_creds = VimCredentials()
        mock_creds.id = 'test_id'
        mock_creds.user = 'user'
        mock_creds.url = 'url'
        mock_creds.password = 'password'
        mock_creds.tenant_name = 'tenant_name'
        mock_creds.type = 'openstack'

        database_manager.return_value.get_credentials.return_value = mock_creds
        collector = Collector()
        vim_type = collector._get_vim_type('test_id')
        self.assertEqual(vim_type, 'openstack')

    @mock.patch("osm_mon.collector.collector.CommonDbClient", mock.Mock())
    @mock.patch.object(OpenstackCollector, "__init__", lambda *args, **kwargs: None)
    @mock.patch.object(OpenstackCollector, "collect")
    @mock.patch.object(Collector, "_get_vim_type")
    def test_init_vim_collector_and_collect_openstack(self, _get_vim_type, collect):
        _get_vim_type.return_value = 'openstack'
        collector = Collector()
        queue = multiprocessing.Queue()
        collector._init_vim_collector_and_collect({}, 'test_vim_account_id', queue)
        collect.assert_called_once_with({}, queue)

    @mock.patch("osm_mon.collector.collector.CommonDbClient", mock.Mock())
    @mock.patch.object(OpenstackCollector, "collect")
    @mock.patch.object(Collector, "_get_vim_type")
    def test_init_vim_collector_and_collect_unknown(self, _get_vim_type, openstack_collect):
        _get_vim_type.return_value = 'unknown'
        collector = Collector()
        queue = multiprocessing.Queue()
        collector._init_vim_collector_and_collect({}, 'test_vim_account_id', queue)
        openstack_collect.assert_not_called()

    @mock.patch("osm_mon.collector.collector.CommonDbClient", mock.Mock())
    @mock.patch("osm_mon.collector.collector.VCACollector", autospec=True)
    def test_init_vca_collector_and_collect(self, vca_collector):
        collector = Collector()
        queue = multiprocessing.Queue()
        collector._init_vca_collector_and_collect({}, queue)
        vca_collector.assert_called_once_with()
        vca_collector.return_value.collect.assert_called_once_with({}, queue)
