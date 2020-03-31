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
# contact: glavado@whitestack.com or fbravo@whitestack.com
##
import logging
import requests
import base64
from osm_mon.core.config import Config

log = logging.getLogger(__name__)


class GrafanaBackend:
    def __init__(self, config: Config):
        self.conf = config
        self.url = config.get('grafana', 'url')
        grafana_user = config.get("grafana", "user")
        grafana_password = config.get("grafana", "password")
        self.headers = {
            'content-type': "application/json",
            'authorization': "Basic %s" % base64.b64encode(
                (grafana_user + ":" + grafana_password).encode("utf-8")).decode()
        }

    def get_all_dashboard_uids(self):
        # Gets only dashboards that were automated by OSM (with tag 'osm_automated')
        response = requests.request("GET", self.url + "/api/search?tag=osm_automated", headers=self.headers)
        dashboards = response.json()
        dashboard_uids = []
        for dashboard in dashboards:
            dashboard_uids.append(dashboard['uid'])
        log.debug("Searching for all dashboard uids: %s", dashboard_uids)
        return dashboard_uids

    def get_dashboard_status(self, uid):
        response = requests.request("GET", self.url + "/api/dashboards/uid/" + uid, headers=self.headers)
        log.debug("Searching for dashboard result: %s", response.text)
        return response

    def create_dashboard(self, uid, name, json_file):
        with open(json_file) as f:
            dashboard_data = f.read()

        dashboard_data = dashboard_data.replace('OSM_ID', uid).replace('OSM_NAME', name)

        response = requests.request(
            "POST", self.url + "/api/dashboards/db/",  data=dashboard_data, headers=self.headers)
        log.debug("Creating dashboard result: %s", response.text)
        return response

    def delete_dashboard(self, uid):
        response = requests.request("DELETE", self.url + "/api/dashboards/uid/" + uid, headers=self.headers)
        log.debug("Delete dashboard result: %s", response.text)
        return response
