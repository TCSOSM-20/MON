# Copyright 2017 Intel Research and Development Ireland Limited
# *************************************************************

# This file is part of OSM Monitoring module
# All Rights Reserved to Intel Corporation

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
# contact: helena.mcgough@intel.com or adrian.hoban@intel.com

# __author__ = "Helena McGough"
"""Test an end to end Openstack alarm requests."""

import json
import logging
import unittest

import mock
from kafka import KafkaConsumer
from kafka import KafkaProducer
from kafka.errors import KafkaError

from osm_mon.core.auth import AuthManager
from osm_mon.core.database import DatabaseManager, VimCredentials
from osm_mon.plugins.OpenStack import response
from osm_mon.plugins.OpenStack.Aodh import alarm_handler
from osm_mon.plugins.OpenStack.common import Common

log = logging.getLogger(__name__)

mock_creds = VimCredentials()
mock_creds.config = '{}'


@mock.patch.object(DatabaseManager, "save_alarm", mock.Mock())
@mock.patch.object(Common, "get_auth_token", mock.Mock())
@mock.patch.object(Common, "get_endpoint", mock.Mock())
class AlarmIntegrationTest(unittest.TestCase):
    def setUp(self):
        try:
            self.producer = KafkaProducer(bootstrap_servers='localhost:9092',
                                          key_serializer=str.encode,
                                          value_serializer=str.encode
                                          )
            self.req_consumer = KafkaConsumer(bootstrap_servers='localhost:9092',
                                              key_deserializer=bytes.decode,
                                              value_deserializer=bytes.decode,
                                              auto_offset_reset='earliest',
                                              consumer_timeout_ms=60000)
            self.req_consumer.subscribe(['alarm_request'])
        except KafkaError:
            self.skipTest('Kafka server not present.')
        # Set up common and alarming class instances
        self.alarms = alarm_handler.OpenstackAlarmHandler()
        self.openstack_auth = Common()

    def tearDown(self):
        self.producer.close()
        self.req_consumer.close()

    @mock.patch.object(Common, "perform_request")
    @mock.patch.object(AuthManager, 'get_credentials')
    @mock.patch.object(alarm_handler.OpenstackAlarmHandler, "update_alarm")
    @mock.patch.object(response.OpenStackResponseBuilder, "generate_response")
    def test_update_alarm_req(self, resp, update_alarm, get_creds, perf_req):
        """Test Aodh update alarm request message from KafkaProducer."""
        # Set-up message, producer and consumer for tests
        payload = {"alarm_update_request": {"correlation_id": 123,
                                            "alarm_uuid": "alarm_id",
                                            "metric_uuid": "metric_id"}}

        get_creds.return_value = mock_creds
        perf_req.return_value = type('obj', (object,), {'text': json.dumps({"metrics": {"cpu_util": "1"}})})
        resp.return_value = ''

        self.producer.send('alarm_request', key="update_alarm_request",
                           value=json.dumps(payload))

        for message in self.req_consumer:
            if message.key == "update_alarm_request":
                # Mock a valid alarm update
                update_alarm.return_value = "alarm_id"
                self.alarms.handle_message(message, 'test_id')

                # A response message is generated and sent via MON's producer
                resp.assert_called_with(
                    'update_alarm_response', alarm_id="alarm_id", cor_id=123,
                    status=True)

                return
        self.fail("No message received in consumer")

    @mock.patch.object(Common, "perform_request")
    @mock.patch.object(AuthManager, 'get_credentials')
    @mock.patch.object(alarm_handler.OpenstackAlarmHandler, "configure_alarm")
    @mock.patch.object(response.OpenStackResponseBuilder, "generate_response")
    def test_create_alarm_req(self, resp, config_alarm, get_creds, perf_req):
        """Test Aodh create alarm request message from KafkaProducer."""
        # Set-up message, producer and consumer for tests
        payload = {"alarm_create_request": {"correlation_id": 123,
                                            "alarm_name": "my_alarm",
                                            "metric_name": "cpu_utilization",
                                            "resource_uuid": "my_resource",
                                            "severity": "WARNING",
                                            "threshold_value": 60,
                                            "operation": "GT",
                                            "vdu_name": "vdu",
                                            "vnf_member_index": "1",
                                            "ns_id": "1"}}

        get_creds.return_value = mock_creds
        perf_req.return_value = type('obj', (object,), {'text': json.dumps({"metrics": {"cpu_util": "1"}})})
        resp.return_value = ''
        self.producer.send('alarm_request', key="create_alarm_request",
                           value=json.dumps(payload))

        for message in self.req_consumer:
            if message.key == "create_alarm_request":
                # Mock a valid alarm creation
                config_alarm.return_value = "alarm_id"
                self.alarms.handle_message(message, 'test_id')

                # A response message is generated and sent via MON's produce
                resp.assert_called_with(
                    'create_alarm_response', status=True, alarm_id="alarm_id",
                    cor_id=123)

                return
        self.fail("No message received in consumer")

    @mock.patch.object(Common, "perform_request")
    @mock.patch.object(AuthManager, 'get_credentials')
    @mock.patch.object(alarm_handler.OpenstackAlarmHandler, "list_alarms")
    @mock.patch.object(response.OpenStackResponseBuilder, "generate_response")
    def test_list_alarm_req(self, resp, list_alarm, get_creds, perf_req):
        """Test Aodh list alarm request message from KafkaProducer."""
        # Set-up message, producer and consumer for tests
        payload = {"alarm_list_request": {"correlation_id": 123,
                                          "resource_uuid": "resource_id", }}

        self.producer.send('alarm_request', key="list_alarm_request",
                           value=json.dumps(payload))

        get_creds.return_value = mock_creds
        perf_req.return_value = type('obj', (object,), {'text': json.dumps([])})
        resp.return_value = ''

        for message in self.req_consumer:
            if message.key == "list_alarm_request":
                # Mock an empty list generated by the request
                list_alarm.return_value = []
                self.alarms.handle_message(message, 'test_id')

                # Response message is generated
                resp.assert_called_with(
                    'list_alarm_response', alarm_list=[],
                    cor_id=123)

                return
        self.fail("No message received in consumer")

    @mock.patch.object(Common, "perform_request")
    @mock.patch.object(AuthManager, 'get_credentials')
    @mock.patch.object(alarm_handler.OpenstackAlarmHandler, "delete_alarm")
    @mock.patch.object(response.OpenStackResponseBuilder, "generate_response")
    def test_delete_alarm_req(self, resp, del_alarm, get_creds, perf_req):
        """Test Aodh delete alarm request message from KafkaProducer."""
        # Set-up message, producer and consumer for tests
        payload = {"alarm_delete_request": {"correlation_id": 123,
                                            "alarm_uuid": "alarm_id", }}

        self.producer.send('alarm_request', key="delete_alarm_request",
                           value=json.dumps(payload))

        get_creds.return_value = mock_creds
        perf_req.return_value = type('obj', (object,), {'text': json.dumps([])})
        resp.return_value = ''

        for message in self.req_consumer:
            if message.key == "delete_alarm_request":
                self.alarms.handle_message(message, 'test_id')

                # Response message is generated and sent by MON's producer
                resp.assert_called_with(
                    'delete_alarm_response', alarm_id="alarm_id",
                    status=True, cor_id=123)

                return
        self.fail("No message received in consumer")

    @mock.patch.object(AuthManager, 'get_credentials')
    @mock.patch.object(alarm_handler.OpenstackAlarmHandler, "update_alarm_state")
    def test_ack_alarm_req(self, ack_alarm, get_creds):
        """Test Aodh acknowledge alarm request message from KafkaProducer."""
        # Set-up message, producer and consumer for tests
        payload = {"ack_details": {"alarm_uuid": "alarm_id", }}

        self.producer.send('alarm_request', key="acknowledge_alarm",
                           value=json.dumps(payload))

        get_creds.return_value = mock_creds
        ack_alarm.return_value = True

        for message in self.req_consumer:
            if message.key == "acknowledge_alarm":
                self.alarms.handle_message(message, 'test_id')
                ack_alarm.assert_called_with(mock.ANY, mock.ANY, 'alarm_id', True)
                return

        self.fail("No message received in consumer")
