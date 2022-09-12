#!/bin/env python

import argparse
import re


def main():
    parser = argparse.ArgumentParser(
        description="Generate ofproto field decoders"
    )
    parser.add_argument(
        "-f",
        "--file",
        action="store",
        required=True,
        help="Read meta-flow info from file",
    )

    args = parser.parse_args()

    fields = extract_ofp_fields(args.file)

    field_decoders = {}
    for field in fields:
        decoder = get_decoder(field)
        field_decoders[field.get("name")] = decoder
        if field.get("extra_name"):
            field_decoders[field.get("extra_name")] = decoder

    code = """
# This file is auto-generated. Do not edit

import functools
from ovs_dbg import decoders

field_decoders = {{
{decoders}
}}
""".format(
        decoders="\n".join(
            [
                "'{name}': {decoder},".format(name=name, decoder=decoder)
                for name, decoder in field_decoders.items()
            ]
        )
    )
    print(code)


def get_decoder(field):
    formatting = field.get("formatting")
    if formatting in ["decimal", "hexadecimal"]:
        if field.get("mask") == "MFM_NONE":
            return "decoders.decode_int"
        else:
            if field.get("n_bits") in [8, 16, 32, 64, 128, 992]:
                return "decoders.Mask{}".format(field.get("n_bits"))
            return "decoders.decode_mask({})".format(field.get("n_bits"))
    elif formatting in ["IPv4", "IPv6"]:
        return "decoders.IPMask"
    elif formatting == "Ethernet":
        return "decoders.EthMask"
    else:
        return "decoders.decode_default"


"""
TODO: Use the one in ovs
"""

import getopt
import sys
import os.path
import re
import xml.dom.minidom
import build.nroff

line = ""

# Maps from user-friendly version number to its protocol encoding.
VERSION = {
    "1.0": 0x01,
    "1.1": 0x02,
    "1.2": 0x03,
    "1.3": 0x04,
    "1.4": 0x05,
    "1.5": 0x06,
}
VERSION_REVERSE = dict((v, k) for k, v in VERSION.items())

TYPES = {
    "u8": (1, False),
    "be16": (2, False),
    "be32": (4, False),
    "MAC": (6, False),
    "be64": (8, False),
    "be128": (16, False),
    "tunnelMD": (124, True),
}

FORMATTING = {
    "decimal": ("MFS_DECIMAL", 1, 8),
    "hexadecimal": ("MFS_HEXADECIMAL", 1, 127),
    "ct state": ("MFS_CT_STATE", 4, 4),
    "Ethernet": ("MFS_ETHERNET", 6, 6),
    "IPv4": ("MFS_IPV4", 4, 4),
    "IPv6": ("MFS_IPV6", 16, 16),
    "OpenFlow 1.0 port": ("MFS_OFP_PORT", 2, 2),
    "OpenFlow 1.1+ port": ("MFS_OFP_PORT_OXM", 4, 4),
    "frag": ("MFS_FRAG", 1, 1),
    "tunnel flags": ("MFS_TNL_FLAGS", 2, 2),
    "TCP flags": ("MFS_TCP_FLAGS", 2, 2),
    "packet type": ("MFS_PACKET_TYPE", 4, 4),
}

PREREQS = {
    "none": "MFP_NONE",
    "Ethernet": "MFP_ETHERNET",
    "ARP": "MFP_ARP",
    "VLAN VID": "MFP_VLAN_VID",
    "IPv4": "MFP_IPV4",
    "IPv6": "MFP_IPV6",
    "IPv4/IPv6": "MFP_IP_ANY",
    "NSH": "MFP_NSH",
    "CT": "MFP_CT_VALID",
    "MPLS": "MFP_MPLS",
    "TCP": "MFP_TCP",
    "UDP": "MFP_UDP",
    "SCTP": "MFP_SCTP",
    "ICMPv4": "MFP_ICMPV4",
    "ICMPv6": "MFP_ICMPV6",
    "ND": "MFP_ND",
    "ND solicit": "MFP_ND_SOLICIT",
    "ND advert": "MFP_ND_ADVERT",
}

