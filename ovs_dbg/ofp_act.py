""" Defines decoders for openflow actions
"""

import netaddr
import functools

from ovs_dbg.kv import nested_kv_decoder, KVDecoders, KeyValue, KVParser
from ovs_dbg.decoders import decode_default, decode_time, decode_flag, decode_int
from ovs_dbg.fields import field_decoders


def decode_output(value):
    """Decodes the output value

    Does not support field specification
    """
    if len(value.split(",")) > 1:
        return nested_kv_decoder()(value)
    try:
        return {"port": int(value)}
    except ValueError:
        return {"port": value.strip('"')}


def decode_controller(value):
    """Decodes the controller action"""
    if not value:
        return KeyValue("output", "controller")
    else:
        # Try controller:max_len
        try:
            max_len = int(value)
            return {
                "max_len": max_len,
            }
        except ValueError:
            pass
        # controller(key[=val], ...)
        return nested_kv_decoder()(value)


def decode_bundle_load(value):
    return decode_bundle(value, True)


def decode_bundle(value, load=False):
    """Decode bundle action"""
    result = {}
    keys = ["fields", "basis", "algorithm", "ofport"]
    if load:
        keys.append("dst")

    for key in keys:
        parts = value.partition(",")
        nvalue = parts[0]
        value = parts[2]
        if key == "ofport":
            continue
        result[key] = decode_default(nvalue)

    # Handle members:
    mvalues = value.split("members:")
    result["members"] = [int(port) for port in mvalues[1].split(",")]
    return result


def decode_encap_ethernet(value):
    """Decodes encap ethernet value"""
    return "ethernet", int(value, 0)


def decode_field(value):
    """Decodes a field as defined in the 'Field Specification' of the actions
    man page: http://www.openvswitch.org/support/dist-docs/ovs-actions.7.txt
    """
    parts = value.strip("]\n\r").split("[")
    result = {
        "field": parts[0],
    }

    if len(parts) > 1 and parts[1]:
        field_range = parts[1].split("..")
        start = field_range[0]
        end = field_range[1] if len(field_range) > 1 else start
        if start:
            result["start"] = int(start)
        if end:
            result["end"] = int(end)

    return result


def decode_load_field(value):
    """Decodes 'load:value->dst' actions"""
    parts = value.split("->")
    if len(parts) != 2:
        raise ValueError("Malformed load action : %s" % value)

    return {"value": int(parts[0], 0), "dst": decode_field(parts[1])}


def decode_set_field(field_decoders, value):
    """Decodes 'set_field:value/mask->dst' actions

    The value is decoded by field_decoders which is a KVDecoders instance
    Args:
        field_decoders
    """
    parts = value.split("->")
    if len(parts) != 2:
        raise ValueError("Malformed set_field action : %s" % value)

    val = parts[0]
    dst = parts[1]

    val_result = field_decoders.decode(dst, val)

    return {
        "value": {val_result[0]: val_result[1]},
        "dst": decode_field(dst),
    }


def decode_move_field(value):
    """Decodes 'move:src->dst' actions"""
    parts = value.split("->")
    if len(parts) != 2:
        raise ValueError("Malformed move action : %s" % value)

    return {
        "src": decode_field(parts[0]),
        "dst": decode_field(parts[1]),
    }


def decode_dec_ttl(value):
    """Decodes dec_ttl and dec_ttl(id, id[2], ...) actions"""
    if not value:
        return True
    return [int(idx) for idx in value.split(",")]


def decode_chk_pkt_larger(value):
    """Decodes 'check_pkt_larger(pkt_len)->dst' actions"""
    parts = value.split("->")
    if len(parts) != 2:
        raise ValueError("Malformed check_pkt_larger action : %s" % value)

    pkt_len = int(parts[0].strip("()"))
    dst = decode_field(parts[1])
    return {"pkt_len": pkt_len, "dst": dst}


# CT decoders
def decode_zone(value):
    """Decodes the 'zone' keyword of the ct action"""
    try:
        return int(value, 0)
    except ValueError:
        pass
    return decode_field(value)


def decode_exec(action_decoders, value):
    """Decodes the 'exec' keyword of the ct action

    Args:
        decode_actions (KVDecoders): the decoders to be used to decode the
            nested exec
        value (string): the string to be decoded
    """
    exec_parser = KVParser(action_decoders)
    exec_parser.parse(value)
    return [{kv.key: kv.value} for kv in exec_parser.kv()]


def decode_learn(action_decoders):
    """Create the decoder to be used to decode the 'learn' action.

    The learn action can include any nested action, therefore we need decoders
    for all possible actions.

    Args:
        action_decoders (dict): dictionary of decoders to be used in nested
            action decoding

    """

    def decode_learn_field(decoder, value):
        """Generates a decoder to be used for the 'field' argument of the
        'learn' action.

        The field can hold a value that should be decoded, either as a field,
        or as a the value (see man(7) ovs-actions)

        Args:
            decoder (callable): The decoder

        """
        if value in field_decoders.keys():
            # It's a field
            return value
        else:
            return decoder(value)

    learn_field_decoders = {
        field: functools.partial(decode_learn_field, decoder)
        for field, decoder in field_decoders.items()
    }
    learn_decoders = {
        **action_decoders,
        **learn_field_decoders,
        "idle_timeout": decode_time,
        "hard_timeout": decode_time,
        "priority": decode_int,
        "cooke": decode_int,
        "send_flow_rem": decode_flag,
        "table": decode_int,
        "delete_learned": decode_flag,
        "limit": decode_int,
        "result_dst": decode_field,
    }

    return functools.partial(decode_exec, KVDecoders(learn_decoders))
