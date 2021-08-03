import sys


try:
    from ovs_dbg.trace import OFPTTrace
    import json
except Exception:
    print("ERROR: Please install the correct support")
    print("       libraries")
    print("       Alternatively, check that your PYTHONPATH is pointing to")
    print("       the correct location.")
    sys.exit(1)

def process_ofpt(OFPTTrace, output_type):
    """
    Process OFPTTrace object into desired output

    Args:
        valid OFPTTrace obj
        desired output type (str)
            (currently only json)
    Return:
        (Currently) Dictionary object to be converted to json by main
        Note* maybe seperate to_json function is redundant if all output
        methods require dict format, just process to dict and send back
        to main. 
    """

    return to_json(OFPTTrace)


def to_json(OFPTTrace):
    trace_Dict = {}
    bridge_entry_dict = {}


    for table in OFPTTrace.parsed_output._bridge.bridge_entries:
        table_entry_dict = {}
        table_entry_dict["match"] = table.match_string
        table_entry_dict["action"] = table.action_string
        bridge_entry_dict["Table " + table.table_num] = table_entry_dict

    trace_Dict["Flow"] = OFPTTrace.parsed_output._ofpt_flow
    trace_Dict["bridge: " + OFPTTrace.parsed_output._bridge.bridge_name] = bridge_entry_dict
    trace_Dict["Final flow"] = OFPTTrace.parsed_output._final_flow
    trace_Dict["MegaFlow"] = OFPTTrace.parsed_output._megaflow
    trace_Dict["Datapath actions"] = OFPTTrace.parsed_output._dpactions

    return trace_Dict
