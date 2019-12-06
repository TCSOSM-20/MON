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

FROM ubuntu:16.04

LABEL authors="Benjamín Díaz"

RUN apt-get --yes update \
 && apt-get --yes install git python3 python3-pip libmysqlclient-dev libssl-dev libffi-dev mysql-client \
 && pip3 install pip==9.0.3

COPY requirements.txt /mon/requirements.txt

RUN pip3 install -r /mon/requirements.txt

COPY . /mon

RUN pip3 install /mon

ENV OSMMON_MESSAGE_DRIVER kafka
ENV OSMMON_MESSAGE_HOST kafka
ENV OSMMON_MESSAGE_PORT 9092

ENV OSMMON_DATABASE_DRIVER mongo
ENV OSMMON_DATABASE_URI mongodb://mongo:27017

ENV OSMMON_SQL_DATABASE_URI sqlite:///mon_sqlite.db
ENV OSMMON_GLOBAL_REQUEST_TIMEOUT 10
ENV OSMMON_GLOBAL_LOGLEVEL INFO
ENV OSMMON_VCA_HOST localhost
ENV OSMMON_VCA_SECRET secret
ENV OSMMON_VCA_USER admin
ENV OSMMON_VCA_CACERT cacert
ENV OSMMON_DATABASE_COMMONKEY changeme
ENV OSMMON_COLLECTOR_INTERVAL 30
ENV OSMMON_EVALUATOR_INTERVAL 30
ENV OSMMON_PROMETHEUS_URL http://prometheus:9090

EXPOSE 8000

HEALTHCHECK --interval=5s --timeout=2s --retries=12 \
  CMD osm-mon-healthcheck || exit 1

CMD /bin/bash mon/docker/scripts/start.sh
