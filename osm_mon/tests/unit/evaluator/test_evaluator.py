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
from unittest import TestCase, mock

from osm_mon.core.common_db import CommonDbClient
from osm_mon.core.config import Config
from osm_mon.core.message_bus_client import MessageBusClient
from osm_mon.evaluator.evaluator import AlarmStatus, Evaluator
from osm_mon.evaluator.service import EvaluatorService


@mock.patch.object(CommonDbClient, "__init__", lambda *args, **kwargs: None)
@mock.patch.object(MessageBusClient, "__init__", lambda *args, **kwargs: None)
class EvaluatorTest(TestCase):
    def setUp(self):
        super().setUp()
        self.config = Config()

    @mock.patch('multiprocessing.Process')
    @mock.patch.object(Evaluator, "notify_alarm")
    @mock.patch.object(EvaluatorService, "evaluate_alarms")
    @mock.patch('osm_mon.core.database.db')
    def test_evaluate(self, db, evaluate_alarms, notify_alarm, process):
        mock_alarm = mock.Mock()
        mock_alarm.operation = 'gt'
        mock_alarm.threshold = 50.0
        evaluate_alarms.return_value = [(mock_alarm, AlarmStatus.ALARM)]

        evaluator = Evaluator(self.config)
        evaluator.evaluate()

        process.assert_called_with(target=notify_alarm, args=(mock_alarm, AlarmStatus.ALARM))
