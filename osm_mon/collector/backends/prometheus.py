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
from typing import List

from prometheus_client import start_http_server
from prometheus_client.core import REGISTRY, GaugeMetricFamily

from osm_mon.collector.backends.base import BaseBackend
from osm_mon.collector.metric import Metric

log = logging.getLogger(__name__)

OSM_METRIC_PREFIX = 'osm_'


class PrometheusBackend(BaseBackend):

    def __init__(self):
        self.custom_collector = CustomCollector()
        self._start_exporter(8000)

    def handle(self, metrics: List[Metric]):
        log.debug('handle')
        log.debug('metrics: %s', metrics)
        prometheus_metrics = {}
        for metric in metrics:
            if metric.name not in prometheus_metrics:
                prometheus_metrics[metric.name] = GaugeMetricFamily(
                    OSM_METRIC_PREFIX + metric.name,
                    'OSM metric',
                    labels=list(metric.tags.keys())
                )
            prometheus_metrics[metric.name].add_metric(list(metric.tags.values()), metric.value)
        self.custom_collector.metrics = prometheus_metrics.values()

    def _start_exporter(self, port):
        log.debug('_start_exporter')
        log.debug('port: %s', port)
        REGISTRY.register(self.custom_collector)
        log.info("Starting MON Prometheus exporter at port %s", port)
        start_http_server(port)


class CustomCollector(object):

    def __init__(self):
        self.metrics = []

    def describe(self):
        log.debug('describe')
        return []

    def collect(self):
        log.debug("collect")
        return self.metrics
