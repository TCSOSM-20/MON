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
import threading
import time
from http.server import HTTPServer

from prometheus_client import MetricsHandler
from prometheus_client.core import REGISTRY

from osm_mon.collector.collector import MonCollector
from osm_mon.core.settings import Config

log = logging.getLogger(__name__)


class MonPrometheusExporter:

    def __init__(self):
        self.mon_collector = MonCollector()
        self.custom_collector = CustomCollector()

    def _run_exporter(self):
        log.debug('_run_exporter')
        REGISTRY.register(self.custom_collector)
        server_address = ('', 8000)
        httpd = HTTPServer(server_address, MetricsHandler)
        log.info("Starting MON Prometheus exporter at port %s", 8000)
        httpd.serve_forever()

    def run(self):
        log.debug('_run')
        self._run_exporter()
        self._run_collector()

    def _run_collector(self):
        log.debug('_run_collector')
        t = threading.Thread(target=self._collect_metrics_forever)
        t.setDaemon(True)
        t.start()

    def _collect_metrics_forever(self):
        log.debug('_collect_metrics_forever')
        cfg = Config.instance()
        while True:
            time.sleep(cfg.OSMMON_COLLECTOR_INTERVAL)
            metrics = self.mon_collector.collect_metrics()
            self.custom_collector.metrics = metrics


class CustomCollector(object):

    def __init__(self):
        self.mon_collector = MonCollector()
        self.metrics = []

    def describe(self):
        log.debug('describe')
        return []

    def collect(self):
        log.debug("collect")
        metrics = self.mon_collector.collect_metrics()
        return metrics


if __name__ == '__main__':
    MonPrometheusExporter().run()
