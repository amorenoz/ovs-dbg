""" Defines the parsers needed to parse ofproto flows
"""

from dataclasses import dataclass
import functools
import re

from ovs_dbg.kv import KVParser, KVDecoders, ParseError, nested_kv_decoder
from ovs_dbg.fields import field_decoders
from ovs_dbg.flow import Flow, Section
from ovs_dbg.list import ListDecoders, nested_list_decoder
from ovs_dbg.decoders import (
    decode_default,
    decode_flag,
    decode_int,
    decode_time,
    decode_mask,
    IPMask,
    EthMask,
    decode_free_output,
    decode_nat,
)
from ovs_dbg.ofp_act import (
    decode_output,
    decode_field,
    decode_controller,
    decode_bundle,
    decode_bundle_load,
    decode_encap_ethernet,
    decode_load_field,
    decode_set_field,
    decode_move_field,
    decode_dec_ttl,
    decode_chk_pkt_larger,
    decode_zone,
    decode_exec,
    decode_learn,
)


class OFPFlow(Flow):
    """OpenFlow Flow"""

    def __init__(self, sections, orig="", id=None):
        """Constructor"""
        super(OFPFlow, self).__init__(sections, orig, id)

    @classmethod
    def from_string(cls, ofp_string, id=None):
        """Parse a ofproto flow string

        The string is expected to have the follwoing format:
            [flow data] [match] actions=[actions]

        :param ofp_string: a ofproto string as dumped by ovs-ofctl tool
        :type ofp_string: str

        :return: an OFPFlow with the content of the flow string
        :rtype: OFPFlow
        """
        sections = list()
        parts = ofp_string.split("actions=")
        if len(parts) != 2:
            raise ValueError("malformed ofproto flow: {}", ofp_string)

        actions = parts[1]

        field_parts = parts[0].rstrip(" ").rpartition(" ")
        if len(field_parts) != 3:
            raise ValueError("malformed ofproto flow: {}", ofp_string)

        info = field_parts[0]
        match = field_parts[2]

        info_decoders = cls._info_decoders()
        iparser = KVParser(info_decoders)
        iparser.parse(info)
        isection = Section(
            name="info", pos=ofp_string.find(info), string=info, data=iparser.kv()
        )
        sections.append(isection)

        match_decoders = KVDecoders(
            {**cls._field_decoders(), **cls._flow_match_decoders()}
        )
        mparser = KVParser(match_decoders)
        mparser.parse(match)
        msection = Section(
            name="match", pos=ofp_string.find(match), string=match, data=mparser.kv()
        )
        sections.append(msection)

        act_decoders = cls._act_decoders()
        aparser = KVParser(act_decoders)
        aparser.parse(actions)
        asection = Section(
            name="actions",
            pos=ofp_string.find(actions),
            string=actions,
            data=aparser.kv(),
            is_list=True,
        )
        sections.append(asection)

        return cls(sections, ofp_string, id)

    @classmethod
    def _info_decoders(cls):
        """Generate the match decoders"""
        info = {
            "table": decode_int,
            "duration": decode_time,
            "n_packet": decode_int,
            "n_bytes": decode_int,
            "cookie": decode_int,
            "idle_timeout": decode_time,
            "hard_timeout": decode_time,
            "hard_age": decode_time,
        }
        return KVDecoders(info)

    @classmethod
    def _flow_match_decoders(cls):
        """Returns the decoders for key-values that are part of the flow match
        but not a flow field"""
        return {
            "priority": decode_int,
        }

    @classmethod
    def _field_decoders(cls):
        shorthands = [
            "eth",
            "ip",
            "ipv6",
            "icmp",
            "icmp6",
            "tcp",
            "tcp6",
            "udp",
            "udp6",
            "sctp",
            "arp",
            "rarp",
            "mpls",
            "mplsm",
        ]

        return {**field_decoders, **{key: decode_flag for key in shorthands}}

    @classmethod
    def _output_actions_decoders(cls):
        """Returns the decoders for the output actions"""
        return {
            "output": decode_output,
            "drop": decode_flag,
            "controller": decode_controller,
            "enqueue": nested_list_decoder(
                ListDecoders([("port", decode_default), ("queue", int)]),
                delims=[",", ":"],
            ),
            "bundle": decode_bundle,
            "bundle_load": decode_bundle_load,
            "group": decode_default,
        }

    @classmethod
    def _encap_actions_decoders(cls):
        """Returns the decoders for the encap actions"""

        return {
            "pop_vlan": decode_flag,
            "strip_vlan": decode_flag,
            "push_vlan": decode_default,
            "decap": decode_flag,
            "encap": nested_kv_decoder(
                KVDecoders(
                    {
                        "nsh": nested_kv_decoder(
                            KVDecoders(
                                {
                                    "md_type": decode_default,
                                    "tlv": nested_list_decoder(
                                        ListDecoders(
                                            [
                                                ("class", decode_int),
                                                ("type", decode_int),
                                                ("value", decode_int),
                                            ]
                                        )
                                    ),
                                }
                            )
                        ),
                    },
                    default=None,
                    default_free=decode_encap_ethernet,
                )
            ),
        }

    @classmethod
    def _field_action_decoders(cls):
        """Returns the decoders for the field modification actions"""
        # Field modification actions
        field_default_decoders = [
            "set_mpls_label",
            "set_mpls_tc",
            "set_mpls_ttl",
            "mod_nw_tos",
            "mod_nw_ecn",
            "mod_tcp_src",
            "mod_tcp_dst",
        ]
        return {
            "load": decode_load_field,
            "set_field": functools.partial(
                decode_set_field, KVDecoders(cls._field_decoders())
            ),
            "move": decode_move_field,
            "mod_dl_dst": EthMask,
            "mod_dl_src": EthMask,
            "mod_nw_dst": IPMask,
            "mod_nw_src": IPMask,
            "dec_ttl": decode_dec_ttl,
            "dec_mpls_ttl": decode_flag,
            "dec_nsh_ttl": decode_flag,
            "check_pkt_larger": decode_chk_pkt_larger,
            **{field: decode_default for field in field_default_decoders},
        }

    @classmethod
    def _meta_action_decoders(cls):
        """Returns the decoders for the metadata actions"""
        meta_default_decoders = ["set_tunnel", "set_tunnel64", "set_queue"]
        return {
            "pop_queue": decode_flag,
            **{field: decode_default for field in meta_default_decoders},
        }

    @classmethod
    def _fw_action_decoders(cls):
        """Returns the decoders for the Firewalling actions"""
        return {
            "ct": nested_kv_decoder(
                KVDecoders(
                    {
                        "commit": decode_flag,
                        "zone": decode_zone,
                        "table": decode_int,
                        "nat": decode_nat,
                        "force": decode_flag,
                        "exec": functools.partial(
                            decode_exec,
                            KVDecoders(
                                {
                                    **cls._encap_actions_decoders(),
                                    **cls._field_action_decoders(),
                                    **cls._meta_action_decoders(),
                                }
                            ),
                        ),
                        "alg": decode_default,
                    }
                )
            ),
            "ct_clear": decode_flag,
        }

    @classmethod
    def _control_action_decoders(cls):
        return {
            "resubmit": nested_list_decoder(
                ListDecoders(
                    [
                        ("port", decode_default),
                        ("table", decode_int),
                        ("ct", decode_flag),
                    ]
                )
            ),
            "push": decode_field,
            "pop": decode_field,
            "exit": decode_flag,
            "multipath": nested_list_decoder(
                ListDecoders(
                    [
                        ("fields", decode_default),
                        ("basis", decode_int),
                        ("algorithm", decode_default),
                        ("n_links", decode_int),
                        ("arg", decode_int),
                        ("dst", decode_field),
                    ]
                )
            ),
        }

    @classmethod
    def _clone_actions_decoders(cls, action_decoders):
        """Generate the decoders for clone actions

        Args:
            action_decoders (dict): The decoders of the supported nested actions
        """
        return {
            "learn": decode_learn(
                {
                    **action_decoders,
                    "fin_timeout": nested_kv_decoder(
                        KVDecoders(
                            {
                                "idle_timeout": decode_time,
                                "hard_timeout": decode_time,
                            }
                        )
                    ),
                }
            ),
            "clone": functools.partial(decode_exec, KVDecoders(action_decoders)),
        }

    @classmethod
    def _other_action_decoders(cls):
        """Recoders for other actions (see man(7) ovs-actions)"""
        return {
            "conjunction": nested_list_decoder(
                ListDecoders(
                    [("id", decode_int), ("k", decode_int), ("n", decode_int)]
                ),
                delims=[",", "/"],
            ),
            "note": decode_default,
            "sample": nested_kv_decoder(
                KVDecoders(
                    {
                        "probability": decode_int,
                        "collector_set_id": decode_int,
                        "obs_domain_id": decode_int,
                        "obs_point_id": decode_int,
                        "sampling_port": decode_default,
                        "ingress": decode_flag,
                        "egress": decode_flag,
                    }
                )
            ),
        }

    @classmethod
    def _act_decoders(cls):
        """Generate the actions decoders"""

        actions = {
            **cls._output_actions_decoders(),
            **cls._encap_actions_decoders(),
            **cls._field_action_decoders(),
            **cls._meta_action_decoders(),
            **cls._fw_action_decoders(),
            **cls._control_action_decoders(),
            **cls._other_action_decoders(),
        }
        clone_actions = cls._clone_actions_decoders(actions)
        actions.update(clone_actions)
        return KVDecoders(actions, default_free=decode_free_output)

    def __str__(self):
        if self._orig:
            return self._orig
        else:
            return self.to_string()

    def to_string(self):
        """Print a text representation of the flow"""
        string = "Info: {}\n" + self.info
        string += "Match : {}\n" + self.match
        string += "Actions: {}\n " + self.actions
        return string
