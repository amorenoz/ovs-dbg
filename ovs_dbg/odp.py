""" Defines an Openvswitch Datapath Flow
"""
from functools import partial
from dataclasses import dataclass

from ovs_dbg.flow import Flow, Section

from ovs_dbg.kv import (
    KVParser,
    KVDecoders,
    ParseError,
    nested_kv_decoder,
    decode_nested_kv,
)
from ovs_dbg.decoders import (
    decode_default,
    decode_time,
    decode_int,
    decode_mask,
    decode_mask8,
    decode_mask16,
    decode_mask32,
    decode_mask128,
    decode_ip,
    decode_mac,
    decode_free_output,
    decode_flag,
    decode_ip_port_range,
    decode_nat,
)


class ODPFlow(Flow):
    """Datapath Flow"""

    def __init__(self, sections, raw=""):
        """Constructor"""
        super(ODPFlow, self).__init__(sections, raw)

    @classmethod
    def from_string(cls, odp_string):
        """Parse a odp flow string

        The string is expected to have the follwoing format:
             [ufid], [match] [flow data] actions:[actions]

        Args:
            odp_string (str): a datapath flow string

        Returns:
            an ODPFlow instance
        """

        sections = []

        # If UFID present, parse it and
        ufid_pos = odp_string.find("ufid:")
        if ufid_pos >= 0:
            ufid_string = odp_string[ufid_pos : (odp_string[ufid_pos:].find(",") + 1)]
            ufid_parser = KVParser(KVDecoders({"ufid": decode_default}))
            ufid_parser.parse(ufid_string)
            if len(ufid_parser.kv()) != 1:
                raise ValueError("malformed odp flow: {}", odp_string)
            sections.append(Section("ufid", ufid_pos, ufid_string, ufid_parser.kv()))

        action_pos = odp_string.find("actions:")
        if action_pos < 0:
            raise ValueError("malformed odp flow: {}", odp_string)

        # rest of the string is between ufid and actions
        rest = odp_string[
            (ufid_pos + len(ufid_string) if ufid_pos >= 0 else 0) : action_pos
        ]

        action_pos += 8  # len("actions:")
        actions = odp_string[action_pos:]

        field_parts = rest.lstrip(" ").partition(" ")

        if len(field_parts) != 3:
            raise ValueError("malformed odp flow: {}", odp_string)

        match = field_parts[0]
        info = field_parts[2]

        info_decoders = cls._info_decoders()
        iparser = KVParser(KVDecoders(info_decoders))
        iparser.parse(info)
        isection = Section(
            name="info", pos=odp_string.find(info), string=info, data=iparser.kv()
        )
        sections.append(isection)

        mparser = cls._match_parser()
        mparser.parse(match)
        msection = Section(
            name="match", pos=odp_string.find(match), string=match, data=mparser.kv()
        )
        sections.append(msection)

        aparser = cls._action_parser()
        aparser.parse(actions)
        asection = Section(
            name="actions",
            pos=action_pos,
            string=actions,
            data=aparser.kv(),
            is_list=True,
        )
        sections.append(asection)

        return cls(sections, odp_string)

    @classmethod
    def _action_parser(cls):
        _decoders = {
            "drop": decode_flag,
            "lb_output": decode_int,
            "trunc": decode_int,
            "recirc": decode_int,
            "userspace": nested_kv_decoder(
                KVDecoders(
                    {
                        "pid": decode_int,
                        "sFlow": nested_kv_decoder(
                            KVDecoders(
                                {
                                    "vid": decode_int,
                                    "pcp": decode_int,
                                    "output": decode_int,
                                }
                            )
                        ),
                        "slow_path": decode_default,
                        "flow_sample": nested_kv_decoder(
                            KVDecoders(
                                {
                                    "probability": decode_int,
                                    "collector_sed_id": decode_int,
                                    "obs_domain_id": decode_int,
                                    "obs_point_id": decode_int,
                                    "output_port": decode_int,
                                    "ingress": decode_flag,
                                    "egress": decode_flag,
                                }
                            )
                        ),
                        "ipfix": nested_kv_decoder(
                            KVDecoders(
                                {
                                    "output_port": decode_int,
                                }
                            )
                        ),
                        "controller": nested_kv_decoder(
                            KVDecoders(
                                {
                                    "reason": decode_int,
                                    "dont_send": decode_int,
                                    "continuation": decode_int,
                                    "recirc_id": decode_int,
                                    "rule_cookie": decode_int,
                                    "controller_id": decode_int,
                                    "max_len": decode_int,
                                }
                            )
                        ),
                        "userdata": decode_default,
                        "actions": decode_flag,
                        "tunnel_out_port": decode_int,
                        "push_eth": nested_kv_decoder(
                            KVDecoders(
                                {
                                    "src": decode_mac,
                                    "dst": decode_mac,
                                    "type": decode_int,
                                }
                            )
                        ),
                        "pop_eth": decode_flag,
                    }
                )
            ),
            "set": nested_kv_decoder(KVDecoders(cls._field_decoders())),
            "push_vlan": nested_kv_decoder(
                KVDecoders(
                    {
                        "vid": decode_int,
                        "pcp": decode_int,
                        "cfi": decode_int,
                        "tpid": decode_int,
                    }
                )
            ),
            "pop_vlan": decode_flag,
            "push_nsh": nested_kv_decoder(
                KVDecoders(
                    {
                        "flags": decode_int,
                        "ttl": decode_int,
                        "mdtype": decode_int,
                        "np": decode_int,
                        "spi": decode_int,
                        "si": decode_int,
                        "c1": decode_int,
                        "c2": decode_int,
                        "c3": decode_int,
                        "c4": decode_int,
                        "md2": decode_int,
                    }
                )
            ),
            "pop_nsh": decode_flag,
            "tnl_pop": decode_int,
            "ct_clear": decode_flag,
            "ct": nested_kv_decoder(
                KVDecoders(
                    {
                        "commit": decode_flag,
                        "force_commit": decode_flag,
                        "zone": decode_int,
                        "mark": decode_mask32,
                        "label": decode_mask128,
                        "helper": decode_default,
                        "timeout": decode_default,
                        "nat": decode_nat,
                    }
                )
            ),
            **cls._tnl_action_decoder(),
        }

        _decoders["clone"] = nested_kv_decoder(
            KVDecoders(decoders=_decoders, default_free=decode_free_output)
        )

        return KVParser(
            KVDecoders(
                decoders={
                    **_decoders,
                    # "clone": nested_kv_decoder(KVDecoders(_decoders)),
                    "sample": nested_kv_decoder(
                        KVDecoders(
                            {
                                "sample": (lambda x: decode_int(x.strip("%"))),
                                "actions": nested_kv_decoder(
                                    KVDecoders(
                                        decoders=_decoders,
                                        default_free=decode_free_output,
                                    )
                                ),
                            }
                        )
                    ),
                    "check_pkt_len": nested_kv_decoder(
                        KVDecoders(
                            {
                                "size": decode_int,
                                "gt": nested_kv_decoder(
                                    KVDecoders(
                                        decoders=_decoders,
                                        default_free=decode_free_output,
                                    )
                                ),
                                "le": nested_kv_decoder(
                                    KVDecoders(
                                        decoders=_decoders,
                                        default_free=decode_free_output,
                                    )
                                ),
                            }
                        )
                    ),
                },
                default_free=decode_free_output,
            )
        )

    @classmethod
    def _tnl_action_decoder(cls):
        return {
            "tnl_push": nested_kv_decoder(
                KVDecoders(
                    {
                        "tnl_port": decode_int,
                        "header": nested_kv_decoder(
                            KVDecoders(
                                {
                                    "size": decode_int,
                                    "type": decode_int,
                                    "eth": nested_kv_decoder(
                                        KVDecoders(
                                            {
                                                "src": decode_mac,
                                                "dst": decode_mac,
                                                "dl_type": decode_int,
                                            }
                                        )
                                    ),
                                    "ipv4": nested_kv_decoder(
                                        KVDecoders(
                                            {
                                                "src": decode_ip,
                                                "dst": decode_ip,
                                                "proto": decode_int,
                                                "tos": decode_int,
                                                "ttl": decode_int,
                                                "frag": decode_int,
                                            }
                                        )
                                    ),
                                    "ipv6": nested_kv_decoder(
                                        KVDecoders(
                                            {
                                                "src": decode_ip,
                                                "dst": decode_ip,
                                                "label": decode_int,
                                                "proto": decode_int,
                                                "tclass": decode_int,
                                                "hlimit": decode_int,
                                            }
                                        )
                                    ),
                                    "udp": nested_kv_decoder(
                                        KVDecoders(
                                            {
                                                "src": decode_int,
                                                "dst": decode_int,
                                                "dsum": decode_mask16,
                                            }
                                        )
                                    ),
                                    "vxlan": nested_kv_decoder(
                                        KVDecoders(
                                            {
                                                "flags": decode_int,
                                                "vni": decode_int,
                                            }
                                        )
                                    ),
                                    "geneve": nested_kv_decoder(
                                        KVDecoders(
                                            {
                                                "oam": decode_flag,
                                                "crit": decode_flag,
                                                "vni": decode_int,
                                                "options": partial(
                                                    decode_geneve, False
                                                ),
                                            }
                                        )
                                    ),
                                    "gre": decode_tnl_gre,
                                    "erspan": nested_kv_decoder(
                                        KVDecoders(
                                            {
                                                "ver": decode_int,
                                                "sid": decode_int,
                                                "idx": decode_int,
                                                "sid": decode_int,
                                                "dir": decode_int,
                                                "hwid": decode_int,
                                            }
                                        )
                                    ),
                                    "gtpu": nested_kv_decoder(
                                        KVDecoders(
                                            {
                                                "flags": decode_int,
                                                "msgtype": decode_int,
                                                "teid": decode_int,
                                            }
                                        )
                                    ),
                                }
                            )
                        ),
                        "out_port": decode_int,
                    }
                )
            )
        }

    @classmethod
    def _info_decoders(cls):
        return {
            "packets": decode_int,
            "bytes": decode_int,
            "used": decode_time,
            "flags": decode_default,
            "dp": decode_default,
        }

    @classmethod
    def _match_parser(cls):
        return KVParser(
            KVDecoders(
                {
                    **cls._field_decoders(),
                    "encap": nested_kv_decoder(KVDecoders(cls._field_decoders())),
                }
            )
        )

    @classmethod
    def _field_decoders(cls):
        return {
            "skb_priority": decode_mask32,
            "skb_mark": decode_mask32,
            "recirc_id": decode_int,
            "dp_hash": decode_mask32,
            "ct_state": decode_default,  # TODO: Parse flags
            "ct_zone": decode_mask16,
            "ct_mark": decode_mask32,
            "ct_label": decode_mask128,
            "ct_tuple4": nested_kv_decoder(
                KVDecoders(
                    {
                        "src": decode_ip,
                        "dst": decode_ip,
                        "proto": decode_mask8,
                        "tcp_src": decode_mask16,
                        "tcp_dst": decode_mask16,
                    }
                )
            ),
            "ct_tuple6": nested_kv_decoder(
                KVDecoders(
                    {
                        "src": decode_ip,
                        "dst": decode_ip,
                        "proto": decode_mask8,
                        "tcp_src": decode_mask16,
                        "tcp_dst": decode_mask16,
                    }
                )
            ),
            "tunnel": nested_kv_decoder(
                KVDecoders(
                    {
                        "tun_id": decode_int,
                        "src": decode_ip,
                        "dst": decode_ip,
                        "ipv6_src": decode_ip,
                        "ipv6_dst": decode_ip,
                        "tos": decode_int,
                        "ttl": decode_int,
                        "tp_src": decode_int,
                        "tp_dst": decode_int,
                        "erspan": nested_kv_decoder(
                            KVDecoders(
                                {
                                    "ver": decode_int,
                                    "idx": decode_int,
                                    "sid": decode_int,
                                    "dir": decode_int,
                                    "hwid": decode_int,
                                }
                            )
                        ),
                        "vxlan": nested_kv_decoder(
                            KVDecoders(
                                {
                                    "gbp": nested_kv_decoder(
                                        KVDecoders(
                                            {
                                                "id": decode_int,
                                                "flags": decode_int,
                                            }
                                        )
                                    )
                                }
                            )
                        ),
                        "geneve": partial(decode_geneve, True),
                        "gtpu": nested_kv_decoder(
                            KVDecoders(
                                {
                                    "flags": decode_mask8,
                                    "msgtype": decode_mask8,
                                }
                            )
                        ),
                        "flags": decode_default,
                    }
                )
            ),
            "in_port": decode_default,
            "eth": nested_kv_decoder(
                KVDecoders(
                    {
                        "src": decode_mac,
                        "dst": decode_mac,
                    }
                )
            ),
            "vlan": nested_kv_decoder(
                KVDecoders(
                    {
                        "vid": decode_mask16,
                        "pcp": decode_mask16,
                        "cfi": decode_mask16,
                    }
                )
            ),
            "eth_type": decode_mask16,
            "mpls": nested_kv_decoder(
                KVDecoders(
                    {
                        "label": decode_mask32,
                        "tc": decode_mask32,
                        "ttl": decode_mask32,
                        "bos": decode_mask32,
                    }
                )
            ),
            "ipv4": nested_kv_decoder(
                KVDecoders(
                    {
                        "src": decode_ip,
                        "dst": decode_ip,
                        "proto": decode_mask8,
                        "tos": decode_mask8,
                        "ttl": decode_mask8,
                        "frag": decode_default,
                    }
                )
            ),
            "ipv6": nested_kv_decoder(
                KVDecoders(
                    {
                        "src": decode_ip,
                        "dst": decode_ip,
                        "label": partial(decode_mask, 20),
                        "proto": decode_mask8,
                        "tclass": decode_mask8,
                        "hlimit": decode_mask8,
                        "frag": decode_default,
                    }
                )
            ),
            "tcp": nested_kv_decoder(
                KVDecoders(
                    {
                        "src": decode_mask16,
                        "dst": decode_mask16,
                    }
                )
            ),
            "tcp_flags": decode_default,
            "udp": nested_kv_decoder(
                KVDecoders(
                    {
                        "src": decode_mask16,
                        "dst": decode_mask16,
                    }
                )
            ),
            "sctp": nested_kv_decoder(
                KVDecoders(
                    {
                        "src": decode_mask16,
                        "dst": decode_mask16,
                    }
                )
            ),
            "icmp": nested_kv_decoder(
                KVDecoders(
                    {
                        "type": decode_mask8,
                        "code": decode_mask8,
                    }
                )
            ),
            "icmpv6": nested_kv_decoder(
                KVDecoders(
                    {
                        "type": decode_mask8,
                        "code": decode_mask8,
                    }
                )
            ),
            "arp": nested_kv_decoder(
                KVDecoders(
                    {
                        "sip": decode_ip,
                        "tip": decode_ip,
                        "op": decode_mask16,
                        "sha": decode_mac,
                        "tha": decode_mac,
                    }
                )
            ),
            "nd": nested_kv_decoder(
                KVDecoders(
                    {
                        "target": decode_ip,
                        "sll": decode_mac,
                        "tll": decode_mac,
                    }
                )
            ),
            "nd_ext": nested_kv_decoder(
                KVDecoders(
                    {
                        "nd_reserved": decode_mask32,
                        "nd_options_type": decode_mask8,
                    }
                )
            ),
            "packet_type": nested_kv_decoder(
                KVDecoders(
                    {
                        "ns": decode_mask16,
                        "id": decode_mask16,
                    }
                )
            ),
            "nsh": nested_kv_decoder(
                KVDecoders(
                    {
                        "flags": decode_mask8,
                        "mdtype": decode_mask8,
                        "np": decode_mask8,
                        "spi": decode_mask32,
                        "si": decode_mask8,
                        "c1": decode_mask32,
                        "c2": decode_mask32,
                        "c3": decode_mask32,
                        "c4": decode_mask32,
                    }
                )
            ),
        }


