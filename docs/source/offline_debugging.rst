=================================
ovs-offline Debugging Tutorial
=================================

ovs-offline is a script that automates the process of locally recreating the ovsdb-servers, and vswitchd from a running OVS. This provides the benefit of running commands such as ovs-appctl, ovs-vsctl, ovn-nbctl, ovn-sbctl, ovsdb-client, and ovs-ofctl without needing direct access to the OVS/OVN cluster in question.

ovs-offline works by collecting the necessary flows and database files from a live environment, and using this information to configure containers running the ovsdb-server, ovn-nb/sb, and vswitchd.

Data can be collected directly from a kubernetes or OpenShift cluster running OVS/OVN or from an SOS report gathered from an OpenStack, OpenShift, Kubernetes, or standalone OVS environment. If needed, data can also be collected manually, and then automatically used to configure the replica environment. 

This tutorial demonstrates how to obtain the information needed and recreate offline environments using all of these methods. It also covers some basic debugging tactics in OVS and OVN that can be implemented in an offline environment.

*****************************
Recreating an Offline Replica
*****************************

Essentially, ovs-offline works in two steps. The first is to run 'ovs-offline collect*' specifying either 'collect-k8s' or 'collect-sos-[ovs/ovn]'.
This will collect all necessary logs, flows, etc in your $WORKDIR.
If using an sos-report, you will likely want to run both 'collect-sos-ovs' and 'collect-sos-ovn' to gather all the necessary files from a worker and controller node respectively.

The second step is to run ovs-offline start which will build the containers using the collected files.
You can view the commands available on your running set up at any time with 'ovs-offline show'.

Finally, when finished, run 'ovs-offline stop' to tear down the containers, and clean up the $WORKDIR.

ovs-offline can be run either by installing ovs-dbg or calling the script directly from git checkout. Installation instructions can be found here: https://github.com/amorenoz/ovs-dbg/blob/main/README.md.

Kubernetes/OpenShift
^^^^^^^^^^^^^^^^^^^^

The first step is to verify you can access the remote cluster, and determine the Kubernetes or Openshift node to collect the flow and database information from. In the case of a Kubernetes cluster, kubectl will provide a list of nodes to select from.

::

    $ kubectl get nodes
    NAME                STATUS   ROLES                  AGE   VERSION
    ovn-control-plane   Ready    control-plane,master   74m   v1.20.0
    ovn-worker          Ready    <none>                 73m   v1.20.0
    ovn-worker2         Ready    <none>                 73m   v1.20.0


For OpenShift use oc:

::

    $ oc get nodes

You can now run ovs-offline using collect-k8s and specifying the node to collect information from.

::

    $ ./bin/ovs-offline collect-k8s ovn-worker


    Offline OVS Debugging: data collected and stored in /tmp/ovs-offline
    **********************


For OpenShift environments, you must specify OCP using the -o option.

::

    $ ./bin/ovs-offline collect-k8s ovn-worker -o

The script will automatically run the OVS script ovs-save in the specified node to dump all the required flows from each OVS bridge, as well as generate a modified ovs-save script which will be used to restore the flows in the local replica. It will also create a local copy of OVS db.conf, ovnnb_db.db, ovnsb_db.db.

You can verify these files have been collected by looking in the working directory, which by default is set to /tmp/ovs-offline (You can also change the working directory using the -w option, or setting the OVS_DBG_WORKDIR env var)

::

    $ ls /tmp/ovs-offline/
    db  ovnkube-node-flqhc_ovs.db  ovnnb_db.db  ovnsb_db.db  restore_flows  var-run
    $ ls /tmp/ovs-offline/restore_flows/
    breth0.flows.dump  breth0.groups.dump  br-int.flows.dump  br-int.groups.dump  do_restore.sh  restore.sh

There is a chance you will see an error message indicating that the database file conf.db was not found in the expected locations. In this case, you can locate and collect the database manually: :ref:`manually_recreate_label-name`

The final step is to run ovs-offline start, which will spin up your local set up in containers and configure them using the files that have been collected.

::

    $ ./bin/ovs-offline start
    Starting container ovsdb-server-ovn_nb
    7c73c7c146f20503d63670127f0723125cb52103ef6aaf311fa6fe8774447c23
    Starting container ovsdb-server-ovn_sb
    7ffab93d6422e9c0a164fe5a564595061b5b8f760316d8984a7a42cf57978dc0
    Starting container ovsdb-server-ovs
    f7a0855addf562c82d0d4cc9fedb7f7b0e7e5bfa8e14fa2134318e4f75a4dbe0
    Starting container ovs-vswitchd
    a5c8a4cef90132b9c1057d9c859e5d0f722437edd3ab0809ce9dfbb2f845a42c

    Offline OVS Debugging started
    ******************************

You will see a list of commands that are available to run on your set up. You can print these again at any time using 'ovs-offline show'.

::

    Offline OVS Debugging started
    ******************************

    Working directory: /tmp/ovs-offline:

    * openvswitch control found at /tmp/ovs-offline/var-run/ovs/ovs-vswitchd.9.ctl
    You can run ovs-appctl commands as:
        ovs-appctl --target=/tmp/ovs-offline/var-run/ovs/ovs-vswitchd.9.ctl [...]

    * ovs ovsdb-server socket found at /tmp/ovs-offline/var-run/ovs/db.sock
    You can run commands such as:
        ovs-vsctl --db unix:/tmp/ovs-offline/var-run/ovs/db.sock [...]
    or
        ovsdb-client [...] --db unix:/tmp/ovs-offline/var-run/ovs/db.sock

    * ovn_nb ovsdb-server socket found at /tmp/ovs-offline/var-run/ovn_nb/db.sock
    You can run commands such as:
        ovn-nbctl --db unix:/tmp/ovs-offline/var-run/ovn_nb/db.sock [...]
    or
        ovsdb-client [...] --db unix:/tmp/ovs-offline/var-run/ovn_nb/db.sock

    * ovn_sb ovsdb-server socket found at /tmp/ovs-offline/var-run/ovn_sb/db.sock
    You can run commands such as:
        ovn-sbctl --db unix:/tmp/ovs-offline/var-run/ovn_sb/db.sock [...]
    or
        ovsdb-client [...] --db unix:/tmp/ovs-offline/var-run/ovn_sb/db.sock

    * openflow bridge management sockets found at /tmp/ovs-offline/var-run/ovs/breth0.mgmt
    /tmp/ovs-offline/var-run/ovs/br-int.mgmt
    You can run ofproto commands such as:
        ovs-ofctl [...] /tmp/ovs-offline/var-run/ovs/breth0.mgmt
        ovs-ofctl [...] /tmp/ovs-offline/var-run/ovs/br-int.mgmt
    
    * You can also run offline commands directly with the following:
        source /tmp/ovs-offline/bin/activate

You are now able to run the provided commands locally. 

Optionally, you can source the script /tmp/ovs-offline/bin/activate, which will set a series on environment variables to allow you to run OVS and OVN commands directly.

::

    $ source /tmp/ovs-offline/bin/activate
    * You can now run the following offline commands directly:
        ovs-appctl [...]

        ovs-vsctl [...]
        ovsdb-client [...]  

        ovn-nbctl [...]
        ovsdb-client [...] $OVN_NB_DB 

        ovn-sbctl [...]
        ovsdb-client [...] $OVN_SB_DB 

        ovs-ofctl [...] [bridge]
    * You can restore your previous environment with: 
        deactivate
    (ovs-offline) $


You can stop and clean up your set up using:

::

    (ovs-offline) $ deactivate
    $ ./bin/ovs-offline stop
    Offline OVS Debugging stopped
    *****************************


OpenShift (Sos report)
^^^^^^^^^^^^^^^^^^^^^^

OVS/OVN running in an OpenShift environment can also be recreated using the information gathered by the sos-report_. This will detail how to both run the sos report in OCP and create the offline debugging environemnt, using a live OpenShift cluster with OVN-Kubernetes CNI.

The process of generating the sos report in OCP is also well documentented here: https://access.redhat.com/solutions/4387261

From your local machine, determine the nodes in your OCP cluster.

::

    $ ./oc get nodes
    NAME                                              STATUS   ROLES    AGE     VERSION
    master-0.4sdaniele2.lab.upshift.rdu2.redhat.com   Ready    master   3d20h   v1.21.1+9807387
    master-1.4sdaniele2.lab.upshift.rdu2.redhat.com   Ready    master   3d20h   v1.21.1+9807387
    master-2.4sdaniele2.lab.upshift.rdu2.redhat.com   Ready    master   3d20h   v1.21.1+9807387
    worker-0.4sdaniele2.lab.upshift.rdu2.redhat.com   Ready    worker   3d19h   v1.21.1+9807387
    worker-1.4sdaniele2.lab.upshift.rdu2.redhat.com   Ready    worker   3d19h   v1.21.1+9807387
    worker-2.4sdaniele2.lab.upshift.rdu2.redhat.com   Ready    worker   3d19h   v1.21.1+9807387

Select a node to debug and create a debug session. This will start a debug pod using the image registry.redhat.io/rhel8/support-tools.

* **Note** To collect both OVS and OVN information you will need to repeat the following process on both a worker and master node

::

    $ ./oc debug node/master-0.4sdaniele2.lab.upshift.rdu2.redhat.com
    Starting pod/master-04sdaniele2labupshiftrdu2redhatcom-debug ...
    To use host binaries, run `chroot /host`
    Pod IP: 10.0.88.193
    If you don't see a command prompt, try pressing enter.
    sh-4.4#

Once in the debug session, you can use chroot to change the apparent root directory to the one of the underlying host:

::

    sh-4.4# chroot /host

At this point, you will use the ‘toolbox’ command to generate a special container with the sos binary.

::

    sh-4.4# toolbox
    Trying to pull registry.redhat.io/rhel8/support-tools...Getting image source signatures
    Copying blob fd8daf2668d1 done
    Copying blob 1457434f891b done
    Copying blob cb3c77f9bdd8 done
    Copying config 517597590f done
    Writing manifest to image destination
    Storing signatures
    517597590ff4236b0e5e3efce75d88b2b238c19a58903f59a018fc4a40cd6cce
    Spawning a container 'toolbox-' with image 'registry.redhat.io/rhel8/support-tools'
    Detected RUN label in the container image. Using that as the default...
    command: podman run -it --name toolbox- --privileged --ipc=host --net=host --pid=host -e HOST=/host -e NAME=toolbox- -e IMAGE=registry.redhat.io/rhel8/support-tools:latest -v /run:/run -v /var/log:/var/log -v /etc/machine-id:/etc/machine-id -v /etc/localtime:/etc/localtime -v /:/host registry.redhat.io/rhel8/support-tools:latest
    [root@ip-10-0-132-143 /]#

* **Note**: this requires a recent update to RHEL support tools which includes sos 4.2. Older versions of the sos report will not collect the necessary OVS/OVN data. You can specify a custom support tools image with the necessary upgrades by adding the file /root/.toolboxrc with the following body:

::

    sh-4.4# cat /root/.toolboxrc
    REGISTRY=quay.io
    IMAGE=sdaniele/updated_support_tools_sos-4.2
    TOOLBOX_NAME=upgraded_support_tools

Then run toolbox to run support tools using the updated image.

::

    sh-4.4# toolbox
    .toolboxrc file detected, overriding defaults...
    Spawning a container 'sdaniele_support_tools' with image 'quay.io/sdaniele/updated_support_tools_sos-4.2'
    Detected RUN label in the container image. Using that as the default...

Once in your sos container, you can run the sos report. The -e flag is required to ensure OVN plugins are enabled and included in the report.

::

    [root@master-0 /]# sos report -e ovn_central -e ovn_host

    sosreport (version 4.2)

    This command will collect diagnostic and configuration information from
    this Red Hat CoreOS system.

    An archive containing the collected information will be generated in
    /host/var/tmp/sos.zjhkv5li and may be provided to a Red Hat support
    representative.

    [...]

    Finishing plugins              [Running: systemd]                                       n]
    Finished running plugins
    Creating compressed archive...

    Your sosreport has been generated and saved in:
        /host/var/tmp/sosreport-master-0-2021-10-12-pssdfxu.tar.xz

    Size        57.46MiB
    Owner       root
    sha256      bd82f731653ce3fd9b5c3a7cdf6bbd812689fa19fed882faaba71faf9a4e9f76

    Please send this file to your support representative.

The next step is to copy the archive back to your local host. One way to do this is using cat and output redirection. On your host machine, run the following, specifying the location of your sos archive provided in the output of the sos report.

