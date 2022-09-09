import pytest

from ovs_dbg.ofparse.dp_tree import FlowTree
from ovs.flow.odp import ODPFlow


def test_odp_tree_nested():
    dump = """recirc_id(0x1) actions:drop
    recirc_id(0x2) actions:2
    recirc_id(0x3) actions:3
    recirc_id(0x4) actions:4
    recirc_id(0x5) actions:5
    recirc_id(0x6) actions:6
    recirc_id(0x0) actions:clone(recirc(0x2)),check_pkt_len(size=200,gt(recirc(0x1)),le(recirc(0x3))),recirc(0x4),sample(sample=15%,actions(clone(recirc(0x5)),recirc(0x6)),recirc(0x6)))"""
    flows = []
    for line in dump.splitlines():
        flows.append(ODPFlow(line))

    ft = FlowTree(flows)
    ft.build()

    # Helper function to check that all flows are nested under the last one.
    nested = 0

    def check(elem, parent):
        nonlocal nested
        if elem.is_root or parent.is_root:
            return
        print("{} -> {}".format(elem.flow, parent.flow))
        if elem.flow.match.get("recirc_id") != 0:
            assert parent.flow == flows[-1]
            print(elem.flow)
            nested = nested + 1

    ft.traverse(check)
    assert nested == 6
