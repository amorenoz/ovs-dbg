""" Defines helpful decoders that can be used to decode information from the
flows

A decoder is generally a callable that accepts a string and returns the value
object
"""


def decode_default(value):
    """Default decoder.

    It tries to convert into an integer value and, if it fails, just
    returns the string.
    """
    try:
        ival = int(value, 0)
        return ival
    except ValueError:
        return value

