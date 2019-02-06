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

all: clean package

clean:
	rm -rf dist deb_dist osm_mon-*.tar.gz osm_mon.egg-info .eggs

package:
	python3 setup.py --command-packages=stdeb.command sdist_dsc
	cp debian/python3-osm-mon.postinst deb_dist/osm-mon*/debian
	cd deb_dist/osm-mon*/  && dpkg-buildpackage -rfakeroot -uc -us