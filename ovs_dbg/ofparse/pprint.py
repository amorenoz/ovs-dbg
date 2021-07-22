import click

from .main import maincli, process_flows
from .console import OFConsole


@maincli.command()
@click.pass_obj
def pprint(opts):
    """
    Pretty print the flows
    """
    console = OFConsole(no_color=opts["no_style"])

    def callback(flow):
        console.print_flow(flow)

    if opts["paged"]:
        with console.console.pager(styles=(not opts["no_style"])):
            process_flows(callback, opts.get("filename"))
    else:
        process_flows(callback, opts.get("filename"))
