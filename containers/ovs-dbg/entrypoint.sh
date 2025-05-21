#!/bin/bash

function build_ovsdb_mon() {
	echo "======= Building ovsdb-mon ======= "
	## From https://github.com/amorenoz/ovsdb-mon/blob/main/dist/entrypoint.sh
	pushd ovsdb-mon

	declare -A db_schemas=( ["OVN_Northbound"]="ovnnb_db.sock" ["OVN_Southbound"]="ovnsb_db.sock" ["Open_vSwitch"]="db.sock")

	declare -a ovs_runpaths=("/run/openvswitch" \
	                         "/var/run/openvswitch" \
	                         "/run/ovn" \
	                         "/run/ovn-ic" \
	                         "/var/lib/ovn/" \
	                         "/var/lib/ovn-ic/" \
	                         "/var/lib/openvswitch/ovn" \
	                         "/var/lib/openvswitch/ovn-ic")

	for k in "${!db_schemas[@]}"; do
	    for path in "${ovs_runpaths[@]}"; do if [ -e "${path}/${db_schemas[${k}]}" ]; then
	            ovsdb-client get-schema "unix:${path}/${db_schemas[${k}]}" ${k} > ${k}.schema
	            SCHEMA=${k}.schema make build
	            mv -v ./bin/ovsdb-mon /usr/local/bin/bin-ovsdb-mon.${k}
	            cat >/usr/local/bin/ovsdb-mon.${k} <<EOF
#!/bin/sh
/usr/local/bin/bin-ovsdb-mon.${k} -db "unix:${path}/${db_schemas[${k}]}" \$@
EOF
	            chmod +x /usr/local/bin/ovsdb-mon.${k}
	            break
	        fi
	    done
	done
	touch /tmp/build_finished
	popd
	echo "======= Done building ovsdb-mon ======= "
}

# Mount Kernel debugfs (needed by bcc and tracing)
mount -t debugfs none /sys/kernel/debug/
build_ovsdb_mon

if [ "$#" -eq 0 ]; then
        cat /etc/motd
	exec "/bin/bash"
else
	exec "$@"
fi
