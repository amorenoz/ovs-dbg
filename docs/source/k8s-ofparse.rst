===================================================
k8s-ovs-ofparse: Online flow analysis in Kubernetes
===================================================

k8s-ofparse is essentially a container a Kubernetes deployment manifest.

It deploys two main components:

- k8s-ofparse client: is a daemonset that is deployed on every node. It exposes the openflow control interface of the local br-int on the NODE_IP
- k8s-ofparse monitor: is a pod that uses "ovs-ofctl" to synchronize the flows from all the nodes into files so you can run ofparse_ on it.



.. _ofparse: ofparse.html

Diagram
*******


::

              ┌───────────────────┐
              │    ovn control    │
              │                   │
              │ ┌───────────────┐ │
              │ │ k8s-ofparse   │ │
              │ │    monitor    │ │
              └─┴────┬─────┬────┴─┘
                     │     │
           ┌─────────┘     └──────────┐
           │                          │
           │NODE_IP:16440             │NODE_IP:16440
    ┌─┬────┴────────┬───┐   ┌───┬─────┴───────┬─┐
    │ │ k8s-ofparse │   │   │   │ k8s-ofparse │ │
    │ │   client    │   │   │   │   client    │ │
    │ │             │   │   │   │             │ │
    │ └─────────────┘   │   │   └─────────────┘ │   ...
    │                   │   │                   │
    │ ┌────────────┐    │   │   ┌───────────┐   │
    │ │  br-int    │    │   │   │ br-int    │   │
    │ └────────────┘    │   │   └───────────┘   │
    │                   │   │                   │
    └───────────────────┘   └───────────────────┘


Usage
*****

::

    $ kubectl apply -f k8s/k8s-ofparse.yaml
    $ kubectl exec -it k8s-ofparse-main -- bash
    ==============================
            k8s-ofparse
    ==============================

    The flows from the following nodes are being synchronized into files ({Node Name} ==> {File Path}):

     - ovn-worker2  ==>  /tmp/k8s-ofparse/ovn-worker2.flows
     - ovn-control-plane  ==>  /tmp/k8s-ofparse/ovn-control-plane.flows
     - ovn-worker  ==>  /tmp/k8s-ofparse/ovn-worker.flows

    You can use "ofparse -i {filename} ..." to look at any individual node
    Also, you can use "k8s-ovs-ofparse ..." to look at all the nodes

    Please report bugs or RFEs to https://github.com/amorenoz/ovs-dbg


