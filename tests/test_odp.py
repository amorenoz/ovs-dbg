import netaddr
import pytest

from ovs_dbg.odp import ODPFlow
from ovs_dbg.kv import KeyValue
from ovs_dbg.decoders import EthMask, IPMask


@pytest.mark.parametrize(
    "input_string,expected",
    [
        (
            "skb_priority(0x123),skb_mark(0x123),recirc_id(0x123),dp_hash(0x123),ct_zone(0x123), actions:",
            [
                KeyValue(
                    "skb_priority",
                    {
                        "value": 0x123,
                        "mask": 0xFFFFFFFF,
                    },
                ),
                KeyValue(
                    "skb_mark",
                    {
                        "value": 0x123,
                        "mask": 0xFFFFFFFF,
                    },
                ),
                KeyValue("recirc_id", 0x123),
                KeyValue(
                    "dp_hash",
                    {
                        "value": 0x123,
                        "mask": 0xFFFFFFFF,
                    },
                ),
                KeyValue(
                    "ct_zone",
                    {
                        "value": 0x123,
                        "mask": 0xFFFF,
                    },
                ),
            ],
        ),
        (
            "tunnel(tun_id=0x7f10354,src=10.10.10.10,dst=20.20.20.20,ttl=64,flags(csum|key)) actions:",
            [
                KeyValue(
                    "tunnel",
                    {
                        "tun_id": 0x7F10354,
                        "src": IPMask("10.10.10.10"),
                        "dst": IPMask("20.20.20.20"),
                        "ttl": 64,
                        "flags": "csum|key",
                    },
                )
            ],
        ),
        (
            "tunnel(geneve({class=0,type=0,len=4,0xa/0xff}),vxlan(flags=0x800000,vni=0x1c7),erspan(ver=2,dir=1,hwid=0x1)), actions:",
            [
                KeyValue(
                    "tunnel",
                    {
                        "geneve": {
                            "class": {"value": 0, "mask": 0xFFFF},
                            "type": {"value": 0, "mask": 0xFF},
                            "len": {"value": 4, "mask": 0xFF},
                            "data": {"value": 0xA, "mask": 0xFF},
                        },
                        "vxlan": {"flags": 0x800000, "vni": 0x1C7},
                        "erspan": {"ver": 2, "dir": 1, "hwid": 0x1},
                    },
                )
            ],
        ),
        (
            "in_port(2),eth(src=11:22:33:44:55:66,dst=66:55:44:33:22:11) actions:",
            [
                KeyValue("in_port", 2),
                KeyValue(
                    "eth",
                    {
                        "src": EthMask("11:22:33:44:55:66"),
                        "dst": EthMask("66:55:44:33:22:11"),
                    },
                ),
            ],
        ),
        (
            "eth_type(0x800/0x006),ipv4(src=192.168.1.1/24,dst=192.168.0.0/16,proto=0x1,tos=0x2/0xf0) actions:",
            [
                KeyValue("eth_type", {"value": 0x800, "mask": 0x006}),
                KeyValue(
                    "ipv4",
                    {
                        "src": IPMask("192.168.1.1/24"),
                        "dst": IPMask("192.168.0.0/16"),
                        "proto": {
                            "value": 0x1,
                            "mask": 0xFF,
                        },
                        "tos": {
                            "value": 0x2,
                            "mask": 0xF0,
                        },
                    },
                ),
            ],
        ),
        (
            "encap(eth_type(0x800/0x006),ipv4(src=192.168.1.1/24,dst=192.168.0.0/16,proto=0x1,tos=0x2/0xf0)) actions:",
            [
                KeyValue(
                    "encap",
                    {
                        "eth_type": {"value": 0x800, "mask": 0x006},
                        "ipv4": {
                            "src": IPMask("192.168.1.1/24"),
                            "dst": IPMask("192.168.0.0/16"),
                            "proto": {
                                "value": 0x1,
                                "mask": 0xFF,
                            },
                            "tos": {
                                "value": 0x2,
                                "mask": 0xF0,
                            },
                        },
                    },
                ),
            ],
        ),
    ],
)
def test_odp_fields(input_string, expected):
    odp = ODPFlow.from_string(input_string)
    match = odp.match_kv
    for i in range(len(expected)):
        assert expected[i].key == match[i].key
        assert expected[i].value == match[i].value

        # Assert positions relative to action string are OK
        mpos = odp.meta.mpos
        mstring = odp.meta.mstring

        kpos = match[i].meta.kpos
        kstr = match[i].meta.kstring
        vpos = match[i].meta.vpos
        vstr = match[i].meta.vstring
        assert mstring[kpos : kpos + len(kstr)] == kstr
        if vpos != -1:
            assert mstring[vpos : vpos + len(vstr)] == vstr

        # assert mstring meta is correct
        assert input_string[mpos : mpos + len(mstring)] == mstring


