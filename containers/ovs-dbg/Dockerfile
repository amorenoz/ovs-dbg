#Image to run ovs and ovsdb-server for debugging purpuses

FROM quay.io/fedora/fedora:31-x86_64 as build

#RUN dnf -y groupinstall "Development Tools"
RUN dnf -y install gcc make autoconf automake libtool diffutils file
RUN dnf -y install libcap-ng-devel openssl-devel libatomic 

RUN dnf -y install git

ARG OVS_REPO=https://github.com/openvswitch/ovs.git
ARG OVS_COMMIT=branch-2.15
RUN echo "Building ovs from ${OVS_REPO} at ${OVS_COMMIT}"

WORKDIR /src
RUN git clone ${OVS_REPO} && cd ovs && git checkout ${OVS_COMMIT}

WORKDIR /src/ovs
RUN ./boot.sh
RUN ./configure CFLAGS="-g -O0"
RUN make && make install

# Create new layer
FROM quay.io/fedora/fedora:31-x86_64

COPY --from=build /usr/local/bin/ovs* /usr/local/bin/
COPY --from=build /usr/local/bin/vtep* /usr/local/bin/
COPY --from=build /usr/local/sbin/* /usr/local/sbin/
COPY --from=build /usr/local/etc/openvswitch /usr/local/etc/openvswitch
COPY --from=build /usr/local/share/openvswitch /usr/local/share/openvswitch
COPY --from=build /usr/local/lib/lib* /usr/local/lib/

RUN dnf install -y libatomic openssl gdb jq ovn-central

RUN mkdir -p /usr/local/var/run/openvswitch

ADD start.sh /
ENTRYPOINT ["/start.sh"]

