""" Defines the parsers needed to parse ofproto flows
"""

from dataclasses import dataclass
import functools
import re

from ovs_dbg.kv import KVParser, KVDecoders, ParseError, nested_kv_decoder
from ovs_dbg.list import ListDecoders, nested_list_decoder
from ovs_dbg.decoders import (
    decode_default,
    decode_flag,
    decode_int,
    decode_time,
    decode_mask8,
    decode_mask16,
    decode_mask32,
    decode_mask64,
    decode_mask128,
    decode_mask,
    decode_ip,
    decode_mac,
)
from ovs_dbg.ofp_act import (
    decode_free_output,
    decode_output,
    decode_controller,
    decode_bundle,
    decode_bundle_load,
    decode_encap_ethernet,
    decode_load_field,
    decode_set_field,
    decode_move_field,
    decode_dec_ttl,
)


@dataclass
class OFPFlowMeta:
    """OFPFlow Metadata"""

    def __init__(self, ipos, istring, fpos, fstring, apos, astring):
        self.ipos = ipos
        self.istring = istring
        self.fpos = fpos
        self.fstring = fstring
        self.apos = apos
        self.astring = astring


class OFPFlow:
    """OpenFlow Flow"""

    def __init__(self, info, fields, actions, meta=None, orig=""):
        """Constructor"""
        self._info = info
        self._fields = fields
        self._actions = actions
        self._meta = meta
        self._orig = orig

    @property
    def info(self):
        """Returns a dictionary representing the flow information"""
        return {item.key: item.value for item in self._info}

    @property
    def fields(self):
        """Returns a dictionary representing the fields"""
        return {item.key: item.value for item in self._fields}

    @property
    def actions(self):
        """Returns a list of dictionaries reprsenting the actions"""
        return [{item.key: item.value} for item in self._actions]

    @property
    def info_kv(self):
        """Returns the information KeyValue list"""
        return self._info

    @property
    def fields_kv(self):
        """Returns the fields KeyValue  list"""
        return self._fields

    @property
    def actions_kv(self):
        """Returns the actions KeyValue list"""
        return self._actions

    @property
    def meta(self):
        """Returns the flow metadata"""
        return self._meta

    @property
    def orig(self):
        """Returns the original flow string"""
        return self._orig

    @classmethod
    def from_string(cls, ofp_string):
        """Parse a ofproto flow string

        The string is expected to have the follwoing format:
            [flow data] [fields] actions=[actions]

        :param ofp_string: a ofproto string as dumped by ovs-ofctl tool
        :type ofp_string: str

        :return: an OFPFlow with the content of the flow string
        :rtype: OFPFlow
        """
        parts = ofp_string.split("actions=")
        if len(parts) != 2:
            raise ValueError("malformed ofproto flow: {}", ofp_string)

        actions = parts[1]

        field_parts = parts[0].rstrip(" ").rpartition(" ")
        if len(field_parts) != 3:
            raise ValueError("malformed ofproto flow: {}", ofp_string)

        info = field_parts[0]
        fields = field_parts[2]

        info_decoders = cls._info_decoders()
        iparser = KVParser(info_decoders)
        iparser.parse(info)

        field_decoders = cls._field_decoders()
        fparser = KVParser(field_decoders)
        fparser.parse(fields)

        act_decoders = cls._act_decoders()
        adecoder = KVParser(act_decoders)
        adecoder.parse(actions)

        meta = OFPFlowMeta(
            ipos=ofp_string.find(info),
            istring=info,
            fpos=ofp_string.find(fields),
            fstring=fields,
            apos=ofp_string.find(actions),
            astring=actions,
        )

        return cls(iparser.kv(), fparser.kv(), adecoder.kv(), meta, ofp_string)

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
    def _field_decoders(cls):
        ip_fields = [
            "tun_src",
            "tun_dst",
            "tun_ipv6_src",
            "tun_ipv6_dst",
            "ct_nw_src",
            "ct_nw_dst",
            "ct_ipv6_dst",
            "ip_src",
            "nw_src",
            "ip_dst",
            "nw_dst",
            "ipv6_src",
            "ipv6_dst",
            "arp_spa",
            "arp_tpa",
            "nd_target",
        ]
        eth_fields = [
            "eth_src",
            "dl_src",
            "dl_dst",
            "eth_dst",
            "arp_sha",
            "arp_tha",
            "nd_sll",
            "nd_tll",
        ]
        ip = {field: decode_ip for field in ip_fields}
        eth = {field: decode_mac for field in eth_fields}

        tun_meta = dict(
            (
                ("tun_metadata{}".format(i), functools.partial(decode_mask, 992))
                for i in range(0, 64)
            )
        )

        nsh = dict((("nshc{}".format(i), decode_mask32) for i in range(1, 5)))
        nsh_ = dict((("nsh_c{}".format(i), decode_mask32) for i in range(1, 5)))

        regs = dict((("reg{}".format(i), decode_mask32) for i in range(0, 4)))
        xregs = dict((("xreg{}".format(i), decode_mask32) for i in range(0, 4)))

        mask_fields = {
            "dp_hash": decode_mask32,
            "tun_id": decode_mask64,
            "tunnel_id": decode_mask64,
            "tun_gbp_id": decode_mask16,
            "tun_gbp_flags": decode_mask8,
            "tun_erspan_idx": decode_mask32,
            "tun_erspan_ver": decode_mask8,
            "tun_erspan_dir": decode_mask8,
            "tun_erspan_hwid": decode_mask8,
            "tun_gtpu_flags": decode_mask8,
            "tun_gtpu_msgtype": decode_mask8,
            "metadata": decode_mask64,
            "pkt_mark": decode_mask32,
            "ct_mark": decode_mask32,
            "ct_label": decode_mask128,
            "ct_tcp_src": decode_mask16,
            "vlan_tci": decode_mask16,
            "vlan_vid": decode_mask8,
            "ipv6_label": decode_mask32,
            "udp_src": decode_mask16,
            "udp_dst": decode_mask16,
            "sctp_src": decode_mask16,
            "sctp_dst": decode_mask16,
            "nsh_flags": decode_mask8,
        }

        fields = {
            "priority": decode_int,
        }
        return KVDecoders(
            {
                **fields,
                **ip,
                **eth,
                **tun_meta,
                **regs,
                **xregs,
                **nsh,
                **nsh_,
                **mask_fields,
            }
        )

    @classmethod
    def _act_decoders(cls):
        """Generate the actions decoders"""

        adec = {
            "output": decode_output,
            "controller": decode_controller,
            "enqueue": nested_list_decoder(
                ListDecoders([("port", decode_default), ("queue", int)]),
                delims=[",", ":"],
            ),
            "bundle": decode_bundle,
            "bundle_load": decode_bundle_load,
        }

        # Actions using default decoder:
        # group
        # push_vlan: ethertype

        # Encapsulation actions
        encap = {
            "pop_vlan": decode_flag,
            "strip_vlan": decode_flag,
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

        # Field modification actions
        fields = {
            "load": decode_load_field,
            "set_field": functools.partial(decode_set_field, cls._field_decoders()),
            "move": decode_move_field,
            "mod_dl_dst": decode_mac,
            "mod_dl_src": decode_mac,
            "mod_nw_dst": decode_ip,
            "mod_nw_src": decode_ip,
            "dec_ttl": decode_dec_ttl,
            "dec_mpls_ttl": decode_flag,
            "dec_nsh_ttl": decode_flag,
        }
        # Field actions using default decoder:
        # set_mpls_label
        # set_mpls_tc
        # set_mpls_ttl
        # mod_nw_tos
        # mod_nw_ecn
        # mod_tcp_src
        # mod_tcp_dst

        actions = {**adec, **encap, **fields}
        return KVDecoders(actions, default_free=decode_free_output)

    def __str__(self):
        if self._orig:
            return self._orig
        else:
            string = "Info: {}\n" + self.info
            string += "Fields: {}\n" + self.fields
            string += "Actions: {}\n " + self.actions
            return string
