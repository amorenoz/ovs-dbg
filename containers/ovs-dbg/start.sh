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

ovn-sb() {
  OVS_OFFLINE_VAR_RUN=${OVS_OFFLINE_VAR_RUN:-/var/run/ovn/}
  OVSDB_SOCKET=$OVS_OFFLINE_VAR_RUN/ovnsb_db.sock
  OVSDB_PIDFILE=$OVS_OFFLINE_VAR_RUN/ovnsb_db.pid
  #OVSDB_CTRL_SOCK=$OVS_OFFLINE_VAR_RUN/ovnsb_db.ctl
  OVSDB_BACKUP=${OVSDB_BACKUP:-${OVS_OFFLINE_VAR_RUN}/ovn_sb.db}
  OVSDB_REMOTE=ptcp:6642
  OVSDB_FILE=/usr/local/etc/openvswitch/ovn_sb.db
  mkdir -p /etc/openvswitch

  do_ovsdb
}

ovn-nb() {
  OVS_OFFLINE_VAR_RUN=${OVS_OFFLINE_VAR_RUN:-/var/run/ovn/}
  OVSDB_SOCKET=$OVS_OFFLINE_VAR_RUN/ovnnb_db.sock
  OVSDB_PIDFILE=$OVS_OFFLINE_VAR_RUN/ovnnb_db.pid
  #OVSDB_CTRL_SOCK=$OVS_OFFLINE_VAR_RUN/ovnnb_db.ctl
  OVSDB_BACKUP=${OVSDB_BACKUP:-${OVS_OFFLINE_VAR_RUN}/ovn_nb.db}
  OVSDB_REMOTE=ptcp:6641
  OVSDB_FILE=/usr/local/etc/openvswitch/ovn_nb.db

  do_ovsdb
}

ovsdb() {
  OVS_OFFLINE_VAR_RUN=${OVS_OFFLINE_VAR_RUN:-/usr/local/var/run/openvswitch/}
  OVSDB_SOCKET=$OVS_OFFLINE_VAR_RUN/db.sock
  OVSDB_PIDFILE=$OVS_OFFLINE_VAR_RUN/ovsdb-server.pid
  #OVSDB_CTRL_SOCK=$OVS_OFFLINE_VAR_RUN/ovnnb_db.ctl
  OVSDB_BACKUP=${OVSDB_BACKUP:-${OVS_OFFLINE_VAR_RUN}/conf.db}
  OVSDB_REMOTE=ptcp:6640
  OVSDB_FILE=/usr/local/etc/openvswitch/conf.db

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
  ovsdb
  ;;
"ovsdb-ovn_nb")
  ovn-nb
  ;;
"ovsdb-ovn_sb")
  ovn-sb
  ;;
"sleep")
  sleep infinity 
  ;;
"*")
  echo "Command not supported: ${cmd}"
  exit 1
esac
