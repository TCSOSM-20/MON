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
import subprocess
import sys

import requests
from aiokafka import AIOKafkaConsumer

from osm_mon.core.settings import Config

log = logging.getLogger(__name__)


def main():
    # Check Kafka
    if not _processes_running():
        sys.exit(1)
    if not _is_kafka_ok():
        sys.exit(1)
    if not _is_prometheus_exporter_ok():
        sys.exit(1)
    sys.exit(0)


def _processes_running():
    def _contains_process(processes, process_name):
        for row in processes:
            if process_name in row:
                return True
        return False
    processes_to_check = ['osm-mon-collector', 'osm-mon-evaluator', 'osm-mon-server']
    ps = subprocess.Popen(['ps', 'aux'], stdout=subprocess.PIPE).communicate()[0]
    processes_running = ps.decode().split('\n')
    for p in processes_to_check:
        if not _contains_process(processes_running, p):
            return False
    return True


def _is_prometheus_exporter_ok():
    try:
        r = requests.get('http://localhost:8000')
        r.raise_for_status()
        return True
    except Exception:
        log.exception("MON Prometheus exporter is not running")
        return False


def _is_kafka_ok():
    async def _test_kafka(loop):
        cfg = Config.instance()
        consumer = AIOKafkaConsumer(
            'healthcheck',
            loop=loop, bootstrap_servers=cfg.BROKER_URI)
        await consumer.start()
        await consumer.stop()

    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(_test_kafka(loop))
        return True
    except Exception:
        log.exception("MON can not connect to Kafka")
        return False


if __name__ == '__main__':
    main()
