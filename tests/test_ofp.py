import pytest

from ovs_dbg.ofp import OFPFlow
from ovs_dbg.kv import KeyValue


@pytest.mark.parametrize(
    "input_string,expected",
    [
        (
            "actions=local,3,4,5,output:foo",
            [
                KeyValue("output", {"port": "local"}),
                KeyValue("output", {"port": 3}),
                KeyValue("output", {"port": 4}),
                KeyValue("output", {"port": 5}),
                KeyValue("output", {"port": "foo"}),
            ],
        ),
    ],
)
def test_act(input_string, expected):
    ofp = OFPFlow.from_string(input_string)
    actions = ofp.actions_kv
    for i in range(len(expected)):
        assert expected[i].key == actions[i].key
        assert expected[i].value == actions[i].value

        # Assert positions relative to action string are OK
        apos = ofp.meta.apos
        astring = ofp.meta.astring

        kpos = actions[i].meta.kpos
        kstr = actions[i].meta.kstring
        vpos = actions[i].meta.vpos
        vstr = actions[i].meta.vstring
        assert astring[kpos: kpos + len(kstr)] == kstr
        if vpos != -1:
            assert astring[vpos: vpos + len(vstr)] == vstr

        # assert astring meta is correct
        assert input_string[apos: apos + len(astring)] == astring
