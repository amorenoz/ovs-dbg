""" Defines helpful decoders that can be used to decode information from the
flows

A decoder is generally a callable that accepts a string and returns the value
object
"""

import re
import functools
import netaddr
import json


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


def decode_mask(size, value):
    """value/mask decoder for values of specific size (bits)

    Used for fields such as:
        reg0=0x248/0xff
    """
    parts = value.split("/")
    if len(parts) > 1:
        value = int(parts[0], 0)
        mask = int(parts[1], 0)
    else:
        value = int(parts[0], 0)
        mask = 2 ** size - 1

    return {"value": value, "mask": mask}


decode_mask8 = functools.partial(decode_mask, 8)
decode_mask16 = functools.partial(decode_mask, 16)
decode_mask32 = functools.partial(decode_mask, 32)
decode_mask64 = functools.partial(decode_mask, 64)
decode_mask128 = functools.partial(decode_mask, 128)


class EthMask:
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


def decode_mac(value):
    """MAC address decoder"""
    return EthMask(value)


class IPMask:
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


def decode_ip(value):
    """IP address decoder. Supports both IPv4 and IPv6 addresses

    Used for fields such as:
        nw_src=192.168.1.1
        nw_src=192.168.1.0/24
        nw_src=192.168.1.0/255.255.255.0
        nw_dst=2001:db8::1000
        nw_dst=2001:db8::0/24
    """
    return IPMask(value)


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
        if (
            isinstance(obj, IPMask)
            or isinstance(obj, EthMask)
            or isinstance(obj, netaddr.IPAddress)
        ):
            return str(obj)
        return json.JSONEncoder.default(self, obj)
