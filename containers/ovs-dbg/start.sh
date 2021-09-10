#!/bin/bash

set -mex

vswitchd-dummy() {
  echo "=============== vswitchd-dummy ==============="
  echo "RESTORE_DIR=$RESTORE_DIR"

  (
  echo "Waiting for ovs-vswitchd to start..."
  sleep 5

  if [ -d "$RESTORE_DIR" ]; then
      echo "Restoring flows"
      sh -e $RESTORE_DIR/restore.sh
  fi
  ) &

  ovs-vswitchd --enable-dummy=override -vvconn -vnetdev_dummy  --no-chdir --pidfile  -vsyslog:off

}

ovsdb() {
  OVSDB_BACKUP=${OVSDB_BACKUP:-/usr/local/var/run/openvswitch/db.backup}
  echo "=============== ovsdb-server ==============="
  echo "OVSDB_BACKUP=$OVSDB_BACKUP"
  DB_FILE=/usr/local/etc/openvswitch/conf.db

  if [ -f ${OVSDB_BACKUP} ]; then
          echo "Using backup DB file at $OVSDB_BACKUP"

          echo "Making a standalone DB if needed"
          ovsdb-tool cluster-to-standalone $DB_FILE $OVSDB_BACKUP || cp $OVSDB_BACKUP $DB_FILE
          echo "Compacting DB"
          ovsdb-tool compact $DB_FILE
  else
          echo "Creating new DB"
          ovsdb-tool create $DB_FILE  /usr/local/share/openvswitch/vswitch.ovsschema
  fi

  mkdir -p /usr/local/var/run/openvswitch/

  ovsdb-server --remote=punix:/usr/local/var/run/openvswitch/db.sock --remote=ptcp:6640 --pidfile=ovsdb-server.pid $DB_FILE

}

cmd=${1:-""}
case ${cmd} in
"vswitchd-dummy")
  vswitchd-dummy
  ;;
"ovsdb")
  ovsdb
  ;;
"sleep")
  sleep infinity 
  ;;
"*")
  echo "Command not supported: ${cmd}"
  exit 1
esac