# Maps a name prefix into an (experimenter ID, class) pair, so:
#
#      - Standard OXM classes are written as (0, <oxm_class>)
#
#      - Experimenter OXM classes are written as (<oxm_vender>, 0xffff)
#
# If a name matches more than one prefix, the longest one is used.
OXM_CLASSES = {
    "NXM_OF_": (0, 0x0000, "extension"),
    "NXM_NX_": (0, 0x0001, "extension"),
    "NXOXM_NSH_": (0x005AD650, 0xFFFF, "extension"),
    "OXM_OF_": (0, 0x8000, "standard"),
    "OXM_OF_PKT_REG": (0, 0x8001, "standard"),
    "ONFOXM_ET_": (0x4F4E4600, 0xFFFF, "standard"),
    "ERICOXM_OF_": (0, 0x1000, "extension"),
    # This is the experimenter OXM class for Nicira, which is the
    # one that OVS would be using instead of NXM_OF_ and NXM_NX_
    # if OVS didn't have those grandfathered in.  It is currently
    # used only to test support for experimenter OXM, since there
    # are barely any real uses of experimenter OXM in the wild.
    "NXOXM_ET_": (0x00002320, 0xFFFF, "extension"),
}


def oxm_name_to_class(name):
    prefix = ""
    class_ = None
    for p, c in OXM_CLASSES.items():
        if name.startswith(p) and len(p) > len(prefix):
            prefix = p
            class_ = c
    return class_


def is_standard_oxm(name):
    oxm_vendor, oxm_class, oxm_class_type = oxm_name_to_class(name)
    return oxm_class_type == "standard"


def decode_version_range(range):
    if range in VERSION:
        return (VERSION[range], VERSION[range])
    elif range.endswith("+"):
        return (VERSION[range[:-1]], max(VERSION.values()))
    else:
        a, b = re.match(r"^([^-]+)-([^-]+)$", range).groups()
        return (VERSION[a], VERSION[b])


def get_line():
    global line
    global line_number
    line = input_file.readline()
    line_number += 1
    if line == "":
        fatal("unexpected end of input")


n_errors = 0


def error(msg):
    global n_errors
    sys.stderr.write("%s:%d: %s\n" % (file_name, line_number, msg))
    n_errors += 1


def fatal(msg):
    error(msg)
    sys.exit(1)


def usage():
    argv0 = os.path.basename(sys.argv[0])
    print(
        """\
%(argv0)s, for extracting OpenFlow field properties from meta-flow.h
usage: %(argv0)s INPUT [--meta-flow | --nx-match]
  where INPUT points to lib/meta-flow.h in the source directory.
Depending on the option given, the output written to stdout is intended to be
saved either as lib/meta-flow.inc or lib/nx-match.inc for the respective C
file to #include.\
"""
        % {"argv0": argv0}
    )
    sys.exit(0)


def make_sizeof(s):
    m = re.match(r"(.*) up to (.*)", s)
    if m:
        struct, member = m.groups()
        return "offsetof(%s, %s)" % (struct, member)
    else:
        return "sizeof(%s)" % s


def parse_oxms(s, prefix, n_bytes):
    if s == "none":
        return ()

    return tuple(parse_oxm(s2.strip(), prefix, n_bytes) for s2 in s.split(","))


match_types = dict()


def parse_oxm(s, prefix, n_bytes):
    global match_types

    m = re.match(
        "([A-Z0-9_]+)\(([0-9]+)\) since(?: OF(1\.[0-9]+) and)? v([12]\.[0-9]+)$",
        s,
    )
    if not m:
        fatal("%s: syntax error parsing %s" % (s, prefix))

    name, oxm_type, of_version, ovs_version = m.groups()

    class_ = oxm_name_to_class(name)
    if class_ is None:
        fatal("unknown OXM class for %s" % name)
    oxm_vendor, oxm_class, oxm_class_type = class_

    if class_ in match_types:
        if oxm_type in match_types[class_]:
            fatal(
                "duplicate match type for %s (conflicts with %s)"
                % (name, match_types[class_][oxm_type])
            )
    else:
        match_types[class_] = dict()
    match_types[class_][oxm_type] = name

    # Normally the oxm_length is the size of the field, but for experimenter
    # OXMs oxm_length also includes the 4-byte experimenter ID.
    oxm_length = n_bytes
    if oxm_class == 0xFFFF:
        oxm_length += 4

    header = (oxm_vendor, oxm_class, int(oxm_type), oxm_length)

    if of_version:
        if oxm_class_type == "extension":
            fatal("%s: OXM extension can't have OpenFlow version" % name)
        if of_version not in VERSION:
            fatal("%s: unknown OpenFlow version %s" % (name, of_version))
        of_version_nr = VERSION[of_version]
        if of_version_nr < VERSION["1.2"]:
            fatal("%s: claimed version %s predates OXM" % (name, of_version))
    else:
        if oxm_class_type == "standard":
            fatal("%s: missing OpenFlow version number" % name)
        of_version_nr = 0

    return (header, name, of_version_nr, ovs_version)


