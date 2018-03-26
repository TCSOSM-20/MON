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

from osm_mon.core.message_bus.producer import KafkaProducer as prod
from osm_mon.plugins.OpenStack import response
from osm_mon.plugins.OpenStack.Aodh import alarming
from osm_mon.plugins.OpenStack.common import Common

log = logging.getLogger(__name__)


class AlarmIntegrationTest(unittest.TestCase):
    def setUp(self):
        # Set up common and alarming class instances
        self.alarms = alarming.Alarming()
        self.openstack_auth = Common()

        try:
            self.producer = KafkaProducer(bootstrap_servers='localhost:9092')
            self.req_consumer = KafkaConsumer(bootstrap_servers='localhost:9092',
                                              group_id='osm_mon',
                                              consumer_timeout_ms=2000)
            self.req_consumer.subscribe(['alarm_request'])
        except KafkaError:
            self.skipTest('Kafka server not present.')

    @mock.patch.object(prod, "update_alarm_response")
    @mock.patch.object(alarming.Alarming, "update_alarm")
    @mock.patch.object(response.OpenStack_Response, "generate_response")
    def test_update_alarm_req(self, resp, update_alarm, update_resp):
        """Test Aodh update alarm request message from KafkaProducer."""
        # Set-up message, producer and consumer for tests
        payload = {"vim_type": "OpenSTACK",
                   "alarm_update_request":
                       {"correlation_id": 123,
                        "alarm_uuid": "alarm_id",
                        "metric_uuid": "metric_id"}}

        self.producer.send('alarm_request', key="update_alarm_request",
                           value=json.dumps(payload))

        for message in self.req_consumer:
            # Check the vim desired by the message
            vim_type = json.loads(message.value)["vim_type"].lower()
            if vim_type == "openstack":
                # Mock a valid alarm update
                update_alarm.return_value = "alarm_id", True
                self.alarms.alarming(message, self.openstack_auth, None)

                # A response message is generated and sent via MON's producer
                resp.assert_called_with(
                    'update_alarm_response', alarm_id="alarm_id", cor_id=123,
                    status=True)
                update_resp.assert_called_with(
                    'update_alarm_response', resp.return_value, 'alarm_response')

                return
        self.fail("No message received in consumer")

    @mock.patch.object(prod, "create_alarm_response")
    @mock.patch.object(alarming.Alarming, "configure_alarm")
    @mock.patch.object(response.OpenStack_Response, "generate_response")
    def test_create_alarm_req(self, resp, config_alarm, create_resp):
        """Test Aodh create alarm request message from KafkaProducer."""
        # Set-up message, producer and consumer for tests
        payload = {"vim_type": "OpenSTACK",
                   "alarm_create_request":
                       {"correlation_id": 123,
                        "alarm_name": "my_alarm",
                        "metric_name": "my_metric",
                        "resource_uuid": "my_resource",
                        "severity": "WARNING"}}

        self.producer.send('alarm_request', key="create_alarm_request",
                           value=json.dumps(payload))

        for message in self.req_consumer:
            # Check the vim desired by the message
            vim_type = json.loads(message.value)["vim_type"].lower()
            if vim_type == "openstack":
                # Mock a valid alarm creation
                config_alarm.return_value = "alarm_id", True
                self.alarms.alarming(message, self.openstack_auth, None)

                # A response message is generated and sent via MON's produce
                resp.assert_called_with(
                    'create_alarm_response', status=True, alarm_id="alarm_id",
                    cor_id=123)
                create_resp.assert_called_with(
                    'create_alarm_response', resp.return_value, 'alarm_response')

                return
        self.fail("No message received in consumer")

    @mock.patch.object(prod, "list_alarm_response")
    @mock.patch.object(alarming.Alarming, "list_alarms")
    @mock.patch.object(response.OpenStack_Response, "generate_response")
    def test_list_alarm_req(self, resp, list_alarm, list_resp):
        """Test Aodh list alarm request message from KafkaProducer."""
        # Set-up message, producer and consumer for tests
        payload = {"vim_type": "OpenSTACK",
                   "alarm_list_request":
                       {"correlation_id": 123,
                        "resource_uuid": "resource_id", }}

        self.producer.send('alarm_request', key="list_alarm_request",
                           value=json.dumps(payload))

        for message in self.req_consumer:
            # Check the vim desired by the message
            vim_type = json.loads(message.value)["vim_type"].lower()
            if vim_type == "openstack":
                # Mock an empty list generated by the request
                list_alarm.return_value = []
                self.alarms.alarming(message, self.openstack_auth, None)

                # Resoonse message is generated
                resp.assert_called_with(
                    'list_alarm_response', alarm_list=[],
                    cor_id=123)
                # Producer attempts to send the response message back to the SO
                list_resp.assert_called_with(
                    'list_alarm_response', resp.return_value, 'alarm_response')

                return
        self.fail("No message received in consumer")

    @mock.patch.object(alarming.Alarming, "delete_alarm")
    @mock.patch.object(prod, "delete_alarm_response")
    @mock.patch.object(response.OpenStack_Response, "generate_response")
    def test_delete_alarm_req(self, resp, del_resp, del_alarm):
        """Test Aodh delete alarm request message from KafkaProducer."""
        # Set-up message, producer and consumer for tests
        payload = {"vim_type": "OpenSTACK",
                   "alarm_delete_request":
                       {"correlation_id": 123,
                        "alarm_uuid": "alarm_id", }}

        self.producer.send('alarm_request', key="delete_alarm_request",
                           value=json.dumps(payload))

        for message in self.req_consumer:
            # Check the vim desired by the message
            vim_type = json.loads(message.value)["vim_type"].lower()
            if vim_type == "openstack":
                self.alarms.alarming(message, self.openstack_auth, None)

                # Response message is generated and sent by MON's producer
                resp.assert_called_with(
                    'delete_alarm_response', alarm_id="alarm_id",
                    status=del_alarm.return_value, cor_id=123)
                del_resp.assert_called_with(
                    'delete_alarm_response', resp.return_value, 'alarm_response')

                return
        self.fail("No message received in consumer")

    @mock.patch.object(alarming.Alarming, "update_alarm_state")
    def test_ack_alarm_req(self, ack_alarm):
        """Test Aodh acknowledge alarm request message from KafkaProducer."""
        # Set-up message, producer and consumer for tests
        payload = {"vim_type": "OpenSTACK",
                   "ack_details":
                       {"alarm_uuid": "alarm_id", }}

        self.producer.send('alarm_request', key="acknowledge_alarm",
                           value=json.dumps(payload))

        for message in self.req_consumer:
            # Check the vim desired by the message
            vim_type = json.loads(message.value)["vim_type"].lower()
            if vim_type == "openstack":
                self.alarms.alarming(message, self.openstack_auth, None)
                # No response message is sent for and ack request
                # Alarm state is updated from alarm -> ok
                ack_alarm.assert_called_with(None, None, "alarm_id")
                return
        self.fail("No message received in consumer")
