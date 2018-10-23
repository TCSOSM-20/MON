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
import random
import unittest

from mock import mock

from osm_mon.collector.collector import MonCollector


class MonCollectorTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(None)

    def test_generate_vca_vdu_name(self):
        vdur_name = 'test-juju-metrics01-1-ubuntuvdu1-1'
        expected = 'test-juju-metricsab-b-ubuntuvdub'
        result = self.loop.run_until_complete(MonCollector._generate_vca_vdu_name(vdur_name))
        self.assertEqual(result, expected)

    @mock.patch.object(random, 'randint')
    def test_generate_read_metric_payload(self, randint):
        randint.return_value = 1
        metric_name = 'cpu_utilization'
        nsr_id = 'test_id'
        vdu_name = 'test_vdu'
        vnf_member_index = 1
        expected_payload = {
            'correlation_id': 1,
            'metric_name': metric_name,
            'ns_id': nsr_id,
            'vnf_member_index': vnf_member_index,
            'vdu_name': vdu_name,
            'collection_period': 1,
            'collection_unit': 'DAY',
        }
        result = self.loop.run_until_complete(
            MonCollector._generate_read_metric_payload(metric_name, nsr_id, vdu_name, vnf_member_index))
        self.assertEqual(result, expected_payload)