def parse_field(mff, comment):
    f = {"mff": mff}

    # First line of comment is the field name.
    m = re.match(
        r'"([^"]+)"(?:\s+\(aka "([^"]+)"\))?(?:\s+\(.*\))?\.', comment[0]
    )
    if not m:
        fatal("%s lacks field name" % mff)
    f["name"], f["extra_name"] = m.groups()

    # Find the last blank line the comment.  The field definitions
    # start after that.
    blank = None
    for i in range(len(comment)):
        if not comment[i]:
            blank = i
    if not blank:
        fatal("%s: missing blank line in comment" % mff)

    d = {}
    for key in (
        "Type",
        "Maskable",
        "Formatting",
        "Prerequisites",
        "Access",
        "Prefix lookup member",
        "OXM",
        "NXM",
        "OF1.0",
        "OF1.1",
    ):
        d[key] = None
    for fline in comment[blank + 1 :]:
        m = re.match(r"([^:]+):\s+(.*)\.$", fline)
        if not m:
            fatal(
                "%s: syntax error parsing key-value pair as part of %s"
                % (fline, mff)
            )
        key, value = m.groups()
        if key not in d:
            fatal("%s: unknown key" % key)
        elif key == "Code point":
            d[key] += [value]
        elif d[key] is not None:
            fatal("%s: duplicate key" % key)
        d[key] = value
    for key, value in d.items():
        if not value and key not in (
            "OF1.0",
            "OF1.1",
            "Prefix lookup member",
            "Notes",
        ):
            fatal("%s: missing %s" % (mff, key))

    m = re.match(r"([a-zA-Z0-9]+)(?: \(low ([0-9]+) bits\))?$", d["Type"])
    if not m:
        fatal("%s: syntax error in type" % mff)
    type_ = m.group(1)
    if type_ not in TYPES:
        fatal("%s: unknown type %s" % (mff, d["Type"]))

    f["n_bytes"] = TYPES[type_][0]
    if m.group(2):
        f["n_bits"] = int(m.group(2))
        if f["n_bits"] > f["n_bytes"] * 8:
            fatal(
                "%s: more bits (%d) than field size (%d)"
                % (mff, f["n_bits"], 8 * f["n_bytes"])
            )
    else:
        f["n_bits"] = 8 * f["n_bytes"]
    f["variable"] = TYPES[type_][1]

    if d["Maskable"] == "no":
        f["mask"] = "MFM_NONE"
    elif d["Maskable"] == "bitwise":
        f["mask"] = "MFM_FULLY"
    else:
        fatal("%s: unknown maskable %s" % (mff, d["Maskable"]))

    fmt = FORMATTING.get(d["Formatting"])
    if not fmt:
        fatal("%s: unknown format %s" % (mff, d["Formatting"]))
    f["formatting"] = d["Formatting"]
    if f["n_bytes"] < fmt[1] or f["n_bytes"] > fmt[2]:
        fatal(
            "%s: %d-byte field can't be formatted as %s"
            % (mff, f["n_bytes"], d["Formatting"])
        )
    f["string"] = fmt[0]

    f["prereqs"] = d["Prerequisites"]
    if f["prereqs"] not in PREREQS:
        fatal("%s: unknown prerequisites %s" % (mff, d["Prerequisites"]))

    if d["Access"] == "read-only":
        f["writable"] = False
    elif d["Access"] == "read/write":
        f["writable"] = True
    else:
        fatal("%s: unknown access %s" % (mff, d["Access"]))

    f["OF1.0"] = d["OF1.0"]
    if not d["OF1.0"] in (None, "exact match", "CIDR mask"):
        fatal("%s: unknown OF1.0 match type %s" % (mff, d["OF1.0"]))

    f["OF1.1"] = d["OF1.1"]
    if not d["OF1.1"] in (None, "exact match", "bitwise mask"):
        fatal("%s: unknown OF1.1 match type %s" % (mff, d["OF1.1"]))

    f["OXM"] = parse_oxms(d["OXM"], "OXM", f["n_bytes"]) + parse_oxms(
        d["NXM"], "NXM", f["n_bytes"]
    )

    f["prefix"] = d["Prefix lookup member"]

    return f


