import sys
import itertools
import click
import colorsys
from rich.tree import Tree
from rich.text import Text
from rich.console import Console
from rich.style import Style
from rich.color import Color

from ovs_dbg.ofp import OFPFlow
from ovs_dbg.ofparse.main import maincli
from ovs_dbg.ofparse.process import process_flows, tojson, pprint
from ovs_dbg.ofparse.console import (
    ConsoleBuffer,
    ConsoleFormatter,
    hash_pallete,
    heat_pallete,
    print_context,
)
from ovs_dbg.ofparse.html import HTMLBuffer, HTMLFormatter

# Try to make it easy to spot same cookies by printing them in different
# colors
cookie_style_gen = hash_pallete(
    hue=[x / 10 for x in range(0, 10)],
    saturation=[0.5],
    value=[0.5 + x / 10 * (0.85 - 0.5) for x in range(0, 10)],
)


@maincli.group(subcommand_metavar="FORMAT")
@click.pass_obj
def openflow(opts):
    """Process OpenFlow Flows"""
    pass


@openflow.command()
@click.pass_obj
def json(opts):
    """Print the flows in JSON format"""
    return tojson(flow_factory=create_ofp_flow, opts=opts)


@openflow.command()
@click.option(
    "-h",
    "--heat-map",
    is_flag=True,
    default=False,
    show_default=True,
    help="Create heat-map with packet and byte counters",
)
@click.pass_obj
def pretty(opts, heat_map):
    """Print the flows with some style"""
    flows = list()

    def callback(flow):
        """Parse the flows and sort them by table"""
        flows.append(flow)

    process_flows(
        flow_factory=create_ofp_flow,
        callback=callback,
        filename=opts.get("filename"),
        filter=opts.get("filter"),
    )

    console = ConsoleFormatter(opts)
    if heat_map and len(flows) > 0:
        for field in ["n_packets", "n_bytes"]:
            values = [f.info.get(field) or 0 for f in flows]
            console.style.set_value_style(field, heat_pallete(min(values), max(values)))

    for flow in flows:
        high = None
        if opts.get("highlight"):
            result = opts.get("highlight").evaluate(flow)
            if result:
                high = result.kv
        with print_context(console.console, opts):
            console.print_flow(flow, high)


