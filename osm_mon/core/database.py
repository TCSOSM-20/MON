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
from typing import Iterable

from peewee import CharField, FloatField, Model, AutoField, Proxy
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
        db.connect()
        with db.atomic():
            router = Router(db, os.path.dirname(migrations.__file__))
            router.run()
        db.close()


class AlarmRepository:
    @staticmethod
    def create(**query) -> Alarm:
        return Alarm.create(**query)

    @staticmethod
    def get(*expressions) -> Alarm:
        return Alarm.select().where(*expressions).get()

    @staticmethod
    def list(*expressions) -> Iterable[Alarm]:
        if expressions == ():
            return Alarm.select()
        else:
            return Alarm.select().where(*expressions)
