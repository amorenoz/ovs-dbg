""" Common helper classes for flow (ofproto/dpif) parsing
"""

import re
import functools
from dataclasses import dataclass


class ParseError(RuntimeError):
    """Exception raised when an error occurs during parsing
    """
    pass


@dataclass
class KeyMetadata:
    """Class for keeping key metadata

    :param kpos: The position of the keyword in the parent string
    :type kpos: int
    :param vpos: The position of the value in the parent string
    :type vpos: int
    :param kstring: The keyword string as found in the flow string
    :type kstring: str
    :param vstring: The value as found in the flow string
    :type vstring: str
    :param end_del: Whether the key has end delimiter, e.g: )
    :type end_del: bool
    """

    def __init__(self, kpos, vpos, kstring, vstring, end_del):
        """Constructor"""
        self.kpos = kpos
        self.vpos = vpos
        self.kstring = kstring
        self.vstring = vstring
        self.end_del = end_del

    def __str__(self):
        return "key: [{},{}), val:[{}, {})".format(
            self.kpos,
            self.kpos + len(self.kstring),
            self.vpos,
            self.vpos + len(self.vstring),
        )


@dataclass
class KeyValue:
    """Class for keeping key-value data

    :param key: The key string
    :type key: str
    :param value: The value data
    :type vpos: any
    :param meta: The key metadata
    :type meta: KeyMetadata, optional
    """

    def __init__(self, key, value, meta=None):
        """Constructor"""
        self.key = key
        self.value = value
        self.meta = meta

    def __str__(self):
        return "{}: {} ({})".format(self.key, str(self.value), str(self.meta))


class KVDecoders:
    """KVDecoders class is used by KVParser to select how to decoode the value
    of a specific keyword.

    A decoder is simply a function that accepts the keyword and value strings
    and returns the keyword and value objects to be stored. The returned
    keyword must be a string but may not be the same as the given keyword.
    The returned value may be of any type.

    :param decoders: A dictionary of decoders indexed by keyword
    :type decoders: dict, optional
    :param default: A decoder used if a match is not found in configured
        decoders. If not provided, the default behavior is to try to decode
        the value into an integer and, if that fails, just return the string
        as-is
    :type default: callable, optional
    :param default_free: A decoder used if a match is not found in configured
        decoders and it's a free value (e.g: a keyword without a value).
        Defaults to returning the free value as keyword and "True" as value
    :type default_free: callable that accepts a single string parameter
        and returns a keyword and a value, optional
    """

    def __init__(self, decoders=None, default=None, default_free=None):
        self._decoders = decoders or dict()
        self._default = default or self._default_decoder
        self._default_free = default_free or self._default_free_decoder

    def decode(self, keyword, value_str):
        """Decode a keyword and value

        :param: keyword: The keyword whose value is to be decoded
        :type keyword: str
        :param: value_str: The value string
        :type value_str: str

        :return: the key and value to be stored
        :rtype: key(str), value(any)
        """
        decoder = self._decoders.get(keyword)
        if decoder:
            return decoder(keyword, value_str)
        else:
            if value_str:
                return self._default(keyword, value_str)
            else:
                return self._default_free(keyword)

    @staticmethod
    def _default_free_decoder(key):
        """Default decoder for free kewords"""
        return key, True

    @staticmethod
    def _default_decoder(key, value):
        """Default decoder

        It tries to convert into an integer value and, if it fails, just
        returns the string"""
        try:
            ival = int(value, 0)
            return key, ival
        except ValueError:
            return key, value


class KVParser:
    """KVParser parses a string looking for key-value pairs

    :param decoders: A KVDecoders instance to use
    :type decoders: KVDecoders, optional
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
        """Parse a string

        :param string: the string to parse
        :type string: str

        """
        kpos = 0
        while kpos < len(string) and string[kpos] != "\n":
            # strip string
            if string[kpos] == "," or string[kpos] == " ":
                kpos += 1
                continue

            split_parts = re.split(r"(\(|=|:|,|\n|\r|\t)", string[kpos:], 1)
            # the delimiter should be included in the returned list
            if len(split_parts) < 3:
                break

            keyword = split_parts[0]
            delimiter = split_parts[1]
            rest = split_parts[2]

            value_str = ""
            vpos = kpos + len(keyword) + 1
            end_delimiter = False

            # Figure out the end of the value
            # If the delimiter is ':' or '=', the end of the value is the end
            # of the string or a ', '
            if delimiter in ("=", ":"):
                value_parts = re.split(r"( |,)", rest, 1)
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
                end_delimiter = True

            elif delimiter in (",", "\n", "\t", "\r"):
                # key with no value
                next_kpos = kpos + len(keyword)
                vpos = -1

            key, val = self._decoders.decode(keyword, value_str)

            meta = KeyMetadata(
                kpos=kpos,
                vpos=vpos,
                kstring=keyword,
                vstring=value_str,
                end_del=end_delimiter,
            )

            self._keyval.append(KeyValue(key, val, meta))

            kpos = next_kpos


def _kv_decoder(decoders, key, value):
    """A key-value decoder that extracts nested key-value pairs and returns
    them in a dictionary

    :param: decoders: the KVDecoders to use
    :type: decoders: KVDecoders, optional
    :param: key: the keyword
    :type key: str
    :param value: the value string
    :type value: str
    """
    parser = KVParser(decoders)
    parser.parse(value)
    return key, {kv.key: kv.value for kv in parser.kv()}


default_kv_decoder = functools.partial(_kv_decoder, None)
