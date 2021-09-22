import click

from ovs_dbg.ofp import OFPFlowFactory
from ovs_dbg.ofparse.ofp_logic import LogicFlowProcessor, CookieProcessor
from ovs_dbg.ofparse.main import maincli
from ovs_dbg.ofparse.process import (
    FlowProcessor,
    JSONProcessor,
    ConsoleProcessor,
)
from ovs_dbg.ofparse.html import HTMLBuffer, HTMLFormatter, HTMLStyle

factory = OFPFlowFactory()


@maincli.group(subcommand_metavar="FORMAT")
@click.pass_obj
def openflow(opts):
    """Process OpenFlow Flows"""
    pass


@openflow.command()
@click.pass_obj
def json(opts):
    """Print the flows in JSON format"""
    proc = JSONProcessor(opts, factory)
    proc.process()
    print(proc.json_string())


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
    proc = ConsoleProcessor(
        opts, factory, heat_map=["n_packets", "n_bytes"] if heat_map else []
    )
    proc.process()
    proc.print()


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
    processor = LogicFlowProcessor(opts, factory, cookie_flag)
    processor.process()
    processor.print(show_flows, heat_map)


class HTMLProcessor(FlowProcessor):
    def __init__(self, opts, factory):
        super().__init__(opts, factory)
        self.data = dict()

    def start_file(self, name, filename):
        self.tables = dict()

    def stop_file(self, name, filename):
        self.data[name] = self.tables

    def process_flow(self, flow, name):
        table = flow.info.get("table") or 0
        if not self.tables.get(table):
            self.tables[table] = list()
        self.tables[table].append(flow)

    def html(self):
        html_obj = ""
        for name, tables in self.data.items():
            name = name.replace(" ", "_")
            html_obj += "<h1>{}</h1>".format(name)
            html_obj += "<div id=flow_list>"
            for table, flows in tables.items():
                formatter = HTMLFormatter(self.opts)

                def anchor(x):
                    return "#table_%s_%s" % (name, x.value["table"])

                formatter.style.set_value_style(
                    "resubmit",
                    HTMLStyle(
                        formatter.style.get("value.resubmit"),
                        anchor_gen=anchor,
                    ),
                )
                html_obj += (
                    "<h2 id=table_{name}_{table}> Table {table}</h2>".format(
                        name=name, table=table
                    )
                )
                html_obj += "<ul id=table_{}_flow_list>".format(table)
                for flow in flows:
                    html_obj += "<li id=flow_{}>".format(flow.id)
                    highlighted = None
                    if self.opts.get("highlight"):
                        result = self.opts.get("highlight").evaluate(flow)
                        if result:
                            highlighted = result.kv
                    buf = HTMLBuffer()
                    formatter.format_flow(buf, flow, highlighted)
                    html_obj += buf.text
                    html_obj += "</li>"
                html_obj += "</ul>"
            html_obj += "</div>"

        return html_obj


@openflow.command()
@click.pass_obj
def html(opts):
    """Print the flows in an HTML list"""
    processor = HTMLProcessor(opts, factory)
    processor.process()
    print(processor.html())


@openflow.command()
@click.pass_obj
def cookie(opts):
    """Print the flow tables sorted by cookie"""
    processor = CookieProcessor(opts, factory)
    processor.process()
    processor.print()