def protocols_to_c(protocols):
    if protocols == set(["of10", "of11", "oxm"]):
        return "OFPUTIL_P_ANY"
    elif protocols == set(["of11", "oxm"]):
        return "OFPUTIL_P_NXM_OF11_UP"
    elif protocols == set(["oxm"]):
        return "OFPUTIL_P_NXM_OXM_ANY"
    elif protocols == set([]):
        return "OFPUTIL_P_NONE"
    else:
        assert False


def autogen_c_comment():
    return [
        "/* Generated automatically; do not modify!    -*- buffer-read-only: t -*- */",
        "",
    ]


def make_meta_flow(meta_flow_h):
    fields = extract_ofp_fields(meta_flow_h)
    output = autogen_c_comment()
    for f in fields:
        output += ["{"]
        output += ["    %s," % f["mff"]]
        if f["extra_name"]:
            output += ['    "%s", "%s",' % (f["name"], f["extra_name"])]
        else:
            output += ['    "%s", NULL,' % f["name"]]

        if f["variable"]:
            variable = "true"
        else:
            variable = "false"
        output += ["    %d, %d, %s," % (f["n_bytes"], f["n_bits"], variable)]

        if f["writable"]:
            rw = "true"
        else:
            rw = "false"
        output += [
            "    %s, %s, %s, %s, false,"
            % (f["mask"], f["string"], PREREQS[f["prereqs"]], rw)
        ]

        oxm = f["OXM"]
        of10 = f["OF1.0"]
        of11 = f["OF1.1"]
        if f["mff"] in ("MFF_DL_VLAN", "MFF_DL_VLAN_PCP"):
            # MFF_DL_VLAN and MFF_DL_VLAN_PCP don't exactly correspond to
            # OF1.1, nor do they have NXM or OXM assignments, but their
            # meanings can be expressed in every protocol, which is the goal of
            # this member.
            protocols = set(["of10", "of11", "oxm"])
        else:
            protocols = set([])
            if of10:
                protocols |= set(["of10"])
            if of11:
                protocols |= set(["of11"])
            if oxm:
                protocols |= set(["oxm"])

        if f["mask"] == "MFM_FULLY":
            cidr_protocols = protocols.copy()
            bitwise_protocols = protocols.copy()

            if of10 == "exact match":
                bitwise_protocols -= set(["of10"])
                cidr_protocols -= set(["of10"])
            elif of10 == "CIDR mask":
                bitwise_protocols -= set(["of10"])
            else:
                assert of10 is None

            if of11 == "exact match":
                bitwise_protocols -= set(["of11"])
                cidr_protocols -= set(["of11"])
            else:
                assert of11 in (None, "bitwise mask")
        else:
            assert f["mask"] == "MFM_NONE"
            cidr_protocols = set([])
            bitwise_protocols = set([])

        output += ["    %s," % protocols_to_c(protocols)]
        output += ["    %s," % protocols_to_c(cidr_protocols)]
        output += ["    %s," % protocols_to_c(bitwise_protocols)]

        if f["prefix"]:
            output += ["    FLOW_U32OFS(%s)," % f["prefix"]]
        else:
            output += ["    -1, /* not usable for prefix lookup */"]

        output += ["},"]
    for oline in output:
        print(oline)


