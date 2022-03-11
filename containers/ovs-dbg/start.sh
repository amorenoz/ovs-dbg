#!/bin/bash

set -mex

vswitchd-dummy() {
  echo "=============== vswitchd-dummy ==============="
  OVSDB_SOCKET=${OVSDB_SOCKET:-/usr/local/var/run/openvswitch/db.sock}
  echo "RESTORE_DIR=${RESTORE_DIR}"

  (
  echo "Waiting for ovs-vswitchd to start..."
  sleep 5

  if [ -d "${RESTORE_DIR}" ]; then
      echo "Restoring flows"
      sh -e ${RESTORE_DIR}/restore.sh
  fi
  ) &

  if [ "${CONTAINER_TYPE}" == docker ]; then
    if [ "$UID" -eq 0 ] || [ -z "${UID}" ]; then
      container_user=root
    else
      useradd new_user -u $UID
      chown -R new_user /usr/local/var/run/openvswitch/
      container_user=new_user
    fi
    user_opt="--user ${container_user}"
  fi

  # Replace DPDK netdevs with dummy ones
  for netdev in dpdk dpdkvhostuser dpdkvhostuserclient; do
    for iface in $(ovs-vsctl --format json --columns=_uuid find Interface type=${netdev} | jq -r '.data[][0][1]'); do
        ovs-vsctl --no-wait set Interface $iface type=dummy;
    done
  done

  ovs-vswitchd ${user_opt-} --enable-dummy=override -vvconn -vnetdev_dummy  --no-chdir --pidfile  -vsyslog:off unix:${OVSDB_SOCKET}

}

ovsdb() {
  OVSDB_BACKUP=${OVSDB_BACKUP:-/usr/local/var/run/openvswitch/conf.db}
  local filename=$(basename ${OVSDB_BACKUP})
  OVSDB_SOCKET=${OVSDB_SOCKET:-/usr/local/var/run/openvswitch/db.sock}
  echo "=============== ovsdb-server ==============="
  echo "OVSDB_BACKUP=$OVSDB_BACKUP"
  DB_FILE=/usr/local/etc/openvswitch/${filename}

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

  if [ "${CONTAINER_TYPE}" == docker ]; then
    if [ "$UID" -eq 0 ] || [ -z "${UID}" ]; then
      container_user=root
    else
      useradd new_user -u $UID
      chown -R new_user /usr/local/var/run/openvswitch/ /usr/local/etc/openvswitch/
      container_user=new_user
    fi
    user_opt="--user ${container_user}"
  fi

  ovsdb-server ${user_opt-} --remote=punix:${OVSDB_SOCKET} --remote=ptcp:6640 --pidfile=ovsdb-server.pid $DB_FILE

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
