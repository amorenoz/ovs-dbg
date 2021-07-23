import click

from .main import maincli, process_flows
from .console import OFConsole, print_context


@maincli.command()
@click.pass_obj
def pprint(opts):
    """
    Pretty print the flows
    """
    console = OFConsole(no_color=opts["no_style"])

    def callback(flow):
        console.print_flow(flow)

    with print_context(console.console, opts["paged"], not opts["no_style"]):
        process_flows(callback, opts.get("filename"))