def make_nx_match(meta_flow_h):
    fields = extract_ofp_fields(meta_flow_h)
    output = autogen_c_comment()
    print("static struct nxm_field_index all_nxm_fields[] = {")
    for f in fields:
        # Sort by OpenFlow version number (nx-match.c depends on this).
        for oxm in sorted(f["OXM"], key=lambda x: x[2]):
            header = "NXM_HEADER(0x%x,0x%x,%s,0,%d)" % oxm[0]
            print(
                """{ .nf = { %s, %d, "%s", %s } },"""
                % (header, oxm[2], oxm[1], f["mff"])
            )
    print("};")
    for oline in output:
        print(oline)


def extract_ofp_fields(fn):
    global file_name
    global input_file
    global line_number
    global line

    file_name = fn
    input_file = open(file_name)
    line_number = 0

    fields = []

    while True:
        get_line()
        if re.match("enum.*mf_field_id", line):
            break

    while True:
        get_line()
        first_line_number = line_number
        here = "%s:%d" % (file_name, line_number)
        if (
            line.startswith("/*")
            or line.startswith(" *")
            or line.startswith("#")
            or not line
            or line.isspace()
        ):
            continue
        elif re.match("}", line) or re.match("\s+MFF_N_IDS", line):
            break

        # Parse the comment preceding an MFF_ constant into 'comment',
        # one line to an array element.
        line = line.strip()
        if not line.startswith("/*"):
            fatal("unexpected syntax between fields")
        line = line[1:]
        comment = []
        end = False
        while not end:
            line = line.strip()
            if line.startswith("*/"):
                get_line()
                break
            if not line.startswith("*"):
                fatal("unexpected syntax within field")

            line = line[1:]
            if line.startswith(" "):
                line = line[1:]
            if line.startswith(" ") and comment:
                continuation = True
                line = line.lstrip()
            else:
                continuation = False

            if line.endswith("*/"):
                line = line[:-2].rstrip()
                end = True
            else:
                end = False

            if continuation:
                comment[-1] += " " + line
            else:
                comment += [line]
            get_line()

        # Drop blank lines at each end of comment.
        while comment and not comment[0]:
            comment = comment[1:]
        while comment and not comment[-1]:
            comment = comment[:-1]

        # Parse the MFF_ constant(s).
        mffs = []
        while True:
            m = re.match("\s+(MFF_[A-Z0-9_]+),?\s?$", line)
            if not m:
                break
            mffs += [m.group(1)]
            get_line()
        if not mffs:
            fatal("unexpected syntax looking for MFF_ constants")

        if len(mffs) > 1 or "<N>" in comment[0]:
            for mff in mffs:
                # Extract trailing integer.
                m = re.match(".*[^0-9]([0-9]+)$", mff)
                if not m:
                    fatal("%s lacks numeric suffix in register group" % mff)
                n = m.group(1)

                # Search-and-replace <N> within the comment,
                # and drop lines that have <x> for x != n.
                instance = []
                for x in comment:
                    y = x.replace("<N>", n)
                    if re.search("<[0-9]+>", y):
                        if ("<%s>" % n) not in y:
                            continue
                        y = re.sub("<[0-9]+>", "", y)
                    instance += [y.strip()]
                fields += [parse_field(mff, instance)]
        else:
            fields += [parse_field(mffs[0], comment)]
        continue

    input_file.close()

    if n_errors:
        sys.exit(1)

    return fields


## ------------------------ ##
## Documentation Generation ##
## ------------------------ ##


