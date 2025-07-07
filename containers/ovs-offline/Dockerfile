#Image to run ovs and ovsdb-server for debugging purpuses

FROM quay.io/fedora/fedora:41-x86_64 as build

#RUN dnf -y groupinstall "Development Tools"
RUN dnf -y install gcc make autoconf automake libtool diffutils file python  \
    libcap-ng-devel openssl-devel libatomic git

ARG OVS_REPO=https://github.com/openvswitch/ovs.git
ARG OVS_COMMIT=main
RUN echo "Building ovs from ${OVS_REPO} at ${OVS_COMMIT}"

WORKDIR /src
RUN git clone ${OVS_REPO} && cd ovs && git checkout ${OVS_COMMIT}

WORKDIR /src/ovs
RUN ./boot.sh
RUN ./configure CFLAGS="-g -O0" --prefix=/usr/
RUN make && make install

# Create new layer
FROM quay.io/fedora/fedora:41-x86_64

COPY --from=build /usr/bin/ovs* /usr/bin/
COPY --from=build /usr/bin/vtep* /usr/bin/
COPY --from=build /usr/sbin/* /usr/sbin/
COPY --from=build /etc/openvswitch /usr/etc/openvswitch
COPY --from=build /usr/share/openvswitch /usr/share/openvswitch
COPY --from=build /usr/lib64/lib* /usr/lib/

RUN dnf install -y libatomic openssl gdb jq ovn-central bcc bcc-tools perf

RUN mkdir -p /var/run/openvswitch

ADD start.sh /
ENTRYPOINT ["/start.sh"]

