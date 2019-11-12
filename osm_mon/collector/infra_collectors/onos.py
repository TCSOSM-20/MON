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
from typing import List

import requests
from requests.auth import HTTPBasicAuth

from osm_mon.collector.infra_collectors.base_sdnc import BaseSdncInfraCollector
from osm_mon.collector.metric import Metric
from osm_mon.core.common_db import CommonDbClient
from osm_mon.core.config import Config

log = logging.getLogger(__name__)


class OnosInfraCollector(BaseSdncInfraCollector):
    def __init__(self, config: Config, sdnc_id: str):
        super().__init__(config, sdnc_id)
        self.common_db = CommonDbClient(config)
        self.sdnc = self.common_db.get_sdnc(sdnc_id)

    def collect(self) -> List[Metric]:
        metrics = []
        sdnc_status = self.is_sdnc_ok()
        sdnc_project_id = self.sdnc['_admin']['projects_read'][0]
        sdnc_tags = {
            'sdnc_id': self.sdnc['_id'],
            'project_id': sdnc_project_id
        }
        sdnc_status_metric = Metric(sdnc_tags, 'sdnc_status', sdnc_status)
        metrics.append(sdnc_status_metric)

        return metrics

    def is_sdnc_ok(self) -> bool:
        try:
            ip = self.sdnc['ip']
            port = self.sdnc['port']
            user = self.sdnc['user']
            password = self.common_db.decrypt_sdnc_password(self.sdnc['password'],
                                                            self.sdnc['schema_version'],
                                                            self.sdnc['_id'])
            # TODO: Add support for https
            url = 'http://{}:{}/onos/v1/devices'.format(ip, port)
            requests.get(url, auth=HTTPBasicAuth(user, password))
            return True
        except Exception:
            log.exception("SDNC status is not OK!")
            return False