def decode_geneve(mask, value):
    """
    Decode geneve options. Used for both tnl_push(header(geneve(options()))) action
    and tunnel(geneve()) match.

    It has the following format:

    {class=0xffff,type=0x80,len=4,0xa}

    Args:
        mask (bool): Whether masking is supported
        value (str): The value to decode
    """
    if mask:
        decoders = {
            "class": decode_mask16,
            "type": decode_mask8,
            "len": decode_mask8,
        }

        def free_decoder(value):
            return "data", decode_mask128(value)

    else:
        decoders = {
            "class": decode_int,
            "type": decode_int,
            "len": decode_int,
        }

        def free_decoder(value):
            return "data", decode_int(value)

    return decode_nested_kv(
        KVDecoders(decoders=decoders, default_free=free_decoder), value.strip("{}")
    )


def decode_tnl_gre(value):
    """
    Decode tnl_push(header(gre())) action

    It has the following format:

    gre((flags=0x2000,proto=0x6558),key=0x1e241))

    Args:
        value (str): The value to decode
    """

    return decode_nested_kv(
        KVDecoders(
            {
                "flags": decode_int,
                "proto": decode_int,
                "key": decode_int,
                "csum": decode_int,
                "seq": decode_int,
            }
        ),
        value.replace("(", "").replace(")", ""),
    )
