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
"""A common KafkaConsumer for all MON plugins."""

import json
import logging
from json import JSONDecodeError

import yaml

from osm_mon.core.auth import AuthManager
from osm_mon.core.common_db import CommonDbClient
from osm_mon.core.database import DatabaseManager
from osm_mon.core.message_bus.consumer import Consumer
from osm_mon.core.message_bus.producer import Producer
from osm_mon.core.response import ResponseBuilder

log = logging.getLogger(__name__)


class Server:

    def __init__(self):
        self.auth_manager = AuthManager()
        self.database_manager = DatabaseManager()
        self.database_manager.create_tables()
        self.common_db = CommonDbClient()

    def run(self):
        common_consumer = Consumer("mon-server")

        topics = ['alarm_request', 'vim_account']
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
                    values['vim_password'] = self.common_db.decrypt_vim_password(values['vim_password'],
                                                                                 values['schema_version'],
                                                                                 values['_id'])
                    self.auth_manager.store_auth_credentials(values)
                if message.key == "delete":
                    self.auth_manager.delete_auth_credentials(values)

            elif message.topic == "alarm_request":
                if message.key == "create_alarm_request":
                    alarm_details = values['alarm_create_request']
                    response_builder = ResponseBuilder()
                    try:
                        alarm = self.database_manager.save_alarm(
                            alarm_details['alarm_name'],
                            alarm_details['threshold_value'],
                            alarm_details['operation'].lower(),
                            alarm_details['severity'].lower(),
                            alarm_details['statistic'].lower(),
                            alarm_details['metric_name'],
                            alarm_details['vdu_name'],
                            alarm_details['vnf_member_index'],
                            alarm_details['ns_id']
                        )
                        response = response_builder.generate_response('create_alarm_response',
                                                                      cor_id=alarm_details['correlation_id'],
                                                                      status=True,
                                                                      alarm_id=alarm.uuid)
                    except Exception:
                        log.exception("Error creating alarm: ")
                        response = response_builder.generate_response('create_alarm_response',
                                                                      cor_id=alarm_details['correlation_id'],
                                                                      status=False,
                                                                      alarm_id=None)
                if message.key == "delete_alarm_request":
                    alarm_details = values['alarm_delete_request']
                    alarm_uuid = alarm_details['alarm_uuid']
                    response_builder = ResponseBuilder()
                    cor_id = alarm_details['correlation_id']
                    try:
                        self.database_manager.delete_alarm(alarm_uuid)
                        response = response_builder.generate_response('delete_alarm_response',
                                                                      cor_id=cor_id,
                                                                      status=True,
                                                                      alarm_id=alarm_uuid)
                    except Exception:
                        log.exception("Error deleting alarm: ")
                        response = response_builder.generate_response('delete_alarm_response',
                                                                      cor_id=cor_id,
                                                                      status=False,
                                                                      alarm_id=alarm_uuid)
            if response:
                self._publish_response(message.topic, message.key, response)

        except Exception:
            log.exception("Exception processing message: ")

    def _publish_response(self, topic: str, key: str, msg: dict):
        topic = topic.replace('request', 'response')
        key = key.replace('request', 'response')
        producer = Producer()
        producer.send(topic=topic, key=key, value=json.dumps(msg))
        producer.flush(timeout=5)
        producer.close()


if __name__ == '__main__':
    Server().run()
