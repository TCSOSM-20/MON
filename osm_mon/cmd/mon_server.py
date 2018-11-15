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
import sys

from osm_mon.core.settings import Config
from osm_mon.server.server import Server


def main():
    cfg = Config.instance()

    root = logging.getLogger()
    root.setLevel(logging.getLevelName(cfg.OSMMON_LOG_LEVEL))
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.getLevelName(cfg.OSMMON_LOG_LEVEL))
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', '%m/%d/%Y %I:%M:%S %p')
    ch.setFormatter(formatter)
    root.addHandler(ch)

    kafka_logger = logging.getLogger('kafka')
    kafka_logger.setLevel(logging.getLevelName(cfg.OSMMON_KAFKA_LOG_LEVEL))

    log = logging.getLogger(__name__)
    log.info("Starting MON Server...")
    log.info("Config: %s", vars(cfg))
    server = Server()
    server.run()


if __name__ == '__main__':
    main()
