#Image to run ovs and ovsdb-server for debugging purpuses

FROM quay.io/fedora/fedora:31-x86_64 as build

#RUN dnf -y groupinstall "Development Tools"
RUN dnf -y install gcc make autoconf automake libtool diffutils file
RUN dnf -y install libcap-ng-devel openssl-devel libatomic 

ARG OVS_VERSION=v2.15.0
ADD https://github.com/openvswitch/ovs/archive/${OVS_VERSION}.tar.gz /src/

WORKDIR /src
RUN mkdir -p /src/ovs
RUN tar --strip-components=1 -C ovs -xvf ${OVS_VERSION}.tar.gz

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

RUN dnf install -y libatomic openssl gdb

RUN mkdir -p /usr/local/var/run/openvswitch

ADD start.sh /
ENTRYPOINT ["/start.sh"]

