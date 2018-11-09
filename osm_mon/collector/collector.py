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

from osm_mon.collector.backends.prometheus import PrometheusBackend
from osm_mon.collector.collectors.juju import VCACollector
from osm_mon.collector.collectors.openstack import OpenstackCollector
from osm_mon.common.common_db_client import CommonDbClient
from osm_mon.core.database import DatabaseManager
from osm_mon.core.settings import Config

log = logging.getLogger(__name__)

VIM_COLLECTORS = {
    "openstack": OpenstackCollector
}


class Collector:
    def __init__(self):
        self.common_db = CommonDbClient()
        self.producer_timeout = 5
        self.consumer_timeout = 5
        self.plugins = []
        self.database_manager = DatabaseManager()
        self.database_manager.create_tables()

    def init_plugins(self):
        prometheus_plugin = PrometheusBackend()
        self.plugins.append(prometheus_plugin)

    def collect_forever(self):
        log.debug('collect_forever')
        cfg = Config.instance()
        while True:
            try:
                self.collect_metrics()
                time.sleep(cfg.OSMMON_COLLECTOR_INTERVAL)
            except Exception:
                log.exception("Error collecting metrics")

    def _get_vim_account_id(self, nsr_id: str, vnf_member_index: int) -> str:
        vnfr = self.common_db.get_vnfr(nsr_id, vnf_member_index)
        return vnfr['vim-account-id']

    def _get_vim_type(self, vim_account_id):
        """Get the vim type that is required by the message."""
        credentials = self.database_manager.get_credentials(vim_account_id)
        return credentials.type

    def _init_vim_collector_and_collect(self, vnfr: dict, vim_account_id: str, queue: multiprocessing.Queue):
        # TODO(diazb) Add support for vrops and aws
        vim_type = self._get_vim_type(vim_account_id)
        if vim_type in VIM_COLLECTORS:
            collector = VIM_COLLECTORS[vim_type](vim_account_id)
            collector.collect(vnfr, queue)
        else:
            log.debug("vimtype %s is not supported.", vim_type)

    def _init_vca_collector_and_collect(self, vnfr: dict, queue: multiprocessing.Queue):
        vca_collector = VCACollector()
        vca_collector.collect(vnfr, queue)

    def collect_metrics(self):
        queue = multiprocessing.Queue()
        vnfrs = self.common_db.get_vnfrs()
        processes = []
        for vnfr in vnfrs:
            nsr_id = vnfr['nsr-id-ref']
            vnf_member_index = vnfr['member-vnf-index-ref']
            vim_account_id = self._get_vim_account_id(nsr_id, vnf_member_index)
            p = multiprocessing.Process(target=self._init_vim_collector_and_collect,
                                        args=(vnfr, vim_account_id, queue))
            processes.append(p)
            p.start()
            p = multiprocessing.Process(target=self._init_vca_collector_and_collect,
                                        args=(vnfr, queue))
            processes.append(p)
            p.start()
        for process in processes:
            process.join()
        metrics = []
        while not queue.empty():
            metrics.append(queue.get())
        for plugin in self.plugins:
            plugin.handle(metrics)
