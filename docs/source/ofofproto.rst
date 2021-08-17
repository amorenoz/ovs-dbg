======================
(PoC) offline-dbg
======================

The offline-dbg tool helps you debug OVS issues offline by recreating the OVSDB
and the Openflow flows from a remote Kubernetes / Openshift node running ovn-kubernetes

------
Usage
------

Build the ovs-dbg container:

::
    cd containers/ovs-dbg && docker build -t ovs-dbg .


or download it from the registry:

::
    docker pull quay.io/amorenoz/ovs-dbg


Make sure you can access the remote k8s/oc node:

::
    kubectl get nodes


Start the offline debugging setup by selecting the NODE you want to debug:

::
    ./bin/offline-dbg start ovn-worker


To clean the setup run:

::
    ./bin/offline-dbg stop


------------
Requirements
------------


- docker
