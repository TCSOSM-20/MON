# Copyright 2017 iIntel Research and Development Ireland Limited
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
"""Tests for all metric request message keys."""

import json
import logging
import unittest

import mock

from osm_mon.core.auth import AuthManager
from osm_mon.plugins.OpenStack.Gnocchi import metric_handler as metric_req
from osm_mon.plugins.OpenStack.Gnocchi.metric_handler import OpenstackMetricHandler
from osm_mon.plugins.OpenStack.common import Common

log = logging.getLogger(__name__)


class Response(object):
    """Mock a response object for requests."""

    def __init__(self):
        """Initialise test and status code values."""
        self.text = json.dumps([{"id": "test_id"}])
        self.status_code = "STATUS_CODE"


class Message(object):
    """A class to mock a message object value for metric requests."""

    def __init__(self):
        """Initialize a mocked message instance."""
        self.topic = "metric_request"
        self.key = None
        self.value = json.dumps({"mock_message": "message_details"})


class TestMetricReq(unittest.TestCase):
    """Integration test for metric request keys."""

    def setUp(self):
        """Setup the tests for metric request keys."""
        super(TestMetricReq, self).setUp()
        self.metrics = metric_req.OpenstackMetricHandler()

    @mock.patch.object(Common, "get_auth_token", mock.Mock())
    @mock.patch.object(Common, "get_endpoint", mock.Mock())
    @mock.patch.object(metric_req.OpenstackMetricHandler, "delete_metric")
    @mock.patch.object(metric_req.OpenstackMetricHandler, "get_metric_id")
    @mock.patch.object(AuthManager, "get_credentials")
    def test_delete_metric_key(self, get_creds, get_metric_id, del_metric):
        """Test the functionality for a delete metric request."""
        value = {"metric_name": "disk_write_ops", "resource_uuid": "my_r_id", "correlation_id": 1}

        get_creds.return_value = type('obj', (object,), {
            'config': '{"insecure":true}'
        })
        del_metric.return_value = True

        # Call the metric functionality and check delete request
        get_metric_id.return_value = "my_metric_id"
        self.metrics.handle_request('delete_metric_request', value, 'test_id')
        del_metric.assert_called_with(mock.ANY, mock.ANY, "my_metric_id", False)

    @mock.patch.object(Common, "get_auth_token", mock.Mock())
    @mock.patch.object(Common, 'get_endpoint', mock.Mock())
    @mock.patch.object(metric_req.OpenstackMetricHandler, "list_metrics")
    @mock.patch.object(AuthManager, "get_credentials")
    def test_list_metric_key(self, get_creds, list_metrics):
        """Test the functionality for a list metric request."""
        value = {"metrics_list_request": {"correlation_id": 1}}

        get_creds.return_value = type('obj', (object,), {
            'config': '{"insecure":true}'
        })

        list_metrics.return_value = []

        # Call the metric functionality and check list functionality
        self.metrics.handle_request('list_metric_request', value, 'test_id')
        list_metrics.assert_called_with(mock.ANY, mock.ANY, {"correlation_id": 1}, False)

    @mock.patch.object(Common, "get_auth_token", mock.Mock())
    @mock.patch.object(Common, 'get_endpoint', mock.Mock())
    @mock.patch.object(AuthManager, "get_credentials")
    @mock.patch.object(Common, "perform_request")
    def test_update_metric_key(self, perf_req, get_creds):
        """Test the functionality for an update metric request."""
        value = {"metric_update_request":
                     {"correlation_id": 1,
                      "metric_name": "my_metric",
                      "resource_uuid": "my_r_id"}}

        get_creds.return_value = type('obj', (object,), {
            'config': '{"insecure":true}'
        })

        mock_response = Response()
        mock_response.text = json.dumps({'metrics': {'my_metric': 'id'}})
        perf_req.return_value = mock_response

        # Call metric functionality and confirm no function is called
        # Gnocchi does not support updating a metric configuration
        self.metrics.handle_request('update_metric_request', value, 'test_id')

    @mock.patch.object(Common, "get_auth_token", mock.Mock())
    @mock.patch.object(Common, 'get_endpoint', mock.Mock())
    @mock.patch.object(OpenstackMetricHandler, "configure_metric")
    @mock.patch.object(AuthManager, "get_credentials")
    def test_config_metric_key(self, get_credentials, config_metric):
        """Test the functionality for a create metric request."""
        value = {"metric_create_request": {"correlation_id": 123}}
        get_credentials.return_value = type('obj', (object,), {'config': '{"insecure":true}'})
        # Call metric functionality and check config metric
        config_metric.return_value = "metric_id", "resource_id"
        self.metrics.handle_request('create_metric_request', value, 'test_id')
        config_metric.assert_called_with(mock.ANY, mock.ANY, {"correlation_id": 123}, False)

    @mock.patch.object(Common, "get_auth_token", mock.Mock())
    @mock.patch.object(Common, 'get_endpoint', mock.Mock())
    @mock.patch.object(OpenstackMetricHandler, "read_metric_data")
    @mock.patch.object(AuthManager, "get_credentials")
    @mock.patch.object(Common, "perform_request")
    def test_read_data_key(self, perf_req, get_creds, read_data):
        """Test the functionality for a read metric data request."""
        value = {"correlation_id": 123, "metric_name": "cpu_utilization", "resource_uuid": "uuid"}

        get_creds.return_value = type('obj', (object,), {
            'config': '{"insecure":true}'
        })

        mock_response = Response()
        mock_response.text = json.dumps({'metrics': {'cpu_util': 'id'}})
        perf_req.return_value = mock_response

        # Call metric functionality and check read data metrics
        read_data.return_value = "time_stamps", "data_values"
        self.metrics.handle_request('read_metric_data_request', value, 'test_id')
        read_data.assert_called_with(
            mock.ANY, mock.ANY, value, False)
