import click
import sys

from ovs_dbg.ofp import OFPFlow
from ovs_dbg.ofparse.filter import OFFilter


class Options(dict):
    """Options dictionary"""

    pass


def process_flows(callback, filename="", filter=None):
    """Process flows from file or stdin"""
    if filename:
        with open(filename) as f:
            for line in f:
                flow = OFPFlow.from_string(line)
                if filter and not filter.evaluate(flow):
                    continue
                callback(flow)
    else:
        data = sys.stdin.read()
        for line in data.split("\n"):
            line = line.strip()
            if line:
                flow = OFPFlow.from_string(line.strip())
                if filter and not filter.evaluate(flow):
                    continue
                callback(flow)


@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
@click.option(
    "-i",
    "-input",
    "filename",
    help="Read flows from specified filepath. If not provided, flows will be"
    " read from stdin",
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
    help="Do not styles (colors)",
    is_flag=True,
    default=False,
    show_default=True,
)
@click.option(
    "-f",
    "--filter",
    help="Filter flows that match the filter expression. See main help for a "
    " detailed Filtering Syntax",
    type=str,
    show_default=False,
)
@click.pass_context
def maincli(ctx, filename, paged, no_style, filter):
    """
    OpenFlow Parse utility.

    It parses openflow flows (such as the output of ovs-ofctl 'dump-flows') and
    prints them in different formats.

    \b
    Filter Syntax
    *************

        [! | not ] {key}[[.subkey[.subkey]..] [= | > | < | ~=] {value})] [&& | || | | or | and | not ] ...

    \b
    Comparison operators are:
        =   equality
        <   less than
        >   more than
        ~=  masking (valid for IP and Ethernet fields)

    \b
    Logical operators are:
        !{expr}:  NOT
        {expr} && {expr}: AND
        {expr} || {expr}: OR

    \b
    Matches and flow metadata:
        To compare against a match or info field, use the field directly, e.g:
            priority=100
            n_bytes>10
        Use simple keywords for flags:
            tcp and ip_src=192.168.1.1
    \b
    Actions:
        Actions values might be dictionaries, use subkeys to access individual
        values, e.g:
            output.port=3
        Use simple keywords for flags
            drop

    \b
    Examples of valid filters.
        nw_addr~=192.168.1.1 && (tcp_dst=80 || tcp_dst=443)
        arp=true && !arp_tsa=192.168.1.1
        n_bytes>0 && drop=true
    """
    ctx.obj = Options()
    ctx.obj["filename"] = filename or ""
    ctx.obj["paged"] = paged
    ctx.obj["no_style"] = no_style
    if filter:
        try:
            ctx.obj["filter"] = OFFilter(filter)
        except Exception as e:
            raise click.BadParameter("Wrong filter syntax: {}".format(e))


def main():
    """
    Main Function
    """
    maincli()
