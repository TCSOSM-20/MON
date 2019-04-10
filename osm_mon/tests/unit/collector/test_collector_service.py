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

from osm_mon.collector.service import CollectorService
from osm_mon.collector.utils import CollectorUtils
from osm_mon.collector.vnf_collectors.openstack import OpenstackCollector
from osm_mon.core.common_db import CommonDbClient
from osm_mon.core.config import Config


@mock.patch.object(CommonDbClient, "__init__", lambda *args, **kwargs: None)
class CollectorServiceTest(TestCase):
    def setUp(self):
        super().setUp()
        self.config = Config()

    @mock.patch.object(OpenstackCollector, "__init__", lambda *args, **kwargs: None)
    @mock.patch.object(OpenstackCollector, "collect")
    @mock.patch.object(CollectorUtils, "get_vim_type")
    def test_init_vim_collector_and_collect_openstack(self, _get_vim_type, collect):
        _get_vim_type.return_value = 'openstack'
        collector = CollectorService(self.config)
        collector._collect_vim_metrics({}, 'test_vim_account_id')
        collect.assert_called_once_with({})

    @mock.patch.object(OpenstackCollector, "collect")
    @mock.patch.object(CollectorUtils, "get_vim_type")
    def test_init_vim_collector_and_collect_unknown(self, _get_vim_type, openstack_collect):
        _get_vim_type.return_value = 'unknown'
        collector = CollectorService(self.config)
        collector._collect_vim_metrics({}, 'test_vim_account_id')
        openstack_collect.assert_not_called()

    @mock.patch("osm_mon.collector.service.VCACollector", autospec=True)
    def test_collect_vca_metrics(self, vca_collector):
        collector = CollectorService(self.config)
        collector._collect_vca_metrics({})
        vca_collector.assert_called_once_with(self.config)
        vca_collector.return_value.collect.assert_called_once_with({})
