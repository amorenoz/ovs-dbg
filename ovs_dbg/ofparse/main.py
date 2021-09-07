import click
import sys
import configparser

from ovs_dbg.filter import OFFilter
from pkg_resources import resource_filename

_default_config_file = "ofparse.conf"
_default_config_path = resource_filename(__name__, _default_config_file)


class Options(dict):
    """Options dictionary"""

    pass


@click.group(
    subcommand_metavar="TYPE", context_settings=dict(help_option_names=["-h", "--help"])
)
@click.option(
    "-c",
    "--config",
    help="Use non-default config file",
    type=click.Path(),
)
@click.option(
    "--style",
    help="Select style (defined in config file)",
    default=None,
    show_default=True,
)
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
    help="Page the result (uses $PAGER). If colors are not disabled you might "
    'need to enable colors on your PAGER, eg: export PAGER="less -r".',
    is_flag=True,
    default=False,
    show_default=True,
)
@click.option(
    "-f",
    "--filter",
    help="Filter flows that match the filter expression. Run 'ofparse filter'"
    "for a detailed description of the filtering syntax",
    type=str,
    show_default=False,
)
@click.option(
    "-l",
    "--highlight",
    help="Highlight flows that match the filter expression. Run 'ofparse filter'"
    "for a detailed description of the filtering syntax",
    type=str,
    show_default=False,
)
@click.pass_context
def maincli(ctx, config, style, filename, paged, filter, highlight):
    """
    OpenFlow Parse utility.

    It parses openflow flows (such as the output of ovs-ofctl 'dump-flows') and
    prints them in different formats.

    """
    ctx.obj = Options()
    ctx.obj["filename"] = filename or ""
    ctx.obj["paged"] = paged
    if filter:
        try:
            ctx.obj["filter"] = OFFilter(filter)
        except Exception as e:
            raise click.BadParameter("Wrong filter syntax: {}".format(e))

    if highlight:
        try:
            ctx.obj["highlight"] = OFFilter(highlight)
        except Exception as e:
            raise click.BadParameter("Wrong filter syntax: {}".format(e))

    config_file = config or _default_config_path
    parser = configparser.ConfigParser()
    parser.read(config_file)

    ctx.obj["config"] = parser
    ctx.obj["style"] = style


@maincli.command(hidden=True)
@click.pass_context
def filter(ctx):
    """
    \b
    Filter Syntax
    *************

        [! | not ] {key}[[.subkey[.subkey]..] [= | > | < | ~=] {value})] [&& | || | or | and | not ] ...

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
        n_bytes>0 && drop=true"""
    click.echo(ctx.command.get_help(ctx))


def main():
    """
    Main Function
    """
    maincli()
