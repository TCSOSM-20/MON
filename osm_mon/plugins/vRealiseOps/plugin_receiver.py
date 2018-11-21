# -*- coding: utf-8 -*-

##
# Copyright 2016-2017 VMware Inc.
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
##

"""
Monitoring plugin receiver that consumes the request messages &
responds using producer for vROPs
"""

import json
import logging
import os
import sys
import traceback
from io import UnsupportedOperation

import six

from osm_mon.core.settings import Config
from osm_mon.plugins.vRealiseOps.mon_plugin_vrops import MonPlugin

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))

from osm_mon.core.auth import AuthManager

from xml.etree import ElementTree as XmlElementTree

schema_version = "1.0"
req_config_params = ('vrops_site', 'vrops_user', 'vrops_password',
                     'vcloud-site', 'admin_username', 'admin_password',
                     'vcenter_ip', 'vcenter_port', 'vcenter_user', 'vcenter_password',
                     'vim_tenant_name', 'orgname')
MODULE_DIR = os.path.dirname(__file__)
CONFIG_FILE_NAME = 'vrops_config.xml'
CONFIG_FILE_PATH = os.path.join(MODULE_DIR, CONFIG_FILE_NAME)

cfg = Config.instance()
logging.basicConfig(stream=sys.stdout,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=logging.getLevelName(cfg.OSMMON_LOG_LEVEL))

logger = logging.getLogger(__name__)