def field_to_xml(field_node, f, body, summary):
    f["used"] = True

    # Summary.
    if field_node.hasAttribute("internal"):
        return

    min_of_version = None
    min_ovs_version = None
    for header, name, of_version_nr, ovs_version_s in f["OXM"]:
        if is_standard_oxm(name) and (
            min_ovs_version is None or of_version_nr < min_of_version
        ):
            min_of_version = of_version_nr
        ovs_version = [int(x) for x in ovs_version_s.split(".")]
        if min_ovs_version is None or ovs_version < min_ovs_version:
            min_ovs_version = ovs_version
    summary += ["\\fB%s\\fR" % f["name"]]
    if f["extra_name"]:
        summary += [" aka \\fB%s\\fR" % f["extra_name"]]
    summary += [";%d" % f["n_bytes"]]
    if f["n_bits"] != 8 * f["n_bytes"]:
        summary += [" (low %d bits)" % f["n_bits"]]
    summary += [";%s;" % {"MFM_NONE": "no", "MFM_FULLY": "yes"}[f["mask"]]]
    summary += ["%s;" % {True: "yes", False: "no"}[f["writable"]]]
    summary += ["%s;" % f["prereqs"]]
    support = []
    if min_of_version is not None:
        support += ["OF %s+" % VERSION_REVERSE[min_of_version]]
    if min_ovs_version is not None:
        support += ["OVS %s+" % ".".join([str(x) for x in min_ovs_version])]
    summary += " and ".join(support)
    summary += ["\n"]

    # Full description.
    if field_node.hasAttribute("hidden"):
        return

    title = field_node.attributes["title"].nodeValue

    body += [
        """.PP
\\fB%s Field\\fR
.TS
tab(;);
l lx.
"""
        % title
    ]

    body += ["Name:;\\fB%s\\fR" % f["name"]]
    if f["extra_name"]:
        body += [" (aka \\fB%s\\fR)" % f["extra_name"]]
    body += ["\n"]

    body += ["Width:;"]
    if f["n_bits"] != 8 * f["n_bytes"]:
        body += [
            "%d bits (only the least-significant %d bits "
            "may be nonzero)" % (f["n_bytes"] * 8, f["n_bits"])
        ]
    elif f["n_bits"] <= 128:
        body += ["%d bits" % f["n_bits"]]
    else:
        body += ["%d bits (%d bytes)" % (f["n_bits"], f["n_bits"] / 8)]
    body += ["\n"]

    body += ["Format:;%s\n" % f["formatting"]]

    masks = {
        "MFM_NONE": "not maskable",
        "MFM_FULLY": "arbitrary bitwise masks",
    }
    body += ["Masking:;%s\n" % masks[f["mask"]]]
    body += ["Prerequisites:;%s\n" % f["prereqs"]]

    access = {True: "read/write", False: "read-only"}[f["writable"]]
    body += ["Access:;%s\n" % access]

    of10 = {
        None: "not supported",
        "exact match": "yes (exact match only)",
        "CIDR mask": "yes (CIDR match only)",
    }
    body += ["OpenFlow 1.0:;%s\n" % of10[f["OF1.0"]]]

    of11 = {
        None: "not supported",
        "exact match": "yes (exact match only)",
        "bitwise mask": "yes",
    }
    body += ["OpenFlow 1.1:;%s\n" % of11[f["OF1.1"]]]

    oxms = []
    for header, name, of_version_nr, ovs_version in [
        x
        for x in sorted(f["OXM"], key=lambda x: x[2])
        if is_standard_oxm(x[1])
    ]:
        of_version = VERSION_REVERSE[of_version_nr]
        oxms += [
            r"\fB%s\fR (%d) since OpenFlow %s and Open vSwitch %s"
            % (name, header[2], of_version, ovs_version)
        ]
    if not oxms:
        oxms = ["none"]
    body += ["OXM:;T{\n%s\nT}\n" % r"\[char59] ".join(oxms)]

    nxms = []
    for header, name, of_version_nr, ovs_version in [
        x
        for x in sorted(f["OXM"], key=lambda x: x[2])
        if not is_standard_oxm(x[1])
    ]:
        nxms += [
            r"\fB%s\fR (%d) since Open vSwitch %s"
            % (name, header[2], ovs_version)
        ]
    if not nxms:
        nxms = ["none"]
    body += ["NXM:;T{\n%s\nT}\n" % r"\[char59] ".join(nxms)]

    body += [".TE\n"]

    body += [".PP\n"]
    body += [build.nroff.block_xml_to_nroff(field_node.childNodes)]


def group_xml_to_nroff(group_node, fields):
    title = group_node.attributes["title"].nodeValue

    summary = []
    body = []
    for node in group_node.childNodes:
        if node.nodeType == node.ELEMENT_NODE and node.tagName == "field":
            id_ = node.attributes["id"].nodeValue
            field_to_xml(node, fields[id_], body, summary)
        else:
            body += [build.nroff.block_xml_to_nroff([node])]

    content = [
        ".bp\n",
        '.SH "%s"\n' % build.nroff.text_to_nroff(title.upper() + " FIELDS"),
        '.SS "Summary:"\n',
        ".TS\n",
        "tab(;);\n",
        "l l l l l l l.\n",
        "Name;Bytes;Mask;RW?;Prereqs;NXM/OXM Support\n",
        "\_;\_;\_;\_;\_;\_\n",
    ]
    content += summary
    content += [".TE\n"]
    content += body
    return "".join(content)


