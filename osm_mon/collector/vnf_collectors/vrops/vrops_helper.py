# -*- coding: utf-8 -*-

# #
# Copyright 2016-2019 VMware Inc.
# This file is part of ETSI OSM
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# For those usages not covered by the Apache License, Version 2.0 please
# contact:  osslegalrouting@vmware.com
# #

import logging
import json
import requests
import traceback

from osm_mon.collector.vnf_metric import VnfMetric
from osm_mon.collector.vnf_collectors.vrops.metrics import METRIC_MAPPINGS
import copy

log = logging.getLogger(__name__)


# If the unit from vROPS does not align with the expected value. multiply by the specified amount to ensure
# the correct unit is returned.
METRIC_MULTIPLIERS = {
    "disk_read_bytes": 1024,
    "disk_write_bytes": 1024,
    "packets_received": 1024,
    "packets_sent": 1024
}


class vROPS_Helper():

    def __init__(self,
                 vrops_site='https://vrops',
                 vrops_user='',
                 vrops_password=''):
        self.vrops_site = vrops_site
        self.vrops_user = vrops_user
        self.vrops_password = vrops_password

    def get_vm_resource_list_from_vrops(self):
        """ Find all known resource IDs in vROPs
        """
        api_url = '/suite-api/api/resources?resourceKind=VirtualMachine'
        headers = {'Accept': 'application/json'}
        resource_list = []

        resp = requests.get(self.vrops_site + api_url,
                            auth=(self.vrops_user, self.vrops_password),
                            verify=False, headers=headers)

        if resp.status_code != 200:
            log.error("Failed to get resource list from vROPS: {} {}".format(resp.status_code,
                                                                             resp.content))
            return resource_list

        try:
            resp_data = json.loads(resp.content.decode('utf-8'))
            if resp_data.get('resourceList') is not None:
                resource_list = resp_data.get('resourceList')

        except Exception as exp:
            log.error("get_vm_resource_id: Error in parsing {}\n{}".format(exp, traceback.format_exc()))

        return resource_list

    def get_metrics(self,
                    vdu_mappings={},
                    monitoring_params={},
                    vnfr=None,
                    tags={}):

        monitoring_keys = {}
        # Collect the names of all the metrics we need to query
        for metric_entry in monitoring_params:
            metric_name = metric_entry['nfvi-metric']
            if metric_name not in METRIC_MAPPINGS:
                log.debug("Metric {} not supported, ignoring".format(metric_name))
                continue
            monitoring_keys[metric_name] = METRIC_MAPPINGS[metric_name]

        metrics = []
        # Make a query for only the stats we have been asked for
        stats_key = ""
        for stat in monitoring_keys.values():
            stats_key += "&statKey={}".format(stat)

        # And only ask for the resource ids that we are interested in
        resource_ids = ""
        sanitized_vdu_mappings = copy.deepcopy(vdu_mappings)
        for key in vdu_mappings.keys():
            vdu = vdu_mappings[key]
            if 'vrops_id' not in vdu:
                log.info("Could not find vROPS id for vdu {}".format(vdu))
                del sanitized_vdu_mappings[key]
                continue
            resource_ids += "&resourceId={}".format(vdu['vrops_id'])
        vdu_mappings = sanitized_vdu_mappings

        try:

            # Now we can make a single call to vROPS to collect all relevant metrics for resources we need to monitor
            api_url = "/suite-api/api/resources/stats?IntervalType=MINUTES&IntervalCount=1"\
                "&rollUpType=MAX&currentOnly=true{}{}".format(stats_key, resource_ids)
            headers = {'Accept': 'application/json'}

            resp = requests.get(self.vrops_site + api_url,
                                auth=(self.vrops_user, self.vrops_password), verify=False, headers=headers)

            if resp.status_code != 200:
                log.error("Failed to get Metrics data from vROPS for {} {}".format(resp.status_code,
                                                                                   resp.content))
                return metrics

            m_data = json.loads(resp.content.decode('utf-8'))
            if 'values' not in m_data:
                return metrics

            statistics = m_data['values']
            for vdu_stat in statistics:
                vrops_id = vdu_stat['resourceId']
                vdu_name = None
                for vdu in vdu_mappings.values():
                    if vdu['vrops_id'] == vrops_id:
                        vdu_name = vdu['name']
                if vdu_name is None:
                    continue
                for item in vdu_stat['stat-list']['stat']:
                    reported_metric = item['statKey']['key']
                    if reported_metric not in METRIC_MAPPINGS.values():
                        continue

                    # Convert the vROPS metric name back to OSM key
                    metric_name = list(METRIC_MAPPINGS.keys())[list(METRIC_MAPPINGS.values()).
                                                               index(reported_metric)]
                    if metric_name in monitoring_keys.keys():
                        metric_value = item['data'][-1]
                        if metric_name in METRIC_MULTIPLIERS:
                            metric_value *= METRIC_MULTIPLIERS[metric_name]
                        metric = VnfMetric(vnfr['nsr-id-ref'],
                                           vnfr['member-vnf-index-ref'],
                                           vdu_name,
                                           metric_name,
                                           metric_value,
                                           tags
                                           )

                        metrics.append(metric)

        except Exception as exp:
            log.error("Exception while parsing metrics data from vROPS {}\n{}".format(exp, traceback.format_exc()))

        return metrics