::

    $ ./oc debug node/master-0.4sdaniele2.lab.upshift.rdu2.redhat.com -- cat /host/var/tmp/sosreport-master-0-2021-10-12-pssdfxu.tar.xz > /tmp/sosreport-master-0-2021-10-12-pssdfxu.tar.xz
    Starting pod/master-04sdaniele2labupshiftrdu2redhatcom-debug ...
    To use host binaries, run `chroot /host`

    Removing debug pod ...

Alternatively, you can copy the file from the host to your debug pod, and then copy the archive from the debug pod to your local system.

Exit the toolbox and return to the debug pod directory. Run the following:

::

    sh-4.4# cp /host/var/tmp/sosreport-master-0-2021-10-12-pssdfxu.tar.xz /var/tmp/

In a second terminal, copy the file locally:

::

    $ oc cp default/worker-0ovsofflinedemolabupshiftrdu2redhatcom-debug:/var/tmp/sosreport-master-0-2021-10-12-pssdfxu.tar.xz /tmp/sosreport-master-0-2021-10-12-pssdfxu.tar.xz


As previously mentioned, you should now repeat this process on a worker node as well.

Once you have the archive saved locally, you can collect all the necessary information directly from the archive using ovs-offline collect-sos-ovs/ovn </path/to/archive/archive.tar.xz>.
Specify the sos report gathered from your worker node for collect-sos-ovs, and your master node archive for collect-sos-ovn.

::

    $ ./ovs-offline collect-sos-ovs /tmp/sosreport-worker-0-2021-10-12-iguyder.tar.xz
    Extracting OVS data from sos report...


    Offline OVS Debugging: OVS data collected and stored in /tmp/ovs-offline
    *******************************************************************
    $ ./ovs-offline collect-sos-ovn /tmp/sosreport-master-0-2021-10-12-pssdfxu.tar.xz
    Extracting OVN data from sos report...


    Offline OVS Debugging: OVN data collected and stored in /tmp/ovs-offline
    *******************************************************************

Finally, you can run ‘ovs-offline start’ and your offline debugging environment will be up and running.

::

    $ ./ovs-offline start
    Starting container ovsdb-server-ovn_nb
    dbbac9153e61e8e5e7206c344ffafe269e18a02c682e1f2158d4c86edb6a8ac9
    Starting container ovsdb-server-ovn_sb
    610f045ce7234cbded75805e7b64fd2bfdd76edf30062561b1240391ce91c868
    Starting container ovsdb-server-ovs
    23a4d08bbe3d228dbe59b8c8234528167cc162ae3ca7e770e7976f2dc85629e9
    Starting container ovs-vswitchd
    a8a8239978703fe5d413e8c2b7949ebeb8226a9e63272977ff3a637a9be60a1d

    Offline OVS Debugging started
    ******************************

    [...]

As previously mentioned, you can run source /tmp/ovs-offline/bin/activate to call OVS / OVN utilities directly rather than having to specify the sock/mgmt/ctl files

::

    $ source /tmp/ovs-offline/bin/activate
    * You can now run the following offline commands directly:
        ovs-appctl [...]

        ovs-vsctl [...]
        ovsdb-client [...]  

        ovn-nbctl [...]
        ovsdb-client [...] $OVN_NB_DB 

        ovn-sbctl [...]
        ovsdb-client [...] $OVN_SB_DB 

        ovs-ofctl [...] [bridge]
    * You can restore your previous environment with: 
        deactivate
    (ovs-offline) $


Stop and clean up your set up using:

::

    (ovs-offline) $ deactivate
    $ ./bin/ovs-offline stop
    Offline OVS Debugging stopped
    *****************************


OpenStack (Sos Report)
^^^^^^^^^^^^^^^^^^^^^^

ovs-offline can also be run using the information gathered from the sos-report_. 

From within your live OpenStack environment, you will need to access a both a controller node (for OVN data) and compute node (for OVS data).

We will start by gathering data from a controller node.

First ssh into you OpenStack cluster. From here you will need to ssh into the target controller node.

Once inside the controller node, create a container running rhel-support-tools_ (a suite of tools to analyse the host system).
At the time of writing this tutorial, the necessary sos changes have not been added to RHEL support tools, so a temporary local repo is used instead: https://quay.io/repository/sdaniele/updated_support_tools_sos-4.2.

In order for the container to run OVS and OVN commands on the host system, the following options will need to be set to mount the container to the host.

::

    $ sudo podman run --privileged --net=host --pid=host -e HOST=/host -v /run:/run -v /var/log:/var/log -v /etc/localtime:/etc/localtime -v /:/host -it quay.io/sdaniele/updated_support_tools_sos-4.2 sh
    Trying to pull quay.io/sdaniele/updated_support_tools_sos-4.2...
    Getting image source signatures
    Copying blob 06038631a24a done
    Copying blob 262268b65bd5 done
    Copying blob a5c763da2f9a done
    Copying blob d195a865bebf done
    Copying blob 6b99e62412cb done
    Copying blob 2bdb97aa069b done
    Copying config 02bab40ca5 done
    Writing manifest to image destination
    Storing signatures
    WARNING: The same type, major and minor should not be used for multiple devices.
    WARNING: The same type, major and minor should not be used for multiple devices.
    WARNING: The same type, major and minor should not be used for multiple devices.
    sh-4.4# 


Once you are inside the support tools container, run the sos report (4.2) with ovn_central and ovn_host explicitly enabled.

::

    sh-4.4# sos report -e ovn_central -e ovn_host 

    sosreport (version 4.2)

    This command will collect diagnostic and configuration information from
    this Red Hat Enterprise Linux system and installed applications.

    An archive containing the collected information will be generated in
    /host/var/tmp/sos.j_jl2ke_ and may be provided to a Red Hat support
    representative.
    [...]

Once complete, the sos report should specify the location of the <sos_report>.tar.xz file on the host system.

::

    [...]
     Running plugins. Please wait ...

        Finishing plugins              [Running: systemd]                                       ]]r]]witch]ove]leo]ent]
        Finished running plugins                                                               
        Creating compressed archive...

        Your sosreport has been generated and saved in:
            /host/var/tmp/sosreport-controller-2-2021-10-13-zveckho.tar.xz

        Size	32.63MiB
        Owner	root
        sha256	95db023ff8a031c284ff3c8c698fdaf2dda6743e5f41eaa883e5c107aa1a2228

        Please send this file to your support representative.

Use scp or some other method to copy the archive file to your local system.

Now repeat this process on a compute node in your set up.

On your local system, you will be able to gather the necessary information directly from the sos archives using collect-sos-ovs (compute node)and collect-sos-ovn(controller node).

::

    $ ./ovs-offline collect-sos-ovs /local/var/tmp/sosreport-compute-2-2021-10-13-ghresdq.tar.xz 
    Extracting OVS data from sos report...


    Offline OVS Debugging: OVS data collected and stored in /tmp/ovs-offline
    *******************************************************************
    $ ./ovs-offline collect-sos-ovn /local/var/tmp/sosreport-controller-2-2021-10-13-zveckho.tar.xz
    Extracting OVN data from sos report...


    Offline OVS Debugging: OVN data collected and stored in /tmp/ovs-offline
    *******************************************************************


There is a small chance that collect-sos-ovs and collect-sos-ovn could fail to locate the database files if they are somewhere other than the default locations. In this event you can manually add a database file: :ref:`manually_recreate_label-name`.

Now you can spin up your set-up using ovs-offline start.

::

    $ ./bin/ovs-offline start
    ./ovs-offline start
    Starting container ovsdb-server-ovn_nb
    d72f407ba3b983a4bde2ca9df26dfcacc858ae9e3c12209da86d2ea87eb0c359
    Starting container ovsdb-server-ovn_sb
    de64abf0d1f8209825a230f94be5c3151bd2f7043d2c8d71ed9cb7e1279ed6c5
    Starting container ovsdb-server-ovs
    ce5a1a19b22736dda67c0fff1c5edda4151b2c78f7d6a03c0d811a7fd1ccef2b
    Starting container ovs-vswitchd
    d927482307724e921815753151a2578c1f0b2cca957f07f4c0639ab29a43e733

    Offline OVS Debugging started
    ******************************

    Working directory: /tmp/ovs-offline:

    * openvswitch control found at /tmp/ovs-offline/var-run/ovs/ovs-vswitchd.9.ctl
    You can run ovs-appctl commands as:
        ovs-appctl --target=/tmp/ovs-offline/var-run/ovs/ovs-vswitchd.9.ctl [...]

    * ovs ovsdb-server socket found at /tmp/ovs-offline/var-run/ovs/db.sock
    You can run commands such as:
        ovs-vsctl --db unix:/tmp/ovs-offline/var-run/ovs/db.sock [...]
    or
        ovsdb-client [...] --db unix:/tmp/ovs-offline/var-run/ovs/db.sock

    * ovn_nb ovsdb-server socket found at /tmp/ovs-offline/var-run/ovn_nb/db.sock
    You can run commands such as:
        ovn-nbctl --db unix:/tmp/ovs-offline/var-run/ovn_nb/db.sock [...]
    or
        ovsdb-client [...] --db unix:/tmp/ovs-offline/var-run/ovn_nb/db.sock

    * ovn_sb ovsdb-server socket found at /tmp/ovs-offline/var-run/ovn_sb/db.sock
    You can run commands such as:
        ovn-sbctl --db unix:/tmp/ovs-offline/var-run/ovn_sb/db.sock [...]
    or
        ovsdb-client [...] --db unix:/tmp/ovs-offline/var-run/ovn_sb/db.sock

    * openflow bridge management sockets found at /tmp/ovs-offline/var-run/ovs/br-data.mgmt
    /tmp/ovs-offline/var-run/ovs/br-int.mgmt
    You can run ofproto commands such as:
        ovs-ofctl [...] /tmp/ovs-offline/var-run/ovs/br-data.mgmt
        ovs-ofctl [...] /tmp/ovs-offline/var-run/ovs/br-int.mgmt


You are now able to run the provided commands locally.

As previously mentioned, you can run source /tmp/ovs-offline/bin/activate to call OVS / OVN utilities directly.

::

    $ source /tmp/ovs-offline/bin/activate
    * You can now run the following offline commands directly:
        ovs-appctl [...]

        ovs-vsctl [...]
        ovsdb-client [...]  

        ovn-nbctl [...]
        ovsdb-client [...] $OVN_NB_DB 

        ovn-sbctl [...]
        ovsdb-client [...] $OVN_SB_DB 

        ovs-ofctl [...] [bridge]
    * You can restore your previous environment with: 
        deactivate
    (ovs-offline) $


Stop and clean up your set up using:

::

    (ovs-offline) $ deactivate
    $ ./bin/ovs-offline stop
    Offline OVS Debugging stopped
    *****************************

    


.. _manually_recreate_label-name:

Manually Recreating an Environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In the event you encounter some error while collecting the data from an OVS/OVN environment, aren't able to access the latest update to the sos report, or need to manually add some files such as OVS/OVN database files, you can still collect the necessary data manually and use ovs-offline to automate spinning up a local set-up.

For the purpose of this tutorial, we will replicate an OVN_Kubernetes_ (KIND) set up, however you should be able to complete these steps regardless of whether you are working in a k8/OCP node, OpenStack vm, or requesting information from a 3rd party's environment.

To start, we will set the local ${WORKDIR} environment variable to make sure we are saving our extracted data to the same directory that will be used to spin up the ovsdb, ovndb, and vswitchd containers.

::

    $ WORKDIR=/tmp/ovs-offline
    $ mkdir $WORKDIR

We will also create sub-directories to store our extracted data, as well as the control, socket, and .mgmt files for our future running set up.

::

    $ mkdir ${WORKDIR}/restore_flows
    $ VAR_RUN=${WORKDIR}/var-run
    $ mkdir $VAR_RUN


We will need to collect the flow dumps, group dumps, and tlv map from each bridge in the target environment. Start by collecting a list of each bridge. Enter into the OVS node or use kubectl/oc exec if applicable, and run the following:

::

    $ kubectl get pods -n ovn-kubernetes -o wide
    
    NAME                              READY   STATUS    RESTARTS   AGE   IP           NODE                ...
    ovnkube-db-7455b798b7-zxb7m       2/2     Running   0          46m   172.18.0.2   ovn-control-plane   ...
    ovnkube-master-85567b87f7-f2sbs   3/3     Running   0          46m   172.18.0.2   ovn-control-plane   ...
    ovnkube-node-fs94v                3/3     Running   0          46m   172.18.0.2   ovn-control-plane   ...
    ovnkube-node-gw4nx                3/3     Running   0          46m   172.18.0.4   ovn-worker          ...
    ovnkube-node-qj45v                3/3     Running   0          46m   172.18.0.3   ovn-worker2         ...
    ovs-node-dsrc9                    1/1     Running   0          46m   172.18.0.3   ovn-worker2         ...
    ovs-node-f74f2                    1/1     Running   0          46m   172.18.0.2   ovn-control-plane   ...
    ovs-node-xx9b7                    1/1     Running   0          46m   172.18.0.4   ovn-worker          ...

    $ bridges=$(kubectl exec -n ovn-kubernetes ovnkube-node-gw4nx -- ovs-vsctl -- --real list-br)
    $ echo $bridges


