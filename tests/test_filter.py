import pytest

from ovs_dbg.filter import OFFilter
from ovs_dbg.ofp import OFPFlow


@pytest.mark.parametrize(
    "expr,flow,expected",
    [
        (
            "nw_src=192.168.1.1 && tcp_dst=80",
            OFPFlow.from_string("nw_src=192.168.1.1,tcp_dst=80 actions=drop"),
            True,
        ),
        (
            "nw_src=192.168.1.2 || tcp_dst=80",
            OFPFlow.from_string("nw_src=192.168.1.1,tcp_dst=80 actions=drop"),
            True,
        ),
        (
            "nw_src=192.168.1.1 || tcp_dst=90",
            OFPFlow.from_string("nw_src=192.168.1.1,tcp_dst=80 actions=drop"),
            True,
        ),
        (
            "nw_src=192.168.1.2 && tcp_dst=90",
            OFPFlow.from_string("nw_src=192.168.1.1,tcp_dst=80 actions=drop"),
            False,
        ),
        (
            "nw_src=192.168.1.1",
            OFPFlow.from_string("nw_src=192.168.1.0/24,tcp_dst=80 actions=drop"),
            False,
        ),
        (
            "nw_src~=192.168.1.1",
            OFPFlow.from_string("nw_src=192.168.1.0/24,tcp_dst=80 actions=drop"),
            True,
        ),
        (
            "nw_src~=192.168.1.1/30",
            OFPFlow.from_string("nw_src=192.168.1.0/24,tcp_dst=80 actions=drop"),
            True,
        ),
        (
            "nw_src~=192.168.1.0/16",
            OFPFlow.from_string("nw_src=192.168.1.0/24,tcp_dst=80 actions=drop"),
            False,
        ),
        (
            "nw_src~=192.168.1.0/16",
            OFPFlow.from_string("nw_src=192.168.1.0/24,tcp_dst=80 actions=drop"),
            False,
        ),
        (
            "n_bytes=100",
            OFPFlow.from_string(
                "n_bytes=100 priority=100,nw_src=192.168.1.0/24,tcp_dst=80 actions=drop"
            ),
            True,
        ),
        (
            "n_bytes>10",
            OFPFlow.from_string(
                "n_bytes=100 priority=100,nw_src=192.168.1.0/24,tcp_dst=80 actions=drop"
            ),
            True,
        ),
        (
            "n_bytes>100",
            OFPFlow.from_string(
                "n_bytes=100 priority=100,nw_src=192.168.1.0/24,tcp_dst=80 actions=drop"
            ),
            False,
        ),
        (
            "n_bytes<100",
            OFPFlow.from_string(
                "n_bytes=100 priority=100,nw_src=192.168.1.0/24,tcp_dst=80 actions=drop"
            ),
            False,
        ),
        (
            "n_bytes<1000",
            OFPFlow.from_string(
                "n_bytes=100 priority=100,nw_src=192.168.1.0/24,tcp_dst=80 actions=drop"
            ),
            True,
        ),
        (
            "n_bytes>0 && drop=true",
            OFPFlow.from_string(
                "n_bytes=100 priority=100,nw_src=192.168.1.0/24,tcp_dst=80 actions=drop"
            ),
            True,
        ),
        (
            "n_bytes>0 && drop=true",
            OFPFlow.from_string(
                "n_bytes=100 priority=100,nw_src=192.168.1.0/24,tcp_dst=80 actions=2"
            ),
            False,
        ),
        (
            "n_bytes>10 && !output.port=3",
            OFPFlow.from_string(
                "n_bytes=100 priority=100,nw_src=192.168.1.0/24,tcp_dst=80 actions=2"
            ),
            True,
        ),
        (
            "dl_src=00:11:22:33:44:55",
            OFPFlow.from_string(
                "n_bytes=100 priority=100,dl_src=00:11:22:33:44:55,nw_src=192.168.1.0/24,tcp_dst=80 actions=2"
            ),
            True,
        ),
        (
            "dl_src~=00:11:22:33:44:55",
            OFPFlow.from_string(
                "n_bytes=100 priority=100,dl_src=00:11:22:33:44:55/ff:ff:ff:ff:ff:00,nw_src=192.168.1.0/24,tcp_dst=80 actions=2"
            ),
            True,
        ),
        (
            "dl_src~=00:11:22:33:44:66",
            OFPFlow.from_string(
                "n_bytes=100 priority=100,dl_src=00:11:22:33:44:55/ff:ff:ff:ff:ff:00,nw_src=192.168.1.0/24,tcp_dst=80 actions=2"
            ),
            True,
        ),
    ],
)
def test_filter(expr, flow, expected):
    ffilter = OFFilter(expr)
    result = ffilter.evaluate(flow)
    assert expected == result
