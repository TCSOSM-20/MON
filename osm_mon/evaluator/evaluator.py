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
import asyncio
import logging
import multiprocessing
import time
from enum import Enum

import peewee
import requests
from osm_common.dbbase import DbException

from osm_mon.collector.backends.prometheus import OSM_METRIC_PREFIX
from osm_mon.core.common_db import CommonDbClient
from osm_mon.core.config import Config
from osm_mon.core.database import DatabaseManager, Alarm
from osm_mon.core.message_bus_client import MessageBusClient
from osm_mon.core.response import ResponseBuilder

log = logging.getLogger(__name__)


class AlarmStatus(Enum):
    ALARM = 'alarm'
    OK = 'ok'
    INSUFFICIENT = 'insufficient-data'


class Evaluator:

    def __init__(self, config: Config, loop=None):
        self.conf = config
        if not loop:
            loop = asyncio.get_event_loop()
        self.loop = loop
        self.common_db = CommonDbClient(self.conf)
        self.plugins = []
        self.database_manager = DatabaseManager(self.conf)
        self.database_manager.create_tables()
        self.queue = multiprocessing.Queue()
        self.msg_bus = MessageBusClient(config)

    def _evaluate_metric(self,
                         nsr_id: str,
                         vnf_member_index: int,
                         vdur_name: str,
                         metric_name: str,
                         alarm: Alarm):
        log.debug("_evaluate_metric")
        # TODO: Refactor to fit backend plugin model
        query_section = "query={0}{{ns_id=\"{1}\",vdu_name=\"{2}\",vnf_member_index=\"{3}\"}}".format(
            OSM_METRIC_PREFIX + metric_name, nsr_id, vdur_name, vnf_member_index)
        request_url = self.conf.get('prometheus', 'url') + "/api/v1/query?" + query_section
        log.info("Querying Prometheus: %s", request_url)
        r = requests.get(request_url, timeout=int(self.conf.get('global', 'request_timeout')))
        if r.status_code == 200:
            json_response = r.json()
            if json_response['status'] == 'success':
                result = json_response['data']['result']
                if result:
                    metric_value = float(result[0]['value'][1])
                    log.info("Metric value: %s", metric_value)
                    if alarm.operation.upper() == 'GT':
                        if metric_value > alarm.threshold:
                            self.queue.put((alarm, AlarmStatus.ALARM))
                        else:
                            self.queue.put((alarm, AlarmStatus.OK))
                    elif alarm.operation.upper() == 'LT':
                        if metric_value < alarm.threshold:
                            self.queue.put((alarm, AlarmStatus.ALARM))
                        else:
                            self.queue.put((alarm, AlarmStatus.OK))
                else:
                    log.warning("No metric result for alarm %s", alarm.id)
                    self.queue.put((alarm, AlarmStatus.INSUFFICIENT))

            else:
                log.warning("Prometheus response is not success. Got status %s", json_response['status'])
        else:
            log.warning("Error contacting Prometheus. Got status code %s: %s", r.status_code, r.text)

    def evaluate_forever(self):
        log.debug('evaluate_forever')
        while True:
            try:
                self.evaluate()
                time.sleep(int(self.conf.get('evaluator', 'interval')))
            except peewee.PeeweeException:
                log.exception("Database error evaluating alarms: ")
                raise
            except Exception:
                log.exception("Error evaluating alarms")

    def evaluate(self):
        log.debug('evaluate')
        processes = []
        for alarm in Alarm.select():
            try:
                vnfr = self.common_db.get_vnfr(alarm.nsr_id, alarm.vnf_member_index)
            except DbException:
                log.exception("Error getting vnfr: ")
                continue
            vnfd = self.common_db.get_vnfd(vnfr['vnfd-id'])
            try:
                vdur = next(filter(lambda vdur: vdur['name'] == alarm.vdur_name, vnfr['vdur']))
            except StopIteration:
                log.warning("No vdur found with name %s for alarm %s", alarm.vdur_name, alarm.id)
                continue
            vdu = next(filter(lambda vdu: vdu['id'] == vdur['vdu-id-ref'], vnfd['vdu']))
            vnf_monitoring_param = next(
                filter(lambda param: param['id'] == alarm.monitoring_param, vnfd['monitoring-param']))
            nsr_id = vnfr['nsr-id-ref']
            vnf_member_index = vnfr['member-vnf-index-ref']
            vdur_name = vdur['name']
            if 'vdu-monitoring-param' in vnf_monitoring_param:
                vdu_monitoring_param = next(filter(
                    lambda param: param['id'] == vnf_monitoring_param['vdu-monitoring-param'][
                        'vdu-monitoring-param-ref'], vdu['monitoring-param']))
                nfvi_metric = vdu_monitoring_param['nfvi-metric']

                p = multiprocessing.Process(target=self._evaluate_metric,
                                            args=(nsr_id,
                                                  vnf_member_index,
                                                  vdur_name,
                                                  nfvi_metric,
                                                  alarm))
                processes.append(p)
                p.start()
            if 'vdu-metric' in vnf_monitoring_param:
                vnf_metric_name = vnf_monitoring_param['vdu-metric']['vdu-metric-name-ref']
                p = multiprocessing.Process(target=self._evaluate_metric,
                                            args=(nsr_id,
                                                  vnf_member_index,
                                                  vdur_name,
                                                  vnf_metric_name,
                                                  alarm))
                processes.append(p)
                p.start()
            if 'vnf-metric' in vnf_monitoring_param:
                vnf_metric_name = vnf_monitoring_param['vnf-metric']['vnf-metric-name-ref']
                p = multiprocessing.Process(target=self._evaluate_metric,
                                            args=(nsr_id,
                                                  vnf_member_index,
                                                  '',
                                                  vnf_metric_name,
                                                  alarm))
                processes.append(p)
                p.start()

        for process in processes:
            process.join(timeout=10)
        alarms_tuples = []
        while not self.queue.empty():
            alarms_tuples.append(self.queue.get())
        for alarm, status in alarms_tuples:
            p = multiprocessing.Process(target=self.notify_alarm,
                                        args=(alarm, status))
            p.start()

    def notify_alarm(self, alarm: Alarm, status: AlarmStatus):
        log.debug("notify_alarm")
        resp_message = self._build_alarm_response(alarm, status)
        log.info("Sent alarm notification: %s", resp_message)
        self.loop.run_until_complete(self.msg_bus.aiowrite('alarm_response', 'notify_alarm', resp_message))

    def _build_alarm_response(self, alarm: Alarm, status: AlarmStatus):
        response = ResponseBuilder()
        now = time.strftime("%d-%m-%Y") + " " + time.strftime("%X")
        return response.generate_response(
            'notify_alarm',
            alarm_id=alarm.uuid,
            vdu_name=alarm.vdur_name,
            vnf_member_index=alarm.vnf_member_index,
            ns_id=alarm.nsr_id,
            metric_name=alarm.monitoring_param,
            operation=alarm.operation,
            threshold_value=alarm.threshold,
            sev=alarm.severity,
            status=status.value,
            date=now)
