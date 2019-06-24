# -*- coding: utf-8 -*-
# Copyright 2019 VMware
# *************************************************************

# This file is part of OSM Monitoring module
# All Rights Reserved to VMware

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
# contact: mbeierl@vmware.com
# #

import os
import re


def mock_vdc_response(mocker, method='GET', site='https://vrops', url_pattern='', response_file='OK'):
    '''Helper function to load a canned response from a file.'''
    with open(os.path.join(os.path.dirname(__file__), 'vcd_mocks',
                           '%s' % response_file), 'r') as f:
        response = f.read()

    matcher = re.compile(site + url_pattern)
    mocker.register_uri(method, matcher, text=response)
