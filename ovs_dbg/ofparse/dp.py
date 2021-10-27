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
    heat_pallete,
)
from ovs_dbg.ofparse.format import FlowStyle
from ovs_dbg.ofparse.html import HTMLBuffer, HTMLFormatter
from ovs_dbg.ofparse.dp_graph import DatapathGraph
from ovs_dbg.ofparse.dp_tree import FlowTree, FlowElem
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
        flow_factory=ODPFlow.from_string,
        callback=callback,
        filename=opts.get("filename"),
        filter=opts.get("filter"),
    )

    console = ConsoleFormatter(opts)
    if heat_map and len(flows) > 0:
        for field in ["packets", "bytes"]:
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


@datapath.command()
@click.option(
    "-h",
    "--heat-map",
    is_flag=True,
    default=False,
    show_default=True,
    help="Create heat-map with packet and byte counters",
)
@click.pass_obj
def logic(opts, heat_map):
    """Print the flows in a tree based on the 'recirc_id'"""
    ofconsole = ConsoleFormatter(opts)

    # Generate a color pallete for cookies
    recirc_style_gen = hash_pallete(
        hue=[x / 50 for x in range(0, 50)], saturation=[0.7], value=[0.8]
    )

    style = ofconsole.style
    style.set_default_value_style(Style(color="bright_black"))
    style.set_key_style("output", Style(color="green"))
    style.set_value_style("output", Style(color="green"))
    style.set_value_style("recirc", recirc_style_gen)
    style.set_value_style("recirc_id", recirc_style_gen)

    console_tree = ConsoleTree(ofconsole, opts)

    process_flows(
        flow_factory=ODPFlow.from_string,
        callback=console_tree.add,
        filename=opts.get("filename"),
    )

    console_tree.build()
    if opts.get("filter"):
        console_tree.filter(opts.get("filter"))
    console_tree.print(heat_map)


@datapath.command()
@click.pass_obj
def html(opts):
    """Print the flows in an HTML list sorted by recirc_id"""

    html_tree = HTMLTree(opts)

    process_flows(
        flow_factory=ODPFlow.from_string,
        callback=html_tree.add,
        filename=opts.get("filename"),
    )

    html_tree.build()
    if opts.get("filter"):
        html_tree.filter(opts.get("filter"))
    print(html_tree.render())


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

    dpg = DatapathGraph(recirc_flows)

    if not html:
        print(dpg.source())
        return

    html_obj = ""
    html_obj += "<h1> Flow Graph </h1>"
    html_obj += "<div width=400px height=300px>"
    svg = dpg.pipe(format="svg")
    html_obj += svg.decode("utf-8")
    html_obj += "</div>"

    html_tree = HTMLTree(opts, recirc_flows)
    html_obj += html_tree.render()

    print(html_obj)


class ConsoleTree(FlowTree):
    """ConsoleTree is a FlowTree that prints the tree in a console

    Args:
        console (ConsoleFormatter): console to use for printing
        opts (dict): Options dictionary
    """

    class ConsoleElem(FlowElem):
        def __init__(self, flow=None, is_root=False):
            self.tree = None
            super(ConsoleTree.ConsoleElem, self).__init__(flow, is_root=is_root)

    def __init__(self, console, opts):
        self.console = console
        self.root = self.ConsoleElem(is_root=True)
        self.opts = opts
        super(ConsoleTree, self).__init__()

    def _new_elem(self, flow, _):
        """Override _new_elem to provide ConsoleElems"""
        return self.ConsoleElem(flow)

    def _append_to_tree(self, elem, parent):
        """Callback to be used for FlowTree._build
        Appends the flow to the rich.Tree
        """
        if elem.is_root:
            elem.tree = Tree("Datapath Flows (logical)")
            return

        buf = ConsoleBuffer(Text())
        highlighted = None
        if self.opts.get("highlight"):
            result = self.opts.get("highlight").evaluate(elem.flow)
            if result:
                highlighted = result.kv
        self.console.format_flow(buf, elem.flow, highlighted)
        elem.tree = parent.tree.add(buf.text)

    def print(self, heat=False):
        """Print the Flow Tree
        Args:
            heat (bool): Optional; whether heat-map style shall be applied
        """
        if heat:
            for field in ["packets", "bytes"]:
                values = []
                for flow_list in self._flows.values():
                    values.extend([f.info.get(field) or 0 for f in flow_list])
                self.console.style.set_value_style(
                    field, heat_pallete(min(values), max(values))
                )
        self.traverse(self._append_to_tree)
        with print_context(self.console.console, self.opts):
            self.console.console.print(self.root.tree)


class HTMLTree(FlowTree):
    """HTMLTree is a Flowtree that prints the tree in html format

    Args:
        opts(dict): Options dictionary
        flows(dict[int, list[DPFlow]): Optional; initial flows
    """

    html_header = """
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

    class HTMLTreeElem(FlowElem):
        """An element within the HTML Tree,
        It is composed of a flow and its subflows that can be added by calling
        append()
        """

        def __init__(self, flow=None, opts=None):
            self._formatter = HTMLFormatter(opts)
            self._opts = opts
            super(HTMLTree.HTMLTreeElem, self).__init__(flow)

        def render(self, item=0):
            """Render the HTML Element
            Args:
                item (int): the item id

            Returns:
                (html_obj, items) tuple where html_obj is the html string and
                items is the number of subitems rendered in total
            """
            html_obj = "<div>"
            if self.flow:
                html_obj += """
            <input id="collapsible_{item}" class="toggle" type="checkbox" onclick="toggle_checkbox(this)" checked>
            <label for="collapsible_{item}" class="lbl-toggle lbl-toggle-flow">Flow {id}</label>
            """.format(
                    item=item, id=self.flow.id
                )
                html_obj += '<div class="flow collapsible-content" id="flow_{id}" onfocus="onFlowClick(this)" onclick="onFlowClick(this)" >'.format(
                    id=self.flow.id
                )
                buf = HTMLBuffer()
                highlighted = None
                if self._opts.get("highlight"):
                    result = self._opts.get("highlight").evaluate(self.flow)
                    if result:
                        highlighted = result.kv
                self._formatter.format_flow(buf, self.flow, highlighted)
                html_obj += buf.text
                html_obj += "</div>"
            if self.children:
                html_obj += "<div>"
                html_obj += "<ul  style='list-style-type:none;'>"
                for sf in self.children:
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

    def __init__(self, opts, flows=None):
        self.opts = opts
        self.root = self.HTMLTreeElem(flow=None, opts=self.opts)
        super(HTMLTree, self).__init__(flows)

    def _new_elem(self, flow, _):
        """Override _new_elem to provide HTMLTreeElems"""
        return self.HTMLTreeElem(flow, self.opts)

    def render(self):
        """Render the Tree in HTML
        Returns:
            an html string representing the element
        """
        html_obj = (
            self.html_header
            + """
        <input id="collapsible_main" class="toggle" type="checkbox" onclick="toggle_checkbox(this)" checked>
        <label for="collapsible_main" class="lbl-toggle lbl-toggle-main">Flow Table</label>
        """
        )

        html_obj += "<div id=flow_list>"
        (html_elem, items) = self.root.render()
        html_obj += html_elem
        html_obj += "</div>"
        return html_obj
