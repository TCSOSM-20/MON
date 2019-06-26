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
import json

from osm_mon.collector.metric import Metric
from osm_mon.core import database
from osm_mon.core.database import VimCredentials, VimCredentialsRepository


class CollectorUtils(Metric):

    @staticmethod
    def get_vim_type(vim_account_id) -> str:
        credentials = CollectorUtils.get_credentials(vim_account_id)
        config = json.loads(credentials.config)
        if 'vim_type' in config:
            vim_type = config['vim_type']
            return str(vim_type.lower())
        else:
            return str(credentials.type)

    @staticmethod
    def get_credentials(vim_account_id) -> VimCredentials:
        database.db.connect()
        try:
            with database.db.atomic():
                return VimCredentialsRepository.get(VimCredentials.uuid == vim_account_id)
        finally:
            database.db.close()

    @staticmethod
    def is_verify_ssl(vim_credentials: VimCredentials):
        vim_config = json.loads(vim_credentials.config)
        return 'insecure' not in vim_config or vim_config['insecure'] is False
