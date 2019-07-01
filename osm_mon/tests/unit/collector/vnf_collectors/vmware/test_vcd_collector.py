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

from osm_mon.collector.vnf_collectors.vmware import VMwareCollector
from osm_mon.core.config import Config
from osm_mon.tests.unit.collector.vnf_collectors.vmware.mock_vcd import mock_vdc_response
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


@mock.patch.object(VMwareCollector, 'get_vm_resource_id',
                   spec_set=True, autospec=True)
@mock.patch.object(VMwareCollector, 'get_vm_moref_id',
                   spec_set=True, autospec=True)
class CollectorTest(TestCase):

    @mock.patch.object(VMwareCollector, 'get_vim_account',
                       spec_set=True, autospec=True)
    @mock.patch('osm_mon.collector.vnf_collectors.vmware.CommonDbClient')
    def setUp(self, mock_db, mock_get_vim_account):
        super().setUp()
        mock_get_vim_account.return_value = VIM_ACCOUNT
        self.collector = VMwareCollector(Config(), "9de6df67-b820-48c3-bcae-ee4838c5c5f4")
        self.mock_db = mock_db
        with open(os.path.join(os.path.dirname(__file__), 'osm_mocks', 'VNFR.json'), 'r') as f:
            self.vnfr = json.load(f)
        with open(os.path.join(os.path.dirname(__file__), 'osm_mocks', 'VNFD.json'), 'r') as f:
            self.vnfd = json.load(f)

    def tearDown(self):
        super().tearDown()

    def test_collect_cpu_and_memory(self, mock_vm_moref_id, mock_vm_resource_id):

        mock_vm_moref_id.return_value = "moref"
        mock_vm_resource_id.return_value = "resource"
        self.mock_db.return_value.get_vnfd.return_value = self.vnfd

        with requests_mock.Mocker() as mock_requests:
            mock_vdc_response(mock_requests,
                              url_pattern='/suite-api/api/resources/stats.*',
                              response_file='vrops_multi.json')
            metrics = self.collector.collect(self.vnfr)
            self.assertEqual(len(metrics), 2, "Number of metrics returned")
            self.assertEqual(metrics[0].name, "cpu_utilization", "First metric name")
            self.assertEqual(metrics[1].name, "average_memory_utilization", "Second metric name")
            self.assertEqual(metrics[0].value, 100.0, "CPU metric value")
            self.assertEqual(metrics[1].value, 20.515941619873047, "Memory metric value")

    def test_collect_one_metric_only(self, mock_vm_moref_id, mock_vm_resource_id):

        mock_vm_moref_id.return_value = "moref"
        mock_vm_resource_id.return_value = "resource"

        self.vnfd['vdu'][0]['monitoring-param'] = [
            {'id': 'cirros_vnfd-VM_cpu_util', 'nfvi-metric': 'cpu_utilization'},
            ]
        self.mock_db.return_value.get_vnfd.return_value = self.vnfd

        with requests_mock.Mocker() as mock_requests:
            mock_vdc_response(mock_requests,
                              url_pattern='/suite-api/api/resources/stats.*',
                              response_file='vrops_multi.json')
            metrics = self.collector.collect(self.vnfr)
            self.assertEqual(len(metrics), 1, "Number of metrics returned")
            self.assertEqual(metrics[0].name, "cpu_utilization", "First metric name")
            self.assertEqual(metrics[0].value, 100.0, "CPU metric value")

    def test_collect_adjusted_metric(self, mock_vm_moref_id, mock_vm_resource_id):

        mock_vm_moref_id.return_value = "moref"
        mock_vm_resource_id.return_value = "resource"

        self.vnfd['vdu'][0]['monitoring-param'] = [
            {'id': 'cirros_vnfd-VM_cpu_util', 'nfvi-metric': 'disk_read_bytes'},
            ]
        self.mock_db.return_value.get_vnfd.return_value = self.vnfd

        with requests_mock.Mocker() as mock_requests:
            mock_vdc_response(mock_requests,
                              url_pattern='/suite-api/api/resources/stats.*',
                              response_file='vrops_multi.json')
            metrics = self.collector.collect(self.vnfr)
            self.assertEqual(len(metrics), 1, "Number of metrics returned")
            self.assertEqual(metrics[0].name, "disk_read_bytes", "First metric name")
            self.assertEqual(metrics[0].value, 10240.0, "Disk read bytes (not KB/s)")

    def test_collect_not_provided_metric(self, mock_vm_moref_id, mock_vm_resource_id):

        mock_vm_moref_id.return_value = "moref"
        mock_vm_resource_id.return_value = "resource"

        self.vnfd['vdu'][0]['monitoring-param'] = [
            {'id': 'cirros_vnfd-VM_packets_sent', 'nfvi-metric': 'packets_sent'},
            ]
        self.mock_db.return_value.get_vnfd.return_value = self.vnfd

        with requests_mock.Mocker() as mock_requests:
            mock_vdc_response(mock_requests,
                              url_pattern='/suite-api/api/resources/stats.*',
                              response_file='OK.json')
            metrics = self.collector.collect(self.vnfr)
            self.assertEqual(len(metrics), 0, "Number of metrics returned")

    def test_collect_unkown_metric(self, mock_vm_moref_id, mock_vm_resource_id):

        mock_vm_moref_id.return_value = "moref"
        mock_vm_resource_id.return_value = "resource"

        self.vnfd['vdu'][0]['monitoring-param'] = [
            {'id': 'cirros_vnfd-Unknown_Metric', 'nfvi-metric': 'unknown'},
            ]
        self.mock_db.return_value.get_vnfd.return_value = self.vnfd

        with requests_mock.Mocker() as mock_requests:
            mock_vdc_response(mock_requests,
                              url_pattern='/suite-api/api/resources/stats.*',
                              response_file='vrops_multi.json')
            metrics = self.collector.collect(self.vnfr)
            self.assertEqual(len(metrics), 0, "Number of metrics returned")

    def test_collect_vrops_error(self, mock_vm_moref_id, mock_vm_resource_id):

        mock_vm_moref_id.return_value = "moref"
        mock_vm_resource_id.return_value = "resource"
        self.mock_db.return_value.get_vnfd.return_value = self.vnfd

        with requests_mock.Mocker():
            metrics = self.collector.collect(self.vnfr)
            self.assertEqual(len(metrics), 0, "Number of metrics returned")
