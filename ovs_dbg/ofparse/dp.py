import sys
import click
import colorsys
import graphviz
import itertools

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
from ovs_dbg.ofparse.format import FlowStyle
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
    ofconsole = ConsoleFormatter(opts)
    console = ofconsole.console

    # HSV_tuples = [(x / size, 0.7, 0.8) for x in range(size)]
    recirc_style_gen = hash_pallete(
        hue=[x / 50 for x in range(0, 50)], saturation=[0.7], value=[0.8]
    )

    style = ofconsole.style
    style.set_default_value_style(Style(color="bright_black"))
    style.set_key_style("output", Style(color="green"))
    style.set_value_style("output", Style(color="green"))
    style.set_value_style("recirc", recirc_style_gen)
    style.set_value_style("recirc_id", recirc_style_gen)

    def append_to_tree(parent, flow):
        buf = ConsoleBuffer(Text())
        highlighted = None
        if opts.get("highlight"):
            result = opts.get("highlight").evaluate(flow)
            if result:
                highlighted = result.kv
        ofconsole.format_flow(buf, flow, highlighted)
        tree_elem = parent.add(buf.text)
        return tree_elem

    process_flow_tree(flow_list, tree, 0, append_to_tree)

    with print_context(console, opts):
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

    html_obj = get_html_obj(flow_list, opts)

    print(html_obj)


@datapath.command()
@click.option(
    "-h",
    "--html",
    is_flag=True,
    default=False,
    show_default=True,
    help="Output an html file containing the graph",
)
@click.pass_obj
def graph(opts, html):
    """Print the flows in an graphviz (.dot) format showing the relationship of recirc_ids"""

    recirc_flows = {}

    def callback(flow):
        """Parse the flows and sort them by table"""
        rid = hex(flow.match.get("recirc_id") or 0)
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
                    cname = "cluster_{}".format(hex(next_recirc))
                    g.edge(name, "f{}".format(hex(next_recirc)), lhead=cname)
                else:
                    g.edge(name, "end")

    g.edge("start", "f0x0", lhead="cluster_0x0")
    g.node("start", shape="Mdiamond")
    g.node("end", shape="Msquare")

    if not html:
        print(g.source)
        return

    html_obj = ""
    html_obj += "<h1> Flow Graph </h1>"
    html_obj += "<div width=400px height=300px>"
    svg = g.pipe(format="svg")
    html_obj += svg.decode("utf-8")
    html_obj += "</div>"

    html_obj += get_html_obj(list(itertools.chain(*recirc_flows.values())), opts)
    print(html_obj)


class HTMLFlowTree:
    def __init__(self, flow=None, opts=None):
        self._flow = flow
        self._formatter = HTMLFormatter(opts)
        self._subflows = list()
        self._opts = opts

    def append(self, flow):
        self._subflows.append(flow)

    def render(self, item=0):
        html_obj = "<div>"
        if self._flow:
            html_obj += """
        <input id="collapsible_{item}" class="toggle" type="checkbox" onclick="toggle_checkbox(this)" checked>
        <label for="collapsible_{item}" class="lbl-toggle lbl-toggle-flow">Flow {id}</label>
        """.format(
                item=item, id=self._flow.id
            )
            html_obj += '<div class="flow collapsible-content" id="flow_{id}" onfocus="onFlowClick(this)" onclick="onFlowClick(this)" >'.format(
                id=self._flow.id
            )
            buf = HTMLBuffer()
            highlighted = None
            if self._opts.get("highlight"):
                result = self._opts.get("highlight").evaluate(self._flow)
                if result:
                    highlighted = result.kv
            self._formatter.format_flow(buf, self._flow, highlighted)
            html_obj += buf.text
            html_obj += "</div>"
        if self._subflows:
            html_obj += "<div>"
            html_obj += "<ul  style='list-style-type:none;'>"
            for sf in self._subflows:
                item += 1
                html_obj += "<li>"
                (html_elem, items) = sf.render(item)
                html_obj += html_elem
                item += items
                html_obj += "</li>"
            html_obj += "</ul>"
            html_obj += "</div>"
        html_obj += "</div>"
        return html_obj, item


