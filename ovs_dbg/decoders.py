""" Defines helpful decoders that can be used to decode information from the
flows

A decoder is generally a callable that accepts a string and returns the value
object
"""

import functools
import json
import netaddr
import re


class Decoder:
    """Base class for all decoder classes"""

    def to_json(self):
        assert "function must be implemented by derived class"


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


def decode_flag(value):
    """Default a flag. It's exising is just flagged by returning True"""
    return True


def decode_int(value):
    """integer decoder

    Both base10 and base16 integers are supported

    Used for fields such as:
        n_bytes=34
        metadata=0x4
    """
    return int(value, 0)


def decode_time(value):
    """time decoder

    Used for fields such as:
        duration=1234.123s
    """
    if value == "never":
        return value

    time_str = value.rstrip("s")
    return float(time_str)


class IntMask(Decoder):
    """Base class for Integer Mask decoder classes

    It supports decoding a value/mask pair. It has to be derived and size
    has to be set to a specific value
    """

    size = None  # size in bits

    def __init__(self, string):
        if not self.size:
            assert "IntMask should be derived and size should be fixed"

        parts = string.split("/")
        if len(parts) > 1:
            self._value = int(parts[0], 0)
            self._mask = int(parts[1], 0)
            if self._mask.bit_length() > self.size:
                raise ValueError(
                    "Integer mask {} is bigger than size {}".format(
                        self._mask, self.size
                    )
                )
        else:
            self._value = int(parts[0], 0)
            self._mask = 2 ** self.size - 1

        if self._value.bit_length() > self.size:
            raise ValueError(
                "Integer value {} is bigger than size {}".format(self._value, self.size)
            )

    @property
    def value(self):
        return self._value

    @property
    def mask(self):
        return self._mask

    def max_mask(self):
        return 2 ** self.size - 1

    def fully(self):
        """Returns if it's fully masked"""
        return self._mask == self.max_mask()

    def min(self):
        return self._value & self._mask

    def max(self):
        return (self.max_mask() & ~self._mask) | (self._value & self._mask)

    def __str__(self):
        if self.fully():
            return str(self._value)
        else:
            return "{}/{}".format(hex(self._value), hex(self._mask))

    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, self)

    def __eq__(self, other):
        return self.value == other.value and self.mask == other.mask

    def __contains__(self, other):
        if isinstance(other, IntMask):
            if other.fully():
                return other.value in self
            return other.min() in self and other.max() in self
        else:
            return other & self._mask == self._value & self._mask

    def dict(self):
        return {"value": self._value, "mask": self._mask}

    def to_json(self):
        return self.dict()


class Mask8(IntMask):
    size = 8


class Mask16(IntMask):
    size = 16


class Mask32(IntMask):
    size = 32


class Mask64(IntMask):
    size = 64


class Mask128(IntMask):
    size = 128


class Mask992(IntMask):
    size = 992


def decode_mask(mask_size):
    """value/mask decoder for values of specific size (bits)

    Used for fields such as:
        reg0=0x248/0xff
    """

    class Mask(IntMask):
        size = mask_size
        __name__ = "Mask{}".format(size)

    return Mask



class EthMask(Decoder):
    """EthMask represents an Ethernet address with optional mask

    It uses netaddr.EUI

    Attributes:
        eth (netaddr.EUI): the ethernet address
        mask (netaddr.EUI): Optional, the ethernet address mask

    Args:
        string (str): A string representing the masked ethernet address
            e.g: 00.11:22:33:44:55 or 01:00:22:00:33:00/01:00:00:00:00:00
    """

    def __init__(self, string):
        mask_parts = string.split("/")
        self._eth = netaddr.EUI(mask_parts[0])
        if len(mask_parts) == 2:
            self._mask = netaddr.EUI(mask_parts[1])
        else:
            self._mask = None

    @property
    def eth(self):
        """The ethernet address"""
        return self._eth

    @property
    def mask(self):
        """The ethernet address mask"""
        return self._mask

    def __eq__(self, other):
        """Returns True if this EthMask is numerically the same as other"""
        return self._mask == other._mask and self._eth == other._eth

    def __contains__(self, other):
        """
        Args:
            other (netaddr.EUI): another Ethernet address

        Returns:
            True if other falls into the masked address range
        """
        if isinstance(other, EthMask):
            if other._mask:
                raise ValueError("EthMask mask comparison not supported")
            return other._eth in self

        if self._mask:
            return (other.value & self._mask.value) == (
                self._eth.value & self._mask.value
            )
        else:
            return other == self._eth

    def __str__(self):
        if self._mask:
            return "/".join(
                [
                    self._eth.format(netaddr.mac_unix),
                    self._mask.format(netaddr.mac_unix),
                ]
            )
        else:
            return self._eth.format(netaddr.mac_unix)

    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, self)

    def to_json(self):
        return str(self)


