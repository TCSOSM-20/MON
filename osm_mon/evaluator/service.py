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
import logging
import multiprocessing
from enum import Enum
from typing import Tuple, List

from osm_mon.core.common_db import CommonDbClient
from osm_mon.core.config import Config
from osm_mon.core.models import Alarm
from osm_mon.evaluator.backends.prometheus import PrometheusBackend

log = logging.getLogger(__name__)

BACKENDS = {
    'prometheus': PrometheusBackend
}


class AlarmStatus(Enum):
    ALARM = 'alarm'
    OK = 'ok'
    INSUFFICIENT = 'insufficient-data'


class EvaluatorService:

    def __init__(self, config: Config):
        self.conf = config
        self.common_db = CommonDbClient(self.conf)
        self.queue = multiprocessing.Queue()

    def _get_metric_value(self,
                          metric_name: str,
                          tags: dict):
        return BACKENDS[self.conf.get('evaluator', 'backend')](self.conf).get_metric_value(metric_name, tags)

    def _evaluate_metric(self,
                         alarm: Alarm):
        log.debug("_evaluate_metric")
        metric_value = self._get_metric_value(alarm.metric, alarm.tags)
        if metric_value is None:
            log.warning("No metric result for alarm %s", alarm.uuid)
            self.queue.put((alarm, AlarmStatus.INSUFFICIENT))
        else:
            if alarm.operation.upper() == 'GT':
                if metric_value > alarm.threshold:
                    self.queue.put((alarm, AlarmStatus.ALARM))
                else:
                    self.queue.put((alarm, AlarmStatus.OK))
            elif alarm.operation.upper() == 'LT':
                if metric_value < alarm.threshold:
                    self.queue.put((alarm, AlarmStatus.ALARM))
                else:
                    self.queue.put((alarm, AlarmStatus.OK))

    def evaluate_alarms(self) -> List[Tuple[Alarm, AlarmStatus]]:
        log.debug('evaluate_alarms')
        processes = []
        for alarm in self.common_db.get_alarms():
            p = multiprocessing.Process(target=self._evaluate_metric,
                                        args=(alarm,))
            processes.append(p)
            p.start()

        for process in processes:
            process.join(timeout=10)
        alarms_tuples = []
        while not self.queue.empty():
            alarms_tuples.append(self.queue.get())
        return alarms_tuples
