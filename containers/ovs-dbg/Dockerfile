# OVS-DBG container image
# cli suggestion:
# sudo podman run -it --rm -v $PWD:/work --privileged --network=host --pid=host   -v /lib/modules:/lib/modules:ro -v /proc:/proc -v /:/mnt/rootdir quay.io/amorenoz/ovs-dbg:next

# build layer: Build ovs.
FROM quay.io/fedora/fedora:41-x86_64 as build

#RUN dnf -y groupinstall "Development Tools"
RUN dnf -y install gcc make autoconf automake libtool diffutils file \
           libcap-ng-devel openssl-devel libatomic python3

RUN dnf -y install git

ARG OVS_REPO=https://github.com/openvswitch/ovs.git
ARG OVS_COMMIT=main
RUN echo "Building ovs from ${OVS_REPO} at ${OVS_COMMIT}"

WORKDIR /src
RUN git clone --depth 1 ${OVS_REPO} --single-branch --branch ${OVS_COMMIT}

WORKDIR /src/ovs
RUN ./boot.sh
RUN ./configure  --prefix=/usr CFLAGS="-g -O0"
RUN make && make install

# Actual container layer
FROM quay.io/fedora/fedora:41-x86_64

COPY --from=build /usr/bin/ovs* /usr/bin/
COPY --from=build /usr/bin/vtep* /usr/bin/
COPY --from=build /usr/sbin/* /usr/sbin/
COPY --from=build /etc/openvswitch /usr/etc/openvswitch
COPY --from=build /usr/share/openvswitch /usr/share/openvswitch
COPY --from=build /usr/lib/* /usr/lib/

# Workaround for https://github.com/iovisor/bcc/commit/eb7cdd28a45e48d9318b0cb3f35d1bb6f01a6611
RUN INSTALL_PKGS=" \
	https://kojipkgs.fedoraproject.org//packages/bcc/0.32.0/1.fc42/x86_64/bcc-0.32.0-1.fc42.x86_64.rpm \
	https://kojipkgs.fedoraproject.org//packages/bcc/0.32.0/1.fc42/x86_64/bcc-tools-0.32.0-1.fc42.x86_64.rpm \
	https://kojipkgs.fedoraproject.org//packages/bcc/0.32.0/1.fc42/noarch/python3-bcc-0.32.0-1.fc42.noarch.rpm \
" && \
    dnf install -y --setopt=tsflags=nodocs $INSTALL_PKGS

# Install retis from f43
RUN INSTALL_PKGS=" \
        https://kojipkgs.fedoraproject.org//packages/retis/1.5.2/0.fc43/x86_64/retis-1.5.2-0.fc43.x86_64.rpm \
" && \
    dnf install -y --setopt=tsflags=nodocs $INSTALL_PKGS

RUN INSTALL_PKGS=" \
	libatomic openssl gdb jq ovn-central perf python3 \
	iproute iputils tcpdump socat procps curl git go python3-scapy python3-psutil \
	sysstat tcpdump iotop htop strace valgrind elfutils pciutils nftables net-tools iftop \
	flamegraph flamegraph-stackcollapse.noarch flamegraph-stackcollapse-perf.noarch bpftrace \
" && \
    dnf install --best --refresh -y --setopt=tsflags=nodocs $INSTALL_PKGS && \
    dnf clean all && rm -rf /var/cache/dnf/*

RUN mkdir -p /var/run/openvswitch

ENV GOPATH=$HOME/go

RUN cd /root/ && git clone --depth 1 https://github.com/amorenoz/ovsdb-mon.git --single-branch --branch main
RUN cd /root/ovsdb-mon && go install github.com/ovn-org/libovsdb/cmd/modelgen && go mod vendor

WORKDIR /root

ADD motd /etc/motd
ADD entrypoint.sh /
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
