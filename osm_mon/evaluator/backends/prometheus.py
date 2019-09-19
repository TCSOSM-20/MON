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

import requests

from osm_mon.core.config import Config
from osm_mon.evaluator.backends.base import BaseBackend

log = logging.getLogger(__name__)

OSM_METRIC_PREFIX = 'osm_'


class PrometheusBackend(BaseBackend):

    def __init__(self, config: Config):
        super().__init__(config)
        self.conf = config

    def get_metric_value(self, metric_name: str, tags: dict):
        query = self._build_query(metric_name, tags)
        request_url = self._build_url(query)
        log.info("Querying Prometheus: %s", request_url)
        r = requests.get(request_url, timeout=int(self.conf.get('global', 'request_timeout')))
        if r.status_code == 200:
            json_response = r.json()
            if json_response['status'] == 'success':
                return self._get_metric_value_from_response(json_response)
            else:
                log.warning("Prometheus response is not success. Got status %s", json_response['status'])
        else:
            log.warning("Error contacting Prometheus. Got status code %s: %s", r.status_code, r.text)
        return None

    def _build_query(self, metric_name: str, tags: dict) -> str:
        query_section_tags = []
        for k, v in tags.items():
            query_section_tags.append(k + '=\"' + v + '\"')
        query_section = "query={0}{{{1}}}".format(OSM_METRIC_PREFIX + metric_name, ','.join(query_section_tags))
        return query_section

    def _build_url(self, query: str):
        return self.conf.get('prometheus', 'url') + "/api/v1/query?" + query

    def _get_metric_value_from_response(self, json_response):
        result = json_response['data']['result']
        if len(result):
            metric_value = float(result[0]['value'][1])
            log.info("Metric value: %s", metric_value)
            return metric_value
        else:
            return None
