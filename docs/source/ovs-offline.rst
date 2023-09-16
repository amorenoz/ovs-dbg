===============================================================
ovs-offline: Spin up OvS and OVN daemons for offline debugging
===============================================================

The **ovs-offline** tool helps you debug OVS issues offline by recreating the OVSDB and the OpenFlow flows.

------
Usage
------

In general, the tool works in two steps. First you must **collect** the logs, flows etc, and then you **start** the offline debugging environment

.. admonition:: Optional
    
    Build the ovs-dbg container. You can choose to specify the ovs-repo and commit to pull the ovs source code from using the ``-r`` and ``-c`` flags respectively (or by setting the ``OVS_DBG_REPO`` and ``OVS_DBG_COMMIT`` env variables).

::

    ./bin/ovs-offline build -r https://github.com/my_repo/ovs.git -c branch-2.15


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

    ./bin/ovs-offline collect-db-ovn-sb /path/to/ovnsb_db.db


Collect data from a sos report archive
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Note collecting OVS information from sos archives requires a recent sos package.

::

    ./bin/ovs-offline collect-sos-ovs /path/to/sos_compute.tar.xz

::

    ./bin/ovs-offline collect-sos-ovn /path/to/sos_controller.tar.xz

.. admonition:: Optional
    
    For OVS, if running an older version of the sos package and encountering errors, you can start the server (start-the-setup_) early, and source the virtual env.
    After that, run the ``./bin/ovs-offline collect-sos-ovs /path/to/sos_compute.tar.xz`` to collect the required files to import the OpenFlows.


Start the setup
^^^^^^^^^^^^^^^

::

    ./bin/ovs-offline start


Once you start, the tool will print the commands that are available for offline debugging.

You can run OVS/OVN commands directly on your offline environment by sourcing the generated script.

.. admonition:: Optional
    
    ovs-offline works with both docker (default) and podman containers. It will automatically detect which is available on your system. To override the default behavior and run with podman containers, use the ``-p`` option.

::

    source /tmp/ovs-offline/bin/activate

Stop and clean the setup
^^^^^^^^^^^^^^^^^^^^^^^^

::

    ovs-offline-deactivate
    ./bin/ovs-offline stop


------------
Requirements
------------


- docker or podman
