import pytest

from ovs_dbg.flows import KVParser, KeyValue, KeyMetadata


@pytest.mark.parametrize(
    "input_string,expected",
    [
        (
            "cookie=0x0, duration=147566.365s, table=0, n_packets=39, n_bytes=2574, idle_age=65534, hard_age=65534",
            [
                KeyValue("cookie", 0),
                KeyValue("duration", "147566.365s"),
                KeyValue("table", 0),
                KeyValue("n_packets", 39),
                KeyValue("n_bytes", 2574),
                KeyValue("idle_age", 65534),
                KeyValue("hard_age", 65534),
            ],
        ),
        (
            "load:0x4->NXM_NX_REG13[],load:0x9->NXM_NX_REG11[],load:0x8->NXM_NX_REG12[],load:0x1->OXM_OF_METADATA[],load:0x1->NXM_NX_REG14[],mod_dl_src:0a:58:a9:fe:00:02,resubmit(,8)",
            [
                KeyValue("load", "0x4->NXM_NX_REG13[]"),
                KeyValue("load", "0x9->NXM_NX_REG11[]"),
                KeyValue("load", "0x8->NXM_NX_REG12[]"),
                KeyValue("load", "0x1->OXM_OF_METADATA[]"),
                KeyValue("load", "0x1->NXM_NX_REG14[]"),
                KeyValue("mod_dl_src", "0a:58:a9:fe:00:02"),
                KeyValue("resubmit", ",8"),
            ],
        ),
        ("l1(l2(l3(l4())))", [KeyValue("l1", "l2(l3(l4()))")]),
        (
            "l1(l2(l3(l4()))),foo:bar",
            [KeyValue("l1", "l2(l3(l4()))"), KeyValue("foo", "bar")],
        ),
    ],
)
def test_kv_parser(input_string, expected):
    tparser = KVParser()
    tparser.parse(input_string)
    result = tparser.kv()
    assert len(expected) == len(result)
    for i in range(0, len(result)):
        assert result[i].key == expected[i].key
        assert result[i].value == expected[i].value
        kpos = result[i].meta.kpos
        kstr = result[i].meta.kstring
        vpos = result[i].meta.vpos
        vstr = result[i].meta.vstring
        assert input_string[kpos: kpos + len(kstr)] == kstr
        if vpos != -1:
            assert input_string[vpos: vpos + len(vstr)] == vstr
