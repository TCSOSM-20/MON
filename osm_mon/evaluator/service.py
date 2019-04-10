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
import multiprocessing
from enum import Enum
from typing import Tuple, List

from osm_common.dbbase import DbException

from osm_mon.core import database
from osm_mon.core.common_db import CommonDbClient
from osm_mon.core.config import Config
from osm_mon.core.database import Alarm, AlarmRepository
from osm_mon.evaluator.backends.prometheus import PrometheusBackend

log = logging.getLogger(__name__)

BACKENDS = {
    'prometheus': PrometheusBackend
}


class AlarmStatus(Enum):
    ALARM = 'alarm'
    OK = 'ok'
    INSUFFICIENT = 'insufficient-data'


class EvaluatorService:

    def __init__(self, config: Config):
        self.conf = config
        self.common_db = CommonDbClient(self.conf)
        self.queue = multiprocessing.Queue()

    def _get_metric_value(self,
                          nsr_id: str,
                          vnf_member_index: int,
                          vdur_name: str,
                          metric_name: str):
        return BACKENDS[self.conf.get('evaluator', 'backend')]().get_metric_value(metric_name, nsr_id, vdur_name,
                                                                                  vnf_member_index)

    def _evaluate_metric(self,
                         nsr_id: str,
                         vnf_member_index: int,
                         vdur_name: str,
                         metric_name: str,
                         alarm: Alarm):
        log.debug("_evaluate_metric")
        metric_value = self._get_metric_value(nsr_id, vnf_member_index, vdur_name, metric_name)
        if not metric_value:
            log.warning("No metric result for alarm %s", alarm.id)
            self.queue.put((alarm, AlarmStatus.INSUFFICIENT))
        else:
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

    def evaluate_alarms(self) -> List[Tuple[Alarm, AlarmStatus]]:
        log.debug('evaluate_alarms')
        processes = []
        database.db.connect()
        try:
            with database.db.atomic():
                for alarm in AlarmRepository.list():
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
                return alarms_tuples
        finally:
            database.db.close()
