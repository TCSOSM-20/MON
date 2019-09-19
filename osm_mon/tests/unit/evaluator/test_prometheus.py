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
import collections
from unittest import TestCase

from osm_mon.core.config import Config
from osm_mon.evaluator.backends.prometheus import PrometheusBackend


class EvaluatorTest(TestCase):
    def setUp(self):
        super().setUp()
        self.config = Config()

    def test_build_query(self):
        prometheus = PrometheusBackend(self.config)
        alarm_tags = collections.OrderedDict()
        alarm_tags['tag_1'] = 'value_1'
        alarm_tags['tag_2'] = 'value_2'
        query = prometheus._build_query('metric_name', alarm_tags)
        self.assertEqual(query, 'query=osm_metric_name{tag_1="value_1",tag_2="value_2"}')
