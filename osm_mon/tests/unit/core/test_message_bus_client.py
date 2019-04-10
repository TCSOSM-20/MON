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
import asyncio
from unittest import TestCase, mock

from osm_common.msgkafka import MsgKafka

from osm_mon.core.message_bus_client import MessageBusClient
from osm_mon.core.config import Config


class TestMessageBusClient(TestCase):

    def setUp(self):
        self.config = Config()
        self.config.set('message', 'driver', 'kafka')
        self.loop = asyncio.new_event_loop()

    @mock.patch.object(MsgKafka, 'aioread')
    def test_aioread(self, aioread):
        async def mock_callback():
            pass

        future = asyncio.Future(loop=self.loop)
        future.set_result('mock')
        aioread.return_value = future
        msg_bus = MessageBusClient(self.config, loop=self.loop)
        topic = 'test_topic'
        self.loop.run_until_complete(msg_bus.aioread([topic], mock_callback))
        aioread.assert_called_with(['test_topic'], self.loop, aiocallback=mock_callback)

    @mock.patch.object(MsgKafka, 'aiowrite')
    def test_aiowrite(self, aiowrite):
        future = asyncio.Future(loop=self.loop)
        future.set_result('mock')
        aiowrite.return_value = future
        msg_bus = MessageBusClient(self.config, loop=self.loop)
        topic = 'test_topic'
        key = 'test_key'
        msg = {'test': 'test_msg'}
        self.loop.run_until_complete(msg_bus.aiowrite(topic, key, msg))
        aiowrite.assert_called_with(topic, key, msg, self.loop)

    @mock.patch.object(MsgKafka, 'aioread')
    def test_aioread_once(self, aioread):
        future = asyncio.Future(loop=self.loop)
        future.set_result('mock')
        aioread.return_value = future
        msg_bus = MessageBusClient(self.config, loop=self.loop)
        topic = 'test_topic'
        self.loop.run_until_complete(msg_bus.aioread_once(topic))
        aioread.assert_called_with('test_topic', self.loop)
