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
import time
import socket
import peewee

from osm_mon.dashboarder.service import DashboarderService
from osm_mon.core.config import Config

log = logging.getLogger(__name__)


class Dashboarder:
    def __init__(self, config: Config):
        self.conf = config
        self.service = DashboarderService(config)

    def dashboard_forever(self):
        log.debug('dashboard_forever')
        while True:
            try:
                socket.gethostbyname("grafana")
                log.debug("Dashboard backend is running")
            except socket.error:
                log.debug("Dashboard backend is not available")
                time.sleep(int(self.conf.get('dashboarder', 'interval')))
                continue
            try:
                self.create_dashboards()
                time.sleep(int(self.conf.get('dashboarder', 'interval')))
            except peewee.PeeweeException:
                log.exception("Database error consuming message: ")
                raise
            except Exception:
                log.exception("Error creating dashboards")

    def create_dashboards(self):
        self.service.create_dashboards()
        log.debug('I just called the dashboarder service!')
