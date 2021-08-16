import sys


try:
    from ovs_dbg.trace import OFPTTrace
    import json
    from ovs_dbg.decoders import FlowEncoder
except Exception:
    print("ERROR: Please install the correct support")
    print("       libraries")
    print("       Alternatively, check that your PYTHONPATH is pointing to")
    print("       the correct location.")
    sys.exit(1)

def process_ofpt(OFPTobj_list, output_type, print_raw):
    """
    Process OFPTTrace object into desired output

    Args:
        valid OFPTTrace obj
        desired output type (str)
            (currently only json)
        raw_output flag (bool)
    Return:
        Output in output_type (currently only json)
    """

    if len(OFPTobj_list) > 1:
        dict_object = list ()
        for trace in OFPTobj_list:
            dict_object.append(to_dict(trace,print_raw))
    else:
        dict_object = to_dict(OFPTobj_list[0], print_raw)

    # process into requested format (default json)
    if output_type == 'json':
        return json.dumps(dict_object, indent = 4,  cls=FlowEncoder)
    else:
        return 'error'


def to_dict(OFPTTrace, print_raw):
    trace_Dict = {}
    bridge_entry_list = list ()

    for table in OFPTTrace.parsed_output._bridge.bridge_entries:
        table_entry_dict = {}
        table_entry_dict["table"] = (int)(table.table_num)
        if table.info:
            table_entry_dict["info"] = table.info
        table_entry_dict["match"] = table.match_string
        table_entry_dict["action"] = table.action_string
        bridge_entry_list.append(table_entry_dict)

    if print_raw:
        trace_Dict["raw"] = OFPTTrace.raw_output

    trace_Dict["Flow"] = OFPTTrace.parsed_output._ofpt_flow
    trace_Dict["bridge: " + OFPTTrace.parsed_output._bridge.bridge_name] = bridge_entry_list
    trace_Dict["Final flow"] = OFPTTrace.parsed_output._final_flow
    trace_Dict["MegaFlow"] = OFPTTrace.parsed_output._megaflow
    trace_Dict["Datapath actions"] = OFPTTrace.parsed_output._dpactions

    return trace_Dict
