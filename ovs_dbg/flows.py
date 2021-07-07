""" Common helper classes for flow (ofproto/dpif) parsing
"""

import re
from dataclasses import dataclass


class ParseError(RuntimeError):
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


class KVParser:
    """KVParser parses a string looking for key-value pairs

    :param kw_parsers: A dictionary of parsers indexed by key
        A special key '*' can be used to specify a default parser
    :type kw_parser dict(str, callable) where the callable must accept
        the key and value as string parameter and return the value object,
        optional
    :param free_parser: A parser to be called on free keys (keys without
        values)
    :type free_parser: A callable that accepts the key string and returns
        a tuple of (key, value)
    """

    def __init__(self, kw_parsers=None, free_parser=None):
        """Constructor"""
        self._kw_parsers = kw_parsers or dict()
        self._free_parser = free_parser
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

            key, val = self._get_key_val(keyword, value_str)

            meta = KeyMetadata(
                kpos=kpos,
                vpos=vpos,
                kstring=keyword,
                vstring=value_str,
                end_del=end_delimiter,
            )

            self._keyval.append(KeyValue(key, val, meta))

            kpos = next_kpos

    def _get_key_val(self, keyword, value_str):
        """Decode the key, value pair from keyword and value strings

        :param keyword: the keyword string
        :type keyword: str
        :param value_str: the value string
        :type value_str: str

        :return: a tuple of key and value
        :type rtype: tuple(str, any)
        """
        if value_str:
            parser = (
                self._kw_parsers.get(keyword)
                or self._kw_parsers.get("*")
                or self._default_parser
            )
            return keyword, parser(keyword, value_str)

        else:
            if self._free_parser:
                return self._free_parser(keyword)
            else:
                # By default with set the 'flag' to True
                return keyword, True

    @staticmethod
    def _default_parser(_, value):
        """Default kw parser

        It tries to convert into an integer value and, if it fails, just
        returns the string """
        try:
            ival = int(value, 0)
            return ival
        except ValueError:
            return value

