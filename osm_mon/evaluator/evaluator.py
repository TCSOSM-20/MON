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
import multiprocessing
import time

from osm_common.dbbase import DbException

from osm_mon.collector.collector import VIM_COLLECTORS
from osm_mon.collector.collectors.juju import VCACollector
from osm_mon.core.common_db import CommonDbClient
from osm_mon.core.database import DatabaseManager, Alarm
from osm_mon.core.message_bus.producer import Producer
from osm_mon.core.response import ResponseBuilder
from osm_mon.core.settings import Config

log = logging.getLogger(__name__)


class Evaluator:
    def __init__(self):
        self.common_db = CommonDbClient()
        self.plugins = []
        self.database_manager = DatabaseManager()
        self.database_manager.create_tables()
        self.queue = multiprocessing.Queue()

    def _evaluate_vim_metric(self,
                             nsr_id: str,
                             vnf_member_index: int,
                             vdur_name: str,
                             nfvi_metric_name: str,
                             vim_account_id: str,
                             alarm: Alarm):
        vim_type = self.database_manager.get_vim_type(vim_account_id)
        if vim_type in VIM_COLLECTORS:
            collector = VIM_COLLECTORS[vim_type](vim_account_id)
            metric = collector.collect_one(nsr_id, vnf_member_index, vdur_name, nfvi_metric_name)
            if alarm.operation.upper() == 'GT':
                if metric.value > alarm.threshold:
                    self.queue.put(alarm)
            elif alarm.operation.upper() == 'LT':
                if metric.value < alarm.threshold:
                    self.queue.put(alarm)

        else:
            log.debug("vimtype %s is not supported.", vim_type)

    def _evaluate_vca_metric(self,
                             nsr_id: str,
                             vnf_member_index: int,
                             vdur_name: str,
                             vnf_metric_name: str,
                             alarm: Alarm):
        collector = VCACollector()
        metric = collector.collect_one(nsr_id, vnf_member_index, vdur_name, vnf_metric_name)
        if alarm.operation.upper() == 'GT':
            if metric.value > alarm.threshold:
                self.queue.put(alarm)
        elif alarm.operation.upper() == 'LT':
            if metric.value < alarm.threshold:
                self.queue.put(alarm)

    def evaluate_forever(self):
        log.debug('collect_forever')
        cfg = Config.instance()
        while True:
            try:
                self.evaluate()
                time.sleep(cfg.OSMMON_EVALUATOR_INTERVAL)
            except Exception:
                log.exception("Error evaluating alarms")

    def evaluate(self):
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

                vim_account_id = self.common_db.get_vim_account_id(nsr_id, vnf_member_index)
                p = multiprocessing.Process(target=self._evaluate_vim_metric,
                                            args=(nsr_id,
                                                  vnf_member_index,
                                                  vdur_name,
                                                  nfvi_metric,
                                                  vim_account_id,
                                                  alarm))
                processes.append(p)
                p.start()
            if 'vdu-metric' in vnf_monitoring_param:
                vnf_metric_name = vnf_monitoring_param['vdu-metric']['vdu-metric-name-ref']
                p = multiprocessing.Process(target=self._evaluate_vca_metric,
                                            args=(nsr_id,
                                                  vnf_member_index,
                                                  vdur_name,
                                                  vnf_metric_name,
                                                  alarm))
                processes.append(p)
                p.start()
            if 'vnf-metric' in vnf_monitoring_param:
                log.warning("vnf-metric is not currently supported.")
                continue

        for process in processes:
            process.join()
        triggered_alarms = []
        while not self.queue.empty():
            triggered_alarms.append(self.queue.get())
        for alarm in triggered_alarms:
            self.notify_alarm(alarm)
            p = multiprocessing.Process(target=self.notify_alarm,
                                        args=(alarm,))
            p.start()

    def notify_alarm(self, alarm: Alarm):
        response = ResponseBuilder()
        now = time.strftime("%d-%m-%Y") + " " + time.strftime("%X")
        # Generate and send response
        resp_message = response.generate_response(
            'notify_alarm',
            alarm_id=alarm.id,
            vdu_name=alarm.vdur_name,
            vnf_member_index=alarm.vnf_member_index,
            ns_id=alarm.nsr_id,
            metric_name=alarm.monitoring_param,
            operation=alarm.operation,
            threshold_value=alarm.threshold,
            sev=alarm.severity,
            status='alarm',
            date=now)
        producer = Producer()
        producer.send(topic='alarm_response', key='notify_alarm', value=json.dumps(resp_message))
        producer.flush()
        log.info("Sent alarm notification: %s", resp_message)
