# Copyright 2017 Intel Research and Development Ireland Limited
# *************************************************************

# This file is part of OSM Monitoring module
# All Rights Reserved to Intel Corporation

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
# contact: prithiv.mohan@intel.com or adrian.hoban@intel.com

from setuptools import setup


def parse_requirements(requirements):
    with open(requirements) as f:
        return [l.strip('\n') for l in f if l.strip('\n') and not l.startswith('#') and '://' not in l]


_name = 'osm_mon'
_version_command = ('git describe --match v* --tags --long --dirty', 'pep440-git-full')
_description = 'OSM Monitoring Module'
_author = "Benjamín Díaz"
_author_email = 'bdiaz@whitestack.com'
_maintainer = 'Gianpietro Lavado'
_maintainer_email = 'glavado@whitestack.com'
_license = 'Apache 2.0'
_url = 'https://osm.etsi.org/gitweb/?p=osm/MON.git;a=tree'

setup(
    name=_name,
    version_command=_version_command,
    description=_description,
    long_description=open('README.rst').read(),
    author=_author,
    author_email=_author_email,
    maintainer=_maintainer,
    maintainer_email=_maintainer_email,
    url=_url,
    license=_license,
    packages=[_name],
    package_dir={_name: _name},
    scripts=['osm_mon/plugins/vRealiseOps/vROPs_Webservice/vrops_webservice',
             'osm_mon/core/message_bus/common_consumer.py'],
    install_requires=[
        "kafka-python==1.4.*",
        "requests==2.18.*",
        "cherrypy==14.0.*",
        "jsmin==2.2.*",
        "jsonschema==2.6.*",
        "python-keystoneclient==3.15.*",
        "boto==2.48",
        "python-cloudwatchlogs-logging==0.0.3",
        "py-cloudwatch==0.0.1",
        "pyvcloud==19.1.1",
        "pyopenssl==17.5.*",
        "six==1.11.*",
        "bottle==0.12.*",
        "peewee==3.1.*",
        "pyyaml==3.*",
        "prometheus_client==0.4.*",
        "gnocchiclient==7.0.*",
        "osm-common",
        "n2vc"
    ],
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "osm-mon-collector = osm_mon.cmd.mon_collector:main",
        ]
    },
    dependency_links=[
        'git+https://osm.etsi.org/gerrit/osm/common.git#egg=osm-common'
    ],
    setup_requires=['setuptools-version-command']
)
