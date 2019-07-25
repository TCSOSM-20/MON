# -*- coding: utf-8 -*-

# #
# Copyright 2016-2019 VMware Inc.
# This file is part of ETSI OSM
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# For those usages not covered by the Apache License, Version 2.0 please
# contact:  osslegalrouting@vmware.com
# #

# Ref: https://docs.vmware.com/en/vRealize-Operations-Manager/7.0/vrealize-operations-manager-70-reference-guide.pdf
# Potential metrics of interest
# "cpu|capacity_contentionPct"
# "cpu|corecount_provisioned"
# "cpu|costopPct"
# "cpu|demandmhz"
# "cpu|demandPct"
# "cpu|effective_limit"
# "cpu|iowaitPct"
# "cpu|readyPct"
# "cpu|swapwaitPct"
# "cpu|usage_average"
# "cpu|usagemhz_average"
# "cpu|usagemhz_average_mtd"
# "cpu|vm_capacity_provisioned"
# "cpu|workload"
# "guestfilesystem|percentage_total"
# "guestfilesystem|usage_total"
# "mem|consumedPct"
# "mem|guest_usage"
# "mem|host_contentionPct"
# "mem|reservation_used"
# "mem|swapinRate_average"
# "mem|swapoutRate_average"
# "mem|swapped_average"
# "mem|usage_average"
# "net:Aggregate of all instances|droppedPct"
# "net|broadcastTx_summation"
# "net|droppedTx_summation"
# "net|multicastTx_summation"
# "net|pnicBytesRx_average"
# "net|pnicBytesTx_average"
# "net|received_average"
# "net|transmitted_average"
# "net|usage_average"
# "virtualDisk:Aggregate of all instances|commandsAveraged_average"
# "virtualDisk:Aggregate of all instances|numberReadAveraged_average"
# "virtualDisk:Aggregate of all instances|numberWriteAveraged_average"
# "virtualDisk:Aggregate of all instances|totalLatency"
# "virtualDisk:Aggregate of all instances|totalReadLatency_average"
# "virtualDisk:Aggregate of all instances|totalWriteLatency_average"
# "virtualDisk:Aggregate of all instances|usage"
# "virtualDisk:Aggregate of all instances|vDiskOIO"
# "virtualDisk|read_average"
# "virtualDisk|write_average"

METRIC_MAPPINGS = {
    # Percent guest operating system active memory.
    "average_memory_utilization": "mem|usage_average",
    # Percentage of CPU that was used out of all the CPU that was allocated.
    "cpu_utilization": "cpu|usage_average",
    # KB/s of data read in the performance interval
    "disk_read_bytes": "virtualDisk|read_average",
    # Average of read commands per second during the collection interval.
    "disk_read_ops": "virtualDisk:aggregate of all instances|numberReadAveraged_average",
    # KB/s  of data written in the performance interval.
    "disk_write_bytes": "virtualDisk|write_average",
    # Average of write commands per second during the collection interval.
    "disk_write_ops": "virtualDisk:aggregate of all instances|numberWriteAveraged_average",
    # Not supported by vROPS, will always return 0.
    "packets_in_dropped": "net|droppedRx_summation",
    # Transmitted packets dropped in the collection interval.
    "packets_out_dropped": "net|droppedTx_summation",
    # Bytes received in the performance interval.
    "packets_received": "net|received_average",
    # Packets transmitted in the performance interval.
    "packets_sent": "net|transmitted_average",
}
