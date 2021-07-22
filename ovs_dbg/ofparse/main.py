import click
import sys

from ovs_dbg.ofp import OFPFlow


class Options(dict):
    pass


def process_flows(callback, filename=""):
    if filename:
        with open(filename) as f:
            for line in f:
                flow = OFPFlow.from_string(line)
                callback(flow)
    else:
        data = sys.stdin.read()
        for line in data.split("\n"):
            line = line.strip()
            if line:
                flow = OFPFlow.from_string(line.strip())
                callback(flow)


@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
@click.option(
    "-f",
    "-file",
    "filename",
    help="Read flows from specified filepath",
    type=click.Path(),
)
@click.option(
    "-p",
    "--paged",
    help="Page the result (uses $PAGER). If styling is not disabled you might "
    'need to enable colors on your $PAGER, eg: export PAGER="less -r".',
    is_flag=True,
    default=False,
    show_default=True,
)
@click.option(
    "--no-style",
    help="Page the result (uses $PAGER)",
    is_flag=True,
    default=False,
    show_default=True,
)
@click.pass_context
def maincli(ctx, filename, paged, no_style):
    """
    OpenFlow Parse utility.

    It parses openflow flows (such as the output of ovs-ofctl 'dump-flows') and
    prints them in different formats
    """
    ctx.obj = Options()
    ctx.obj["filename"] = filename or ""
    ctx.obj["paged"] = paged
    ctx.obj["no_style"] = no_style


def main():
    """
    Main Function
    """
    maincli()