@openflow.command()
@click.option(
    "-s",
    "--show-flows",
    is_flag=True,
    default=False,
    show_default=True,
    help="Show the full flows under each logical flow",
)
@click.option(
    "-c",
    "--cookie",
    "cookie_flag",
    is_flag=True,
    default=False,
    show_default=True,
    help="Consider the cookie in the logical flow",
)
@click.option(
    "-h",
    "--heat-map",
    is_flag=True,
    default=False,
    show_default=True,
    help="Create heat-map with packet and byte counters (when -s is used)",
)
@click.pass_obj
def logic(opts, show_flows, cookie_flag, heat_map):
    """
    Print the logical structure of the flows.

    First, sorts the flows based on tables and priorities.
    Then, deduplicates logically equivalent flows: these a flows that match
    on the same set of fields (regardless of the values they match against),
    have the same priority, and actions (regardless of action arguments,
    except in the case of output and recirculate).
    Optionally, the cookie can also be considered to be part of the logical
    flow.
    """
    tables = dict()

    class LFlow:
        """A Logical Flow represents the scheleton of a flow

        Attributes:
            flow (OFPFlow): The flow
            match_action_keys(list): Optional; list of action keys that are
                mathched exactly (not just the key but the value also)
            match_cookie (bool): Optional; if cookies are part of the logical
                flow
        """

        def __init__(self, flow, match_action_keys=[], match_cookie=False):
            self.cookie = flow.info.get("cookie") or 0 if match_cookie else None
            self.priority = flow.match.get("priority") or 0
            self.match_keys = tuple([kv.key for kv in flow.match_kv])

            self.action_keys = tuple(
                [kv.key for kv in flow.actions_kv if kv.key not in match_action_keys]
            )
            self.match_action_kvs = [
                kv for kv in flow.actions_kv if kv.key in match_action_keys
            ]

        def __eq__(self, other):
            return (
                (self.cookie == other.cookie if self.cookie else True)
                and self.priority == other.priority
                and self.action_keys == other.action_keys
                and self.equal_match_action_kvs(other)
                and self.match_keys == other.match_keys
            )

        def equal_match_action_kvs(self, other):
            """
            Compares the logical flow's match action key-values with the other's
            Args:
                other (LFlow): The other LFlow to compare against

            Returns true if both LFlow have the same action k-v
            """
            if len(other.match_action_kvs) != len(self.match_action_kvs):
                return False

            for kv in self.match_action_kvs:
                found = False
                for other_kv in other.match_action_kvs:
                    if self.match_kv(kv, other_kv):
                        found = True
                        break
                if not found:
                    return False
            return True

        def match_kv(self, one, other):
            """Compares a KeyValue
            Args:
                one, other (KeyValue): The objects to compare

            Returns true if both KeyValue objects have the same key and value
            """
            return one.key == other.key and one.value == other.value

        def __hash__(self):
            hash_data = [
                self.cookie,
                self.priority,
                self.action_keys,
                tuple((kv.key, str(kv.value)) for kv in self.match_action_kvs),
                self.match_keys,
            ]
            if self.cookie:
                hash_data.append(self.cookie)
            return tuple(hash_data).__hash__()

        def format(self, buf):
            """Format the Logical Flow into a Buffer"""
            formatter = ConsoleFormatter(opts)

            if self.cookie:
                buf.append_extra(
                    "cookie={} ".format(hex(self.cookie)).ljust(18),
                    style=cookie_style_gen(str(self.cookie)),
                )

            buf.append_extra("priority={} ".format(self.priority), style="steel_blue")
            buf.append_extra(",".join(self.match_keys), style="steel_blue")
            buf.append_extra("  --->  ", style="bold magenta")
            buf.append_extra(",".join(lflow.action_keys), style="steel_blue")

            if len(self.match_action_kvs) > 0:
                buf.append_extra(" ", style=None)

            for kv in self.match_action_kvs:
                formatter.format_kv(buf, kv, formatter.style)
                buf.append_extra(",", style=None)

    def callback(flow):
        """Parse the flows and sort them by table and logical flow"""
        table = flow.info.get("table") or 0
        if not tables.get(table):
            tables[table] = dict()

        # Group flows by logical hash
        lflow = LFlow(
            flow,
            match_action_keys=["output", "resubmit", "drop"],
            match_cookie=cookie_flag,
        )

        if not tables[table].get(lflow):
            tables[table][lflow] = list()

        tables[table][lflow].append(flow)

    process_flows(
        flow_factory=create_ofp_flow,
        callback=callback,
        filename=opts.get("filename"),
        filter=opts.get("filter"),
    )

    tree = Tree("Ofproto Flows (logical)")
    console = Console(color_system=None if opts["style"] is None else "256")
    formatter = ConsoleFormatter(opts=opts, console=console)

    for table_num in sorted(tables.keys()):
        table = tables[table_num]
        table_tree = tree.add("** TABLE {} **".format(table_num))

        if heat_map:
            for field in ["n_packets", "n_bytes"]:
                values = []
                for flow_list in table.values():
                    values.extend([f.info.get(field) or 0 for f in flow_list])
                formatter.style.set_value_style(
                    field, heat_pallete(min(values), max(values))
                )

        for lflow in sorted(
            table.keys(),
            key=(lambda x: x.priority),
            reverse=True,
        ):
            flows = table[lflow]

            buf = ConsoleBuffer(Text())

            lflow.format(buf)
            buf.append_extra(" ( x {} )".format(len(flows)), style="dark_olive_green3")
            lflow_tree = table_tree.add(buf.text)

            if show_flows:
                for flow in flows:
                    buf = ConsoleBuffer(Text())
                    highlighted = None
                    if opts.get("highlight"):
                        result = opts.get("highlight").evaluate(flow)
                        if result:
                            highlighted = result.kv
                    formatter.format_flow(buf, flow, highlighted)
                    lflow_tree.add(buf.text)

    with print_context(console, opts):
        console.print(tree)


@openflow.command()
@click.pass_obj
def html(opts):
    """Print the flows in an HTML list"""
    tables = dict()

    def callback(flow):
        """Parse the flows and sort them by table"""
        table = flow.info.get("table") or 0
        if not tables.get(table):
            tables[table] = list()
        tables[table].append(flow)

    process_flows(
        flow_factory=create_ofp_flow,
        callback=callback,
        filename=opts.get("filename"),
        filter=opts.get("filter"),
    )

    html_obj = "<div id=flow_list>"
    for table, flows in tables.items():
        html_obj += "<h2 id=table_{table}> Table {table}</h2>".format(table=table)
        html_obj += "<ul id=table_{}_flow_list>".format(table)
        for flow in flows:
            html_obj += "<li id=flow_{}>".format(flow.id)
            highlighted = None
            if opts.get("highlight"):
                result = opts.get("highlight").evaluate(flow)
                if result:
                    highlighted = result.kv
            buf = HTMLBuffer()
            HTMLFormatter(opts).format_flow(buf, flow, highlighted)
            html_obj += buf.text
            html_obj += "</li>"
        html_obj += "</ul>"
    html_obj += "</div>"
    print(html_obj)


def create_ofp_flow(string, idx):
    """Create a OFPFlow"""
    if " reply " in string:
        return None
    return OFPFlow.from_string(string, idx)
