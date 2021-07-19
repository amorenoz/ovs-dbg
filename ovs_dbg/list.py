import re
import functools

from ovs_dbg.kv import KeyValue, KeyMetadata, ParseError
from ovs_dbg.decoders import decode_default


class ListDecoders:
    """ListDecoders is used by ListParser to decode the elements in the list

    A decoder is a function that accepts a value and returns its decoded
    object
    The list_decoder to be used is determined by index in the list provided to
    ListDecoders is important.

    Args:
        decoders (list of tuples): Optional,  A list of tuples.
            The first element in the tuple is the keyword associated with the
            value. The second element in the tuple is the decoder function.
    """

    def __init__(self, decoders=None):
        self._decoders = decoders or list()

    def decode(self, index, value_str):
        """Decode the index'th element of the list

        Args:
            index (int): the position in the list of the element ot decode
            value_str (str): the value string to decode
        """
        if index < 0 or index >= len(self._decoders):
            return self._default_decoder(index, value_str)

        try:
            key = self._decoders[index][0]
            value = self._decoders[index][1](value_str)
            return key, value
        except Exception as e:
            raise ParseError("Failed to decode value_str %s: %s" % (value_str, str(e)))

    @staticmethod
    def _default_decoder(index, value):
        key = "elem_{}".format(index)
        return key, decode_default(value)


class ListParser:
    """ListParser parses a list of values and stores them as key-value pairs

    It uses a ListDecoders instance to decode each element in the list.

    Args:
        decoders (ListDecoders): Optional, the decoders to use
        delims (list): Optional, list of delimiters of the list. Defaults to
            [',']
    """

    def __init__(self, decoders=None, delims=None):
        self._decoders = decoders or ListDecoders()
        self._keyval = list()
        delims = delims or [","]
        delims.append("$")
        self._regexp = r"({})".format("|".join(delims))

    def kv(self):
        return self._keyval

    def __iter__(self):
        return iter(self._keyval)

    def parse(self, string):
        """Parse the list in string

        Args:
            string (str): the string to parse

        Raises:
            ParseError if any parsing error occurs.
        """
        kpos = 0
        index = 0
        while kpos < len(string) and string[kpos] != "\n":
            split_parts = re.split(self._regexp, string[kpos:], 1)
            if len(split_parts) < 3:
                break

            value_str = split_parts[0]

            key, value = self._decoders.decode(index, value_str)

            meta = KeyMetadata(
                kpos=kpos,
                vpos=kpos,
                kstring=value_str,
                vstring=value_str,
            )
            self._keyval.append(KeyValue(key, value, meta))

            kpos += len(value_str) + 1
            index += 1


def decode_nested_list(decoders, delims, value):
    """Extracts nested list from te string and returns it in a dictionary
    them in a dictionary

    Args:
        decoders (ListDecoders): the ListDecoders to use.
        value (str): the value string to decode.
    """
    parser = ListParser(decoders, delims)
    parser.parse(value)
    return {kv.key: kv.value for kv in parser.kv()}


def nested_list_decoder(decoders=None, delims=None):
    """Helper function that creates a nested list decoder with given
    ListDecoders
    """
    return functools.partial(decode_nested_list, decoders, delims)
