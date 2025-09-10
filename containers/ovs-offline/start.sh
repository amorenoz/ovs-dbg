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

set_runtime_vars() {
    local db_type=$1

    case $db_type in
        ovs)
            OVS_RUNDIR=${OVS_RUNDIR:-/usr/local/var/run/openvswitch/}
            OVSDB_SOCKET=$OVS_RUNDIR/db.sock
            OVSDB_PIDFILE=$OVS_RUNDIR/ovsdb-server.pid
            OVSDB_BACKUP=${OVSDB_BACKUP:-${OVS_RUNDIR}/conf.db}
            OVSDB_REMOTE=ptcp:6640
            OVSDB_FILE=/usr/local/etc/openvswitch/conf.db
            ;;
        ovn_nb)
            OVS_RUNDIR=${OVS_RUNDIR:-/var/run/ovn/}
            OVSDB_SOCKET=$OVS_RUNDIR/ovnnb_db.sock
            OVSDB_PIDFILE=$OVS_RUNDIR/ovnnb_db.pid
            OVSDB_BACKUP=${OVSDB_BACKUP:-${OVS_RUNDIR}/ovn_nb.db}
            OVSDB_REMOTE=ptcp:6641
            OVSDB_FILE=/usr/local/etc/openvswitch/ovn_nb.db
            ;;
        ovn_sb)
            OVS_RUNDIR=${OVS_RUNDIR:-/var/run/ovn/}
            OVSDB_SOCKET=$OVS_RUNDIR/ovnsb_db.sock
            OVSDB_PIDFILE=$OVS_RUNDIR/ovnsb_db.pid
            OVSDB_BACKUP=${OVSDB_BACKUP:-${OVS_RUNDIR}/ovn_sb.db}
            OVSDB_REMOTE=ptcp:6642
            OVSDB_FILE=/usr/local/etc/openvswitch/ovn_sb.db
            mkdir -p /etc/openvswitch
            ;;
        *)
            echo "Error: Unknown database type: $db_type"
            exit 1
            ;;
    esac
}

ovsdb() {
    local db_type=$1
    set_runtime_vars $db_type
    do_ovsdb
}

do_ovsdb() {
  echo "=============== ovsdb-server ==============="
  echo "OVSDB_BACKUP=$OVSDB_BACKUP"

  if [ -f ${OVSDB_BACKUP} ]; then
          echo "Using backup DB file at $OVSDB_BACKUP"

          echo "Making a standalone DB if needed"
          ovsdb-tool cluster-to-standalone $OVSDB_FILE $OVSDB_BACKUP || cp $OVSDB_BACKUP $OVSDB_FILE
          echo "Compacting DB"
          ovsdb-tool compact $OVSDB_FILE
  else
          echo "Creating new DB"
          ovsdb-tool create $OVSDB_FILE  /usr/local/share/openvswitch/vswitch.ovsschema
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

  ovsdb-server ${user_opt-} --remote=punix:${OVSDB_SOCKET} --remote=${OVSDB_REMOTE} --pidfile=${OVSDB_PIDFILE} $OVSDB_FILE

}
cmd=${1:-""}
case ${cmd} in
"vswitchd-dummy")
  vswitchd-dummy
  ;;
"ovsdb-ovs")
  ovsdb ovs
  ;;
"ovsdb-ovn_nb")
  ovsdb ovn_nb
  ;;
"ovsdb-ovn_sb")
  ovsdb ovn_sb
  ;;
"sleep")
  sleep infinity 
  ;;
"*")
  echo "Command not supported: ${cmd}"
  exit 1
esac