def make_oxm_classes_xml(document):
    s = """tab(;);
l l l.
Prefix;Vendor;Class
\_;\_;\_
"""
    for key in sorted(OXM_CLASSES, key=OXM_CLASSES.get):
        vendor, class_, class_type = OXM_CLASSES.get(key)
        s += r"\fB%s\fR;" % key.rstrip("_")
        if vendor:
            s += r"\fL0x%08x\fR;" % vendor
        else:
            s += "(none);"
        s += r"\fL0x%04x\fR;" % class_
        s += "\n"
    e = document.createElement("tbl")
    e.appendChild(document.createTextNode(s))
    return e


def recursively_replace(node, name, replacement):
    for child in node.childNodes:
        if child.nodeType == node.ELEMENT_NODE:
            if child.tagName == name:
                node.replaceChild(replacement, child)
            else:
                recursively_replace(child, name, replacement)


def make_ovs_fields(meta_flow_h, meta_flow_xml):
    fields = extract_ofp_fields(meta_flow_h)
    fields_map = {}
    for f in fields:
        fields_map[f["mff"]] = f

    document = xml.dom.minidom.parse(meta_flow_xml)
    doc = document.documentElement

    global version
    if version == None:
        version = "UNKNOWN"

    print(
        """\
'\\" tp
.\\" -*- mode: troff; coding: utf-8 -*-
.TH "ovs\-fields" 7 "%s" "Open vSwitch" "Open vSwitch Manual"
.fp 5 L CR              \\" Make fixed-width font available as \\fL.
.de ST
.  PP
.  RS -0.15in
.  I "\\\\$1"
.  RE
..

.de SU
.  PP
.  I "\\\\$1"
..

.de IQ
.  br
.  ns
.  IP "\\\\$1"
..

.de TQ
.  br
.  ns
.  TP "\\\\$1"
..
.de URL
\\\\$2 \\(laURL: \\\\$1 \\(ra\\\\$3
..
.if \\n[.g] .mso www.tmac
.SH NAME
ovs\-fields \- protocol header fields in OpenFlow and Open vSwitch
.
.PP
"""
        % version
    )

    recursively_replace(doc, "oxm_classes", make_oxm_classes_xml(document))

    s = ""
    for node in doc.childNodes:
        if node.nodeType == node.ELEMENT_NODE and node.tagName == "group":
            s += group_xml_to_nroff(node, fields_map)
        elif node.nodeType == node.TEXT_NODE:
            assert node.data.isspace()
        elif node.nodeType == node.COMMENT_NODE:
            pass
        else:
            s += build.nroff.block_xml_to_nroff([node])

    for f in fields:
        if "used" not in f:
            fatal(
                "%s: field not documented "
                "(please add documentation in lib/meta-flow.xml)" % f["mff"]
            )
    if n_errors:
        sys.exit(1)

    output = []
    for oline in s.split("\n"):
        oline = oline.strip()

        # Life is easier with nroff if we don't try to feed it Unicode.
        # Fortunately, we only use a few characters outside the ASCII range.
        oline = oline.replace("\u2208", r"\[mo]")
        oline = oline.replace("\u2260", r"\[!=]")
        oline = oline.replace("\u2264", r"\[<=]")
        oline = oline.replace("\u2265", r"\[>=]")
        oline = oline.replace("\u00d7", r"\[mu]")
        if len(oline):
            output += [oline]

    # nroff tends to ignore .bp requests if they come after .PP requests,
    # so remove .PPs that precede .bp.
    for i in range(len(output)):
        if output[i] == ".bp":
            j = i - 1
            while j >= 0 and output[j] == ".PP":
                output[j] = None
                j -= 1
    for i in range(len(output)):
        if output[i] is not None:
            print(output[i])


if __name__ == "__main__":
    main()
