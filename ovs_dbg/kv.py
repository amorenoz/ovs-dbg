""" Common helper classes for flow (ofproto/dpif) parsing
"""

import re
import functools

from ovs_dbg.decoders import decode_default


class ParseError(RuntimeError):
    """Exception raised when an error occurs during parsing."""

    pass


class KeyMetadata:
    """Class for keeping key metadata.

    Attributes:
        kpos (int): The position of the keyword in the parent string.
        vpos (int): The position of the value in the parent string.
        kstring (string): The keyword string as found in the flow string.
        vstring (string): The value as found in the flow string.
        end_del (bool): Whether the key has end delimiter.
    """

    def __init__(self, kpos, vpos, kstring, vstring, delim="", end_delim=""):
        """Constructor"""
        self.kpos = kpos
        self.vpos = vpos
        self.kstring = kstring
        self.vstring = vstring
        self.delim = delim
        self.end_delim = end_delim

    def __str__(self):
        return "key: [{},{}), val:[{}, {})".format(
            self.kpos,
            self.kpos + len(self.kstring),
            self.vpos,
            self.vpos + len(self.vstring),
        )

    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, self)


class KeyValue:
    """Class for keeping key-value data

    Attributes:
        key (str): The key string.
        value (any): The value data.
        meta (KeyMetadata): The key metadata.
    """

    def __init__(self, key, value, meta=None):
        """Constructor"""
        self.key = key
        self.value = value
        self.meta = meta

    def __str__(self):
        return "{}: {} ({})".format(self.key, str(self.value), str(self.meta))

    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, self)


class KVDecoders:
    """KVDecoders class is used by KVParser to select how to decoode the value
    of a specific keyword.

    A decoder is simply a function that accepts a value string
    and returns the value objects to be stored.
    The returned value may be of any type.

    Decoders may return a KeyValue instance to indicate that the keyword should
    also be modified to match the one provided in the returned KeyValue

    The free_decoder, however, must return the key and value to be stored

    Args:
        decoders (dict): Optional; A dictionary of decoders indexed by keyword.
        default (callable): Optional; A decoder used if a match is not found in
            configured decoders. If not provided, the default behavior is to
            try to decode the value into an integer and, if that fails,
            just return the string as-is.
        default_free (callable): Optional; The decoder used if a match is not
            found in configured decoders and it's a free value (e.g:
            a value without a key) Defaults to returning the free value as
            keyword and "True" as value.
            The callable must accept a string and return a key, value pair
    """

    def __init__(self, decoders=None, default=None, default_free=None):
        self._decoders = decoders or dict()
        self._default = default or decode_default
        self._default_free = default_free or self._default_free_decoder

    def decode(self, keyword, value_str):
        """Decode a keyword and value.

        Args:
            keyword (str): The keyword whose value is to be decoded.
            value_str (str): The value string.

        Returns:
            The key (str) and value(any) to be stored.
        """

        decoder = self._decoders.get(keyword)
        if decoder:
            result = decoder(value_str)
            if isinstance(result, KeyValue):
                keyword = result.key
                value = result.value
            else:
                value = result

            return keyword, value
        else:
            if value_str:
                return keyword, self._default(value_str)
            else:
                return self._default_free(keyword)

    @staticmethod
    def _default_free_decoder(key):
        """Default decoder for free kewords."""
        return key, True


class KVParser:
    """KVParser parses a string looking for key-value pairs.

    Args:
        decoders (KVDecoders): Optional; the KVDecoders instance to use.
    """

    def __init__(self, decoders=None):
        """Constructor"""
        self._decoders = decoders or KVDecoders()
        self._keyval = list()

    def keys(self):
        return list(kv.key for kv in self._keyval)

    def kv(self):
        return self._keyval

    def __iter__(self):
        return iter(self._keyval)

    def parse(self, string):
        """Parse the key-value pairs in string.

        Args:
            string (str): the string to parse.

        Raises:
            ParseError if any parsing error occurs.
        """
        kpos = 0
        while kpos < len(string) and string[kpos] != "\n":
            # strip string
            if string[kpos] == "," or string[kpos] == " ":
                kpos += 1
                continue

            split_parts = re.split(r"(\(|=|:|,|\n|\r|\t|$)", string[kpos:], 1)
            # the delimiter should be included in the returned list
            if len(split_parts) < 3:
                break

            keyword = split_parts[0]
            delimiter = split_parts[1]
            rest = split_parts[2]

            value_str = ""
            vpos = kpos + len(keyword) + 1
            end_delimiter = ""

            # Figure out the end of the value
            # If the delimiter is ':' or '=', the end of the value is the end
            # of the string or a ', '
            if delimiter in ("=", ":"):
                value_parts = re.split(r"( |,|\n|\r|\t)", rest, 1)
                value_str = value_parts[0] if len(value_parts) == 3 else rest
                next_kpos = vpos + len(value_str)

            elif delimiter == "(":
                # Find the next ')'
                level = 1
                index = 0
                value_parts = re.split(r"(\(|\))", rest)
                for val in value_parts:
                    if val == "(":
                        level += 1
                    elif val == ")":
                        level -= 1
                    index += len(val)
                    if level == 0:
                        break

                if level != 0:
                    raise ParseError(
                        "Error parsing string {}: "
                        "Failed to find matching ')' in {}".format(string, rest)
                    )

                value_str = rest[: index - 1]
                next_kpos = vpos + len(value_str) + 1
                end_delimiter = ")"

                # Exceptionally, if after the () we find -> {}, do not treat
                # the content of the parenthesis as the value, consider
                # ({})->{} as the string value
                if index < len(rest) - 2 and rest[index : index + 2] == "->":
                    extra_val = rest[index + 2 :].split(",")[0]
                    value_str = "({})->{}".format(value_str, extra_val)
                    # remove the first "("
                    vpos -= 1
                    next_kpos = vpos + len(value_str)
                    end_delimiter = ""

            elif delimiter in (",", "\n", "\t", "\r", ""):
                # key with no value
                next_kpos = kpos + len(keyword)
                vpos = -1

            try:
                key, val = self._decoders.decode(keyword, value_str)
            except Exception as e:
                raise ParseError(
                    "Error parsing key-value ({}, {})".format(keyword, value_str)
                ) from e

            meta = KeyMetadata(
                kpos=kpos,
                vpos=vpos,
                kstring=keyword,
                vstring=value_str,
                delim=delimiter,
                end_delim=end_delimiter,
            )

            self._keyval.append(KeyValue(key, val, meta))

            kpos = next_kpos


def decode_nested_kv(decoders, value):
    """A key-value decoder that extracts nested key-value pairs and returns
    them in a dictionary

    Args:
        decoders (KVDecoders): the KVDecoders to use.
        value (str): the value string to decode.
    """
    if not value:
        # Mark as flag
        return True

    parser = KVParser(decoders)
    parser.parse(value)
    return {kv.key: kv.value for kv in parser.kv()}


def nested_kv_decoder(decoders=None):
    """Helper function that creates a nested kv decoder with given KVDecoders"""
    return functools.partial(decode_nested_kv, decoders)
