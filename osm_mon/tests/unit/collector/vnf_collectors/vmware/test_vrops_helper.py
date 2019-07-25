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

from osm_mon.collector.vnf_collectors.vrops.vrops_helper import vROPS_Helper
from osm_mon.tests.unit.collector.vnf_collectors.vmware.mock_http import mock_http_response
from unittest import TestCase

import json
import os
import requests_mock


class vROPS_Helper_Resource_List_Test(TestCase):

    def setUp(self):
        super().setUp()
        self.vrops = vROPS_Helper()

    def tearDown(self):
        super().tearDown()

    def test_get_vm_resource_list_from_vrops(self):
        with requests_mock.Mocker() as mock_requests:
            mock_http_response(mock_requests,
                               url_pattern='/suite-api/api/resources\\?resourceKind=VirtualMachine',
                               response_file='vrops_resources.json')
            resource_list = self.vrops.get_vm_resource_list_from_vrops()
            self.assertEqual(len(resource_list), 3, "List of resources from canned vrops_resources.json")

    def test_get_vm_resource_list_from_vrops_http_404(self):
        with requests_mock.Mocker() as mock_requests:
            mock_http_response(mock_requests,
                               url_pattern='/suite-api/api/resources\\?resourceKind=VirtualMachine',
                               response_file='404.txt', status_code=404)
            resource_list = self.vrops.get_vm_resource_list_from_vrops()
            self.assertEqual(len(resource_list), 0, "Should return an empty list")

    def test_get_vm_resource_list_from_vrops_bad_json(self):
        with requests_mock.Mocker() as mock_requests:
            mock_http_response(mock_requests,
                               url_pattern='/suite-api/api/resources\\?resourceKind=VirtualMachine',
                               response_file='malformed.json')
            resource_list = self.vrops.get_vm_resource_list_from_vrops()
            self.assertEqual(len(resource_list), 0, "Should return an empty list")


