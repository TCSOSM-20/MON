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
import unittest

import mock
from kafka import KafkaProducer
from kafka.errors import KafkaError
from osm_common import dbmongo

from osm_mon.collector.collector import MonCollector
from osm_mon.core.database import VimCredentials, DatabaseManager
from osm_mon.core.message_bus.common_consumer import CommonConsumer


@mock.patch.object(dbmongo.DbMongo, "db_connect", mock.Mock())
class MonCollectorTest(unittest.TestCase):
    def test_generate_metric_data_payloads(self):
        vnfr = {
            "_id": "0d9d06ad-3fc2-418c-9934-465e815fafe2",
            "ip-address": "192.168.160.2",
            "created-time": 1535392482.0044956,
            "vim-account-id": "be48ae31-1d46-4892-a4b4-d69abd55714b",
            "vdur": [
                {
                    "interfaces": [
                        {
                            "mac-address": "fa:16:3e:71:fd:b8",
                            "name": "eth0",
                            "ip-address": "192.168.160.2"
                        }
                    ],
                    "status": "ACTIVE",
                    "vim-id": "63a65636-9fc8-4022-b070-980823e6266a",
                    "name": "cirros_ns-1-cirros_vnfd-VM-1",
                    "status-detailed": None,
                    "ip-address": "192.168.160.2",
                    "vdu-id-ref": "cirros_vnfd-VM"
                }
            ],
            "id": "0d9d06ad-3fc2-418c-9934-465e815fafe2",
            "vnfd-ref": "cirros_vdu_scaling_vnf",
            "vnfd-id": "63f44c41-45ee-456b-b10d-5f08fb1796e0",
            "_admin": {
                "created": 1535392482.0067868,
                "projects_read": [
                    "admin"
                ],
                "modified": 1535392482.0067868,
                "projects_write": [
                    "admin"
                ]
            },
            "nsr-id-ref": "87776f33-b67c-417a-8119-cb08e4098951",
            "member-vnf-index-ref": "1",
            "connection-point": [
                {
                    "name": "eth0",
                    "id": None,
                    "connection-point-id": None
                }
            ]
        }
        vnfd = {
            "_id": "63f44c41-45ee-456b-b10d-5f08fb1796e0",
            "name": "cirros_vdu_scaling_vnf",
            "vendor": "OSM",
            "vdu": [
                {
                    "name": "cirros_vnfd-VM",
                    "monitoring-param": [
                        {
                            "id": "cirros_vnfd-VM_memory_util",
                            "nfvi-metric": "average_memory_utilization"
                        }
                    ],
                    "vm-flavor": {
                        "vcpu-count": 1,
                        "memory-mb": 256,
                        "storage-gb": 2
                    },
                    "description": "cirros_vnfd-VM",
                    "count": 1,
                    "id": "cirros_vnfd-VM",
                    "interface": [
                        {
                            "name": "eth0",
                            "external-connection-point-ref": "eth0",
                            "type": "EXTERNAL",
                            "virtual-interface": {
                                "bandwidth": "0",
                                "type": "VIRTIO",
                                "vpci": "0000:00:0a.0"
                            }
                        }
                    ],
                    "image": "cirros034"
                }
            ],
            "monitoring-param": [
                {
                    "id": "cirros_vnf_memory_util",
                    "name": "cirros_vnf_memory_util",
                    "aggregation-type": "AVERAGE",
                    "vdu-monitoring-param-ref": "cirros_vnfd-VM_memory_util",
                    "vdu-ref": "cirros_vnfd-VM"
                }
            ],
            "description": "Simple VNF example with a cirros and a scaling group descriptor",
            "id": "cirros_vdu_scaling_vnf",
            "logo": "cirros-64.png",
            "version": "1.0",
            "connection-point": [
                {
                    "name": "eth0",
                    "type": "VPORT"
                }
            ],
            "mgmt-interface": {
                "cp": "eth0"
            },
            "scaling-group-descriptor": [
                {
                    "name": "scale_cirros_vnfd-VM",
                    "min-instance-count": 1,
                    "vdu": [
                        {
                            "count": 1,
                            "vdu-id-ref": "cirros_vnfd-VM"
                        }
                    ],
                    "max-instance-count": 10,
                    "scaling-policy": [
                        {
                            "name": "auto_memory_util_above_threshold",
                            "scaling-type": "automatic",
                            "cooldown-time": 60,
                            "threshold-time": 10,
                            "scaling-criteria": [
                                {
                                    "name": "group1_memory_util_above_threshold",
                                    "vnf-monitoring-param-ref": "cirros_vnf_memory_util",
                                    "scale-out-threshold": 80,
                                    "scale-out-relational-operation": "GT",
                                    "scale-in-relational-operation": "LT",
                                    "scale-in-threshold": 20
                                }
                            ]
                        }
                    ]
                }
            ],
            "short-name": "cirros_vdu_scaling_vnf",
            "_admin": {
                "created": 1535392242.6281035,
                "modified": 1535392242.6281035,
                "storage": {
                    "zipfile": "package.tar.gz",
                    "pkg-dir": "cirros_vnf",
                    "path": "/app/storage/",
                    "folder": "63f44c41-45ee-456b-b10d-5f08fb1796e0",
                    "fs": "local",
                    "descriptor": "cirros_vnf/cirros_vdu_scaling_vnfd.yaml"
                },
                "usageSate": "NOT_IN_USE",
                "onboardingState": "ONBOARDED",
                "userDefinedData": {

                },
                "projects_read": [
                    "admin"
                ],
                "operationalState": "ENABLED",
                "projects_write": [
                    "admin"
                ]
            }
        }
        payloads = MonCollector._generate_metric_data_payloads(vnfr, vnfd)
        expected_payload = {'ns_id': '87776f33-b67c-417a-8119-cb08e4098951',
                            'vnf_member_index': '1',
                            'metric_name': 'average_memory_utilization',
                            'collection_period': 1,
                            'collection_unit': 'DAY',
                            'vdu_name': 'cirros_ns-1-cirros_vnfd-VM-1'}
        self.assertEqual(len(payloads), 1)
        self.assertEqual(set(expected_payload.items()).issubset(set(payloads[0].items())), True)