Next we will use a built-in script in OVS called ovs-save.

ovs-save:

- Saves the flows and groups for each bridge into a .dump file in /tmp/ovs-save.<save_id>/<bridge_name>.flows.dump and /tmp/ovs-save.<save_id>/<bridge_name>.groups.dump respectively
- Outputs a script which restores OVS using the dumped data

We will first run the script and pipe the output to a new script 'do_restore.sh' which will allow our offline replica to restore OVS. We will then copy the .dump files generated in the live OVS environment to our local environment. Finally, we will add a small workaround script to allow the offline replica to use the default restore script generated by ovs-save.

* **Note**. If you are completing this step manually from an sos-report or information provided by a client rather than running the script, take a look at the ovs-save script, as it contains additional processing on the flow/group dumps that you may need to perform on your flows to restore them later. You will need to save the flow, group, and tlv map dumps for each bridge, as well as manually write a script called "restore.sh" to restore them.

Run ovs-save and pipe the output to a script called do_restore.sh

::

    $ kubectl exec -it -n ovn-kubernetes ovnkube-node-gw4nx -- sh -c "/usr/share/openvswitch/scripts/ovs-save save-flows $(echo $bridges | xargs) > /tmp/do_restore.sh"


You will then need to copy the resulting .dump files and restore.sh script from your OVS environment into your local working directory. We will also set the env variable SAVE_DIR locally to the name of the directory specified in do_restore.sh

::

    $ kubectl cp -n ovn-kubernetes ovnkube-node-gw4nx:/tmp/do_restore.sh /$WORKDIR/restore_flows/do_restore.sh
    $ SAVE_DIR=$(cat /$WORKDIR/restore_flows/do_restore.sh | awk '/replace/{print $6; exit}' | xargs dirname)
    $ kubectl cp -n ovn-kubernetes ovnkube-node-gw4nx:$SAVE_DIR. $WORKDIR/restore_flows
    $ echo $SAVE_DIR
    /tmp/ovs-save.<ovs-save_id>

do_restore.sh generated by ovs-save specifies directories in your live OVS environment to restore from. To work around this, create the file $WORKDIR/restore_flows/restore.sh and add the following lines:
::

    CURR_DIR=$(dirname $(realpath $0))
    ln -s $CURR_DIR /tmp/ovs-save.<your_ovs-save_id>
    sh $CURR_DIR/do_restore.sh


The only other data you need is the relevant OVS and OVN database files. These can be automatically prepared for offline debugging by copying locally, and then collecting with collect-db-<ovs/ovn>

::

    kubectl cp -n ovn-kubernetes ovnkube-node-gw4nx:path/to/ovs/conf.db /$WORKDIR/conf.db

Generally the OVS database file can be found in one of the following:

    - var/lib/openvswitch/conf.db
    - etc/openvswitch/conf.db
    - usr/local/etc/openvswitch/conf.db

Similarly, OVN database files should be found in one of the following:

    - /var/lib/openvswitch/ovn/
    - /usr/local/etc/openvswitch/
    - /etc/openvswitch/
    - /var/lib/openvswitch/

If the env variable $OVS_DBDIR is set, this will likely be the path to the OVS/OVN db files.

Alternatively, you can collect the ovs-db using ovsdb-client backup, although on a live environment this has the disadvantage of needing to interact with the running server.

::

    kubectl exec -i -n ovn-kubernetes ovnkube-node-gw4nx ovsdb-client backup > /$WORKDIR/conf.db

::

    $ ./bin/ovs-offline collect-db-ovs /local_path/to/openvswitch/conf.db
    $ ./bin/ovs-offline collect-db-ovn-nb /local_path/to/ovnnb_db.db
    $ ./bin/ovs-offline collect-db-ovn-sb /local_path/to/ovnsb_db.db

Once you have the flow and group dumps, do_restore.sh, restore.sh, and necessary db files properly collected in your $WORKDIR, you can spin up your OVS offline replica.

::

    $ ./bin/ovs-offline start
    Starting container ovsdb-server-ovs
    42b747f9e78d692bc382e14d475e7aaf4871003226360cc043dbdb6cf610425d
    Starting container ovs-vswitchd
    d46bb6438d6367a0e5b8c46fa1763a644fb398dc14325428e7de657a3f506659

    Offline OVS Debugging started
    ******************************

    Working directory: /tmp/ovs-offline:


You are now able to run the provided commands locally. You can stop and clean up your set up using:

::

    $ ./bin/ovs-offline stop
    Offline OVS Debugging stopped
    *****************************

    
*****************
Debugging Methods
*****************

The following outlines some basic debugging methods that can be used on your offline environment.

Basic OVS/OVN introspection
^^^^^^^^^^^^^^^^^^^^^^^^^^^

ovs-vsctl
=========

ovs-vsctl commands can be run offline by specifying the ovsdb-server socket using --db. This can provide a high-level interface to the ovs-vswitchd configuration database. See https://man7.org/linux/man-pages/man8/ovs-vsctl.8.html.

'ovs-vsctl show' provides an overview of the database contents, listing each bridge and its corresponding interface / ports.

::

    $ ovs-vsctl --db unix:/tmp/ovs-offline/var-run/ovs/db.sock show
    6e519ba3-1d89-456f-af61-8f0223dd9712
    Manager "ptcp:6640:127.0.0.1"
    Bridge br-int
        fail_mode: secure
        datapath_type: system
        Port ovn-ecf608-0
            Interface ovn-ecf608-0
                type: geneve
                options: {csum="true", key=flow, remote_ip="10.10.51.136"}
                bfd_status: {diagnostic="No Diagnostic", flap_count="0", forwarding="false", remote_diagnostic="No Diagnostic", remote_state=down, state=down}
        Port patch-br-int-to-provnet-df741617-6923-41e3-9ef6-075004808738
            Interface patch-br-int-to-provnet-df741617-6923-41e3-9ef6-075004808738
                type: patch
                options: {peer=patch-provnet-df741617-6923-41e3-9ef6-075004808738-to-br-int}
        Port enp4s0f1_2
            Interface enp4s0f1_2
        Port br-int
            Interface br-int
                type: internal
        Port tap555ce370-10
            Interface tap555ce370-10
    Bridge br-data
        [...]
    ovs_version: "2.15.1"


Similarly, 'ovs-vsctl list-br' will provide a compact list of all bridges, 'ovs-vsctl list-ports <bridge>' will list the ports, and 'ovs-vsctl list-ifaces <bridge>' will list the interfaces (typically 1 to 1 with the ports aside from bonds [ports with more than 1 interface])

::

    $ ovs-vsctl --db unix:/tmp/ovs-offline/var-run/ovs/db.sock list-br
    br-data
    br-int
    $ ovs-vsctl --db unix:/tmp/ovs-offline/var-run/ovs/db.sock list-ports br-int
    enp4s0f1_2
    ovn-ecf608-0
    patch-br-int-to-provnet-df741617-6923-41e3-9ef6-075004808738
    tap555ce370-10
    $ ovs-vsctl --db unix:/tmp/ovs-offline/var-run/ovs/db.sock list-ifaces br-int
    enp4s0f1_2
    ovn-ecf608-0
    patch-br-int-to-provnet-df741617-6923-41e3-9ef6-075004808738
    tap555ce370-10

'ovs-vsctl list interface' provides a detailed list of each interface and relavant information such as the ofport, mac address, ip, statistics, and more.

::

    $ ovs-vsctl --db unix:/tmp/ovs-offline/var-run/ovs/db.sock list interface
    2021-10-06T19:49:10Z|00001|ovsdb_idl|WARN|Interface table in Open_vSwitch database lacks ingress_policing_kpkts_burst column (database needs upgrade?)
    2021-10-06T19:49:10Z|00002|ovsdb_idl|WARN|Interface table in Open_vSwitch database lacks ingress_policing_kpkts_rate column (database needs upgrade?)
    _uuid               : 6c34abda-2d36-441a-926b-5956625190ae
    admin_state         : up
    bfd                 : {}
    bfd_status          : {}
    cfm_fault           : []
    cfm_fault_status    : []
    cfm_flap_count      : []
    cfm_health          : []
    cfm_mpid            : []
    cfm_remote_mpids    : []
    cfm_remote_opstate  : []
    duplex              : []
    error               : []
    external_ids        : {}
    ifindex             : 0
    ingress_policing_burst: 0
    ingress_policing_kpkts_burst: 0
    ingress_policing_kpkts_rate: 0
    ingress_policing_rate: 0
    lacp_current        : []
    link_resets         : 0
    link_speed          : []
    link_state          : up
    lldp                : {}
    mac                 : []
    mac_in_use          : "d6:60:d8:7a:76:cd"
    mtu                 : 1500
    mtu_request         : []
    name                : br-int
    ofport              : 65534
    ofport_request      : []
    options             : {}
    other_config        : {}
    statistics          : {rx_bytes=0, rx_custom_packets_1=0, rx_custom_packets_2=0, rx_packets=0, tx_bytes=0, tx_packets=0}
    status              : {}
    type                : internal

    _uuid               : ec943383-e7a3-4c0c-a386-2e904a876ab3
    [...]
    type                : ""

    _uuid               : 8ef68adb-fbee-4632-b132-ee05b9c987e3
    [...]
    mac_in_use          : "aa:55:aa:55:00:09"
    mtu                 : 1500
    mtu_request         : []
    name                : ovn-ecf608-0
    ofport              : 2
    ofport_request      : []
    options             : {csum="true", key=flow, remote_ip="10.10.51.136"}
    other_config        : {}
    statistics          : {rx_bytes=0, rx_custom_packets_1=0, rx_custom_packets_2=0, rx_packets=0, tx_bytes=144540, tx_packets=2190}
    status              : {}
    type                : geneve

    [...]

ovs-ofctl
=========

When you start your offline replica or run ovs-offline show, a list of management sockets will be created which allow for the use of ovs-ofctl.

::

    * openflow bridge management sockets found at /tmp/ovs-offline/var-run/ovs/br-data.mgmt
    /tmp/ovs-offline/var-run/ovs/br-int.mgmt
    You can run ofproto commands such as:
        ovs-ofctl [...] /tmp/ovs-offline/var-run/ovs/br-data.mgmt
        ovs-ofctl [...] /tmp/ovs-offline/var-run/ovs/br-int.mgmt

The ovs-ofctl program is a command line tool for monitoring and administering OpenFlow switches. It is able to show the current state of a switch, including features, configuration, and table entries

'ovs-ofctl dump-tables' can be useful for examining the consol statistics for each flow table used by the switch.

::

    $ ovs-ofctl dump-tables /tmp/ovs-offline/var-run/ovs/br-data.mgmt
    OFPST_TABLE reply (xid=0x2):
    table 0:
        active=1, lookup=0, matched=0
        max_entries=1000000
        matching:
        exact match or wildcard: in_port eth_{src,dst,type} vlan_{vid,pcp} ip_{src,dst} nw_{proto,tos} tcp_{src,dst}

    table 1:
        active=0, lookup=0, matched=0
        (same features)

    tables 2...253: ditto



'ovs-ofctl dump-flows' is one of the most useful tools for examining the OpenFlow pipeline in OVS. It will list all the flows for a given bridge.

::

    $ ovs-ofctl dump-flows /tmp/ovs-offline/var-run/ovs/br-int.mgmt
    cookie=0xc352b4c6, duration=115.399s, table=0, n_packets=0, n_bytes=0, priority=180,conj_id=100,in_port="patch-br-int-to",dl_vlan=405 actions=strip_vlan,load:0x5->NXM_NX_REG13[],load:0x1->NXM_NX_REG11[],load:0x4->NXM_NX_REG12[],load:0x2->OXM_OF_METADATA[],load:0x1->NXM_NX_REG14[],mod_dl_src:fa:16:3e:c1:0d:1a,resubmit(,8)
    cookie=0xc352b4c6, duration=115.399s, table=0, n_packets=0, n_bytes=0, priority=180,dl_vlan=405 actions=conjunction(100,2/2)
    cookie=0xb8c7cc70, duration=115.399s, table=0, n_packets=0, n_bytes=0, priority=150,in_port="patch-br-int-to",dl_vlan=405 actions=strip_vlan,load:0x5->NXM_NX_REG13[],load:0x1->NXM_NX_REG11[],load:0x4->NXM_NX_REG12[],load:0x2->OXM_OF_METADATA[],load:0x1->NXM_NX_REG14[],resubmit(,8)
    [...]

