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
import logging
import multiprocessing
import time

import peewee

from osm_mon.core.config import Config
from osm_mon.core.database import Alarm
from osm_mon.core.message_bus_client import MessageBusClient
from osm_mon.core.response import ResponseBuilder
from osm_mon.evaluator.service import EvaluatorService, AlarmStatus

log = logging.getLogger(__name__)


class Evaluator:

    def __init__(self, config: Config, loop=None):
        self.conf = config
        if not loop:
            loop = asyncio.get_event_loop()
        self.loop = loop
        self.service = EvaluatorService(config)
        self.msg_bus = MessageBusClient(config)

    def evaluate_forever(self):
        log.debug('evaluate_forever')
        while True:
            try:
                self.evaluate()
                time.sleep(int(self.conf.get('evaluator', 'interval')))
            except peewee.PeeweeException:
                log.exception("Database error evaluating alarms: ")
                raise
            except Exception:
                log.exception("Error evaluating alarms")

    def evaluate(self):
        log.debug('evaluate')
        alarms_tuples = self.service.evaluate_alarms()
        processes = []
        for alarm, status in alarms_tuples:
            p = multiprocessing.Process(target=self.notify_alarm,
                                        args=(alarm, status))
            p.start()
            processes.append(p)
        for process in processes:
            process.join(timeout=10)

    def notify_alarm(self, alarm: Alarm, status: AlarmStatus):
        log.debug("notify_alarm")
        resp_message = self._build_alarm_response(alarm, status)
        log.info("Sent alarm notification: %s", resp_message)
        self.loop.run_until_complete(self.msg_bus.aiowrite('alarm_response', 'notify_alarm', resp_message))

    def _build_alarm_response(self, alarm: Alarm, status: AlarmStatus):
        response = ResponseBuilder()
        tags = {}
        for tag in alarm.tags:
            tags[tag.name] = tag.value
        now = time.strftime("%d-%m-%Y") + " " + time.strftime("%X")
        return response.generate_response(
            'notify_alarm',
            alarm_id=alarm.uuid,
            metric_name=alarm.metric,
            operation=alarm.operation,
            threshold_value=alarm.threshold,
            sev=alarm.severity,
            status=status.value,
            date=now,
            tags=tags)
