from ovs_dbg.ofptp import string_to_dict
import pytest

from ovs_dbg.ofp import OFPFlow
from ovs_dbg.kv import KeyValue
from ovs_dbg.decoders import EthMask, IPMask


@pytest.mark.parametrize(
    "input_string,section_type,expected",
    [
        (
            "cookie=0x11111111","info",
            {"cookie" : int('11111111', 16)},
        ),
        (
            "cookie=0x95721583","info",
            {"cookie" : int('95721583', 16)},
        ),
        (
            "ip,metadata=0x1,nw_dst=0.0.0.0/8,priority=100","match",
            {
                'ip': True, 
                'metadata': 
                {
                    'value': 1, 
                    'mask': 18446744073709551615
                }, 
                'nw_dst': IPMask('0.0.0.0/8'), 
                'priority': 100
            }
        ),
        (
            "reg14=0x6,metadata=0x4,dl_src=0a:58:0a:f4:01:06,priority=50","match",
            {
                
                'reg14': {
                    'value': 6,
                    'mask': 4294967295
                },
                'metadata': {
                    'value': 4,
                    'mask': 18446744073709551615
                },
                'dl_src': EthMask('a:58:a:f4:1:6'),
                'priority': 50
                
            }
        ),
        (
            "ip,reg14=0x6,metadata=0x4,dl_src=0a:58:0a:f4:01:06,nw_src=10.244.1.6,priority=90","match",
            {
                'ip': True,
                'reg14': {
                    'value': 6,
                    'mask': 4294967295
                },
                'metadata': {
                    'value': 4,
                    'mask': 18446744073709551615
                },
                'dl_src': EthMask('a:58:a:f4:1:6'),
                'nw_src': IPMask('10.244.1.6/32'),
                'priority': 90
            }
        ),
        (
            "ct_state=-new+est-rpl+trk,ct_label=0/0x1,metadata=0x4,priority=4","match",
            {
                'ct_state': '-new+est-rpl+trk',
                'ct_label': {
                    'value': 0,
                    'mask': 1
                },
                'metadata': {
                    'value': 4,
                    'mask': 18446744073709551615
                },
                'priority': 4
            }
        ),
    ],
)
def test_act(input_string, section_type, expected):
    assert string_to_dict(input_string, section_type) == expected