Additionally, a flow can be specified to print only flows containing that value.

::

    $ ovs-ofctl dump-flows /tmp/ovs-offline/var-run/ovs/br-int.mgmt icmp
    cookie=0xea0be1f0, duration=1629.229s, table=11, n_packets=0, n_bytes=0, priority=90,icmp,metadata=0x3,nw_dst=10.10.54.165,icmp_type=8,icmp_code=0 actions=push:NXM_OF_IP_SRC[],push:NXM_OF_IP_DST[],pop:NXM_OF_IP_SRC[],pop:NXM_OF_IP_DST[],load:0xff->NXM_NX_IP_TTL[],load:0->NXM_OF_ICMP_TYPE[],load:0x1->NXM_NX_REG10[0],resubmit(,12)
    cookie=0x710cdc08, duration=1629.230s, table=11, n_packets=0, n_bytes=0, priority=90,icmp,metadata=0x3,nw_dst=7.7.7.1,icmp_type=8,icmp_code=0 actions=push:NXM_OF_IP_SRC[],push:NXM_OF_IP_DST[],pop:NXM_OF_IP_SRC[],pop:NXM_OF_IP_DST[],load:0xff->NXM_NX_IP_TTL[],load:0->NXM_OF_ICMP_TYPE[],load:0x1->NXM_NX_REG10[0],resubmit(,12)
    cookie=0x44b233ed, duration=1629.217s, table=44, n_packets=0, n_bytes=0, priority=2002,icmp,reg0=0x100/0x100,reg15=0x3,metadata=0x1 actions=resubmit(,45)
    cookie=0xb460c36f, duration=1629.217s, table=44, n_packets=0, n_bytes=0, priority=2002,icmp,reg0=0x80/0x80,reg15=0x3,metadata=0x1 actions=load:0x1->NXM_NX_XXREG0[97],resubmit(,45

Often times the flow dumps can be tedious and hard to parse through in the given format. These flows can be handed to another OVS-dbg tool: :ref:`ofparse-reference-label` to view and analyse them in more human-readable formats.

More information on ovs-ofctl can be found here: https://man7.org/linux/man-pages/man8/ovs-ofctl.8.html

ovs-appctl
==========

The ovs-appctl program provides commands to control and query the ovs-vswitchd daemon at runtime, and print the daemon's response on standard output.

'ovs-appctl ofproto/trace' is one of the most useful and versatile tools for debugging, and is covered in greater detail here: :ref:`ofprototrace_label-name`.

'ovs-appctl dpif/show' provides the OpenFlow port / DP port for each bridge.

::

    $ovs-appctl --target=/tmp/ovs-offline/var-run/ovs/ovs-vswitchd.9.ctl dpif/show
    system@ovs-system: hit:0 missed:0
    br-data:
        br-data 65534/2: (dummy-internal)
        mx-bond 1/3: (system)
        patch-provnet-df741617-6923-41e3-9ef6-075004808738-to-br-int 3/none: (patch: peer=patch-br-int-to-provnet-df741617-6923-41e3-9ef6-075004808738)
        vlan405 2/405: (dummy-internal)
    br-int:
        br-int 65534/1: (dummy-internal)
        enp4s0f1_2 4/4: (system)
        ovn-ecf608-0 2/608: (geneve)
        patch-br-int-to-provnet-df741617-6923-41e3-9ef6-075004808738 3/none: (patch: peer=patch-provnet-df741617-6923-41e3-9ef6-075004808738-to-br-int)
        tap555ce370-10 5/555: (system)


More information regarding ovs-appctl can be found here: https://man7.org/linux/man-pages/man8/ovs-appctl.8.html.

ovsdb-client
============

ovsdb-client is available by specifying the server socket, and allows for interaction with the ovsdb-server, or OVN nb and sb servers.

For example, 'ovsdb-client list-tables provides' a convenient list of all tables in the OVS database, while ovsdb-client list-columns lists each column for a specified table.

::

    $ ovsdb-client list-tables unix:/tmp/ovs-offline/var-run/ovs/db.sock 
    Table
    -------------------------
    Controller
    Bridge
    QoS
    Datapath
    SSL
    Port
    [...]
    $ ovsdb-client list-columns unix:/tmp/ovs-offline/var-run/ovs/db.sock Port
    Column            Type
    ----------------- --------------------------------------------------------------------------------------------------------------------
    bond_downdelay    "integer"
    name              "string"
    statistics        {"key":"string","max":"unlimited","min":0,"value":"integer"}
    protected         "boolean"
    fake_bridge       "boolean"
    mac               {"key":"string","min":0}
    trunks            {"key":{"maxInteger":4095,"minInteger":0,"type":"integer"},"max":4096,"min":0}
    _uuid             "uuid"
    rstp_status       {"key":"string","max":"unlimited","min":0,"value":"string"}
    [...]

'ovsdb-client backup' can also be used to produce a backup of the database in a format able to be restored.
More information regarding ovsdb-client can be found here: https://man7.org/linux/man-pages/man1/ovsdb-client.1.html.


ovn-nbctl
=========
ovn-nbctl is a utility used to manage the OVN northbound database.

'ovn-nbctl show' can be used to print an overview of the database contents. Specific logical routers or switches can also be specified to print only related details.

::

    $ ovn-nbctl --db unix:/tmp/ovs-offline/var-run/ovn_nb/db.sock show 
    switch a04f416c-620d-4108-a3c1-68b89154ed26 (ovn-control-plane)
        port k8s-ovn-control-plane
            addresses: ["02:5e:fd:2b:13:62 10.244.2.2"]
        port stor-ovn-control-plane
            type: router
            router-port: rtos-ovn-control-plane
    [...]
    router 858c8778-ffd5-49aa-8aff-6691defbd1bc (GR_ovn-worker2)
        port rtoe-GR_ovn-worker2
            mac: "02:42:ac:12:00:04"
            networks: ["172.18.0.4/16"]
        port rtoj-GR_ovn-worker2
            mac: "0a:58:64:40:00:03"
            networks: ["100.64.0.3/16"]
        nat 7a293824-f025-45b2-9c9e-9565ff59f0c0
            external ip: "172.18.0.4"
            logical ip: "10.244.0.0/16"
            type: "snat"
    [...]

Queries can be made against the ovsdb tables following the instructions outlined in the ovn-nbctl_man-pages_.


'ovn-nbctl acl-list <logical_switch>' provides a list of the ACLs (access control lists) applied to the specified switch.

::

    $ ovn-nbctl --db unix:/tmp/ovs-offline/var-run/ovn_nb/db.sock acl-list 7e57d77f-137e-4192-9c6d-508350a1437c
    to-lport  1001 (ip4.src==10.244.1.2) allow-related

Similarly 'ovn-nbctl qos-list <logical_switch> lists the quality of service rules for the specified switch.

'ovn-nbctl list meter' can be used to examine the meters in place which serve to prevent overwhelming the OVN controller with logging events.

::

    $ ovn-nbctl --db unix:/tmp/ovs-offline/var-run/ovn_nb/db.sock list meter
    _uuid               : 172f0dab-9a45-4573-a9a5-405b23c25f36
    bands               : [cff2a26d-8730-495b-a8dd-cc7aa05377bb]
    external_ids        : {}
    fair                : true
    name                : acl-logging
    unit                : pktps
    [root@fedora bin]# ovn-nbctl --db unix:/tmp/ovs-offline/var-run/ovn_nb/db.sock list meter-band
    _uuid               : cff2a26d-8730-495b-a8dd-cc7aa05377bb
    action              : drop
    burst_size          : 0
    external_ids        : {}
    rate                : 20

'ovn-nbctl lr-route-list <router>' prints out the routes on a specified router.

::

    $ ovn-nbctl --db unix:/tmp/ovs-offline/var-run/ovn_nb/db.sock lr-route-list fe680793-e0ce-489c-8b16-cecb012bd4d4
    IPv4 Routes
                10.244.0.0/16                100.64.0.1 dst-ip
                    0.0.0.0/0                172.18.0.1 dst-ip rtoe-GR_ovn-control-plane

'lr-nat-list <router>' prints the NATs on a specified router.

::

    $ ovn-nbctl --db unix:/tmp/ovs-offline/var-run/ovn_nb/db.sock lr-nat-list fe680793-e0ce-489c-8b16-cecb012bd4d4
    TYPE             EXTERNAL_IP        EXTERNAL_PORT    LOGICAL_IP            EXTERNAL_MAC         LOGICAL_PORT
    snat             172.18.0.2                          10.244.0.0/16



More information regarding ovn-nbctl can be found here: https://man7.org/linux/man-pages/man8/ovn-nbctl.8.html


ovn-sbctl
=========

ovn-sbctl is a utility for querying and configuring the OVN_Southbound database.

'ovn-sbctl show' provides a brief overview of the database contents.

::

    $ ovn-sbctl --db unix:/tmp/ovs-offline/var-run/ovn_sb/db.sock show
    Chassis "fe4e7b3c-4180-43c3-91f6-b38b9c898cbd"
        hostname: ovn-control-plane
        Encap geneve
            ip: "172.18.0.2"
            options: {csum="true"}
        Port_Binding rtoj-GR_ovn-control-plane
        Port_Binding k8s-ovn-control-plane
        Port_Binding etor-GR_ovn-control-plane
        Port_Binding jtor-GR_ovn-control-plane
        Port_Binding rtoe-GR_ovn-control-plane
        Port_Binding cr-rtos-ovn-control-plane
    Chassis "f5e8f3fd-2848-4efb-8028-5673c3866a57"
        hostname: ovn-worker2
        Encap geneve
            ip: "172.18.0.4"
            options: {csum="true"}
        Port_Binding rtoj-GR_ovn-worker2
        Port_Binding rtoe-GR_ovn-worker2
        Port_Binding etor-GR_ovn-worker2
        Port_Binding cr-rtos-ovn-worker2
    [...]


'ovn-sbctl lflow-list' provides a full list of the logical flows.

::

    $ ovn-sbctl --db unix:/tmp/ovs-offline/var-run/ovn_sb/db.sock lflow-list
    Datapath: "GR_ovn-control-plane" (81daa3cf-3bf9-42ac-806b-2ee95e28f11c)  Pipeline: ingress
    table=0 (lr_in_admission    ), priority=100  , match=(vlan.present || eth.src[40]), action=(drop;)
    table=0 (lr_in_admission    ), priority=50   , match=(eth.dst == 02:42:ac:12:00:02 && inport == "rtoe-GR_ovn-control-plane"), action=(xreg0[0..47] = 02:42:ac:12:00:02; next;)
    table=0 (lr_in_admission    ), priority=50   , match=(eth.dst == 0a:58:64:40:00:02 && inport == "rtoj-GR_ovn-control-plane"), action=(xreg0[0..47] = 0a:58:64:40:00:02; next;)
    table=0 (lr_in_admission    ), priority=50   , match=(eth.mcast && inport == "rtoe-GR_ovn-control-plane"), action=(xreg0[0..47] = 02:42:ac:12:00:02; next;)
    table=0 (lr_in_admission    ), priority=50   , match=(eth.mcast && inport == "rtoj-GR_ovn-control-plane"), action=(xreg0[0..47] = 0a:58:64:40:00:02; next;)
    table=1 (lr_in_lookup_neighbor), priority=110  , match=(inport == "rtoe-GR_ovn-control-plane" && arp.spa == 172.18.0.0/16 && arp.tpa == 172.18.0.2 && arp.op == 1), action=(reg9[2] = lookup_arp(inport, arp.spa, arp.sha); reg9[3] = 1; next;)
    table=1 (lr_in_lookup_neighbor), priority=110  , match=(inport == "rtoj-GR_ovn-control-plane" && arp.spa == 100.64.0.0/16 && arp.tpa == 100.64.0.2 && arp.op == 1), action=(reg9[2] = lookup_arp(inport, arp.spa, arp.sha); reg9[3] = 1; next;)
    table=1 (lr_in_lookup_neighbor), priority=100  , match=(arp.op == 2), action=(reg9[2] = lookup_arp(inport, arp.spa, arp.sha); reg9[3] = 1; next;)
    [...]

These flows look somewhat similar to OpenFlow flow dumps, but with a few notable differences (https://blog.russellbryant.net/2016/11/11/ovn-logical-flows-and-ovn-trace/)

    - Ports are logical entities that reside somewhere on a network, not physical ports on a single switch.
    - Each table in the pipeline is given a name in addition to its number. The name describes the purpose of that stage in the pipeline.
    - The match syntax is far more flexible and supports complex boolean expressions.
    - The actions supported in OVN logical flows extend beyond what you would expect from OpenFlow.

Queries can be made against the ovsdb tables following the instructions outlined in the ovn-sbctl_man-pages_.

More information regarding ovn-sbctl can be found here: https://man7.org/linux/man-pages/man8/ovn-sbctl.8.html

.. _ofprototrace_label-name:

appctl ofproto/trace
^^^^^^^^^^^^^^^^^^^^
appctl ofproto/trace is a valuable tool that enables the user to track packet flow within openvswitch without needing to send any actual packets. It can be a great tool in diagnosing unexpected behaviors in a network and gaining insight into the pipeline processing.

Basic usage of the ofproto/trace command is covered in ovs-vswitchd_

Additional examples of packet tracing in OVS can be found here:

- https://developers.redhat.com/blog/2016/10/12/tracing-packets-inside-open-vswitch

- https://docs.openvswitch.org/en/latest/topics/tracing/

The following is an example of running ofproto/trace on an offline replica of a OVN KIND kubernetes set up.

Using the result of 'ovsnb-ctl show' we can determine there is a switch called "ovn-worker" and gather further details into its configuration.

::

    $ ovn-nbctl --db unix:/tmp/ovs-offline/var-run/ovn_nb/db.sock show ovn-worker
    switch 8ba6be15-4af2-4b31-96dd-4fca70352584 (ovn-worker)
        port k8s-ovn-worker
            addresses: ["3a:25:93:71:79:d7 10.244.2.2"]
        port stor-ovn-worker
            type: router
            router-port: rtos-ovn-worker
        port local-path-storage_local-path-provisioner-78776bfc44-skmjb
            addresses: ["0a:58:0a:f4:02:03 10.244.2.3"]
        port kube-system_coredns-74ff55c5b-7shvq
            addresses: ["0a:58:0a:f4:02:04 10.244.2.4"]

Here we see a port 'k8s-own-worker' with an address of 10.244.2.2. Using ofproto/trace, we can inspect traffic from this port / address to another.

ovs-appctl dpif/show will allow us to determine the OpenFlow port corresponding to 'k8-ovn-worker'

::

    ovs-appctl --target=/tmp/ovs-offline/var-run/ovs/ovs-vswitchd.8.ctl dpif/show
    system@ovs-system: hit:0 missed:0
    br-int:
        788cad40b54931d 5/788: (system)
        b277e72b9dee11e 6/277: (system)
        br-int 65534/1: (dummy-internal)
        ovn-6696e2-0 1/6696: (geneve)
        ovn-d30e9f-0 3/30: (geneve)
        ovn-k8s-mp0 2/8: (dummy-internal)
        patch-br-int-to-breth0_ovn-worker 4/none: (patch: peer=patch-breth0_ovn-worker-to-br-int)
    breth0:
        breth0 65534/100: (dummy-internal)
        eth0 1/2: (system)
        patch-breth0_ovn-worker-to-br-int 2/none: (patch: peer=patch-br-int-to-breth0_ovn-worker)

Now we have our OpenFlow in_port, 2. We can test what will happen to traffic from port 2 and nw_src 10.244.2.2 to port kube-system_coredns-74ff55c5b-7shvq at 10.244.2.4. We will need to specify a network protocol, so we will look for icmp traffic (nw_proto=1).

We can improve our trace by adding the mac address of ovn-k8s-mp0 port which is listed in 'ovs-vsctl list interface'

::

    [...]
    mac                 : "3a:25:93:71:79:d7"
    mac_in_use          : "3a:25:93:71:79:d7"
    mtu                 : 1400
    mtu_request         : 1400
    name                : ovn-k8s-mp0
    ofport              : 2
    ofport_request      : []
    options             : {}
    other_config        : {}
    [...]

Finally we can add the destination mac address as the port we selected earlier.

::

    port kube-system_coredns-74ff55c5b-7shvq
            addresses: ["0a:58:0a:f4:02:04 10.244.2.4"]

Let's see what our current trace will return.

::

    $ ovs-appctl --target=/tmp/ovs-offline/var-run/ovs/ovs-vswitchd.8.ctl ofproto/trace br-int in_port=2,ip,nw_proto=1,nw_src=10.244.2.2,nw_dst=10.244.2.4,eth_src=3a:25:93:71:79:d7,eth_dst=0a:58:0a:f4:02:04
    Flow: icmp,in_port=2,vlan_tci=0x0000,dl_src=3a:25:93:71:79:d7,dl_dst=0a:58:0a:f4:02:04,nw_src=10.244.2.2,nw_dst=10.244.2.4,nw_tos=0,nw_ecn=0,nw_ttl=0,icmp_type=0,icmp_code=0

    bridge("br-int")
    ----------------
    0. in_port=2, priority 100, cookie 0x78313dc8
        set_field:0x7->reg13
        set_field:0x6->reg11
        set_field:0x4->reg12
        set_field:0x4->metadata
        set_field:0x2->reg14
        resubmit(,8)
    8. reg14=0x2,metadata=0x4, priority 50, cookie 0x4e19f28a
        resubmit(,9)
    9. metadata=0x4, priority 0, cookie 0xbeae1d65
        resubmit(,10)
    10. metadata=0x4, priority 0, cookie 0x4f53ff78
        resubmit(,11)
    11. metadata=0x4, priority 0, cookie 0xdef27d9d
        resubmit(,12)
    12. metadata=0x4, priority 0, cookie 0x2974b337
        resubmit(,13)
    13. ip,metadata=0x4, priority 100, cookie 0x7dc8753
        load:0x1->NXM_NX_XXREG0[96]
        resubmit(,14)
    14. ip,metadata=0x4, priority 100, cookie 0x8c371f3d
        load:0x1->NXM_NX_XXREG0[98]
        resubmit(,15)
    15. ip,reg0=0x4/0x4,metadata=0x4, priority 110, cookie 0x6f9c8080
        ct(table=16,zone=NXM_NX_REG13[0..15],nat)
        nat
        -> A clone of the packet is forked to recirculate. The forked pipeline will be resumed at table 16.
        -> Sets the packet to an untracked state, and clears all the conntrack fields.

    Final flow: icmp,reg0=0x5,reg11=0x6,reg12=0x4,reg13=0x7,reg14=0x2,metadata=0x4,in_port=2,vlan_tci=0x0000,dl_src=3a:25:93:71:79:d7,dl_dst=0a:58:0a:f4:02:04,nw_src=10.244.2.2,nw_dst=10.244.2.4,nw_tos=0,nw_ecn=0,nw_ttl=0,icmp_type=0,icmp_code=0
    Megaflow: recirc_id=0,ct_state=-new-est-trk,ct_label=0/0x2,eth,icmp,in_port=2,dl_src=00:00:00:00:00:00/01:00:00:00:00:00,dl_dst=0a:58:0a:f4:02:04,nw_frag=no
    Datapath actions: ct(zone=7,nat),recirc(0x37)

    ===============================================================================
    recirc(0x37) - resume conntrack with default ct_state=trk|new (use --ct-next to customize)
    Replacing src/dst IP/ports to simulate NAT:
    Initial flow: 
    Modified flow: 
    ===============================================================================
    [...]



Here we can see in the first 'Flow' line of the output the flow that was extracted from the one we entered in the command line.
The nw_protocol has been identified as icmp, and the keyword has been added accordingly.
Unspecified packet fields are zeroed, so in our case the nw tos, ecn, ttl and the icmp fields.
The next section beginning with 'bridge "br-int"' shows the matches our flow had within the flow tables in br-int followed by the actions taken as a result. 
In table 0, our flow matched as traffic from in_port 2, and as a result various register flags are set (and later matched on) and the flow is resubmitted to table 8.

After the flow traverses the match/actions of each table, the final state of the flow is shown, followed by the Megaflow which matches on all relevant fields.
Last is the datapath actions, which in this case show the conntrack zone is set, NAT occurs, and the flow is recirulated.
Conntrack is a connection tracking module for stateful packet inspection that allows the flow to match based on the state of the connection (established, new, tracked, reply, etc).
Ofproto/trace simulates OVS checking the conntrack module for an existing connection, and since we did not specify the ct state in this way, it sets a default ct_state for each recirculated flow as 'tracked' and 'new'.

Further details regarding conntrack in OVS is outside the scope of this tutorial and can be read about further here: https://docs.openvswitch.org/en/latest/tutorials/ovs-conntrack/

As mentioned in the ofproto/trace output, we can use --ct-next to set the ct state for when the flow is recirculated, and make our flow more realistic.

Further insight may be available in the datapath flows (collected from the live OVS set up using 'ovs-appctl dpctl/dump-flows') which can be helpful in accessing packet flow.
In this case, the following datapath flows confirm the ct-state that the OpenFlow tables will match on, as well as reveal the expected action for the datapath flow corresponding to our OpenFlow flow.

::

    recirc_id(0),in_port(3),ct_state(+new-est+trk),ct_label(0/0x2),eth(src=00:00:00:00:00:00/01:00:00:00:00:00,dst=0a:58:0a:f4:02:04),eth_type(0x0800),ipv4(dst=10.244.2.4,proto=6,frag=no),tcp(dst=8181), packets:543, bytes:40182, used:2.406s, flags:S, actions:ct(zone=7,nat),recirc(0x2a)

    recirc_id(0x2a),in_port(3),ct_state(+new-est-rel-rpl-inv+trk),ct_label(0/0x1),eth(src=3a:25:93:71:79:d7,dst=0a:58:0a:f4:02:04),eth_type(0x0800),ipv4(dst=10.244.0.0/255.255.0.0,proto=6,frag=no), packets:543, bytes:40182, used:2.406s, flags:S, actions:ct(commit,zone=7,label=0/0x1),ct(zone=12,nat),recirc(0x2b)

    recirc_id(0x2b),in_port(3),ct_state(-new+est-rel-rpl-inv+trk),ct_label(0/0x1),eth(src=3a:25:93:71:79:d7,dst=0a:58:0a:f4:02:04),eth_type(0x0800),ipv4(src=10.244.2.2,dst=10.244.2.4,frag=no), packets:99877, bytes:9012994, used:2.403s, flags:FP., actions:7

We can add the proper connection tracker simulation to our flow, and confirm the flow does in fact reach the expected destination port (dpif/show in the live OVS set-up reveals dp port 3 and 7 correspond to dp port 2 and 277 in the offline replica respectively).

::

    $ ovs-appctl --target=/tmp/ovs-offline/var-run/ovs/ovs-vswitchd.8.ctl ofproto/trace br-int in_port=2,ip,nw_proto=1,nw_src=10.244.2.2,nw_dst=10.244.2.4,eth_src=3a:25:93:71:79:d7,eth_dst=0a:58:0a:f4:02:04 --ct-next new,trk --ct-next est,trk
    Flow: icmp,in_port=2,vlan_tci=0x0000,dl_src=3a:25:93:71:79:d7,dl_dst=0a:58:0a:f4:02:04,nw_src=10.244.2.2,nw_dst=10.244.2.4,nw_tos=0,nw_ecn=0,nw_ttl=0,icmp_type=0,icmp_code=0

    bridge("br-int")
    ----------------
    0. in_port=2, priority 100, cookie 0x78313dc8
        set_field:0x7->reg13
        set_field:0x6->reg11
        set_field:0x4->reg12
        set_field:0x4->metadata
        set_field:0x2->reg14
        resubmit(,8)
    8. reg14=0x2,metadata=0x4, priority 50, cookie 0x4e19f28a
        resubmit(,9)
    9. metadata=0x4, priority 0, cookie 0xbeae1d65
        resubmit(,10)
    10. metadata=0x4, priority 0, cookie 0x4f53ff78
        resubmit(,11)
    11. metadata=0x4, priority 0, cookie 0xdef27d9d
        resubmit(,12)
    12. metadata=0x4, priority 0, cookie 0x2974b337
        resubmit(,13)
    13. ip,metadata=0x4, priority 100, cookie 0x7dc8753
        load:0x1->NXM_NX_XXREG0[96]
        resubmit(,14)
    14. ip,metadata=0x4, priority 100, cookie 0x8c371f3d
        load:0x1->NXM_NX_XXREG0[98]
        resubmit(,15)
    15. ip,reg0=0x4/0x4,metadata=0x4, priority 110, cookie 0x6f9c8080
        ct(table=16,zone=NXM_NX_REG13[0..15],nat)
        nat
        -> A clone of the packet is forked to recirculate. The forked pipeline will be resumed at table 16.
        -> Sets the packet to an untracked state, and clears all the conntrack fields.

    Final flow: icmp,reg0=0x5,reg11=0x6,reg12=0x4,reg13=0x7,reg14=0x2,metadata=0x4,in_port=2,vlan_tci=0x0000,dl_src=3a:25:93:71:79:d7,dl_dst=0a:58:0a:f4:02:04,nw_src=10.244.2.2,nw_dst=10.244.2.4,nw_tos=0,nw_ecn=0,nw_ttl=0,icmp_type=0,icmp_code=0
    Megaflow: recirc_id=0,ct_state=-new-est-trk,ct_label=0/0x2,eth,icmp,in_port=2,dl_src=00:00:00:00:00:00/01:00:00:00:00:00,dl_dst=0a:58:0a:f4:02:04,nw_frag=no
    Datapath actions: ct(zone=7,nat),recirc(0x39)

    ===============================================================================
    recirc(0x39) - resume conntrack with ct_state=new|trk
    Replacing src/dst IP/ports to simulate NAT:
    Initial flow: 
    Modified flow: 
    ===============================================================================

    Flow: recirc_id=0x39,ct_state=new|trk,ct_zone=7,eth,icmp,reg0=0x5,reg11=0x6,reg12=0x4,reg13=0x7,reg14=0x2,metadata=0x4,in_port=2,vlan_tci=0x0000,dl_src=3a:25:93:71:79:d7,dl_dst=0a:58:0a:f4:02:04,nw_src=10.244.2.2,nw_dst=10.244.2.4,nw_tos=0,nw_ecn=0,nw_ttl=0,icmp_type=0,icmp_code=0

    bridge("br-int")
    ----------------
        thaw
            Resuming from table 16
    16. ct_state=+new-est+trk,metadata=0x4, priority 7, cookie 0xae73ccef
        load:0x1->NXM_NX_XXREG0[103]
        load:0x1->NXM_NX_XXREG0[105]
        resubmit(,17)
    17. ct_state=-est+trk,ip,metadata=0x4, priority 1, cookie 0xbb19e5f
        load:0x1->NXM_NX_XXREG0[97]
        resubmit(,18)
    18. metadata=0x4, priority 0, cookie 0xe16802a6
        resubmit(,19)
    19. metadata=0x4, priority 0, cookie 0x14179fb6
        resubmit(,20)
    20. ip,reg0=0x2/0x2002,metadata=0x4, priority 100, cookie 0x775cd4b6
        ct(commit,zone=NXM_NX_REG13[0..15],exec(load:0->NXM_NX_CT_LABEL[0]))
        load:0->NXM_NX_CT_LABEL[0]
        -> Sets the packet to an untracked state, and clears all the conntrack fields.
        resubmit(,21)
    21. metadata=0x4, priority 0, cookie 0x73284dae
        resubmit(,22)
    22. metadata=0x4, priority 0, cookie 0xef0f8ceb
        resubmit(,23)
    23. metadata=0x4, priority 0, cookie 0x8962f4bd
        resubmit(,24)
    24. metadata=0x4, priority 0, cookie 0x730f5e33
        resubmit(,25)
    25. metadata=0x4, priority 0, cookie 0xa1c173b1
        resubmit(,26)
    26. metadata=0x4, priority 0, cookie 0x6d47644e
        resubmit(,27)
    27. metadata=0x4, priority 0, cookie 0x5156c7c3
        resubmit(,28)
    28. metadata=0x4, priority 0, cookie 0x5676dd05
        resubmit(,29)
    29. metadata=0x4, priority 0, cookie 0xb7732b0e
        resubmit(,30)
    30. metadata=0x4,dl_dst=0a:58:0a:f4:02:04, priority 50, cookie 0xee34920b
        set_field:0x4->reg15
        resubmit(,37)
    37. priority 0
        resubmit(,38)
    38. reg15=0x4,metadata=0x4, priority 100, cookie 0x209c1570
        set_field:0xc->reg13
        set_field:0x6->reg11
        set_field:0x4->reg12
        resubmit(,39)
    39. priority 0
        set_field:0->reg0
        set_field:0->reg1
        set_field:0->reg2
        set_field:0->reg3
        set_field:0->reg4
        set_field:0->reg5
        set_field:0->reg6
        set_field:0->reg7
        set_field:0->reg8
        set_field:0->reg9
        resubmit(,40)
    40. ip,metadata=0x4, priority 100, cookie 0xdbc40f65
        load:0x1->NXM_NX_XXREG0[98]
        resubmit(,41)
    41. ip,metadata=0x4, priority 100, cookie 0xfd031257
        load:0x1->NXM_NX_XXREG0[96]
        resubmit(,42)
    42. ip,reg0=0x4/0x4,metadata=0x4, priority 110, cookie 0xf8dd82fb
        ct(table=43,zone=NXM_NX_REG13[0..15],nat)
        nat
        -> A clone of the packet is forked to recirculate. The forked pipeline will be resumed at table 43.
        -> Sets the packet to an untracked state, and clears all the conntrack fields.

    Final flow: recirc_id=0x39,eth,icmp,reg0=0x5,reg11=0x6,reg12=0x4,reg13=0xc,reg14=0x2,reg15=0x4,metadata=0x4,in_port=2,vlan_tci=0x0000,dl_src=3a:25:93:71:79:d7,dl_dst=0a:58:0a:f4:02:04,nw_src=10.244.2.2,nw_dst=10.244.2.4,nw_tos=0,nw_ecn=0,nw_ttl=0,icmp_type=0,icmp_code=0
    Megaflow: recirc_id=0x39,ct_state=+new-est-rel-rpl-inv+trk,ct_label=0/0x1,eth,icmp,in_port=2,dl_src=3a:25:93:71:79:d7,dl_dst=0a:58:0a:f4:02:04,nw_dst=10.244.0.0/16,nw_frag=no
    Datapath actions: ct(commit,zone=7,label=0/0x1),ct(zone=12,nat),recirc(0x3a)

    ===============================================================================
    recirc(0x3a) - resume conntrack with ct_state=est|trk
    Replacing src/dst IP/ports to simulate NAT:
    Initial flow: 
    Modified flow: 
    ===============================================================================

    Flow: recirc_id=0x3a,ct_state=est|trk,ct_zone=12,eth,icmp,reg0=0x5,reg11=0x6,reg12=0x4,reg13=0xc,reg14=0x2,reg15=0x4,metadata=0x4,in_port=2,vlan_tci=0x0000,dl_src=3a:25:93:71:79:d7,dl_dst=0a:58:0a:f4:02:04,nw_src=10.244.2.2,nw_dst=10.244.2.4,nw_tos=0,nw_ecn=0,nw_ttl=0,icmp_type=0,icmp_code=0

    bridge("br-int")
    ----------------
        thaw
            Resuming from table 43
    43. ct_state=-new+est-rpl+trk,ct_label=0/0x1,metadata=0x4, priority 4, cookie 0x524878a0
        load:0x1->NXM_NX_XXREG0[104]
        load:0x1->NXM_NX_XXREG0[106]
        resubmit(,44)
    44. ip,reg0=0x100/0x100,metadata=0x4,nw_src=10.244.2.2, priority 2001, cookie 0x904220e3
        resubmit(,45)
    45. metadata=0x4, priority 0, cookie 0x58bf876b
        resubmit(,46)
    46. metadata=0x4, priority 0, cookie 0xb83daa36
        resubmit(,47)
    47. metadata=0x4, priority 0, cookie 0x969914b0
        resubmit(,48)
    48. ip,reg15=0x4,metadata=0x4,dl_dst=0a:58:0a:f4:02:04,nw_dst=10.244.2.4, priority 90, cookie 0xc3524798
        resubmit(,49)
    49. reg15=0x4,metadata=0x4,dl_dst=0a:58:0a:f4:02:04, priority 50, cookie 0x861f6c28
        resubmit(,64)
    64. priority 0
        resubmit(,65)
    65. reg15=0x4,metadata=0x4, priority 100, cookie 0x209c1570
        output:6

    Final flow: recirc_id=0x3a,ct_state=est|trk,ct_zone=12,eth,icmp,reg0=0x505,reg11=0x6,reg12=0x4,reg13=0xc,reg14=0x2,reg15=0x4,metadata=0x4,in_port=2,vlan_tci=0x0000,dl_src=3a:25:93:71:79:d7,dl_dst=0a:58:0a:f4:02:04,nw_src=10.244.2.2,nw_dst=10.244.2.4,nw_tos=0,nw_ecn=0,nw_ttl=0,icmp_type=0,icmp_code=0
    Megaflow: recirc_id=0x3a,ct_state=-new+est-rel-rpl-inv+trk,ct_label=0/0x1,eth,ip,in_port=2,dl_src=3a:25:93:71:79:d7,dl_dst=0a:58:0a:f4:02:04,nw_src=10.244.2.2,nw_dst=10.244.2.4,nw_frag=no
    Datapath actions: 277

As expected, the final action after recirculating the packet with the --ct-next set to emulate the real life ct state results in the hypothetical packet being output to port 277.
The results of our ofproto/trace can be further examined using ovn-detrace.

ovn-detrace
^^^^^^^^^^^

ovn-detrace reads output from ovs-appctl ofproto/trace and expands each cookie with corresponding OVN logical flows.
This can provide helpful insights such as the ACL that generated the logical flow.

We can come up with a quick flow to test this with by looking at the datapath flow dump in the live OVS set up.

::

    $ ovs-appctl dpctl/dump-flows
    recirc_id(0xf),in_port(4),ct_state(+est+trk),ct_mark(0x2),eth(),eth_type(0x0800),ipv4(frag=no), packets:1404, bytes:119266, used:0.031s, flags:P., actions:5

This can be abstracted into following OpenFlow, which we can hand to ofproto/trace. We will save the output to a text file for use with ovn-detrace.

::

    $ ovs-appctl ofproto/trace breth0 in_port=1,eth_type=0x0800 --ct-next est,trk >> ofprototrace_output.txt


We need to specify to the ovn-detrace program the nb and sb server remote to contact. This can be done using the --ovnnb/sn flags, or by setting the following environment variables:

::

    $ OVN_SB_DB=/tmp/ovs-offline/var-run/ovn_sb/db.sock
    $ OVN_NB_DB=/tmp/ovs-offline/var-run/ovn_nb/db.sock

Now we can run ovn-detrace handing it the output of our previous ofproto/trace.

::

    $ ovn-detrace < ofprototrace_output.txt              
    Flow: ip,in_port=1,vlan_tci=0x0000,dl_src=00:00:00:00:00:00,dl_dst=00:00:00:00:00:00,nw_src=0.0.0.0,nw_dst=0.0.0.0,nw_proto=0,nw_tos=0,nw_ecn=0,nw_ttl=0

    bridge("breth0")
    ----------------
    0. ip,in_port=1, priority 50, cookie 0xdeff105
    ct(table=1,zone=64000)
    drop
    -> A clone of the packet is forked to recirculate. The forked pipeline will be resumed at table 1.
    -> Sets the packet to an untracked state, and clears all the conntrack fields.

    Final flow: unchanged
    Megaflow: recirc_id=0,eth,ip,in_port=1,dl_dst=00:00:00:00:00:00,nw_proto=0,nw_frag=no
    Datapath actions: ct(zone=64000),recirc(0x1)

    ===============================================================================
    recirc(0x1) - resume conntrack with ct_state=est|trk
    ===============================================================================

    Flow: recirc_id=0x1,ct_state=est|trk,ct_zone=64000,eth,ip,in_port=1,vlan_tci=0x0000,dl_src=00:00:00:00:00:00,dl_dst=00:00:00:00:00:00,nw_src=0.0.0.0,nw_dst=0.0.0.0,nw_proto=0,nw_tos=0,nw_ecn=0,nw_ttl=0

    bridge("breth0")
    ----------------
    thaw
    Resuming from table 1
    1. priority 0, cookie 0xdeff105
    NORMAL
    -> no learned MAC for destination, flooding

    bridge("br-int")
    ----------------
    0. in_port=4,vlan_tci=0x0000/0x1000, priority 100, cookie 0x7aed837a
    set_field:0xa->reg11
    set_field:0x9->reg12
    set_field:0x7->metadata
    set_field:0x1->reg14
    resubmit(,8)
    *  Logical datapath: "ext_ovn-worker" (eb511c92-a224-4709-931a-b6a3a5289dfc)
    *  Port Binding: logical_port "breth0_ovn-worker", tunnel_key 1, 
    8. reg14=0x1,metadata=0x7, priority 50, cookie 0x1937006c
    resubmit(,9)
    *  Logical datapaths:
    *      "ext_ovn-worker" (eb511c92-a224-4709-931a-b6a3a5289dfc) [ingress]
    *  Logical flow: table=0 (ls_in_port_sec_l2), priority=50, match=(inport == "breth0_ovn-worker), actions=(next;)
    *  Logical Switch Port: breth0_ovn-worker type localnet (addresses ['unknown'], dynamic addresses [], security []
    9. metadata=0x7, priority 0, cookie 0x5890e5c
    resubmit(,10)
    *  Logical datapaths:
    *      "ovn-worker" (29f8d327-0be2-4947-aee6-a2456e52f51a) [ingress]
    *      "ovn-control-plane" (6edbe5e2-221b-4b0e-9a3a-73d97e54b0ca) [ingress]
    *      "ovn-worker2" (9260cc1e-3ed6-4df5-8732-8463ad20760c) [ingress]
    *      "ext_ovn-worker2" (d6f5cd63-b50a-49ab-98dd-0430965868ef) [ingress]
    *      "join" (d74ad6c7-87b2-4429-8c5a-1d2ecf193d7b) [ingress]
    *      "ext_ovn-control-plane" (e6a5ca61-cf8b-4d46-bbe9-d38b2f3d4ebc) [ingress]
    *      "ext_ovn-worker" (eb511c92-a224-4709-931a-b6a3a5289dfc) [ingress]
    *  Logical flow: table=1 (ls_in_port_sec_ip), priority=0, match=(1), actions=(next;)
    10. metadata=0x7, priority 0, cookie 0xa78b7522
    resubmit(,11)
    *  Logical datapaths:
    *      "ovn-worker" (29f8d327-0be2-4947-aee6-a2456e52f51a) [ingress]
    *      "ovn-control-plane" (6edbe5e2-221b-4b0e-9a3a-73d97e54b0ca) [ingress]
    *      "ovn-worker2" (9260cc1e-3ed6-4df5-8732-8463ad20760c) [ingress]
    *      "ext_ovn-worker2" (d6f5cd63-b50a-49ab-98dd-0430965868ef) [ingress]
    *      "join" (d74ad6c7-87b2-4429-8c5a-1d2ecf193d7b) [ingress]
    *      "ext_ovn-control-plane" (e6a5ca61-cf8b-4d46-bbe9-d38b2f3d4ebc) [ingress]
    *      "ext_ovn-worker" (eb511c92-a224-4709-931a-b6a3a5289dfc) [ingress]
    *  Logical flow: table=2 (ls_in_port_sec_nd), priority=0, match=(1), actions=(next;)
    11. metadata=0x7, priority 0, cookie 0xb33d79ba
    resubmit(,12)
    *  Logical datapaths:
    *      "ovn-worker" (29f8d327-0be2-4947-aee6-a2456e52f51a) [ingress]
    *      "ovn-control-plane" (6edbe5e2-221b-4b0e-9a3a-73d97e54b0ca) [ingress]
    *      "ovn-worker2" (9260cc1e-3ed6-4df5-8732-8463ad20760c) [ingress]
    *      "ext_ovn-worker2" (d6f5cd63-b50a-49ab-98dd-0430965868ef) [ingress]
    *      "join" (d74ad6c7-87b2-4429-8c5a-1d2ecf193d7b) [ingress]
    *      "ext_ovn-control-plane" (e6a5ca61-cf8b-4d46-bbe9-d38b2f3d4ebc) [ingress]
    *      "ext_ovn-worker" (eb511c92-a224-4709-931a-b6a3a5289dfc) [ingress]
    *  Logical flow: table=3 (ls_in_lookup_fdb), priority=0, match=(1), actions=(next;)
    12. metadata=0x7, priority 0, cookie 0xdbece922
    resubmit(,13)
    *  Logical datapaths:
    *      "ovn-worker" (29f8d327-0be2-4947-aee6-a2456e52f51a) [ingress]
    *      "ovn-control-plane" (6edbe5e2-221b-4b0e-9a3a-73d97e54b0ca) [ingress]
    *      "ovn-worker2" (9260cc1e-3ed6-4df5-8732-8463ad20760c) [ingress]
    *      "ext_ovn-worker2" (d6f5cd63-b50a-49ab-98dd-0430965868ef) [ingress]
    *      "join" (d74ad6c7-87b2-4429-8c5a-1d2ecf193d7b) [ingress]
    *      "ext_ovn-control-plane" (e6a5ca61-cf8b-4d46-bbe9-d38b2f3d4ebc) [ingress]
    *      "ext_ovn-worker" (eb511c92-a224-4709-931a-b6a3a5289dfc) [ingress]
    *  Logical flow: table=4 (ls_in_put_fdb), priority=0, match=(1), actions=(next;)
    13. metadata=0x7, priority 0, cookie 0x91bbd81b
    resubmit(,14)
    *  Logical datapaths:
    *      "ovn-worker" (29f8d327-0be2-4947-aee6-a2456e52f51a) [ingress]
    *      "ovn-control-plane" (6edbe5e2-221b-4b0e-9a3a-73d97e54b0ca) [ingress]
    *      "ovn-worker2" (9260cc1e-3ed6-4df5-8732-8463ad20760c) [ingress]
    *      "ext_ovn-worker2" (d6f5cd63-b50a-49ab-98dd-0430965868ef) [ingress]
    *      "join" (d74ad6c7-87b2-4429-8c5a-1d2ecf193d7b) [ingress]
    *      "ext_ovn-control-plane" (e6a5ca61-cf8b-4d46-bbe9-d38b2f3d4ebc) [ingress]
    *      "ext_ovn-worker" (eb511c92-a224-4709-931a-b6a3a5289dfc) [ingress]
    *  Logical flow: table=5 (ls_in_pre_acl), priority=0, match=(1), actions=(next;)
    14. ip,reg14=0x1,metadata=0x7, priority 110, cookie 0x7e04616c
    resubmit(,15)
    *  Logical datapaths:
    *      "ext_ovn-worker" (eb511c92-a224-4709-931a-b6a3a5289dfc) [ingress]
    *  Logical flow: table=6 (ls_in_pre_lb), priority=110, match=(ip && inport == "breth0_ovn-worker), actions=(next;)
    *  Logical Switch Port: breth0_ovn-worker type localnet (addresses ['unknown'], dynamic addresses [], security []
    15. metadata=0x7, priority 0, cookie 0x31572a10
    resubmit(,16)
    *  Logical datapaths:
    *      "ovn-worker" (29f8d327-0be2-4947-aee6-a2456e52f51a) [ingress]
    *      "ovn-control-plane" (6edbe5e2-221b-4b0e-9a3a-73d97e54b0ca) [ingress]
    *      "ovn-worker2" (9260cc1e-3ed6-4df5-8732-8463ad20760c) [ingress]
    *      "ext_ovn-worker2" (d6f5cd63-b50a-49ab-98dd-0430965868ef) [ingress]
    *      "join" (d74ad6c7-87b2-4429-8c5a-1d2ecf193d7b) [ingress]
    *      "ext_ovn-control-plane" (e6a5ca61-cf8b-4d46-bbe9-d38b2f3d4ebc) [ingress]
    *      "ext_ovn-worker" (eb511c92-a224-4709-931a-b6a3a5289dfc) [ingress]
    *  Logical flow: table=7 (ls_in_pre_stateful), priority=0, match=(1), actions=(next;)
    16. metadata=0x7, priority 65535, cookie 0xe387fa95
    resubmit(,17)
    *  Logical datapaths:
    *      "ext_ovn-worker2" (d6f5cd63-b50a-49ab-98dd-0430965868ef) [ingress]
    *      "join" (d74ad6c7-87b2-4429-8c5a-1d2ecf193d7b) [ingress]
    *      "ext_ovn-control-plane" (e6a5ca61-cf8b-4d46-bbe9-d38b2f3d4ebc) [ingress]
    *      "ext_ovn-worker" (eb511c92-a224-4709-931a-b6a3a5289dfc) [ingress]
    *  Logical flow: table=8 (ls_in_acl_hint), priority=65535, match=(1), actions=(next;)
    17. metadata=0x7, priority 65535, cookie 0xaff44405
    resubmit(,18)
    *  Logical datapaths:
    *      "ext_ovn-worker2" (d6f5cd63-b50a-49ab-98dd-0430965868ef) [ingress]
    *      "join" (d74ad6c7-87b2-4429-8c5a-1d2ecf193d7b) [ingress]
    *      "ext_ovn-control-plane" (e6a5ca61-cf8b-4d46-bbe9-d38b2f3d4ebc) [ingress]
    *      "ext_ovn-worker" (eb511c92-a224-4709-931a-b6a3a5289dfc) [ingress]
    *  Logical flow: table=9 (ls_in_acl), priority=65535, match=(1), actions=(next;)
    18. metadata=0x7, priority 0, cookie 0x7106ab7b
    resubmit(,19)
    *  Logical datapaths:
    *      "ovn-worker" (29f8d327-0be2-4947-aee6-a2456e52f51a) [ingress]
    *      "ovn-control-plane" (6edbe5e2-221b-4b0e-9a3a-73d97e54b0ca) [ingress]
    *      "ovn-worker2" (9260cc1e-3ed6-4df5-8732-8463ad20760c) [ingress]
    *      "ext_ovn-worker2" (d6f5cd63-b50a-49ab-98dd-0430965868ef) [ingress]
    *      "join" (d74ad6c7-87b2-4429-8c5a-1d2ecf193d7b) [ingress]
    *      "ext_ovn-control-plane" (e6a5ca61-cf8b-4d46-bbe9-d38b2f3d4ebc) [ingress]
    *      "ext_ovn-worker" (eb511c92-a224-4709-931a-b6a3a5289dfc) [ingress]
    *  Logical flow: table=10 (ls_in_qos_mark), priority=0, match=(1), actions=(next;)
    19. metadata=0x7, priority 0, cookie 0x698dc4b8
    resubmit(,20)
    *  Logical datapaths:
    *      "ovn-worker" (29f8d327-0be2-4947-aee6-a2456e52f51a) [ingress]
    *      "ovn-control-plane" (6edbe5e2-221b-4b0e-9a3a-73d97e54b0ca) [ingress]
    *      "ovn-worker2" (9260cc1e-3ed6-4df5-8732-8463ad20760c) [ingress]
    *      "ext_ovn-worker2" (d6f5cd63-b50a-49ab-98dd-0430965868ef) [ingress]
    *      "join" (d74ad6c7-87b2-4429-8c5a-1d2ecf193d7b) [ingress]
    *      "ext_ovn-control-plane" (e6a5ca61-cf8b-4d46-bbe9-d38b2f3d4ebc) [ingress]
    *      "ext_ovn-worker" (eb511c92-a224-4709-931a-b6a3a5289dfc) [ingress]
    *  Logical flow: table=11 (ls_in_qos_meter), priority=0, match=(1), actions=(next;)
    20. metadata=0x7, priority 0, cookie 0x3141efa1
    resubmit(,21)
    *  Logical datapaths:
    *      "ovn-worker" (29f8d327-0be2-4947-aee6-a2456e52f51a) [ingress]
    *      "ovn-control-plane" (6edbe5e2-221b-4b0e-9a3a-73d97e54b0ca) [ingress]
    *      "ovn-worker2" (9260cc1e-3ed6-4df5-8732-8463ad20760c) [ingress]
    *      "ext_ovn-worker2" (d6f5cd63-b50a-49ab-98dd-0430965868ef) [ingress]
    *      "join" (d74ad6c7-87b2-4429-8c5a-1d2ecf193d7b) [ingress]
    *      "ext_ovn-control-plane" (e6a5ca61-cf8b-4d46-bbe9-d38b2f3d4ebc) [ingress]
    *      "ext_ovn-worker" (eb511c92-a224-4709-931a-b6a3a5289dfc) [ingress]
    *  Logical flow: table=12 (ls_in_stateful), priority=0, match=(1), actions=(next;)
    21. metadata=0x7, priority 0, cookie 0x2266687e
    resubmit(,22)
    *  Logical datapaths:
    *      "ovn-worker" (29f8d327-0be2-4947-aee6-a2456e52f51a) [ingress]
    *      "ovn-control-plane" (6edbe5e2-221b-4b0e-9a3a-73d97e54b0ca) [ingress]
    *      "ovn-worker2" (9260cc1e-3ed6-4df5-8732-8463ad20760c) [ingress]
    *      "ext_ovn-worker2" (d6f5cd63-b50a-49ab-98dd-0430965868ef) [ingress]
    *      "join" (d74ad6c7-87b2-4429-8c5a-1d2ecf193d7b) [ingress]
    *      "ext_ovn-control-plane" (e6a5ca61-cf8b-4d46-bbe9-d38b2f3d4ebc) [ingress]
    *      "ext_ovn-worker" (eb511c92-a224-4709-931a-b6a3a5289dfc) [ingress]
    *  Logical flow: table=13 (ls_in_pre_hairpin), priority=0, match=(1), actions=(next;)
    22. metadata=0x7, priority 0, cookie 0x44106202
    resubmit(,23)
    *  Logical datapaths:
    *      "ovn-worker" (29f8d327-0be2-4947-aee6-a2456e52f51a) [ingress]
    *      "ovn-control-plane" (6edbe5e2-221b-4b0e-9a3a-73d97e54b0ca) [ingress]
    *      "ovn-worker2" (9260cc1e-3ed6-4df5-8732-8463ad20760c) [ingress]
    *      "ext_ovn-worker2" (d6f5cd63-b50a-49ab-98dd-0430965868ef) [ingress]
    *      "join" (d74ad6c7-87b2-4429-8c5a-1d2ecf193d7b) [ingress]
    *      "ext_ovn-control-plane" (e6a5ca61-cf8b-4d46-bbe9-d38b2f3d4ebc) [ingress]
    *      "ext_ovn-worker" (eb511c92-a224-4709-931a-b6a3a5289dfc) [ingress]
    *  Logical flow: table=14 (ls_in_nat_hairpin), priority=0, match=(1), actions=(next;)
    23. metadata=0x7, priority 0, cookie 0xbf13b989
    resubmit(,24)
    *  Logical datapaths:
    *      "ovn-worker" (29f8d327-0be2-4947-aee6-a2456e52f51a) [ingress]
    *      "ovn-control-plane" (6edbe5e2-221b-4b0e-9a3a-73d97e54b0ca) [ingress]
    *      "ovn-worker2" (9260cc1e-3ed6-4df5-8732-8463ad20760c) [ingress]
    *      "ext_ovn-worker2" (d6f5cd63-b50a-49ab-98dd-0430965868ef) [ingress]
    *      "join" (d74ad6c7-87b2-4429-8c5a-1d2ecf193d7b) [ingress]
    *      "ext_ovn-control-plane" (e6a5ca61-cf8b-4d46-bbe9-d38b2f3d4ebc) [ingress]
    *      "ext_ovn-worker" (eb511c92-a224-4709-931a-b6a3a5289dfc) [ingress]
    *  Logical flow: table=15 (ls_in_hairpin), priority=0, match=(1), actions=(next;)
    24. reg14=0x1,metadata=0x7, priority 100, cookie 0xbde76cc4
    resubmit(,25)
    *  Logical datapaths:
    *      "ext_ovn-worker" (eb511c92-a224-4709-931a-b6a3a5289dfc) [ingress]
    *  Logical flow: table=16 (ls_in_arp_rsp), priority=100, match=(inport == "breth0_ovn-worker), actions=(next;)
    *  Logical Switch Port: breth0_ovn-worker type localnet (addresses ['unknown'], dynamic addresses [], security []
    25. metadata=0x7, priority 0, cookie 0x63050c7f
    resubmit(,26)
    *  Logical datapaths:
    *      "ovn-worker" (29f8d327-0be2-4947-aee6-a2456e52f51a) [ingress]
    *      "ovn-control-plane" (6edbe5e2-221b-4b0e-9a3a-73d97e54b0ca) [ingress]
    *      "ovn-worker2" (9260cc1e-3ed6-4df5-8732-8463ad20760c) [ingress]
    *      "ext_ovn-worker2" (d6f5cd63-b50a-49ab-98dd-0430965868ef) [ingress]
    *      "join" (d74ad6c7-87b2-4429-8c5a-1d2ecf193d7b) [ingress]
    *      "ext_ovn-control-plane" (e6a5ca61-cf8b-4d46-bbe9-d38b2f3d4ebc) [ingress]
    *      "ext_ovn-worker" (eb511c92-a224-4709-931a-b6a3a5289dfc) [ingress]
    *  Logical flow: table=17 (ls_in_dhcp_options), priority=0, match=(1), actions=(next;)
    26. metadata=0x7, priority 0, cookie 0xb5e5b1c1
    resubmit(,27)
    *  Logical datapaths:
    *      "ovn-worker" (29f8d327-0be2-4947-aee6-a2456e52f51a) [ingress]
    *      "ovn-control-plane" (6edbe5e2-221b-4b0e-9a3a-73d97e54b0ca) [ingress]
    *      "ovn-worker2" (9260cc1e-3ed6-4df5-8732-8463ad20760c) [ingress]
    *      "ext_ovn-worker2" (d6f5cd63-b50a-49ab-98dd-0430965868ef) [ingress]
    *      "join" (d74ad6c7-87b2-4429-8c5a-1d2ecf193d7b) [ingress]
    *      "ext_ovn-control-plane" (e6a5ca61-cf8b-4d46-bbe9-d38b2f3d4ebc) [ingress]
    *      "ext_ovn-worker" (eb511c92-a224-4709-931a-b6a3a5289dfc) [ingress]
    *  Logical flow: table=18 (ls_in_dhcp_response), priority=0, match=(1), actions=(next;)
    27. metadata=0x7, priority 0, cookie 0x5c30dc1b
    resubmit(,28)
    *  Logical datapaths:
    *      "ovn-worker" (29f8d327-0be2-4947-aee6-a2456e52f51a) [ingress]
    *      "ovn-control-plane" (6edbe5e2-221b-4b0e-9a3a-73d97e54b0ca) [ingress]
    *      "ovn-worker2" (9260cc1e-3ed6-4df5-8732-8463ad20760c) [ingress]
    *      "ext_ovn-worker2" (d6f5cd63-b50a-49ab-98dd-0430965868ef) [ingress]
    *      "join" (d74ad6c7-87b2-4429-8c5a-1d2ecf193d7b) [ingress]
    *      "ext_ovn-control-plane" (e6a5ca61-cf8b-4d46-bbe9-d38b2f3d4ebc) [ingress]
    *      "ext_ovn-worker" (eb511c92-a224-4709-931a-b6a3a5289dfc) [ingress]
    *  Logical flow: table=19 (ls_in_dns_lookup), priority=0, match=(1), actions=(next;)
    28. metadata=0x7, priority 0, cookie 0x6141f050
    resubmit(,29)
    *  Logical datapaths:
    *      "ovn-worker" (29f8d327-0be2-4947-aee6-a2456e52f51a) [ingress]
    *      "ovn-control-plane" (6edbe5e2-221b-4b0e-9a3a-73d97e54b0ca) [ingress]
    *      "ovn-worker2" (9260cc1e-3ed6-4df5-8732-8463ad20760c) [ingress]
    *      "ext_ovn-worker2" (d6f5cd63-b50a-49ab-98dd-0430965868ef) [ingress]
    *      "join" (d74ad6c7-87b2-4429-8c5a-1d2ecf193d7b) [ingress]
    *      "ext_ovn-control-plane" (e6a5ca61-cf8b-4d46-bbe9-d38b2f3d4ebc) [ingress]
    *      "ext_ovn-worker" (eb511c92-a224-4709-931a-b6a3a5289dfc) [ingress]
    *  Logical flow: table=20 (ls_in_dns_response), priority=0, match=(1), actions=(next;)
    29. metadata=0x7, priority 0, cookie 0x6dc563f6
    resubmit(,30)
    *  Logical datapaths:
    *      "ovn-worker" (29f8d327-0be2-4947-aee6-a2456e52f51a) [ingress]
    *      "ovn-control-plane" (6edbe5e2-221b-4b0e-9a3a-73d97e54b0ca) [ingress]
    *      "ovn-worker2" (9260cc1e-3ed6-4df5-8732-8463ad20760c) [ingress]
    *      "ext_ovn-worker2" (d6f5cd63-b50a-49ab-98dd-0430965868ef) [ingress]
    *      "join" (d74ad6c7-87b2-4429-8c5a-1d2ecf193d7b) [ingress]
    *      "ext_ovn-control-plane" (e6a5ca61-cf8b-4d46-bbe9-d38b2f3d4ebc) [ingress]
    *      "ext_ovn-worker" (eb511c92-a224-4709-931a-b6a3a5289dfc) [ingress]
    *  Logical flow: table=21 (ls_in_external_port), priority=0, match=(1), actions=(next;)
    30. metadata=0x7, priority 0, cookie 0xbb40340d
    set_field:0->reg15
    resubmit(,71)
    *  Logical datapaths:
    *      "ovn-worker" (29f8d327-0be2-4947-aee6-a2456e52f51a) [ingress]
    *      "ovn-control-plane" (6edbe5e2-221b-4b0e-9a3a-73d97e54b0ca) [ingress]
    *      "ovn-worker2" (9260cc1e-3ed6-4df5-8732-8463ad20760c) [ingress]
    *      "ext_ovn-worker2" (d6f5cd63-b50a-49ab-98dd-0430965868ef) [ingress]
    *      "join" (d74ad6c7-87b2-4429-8c5a-1d2ecf193d7b) [ingress]
    *      "ext_ovn-control-plane" (e6a5ca61-cf8b-4d46-bbe9-d38b2f3d4ebc) [ingress]
    *      "ext_ovn-worker" (eb511c92-a224-4709-931a-b6a3a5289dfc) [ingress]
    *  Logical flow: table=22 (ls_in_l2_lkup), priority=0, match=(1), actions=(outport = get_fdb(eth.dst); next;)
    71. reg0=0x2, priority 0
    drop
    resubmit(,31)
    31. reg15=0,metadata=0x7, priority 50, cookie 0xfe590022
    set_field:0x8001->reg15
    resubmit(,37)
    *  Logical datapaths:
    *      "ext_ovn-worker2" (d6f5cd63-b50a-49ab-98dd-0430965868ef) [ingress]
    *      "ext_ovn-control-plane" (e6a5ca61-cf8b-4d46-bbe9-d38b2f3d4ebc) [ingress]
    *      "ext_ovn-worker" (eb511c92-a224-4709-931a-b6a3a5289dfc) [ingress]
    *  Logical flow: table=23 (ls_in_l2_unknown), priority=50, match=(outport == "none), actions=(outport = "_MC_unknown"; output;)
    37. priority 0
    resubmit(,38)
    38. reg15=0x8001,metadata=0x7, priority 100, cookie 0xc218d347
    set_field:0x1->reg15
    resubmit(,39)
    *  Logical datapath: "ext_ovn-worker" (eb511c92-a224-4709-931a-b6a3a5289dfc)
    *  Multicast Group: name "_MC_unknown", tunnel_key 32769 ports: (breth0_ovn-worker)
    39. reg10=0/0x1,reg14=0x1,reg15=0x1,metadata=0x7, priority 100, cookie 0x7aed837a
    drop
    set_field:0x8001->reg15
    *  Logical datapath: "ext_ovn-worker" (eb511c92-a224-4709-931a-b6a3a5289dfc)
    *  Port Binding: logical_port "breth0_ovn-worker", tunnel_key 1, 

    Final flow: unchanged
    Megaflow: recirc_id=0x1,ct_state=-new+est-rel+trk,ct_mark=0,ct_label=0/0x2,eth,ip,in_port=1,dl_src=00:00:00:00:00:00,dl_dst=00:00:00:00:00:00,nw_proto=0,nw_frag=no
    Datapath actions: 100

* **Note** This reveals a limitation of offline analysis, as unlike the OpenFlow ports which are consistent between the live and offline set-ups, the live datapath information is unavailable to our offline replica, and therefore the port numbers will not match.
That being said, a quick comparison between dpif/show online and offline will reveal that there is still a 1 to 1 relationship betweem the ports despite their different numbers, and in this case the offline datapath port 100 corresponds to the live datapath port 5 (so this is in fact the same datapath action as the datapath flow the OpenFlow flow for the trace was derived from).

As you can see, ovn-detrace will annotate the proto/trace output with the logical flows that yield those OpenFlow flows.

Additional information regarding ovn-detrace can be found here: https://man7.org/linux/man-pages/man1/ovn-detrace.1.html


.. _sos-report: https://github.com/sosreport/sos
.. _OVN_kubernetes: https://github.com/ovn-org/ovn-kubernetes/blob/master/docs/kind.md
.. _ovs-vswitchd: http://www.openvswitch.org//support/dist-docs/ovs-vswitchd.8.html#:~:text=OpenFlow%0A%20%20%20%20%20%20%20%20%20%20%20%20%20%20flow%20entries.-,OFPROTO%20COMMANDS,-These%20commands%20manage
.. _ovn-sbctl_man-pages: https://man7.org/linux/man-pages/man8/ovn-sbctl.8.html#:~:text=the%20Address_Set%20table.-,Database%20Values,-Each%20column%20in
.. _ovn-nbctl_man-pages: https://man7.org/linux/man-pages/man8/ovn-nbctl.8.html#:~:text=Identifying%20Tables%2C%20Records%2C%20and%20Columns
.. _rhel-support-tools: https://catalog.redhat.com/software/containers/rhel7/support-tools/5a2537edac3db95fc9966015?container-tabs=overview&gti-tabs=red-hat-login