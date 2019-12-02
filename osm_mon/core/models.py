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
import uuid


class Alarm:

    def __init__(self, name: str = None, severity: str = None, threshold: float = None, operation: str = None,
                 statistic: str = None, metric: str = None, tags: dict = {}):
        self.uuid = str(uuid.uuid4())
        self.name = name
        self.severity = severity
        self.threshold = threshold
        self.operation = operation
        self.statistic = statistic
        self.metric = metric
        self.tags = tags

    def to_dict(self) -> dict:
        alarm = {
            'uuid': self.uuid,
            'name': self.name,
            'severity': self.severity,
            'threshold': self.threshold,
            'statistic': self.statistic,
            'metric': self.metric,
            'tags': self.tags,
            'operation': self.operation
        }
        return alarm

    @staticmethod
    def from_dict(data: dict):
        alarm = Alarm()
        alarm.uuid = data.get('uuid', str(uuid.uuid4()))
        alarm.name = data.get('name')
        alarm.severity = data.get('severity')
        alarm.threshold = float(data.get('threshold'))
        alarm.statistic = data.get('statistic')
        alarm.metric = data.get('metric')
        alarm.tags = data.get('tags')
        alarm.operation = data.get('operation')
        return alarm
