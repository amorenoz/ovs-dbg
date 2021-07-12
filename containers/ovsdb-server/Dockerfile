FROM gcc:10.3 as build

ARG OVS_VERSION=v2.15.0
ADD https://github.com/openvswitch/ovs/archive/${OVS_VERSION}.tar.gz /src/

WORKDIR /src
RUN mkdir -p /src/ovs
RUN tar --strip-components=1 -C ovs -xvf ${OVS_VERSION}.tar.gz

WORKDIR /src/ovs
RUN ./boot.sh
RUN ./configure
RUN make && make install

FROM fedora:33

COPY --from=build /usr/local/bin/ovs* /usr/local/bin/
COPY --from=build /usr/local/bin/vtep* /usr/local/bin/
COPY --from=build /usr/local/sbin/* /usr/local/sbin/
COPY --from=build /usr/local/etc/openvswitch /usr/local/etc/openvswitch
COPY --from=build /usr/local/share/openvswitch /usr/local/share/openvswitch
COPY --from=build /usr/local/lib/lib* /usr/local/lib/

RUN dnf install -y libatomic

#RUN ovsdb-tool create /usr/local/etc/openvswitch/conf.db /usr/local/share/openvswitch/vswitch.ovsschema

RUN mkdir -p /usr/local/var/run/openvswitch

ADD start.sh /

ENTRYPOINT ["/start.sh"]


