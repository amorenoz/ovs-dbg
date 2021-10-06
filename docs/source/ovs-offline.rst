===============================================================
ovs-offline: Spin up OvS and OVN daemons for offline debugging
===============================================================

The **ovs-offline** tool helps you debug OVS issues offline by recreating the OVSDB and the Openflow flows.

------
Usage
------

In general, the tool work in two steps. First you must **collect** the logs, flows etc, and then you **start** the offline debugging environment

(Optional) Build the ovs-dbg container:

::

    ./bin/ovs-offline build


Collect data from a running kubernetes / Openshift cluster
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Make sure you can access the remote k8s/oc node:

::

    kubectl get nodes


Select the NODE you want to "recreate" and run:

::

    ./bin/ovs-offline collect-k8s ovn-worker



Collect data from a Database backup file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

    ./bin/ovs-offline collect-db-ovs /path/to/openvswitch/conf.db


You can also collect OVN NB and OVN SB databases:

::

    ./bin/ovs-offline collect-db-ovn-nb /path/to/ovnnb_db.db


::

    ./bin/ovs-offline collect-db-ovn-nb /path/to/ovnsb_db.db


Collect data from a sos report archive
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Note collecting OVS information from sos archives requires a recent sos package.

::

    ./bin/ovs-offline collect-sos-ovs /path/to/sos_compute.tar.xz

::

    ./bin/ovs-offline collect-sos-ovn /path/to/sos_controller.tar.xz



Start the setup
^^^^^^^^^^^^^^^

::

    ./bin/ovs-offline start


Once you start, the tool will print the commands that are available for offline debugging.


Stop and clean the setup
^^^^^^^^^^^^^^^^^^^^^^^^

::

    ./bin/ovs-offline stop


------------
Requirements
------------


- docker