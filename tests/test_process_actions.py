import pytest

import json
from ovs_dbg.decoders import FlowEncoder
from ovs_dbg.trace import process_actions


@pytest.mark.parametrize(
    "input_string,expected",
    [
        (
            (
    """    set_field:0x1d->reg13
    set_field:0x9->reg11
    set_field:0x5->reg12
    set_field:0x4->metadata
    set_field:0x6->reg14
    resubmit(,8)"""
            ), 
            (
    """{
    "actions": [
        {
            "set_field": {
                "value": {
                    "reg13": {
                        "value": 29,
                        "mask": 4294967295
                    }
                },
                "dst": {
                    "field": "reg13"
                }
            }
        },
        {
            "set_field": {
                "value": {
                    "reg11": {
                        "value": 9,
                        "mask": 4294967295
                    }
                },
                "dst": {
                    "field": "reg11"
                }
            }
        },
        {
            "set_field": {
                "value": {
                    "reg12": {
                        "value": 5,
                        "mask": 4294967295
                    }
                },
                "dst": {
                    "field": "reg12"
                }
            }
        },
        {
            "set_field": {
                "value": {
                    "metadata": {
                        "value": 4,
                        "mask": 18446744073709551615
                    }
                },
                "dst": {
                    "field": "metadata"
                }
            }
        },
        {
            "set_field": {
                "value": {
                    "reg14": {
                        "value": 6,
                        "mask": 4294967295
                    }
                },
                "dst": {
                    "field": "reg14"
                }
            }
        },
        {
            "resubmit": {
                "port": "",
                "table": 8
            }
        }
    ]
}"""
            )
        ),
        (
            (
'''    set_field:0/0x80->reg10
    resubmit(,68)
    68. in_port=5,vlan_tci=0x0000/0x1000, priority 100
            set_field:0x15->reg13
            set_field:0x1->reg15
            resubmit(,39)
            69. No match.
                    move:NXM_NX_REG10[7]->NXM_NX_XXREG0[108]
                     -> NXM_NX_XXREG0[108] is now 0
                    drop
    resubmit(,22)'''
            ),
            (
'''{
    "actions": [
        {
            "set_field": {
                "value": {
                    "reg10": {
                        "value": 0,
                        "mask": 128
                    }
                },
                "dst": {
                    "field": "reg10"
                }
            }
        },
        {
            "resubmit": {
                "port": "",
                "table": 68
            }
        },
        {
            "next": {
                "table": "68",
                "info": null,
                "match": {
                    "in_port": 5,
                    "vlan_tci": {
                        "value": 0,
                        "mask": 4096
                    },
                    "priority": 100
                },
                "actions": [
                    {
                        "set_field": {
                            "value": {
                                "reg13": {
                                    "value": 21,
                                    "mask": 4294967295
                                }
                            },
                            "dst": {
                                "field": "reg13"
                            }
                        }
                    },
                    {
                        "set_field": {
                            "value": {
                                "reg15": {
                                    "value": 1,
                                    "mask": 4294967295
                                }
                            },
                            "dst": {
                                "field": "reg15"
                            }
                        }
                    },
                    {
                        "resubmit": {
                            "port": "",
                            "table": 39
                        }
                    },
                    {
                        "next": {
                            "table": "69",
                            "info": null,
                            "match": "No Match",
                            "actions": [
                                {
                                    "move": {
                                        "src": {
                                            "field": "NXM_NX_REG10",
                                            "start": 7,
                                            "end": 7
                                        },
                                        "dst": {
                                            "field": "NXM_NX_XXREG0",
                                            "start": 108,
                                            "end": 108
                                        }
                                    }
                                },
                                {
                                    "drop": true
                                }
                            ]
                        }
                    }
                ]
            }
        },
        {
            "resubmit": {
                "port": "",
                "table": 22
            }
        }
    ]
}'''
            )
        ),
    ]
        
)

def test_kv_parser(input_string, expected):
    
    action_list = process_actions(input_string)
    trace_Dict = {}
    trace_Dict['actions'] = action_list

    assert(json.dumps(trace_Dict, indent = 4,  cls=FlowEncoder)) == expected