class IPMask(Decoder):
    """IPMask stores an IPv6 or IPv4 and a mask

    It uses netaddr.IPAddress. The IPMask can be represented by a
    netaddr.IPNetwork (if it's a valid cidr) or by an ip and a mask

    Args:
        string (str): A string representing the ip/mask
    """

    def __init__(self, string):
        """Constructor"""
        self._ipnet = None
        self._ip = None
        self._mask = None
        try:
            self._ipnet = netaddr.IPNetwork(string)
        except netaddr.AddrFormatError:
            pass

        if not self._ipnet:
            # It's not a valid CIDR. Store ip and mask indendently
            parts = string.split("/")
            if len(parts) != 2:
                raise ValueError(
                    "value {}: is not an ipv4 or ipv6 address".format(string)
                )
            try:
                self._ip = netaddr.IPAddress(parts[0])
                self._mask = netaddr.IPAddress(parts[1])
            except netaddr.AddrFormatError as exc:
                raise ValueError(
                    "value {}: is not an ipv4 or ipv6 address".format(string)
                ) from exc

    def __eq__(self, other):
        """Returns True if this IPMask is numerically the same as other"""
        if isinstance(other, netaddr.IPNetwork):
            return self._ipnet and self._ipnet == other
        if isinstance(other, netaddr.IPAddress):
            return self._ipnet and self._ipnet.ip == other
        elif isinstance(other, IPMask):
            if self._ipnet:
                return self._ipnet == other._ipnet

            return self._ip == other._ip and self._mask == other._mask
        else:
            return False

    def __contains__(self, other):
        """
        Args:
            other (netaddr.IPAddres): another IP address

        Returns:
            True if other falls into the masked ip range
        """
        if isinstance(other, IPMask):
            if not other._ipnet:
                raise ValueError("ip/mask comparisons not supported")

            return (
                netaddr.IPAddress(other._ipnet.first) in self
                and netaddr.IPAddress(other._ipnet.last) in self
            )

        elif isinstance(other, netaddr.IPAddress):
            if self._ipnet:
                return other in self._ipnet
            return (other & self._mask) == (self._ip & self._mask)

    def cidr(self):
        """
        Returns True if the IPMask is a valid CIDR
        """
        return self._ipnet is not None

    @property
    def ip(self):
        """The IP address"""
        if self._ipnet:
            return self._ipnet.ip
        return self._ip

    @property
    def mask(self):
        """The IP mask"""
        if self._ipnet:
            return self._ipnet.netmask
        return self._mask

    def __str__(self):
        if self._ipnet:
            return str(self._ipnet)
        return "/".join([str(self._ip), str(self._mask)])

    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, self)

    def to_json(self):
        return str(self)


def decode_free_output(value):
    """Decodes the output value when found free (without the 'output' keyword)"""
    try:
        return "output", {"port": int(value)}
    except ValueError:
        return "output", {"port": value.strip('"')}


ipv4 = r"[\d\.]+"
ipv4_capture = r"({ipv4})".format(ipv4=ipv4)
ipv6 = r"[\w:]+"
ipv6_capture = r"(?:\[*)?({ipv6})(?:\]*)?".format(ipv6=ipv6)
port_range = r":(\d+)(?:-(\d+))?"
ip_range_regexp = r"{ip_cap}(?:-{ip_cap})?(?:{port_range})?"
ipv4_port_regex = re.compile(
    ip_range_regexp.format(ip_cap=ipv4_capture, port_range=port_range)
)
ipv6_port_regex = re.compile(
    ip_range_regexp.format(ip_cap=ipv6_capture, port_range=port_range)
)


def decode_ip_port_range(value):
    """
    Decodes an IP and port range:
        {ip_start}-{ip-end}:{port_start}-{port_end}

    IPv6 addresses are surrounded by "[" and "]" if port ranges are also
    present

    Returns the following dictionary:
        {
            "addrs": {
                "start": {ip_start}
                "end": {ip_end}
            }
            "ports": {
                "start": {port_start},
                "end": {port_end}
        }
        (the "ports" key might be omitted)
    """
    if value.count(":") > 1:
        match = ipv6_port_regex.match(value)
    else:
        match = ipv4_port_regex.match(value)

    ip_start = match.group(1)
    ip_end = match.group(2)
    port_start = match.group(3)
    port_end = match.group(4)

    result = {
        "addrs": {
            "start": netaddr.IPAddress(ip_start),
            "end": netaddr.IPAddress(ip_end or ip_start),
        }
    }
    if port_start:
        result["ports"] = {"start": int(port_start), "end": int(port_end or port_start)}

    return result


def decode_nat(value):
    """Decodes the 'nat' keyword of the ct action"""
    if not value:
        return True

    result = dict()
    type_parts = value.split("=")
    result["type"] = type_parts[0]

    if len(type_parts) > 1:
        value_parts = type_parts[1].split(",")
        if len(type_parts) != 2:
            raise ValueError("Malformed nat action: %s" % value)

        ip_port_range = decode_ip_port_range(value_parts[0])

        result = {"type": type_parts[0], **ip_port_range}

        for flag in value_parts[1:]:
            result[flag] = True

    return result


class FlowEncoder(json.JSONEncoder):
    """FlowEncoder is a json.JSONEncoder instance that can be used to
    serialize flow fields
    """

    def default(self, obj):
        if isinstance(obj, Decoder):
            return obj.to_json()
        elif isinstance(obj, netaddr.IPAddress):
            return str(obj)

        return json.JSONEncoder.default(self, obj)
