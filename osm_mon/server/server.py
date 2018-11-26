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
import asyncio
import json
import logging
from json import JSONDecodeError

import yaml
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from osm_mon.core.auth import AuthManager
from osm_mon.core.common_db import CommonDbClient
from osm_mon.core.database import DatabaseManager
from osm_mon.core.response import ResponseBuilder
from osm_mon.core.settings import Config

log = logging.getLogger(__name__)


class Server:

    def __init__(self, loop=None):
        cfg = Config.instance()
        if not loop:
            loop = asyncio.get_event_loop()
        self.loop = loop
        self.auth_manager = AuthManager()
        self.database_manager = DatabaseManager()
        self.database_manager.create_tables()
        self.common_db = CommonDbClient()
        self.kafka_server = cfg.BROKER_URI

    def run(self):
        self.loop.run_until_complete(self.start())

    async def start(self):
        consumer = AIOKafkaConsumer(
            "vim_account",
            "alarm_request",
            loop=self.loop,
            bootstrap_servers=self.kafka_server,
            group_id="mon-server",
            key_deserializer=bytes.decode,
            value_deserializer=bytes.decode,
        )
        await consumer.start()
        try:
            async for message in consumer:
                log.info("Message arrived: %s", message)
                await self.consume_message(message)
        finally:
            await consumer.stop()

    async def consume_message(self, message):
        try:
            try:
                values = json.loads(message.value)
            except JSONDecodeError:
                values = yaml.safe_load(message.value)

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
                    cor_id = alarm_details['correlation_id']
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
                                                                      cor_id=cor_id,
                                                                      status=True,
                                                                      alarm_id=alarm.uuid)
                    except Exception:
                        log.exception("Error creating alarm: ")
                        response = response_builder.generate_response('create_alarm_response',
                                                                      cor_id=cor_id,
                                                                      status=False,
                                                                      alarm_id=None)
                    await self._publish_response('alarm_response_' + str(cor_id), 'create_alarm_response', response)

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
                    await self._publish_response('alarm_response_' + str(cor_id), 'delete_alarm_response', response)

        except Exception:
            log.exception("Exception processing message: ")

    async def _publish_response(self, topic: str, key: str, msg: dict):
        producer = AIOKafkaProducer(loop=self.loop,
                                    bootstrap_servers=self.kafka_server,
                                    key_serializer=str.encode,
                                    value_serializer=str.encode)
        await producer.start()
        log.info("Sending response %s to topic %s with key %s", json.dumps(msg), topic, key)
        try:
            await producer.send_and_wait(topic, key=key, value=json.dumps(msg))
        finally:
            await producer.stop()


if __name__ == '__main__':
    Server().run()
