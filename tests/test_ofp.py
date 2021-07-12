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
        (
            "actions=controller,controller:200",
            [
                KeyValue("output", "controller"),
                KeyValue("controller", {"max_len": 200}),
            ],
        ),
        (
            "actions=enqueue(foo,42),enqueue:foo:42,enqueue(bar,4242)",
            [
                KeyValue("enqueue", {"port": "foo", "queue": 42}),
                KeyValue("enqueue", {"port": "foo", "queue": 42}),
                KeyValue("enqueue", {"port": "bar", "queue": 4242}),
            ],
        ),
        (
            "actions=bundle(eth_src,0,hrw,ofport,members:4,8)",
            [
                KeyValue(
                    "bundle",
                    {
                        "fields": "eth_src",
                        "basis": 0,
                        "algorithm": "hrw",
                        "members": [4, 8],
                    },
                ),
            ],
        ),
        (
            "actions=bundle_load(eth_src,0,hrw,ofport,reg0,members:4,8)",
            [
                KeyValue(
                    "bundle_load",
                    {
                        "fields": "eth_src",
                        "basis": 0,
                        "algorithm": "hrw",
                        "dst": "reg0",
                        "members": [4, 8],
                    },
                ),
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
        assert astring[kpos : kpos + len(kstr)] == kstr
        if vpos != -1:
            assert astring[vpos : vpos + len(vstr)] == vstr

        # assert astring meta is correct
        assert input_string[apos : apos + len(astring)] == astring
