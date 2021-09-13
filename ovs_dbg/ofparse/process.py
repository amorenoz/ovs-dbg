""" Defines common flow processing functionality
"""
import sys
import json
import rich

from ovs_dbg.ofp import OFPFlow
from ovs_dbg.decoders import FlowEncoder
from ovs_dbg.ofparse.console import ConsoleFormatter, print_context


def process_flows(flow_factory, callback, filename="", filter=None):
    """Process flows from file or stdin

    Args:
        flow_factory(Callable): function to call to create a flow
        callback (Callable): function to call with each processed flow
        filename (str): Optional; filename to read frows from
        filter (OFFilter): Optional; filter to use to filter flows
    """
    idx = 0
    if filename:
        with open(filename) as f:
            for line in f:
                flow = flow_factory(line, idx)
                idx += 1
                if not flow or (filter and not filter.evaluate(flow)):
                    continue
                callback(flow)
    else:
        data = sys.stdin.read()
        for line in data.split("\n"):
            line = line.strip()
            if line:
                flow = flow_factory(line, idx)
                idx += 1
                if not flow or (filter and not filter.evaluate(flow)):
                    continue
                callback(flow)


def tojson(flow_factory, opts):
    """
    Print the json representation of the flow list

    Args:
        flow_factory (Callable): Function to call to create the flows
        opts (dict): Options
    """
    flows = []

    def callback(flow):
        flows.append(flow)

    process_flows(flow_factory, callback, opts.get("filename"), opts.get("filter"))

    flow_json = json.dumps(
        [flow.dict() for flow in flows],
        indent=4,
        cls=FlowEncoder,
    )

    if opts["paged"]:
        console = rich.Console()
        with print_context(console, opts):
            console.print(flow_json)
    else:
        print(flow_json)


def pprint(flow_factory, opts):
    """
    Pretty print the flows

    Args:
        flow_factory (Callable): Function to call to create the flows
        opts (dict): Options
    """
    console = ConsoleFormatter(opts)

    def callback(flow):
        high = None
        if opts.get("highlight"):
            result = opts.get("highlight").evaluate(flow)
            if result:
                high = result.kv
        console.print_flow(flow, high)

    with print_context(console.console, opts):
        process_flows(flow_factory, callback, opts.get("filename"), opts.get("filter"))
