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
    long_description=open('README.rst', encoding='utf-8').read(),
    author=_author,
    author_email=_author_email,
    maintainer=_maintainer,
    maintainer_email=_maintainer_email,
    url=_url,
    license=_license,
    packages=[_name],
    package_dir={_name: _name},
    install_requires=[
        "aiokafka==0.6.0",
        "requests==2.18.*",
        "python-keystoneclient==3.15.*",
        "six==1.11.*",
        "peewee==3.8.*",
        "pyyaml>=5.1.2",
        "prometheus_client==0.4.*",
        "gnocchiclient==7.0.*",
        "pyvcloud==19.1.1",
        "python-ceilometerclient==2.9.*",
        "peewee-migrate==1.1.*",
        "python-novaclient==12.0.*",
        "pymysql==0.9.*",
        "python-neutronclient==5.1.*",
        "osm-common",
        "n2vc"
    ],
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "osm-mon-server = osm_mon.cmd.mon_server:main",
            "osm-mon-evaluator = osm_mon.cmd.mon_evaluator:main",
            "osm-mon-collector = osm_mon.cmd.mon_collector:main",
            "osm-mon-dashboarder = osm_mon.cmd.mon_dashboarder:main",            
            "osm-mon-healthcheck = osm_mon.cmd.mon_healthcheck:main",
        ]
    },
    dependency_links=[
        'git+https://osm.etsi.org/gerrit/osm/common.git#egg=osm-common@v5.0',
        'git+https://osm.etsi.org/gerrit/osm/common.git#egg=n2vc@v5.0'
    ],
    setup_requires=['setuptools-version-command']
)
