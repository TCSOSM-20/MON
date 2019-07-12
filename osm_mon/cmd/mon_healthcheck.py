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
import argparse
import logging
import subprocess
import sys

import requests

log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(prog='osm-mon-healthcheck')
    parser.add_argument('--config-file', nargs='?', help='MON configuration file')
    # args = parser.parse_args()
    # cfg = Config(args.config_file)

    if not _processes_running():
        sys.exit(1)
    if not _is_prometheus_exporter_ok():
        sys.exit(1)
    sys.exit(0)


def _processes_running():
    def _contains_process(processes, process_name):
        for row in processes:
            if process_name in row:
                return True
        return False

    processes_to_check = ['osm-mon-collector', 'osm-mon-evaluator', 'osm-mon-server']
    ps = subprocess.Popen(['ps', 'aux'], stdout=subprocess.PIPE).communicate()[0]
    processes_running = ps.decode().split('\n')
    for p in processes_to_check:
        if not _contains_process(processes_running, p):
            log.error("Process %s not running!" % p)
            return False
    return True


def _is_prometheus_exporter_ok():
    try:
        r = requests.get('http://localhost:8000')
        r.raise_for_status()
        return True
    except Exception:
        log.exception("MON Prometheus exporter is not running")
        return False


if __name__ == '__main__':
    main()
