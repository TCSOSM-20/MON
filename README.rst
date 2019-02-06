..
 Copyright 2018 Whitestack, LLC
 *************************************************************

 This file is part of OSM Monitoring module
 All Rights Reserved to Whitestack, LLC

 Licensed under the Apache License, Version 2.0 (the "License"); you may
 not use this file except in compliance with the License. You may obtain
 a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 License for the specific language governing permissions and limitations
 under the License.
 For those usages not covered by the Apache License, Version 2.0 please
 contact: bdiaz@whitestack.com or glavado@whitestack.com

OSM MON Module
****************

MON is a monitoring module for OSM.
It collects metrics from VIMs and VNFs and exports them to a Prometheus TSDB.
It manages and evaluates alarms based on those metrics.

Components
**********

MON module has the following components:

 - MON Central: Handles vim accounts registration and alarms CRUD operations, through messages in the Kafka bus.
 - MON Collector: Collects metrics from VIMs and VNFs and then exports them to a TSDB. It uses a plugin model both for collectors and for backends.
 - MON Evaluator: Evaluates alarms and sends notifications through the Kafka bus when they trigger.


Supported Collector Plugins
***************************

 - OpenStack: Requires Gnocchi to be enabled.
 - VROPS
 - AWS: TBD

Developers
**********

  - Benjamín Díaz, Whitestack, Argentina

Maintainers
***********

 - Gianpietro Lavado, Whitestack, Peru

Contributions
*************

For information on how to contribute to OSM MON module, please get in touch with
the developer or the maintainer.

Any new code must follow the development guidelines detailed in the Dev Guidelines
in the OSM Wiki and pass all tests.

Dev Guidelines can be found at:

    [https://osm.etsi.org/wikipub/index.php/Workflow_with_OSM_tools]
