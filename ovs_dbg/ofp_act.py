""" Defines decoders for openflow actions
"""

from ovs_dbg.kv import nested_kv_decoder, KVDecoders, KeyValue
from ovs_dbg.decoders import decode_default


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


def decode_free_output(value):
    """Decodes the output value when found free (without the 'output' keyword)"""
    try:
        return "output", {"port": int(value)}
    except ValueError:
        return "output", {"port": value.strip('"')}


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