def get_html_obj(flow_list, opts=None):
    def append_to_html(parent, flow):
        html_flow = HTMLFlowTree(flow, opts)
        parent.append(html_flow)
        return html_flow

    root = HTMLFlowTree(flow=None, opts=opts)
    process_flow_tree(flow_list, root, 0, append_to_html)

    html_obj = """
    <style>
    .flow{
        background-color:white;
        display: inline-block;
        text-align: left;
        font-family: monospace;
    }
    .active{
        border: 2px solid #0008ff;
    }
    input[type='checkbox'] { display: none; }
    .wrap-collabsible {
        margin: 1.2rem 0;
    }
    .lbl-toggle-main {
        font-weight: bold;
        font-family: monospace;
        font-size: 1.5rem;
        text-transform: uppercase;
        text-align: center;
        padding: 1rem;
        #cursor: pointer;
        border-radius: 7px;
        transition: all 0.25s ease-out;
    }
    .lbl-toggle-flow {
        font-family: monospace;
        font-size: 1.0rem;
        text-transform: uppercase;
        text-align: center;
        padding: 1rem;
        #cursor: pointer;
        border-radius: 7px;
        transition: all 0.25s ease-out;
    }
    .lbl-toggle:hover {
        color: #0008ff;
    }
    .lbl-toggle::before {
        content: ' ';
        display: inline-block;
        border-top: 5px solid transparent;
        border-bottom: 5px solid transparent;
        border-left: 5px solid currentColor;
        vertical-align: middle;
        margin-right: .7rem;
        transform: translateY(-2px);
        transition: transform .2s ease-out;
    }
    .toggle:checked+.lbl-toggle::before {
        transform: rotate(90deg) translateX(-3px);
    }
    .collapsible-content {
        max-height: 0px;
        overflow: hidden;
        transition: max-height .25s ease-in-out;
    }
    .toggle:checked + .lbl-toggle + .collapsible-content {
        max-height: 350px;
    }
    .toggle:checked+.lbl-toggle {
        border-bottom-right-radius: 0;
        border-bottom-left-radius: 0;
    }
    .collapsible-content .content-inner {
        background: rgba(0, 105, 255, .2);
        border-bottom: 1px solid rgba(0, 105, 255, .45);
        border-bottom-left-radius: 7px;
        border-bottom-right-radius: 7px;
        padding: .5rem 1rem;
    }
    .collapsible-content p {
        margin-bottom: 0;
    }
    </style>

    <script>
      function onFlowClick(elem) {
          var flows = document.getElementsByClassName("flow");
          for (i = 0; i < flows.length; i++) {
              flows[i].classList.remove('active')
          }
          elem.classList.add("active");
          var my_toggle = document.getElementsByClassName("flow");
          toggleAll(elem, true);
      }
      function locationHashChanged() {
          var elem = document.getElementById(location.hash.substring(1));
          console.log(elem)
          if (elem) {
            if (elem.classList.contains("flow")) {
                onFlowClick(elem);
            }
          }
      }
      function toggle_checkbox(elem) {
         if (elem.checked == true) {
            toggleAll(elem, true)
         } else {
            toggleAll(elem, false)
         }
      }
      function toggleAll(elem, value) {
          var subs = elem.parentElement.querySelectorAll(".toggle:not([id=" + CSS.escape(elem.id) + "])");
          console.log(subs);
          console.log(value);
          for (i = 0; i < subs.length; ++i) {
              subs[i].checked = value;
          }
      }
      window.onhashchange = locationHashChanged;
    </script>
    """
    html_obj += """
        <input id="collapsible_main" class="toggle" type="checkbox" onclick="toggle_checkbox(this)" checked>
        <label for="collapsible_main" class="lbl-toggle lbl-toggle-main">Flow Table</label>
        """
    html_obj += "<div id=flow_list>"
    (html_elem, items) = root.render()
    html_obj += html_elem
    html_obj += "</div>"
    return html_obj


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
