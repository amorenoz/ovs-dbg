import sys
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
    print_context,
)
from ovs_dbg.ofparse.html import HTMLBuffer, HTMLFormatter


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
@click.pass_obj
def pretty(opts):
    """Print the flows with some style"""
    return pprint(flow_factory=create_ofp_flow, opts=opts)


@openflow.command()
@click.option(
    "-s",
    "--show-flows",
    is_flag=True,
    default=False,
    show_default=True,
    help="Show the full flows under each logical flow",
)
@click.pass_obj
def logic(opts, show_flows):
    """
    Print the logical structure of the flows.

    First, sorts the flows based on tables and priorities.
    Then, deduplicates logically equivalent flows: these a flows that match
    on the same set of fields (regardless of the values they match against),
    have the same priority, cookie and actions (regardless of action arguments)

    Frisorting the flows based on tables and priority, deduplicates flows
    based on
    """
    tables = dict()

    class LFlow:
        """A Logical Flow represents the scheleton of a flow

        Attributes:
            cookie (int): The flow cookie
            priority (int): The flow priority
            action_keys (tuple): The action keys
            match_keys (tuple): The match keys
        """

        def __init__(self, flow):
            self.priority = flow.match.get("priority") or 0
            self.cookie = flow.info.get("cookie") or 0
            self.action_keys = tuple([kv.key for kv in flow.actions_kv])
            self.match_keys = tuple([kv.key for kv in flow.match_kv])

        def __eq__(self, other):
            return (
                self.cookie == other.cookie
                and self.priority == other.priority
                and self.action_keys == other.action_keys
                and self.match_keys == other.match_keys
            )

        def __hash__(self):
            return tuple(
                [self.cookie, self.priority, self.action_keys, self.match_keys]
            ).__hash__()

    def callback(flow):
        """Parse the flows and sort them by table and logical flow"""
        table = flow.info.get("table") or 0
        if not tables.get(table):
            tables[table] = dict()

        # Group flows by logical hash
        lflow = LFlow(flow)

        if not tables[table].get(lflow):
            tables[table][lflow] = list()

        tables[table][lflow].append(flow)

    process_flows(
        flow_factory=create_ofp_flow,
        callback=callback,
        filename=opts.get("filename"),
        filter=opts.get("filter"),
    )

    # Try to make it easy to spot same cookies by printing them in different
    # colors
    cookie_style_gen = hash_pallete(
        hue=[x / 10 for x in range(0, 10)],
        saturation=[0.5],
        value=[0.5 + x / 10 * (0.85 - 0.5) for x in range(0, 10)],
    )

    tree = Tree("Ofproto Flows (logical)")
    console = Console(color_system=None if opts["style"] is None else "256")

    for table_num in sorted(tables.keys()):
        table = tables[table_num]
        table_tree = tree.add("** TABLE {} **".format(table_num))

        for lflow in sorted(
            table.keys(),
            key=(lambda x: x.priority),
            reverse=True,
        ):
            flows = table[lflow]

            buf = ConsoleBuffer(Text())

            buf.append_extra(
                "cookie={} ".format(hex(lflow.cookie)).ljust(18),
                style=cookie_style_gen(str(lflow.cookie)),
            )
            buf.append_extra("priority={} ".format(lflow.priority), style="steel_blue")
            buf.append_extra(",".join(lflow.match_keys), style="steel_blue")
            buf.append_extra("  --->  ", style="bold magenta")
            buf.append_extra(",".join(lflow.action_keys), style="steel_blue")
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
                    ConsoleFormatter(console, opts).format_flow(buf, flow, highlighted)
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
