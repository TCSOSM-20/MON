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
import os
import uuid
import json

from peewee import CharField, TextField, FloatField, Model, AutoField, Proxy
from peewee_migrate import Router
from playhouse.db_url import connect

from osm_mon import migrations
from osm_mon.core.config import Config

log = logging.getLogger(__name__)

db = Proxy()


class BaseModel(Model):
    id = AutoField(primary_key=True)

    class Meta:
        database = db


class VimCredentials(BaseModel):
    uuid = CharField(unique=True)
    name = CharField()
    type = CharField()
    url = CharField()
    user = CharField()
    password = CharField()
    tenant_name = CharField()
    config = TextField(default='{}')


class Alarm(BaseModel):
    uuid = CharField(unique=True)
    name = CharField()
    severity = CharField()
    threshold = FloatField()
    operation = CharField()
    statistic = CharField()
    monitoring_param = CharField()
    vdur_name = CharField()
    vnf_member_index = CharField()
    nsr_id = CharField()


class DatabaseManager:
    def __init__(self, config: Config):
        db.initialize(connect(config.get('sql', 'database_uri')))

    def create_tables(self) -> None:
        with db.atomic():
            router = Router(db, os.path.dirname(migrations.__file__))
            router.run()

    def get_credentials(self, vim_uuid: str = None) -> VimCredentials:
        with db.atomic():
            return VimCredentials.get_or_none(VimCredentials.uuid == vim_uuid)

    def save_credentials(self, vim_credentials) -> VimCredentials:
        """Saves vim credentials. If a record with same uuid exists, overwrite it."""
        with db.atomic():
            exists = VimCredentials.get_or_none(VimCredentials.uuid == vim_credentials.uuid)
            if exists:
                vim_credentials.id = exists.id
            vim_credentials.save()
            return vim_credentials

    def get_alarm(self, alarm_id) -> Alarm:
        with db.atomic():
            alarm = (Alarm.select()
                     .where(Alarm.alarm_id == alarm_id)
                     .get())
            return alarm

    def save_alarm(self, name, threshold, operation, severity, statistic, metric_name, vdur_name,
                   vnf_member_index, nsr_id) -> Alarm:
        """Saves alarm."""
        # TODO: Add uuid optional param and check if exists to handle updates (see self.save_credentials)
        with db.atomic():
            alarm = Alarm()
            alarm.uuid = str(uuid.uuid4())
            alarm.name = name
            alarm.threshold = threshold
            alarm.operation = operation
            alarm.severity = severity
            alarm.statistic = statistic
            alarm.monitoring_param = metric_name
            alarm.vdur_name = vdur_name
            alarm.vnf_member_index = vnf_member_index
            alarm.nsr_id = nsr_id
            alarm.save()
            return alarm

    def delete_alarm(self, alarm_uuid) -> None:
        with db.atomic():
            alarm = (Alarm.select()
                     .where(Alarm.uuid == alarm_uuid)
                     .get())
            alarm.delete_instance()

    def get_vim_type(self, vim_account_id) -> str:
        """Get the vim type that is required by the message."""
        vim_type = None
        credentials = self.get_credentials(vim_account_id)
        config = json.loads(credentials.config)
        if 'vim_type' in config:
            vim_type = config['vim_type']
            return str(vim_type.lower())
        else:
            return str(credentials.type)
