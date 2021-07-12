""" Defines decoders for openflow actions
"""

from ovs_dbg.kv import nested_kv_decoder, KVDecoders, KeyValue


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
