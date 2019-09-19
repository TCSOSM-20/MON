# Copyright 2017 Intel Research and Development Ireland Limited
# *************************************************************

# This file is part of OSM Monitoring module
# All Rights Reserved to Intel Corporation

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
# contact: helena.mcgough@intel.com or adrian.hoban@intel.com
##
"""Generate valid responses to send back to the SO."""

import logging

log = logging.getLogger(__name__)

schema_version = "1.1"


class ResponseBuilder(object):
    """Generates responses for OpenStack plugin."""

    def __init__(self):
        """Initialize OpenStack Response instance."""

    def generate_response(self, key, **kwargs) -> dict:
        """Make call to appropriate response function."""
        if key == "create_alarm_response":
            message = self.create_alarm_response(**kwargs)
        elif key == "delete_alarm_response":
            message = self.delete_alarm_response(**kwargs)
        elif key == "notify_alarm":
            message = self.notify_alarm(**kwargs)
        else:
            log.warning("Failed to generate a valid response message.")
            message = None

        return message

    def create_alarm_response(self, **kwargs) -> dict:
        """Generate a response for a create alarm request."""
        create_alarm_resp = {"schema_version": schema_version,
                             "schema_type": "create_alarm_response",
                             "alarm_create_response": {
                                 "correlation_id": kwargs['cor_id'],
                                 "alarm_uuid": kwargs['alarm_id'],
                                 "status": kwargs['status']}}
        return create_alarm_resp

    def delete_alarm_response(self, **kwargs) -> dict:
        """Generate a response for a delete alarm request."""
        delete_alarm_resp = {"schema_version": schema_version,
                             "schema_type": "alarm_delete_response",
                             "alarm_delete_response": {
                                 "correlation_id": kwargs['cor_id'],
                                 "alarm_uuid": kwargs['alarm_id'],
                                 "status": kwargs['status']}}
        return delete_alarm_resp

    def notify_alarm(self, **kwargs) -> dict:
        """Generate a response to send alarm notifications."""
        notify_alarm_resp = {"schema_version": schema_version,
                             "schema_type": "notify_alarm",
                             "notify_details": {
                                 "alarm_uuid": kwargs['alarm_id'],
                                 "metric_name": kwargs['metric_name'],
                                 "threshold_value": kwargs['threshold_value'],
                                 "operation": kwargs['operation'],
                                 "severity": kwargs['sev'],
                                 "status": kwargs['status'],
                                 "start_date": kwargs['date'],
                                 "tags": kwargs['tags']}}
        return notify_alarm_resp
