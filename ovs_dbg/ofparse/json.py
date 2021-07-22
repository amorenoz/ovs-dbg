import json
import click
import netaddr

from .main import maincli, process_flows
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

    process_flows(callback, opts.get("filename"))

    print(
        json.dumps(
            [
                {
                    "raw": flow.orig,
                    "info": flow.info,
                    "match": flow.match,
                    "actions": flow.actions,
                }
                for flow in flows
            ],
            indent=4,
            cls=FlowEncoder,
        )
    )
