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
from collections import Iterable

from kafka import KafkaProducer, KafkaConsumer
from osm_common import dbmongo
from prometheus_client.core import GaugeMetricFamily

from osm_mon.core.settings import Config

log = logging.getLogger(__name__)


class MonCollector:
    def __init__(self):
        cfg = Config.instance()
        self.kafka_server = cfg.BROKER_URI
        self.common_db_host = cfg.MONGO_URI.split(':')[0]
        self.common_db_port = cfg.MONGO_URI.split(':')[1]
        self.common_db = dbmongo.DbMongo()
        self.common_db.db_connect({'host': self.common_db_host, 'port': int(self.common_db_port), 'name': 'osm'})
        self.producer = KafkaProducer(bootstrap_servers=self.kafka_server,
                                      key_serializer=str.encode,
                                      value_serializer=str.encode)
        self.consumer = KafkaConsumer(bootstrap_servers=self.kafka_server,
                                      key_deserializer=bytes.decode,
                                      value_deserializer=bytes.decode,
                                      consumer_timeout_ms=10000,
                                      group_id='mon-collector-' + str(uuid.uuid4()))
        self.consumer.subscribe(['metric_response'])

    def collect_metrics(self) -> Iterable:
        # TODO(diazb): Remove dependencies on prometheus_client
        log.debug("collect_metrics")
        metrics = {}
        vnfrs = self.common_db.get_list('vnfrs')
        for vnfr in vnfrs:
            nsr_id = vnfr['nsr-id-ref']
            vnfd = self.common_db.get_one('vnfds', {"_id": vnfr['vnfd-id']})
            payloads = self._generate_metric_data_payloads(vnfr, vnfd)
            for payload in payloads:
                cor_id = payload['correlation_id']
                metric_name = payload['metric_name']
                vnf_member_index = payload['vnf_member_index']
                vdu_name = payload['vdu_name']
                self.producer.send(topic='metric_request', key='read_metric_data_request',
                                   value=json.dumps(payload))
                self.producer.flush()
                for message in self.consumer:
                    if message.key == 'read_metric_data_response':
                        content = json.loads(message.value)
                        if content['correlation_id'] == cor_id:
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
        return metrics.values()

    @staticmethod
    def _generate_metric_data_payloads(vnfr: dict, vnfd: dict) -> list:
        log.debug('_generate_metric_data_payloads')
        payloads = []
        nsr_id = vnfr['nsr-id-ref']
        for vdur in vnfr['vdur']:
            # This avoids errors when vdur records have not been completely filled
            if 'name' not in vdur:
                continue
            vdu = next(
                filter(lambda vdu: vdu['id'] == vdur['vdu-id-ref'], vnfd['vdu'])
            )
            if 'monitoring-param' in vdu:
                for param in vdu['monitoring-param']:
                    metric_name = param['nfvi-metric']
                    vnf_member_index = vnfr['member-vnf-index-ref']
                    vdu_name = vdur['name']
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
                    payloads.append(payload)
        return payloads
