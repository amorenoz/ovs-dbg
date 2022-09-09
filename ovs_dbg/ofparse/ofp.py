import click
import os

from ovs.flow.ofp import OFPFlow
from ovs_dbg.ofparse.ofp_logic import LogicFlowProcessor, CookieProcessor
from ovs_dbg.ofparse.main import maincli
from ovs_dbg.ofparse.process import (
    FlowProcessor,
    JSONProcessor,
    ConsoleProcessor,
)
from ovs_dbg.ofparse.html import HTMLBuffer, HTMLFormatter, HTMLStyle


def create_ofp_flow(string, idx):
    if " reply " in string:
        return None
    return OFPFlow(string, idx)


@maincli.group(subcommand_metavar="FORMAT")
@click.pass_obj
def openflow(opts):
    """Process OpenFlow Flows"""
    pass


@openflow.command()
@click.pass_obj
def json(opts):
    """Print the flows in JSON format"""
    proc = JSONProcessor(opts, create_ofp_flow)
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
def console(opts, heat_map):
    """Print the flows in the console with some style"""
    proc = ConsoleProcessor(
        opts,
        create_ofp_flow,
        heat_map=["n_packets", "n_bytes"] if heat_map else [],
    )
    proc.process()
    proc.print()


def ovn_detrace_callback(ctx, param, value):
    """click callback to add detrace information to config object and
    set general ovn-detrace flag to True
    """
    ctx.obj[param.name] = value
    if value != param.default:
        ctx.obj["ovn_detrace_flag"] = True
    return value


@openflow.command()
@click.option(
    "-d",
    "--ovn-detrace",
    "ovn_detrace_flag",
    is_flag=True,
    show_default=True,
    help="Use ovn-detrace to extract cookie information (implies '-c')",
)
@click.option(
    "--ovn-detrace-path",
    default="/usr/bin",
    type=click.Path(),
    help="Use an alternative path to where ovn_detrace.py is located. "
    "Instead of using this option you can just set PYTHONPATH accordingly",
    show_default=True,
    callback=ovn_detrace_callback,
)
@click.option(
    "--ovnnb-db",
    default=os.getenv("OVN_NB_DB") or "unix:/var/run/ovn/ovnnb_db.sock",
    help="Specify the OVN NB database string (implies -d). "
    "If the OVN_NB_DB environment variable is set, it's used as default. "
    "Otherwise, the default is unix:/var/run/ovn/ovnnb_db.sock",
    callback=ovn_detrace_callback,
)
@click.option(
    "--ovnsb-db",
    default=os.getenv("OVN_SB_DB") or "unix:/var/run/ovn/ovnsb_db.sock",
    help="Specify the OVN NB database string (implies -d). "
    "If the OVN_NB_DB environment variable is set, it's used as default. "
    "Otherwise, the default is unix:/var/run/ovn/ovnnb_db.sock",
    callback=ovn_detrace_callback,
)
@click.option(
    "-o",
    "--ovn-filter",
    help="Specify a filter to be run on ovn-detrace information (implied -d). "
    "Format: python regular expression "
    "(see https://docs.python.org/3/library/re.html)",
    callback=ovn_detrace_callback,
)
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
def logic(
    opts,
    ovn_detrace_flag,
    ovn_detrace_path,
    ovnnb_db,
    ovnsb_db,
    ovn_filter,
    show_flows,
    cookie_flag,
    heat_map,
):
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
    if ovn_detrace_flag:
        opts["ovn_detrace_flag"] = True
    if opts.get("ovn_detrace_flag"):
        cookie_flag = True

    processor = LogicFlowProcessor(opts, create_ofp_flow, cookie_flag)
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
    processor = HTMLProcessor(opts, create_ofp_flow)
    processor.process()
    print(processor.html())


@openflow.command()
@click.option(
    "-d",
    "--ovn-detrace",
    "ovn_detrace_flag",
    is_flag=True,
    show_default=True,
    help="Use ovn-detrace to extract cookie information",
)
@click.option(
    "--ovn-detrace-path",
    default="/usr/bin",
    type=click.Path(),
    help="Use an alternative path to where ovn_detrace.py is located. "
    "Instead of using this option you can just set PYTHONPATH accordingly",
    show_default=True,
    callback=ovn_detrace_callback,
)
@click.option(
    "--ovnnb-db",
    default=os.getenv("OVN_NB_DB") or "unix:/var/run/ovn/ovnnb_db.sock",
    help="Specify the OVN NB database string (implies -d). "
    "If the OVN_NB_DB environment variable is set, it's used as default. "
    "Otherwise, the default is unix:/var/run/ovn/ovnnb_db.sock",
    callback=ovn_detrace_callback,
)
@click.option(
    "--ovnsb-db",
    default=os.getenv("OVN_SB_DB") or "unix:/var/run/ovn/ovnsb_db.sock",
    help="Specify the OVN NB database string (implies -d). "
    "If the OVN_NB_DB environment variable is set, it's used as default. "
    "Otherwise, the default is unix:/var/run/ovn/ovnnb_db.sock",
    callback=ovn_detrace_callback,
)
@click.option(
    "-o",
    "--ovn-filter",
    help="Specify a filter to be run on ovn-detrace information (implied -d). "
    "Format: python regular expression "
    "(see https://docs.python.org/3/library/re.html)",
    callback=ovn_detrace_callback,
)
@click.pass_obj
def cookie(
    opts, ovn_detrace_flag, ovn_detrace_path, ovnnb_db, ovnsb_db, ovn_filter
):
    """Print the flow tables sorted by cookie"""
    if ovn_detrace_flag:
        opts["ovn_detrace_flag"] = True

    processor = CookieProcessor(opts, create_ofp_flow)
    processor.process()
    processor.print()
