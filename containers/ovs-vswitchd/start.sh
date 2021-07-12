#!/bin/bash

set -mex

ovs-vswitchd --enable-dummy=override -vvconn -vnetdev_dummy  --no-chdir --pidfile  -vsyslog:off &

sleep 5

if [ -d "$RESTORE_DIR" ]; then
    echo "Restoring flows"
    for file in $(ls -x $RESTORE_DIR/*flows.dump); do
        # fix igmp flows
        sed -i 's/igmp,/ip,nw_proto=2,/g' $file
    done
    # do not remove directory
    sed -i '/rm.*/d' $RESTORE_DIR/restore.sh

    sh -e $RESTORE_DIR/restore.sh
fi

fg 

