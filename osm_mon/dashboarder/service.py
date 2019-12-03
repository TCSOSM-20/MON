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
# contact: glavado@whitestack.com
##
import logging

from osm_mon.core.common_db import CommonDbClient
from osm_mon.core.config import Config
import osm_mon.dashboarder.backends.grafana as grafana
from osm_mon import __path__ as mon_path

log = logging.getLogger(__name__)


class DashboarderService:
    def __init__(self, config: Config):
        self.conf = config
        self.common_db = CommonDbClient(self.conf)

    def create_dashboards(self):
        # TODO lavado: migrate these methods to mongo change streams
        # Lists all dashboards and OSM resources for later comparisons
        dashboard_uids = grafana.get_all_dashboard_uids()
        osm_resource_uids = []

        # Reads existing project list and creates a dashboard for each
        projects = self.common_db.get_projects()
        for project in projects:
            project_id = project['_id']
            # Collect Project IDs for periodical dashboard clean-up
            osm_resource_uids.append(project_id)
            dashboard_path = '{}/dashboarder/templates/project_scoped.json'.format(mon_path[0])
            if project_id not in dashboard_uids:
                project_name = project['name']
                grafana.create_dashboard(project_id, project_name,
                                         dashboard_path)
                log.debug('Created dashboard for Project: %s', project_id)
            else:
                log.debug('Dashboard already exists')

        # Reads existing NS list and creates a dashboard for each
        # TODO lavado: only create for ACTIVE NSRs
        nsrs = self.common_db.get_nsrs()
        for nsr in nsrs:
            nsr_id = nsr['_id']
            dashboard_path = '{}/dashboarder/templates/ns_scoped.json'.format(mon_path[0])
            # Collect NS IDs for periodical dashboard clean-up
            osm_resource_uids.append(nsr_id)
            # Check if the NSR's VNFDs contain metrics
            constituent_vnfds = nsr['nsd']['constituent-vnfd']
            for constituent_vnfd in constituent_vnfds:
                try:
                    vnfd = self.common_db.get_vnfd_by_name(constituent_vnfd['vnfd-id-ref'])
                    # If there are metrics, create dashboard (if exists)
                    if 'monitoring-param' in vnfd:
                        if nsr_id not in dashboard_uids:
                            nsr_name = nsr['name']
                            grafana.create_dashboard(nsr_id, nsr_name,
                                                     dashboard_path)
                            log.debug('Created dashboard for NS: %s', nsr_id)
                        else:
                            log.debug('Dashboard already exists')
                        break
                    else:
                        log.debug('NS does not has metrics')
                except Exception:
                    log.exception("VNFD is not valid or has been renamed")
                    continue

        # Delete obsolete dashboards
        for dashboard_uid in dashboard_uids:
            if dashboard_uid not in osm_resource_uids:
                grafana.delete_dashboard(dashboard_uid)
                log.debug('Deleted obsolete dashboard: %s', dashboard_uid)
            else:
                log.debug('All dashboards in use')
