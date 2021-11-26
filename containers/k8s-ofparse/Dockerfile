FROM quay.io/fedora/fedora:33-x86_64

RUN dnf install -y git jq python3-pip python3 openvswitch ovn && dnf clean all && rm -rf /var/cache/dnf/*

RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
RUN mv kubectl /usr/local/bin
RUN chmod +x /usr/local/bin/kubectl

ADD . /root/ovs-dbg
WORKDIR /root/ovs-dbg
RUN python3 -m pip install .

WORKDIR /root
ADD containers/k8s-ofparse/monitor.sh /root/
ENTRYPOINT ["/root/monitor.sh"]

