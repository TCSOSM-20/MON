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
import time

import peewee

from osm_mon.collector.backends.prometheus import PrometheusBackend
from osm_mon.collector.vnf_collectors.vmware import VMwareCollector
from osm_mon.collector.infra_collectors.openstack import OpenstackInfraCollector
from osm_mon.collector.metric import Metric
from osm_mon.collector.vnf_collectors.juju import VCACollector
from osm_mon.collector.vnf_collectors.openstack import OpenstackCollector
from osm_mon.core.common_db import CommonDbClient
from osm_mon.core.database import DatabaseManager
from osm_mon.core.settings import Config

log = logging.getLogger(__name__)

VIM_COLLECTORS = {
    "openstack": OpenstackCollector,
    "vmware": VMwareCollector
}
VIM_INFRA_COLLECTORS = {
    "openstack": OpenstackInfraCollector
}
METRIC_BACKENDS = [
    PrometheusBackend
]


class Collector:
    def __init__(self):
        self.common_db = CommonDbClient()
        self.plugins = []
        self.database_manager = DatabaseManager()
        self.database_manager.create_tables()
        self.queue = multiprocessing.Queue()
        self._init_backends()

    def collect_forever(self):
        log.debug('collect_forever')
        cfg = Config.instance()
        while True:
            try:
                self.collect_metrics()
                time.sleep(cfg.OSMMON_COLLECTOR_INTERVAL)
            except peewee.PeeweeException:
                log.exception("Database error consuming message: ")
                raise
            except Exception:
                log.exception("Error collecting metrics")

    def _collect_vim_metrics(self, vnfr: dict, vim_account_id: str):
        # TODO(diazb) Add support for vrops and aws
        database_manager = DatabaseManager()
        vim_type = database_manager.get_vim_type(vim_account_id)
        if vim_type in VIM_COLLECTORS:
            collector = VIM_COLLECTORS[vim_type](vim_account_id)
            metrics = collector.collect(vnfr)
            for metric in metrics:
                self.queue.put(metric)
        else:
            log.debug("vimtype %s is not supported.", vim_type)

    def _collect_vim_infra_metrics(self, vim_account_id: str):
        database_manager = DatabaseManager()
        vim_type = database_manager.get_vim_type(vim_account_id)
        if vim_type in VIM_INFRA_COLLECTORS:
            collector = VIM_INFRA_COLLECTORS[vim_type](vim_account_id)
            status = collector.is_vim_ok()
            status_metric = Metric({'vim_id': vim_account_id}, 'vim_status', status)
            self.queue.put(status_metric)
        else:
            log.debug("vimtype %s is not supported.", vim_type)

    def _collect_vca_metrics(self, vnfr: dict):
        log.debug('_collect_vca_metrics')
        log.debug('vnfr: %s', vnfr)
        vca_collector = VCACollector()
        metrics = vca_collector.collect(vnfr)
        for metric in metrics:
            self.queue.put(metric)

    def collect_metrics(self):
        vnfrs = self.common_db.get_vnfrs()
        processes = []
        for vnfr in vnfrs:
            nsr_id = vnfr['nsr-id-ref']
            vnf_member_index = vnfr['member-vnf-index-ref']
            vim_account_id = self.common_db.get_vim_account_id(nsr_id, vnf_member_index)
            p = multiprocessing.Process(target=self._collect_vim_metrics,
                                        args=(vnfr, vim_account_id))
            processes.append(p)
            p.start()
            p = multiprocessing.Process(target=self._collect_vca_metrics,
                                        args=(vnfr,))
            processes.append(p)
            p.start()
        vims = self.common_db.get_vim_accounts()
        for vim in vims:
            p = multiprocessing.Process(target=self._collect_vim_infra_metrics,
                                        args=(vim['_id'],))
            processes.append(p)
            p.start()
        for process in processes:
            process.join()
        metrics = []
        while not self.queue.empty():
            metrics.append(self.queue.get())
        for plugin in self.plugins:
            plugin.handle(metrics)

    def _init_backends(self):
        for backend in METRIC_BACKENDS:
            self.plugins.append(backend())
