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
import datetime
from unittest import TestCase, mock

from osm_mon.collector.vnf_collectors.openstack import GnocchiBackend
from osm_mon.core.config import Config


class CollectorTest(TestCase):
    def setUp(self):
        super().setUp()
        self.config = Config()

    def tearDown(self):
        super().tearDown()

    @mock.patch.object(GnocchiBackend, '_build_neutron_client')
    @mock.patch.object(GnocchiBackend, '_build_gnocchi_client')
    def test_collect_gnocchi_instance(self, build_gnocchi_client, build_neutron_client):
        mock_gnocchi_client = mock.Mock()
        mock_gnocchi_client.metric.get_measures.return_value = [(datetime.datetime(2019, 4, 12, 15, 43,
                                                                                   tzinfo=datetime.timezone(
                                                                                       datetime.timedelta(0),
                                                                                       '+00:00')), 60.0, 0.0345442539),
                                                                (datetime.datetime(2019, 4, 12, 15, 44,
                                                                                   tzinfo=datetime.timezone(
                                                                                       datetime.timedelta(0),
                                                                                       '+00:00')), 60.0, 0.0333070363)]
        build_gnocchi_client.return_value = mock_gnocchi_client

        backend = GnocchiBackend({'_id': 'test_uuid'})
        value = backend._collect_instance_metric('cpu_utilization', 'test_resource_id')
        self.assertEqual(value, 0.0333070363)
        mock_gnocchi_client.metric.get_measures.assert_called_once_with('cpu_utilization',
                                                                        limit=1,
                                                                        resource_id='test_resource_id')

    @mock.patch.object(GnocchiBackend, '_build_neutron_client')
    @mock.patch.object(GnocchiBackend, '_build_gnocchi_client')
    def test_collect_interface_one_metric(self, build_gnocchi_client, build_neutron_client):
        mock_gnocchi_client = mock.Mock()
        mock_gnocchi_client.resource.search.return_value = [{'id': 'test_id'}]
        mock_gnocchi_client.metric.get_measures.return_value = [(datetime.datetime(2019, 4, 12, 15, 43,
                                                                                   tzinfo=datetime.timezone(
                                                                                       datetime.timedelta(0),
                                                                                       '+00:00')), 60.0, 0.0345442539),
                                                                (datetime.datetime(2019, 4, 12, 15, 44,
                                                                                   tzinfo=datetime.timezone(
                                                                                       datetime.timedelta(0),
                                                                                       '+00:00')), 60.0, 0.0333070363)]
        mock_neutron_client = mock.Mock()
        mock_neutron_client.list_ports.return_value = {'ports': [
            {'binding:vnic_type': 'normal', 'created_at': '2019-04-15T17:11:39Z',
             'tenant_id': '88b78c76e01f4b228e68a06f8ebec6da',
             'binding:vif_details': {'port_filter': True, 'ovs_hybrid_plug': True, 'datapath_type': 'system'},
             'revision_number': 6, 'updated_at': '2019-04-15T17:11:48Z', 'binding:profile': {},
             'mac_address': 'fa:16:3e:1c:e3:00', 'status': 'ACTIVE', 'project_id': '88b78c76e01f4b228e68a06f8ebec6da',
             'network_id': '7f34edad-9064-4de8-b535-b14f9b715ed9', 'port_security_enabled': True, 'tags': [],
             'description': '', 'security_groups': ['3d60c37e-6229-487b-858d-3aff6d98d66f'], 'admin_state_up': True,
             'binding:vif_type': 'ovs', 'allowed_address_pairs': [], 'name': 'eth0',
             'id': '1c6f9a06-6b88-45f3-8d32-dc1216436f0a', 'binding:host_id': 's111412',
             'fixed_ips': [{'ip_address': '10.0.0.51', 'subnet_id': '4c3fa16c-3e22-43f4-9798-7b10593aff93'}],
             'device_owner': 'compute:nova', 'device_id': '5cf5bbc4-e4f8-4e22-8bbf-6970218e774d',
             'extra_dhcp_opts': []}]}

        build_gnocchi_client.return_value = mock_gnocchi_client
        build_neutron_client.return_value = mock_neutron_client

        backend = GnocchiBackend({'_id': 'test_uuid'})
        value = backend._collect_interface_one_metric('packets_received', 'test_resource_id', 'eth0')
        self.assertEqual(value, 0.0333070363)
        mock_gnocchi_client.metric.get_measures.assert_called_once_with('packets_received', resource_id='test_id',
                                                                        limit=1)
        mock_neutron_client.list_ports.assert_called_once_with(device_id='test_resource_id', name='eth0')

    @mock.patch.object(GnocchiBackend, '_build_neutron_client')
    @mock.patch.object(GnocchiBackend, '_build_gnocchi_client')
    def test_collect_interface_all_metric(self, build_gnocchi_client, build_neutron_client):
        mock_gnocchi_client = mock.Mock()
        mock_gnocchi_client.resource.search.return_value = [{'id': 'test_id_1'}, {'id': 'test_id_2'}]
        mock_gnocchi_client.metric.get_measures.return_value = [(datetime.datetime(2019, 4, 12, 15, 43,
                                                                                   tzinfo=datetime.timezone(
                                                                                       datetime.timedelta(0),
                                                                                       '+00:00')), 60.0, 0.0345442539),
                                                                (datetime.datetime(2019, 4, 12, 15, 44,
                                                                                   tzinfo=datetime.timezone(
                                                                                       datetime.timedelta(0),
                                                                                       '+00:00')), 60.0, 0.0333070363)]

        build_gnocchi_client.return_value = mock_gnocchi_client

        backend = GnocchiBackend({'_id': 'test_uuid'})
        value = backend._collect_interface_all_metric('packets_received', 'test_resource_id')
        self.assertEqual(value, 0.0666140726)
        mock_gnocchi_client.metric.get_measures.assert_any_call('packets_received', resource_id='test_id_1',
                                                                limit=1)
        mock_gnocchi_client.metric.get_measures.assert_any_call('packets_received', resource_id='test_id_2',
                                                                limit=1)