@pytest.mark.parametrize(
    "input_string,expected",
    [
        (
            "actions:ct"
            ",ct(commit)"
            ",ct(commit,zone=5)"
            ",ct(commit,mark=0xa0a0a0a0/0xfefefefe)"
            ",ct(commit,label=0x1234567890abcdef1234567890abcdef/0xf1f2f3f4f5f6f7f8f9f0fafbfcfdfeff)"
            ",ct(commit,helper=ftp)"
            ",ct(commit,helper=tftp)"
            ",ct(commit,timeout=ovs_tp_1_tcp4)"
            ",ct(nat)",
            [
                KeyValue("ct", True),
                KeyValue("ct", {"commit": True}),
                KeyValue("ct", {"commit": True, "zone": 5}),
                KeyValue(
                    "ct",
                    {"commit": True, "mark": {"value": 0xA0A0A0A0, "mask": 0xFEFEFEFE}},
                ),
                KeyValue(
                    "ct",
                    {
                        "commit": True,
                        "label": {
                            "value": 0x1234567890ABCDEF1234567890ABCDEF,
                            "mask": 0xF1F2F3F4F5F6F7F8F9F0FAFBFCFDFEFF,
                        },
                    },
                ),
                KeyValue("ct", {"commit": True, "helper": "ftp"}),
                KeyValue("ct", {"commit": True, "helper": "tftp"}),
                KeyValue("ct", {"commit": True, "timeout": "ovs_tp_1_tcp4"}),
                KeyValue("ct", {"nat": True}),
            ],
        ),
        (
            "actions:ct(nat)"
            ",ct(commit,nat(src))"
            ",ct(commit,nat(dst))"
            ",ct(commit,nat(src=10.0.0.240,random))"
            ",ct(commit,nat(src=10.0.0.240:32768-65535,random))"
            ",ct(commit,nat(dst=10.0.0.128-10.0.0.254,hash))"
            ",ct(commit,nat(src=10.0.0.240-10.0.0.254:32768-65535,persistent))"
            ",ct(commit,nat(src=fe80::20c:29ff:fe88:a18b,random))"
            ",ct(commit,nat(src=fe80::20c:29ff:fe88:1-fe80::20c:29ff:fe88:a18b,random))"
            ",ct(commit,nat(src=[[fe80::20c:29ff:fe88:1]]-[[fe80::20c:29ff:fe88:a18b]]:255-4096,random))"
            ",ct(commit,helper=ftp,nat(src=10.1.1.240-10.1.1.255))"
            ",ct(force_commit)",
            [
                KeyValue("ct", {"nat": True}),
                KeyValue("ct", {"commit": True, "nat": {"type": "src"}}),
                KeyValue("ct", {"commit": True, "nat": {"type": "dst"}}),
                KeyValue(
                    "ct",
                    {
                        "commit": True,
                        "nat": {
                            "type": "src",
                            "addrs": {
                                "start": netaddr.IPAddress("10.0.0.240"),
                                "end": netaddr.IPAddress("10.0.0.240"),
                            },
                            "random": True,
                        },
                    },
                ),
                KeyValue(
                    "ct",
                    {
                        "commit": True,
                        "nat": {
                            "type": "src",
                            "addrs": {
                                "start": netaddr.IPAddress("10.0.0.240"),
                                "end": netaddr.IPAddress("10.0.0.240"),
                            },
                            "ports": {
                                "start": 32768,
                                "end": 65535,
                            },
                            "random": True,
                        },
                    },
                ),
                KeyValue(
                    "ct",
                    {
                        "commit": True,
                        "nat": {
                            "type": "dst",
                            "addrs": {
                                "start": netaddr.IPAddress("10.0.0.128"),
                                "end": netaddr.IPAddress("10.0.0.254"),
                            },
                            "hash": True,
                        },
                    },
                ),
                KeyValue(
                    "ct",
                    {
                        "commit": True,
                        "nat": {
                            "type": "src",
                            "addrs": {
                                "start": netaddr.IPAddress("10.0.0.240"),
                                "end": netaddr.IPAddress("10.0.0.254"),
                            },
                            "ports": {
                                "start": 32768,
                                "end": 65535,
                            },
                            "persistent": True,
                        },
                    },
                ),
                KeyValue(
                    "ct",
                    {
                        "commit": True,
                        "nat": {
                            "type": "src",
                            "addrs": {
                                "start": netaddr.IPAddress("fe80::20c:29ff:fe88:a18b"),
                                "end": netaddr.IPAddress("fe80::20c:29ff:fe88:a18b"),
                            },
                            "random": True,
                        },
                    },
                ),
                KeyValue(
                    "ct",
                    {
                        "commit": True,
                        "nat": {
                            "type": "src",
                            "addrs": {
                                "start": netaddr.IPAddress("fe80::20c:29ff:fe88:1"),
                                "end": netaddr.IPAddress("fe80::20c:29ff:fe88:a18b"),
                            },
                            "random": True,
                        },
                    },
                ),
                KeyValue(
                    "ct",
                    {
                        "commit": True,
                        "nat": {
                            "type": "src",
                            "addrs": {
                                "start": netaddr.IPAddress("fe80::20c:29ff:fe88:1"),
                                "end": netaddr.IPAddress("fe80::20c:29ff:fe88:a18b"),
                            },
                            "ports": {
                                "start": 255,
                                "end": 4096,
                            },
                            "random": True,
                        },
                    },
                ),
                KeyValue(
                    "ct",
                    {
                        "commit": True,
                        "nat": {
                            "type": "src",
                            "addrs": {
                                "start": netaddr.IPAddress("10.1.1.240"),
                                "end": netaddr.IPAddress("10.1.1.255"),
                            },
                        },
                        "helper": "ftp",
                    },
                ),
                KeyValue("ct", {"force_commit": True}),
            ],
        ),
        (
            "actions:set(tunnel(tun_id=0xabcdef1234567890,src=1.1.1.1,dst=2.2.2.2,ttl=64,flags(df|csum|key)))"
            ",tnl_pop(4)"
            ",tnl_push(tnl_port(6),header(size=50,type=4,eth(dst=f8:bc:12:44:34:b6,src=f8:bc:12:46:58:e0,dl_type=0x0800),ipv4(src=1.1.2.88,dst=1.1.2.92,proto=17,tos=0,ttl=64,frag=0x4000),udp(src=0,dst=4789,csum=0x0),vxlan(flags=0x8000000,vni=0x1c7)),out_port(1))"
            ",tnl_push(tnl_port(6),header(size=70,type=4,eth(dst=f8:bc:12:44:34:b6,src=f8:bc:12:46:58:e0,dl_type=0x86dd),ipv6(src=2001:cafe::88,dst=2001:cafe::92,label=0,proto=17,tclass=0x0,hlimit=64),udp(src=0,dst=4789,csum=0x0),vxlan(flags=0x8000000,vni=0x1c7)),out_port(1))",
            [
                KeyValue(
                    "set",
                    {
                        "tunnel": {
                            "tun_id": 0xABCDEF1234567890,
                            "src": IPMask("1.1.1.1"),
                            "dst": IPMask("2.2.2.2"),
                            "ttl": 64,
                            "flags": "df|csum|key",
                        }
                    },
                ),
                KeyValue("tnl_pop", 4),
                KeyValue(
                    "tnl_push",
                    {
                        "tnl_port": 6,
                        "header": {
                            "size": 50,
                            "type": 4,
                            "eth": {
                                "dst": EthMask("f8:bc:12:44:34:b6"),
                                "src": EthMask("f8:bc:12:46:58:e0"),
                                "dl_type": 0x800,
                            },
                            "ipv4": {
                                "src": IPMask("1.1.2.88"),
                                "dst": IPMask("1.1.2.92"),
                                "proto": 17,
                                "tos": 0,
                                "ttl": 64,
                                "frag": 0x4000,
                            },
                            "udp": {"src": 0, "dst": 4789, "csum": 0x0},
                            "vxlan": {
                                "flags": 0x8000000,
                                "vni": 0x1C7,
                            },
                        },
                        "out_port": 1,
                    },
                ),
                KeyValue(
                    "tnl_push",
                    {
                        "tnl_port": 6,
                        "header": {
                            "size": 70,
                            "type": 4,
                            "eth": {
                                "dst": EthMask("f8:bc:12:44:34:b6"),
                                "src": EthMask("f8:bc:12:46:58:e0"),
                                "dl_type": 0x86DD,
                            },
                            "ipv6": {
                                "src": IPMask("2001:cafe::88"),
                                "dst": IPMask("2001:cafe::92"),
                                "label": 0,
                                "proto": 17,
                                "tclass": 0x0,
                                "hlimit": 64,
                            },
                            "udp": {"src": 0, "dst": 4789, "csum": 0x0},
                            "vxlan": {
                                "flags": 0x8000000,
                                "vni": 0x1C7,
                            },
                        },
                        "out_port": 1,
                    },
                ),
            ],
        ),
        (
            "actions:tnl_push(header(geneve(oam,vni=0x1c7)))"
            ",tnl_push(header(geneve(crit,vni=0x1c7,options({class=0xffff,type=0x80,len=4,0xa}))))"
            ",tnl_push(header(gre((flags=0xa000,proto=0x6558),csum=0x0,key=0x1e241)))",
            [
                KeyValue(
                    "tnl_push",
                    {
                        "header": {
                            "geneve": {
                                "oam": True,
                                "vni": 0x1C7,
                            }
                        }
                    },
                ),
                KeyValue(
                    "tnl_push",
                    {
                        "header": {
                            "geneve": {
                                "crit": True,
                                "vni": 0x1C7,
                                "options": {
                                    "class": 0xFFFF,
                                    "type": 0x80,
                                    "len": 4,
                                    "data": 0xA,
                                },
                            }
                        }
                    },
                ),
                KeyValue(
                    "tnl_push",
                    {
                        "header": {
                            "gre": {
                                "flags": 0xA000,
                                "proto": 0x6558,
                                "key": 0x1E241,
                                "csum": 0x0,
                            }
                        }
                    },
                ),
            ],
        ),
        (
            "actions:clone(1)" ",clone(clone(push_vlan(vid=12,pcp=0),2),1)",
            [
                KeyValue("clone", {"output": {"port": 1}}),
                KeyValue(
                    "clone",
                    {
                        "output": {"port": 1},
                        "clone": {
                            "push_vlan": {
                                "vid": 12,
                                "pcp": 0,
                            },
                            "output": {"port": 2},
                        },
                    },
                ),
            ],
        ),
        (
            "actions: check_pkt_len(size=200,gt(4),le(5))"
            ",check_pkt_len(size=200,gt(drop),le(5))"
            ",check_pkt_len(size=200,gt(ct(nat)),le(drop))",
            [
                KeyValue(
                    "check_pkt_len",
                    {
                        "size": 200,
                        "gt": {"output": {"port": 4}},
                        "le": {"output": {"port": 5}},
                    },
                ),
                KeyValue(
                    "check_pkt_len",
                    {
                        "size": 200,
                        "gt": {"drop": True},
                        "le": {"output": {"port": 5}},
                    },
                ),
                KeyValue(
                    "check_pkt_len",
                    {
                        "size": 200,
                        "gt": {"ct": {"nat": True}},
                        "le": {"drop": True},
                    },
                ),
            ],
        ),
    ],
)
def test_odp_actions(input_string, expected):
    odp = ODPFlow.from_string(input_string)
    actions = odp.actions_kv
    for i in range(len(expected)):
        assert expected[i].key == actions[i].key
        assert expected[i].value == actions[i].value

        # Assert positions relative to action string are OK
        apos = odp.meta.apos
        astring = odp.meta.astring

        kpos = actions[i].meta.kpos
        kstr = actions[i].meta.kstring
        vpos = actions[i].meta.vpos
        vstr = actions[i].meta.vstring
        assert astring[kpos : kpos + len(kstr)] == kstr
        if vpos != -1:
            assert astring[vpos : vpos + len(vstr)] == vstr

        # assert astring meta is correct
        assert input_string[apos : apos + len(astring)] == astring