import sys
import click
import colorsys
import graphviz

from rich.tree import Tree
from rich.text import Text
from rich.console import Console
from rich.style import Style
from rich.color import Color

from ovs_dbg.ofparse.main import maincli
from ovs_dbg.ofparse.process import process_flows, tojson, pprint
from ovs_dbg.ofparse.console import (
    ConsoleFormatter,
    ConsoleBuffer,
    print_context,
    hash_pallete,
)
from ovs_dbg.ofparse.html import HTMLBuffer, HTMLFormatter
from ovs_dbg.odp import ODPFlow
from ovs_dbg.filter import OFFilter


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
    console = Console(color_system=None if opts["no_color"] else "256")
    ofconsole = ConsoleFormatter(console)

    # HSV_tuples = [(x / size, 0.7, 0.8) for x in range(size)]
    recirc_style_gen = hash_pallete(
        hue=[x / 50 for x in range(0, 50)], saturation=[0.7], value=[0.8]
    )

    style = ConsoleFormatter.default_style_obj
    style.set_default_value_style(Style(color="bright_black"))
    style.set_key_style("output", Style(color="green"))
    style.set_value_style("output", Style(color="green"))
    style.set_value_style("recirc", recirc_style_gen)
    style.set_value_style("recirc_id", recirc_style_gen)

    def append_to_tree(parent, flow):
        buf = ConsoleBuffer(Text())
        ofconsole.format_flow(buf=buf, flow=flow, style=style)
        tree_elem = parent.add(buf.text)
        return tree_elem

    process_flow_tree(flow_list, tree, 0, append_to_tree)

    with print_context(console, opts["paged"], not opts["no_color"]):
        console.print(tree)


@datapath.command()
@click.pass_obj
def html(opts):
    """Print the flows in an HTML list sorted by recirc_id"""

    flow_list = []

    def callback(flow):
        flow_list.append(flow)

    process_flows(
        flow_factory=ODPFlow.from_string,
        callback=callback,
        filename=opts.get("filename"),
        filter=opts.get("filter"),
    )

    class HTMLFlowTree:
        def __init__(self, flow=None, style=None):
            self._flow = flow
            self._style = style
            self._subflows = list()

        def append(self, flow):
            self._subflows.append(flow)

        def render(self):
            html_obj = "<div>"
            if self._flow:
                html_obj += "<div id=flow_{}>".format(self._flow.id)
                buf = HTMLBuffer()
                HTMLFormatter().format_flow(buf, self._flow, self._style)
                html_obj += buf.text
                html_obj += "</div>"
            if len(self._subflows) > 1:
                html_obj += "<div>"
                html_obj += "<ul>"
                for sf in self._subflows:
                    html_obj += "<li>"
                    html_obj += sf.render()
                    html_obj += "</li>"
                html_obj += "</ul>"
                html_obj += "</div>"
            html_obj += "</div>"
            return html_obj

    def append_to_html(parent, flow):
        html_flow = HTMLFlowTree(flow)
        parent.append(html_flow)
        return html_flow

    root = HTMLFlowTree()
    process_flow_tree(flow_list, root, 0, append_to_html)

    html_obj = "<div id=flow_list>"
    html_obj += root.render()
    html_obj += "</div>"

    print(html_obj)


@datapath.command()
@click.pass_obj
def graph(opts):
    """Print the flows in an graphviz format showing the relationship of recirc_ids"""

    recirc_flows = {}

    def callback(flow):
        """Parse the flows and sort them by table"""
        rid = flow.match.get("recirc_id") or 0
        if not recirc_flows.get(rid):
            recirc_flows[rid] = list()
        recirc_flows[rid].append(flow)

    process_flows(
        flow_factory=ODPFlow.from_string,
        callback=callback,
        filename=opts.get("filename"),
        filter=opts.get("filter"),
    )

    node_styles = {
        OFFilter("ct and (ct_state or ct_label or ct_mark)"): {"color": "#ff00ff"},
        OFFilter("ct_state or ct_label or ct_mark"): {"color": "#0000ff"},
        OFFilter("ct"): {"color": "#ff0000"},
    }

    g = graphviz.Digraph("DP flows", node_attr={"shape": "rectangle"})
    g.attr(compound="true")
    g.attr(rankdir="TB")

    for recirc, flows in recirc_flows.items():
        with g.subgraph(
            name="cluster_{}".format(recirc), comment="recirc {}".format(recirc)
        ) as sg:

            sg.attr(rankdir="TB")
            sg.attr(ranksep="0.02")
            sg.attr(label="recirc_id {}".format(recirc))

            invis = "f{}".format(recirc)
            sg.node(invis, color="white", len="0", shape="point", width="0", height="0")

            previous = None
            for flow in flows:
                name = "Flow_{}".format(flow.id)
                summary = "Line: {} \n".format(flow.id)
                summary += "\n".join(
                    [
                        flow.ufid.get("ufid") if hasattr(flow, "ufid") else "",
                        flow.section("info").string,
                        ",".join(flow.match.keys()),
                        "actions: " + ",".join(list(a.keys())[0] for a in flow.actions),
                    ]
                )
                attr = (
                    node_styles.get(
                        next(filter(lambda f: f.evaluate(flow), node_styles), None)
                    )
                    or {}
                )

                sg.node(
                    name=name,
                    label=summary,
                    _attributes=attr,
                    fontsize="8",
                    nojustify="true",
                    URL="#flow_{}".format(flow.id),
                )

                if previous:
                    sg.edge(previous, name, color="white")
                else:
                    sg.edge(invis, name, color="white", length="0")
                previous = name

                next_recirc = next(
                    (kv.value for kv in flow.actions_kv if kv.key == "recirc"), None
                )
                if next_recirc:
                    cname = "cluster_{}".format(next_recirc)
                    g.edge(name, "f{}".format(next_recirc), lhead=cname)
                else:
                    g.edge(name, "end")

    g.edge("start", "f0", lhead="cluster_0")
    g.node("start", shape="Mdiamond")
    g.node("end", shape="Msquare")
    print(g.source)


def process_flow_tree(flow_list, parent, recirc_id, callback):
    """Process the datapath flows into a tree by "recirc_id" and sorted by "packets"
    Args:
        flow_list (list[odp.ODPFlow]): original list of flows
        parent (Any): current tree node that serves as parent
        recirc_id (int): recirc_id to traverse
        callback(callable): a callback that must accept the current parent and
            a flow and return an object that can potentially serve as parent for
            a nested call to callback

    This function is recursive
    """
    sorted_flows = sorted(
        filter(lambda f: f.match.get("recirc_id") == recirc_id, flow_list),
        key=lambda x: x.info.get("packets") or 0,
        reverse=True,
    )

    for flow in sorted_flows:
        next_recirc = next(
            (kv.value for kv in flow.actions_kv if kv.key == "recirc"), None
        )

        next_parent = callback(parent, flow)

        if next_recirc:
            process_flow_tree(flow_list, next_parent, next_recirc, callback)
