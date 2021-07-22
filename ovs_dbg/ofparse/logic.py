import click
import colorsys
from rich.tree import Tree
from rich.text import Text
from rich.console import Console
from rich.style import Style
from rich.color import Color

from .main import maincli, process_flows
from .console import OFConsole


class LFlow:
    """A Logical Flow represents the scheleton of a flow

    Attributes:
        cookie (int): The flow cookie
        priority (int): The flow priority
        action_keys (tuple): The action keys
        match_keys (tuple): The match keys
    """

    def __init__(self, flow):
        self.priority = flow.match.get("priority") or 0
        self.cookie = flow.info.get("cookie") or 0
        self.action_keys = tuple([kv.key for kv in flow.actions_kv])
        self.match_keys = tuple([kv.key for kv in flow.match_kv])

    def __eq__(self, other):
        return (
            self.cookie == other.cookie
            and self.priority == other.priority
            and self.action_keys == other.action_keys
            and self.match_keys == other.match_keys
        )

    def __hash__(self):
        return tuple(
            [self.cookie, self.priority, self.action_keys, self.match_keys]
        ).__hash__()


@maincli.command()
@click.option(
    "-s",
    "--show-flows",
    is_flag=True,
    default=False,
    show_default=True,
    help="Show the full flows under each logical flow",
)
@click.pass_obj
def logic(opts, show_flows):
    """
    Print the logical structure of the flows.

    First, sorts the flows based on tables and priorities.
    Then, deduplicates logically equivalent flows: these a flows that match
    on the same set of fields (regardless of the values they match against),
    have the same priority, cookie and actions (regardless of action arguments)

    Frisorting the flows based on tables and priority, deduplicates flows
    based on
    """
    console = OFConsole()

    tables = dict()

    # Generate a color pallete to display different cookies
    N = 200
    HSV_tuples = [(x * 1.0 / N, 0.5, 0.5) for x in range(N)]
    RGB_tuples = map(lambda x: colorsys.hsv_to_rgb(*x), HSV_tuples)
    cookie_styles = [
        Style(color=Color.from_rgb(r * 255, g * 255, b * 255)) for r, g, b in RGB_tuples
    ]

    def callback(flow):
        table = flow.info.get("table") or 0
        if not tables.get(table):
            tables[table] = dict()

        # Group flows by logical hash
        lflow = LFlow(flow)

        if not tables[table].get(lflow):
            tables[table][lflow] = list()

        tables[table][lflow].append(flow)

    process_flows(callback, opts.get("filename"))

    tree = Tree("Ofproto Flows (logical)")
    console = Console(color_system="256")

    for table_num in sorted(tables.keys()):
        table = tables[table_num]
        table_tree = tree.add("** TABLE {} **".format(table_num))

        for lflow in sorted(
            table.keys(),
            key=(lambda x: x.priority),
            reverse=True,
        ):
            flows = table[lflow]

            text = Text()

            text.append(
                "cookie={} ".format(hex(lflow.cookie)).ljust(18),
                style=cookie_styles[(lflow.cookie * 0x27D4EB2D) % len(cookie_styles)],
            )
            text.append("priority={} ".format(lflow.priority), style="steel_blue")
            text.append(",".join(lflow.match_keys), style="steel_blue")
            text.append("  --->  ", style="bold magenta")
            text.append(",".join(lflow.action_keys), style="steel_blue")
            text.append(" ( x {} )".format(len(flows)), style="dark_olive_green3")
            lflow_tree = table_tree.add(text)

            if show_flows:
                for flow in flows:
                    text = Text()
                    OFConsole(console).format_flow(flow, text=text)
                    lflow_tree.add(text)

    if opts.get("paged"):
        with console.pager(styles=(not opts["no_style"])):
            console.print(tree)
    else:
        console.print(tree)