class vROPS_Helper_Get_Metrics_Test(TestCase):

    def setUp(self):
        super().setUp()
        self.vrops = vROPS_Helper()
        with open(os.path.join(os.path.dirname(__file__), 'osm_mocks', 'VNFR.json'), 'r') as f:
            self.vnfr = json.load(f)

    def tearDown(self):
        super().tearDown()

    def test_collect_one_metric_only(self):
        vdu_mappings = {'VMWARE-OID-VM-1':
                        {'name': 'vmware-scaling-1-ubuntu_vnfd-VM-2',
                         'vrops_id': 'VROPS-UUID-1'}}
        monitoring_params = [
            {"id": "ubuntu_vnfd-VM_cpu_util", "nfvi-metric": "cpu_utilization"},
            ]

        with requests_mock.Mocker() as mock_requests:
            mock_http_response(mock_requests,
                               url_pattern='/suite-api/api/resources/stats.*',
                               response_file='vrops_multi.json')

            metrics = self.vrops.get_metrics(vdu_mappings, monitoring_params, self.vnfr)
        self.assertEqual(len(metrics), 1, "Number of metrics returned")
        self.assertEqual(metrics[0].name, "cpu_utilization", "First metric name")
        self.assertEqual(metrics[0].value, 100.0, "CPU metric value")

    def test_collect_cpu_and_memory(self):
        vdu_mappings = {'VMWARE-OID-VM-1':
                        {'name': 'vmware-scaling-1-ubuntu_vnfd-VM-2',
                         'vrops_id': 'VROPS-UUID-1'}}
        monitoring_params = [
            {"id": "ubuntu_vnfd-VM_cpu_util", "nfvi-metric": "cpu_utilization"},
            {"id": "ubuntu_vnfd-VM_average_memory_utilization", "nfvi-metric": "average_memory_utilization"}
            ]

        with requests_mock.Mocker() as mock_requests:
            mock_http_response(mock_requests,
                               url_pattern='/suite-api/api/resources/stats.*',
                               response_file='vrops_multi.json')

            metrics = self.vrops.get_metrics(vdu_mappings, monitoring_params, self.vnfr)

        self.assertEqual(len(metrics), 2, "Number of metrics returned")
        self.assertEqual(metrics[0].name, "cpu_utilization", "First metric name")
        self.assertEqual(metrics[0].value, 100.0, "CPU metric value")
        self.assertEqual(metrics[1].name, "average_memory_utilization", "Second metric name")
        self.assertEqual(metrics[1].value, 20.515941619873047, "Memory metric value")

    def test_collect_adjusted_metric(self):
        vdu_mappings = {'VMWARE-OID-VM-1':
                        {'name': 'vmware-scaling-1-ubuntu_vnfd-VM-2',
                         'vrops_id': 'VROPS-UUID-1'}}
        monitoring_params = [
            {'id': 'ubuntu_vnfd-VM_cpu_util', 'nfvi-metric': 'disk_read_bytes'}
            ]

        with requests_mock.Mocker() as mock_requests:
            mock_http_response(mock_requests,
                               url_pattern='/suite-api/api/resources/stats.*',
                               response_file='vrops_multi.json')

            metrics = self.vrops.get_metrics(vdu_mappings, monitoring_params, self.vnfr)

        self.assertEqual(len(metrics), 1, "Number of metrics returned")
        self.assertEqual(metrics[0].name, "disk_read_bytes", "First metric name")
        self.assertEqual(metrics[0].value, 10240.0, "Disk read bytes (not KB/s)")

    def test_collect_not_provided_metric(self):
        vdu_mappings = {'VMWARE-OID-VM-1':
                        {'name': 'vmware-scaling-1-ubuntu_vnfd-VM-2',
                         'vrops_id': 'VROPS-UUID-1'}}
        monitoring_params = [
            {'id': 'cirros_vnfd-VM_packets_sent', 'nfvi-metric': 'packets_in_dropped'},
            ]

        with requests_mock.Mocker() as mock_requests:
            mock_http_response(mock_requests,
                               url_pattern='/suite-api/api/resources/stats.*',
                               response_file='vrops_multi.json')

            metrics = self.vrops.get_metrics(vdu_mappings, monitoring_params, self.vnfr)

        self.assertEqual(len(metrics), 0, "Number of metrics returned")

    def test_collect_unkown_metric(self):
        vdu_mappings = {'VMWARE-OID-VM-1':
                        {'name': 'vmware-scaling-1-ubuntu_vnfd-VM-2',
                         'vrops_id': 'VROPS-UUID-1'}}
        monitoring_params = [
            {'id': 'cirros_vnfd-Unknown_Metric', 'nfvi-metric': 'unknown'},
            ]

        with requests_mock.Mocker() as mock_requests:
            mock_http_response(mock_requests,
                               url_pattern='/suite-api/api/resources/stats.*',
                               response_file='vrops_multi.json')

            metrics = self.vrops.get_metrics(vdu_mappings, monitoring_params, self.vnfr)

        self.assertEqual(len(metrics), 0, "Number of metrics returned")

    def test_collect_vrops_no_data(self):
        vdu_mappings = {'VMWARE-OID-VM-1':
                        {'name': 'vmware-scaling-1-ubuntu_vnfd-VM-2',
                         'vrops_id': 'VROPS-UUID-1'}}
        monitoring_params = [
            {"id": "ubuntu_vnfd-VM_cpu_util", "nfvi-metric": "cpu_utilization"},
            ]

        with requests_mock.Mocker() as mock_requests:
            mock_http_response(mock_requests,
                               url_pattern='/suite-api/api/resources/stats.*',
                               response_file='OK.json')

            metrics = self.vrops.get_metrics(vdu_mappings, monitoring_params, self.vnfr)

        self.assertEqual(len(metrics), 0, "Number of metrics returned")

    def test_collect_vrops_unknown_vim_id(self):
        vdu_mappings = {'VMWARE-OID-VM-1':
                        {'name': 'vmware-scaling-1-ubuntu_vnfd-VM-2'}}
        monitoring_params = [
            {"id": "ubuntu_vnfd-VM_cpu_util", "nfvi-metric": "cpu_utilization"},
            ]

        with requests_mock.Mocker() as mock_requests:
            mock_http_response(mock_requests,
                               url_pattern='/suite-api/api/resources/stats.*',
                               response_file='vrops_multi.json')

            metrics = self.vrops.get_metrics(vdu_mappings, monitoring_params, self.vnfr)

        self.assertEqual(len(metrics), 0, "Number of metrics returned")

    def test_collect_vrops_http_error(self):
        vdu_mappings = {'VMWARE-OID-VM-1':
                        {'name': 'vmware-scaling-1-ubuntu_vnfd-VM-2',
                         'vrops_id': 'VROPS-UUID-1'}}
        monitoring_params = [
            {"id": "ubuntu_vnfd-VM_cpu_util", "nfvi-metric": "cpu_utilization"},
            ]

        with requests_mock.Mocker() as mock_requests:
            mock_http_response(mock_requests,
                               url_pattern='/suite-api/api/resources/stats.*',
                               response_file='404.txt', status_code=404)

            metrics = self.vrops.get_metrics(vdu_mappings, monitoring_params, self.vnfr)

        self.assertEqual(len(metrics), 0, "Number of metrics returned")

    def test_collect_vrops_json_parse_error(self):
        vdu_mappings = {'VMWARE-OID-VM-1':
                        {'name': 'vmware-scaling-1-ubuntu_vnfd-VM-2',
                         'vrops_id': 'VROPS-UUID-1'}}
        monitoring_params = [
            {"id": "ubuntu_vnfd-VM_cpu_util", "nfvi-metric": "cpu_utilization"},
            ]

        with requests_mock.Mocker() as mock_requests:
            mock_http_response(mock_requests,
                               url_pattern='/suite-api/api/resources/stats.*',
                               response_file='404.txt')

            metrics = self.vrops.get_metrics(vdu_mappings, monitoring_params, self.vnfr)

        self.assertEqual(len(metrics), 0, "Number of metrics returned")

    def test_collect_multi_vdu(self):
        vdu_mappings = {'VMWARE-UUID-VM-1':
                        {'name': 'vmware-scaling-1-ubuntu_vnfd-VM-1', 'vrops_id': 'VROPS-UUID-1'},
                        'VMWARE-UUID-VM-2':
                        {'name': 'vmware-scaling-1-ubuntu_vnfd-VM-2', 'vrops_id': 'VROPS-UUID-2'},
                        'VMWARE-UUID-VM-3':
                        {'name': 'vmware-scaling-1-ubuntu_vnfd-VM-2', 'vrops_id': 'VROPS-UUID-3'}
                        }
        monitoring_params = [
            {'id': 'ubuntu_vnfd-VM_cpu_util', 'nfvi-metric': 'cpu_utilization'},
            {'id': 'ubuntu_vnfd-VM_average_memory_utilization', 'nfvi-metric': 'average_memory_utilization'},
            {'id': 'ubuntu_vnfd-VM_disk_read_ops', 'nfvi-metric': 'disk_read_ops'},
            {'id': 'ubuntu_vnfd-VM_disk_write_ops', 'nfvi-metric': 'disk_write_ops'},
            {'id': 'ubuntu_vnfd-VM_disk_read_bytes', 'nfvi-metric': 'disk_read_bytes'},
            {'id': 'ubuntu_vnfd-VM_disk_write_bytes', 'nfvi-metric': 'disk_write_bytes'},
            {'id': 'ubuntu_vnfd-VM_packets_out_dropped', 'nfvi-metric': 'packets_out_dropped'},
            {'id': 'ubuntu_vnfd-VM_packets_received', 'nfvi-metric': 'packets_received'},
            {'id': 'ubuntu_vnfd-VM_packets_sent', 'nfvi-metric': 'packets_sent'}
            ]

        with requests_mock.Mocker() as mock_requests:
            mock_http_response(mock_requests,
                               url_pattern='/suite-api/api/resources/stats.*',
                               response_file='vrops_multi.json')
            metrics = self.vrops.get_metrics(vdu_mappings, monitoring_params, self.vnfr)

        self.assertEqual(len(metrics), len(monitoring_params) * len(vdu_mappings), "Number of metrics returned")
