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
import json
import logging
import uuid

from osm_mon.core import database
from osm_mon.core.common_db import CommonDbClient
from osm_mon.core.config import Config
from osm_mon.core.database import VimCredentialsRepository, VimCredentials, AlarmRepository, Alarm

log = logging.getLogger(__name__)


class ServerService:

    def __init__(self, config: Config):
        self.common_db = CommonDbClient(config)

    def upsert_vim_account(self,
                           vim_uuid: str,
                           name: str,
                           vim_type: str,
                           url: str,
                           user: str,
                           password: str,
                           tenant_name: str,
                           schema_version: str,
                           config: dict) -> VimCredentials:
        decrypted_vim_password = self.common_db.decrypt_vim_password(password,
                                                                     schema_version,
                                                                     vim_uuid)

        vim_config_encrypted = ("admin_password", "nsx_password", "vcenter_password")
        for key in config:
            if key in vim_config_encrypted:
                config[key] = self.common_db.decrypt_vim_password(config[key],
                                                                  schema_version,
                                                                  vim_uuid)
        database.db.connect()
        try:
            with database.db.atomic():
                return VimCredentialsRepository.upsert(
                    uuid=vim_uuid,
                    name=name,
                    type=vim_type,
                    url=url,
                    user=user,
                    password=decrypted_vim_password,
                    tenant_name=tenant_name,
                    config=json.dumps(config)
                )
        finally:
            database.db.close()

    def delete_vim_account(self, vim_uuid: str) -> None:
        database.db.connect()
        try:
            with database.db.atomic():
                vim_credentials = VimCredentialsRepository.get(VimCredentials.uuid == vim_uuid)
                vim_credentials.delete_instance()
        finally:
            database.db.close()

    def create_alarm(self,
                     name: str,
                     threshold: str,
                     operation: str,
                     severity: str,
                     statistic: str,
                     metric_name: str,
                     vdur_name: str,
                     vnf_member_index: str,
                     nsr_id: str) -> Alarm:
        database.db.connect()
        try:
            with database.db.atomic():
                return AlarmRepository.create(
                    uuid=str(uuid.uuid4()),
                    name=name,
                    threshold=threshold,
                    operation=operation.lower(),
                    severity=severity.lower(),
                    statistic=statistic.lower(),
                    monitoring_param=metric_name,
                    vdur_name=vdur_name,
                    vnf_member_index=vnf_member_index,
                    nsr_id=nsr_id
                )

        finally:
            database.db.close()

    def delete_alarm(self,
                     alarm_uuid: str) -> None:
        database.db.connect()
        try:
            with database.db.atomic():
                alarm = AlarmRepository.get(Alarm.uuid == alarm_uuid)
                alarm.delete_instance()
        finally:
            database.db.close()
