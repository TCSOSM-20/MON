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
from osm_mon.collector.metric import Metric
import logging

log = logging.getLogger(__name__)


class VnfMetric(Metric):
    def __init__(self, nsr_id, vnf_member_index, vdur_name, name, value, extra_tags: dict = None):
        tags = {
            'ns_id': nsr_id,
            'vnf_member_index': vnf_member_index,
            'vdu_name': vdur_name
        }
        if extra_tags:
            tags.update(extra_tags)
        log.debug('Tags: %s', tags)
        super().__init__(tags, name, value)
