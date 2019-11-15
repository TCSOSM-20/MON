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
# contact: glavado@whitestack.com
##
DB_EXISTS=""

max_attempts=120
function wait_db(){
    db_host=$1
    db_port=$2
    attempt=0
    echo "Wait until $max_attempts seconds for MySQL mano Server ${db_host}:${db_port} "
    while ! mysqladmin ping -h"$db_host" -P"$db_port" --silent; do
        #wait 120 sec
        if [ $attempt -ge $max_attempts ]; then
            echo
            echo "Can not connect to database ${db_host}:${db_port} during $max_attempts sec"
            return 1
        fi
        attempt=$[$attempt+1]
        echo -n "."
        sleep 1
    done
    return 0
}

function is_db_created() {
    db_host=$1
    db_port=$2
    db_user=$3
    db_pswd=$4
    db_name=$5

    if mysqlshow -h"$db_host" -P"$db_port" -u"$db_user" -p"$db_pswd" | grep -v Wildcard | grep -q $db_name; then
        echo "DB $db_name exists"
        return 0
    else
        echo "DB $db_name does not exist"
        return 1
    fi
}

if [[ $OSMMON_SQL_DATABASE_URI == *'mysql'* ]]; then
    DB_HOST=$(echo $OSMMON_SQL_DATABASE_URI | sed -r 's|^.+://.+:.+@(.+):.*$|\1|')
    DB_PORT=$(echo $OSMMON_SQL_DATABASE_URI | sed -r 's|^.+://.*:([0-9]+).*$|\1|')
    DB_USER=$(echo $OSMMON_SQL_DATABASE_URI | sed -r 's|^.+://(.+):.+@.+$|\1|')
    DB_PASSWORD=$(echo $OSMMON_SQL_DATABASE_URI | sed -r 's|^.+://.+:(.+)@.*$|\1|')
    DB_NAME=$(echo $OSMMON_SQL_DATABASE_URI | sed -r 's|^.+://.+:.+@.+:.*/(\w+)(\?.*)?$|\1|')
    
    wait_db "$DB_HOST" "$DB_PORT" || exit 1

    is_db_created "$DB_HOST" "$DB_PORT" "$DB_USER" "$DB_PASSWORD" "$DB_NAME" && DB_EXISTS="Y"

    if [ -z $DB_EXISTS ]; then
        mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASSWORD" --default_character_set utf8 -e "CREATE DATABASE $DB_NAME"
    fi
fi

osm-mon-server &
osm-mon-evaluator &
osm-mon-collector &
osm-mon-dashboarder