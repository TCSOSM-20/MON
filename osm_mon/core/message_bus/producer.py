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
from kafka import KafkaProducer

from osm_mon.core.settings import Config


class Producer(KafkaProducer):
    def __init__(self):
        cfg = Config.instance()
        super().__init__(bootstrap_servers=cfg.BROKER_URI,
                         key_serializer=str.encode,
                         value_serializer=str.encode)

    def send(self, topic, value=None, key=None, partition=None, timestamp_ms=None):
        return super().send(topic, value, key, partition, timestamp_ms)
