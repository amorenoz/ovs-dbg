#!/bin/sh

set -mex

OVSDB_BACKUP=${OVSDB_BACKUP:-/usr/local/var/run/openvswitch/db.backup}

ovs_version=$(ovs-vsctl -V | grep ovs-vsctl | awk '{print $4}')
ovs_db_version=$(ovsdb-tool schema-version /usr/local/share/openvswitch/vswitch.ovsschema)

ls /usr/local/var/run/openvswitch/db.backup

if [ -f ${OVSDB_BACKUP} ]; then
        echo "Using backup DB file at $OVSDB_BACKUP"
        cp $OVSDB_BACKUP /usr/local/etc/openvswitch/conf.db
else
        echo "Creating new DB"
        ovsdb-tool create /usr/local/etc/openvswitch/conf.db /usr/local/share/openvswitch/vswitch.ovsschema
fi

ovsdb-server --remote=punix:/usr/local/var/run/openvswitch/db.sock --remote=ptcp:6640 --pidfile=ovsdb-server.pid

# wait for ovsdb server to start
#sleep 0.1

#fg %1
