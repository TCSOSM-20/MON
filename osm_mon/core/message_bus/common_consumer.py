# Copyright 2017 Intel Research and Development Ireland Limited
# *************************************************************
# This file is part of OSM Monitoring module
# All Rights Reserved to Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License"); you
# may not use this file except in compliance with the License. You may
# obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied. See the License for the specific language governing
# permissions and limitations under the License.
#
# For those usages not covered by the Apache License, Version 2.0 please
# contact: helena.mcgough@intel.com or adrian.hoban@intel.com
"""A common KafkaConsumer for all MON plugins."""

import json
import logging
import sys
from json import JSONDecodeError

import six
import yaml

from osm_mon.common.common_db_client import CommonDbClient
from osm_mon.core.auth import AuthManager
from osm_mon.core.database import DatabaseManager
from osm_mon.core.message_bus.consumer import Consumer
from osm_mon.core.message_bus.producer import Producer
from osm_mon.core.settings import Config
from osm_mon.plugins.CloudWatch.access_credentials import AccessCredentials
from osm_mon.plugins.CloudWatch.connection import Connection
from osm_mon.plugins.CloudWatch.plugin_alarm import plugin_alarms
from osm_mon.plugins.CloudWatch.plugin_metric import plugin_metrics
from osm_mon.plugins.OpenStack.Aodh import alarm_handler
from osm_mon.plugins.OpenStack.Gnocchi import metric_handler
from osm_mon.plugins.vRealiseOps import plugin_receiver

cfg = Config.instance()

logging.basicConfig(stream=sys.stdout,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=logging.getLevelName(cfg.OSMMON_LOG_LEVEL))
log = logging.getLogger(__name__)

kafka_logger = logging.getLogger('kafka')
kafka_logger.setLevel(logging.getLevelName(cfg.OSMMON_KAFKA_LOG_LEVEL))
kafka_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
kafka_handler = logging.StreamHandler(sys.stdout)
kafka_handler.setFormatter(kafka_formatter)
kafka_logger.addHandler(kafka_handler)


class CommonConsumer:

    def __init__(self):
        self.auth_manager = AuthManager()
        self.database_manager = DatabaseManager()
        self.database_manager.create_tables()

        # Create OpenStack alarming and metric instances
        self.openstack_metrics = metric_handler.OpenstackMetricHandler()
        self.openstack_alarms = alarm_handler.OpenstackAlarmHandler()

        # Create CloudWatch alarm and metric instances
        self.cloudwatch_alarms = plugin_alarms()
        self.cloudwatch_metrics = plugin_metrics()
        self.aws_connection = Connection()
        self.aws_access_credentials = AccessCredentials()

        # Create vROps plugin_receiver class instance
        self.vrops_rcvr = plugin_receiver.PluginReceiver()

        log.info("Connecting to MongoDB...")
        self.common_db = CommonDbClient()
        log.info("Connection successful.")

    def get_vim_type(self, vim_uuid):
        """Get the vim type that is required by the message."""
        credentials = self.database_manager.get_credentials(vim_uuid)
        return credentials.type

    def run(self):
        common_consumer = Consumer("mon-consumer")

        topics = ['metric_request', 'alarm_request', 'vim_account']
        common_consumer.subscribe(topics)

        log.info("Listening for messages...")
        for message in common_consumer:
            self.consume_message(message)

    def consume_message(self, message):
        log.info("Message arrived: %s", message)
        try:
            try:
                values = json.loads(message.value)
            except JSONDecodeError:
                values = yaml.safe_load(message.value)

            response = None

            if message.topic == "vim_account":
                if message.key == "create" or message.key == "edit":
                    self.auth_manager.store_auth_credentials(values)
                if message.key == "delete":
                    self.auth_manager.delete_auth_credentials(values)

            else:
                # Get ns_id from message
                # TODO: Standardize all message models to avoid the need of figuring out where are certain fields
                contains_list = False
                list_index = None
                for k, v in six.iteritems(values):
                    if isinstance(v, dict):
                        if 'ns_id' in v:
                            contains_list = True
                            list_index = k
                            break
                if not contains_list and 'ns_id' in values:
                    ns_id = values['ns_id']
                else:
                    ns_id = values[list_index]['ns_id']

                vnf_index = values[list_index]['vnf_member_index'] if contains_list else values['vnf_member_index']

                # Check the vim desired by the message
                vnfr = self.common_db.get_vnfr(ns_id, vnf_index)
                vim_uuid = vnfr['vim-account-id']

                if (contains_list and 'vdu_name' in values[list_index]) or 'vdu_name' in values:
                    vdu_name = values[list_index]['vdu_name'] if contains_list else values['vdu_name']
                    vdur = self.common_db.get_vdur(ns_id, vnf_index, vdu_name)
                    if contains_list:
                        values[list_index]['resource_uuid'] = vdur['vim-id']
                    else:
                        values['resource_uuid'] = vdur['vim-id']
                    message = message._replace(value=json.dumps(values))

                vim_type = self.get_vim_type(vim_uuid)

                if vim_type == "openstack":
                    log.info("This message is for the OpenStack plugin.")
                    if message.topic == "metric_request":
                        response = self.openstack_metrics.handle_request(message.key, values, vim_uuid)
                    if message.topic == "alarm_request":
                        response = self.openstack_alarms.handle_message(message.key, values, vim_uuid)

                elif vim_type == "aws":
                    log.info("This message is for the CloudWatch plugin.")
                    aws_conn = self.aws_connection.setEnvironment()
                    if message.topic == "metric_request":
                        response = self.cloudwatch_metrics.metric_calls(message.key, values, aws_conn)
                    if message.topic == "alarm_request":
                        response = self.cloudwatch_alarms.alarm_calls(message.key, values, aws_conn)

                elif vim_type == "vmware":
                    log.info("This metric_request message is for the vROPs plugin.")
                    if message.topic == "metric_request":
                        response = self.vrops_rcvr.handle_metric_requests(message.key, values, vim_uuid)
                    if message.topic == "alarm_request":
                        response = self.vrops_rcvr.handle_alarm_requests(message.key, values, vim_uuid)

                else:
                    log.debug("vim_type is misconfigured or unsupported; %s",
                              vim_type)
            if response:
                self._publish_response(message.topic, message.key, response)

        except Exception:
            log.exception("Exception processing message: ")

    def _publish_response(self, topic: str, key: str, msg: dict):
        topic = topic.replace('request', 'response')
        key = key.replace('request', 'response')
        producer = Producer()
        producer.send(topic=topic, key=key, value=json.dumps(msg))
        producer.flush()
        producer.close()


if __name__ == '__main__':
    CommonConsumer().run()
