import json
import click
import netaddr
from rich.console import Console

from .main import maincli, process_flows
from .console import print_context
from ovs_dbg.decoders import IPMask, EthMask


class FlowEncoder(json.JSONEncoder):
    def default(self, obj):
        if (
            isinstance(obj, IPMask)
            or isinstance(obj, EthMask)
            or isinstance(obj, netaddr.IPAddress)
        ):
            return str(obj)
        return json.JSONEncoder.default(self, obj)


@maincli.command("json")
@click.pass_obj
def tojson(opts):
    """
    Print the json representation of the flow list
    """
    flows = []

    def callback(flow):
        flows.append(flow)

    process_flows(callback, opts.get("filename"), opts.get("filter"))

    flow_json = json.dumps(
        [flow.dict() for flow in flows],
        indent=4,
        cls=FlowEncoder,
    )

    if opts["paged"]:
        console = Console()
        with print_context(console, opts["paged"], not opts["no_style"]):
            console.print(flow_json)
    else:
        print(flow_json)
