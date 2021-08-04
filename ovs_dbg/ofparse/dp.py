import sys
import click
import colorsys
from rich.tree import Tree
from rich.text import Text
from rich.console import Console
from rich.style import Style
from rich.color import Color

from ovs_dbg.ofparse.main import maincli
from ovs_dbg.ofparse.process import process_flows, tojson, pprint
from .console import OFConsole, print_context
from ovs_dbg.odp import ODPFlow


@maincli.group(subcommand_metavar="FORMAT")
@click.pass_obj
def datapath(opts):
    """Process DPIF Flows"""
    pass


@datapath.command()
@click.pass_obj
def json(opts):
    """Print the flows in JSON format"""
    return tojson(flow_factory=ODPFlow.from_string, opts=opts)


@datapath.command()
@click.pass_obj
def pretty(opts):
    """Print the flows with some style"""
    return pprint(flow_factory=ODPFlow.from_string, opts=opts)


@datapath.command()
@click.pass_obj
def logic(opts):
    """Print the flows in a tree based on the 'recirc_id'"""

    flow_list = []

    def callback(flow):
        flow_list.append(flow)

    process_flows(
        flow_factory=ODPFlow.from_string,
        callback=callback,
        filename=opts.get("filename"),
        filter=opts.get("filter"),
    )

    tree = Tree("Datapath Flows (logical)")
    console = Console(color_system="256")
    ofconsole = OFConsole(console)

    recirc_styles = [
        Style(color=Color.from_rgb(r * 255, g * 255, b * 255))
        for r, g, b in create_color_pallete(50)
    ]

    def process_flow_tree(parent, recirc_id):
        sorted_flows = sorted(
            filter(lambda f: f.match.get("recirc_id") == recirc_id, flow_list),
            key=lambda x: x.info.get("packets") or 0,
            reverse=True,
        )

        style = OFConsole.default_style
        style["value"] = Style(color="bright_black")
        style["key.output"] = Style(color="green")
        style["value.output"] = Style(color="green")
        for flow in sorted_flows:
            next_recirc = next(
                (kv.value for kv in flow.actions_kv if kv.key == "recirc"), None
            )
            if next_recirc:
                style["value.recirc"] = recirc_styles[next_recirc % len(recirc_styles)]

            text = Text()
            style["value.recirc_id"] = recirc_styles[
                (flow.match.get("recirc_id")) % len(recirc_styles)
            ]
            ofconsole.format_flow(flow=flow, style=style, text=text)
            tree_elem = parent.add(text)

            if next_recirc:
                process_flow_tree(tree_elem, next_recirc)

    process_flow_tree(tree, 0)

    with print_context(console, opts["paged"], not opts["no_style"]):
        console.print(tree)


def create_color_pallete(size):
    """Create a color pallete of size colors by modifying the Hue in the HSV
    color space
    """
    HSV_tuples = [(x / size, 0.7, 0.8) for x in range(size)]
    return map(lambda x: colorsys.hsv_to_rgb(*x), HSV_tuples)
