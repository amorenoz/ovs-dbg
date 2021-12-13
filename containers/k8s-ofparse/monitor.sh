#!/bin/bash

set -mx

BRIDGE="br-int" # TODO other bridges
PORT=16640
BASE_DIR=/tmp/k8s-ofparse

client_stop() {
  echo "=============== k8-ovs-flowparse client stop ==============="
  ovs-vsctl del-controller $BRIDGE
}

client_start() {
  echo "=============== k8-ovs-flowparse client start ==============="
  ovs-vsctl set-controller $BRIDGE ptcp:$PORT
  exec sleep infinity
}

# Returns the filename where a node's flows shall be synchronized
_filename() {
    local node=$1
    echo ${BASE_DIR}/${node}.flows
}

monitor() {
  echo "=============== k8-ovs-flowparse monitor start ==============="
    mkdir -p ${BASE_DIR}
    declare -A nodes
    local ofparse_args=""
    for node in $(kubectl get nodes -o name); do
        node_name=${node#"node/"}
        file=$(_filename ${node_name})
        ip=$(kubectl get ${node} -o json | jq -r '.status.addresses[] | select(.type == "InternalIP") | .address')
        nodes[${node_name}]=${ip}
        ofparse_args="$ofparse_args -i ${node_name},${file}"
    done

    cat > /usr/local/bin/k8s-ovs-ofparse <<EOF
#!/bin/bash

OFPARSE_ARGS="$ofparse_args"
exec ovs-ofparse \$OFPARSE_ARGS "\$@"
EOF
    chmod +x /usr/local/bin/k8s-ovs-ofparse

    cat > /etc/motd <<EOF
==============================
        k8s-ovs-ofparse
==============================

The flows from the following nodes are being synchronized into files ({Node Name} ==> {File Path}):

EOF

    for node in "${!nodes[@]}"; do
        echo " - ${node}  ==>  $(_filename ${node})" >> /etc/motd
    done
    cat >> /etc/motd <<EOF

You can use "ofparse -i {filename} ..." to look at any individual node
Also, you can use "k8s-ovs-ofparse ..." to look at all the nodes

Please report bugs or RFEs to https://github.com/amorenoz/ovs-dbg


EOF

    echo '[ ! -z "$TERM" -a -r /etc/motd ] && cat /etc/motd' >> /root/.bashrc
    echo 'export PAGER="less -r"' >> /root/.bashrc
    echo 'eval "$(ovs-dbg-complete)"' >> /root/.bashrc
    echo 'eval "complete -o nosort -F _ofparse_completion k8s-ovs-ofparse"' >> /root/.bashrc # apply same autocomplete to k8s-ofparse

    while sleep 15; do
        for node in "${!nodes[@]}"; do
            target="tcp:${nodes[$node]}:${PORT}"
            file=$(_filename ${node})
            ovs-ofctl dump-flows ${target} > ${file}.tmp
            if [ $? -eq 0 ]; then
                mv ${file}.tmp ${file}
                echo "$(date): Updated flows for node ${node}"
            else
                echo "ERROR ovs-ofctl fails for node $node"
            fi
        done
    done
}

cmd=${1:-""}
case ${cmd} in
"start")
  monitor
  ;;
"client_start")
  client_start
  ;;
"client_stop")
  client_stop
  ;;
"*")
  echo "Command not supported: ${cmd}"
  exit 1
esac
