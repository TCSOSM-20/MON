# -*- coding: utf-8 -*-
# #
# Copyright 2016-2019 VMware Inc.
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
# #

from osm_mon.collector.vnf_collectors.vio import VIOCollector
from osm_mon.core.config import Config
from osm_mon.tests.unit.collector.vnf_collectors.vmware.mock_http import mock_http_response
from unittest import TestCase, mock

import json
import os
import requests_mock

VIM_ACCOUNT = {"vrops_site": "https://vrops",
               "vrops_user": "",
               "vrops_password": "",
               "vim_url": "",
               "admin_username": "",
               "admin_password": "",
               "vim_uuid": ""}


class CollectorTest(TestCase):

    @mock.patch.object(VIOCollector, 'get_vim_account',
                       spec_set=True, autospec=True)
    @mock.patch('osm_mon.collector.vnf_collectors.vio.CommonDbClient')
    def setUp(self, mock_db, mock_get_vim_account):
        super().setUp()
        self.mock_db = mock_db
        mock_get_vim_account.return_value = VIM_ACCOUNT
        self.collector = VIOCollector(Config(), "9de6df67-b820-48c3-bcae-ee4838c5c5f4")
        with open(os.path.join(os.path.dirname(__file__), 'osm_mocks', 'VNFR.json'), 'r') as f:
            self.vnfr = json.load(f)
        with open(os.path.join(os.path.dirname(__file__), 'osm_mocks', 'VNFD.json'), 'r') as f:
            self.vnfd = json.load(f)

    def tearDown(self):
        super().tearDown()

    def test_collect_cpu_and_memory(self):
        self.vnfd['vdu'][0]['monitoring-param'] = [
            {"id": "ubuntu_vnfd-VM_cpu_util", "nfvi-metric": "cpu_utilization"},
            {"id": "ubuntu_vnfd-VM_average_memory_utilization", "nfvi-metric": "average_memory_utilization"}
            ]
        self.mock_db.return_value.get_vnfd.return_value = self.vnfd
        with requests_mock.Mocker() as mock_requests:
            mock_http_response(mock_requests,
                               url_pattern='/suite-api/api/resources\\?resourceKind=VirtualMachine',
                               response_file='vrops_resources.json')
            mock_http_response(mock_requests,
                               url_pattern='/suite-api/api/resources/stats.*',
                               response_file='vrops_multi.json')
            metrics = self.collector.collect(self.vnfr)
            self.assertEqual(len(metrics), 4, "Number of metrics returned")
            self.assertEqual(metrics[0].name, "cpu_utilization", "First metric name")
            self.assertEqual(metrics[0].value, 100.0, "CPU metric value")
            self.assertEqual(metrics[1].name, "average_memory_utilization", "Second metric name")
            self.assertEqual(metrics[1].value, 20.515941619873047, "Memory metric value")
            self.assertEqual(metrics[2].name, "cpu_utilization", "First metric name")
            self.assertEqual(metrics[2].value, 0.05400000140070915, "CPU metric value")
            self.assertEqual(metrics[3].name, "average_memory_utilization", "Second metric name")
            self.assertEqual(metrics[3].value, 15.23439884185791, "Memory metric value")

    def test_collect_no_monitoring_param(self):
        self.vnfd['vdu'][0]['monitoring-param'] = []
        self.mock_db.return_value.get_vnfd.return_value = self.vnfd
        with requests_mock.Mocker() as mock_requests:
            mock_http_response(mock_requests,
                               url_pattern='/suite-api/api/resources\\?resourceKind=VirtualMachine',
                               response_file='vrops_resources.json')
            mock_http_response(mock_requests,
                               url_pattern='/suite-api/api/resources/stats.*',
                               response_file='vrops_multi.json')
            metrics = self.collector.collect(self.vnfr)
            self.assertEqual(len(metrics), 0, "Number of metrics returned")

    def test_collect_empty_monitoring_param(self):
        del self.vnfd['vdu'][0]['monitoring-param']
        self.mock_db.return_value.get_vnfd.return_value = self.vnfd
        with requests_mock.Mocker() as mock_requests:
            mock_http_response(mock_requests,
                               url_pattern='/suite-api/api/resources\\?resourceKind=VirtualMachine',
                               response_file='vrops_resources.json')
            mock_http_response(mock_requests,
                               url_pattern='/suite-api/api/resources/stats.*',
                               response_file='vrops_multi.json')
            metrics = self.collector.collect(self.vnfr)
            self.assertEqual(len(metrics), 0, "Number of metrics returned")

    def test_collect_no_name(self):
        del self.vnfr['vdur'][0]['name']
        del self.vnfr['vdur'][1]['name']
        self.mock_db.return_value.get_vnfd.return_value = self.vnfd
        with requests_mock.Mocker() as mock_requests:
            mock_http_response(mock_requests,
                               url_pattern='/suite-api/api/resources\\?resourceKind=VirtualMachine',
                               response_file='vrops_resources.json')
            mock_http_response(mock_requests,
                               url_pattern='/suite-api/api/resources/stats.*',
                               response_file='vrops_multi.json')
            metrics = self.collector.collect(self.vnfr)
            self.assertEqual(len(metrics), 0, "Number of metrics returned")
