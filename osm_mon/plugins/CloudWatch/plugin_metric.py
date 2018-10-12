##
# Copyright 2017 xFlow Research Pvt. Ltd
# This file is part of MON module
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
# contact with: wajeeha.hamid@xflowresearch.com
##

"""
AWS-Plugin implements all the methods of MON to interact with AWS using the BOTO client
"""
from io import UnsupportedOperation

from osm_mon.core.settings import Config
from osm_mon.plugins.CloudWatch.metrics import Metrics

__author__ = "Wajeeha Hamid"
__date__ = "18-September-2017"

import logging

log = logging.getLogger(__name__)


class plugin_metrics:
    """Receives Alarm info from MetricAlarm and connects with the consumer/producer """

    def __init__(self):
        self._cfg = Config.instance()
        self.metric = Metrics()

    def create_metric_request(self, metric_info):
        """Compatible API using normalized parameters"""
        metric_resp = self.metric.createMetrics(self.cloudwatch_conn, metric_info)
        return metric_resp

    def update_metric_request(self, updated_info):
        """Compatible API using normalized parameters"""
        update_resp = self.metric.updateMetrics(self.cloudwatch_conn, updated_info)
        return update_resp

    def delete_metric_request(self, delete_info):
        """Compatible API using normalized parameters"""
        del_resp = self.metric.deleteMetrics(self.cloudwatch_conn, delete_info)
        return del_resp

    def list_metrics_request(self, list_info):
        """Compatible API using normalized parameters"""
        list_resp = self.metric.listMetrics(self.cloudwatch_conn, list_info)
        return list_resp

    def read_metrics_data(self, list_info):
        """Compatible API using normalized parameters
        Read all metric data related to a specified metric"""
        data_resp = self.metric.metricsData(self.cloudwatch_conn, list_info)
        return data_resp

    def metric_calls(self, key: str, metric_info: dict, aws_conn: dict):
        """Gets the message from the common consumer"""

        try:
            self.cloudwatch_conn = aws_conn['cloudwatch_connection']
            self.ec2_conn = aws_conn['ec2_connection']

            metric_response = dict()

            log.debug("VIM support : AWS")

            if key == "create_metric_request":
                if self.check_resource(metric_info['metric_create_request']['resource_uuid']):
                    metric_resp = self.create_metric_request(
                        metric_info['metric_create_request'])  # alarm_info = message.value
                    metric_response['schema_version'] = metric_info['schema_version']
                    metric_response['schema_type'] = "create_metric_response"
                    metric_response['metric_create_response'] = metric_resp
                    log.info("Metric configured: %s", metric_resp)
                    return metric_response

            elif key == "update_metric_request":
                if self.check_resource(metric_info['metric_create_request']['resource_uuid']):
                    update_resp = self.update_metric_request(metric_info['metric_create_request'])
                    metric_response['schema_version'] = metric_info['schema_version']
                    metric_response['schema_type'] = "update_metric_response"
                    metric_response['metric_update_response'] = update_resp
                    log.info("Metric Updates: %s", metric_response)
                    return metric_response

            elif key == "delete_metric_request":
                if self.check_resource(metric_info['resource_uuid']):
                    del_resp = self.delete_metric_request(metric_info)
                    log.info("Metric Deletion Not supported in AWS : %s", del_resp)
                    return del_resp

            elif key == "list_metric_request":
                if self.check_resource(metric_info['metrics_list_request']['resource_uuid']):
                    list_resp = self.list_metrics_request(metric_info['metrics_list_request'])
                    metric_response['schema_version'] = metric_info['schema_version']
                    metric_response['schema_type'] = "list_metric_response"
                    metric_response['correlation_id'] = metric_info['metrics_list_request']['correlation_id']
                    metric_response['vim_type'] = metric_info['vim_type']
                    metric_response['metrics_list'] = list_resp
                    log.info("Metric List: %s", metric_response)
                    return metric_response

            elif key == "read_metric_data_request":
                if self.check_resource(metric_info['resource_uuid']):
                    data_resp = self.read_metrics_data(metric_info)
                    metric_response['schema_version'] = metric_info['schema_version']
                    metric_response['schema_type'] = "read_metric_data_response"
                    metric_response['metric_name'] = metric_info['metric_name']
                    metric_response['metric_uuid'] = metric_info['metric_uuid']
                    metric_response['correlation_id'] = metric_info['correlation_uuid']
                    metric_response['resource_uuid'] = metric_info['resource_uuid']
                    metric_response['tenant_uuid'] = metric_info['tenant_uuid']
                    metric_response['metrics_data'] = data_resp
                    log.info("Metric Data Response: %s", metric_response)
                    return metric_response

            else:
                raise UnsupportedOperation("Unknown key, no action will be performed")

        except Exception as e:
            log.error("Consumer exception: %s", str(e))

    def check_resource(self, resource_uuid):

        """Checking the resource_uuid is present in EC2 instances"""
        try:
            check_resp = dict()
            instances = self.ec2_conn.get_all_instance_status()
            status_resource = False

            # resource_id
            for instance_id in instances:
                instance_id = str(instance_id).split(':')[1]
                if instance_id == resource_uuid:
                    check_resp['resource_uuid'] = resource_uuid
                    status_resource = True
                else:
                    status_resource = False

            # status
            return status_resource

        except Exception as e:
            log.error("Error in Plugin Inputs %s", str(e))
