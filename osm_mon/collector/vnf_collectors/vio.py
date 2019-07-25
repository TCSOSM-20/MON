# -*- coding: utf-8 -*-

##
# Copyright 2016-2017 VMware Inc.
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
##

import json
import logging

from osm_mon.collector.utils.collector import CollectorUtils
from osm_mon.collector.vnf_collectors.base_vim import BaseVimCollector
from osm_mon.core.common_db import CommonDbClient
from osm_mon.core.config import Config
from osm_mon.collector.vnf_collectors.vrops.vrops_helper import vROPS_Helper

log = logging.getLogger(__name__)


class VIOCollector(BaseVimCollector):
    def __init__(self, config: Config, vim_account_id: str):
        super().__init__(config, vim_account_id)
        self.common_db = CommonDbClient(config)
        cfg = self.get_vim_account(vim_account_id)
        self.vrops = vROPS_Helper(vrops_site=cfg['vrops_site'],
                                  vrops_user=cfg['vrops_user'],
                                  vrops_password=cfg['vrops_password'])

    def get_vim_account(self, vim_account_id: str):
        vim_account_info = CollectorUtils.get_credentials(vim_account_id)
        return json.loads(vim_account_info.config)

    def collect(self, vnfr: dict):
        vnfd = self.common_db.get_vnfd(vnfr['vnfd-id'])
        vdu_mappings = {}

        # Fetch the list of all known resources from vROPS.
        resource_list = self.vrops.get_vm_resource_list_from_vrops()

        for vdur in vnfr['vdur']:
            # This avoids errors when vdur records have not been completely filled
            if 'name' not in vdur:
                continue

            vdu = next(
                filter(lambda vdu: vdu['id'] == vdur['vdu-id-ref'], vnfd['vdu'])
            )
            if 'monitoring-param' not in vdu:
                continue

            vim_id = vdur['vim-id']
            vdu_mappings[vim_id] = {'name': vdur['name']}

            # Map the vROPS instance id to the vim-id so we can look it up.
            for resource in resource_list:
                for resourceIdentifier in resource['resourceKey']['resourceIdentifiers']:
                    if resourceIdentifier['identifierType']['name'] == 'VMEntityInstanceUUID':
                        if resourceIdentifier['value'] != vim_id:
                            continue
                        vdu_mappings[vim_id]['vrops_id'] = resource['identifier']

        if len(vdu_mappings) != 0:
            return self.vrops.get_metrics(vdu_mappings=vdu_mappings,
                                          monitoring_params=vdu['monitoring-param'],
                                          vnfr=vnfr)
        else:
            return []