class PluginReceiver:
    """MON Plugin receiver receiving request messages & responding using producer for vROPs
    telemetry plugin
    """

    def __init__(self):
        """Constructor of PluginReceiver
        """
        self._cfg = Config.instance()

    def handle_alarm_requests(self, key: str, values: dict, vim_uuid: str):
        values['vim_uuid'] = vim_uuid
        if key == "create_alarm_request":
            config_alarm_info = values
            alarm_uuid = self.create_alarm(config_alarm_info)
            logger.info("Alarm created with alarm uuid: {}".format(alarm_uuid))
            # Publish message using producer
            return self.publish_create_alarm_status(alarm_uuid, config_alarm_info)
        elif key == "update_alarm_request":
            update_alarm_info = values
            alarm_uuid = self.update_alarm(update_alarm_info)
            logger.info("Alarm definition updated : alarm uuid: {}".format(alarm_uuid))
            # Publish message using producer
            return self.publish_update_alarm_status(alarm_uuid, update_alarm_info)
        elif key == "delete_alarm_request":
            delete_alarm_info = values
            alarm_uuid = self.delete_alarm(delete_alarm_info)
            logger.info("Alarm definition deleted : alarm uuid: {}".format(alarm_uuid))
            # Publish message using producer
            return self.publish_delete_alarm_status(alarm_uuid, delete_alarm_info)
        elif key == "list_alarm_request":
            request_input = values
            triggered_alarm_list = self.list_alarms(request_input)
            # Publish message using producer
            return self.publish_list_alarm_response(triggered_alarm_list, request_input)
        else:
            raise UnsupportedOperation("Unknown key, no action will be performed")

    def handle_metric_requests(self, key: str, values: dict, vim_uuid: str):
        values['vim_uuid'] = vim_uuid
        if key == "read_metric_data_request":
            metric_request_info = values
            access_config = self.get_vim_access_config(metric_request_info['vim_uuid'])
            mon_plugin_obj = MonPlugin(access_config)
            metrics_data = mon_plugin_obj.get_metrics_data(metric_request_info)
            logger.info("Collected Metrics Data: {}".format(metrics_data))
            # Publish message using producer
            return self.publish_metrics_data_status(metrics_data)
        elif key == "create_metric_request":
            metric_info = values
            metric_status = self.verify_metric(metric_info)
            # Publish message using producer
            return self.publish_create_metric_response(metric_info, metric_status)
        elif key == "update_metric_request":
            metric_info = values
            metric_status = self.verify_metric(metric_info)
            # Publish message using producer
            return self.publish_update_metric_response(metric_info, metric_status)
        elif key == "delete_metric_request":
            metric_info = values
            # Deleting Metric Data is not allowed. Publish status as False
            logger.warning("Deleting Metric is not allowed by VMware vROPs plugin: {}"
                           .format(metric_info['metric_name']))
            # Publish message using producer
            return self.publish_delete_metric_response(metric_info)

        else:
            raise UnsupportedOperation("Unknown key, no action will be performed")

    def create_alarm(self, config_alarm_info):
        """Create alarm using vROPs plugin
        """
        access_config = self.get_vim_access_config(config_alarm_info['vim_uuid'])
        mon_plugin = MonPlugin(access_config)
        mon_plugin.configure_rest_plugin()
        alarm_uuid = mon_plugin.configure_alarm(config_alarm_info['alarm_create_request'])
        return alarm_uuid

    def publish_create_alarm_status(self, alarm_uuid, config_alarm_info):
        """Publish create alarm status using producer
        """
        topic = 'alarm_response'
        msg_key = 'create_alarm_response'
        response_msg = {"schema_version": schema_version,
                        "schema_type": "create_alarm_response",
                        "vim_uuid": config_alarm_info["vim_uuid"],
                        "alarm_create_response":
                            {"correlation_id": config_alarm_info["alarm_create_request"]["correlation_id"],
                             "alarm_uuid": alarm_uuid,
                             "status": True if alarm_uuid else False
                             }
                        }
        logger.info("Publishing response:\nTopic={}\nKey={}\nValue={}"
                    .format(topic, msg_key, response_msg))

        return response_msg

    def update_alarm(self, update_alarm_info):
        """Update already created alarm
        """
        access_config = self.get_vim_access_config(update_alarm_info['vim_uuid'])
        mon_plugin = MonPlugin(access_config)
        alarm_uuid = mon_plugin.update_alarm_configuration(update_alarm_info['alarm_update_request'])
        return alarm_uuid

    def publish_update_alarm_status(self, alarm_uuid, update_alarm_info):
        """Publish update alarm status requests using producer
        """
        topic = 'alarm_response'
        msg_key = 'update_alarm_response'
        response_msg = {"schema_version": schema_version,
                        "schema_type": "update_alarm_response",
                        "vim_uuid": update_alarm_info["vim_uuid"],
                        "alarm_update_response":
                            {"correlation_id": update_alarm_info["alarm_update_request"]["correlation_id"],
                             "alarm_uuid": update_alarm_info["alarm_update_request"]["alarm_uuid"] \
                                 if update_alarm_info["alarm_update_request"].get('alarm_uuid') is not None else None,
                             "status": True if alarm_uuid else False
                             }
                        }
        logger.info("Publishing response:\nTopic={}\nKey={}\nValue={}"
                    .format(topic, msg_key, response_msg))

        return response_msg

    def delete_alarm(self, delete_alarm_info):
        """Delete alarm configuration
        """
        access_config = self.get_vim_access_config(delete_alarm_info['vim_uuid'])
        mon_plugin = MonPlugin(access_config)
        alarm_uuid = mon_plugin.delete_alarm_configuration(delete_alarm_info['alarm_delete_request'])
        return alarm_uuid

    def publish_delete_alarm_status(self, alarm_uuid, delete_alarm_info):
        """Publish update alarm status requests using producer
        """
        topic = 'alarm_response'
        msg_key = 'delete_alarm_response'
        response_msg = {"schema_version": schema_version,
                        "schema_type": "delete_alarm_response",
                        "vim_uuid": delete_alarm_info['vim_uuid'],
                        "alarm_deletion_response":
                            {"correlation_id": delete_alarm_info["alarm_delete_request"]["correlation_id"],
                             "alarm_uuid": delete_alarm_info["alarm_delete_request"]["alarm_uuid"],
                             "status": True if alarm_uuid else False
                             }
                        }
        logger.info("Publishing response:\nTopic={}\nKey={}\nValue={}"
                    .format(topic, msg_key, response_msg))

        return response_msg

    def publish_metrics_data_status(self, metrics_data):
        """Publish the requested metric data using producer
        """
        topic = 'metric_response'
        msg_key = 'read_metric_data_response'
        logger.info("Publishing response:\nTopic={}\nKey={}\nValue={}"
                    .format(topic, msg_key, metrics_data))

        return metrics_data

    def verify_metric(self, metric_info):
        """Verify if metric is supported or not
        """
        access_config = self.get_vim_access_config(metric_info['vim_uuid'])
        mon_plugin = MonPlugin(access_config)
        if 'metric_create_request' in metric_info:
            metric_key_status = mon_plugin.verify_metric_support(metric_info['metric_create_request'])
        else:
            metric_key_status = mon_plugin.verify_metric_support(metric_info['metric_update_request'])
        return metric_key_status

    def publish_create_metric_response(self, metric_info, metric_status):
        """Publish create metric response
        """
        topic = 'metric_response'
        msg_key = 'create_metric_response'
        response_msg = {"schema_version": schema_version,
                        "schema_type": "create_metric_response",
                        ##"vim_uuid":metric_info['vim_uuid'],
                        ##"correlation_id":metric_info['correlation_id'],
                        "metric_create_response":
                            {
                                ##"metric_uuid":'0',
                                ##"resource_uuid":metric_info['metric_create']['resource_uuid'],
                                ##"vim_uuid":metric_info['vim_uuid'], #May be required. TODO - Confirm
                                "correlation_id": metric_info['correlation_id'],
                                "status": metric_status
                            }
                        }
        logger.info("Publishing response:\nTopic={}\nKey={}\nValue={}"
                    .format(topic, msg_key, response_msg))

        return response_msg

    def publish_update_metric_response(self, metric_info, metric_status):
        """Publish update metric response
        """
        topic = 'metric_response'
        msg_key = 'update_metric_response'
        response_msg = {"schema_version": schema_version,
                        "schema_type": "metric_update_response",
                        "vim_uuid": metric_info['vim_uuid'],
                        "metric_update_response":
                            {
                                "metric_uuid": '0',
                                "correlation_id": metric_info['correlation_id'],
                                "resource_uuid": metric_info['metric_create']['resource_uuid'],
                                "status": metric_status
                            }
                        }
        logger.info("Publishing response:\nTopic={}\nKey={}\nValue={}"
                    .format(topic, msg_key, response_msg))

        return response_msg

    def publish_delete_metric_response(self, metric_info):
        """Publish delete metric response
        """
        topic = 'metric_response'
        msg_key = 'delete_metric_response'
        if 'tenant_uuid' in metric_info and metric_info['tenant_uuid'] is not None:
            tenant_uuid = metric_info['tenant_uuid']
        else:
            tenant_uuid = None

        response_msg = {"schema_version": schema_version,
                        "schema_type": "delete_metric_response",
                        "vim_uuid": metric_info['vim_uuid'],
                        "correlation_id": metric_info['correlation_id'],
                        "metric_name": metric_info['metric_name'],
                        "metric_uuid": '0',
                        "resource_uuid": metric_info['resource_uuid'],
                        "tenant_uuid": tenant_uuid,
                        "status": False
                        }
        logger.info("Publishing response:\nTopic={}\nKey={}\nValue={}"
                    .format(topic, msg_key, response_msg))

        return response_msg

    def list_alarms(self, list_alarm_input):
        """Collect list of triggered alarms based on input
        """
        access_config = self.get_vim_access_config(list_alarm_input['vim_uuid'])
        mon_plugin = MonPlugin(access_config)
        triggered_alarms = mon_plugin.get_triggered_alarms_list(list_alarm_input['alarm_list_request'])
        return triggered_alarms

    def publish_list_alarm_response(self, triggered_alarm_list, list_alarm_input):
        """Publish list of triggered alarms
        """
        topic = 'alarm_response'
        msg_key = 'list_alarm_response'
        response_msg = {"schema_version": schema_version,
                        "schema_type": "list_alarm_response",
                        "vim_type": "VMware",
                        "vim_uuid": list_alarm_input['vim_uuid'],
                        "correlation_id": list_alarm_input['alarm_list_request']['correlation_id'],
                        "list_alarm_response": triggered_alarm_list
                        }
        logger.info("Publishing response:\nTopic={}\nKey={}\nValue={}"
                    .format(topic, msg_key, response_msg))

        return response_msg

    def update_access_credentials(self, access_info):
        """Verify if all the required access config params are provided and
           updates access config in default vrops config file
        """
        update_status = False
        # Check if all the required config params are passed in request
        if not all(keys in access_info for keys in req_config_params):
            logger.debug("All required Access Config Parameters not provided")
            logger.debug("List of required Access Config Parameters: {}".format(req_config_params))
            logger.debug("List of given Access Config Parameters: {}".format(access_info))
            return update_status

        wr_status = self.write_access_config(access_info)
        return wr_status  # True/False

    def write_access_config(self, access_info):
        """Write access configuration to vROPs config file.
        """
        wr_status = False
        try:
            tree = XmlElementTree.parse(CONFIG_FILE_PATH)
            root = tree.getroot()
            alarmParams = {}
            for config in root:
                if config.tag == 'Access_Config':
                    for param in config:
                        for key, val in six.iteritems(access_info):
                            if param.tag == key:
                                # print param.tag, val
                                param.text = val

            tree.write(CONFIG_FILE_PATH)
            wr_status = True
        except Exception as exp:
            logger.warning("Failed to update Access Config Parameters: {}".format(exp))

        return wr_status

    def publish_access_update_response(self, access_update_status, access_info_req):
        """Publish access update response
        """
        topic = 'access_credentials'
        msg_key = 'vim_access_credentials_response'
        response_msg = {"schema_version": schema_version,
                        "schema_type": "vim_access_credentials_response",
                        "correlation_id": access_info_req['access_config']['correlation_id'],
                        "status": access_update_status
                        }
        logger.info("Publishing response:\nTopic={}\nKey={}\nValue={}" \
                    .format(topic, msg_key, response_msg))
        # Core Add producer
        return response_msg

    def get_vim_access_config(self, vim_uuid):
        """Get VIM access configuration & account details from path: VIM_ACCOUNTS_FILE_PATH
        """
        vim_account = {}
        auth_manager = AuthManager()
        vim_account_details = auth_manager.get_credentials(vim_uuid)

        try:
            if vim_account_details is not None:
                vim_account['name'] = vim_account_details.name
                vim_account['vim_tenant_name'] = vim_account_details.tenant_name
                vim_account['vim_type'] = vim_account_details.type
                vim_account['vim_url'] = vim_account_details.url
                vim_account['org_user'] = vim_account_details.user
                vim_account['org_password'] = vim_account_details.password
                vim_account['vim_uuid'] = vim_account_details.uuid

                vim_config = json.loads(vim_account_details.config)
                vim_account['admin_username'] = vim_config['admin_username']
                vim_account['admin_password'] = vim_config['admin_password']
                vim_account['vrops_site'] = vim_config['vrops_site']
                vim_account['vrops_user'] = vim_config['vrops_user']
                vim_account['vrops_password'] = vim_config['vrops_password']
                vim_account['vcenter_ip'] = vim_config['vcenter_ip']
                vim_account['vcenter_port'] = vim_config['vcenter_port']
                vim_account['vcenter_user'] = vim_config['vcenter_user']
                vim_account['vcenter_password'] = vim_config['vcenter_password']

                if vim_config['nsx_manager'] is not None:
                    vim_account['nsx_manager'] = vim_config['nsx_manager']
                if vim_config['nsx_user'] is not None:
                    vim_account['nsx_user'] = vim_config['nsx_user']
                if vim_config['nsx_password'] is not None:
                    vim_account['nsx_password'] = vim_config['nsx_password']
                if vim_config['orgname'] is not None:
                    vim_account['orgname'] = vim_config['orgname']
        except Exception as exp:
            logger.error("VIM account details not sufficient: {}".format(exp))
        return vim_account


"""
def main():
    #log.basicConfig(filename='mon_vrops_log.log',level=log.DEBUG)
    set_logger()
    plugin_rcvr = PluginReceiver()
    plugin_rcvr.consume()

if __name__ == "__main__":
    main()
"""
