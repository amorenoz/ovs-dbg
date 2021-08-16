'''
Accepts the output of OFProto/trace as an input string.
Returns a ofpt_parser object with an OfProtoTraceOutput object.
Each member variable of OfProtoTraceOutput objects contain a string
formatted to be additionally parsed by the other tools in ovs_dbg.

To Do
- Edge cases
- Refactor ofp class functions to allow for tighter integration?
- Address resubmit nested table / extra text output

'''
import sys
from ovs_dbg.ofparse.process import process_flows, tojson, pprint
from ovs_dbg.ofptp import string_to_dict

class Ofpt_Output:
    """
    Class for storing each component of ofprototrace output

    Args:
        ofpt_flow (string): Key-value string following "Flow:"
        bridge (list): List of ofpt_bridge_entry objects 
        final_flow (string): Key-value String Following "Final_Flow:"
        megaflow (string): Key-value String Following "Mega_flow:"
        dpactions (string): Action string following "Datapath Actions" 
        reformmated to ofp_act parable format
    """
    def __init__(self, ofpt_flow, bridge, final_flow, megaflow, dpactions):
        # Constructor
        self._ofpt_flow = string_to_dict(ofpt_flow, "match")
        self._bridge = bridge
        self._final_flow = string_to_dict(final_flow, "match")
        self._megaflow = string_to_dict(megaflow, "match")
        self._dpactions = string_to_dict(dpactions, "actions")

class Ofpt_Bridge:
    """
    Class for storing each component of ofproto/trace bridge output

    Args:
        bridge_name (string)
        bridge_entries (list): List of Ofpt_bridge_entry objects
    """
    def __init__(self, name, entry_string):
        self.bridge_name = name
        self.bridge_entries = self.entries_string_to_list(entry_string)
    

    def entries_string_to_list(self, entry_string):
        lines = entry_string.split("\n")

        strings = list()
        temp_string = ''
        for line in lines:
            if not line.startswith("    "):
                if not temp_string == '':
                    strings.append(temp_string.strip())
                    temp_string = ''
            temp_string += line + '\n'
        strings.append(temp_string.strip())

        bridge_entry_list = list()

        for string in strings:
            try:
                parts = string.split(". ", 1)
                num = parts[0].strip()
                match_info = parts[1].split("\n", 1)[0]
                actions = parts[1].split("\n", 1)[1].strip()
            except:
                print("encountered edge case within bridge entry: ",string, file = sys.stderr)
                #strings.remove(string)
                continue
            match_info_list = parse_match_info(match_info)
            bridge_entry_list.append(Ofpt_Bridge_Entry(
                    num,
                    match_info_list[0],
                    match_info_list[1],
                    actions
                    ))

        return bridge_entry_list
        # for each string in list
            # extract table num
            # extract and process matches
            # extract and process actions
            # init entry w/ tabnum, match, action


class Ofpt_Bridge_Entry:
    """
    Struct containing table Numbers, Info, Match, and Action strings in 
    KVparsable formatting. Each entry corresponds to a single flow through a 
    table in ofProto/Trace output
    """
    def __init__(self, table_num, match_string, info_string, action_string):
        self.table_num = table_num
        self.info = self.process_info(info_string)
        self.match_string = self.process_match(match_string)
        self.action_string = self.process_action(action_string)

    def process_info(self, info_string):
        if info_string:
            return string_to_dict(info_string, "info")
        else:
            return None

    def process_match(self, match_string):
        return string_to_dict(match_string.replace(", ",",").replace(" ","="), "match")
    
    def process_action(self, action_string):
        # need to handle nested table due to resubmit
        # need to handle "->"" informational messages
        return string_to_dict(action_string.replace("\n",",").replace(" ",""), "actions")
        

class OFPTTrace:
    """ovs/appctl ofproto/trace trace result"""
    def __init__(self, input_string):
        """Constructor"""
        self.raw_output = input_string
        self.parsed_output = self.initialize_output(input_string)
        
    def process_final_flow(self, final_flow):
        if final_flow == "unchanged":
            final_flow = "unchanged,0"
        return final_flow

    def process_dpactions(self, dpactions):
        return dpactions

    def initialize_output(self, input_string):
        """
        Parses the output of ofproto/trace

        Args:
            input_string(str): output from ofproto/trace

        Returns:
            OfProtoTraceOutput instance containing member variables
            corresponding to each section of ofproto/trace output
        """

        parts = input_string.split("Datapath actions: ")
        if len(parts) != 2:
            raise ValueError("malformed ofprototrace output - Dp actions")
        dpactions = parts[1].strip()
        parts = parts[0].split("Megaflow: ")
        if len(parts) != 2:
            raise ValueError("malformed ofprototrace output - Megaflow")
        megaflow = parts[1].strip()
        parts = parts[0].split("Final flow: ")
        if len(parts) != 2:
            raise ValueError("malformed ofprototrace output - Final flow")
        final_flow = parts[1].strip()
        # determine length of next delimiter
        for line in parts[0].split("\n"):
            if "bridge(\"" in line:
                line_len = len(line)
        parts = parts[0].split("-" * line_len)
        if len(parts) != 2:
            raise ValueError("malformed ofprototrace output - tables")
        bridge_entries = parts[1].strip()
        parts = parts[0].split("bridge(\"")
        if len(parts) != 2:
            raise ValueError("malformed ofprototrace output - bridge name")
        bridge_name = parts[1].strip()[:-2]
        parts = parts[0].split("Flow: ")
        if len(parts) != 2:
            raise ValueError("malformed ofprototrace output - flow")
        flow = parts[1].strip()

        # Current assumptions:
        # Flow: is always a valid ofp flow
        # Bridge->see OFPT_Bridge
        # Process Final Flow only for "unchanged" case
        # Megaflow is always a valid ofp flow
        # dpactions should always be valid action string parsable by ofp_act

        return Ofpt_Output(
            flow,
            Ofpt_Bridge(bridge_name,bridge_entries),
            self.process_final_flow(final_flow),
            megaflow,
            self.process_dpactions(dpactions))

def parse_for_recirc(input_string):
    """
    Parses raw OFPT Input to determine if multiple OFPTTrace objects
    are contained within a single output stream 
    (e.g recirc resulting in thaw and resume)

    Args:
        OFPT raw output (str)
    Returns:
        List of OFPT strings

    """
    ofptTrace_list = list()

    recirc_delim = "=" * 79

    while len(input_string.split(recirc_delim, 2)) >= 3:
        ofptTrace_list.append(input_string.split(recirc_delim, 2)[0])
        input_string = input_string.split(recirc_delim, 2)[2]
    ofptTrace_list.append(input_string)

    return ofptTrace_list

def parse_match_info(match_info):
    # Currently only expects "cookie" as potential info
    parts = match_info.split(", cookie ")
    if len(parts) == 1:
        return (match_info, None)
    if len(parts) > 2:
        raise ValueError("malformed ofprototrace output - Cookie")

    return (parts[0], "cookie=" + parts[1])