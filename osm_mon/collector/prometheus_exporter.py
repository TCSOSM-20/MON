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
import threading
import time

from prometheus_client import start_http_server
from prometheus_client.core import REGISTRY

from osm_mon.collector.collector import MonCollector
from osm_mon.core.settings import Config

log = logging.getLogger(__name__)


class MonPrometheusExporter:

    def __init__(self):
        self.custom_collector = CustomCollector()

    def _run_exporter(self):
        log.debug('_run_exporter')
        REGISTRY.register(self.custom_collector)
        log.info("Starting MON Prometheus exporter at port %s", 8000)
        start_http_server(8000)

    def run(self):
        log.debug('_run')
        collector_thread = threading.Thread(target=self._run_collector)
        collector_thread.setDaemon(True)
        collector_thread.start()
        exporter_thread = threading.Thread(target=self._run_exporter)
        exporter_thread.setDaemon(True)
        exporter_thread.start()
        collector_thread.join()
        exporter_thread.join()

    def _run_collector(self):
        log.debug('_run_collector')
        asyncio.set_event_loop(asyncio.new_event_loop())
        mon_collector = MonCollector()
        cfg = Config.instance()
        while True:
            try:
                log.debug('_run_collector_loop')
                metrics = asyncio.get_event_loop().run_until_complete(mon_collector.collect_metrics())
                self.custom_collector.metrics = metrics
                time.sleep(cfg.OSMMON_COLLECTOR_INTERVAL)
            except Exception:
                log.exception("Error collecting metrics")



class CustomCollector(object):

    def __init__(self):
        self.mon_collector = MonCollector()
        self.metrics = []

    def describe(self):
        log.debug('describe')
        return []

    def collect(self):
        log.debug("collect")
        return self.metrics


if __name__ == '__main__':
    MonPrometheusExporter().run()
