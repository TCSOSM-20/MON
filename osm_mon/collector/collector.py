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
import random
import uuid

from n2vc.vnf import N2VC
from prometheus_client.core import GaugeMetricFamily

from osm_mon.common.common_db_client import CommonDbClient
from osm_mon.core.message_bus.consumer import Consumer
from osm_mon.core.message_bus.producer import Producer
from osm_mon.core.settings import Config

log = logging.getLogger(__name__)


class MonCollector:
    def __init__(self):
        cfg = Config.instance()
        self.kafka_server = cfg.BROKER_URI
        self.common_db_client = CommonDbClient()
        self.n2vc = N2VC(server=cfg.OSMMON_VCA_HOST, user=cfg.OSMMON_VCA_USER, secret=cfg.OSMMON_VCA_SECRET)
        self.producer_timeout = 5

    async def collect_metrics(self):
        """
        Collects vdu metrics. These can be vim and/or n2vc metrics.
        It checks for monitoring-params or metrics inside vdu section of vnfd, then collects the metric accordingly.
        If vim related, it sends a metric read request through Kafka, to be handled by mon-proxy.
        If n2vc related, it uses the n2vc client to obtain the readings.
        :return: lists of metrics
        """
        # TODO(diazb): Remove dependencies on prometheus_client
        log.debug("collect_metrics")
        producer = Producer()
        consumer = Consumer('mon-collector-' + str(uuid.uuid4()),
                            consumer_timeout_ms=10000,
                            enable_auto_commit=False)
        consumer.subscribe(['metric_response'])
        metrics = {}
        vnfrs = self.common_db_client.get_vnfrs()
        vca_model_name = 'default'
        for vnfr in vnfrs:
            nsr_id = vnfr['nsr-id-ref']
            nsr = self.common_db_client.get_nsr(nsr_id)
            vnfd = self.common_db_client.get_vnfd(vnfr['vnfd-id'])
            for vdur in vnfr['vdur']:
                # This avoids errors when vdur records have not been completely filled
                if 'name' not in vdur:
                    continue
                vdu = next(
                    filter(lambda vdu: vdu['id'] == vdur['vdu-id-ref'], vnfd['vdu'])
                )
                vnf_member_index = vnfr['member-vnf-index-ref']
                vdu_name = vdur['name']
                if 'monitoring-param' in vdu:
                    for param in vdu['monitoring-param']:
                        metric_name = param['nfvi-metric']
                        payload = self._generate_read_metric_payload(metric_name,
                                                                     nsr_id,
                                                                     vdu_name,
                                                                     vnf_member_index)
                        producer.send(topic='metric_request', key='read_metric_data_request',
                                      value=json.dumps(payload))
                        producer.flush(self.producer_timeout)
                        for message in consumer:
                            if message.key == 'read_metric_data_response':
                                content = json.loads(message.value)
                                if content['correlation_id'] == payload['correlation_id']:
                                    log.debug("Found read_metric_data_response with same correlation_id")
                                    if len(content['metrics_data']['metrics_series']):
                                        metric_reading = content['metrics_data']['metrics_series'][-1]
                                        if metric_name not in metrics.keys():
                                            metrics[metric_name] = GaugeMetricFamily(
                                                metric_name,
                                                'OSM metric',
                                                labels=['ns_id', 'vnf_member_index', 'vdu_name']
                                            )
                                        metrics[metric_name].add_metric([nsr_id, vnf_member_index, vdu_name],
                                                                        metric_reading)
                                    break
                if 'vdu-configuration' in vdu and 'metrics' in vdu['vdu-configuration']:
                    vnf_name_vca = self.n2vc.FormatApplicationName(nsr['name'], vnf_member_index, vdur['vdu-id-ref'])
                    vnf_metrics = await self.n2vc.GetMetrics(vca_model_name, vnf_name_vca)
                    log.debug('VNF Metrics: %s', vnf_metrics)
                    for vnf_metric_list in vnf_metrics.values():
                        for vnf_metric in vnf_metric_list:
                            log.debug("VNF Metric: %s", vnf_metric)
                            if vnf_metric['key'] not in metrics.keys():
                                metrics[vnf_metric['key']] = GaugeMetricFamily(
                                    vnf_metric['key'],
                                    'OSM metric',
                                    labels=['ns_id', 'vnf_member_index', 'vdu_name']
                                )
                            metrics[vnf_metric['key']].add_metric([nsr_id, vnf_member_index, vdu_name],
                                                                  float(vnf_metric['value']))
        consumer.close()
        producer.close(self.producer_timeout)
        log.debug("metric.values = %s", metrics.values())
        return metrics.values()

    @staticmethod
    def _generate_read_metric_payload(metric_name, nsr_id, vdu_name, vnf_member_index) -> dict:
        """
        Builds JSON payload for asking for a metric measurement in MON. It follows the model defined in core.models.
        :param metric_name: OSM metric name (e.g.: cpu_utilization)
        :param nsr_id: NSR ID
        :param vdu_name: Vdu name according to the vdur
        :param vnf_member_index: Index of the VNF in the NS according to the vnfr
        :return: JSON payload as dict
        """
        cor_id = random.randint(1, 10e7)
        payload = {
            'correlation_id': cor_id,
            'metric_name': metric_name,
            'ns_id': nsr_id,
            'vnf_member_index': vnf_member_index,
            'vdu_name': vdu_name,
            'collection_period': 1,
            'collection_unit': 'DAY',
        }
        return payload
