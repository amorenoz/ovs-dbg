from rich.tree import Tree
from rich.text import Text
from rich.console import Console

from ovs_dbg.ofparse.process import FlowProcessor
from ovs_dbg.ofparse.console import (
    ConsoleFormatter,
    ConsoleBuffer,
    hash_pallete,
    file_header,
    heat_pallete,
    print_context,
)

# Try to make it easy to spot same cookies by printing them in different
# colors
cookie_style_gen = hash_pallete(
    hue=[x / 10 for x in range(0, 10)],
    saturation=[0.5],
    value=[0.5 + x / 10 * (0.85 - 0.5) for x in range(0, 10)],
)


class LFlow:
    """A Logical Flow represents the scheleton of a flow

    Attributes:
        flow (OFPFlow): The flow
        match_action_keys(list): Optional; list of action keys that are
            mathched exactly (not just the key but the value also)
        match_cookie (bool): Optional; if cookies are part of the logical
            flow
    """

    def __init__(self, flow, match_action_keys=[], match_cookie=False):
        self.cookie = flow.info.get("cookie") or 0 if match_cookie else None
        self.priority = flow.match.get("priority") or 0
        self.match_keys = tuple([kv.key for kv in flow.match_kv])

        self.action_keys = tuple(
            [
                kv.key
                for kv in flow.actions_kv
                if kv.key not in match_action_keys
            ]
        )
        self.match_action_kvs = [
            kv for kv in flow.actions_kv if kv.key in match_action_keys
        ]

    def __eq__(self, other):
        return (
            (self.cookie == other.cookie if self.cookie else True)
            and self.priority == other.priority
            and self.action_keys == other.action_keys
            and self.equal_match_action_kvs(other)
            and self.match_keys == other.match_keys
        )

    def equal_match_action_kvs(self, other):
        """
        Compares the logical flow's match action key-values with the other's
        Args:
            other (LFlow): The other LFlow to compare against

        Returns true if both LFlow have the same action k-v
        """
        if len(other.match_action_kvs) != len(self.match_action_kvs):
            return False

        for kv in self.match_action_kvs:
            found = False
            for other_kv in other.match_action_kvs:
                if self.match_kv(kv, other_kv):
                    found = True
                    break
            if not found:
                return False
        return True

    def match_kv(self, one, other):
        """Compares a KeyValue
        Args:
            one, other (KeyValue): The objects to compare

        Returns true if both KeyValue objects have the same key and value
        """
        return one.key == other.key and one.value == other.value

    def __hash__(self):
        hash_data = [
            self.cookie,
            self.priority,
            self.action_keys,
            tuple((kv.key, str(kv.value)) for kv in self.match_action_kvs),
            self.match_keys,
        ]
        if self.cookie:
            hash_data.append(self.cookie)
        return tuple(hash_data).__hash__()

    def format(self, buf, formatter):
        """Format the Logical Flow into a Buffer"""
        if self.cookie:
            buf.append_extra(
                "cookie={} ".format(hex(self.cookie)).ljust(18),
                style=cookie_style_gen(str(self.cookie)),
            )

        buf.append_extra(
            "priority={} ".format(self.priority), style="steel_blue"
        )
        buf.append_extra(",".join(self.match_keys), style="steel_blue")
        buf.append_extra("  --->  ", style="bold magenta")
        buf.append_extra(",".join(self.action_keys), style="steel_blue")

        if len(self.match_action_kvs) > 0:
            buf.append_extra(" ", style=None)

        for kv in self.match_action_kvs:
            formatter.format_kv(buf, kv, formatter.style)
            buf.append_extra(",", style=None)


class LogicFlowProcessor(FlowProcessor):
    def __init__(self, opts, factory, match_cookie):
        super().__init__(opts, factory)
        self.data = dict()
        self.match_cookie = match_cookie

    def start_file(self, name, filename):
        self.tables = dict()

    def stop_file(self, name, filename):
        self.data[name] = self.tables

    def process_flow(self, flow, name):
        """Sort the flows by table and logical flow"""
        table = flow.info.get("table") or 0
        if not self.tables.get(table):
            self.tables[table] = dict()

        # Group flows by logical hash
        lflow = LFlow(
            flow,
            match_action_keys=["output", "resubmit", "drop"],
            match_cookie=self.match_cookie,
        )

        if not self.tables[table].get(lflow):
            self.tables[table][lflow] = list()

        self.tables[table][lflow].append(flow)

    def print(self, show_flows, heat_map):
        console = Console(
            color_system=None if self.opts["style"] is None else "256"
        )
        formatter = ConsoleFormatter(opts=self.opts, console=console)
        with print_context(console, self.opts):
            for name, tables in self.data.items():
                console.print("\n")
                console.print(file_header(name))
                tree = Tree("Ofproto Flows (logical)")

                for table_num in sorted(tables.keys()):
                    table = tables[table_num]
                    table_tree = tree.add("** TABLE {} **".format(table_num))

                    if heat_map:
                        for field in ["n_packets", "n_bytes"]:
                            values = []
                            for flow_list in table.values():
                                values.extend(
                                    [f.info.get(field) or 0 for f in flow_list]
                                )
                            formatter.style.set_value_style(
                                field, heat_pallete(min(values), max(values))
                            )

                    for lflow in sorted(
                        table.keys(),
                        key=(lambda x: x.priority),
                        reverse=True,
                    ):
                        flows = table[lflow]

                        buf = ConsoleBuffer(Text())

                        lflow.format(buf, formatter)
                        buf.append_extra(
                            " ( x {} )".format(len(flows)),
                            style="dark_olive_green3",
                        )
                        lflow_tree = table_tree.add(buf.text)

                        if show_flows:
                            for flow in flows:
                                buf = ConsoleBuffer(Text())
                                highlighted = None
                                if self.opts.get("highlight"):
                                    result = self.opts.get(
                                        "highlight"
                                    ).evaluate(flow)
                                    if result:
                                        highlighted = result.kv
                                formatter.format_flow(buf, flow, highlighted)
                                lflow_tree.add(buf.text)

                console.print(tree)
