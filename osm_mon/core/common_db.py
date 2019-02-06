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
from osm_common import dbmongo, dbmemory

from osm_mon.core.config import Config


class CommonDbClient:
    def __init__(self, config: Config):
        if config.get('database', 'driver') == "mongo":
            self.common_db = dbmongo.DbMongo()
        elif config.get('database', 'driver') == "memory":
            self.common_db = dbmemory.DbMemory()
        else:
            raise Exception("Unknown database driver {}".format(config.get('section', 'driver')))
        self.common_db.db_connect(config.get("database"))

    def get_vnfr(self, nsr_id: str, member_index: int):
        vnfr = self.common_db.get_one("vnfrs",
                                      {"nsr-id-ref": nsr_id, "member-vnf-index-ref": str(member_index)})
        return vnfr

    def get_vnfrs(self, nsr_id: str = None):
        if nsr_id:
            return [self.get_vnfr(nsr_id, member['member-vnf-index']) for member in
                    self.get_nsr(nsr_id)['nsd']['constituent-vnfd']]
        else:
            return self.common_db.get_list('vnfrs')

    def get_vnfd(self, vnfd_id: str):
        vnfr = self.common_db.get_one("vnfds",
                                      {"_id": vnfd_id})
        return vnfr

    def get_nsr(self, nsr_id: str):
        nsr = self.common_db.get_one("nsrs",
                                     {"id": nsr_id})
        return nsr

    def get_nslcmop(self, nslcmop_id):
        nslcmop = self.common_db.get_one("nslcmops",
                                         {"_id": nslcmop_id})
        return nslcmop

    def get_vdur(self, nsr_id, member_index, vdur_name):
        vnfr = self.get_vnfr(nsr_id, member_index)
        for vdur in vnfr['vdur']:
            if vdur['name'] == vdur_name:
                return vdur
        raise ValueError('vdur not found for nsr-id %s, member_index %s and vdur_name %s', nsr_id, member_index,
                         vdur_name)

    def decrypt_vim_password(self, vim_password: str, schema_version: str, vim_id: str):
        return self.common_db.decrypt(vim_password, schema_version, vim_id)

    def get_vim_account_id(self, nsr_id: str, vnf_member_index: int) -> str:
        vnfr = self.get_vnfr(nsr_id, vnf_member_index)
        return vnfr['vim-account-id']

    def get_vim_accounts(self):
        return self.common_db.get_list('vim_accounts')
