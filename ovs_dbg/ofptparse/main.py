#!/bin/env python
"""
To Do:

Take input pipes from ofproto/trace directly
Accept flags for help / raw / output to file / other formats than json (ovn detrace option?)

"""
import sys
import argparse
import json

try:
    from ovs_dbg.trace import OFPTTrace, parse_for_recirc
    from ovs_dbg.ofptparse.process import process_ofpt
except Exception:
    print("ERROR: Please install the correct support")
    print("       libraries")
    print("       Alternatively, check that your PYTHONPATH is pointing to")
    print("       the correct location.")
    sys.exit(1)


def extract_ofpt_output(fn):
    input_string = open(fn)
    # check for recirc, if so process as multiple strings
    traces = parse_for_recirc(input_string.read())
    # parse for each string
    OFPTobj_list = list ()
    for trace in traces:
        OFPTobj_list.append(OFPTTrace(trace))
    return OFPTobj_list


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-f",
        "--file",
        action="store",
        required=True,
        help="Read meta-flow info from file",
    )
    parser.add_argument("-o", "--output", help="Output result to a file.", action="store_true")
    args = parser.parse_args()

    OFPTobj_list = extract_ofpt_output(args.file)
    if len(OFPTobj_list) > 1:
        json_object = list ()
        for trace in OFPTobj_list:
        # process into requested format (default json)
            json_object.append(process_ofpt(trace, "json"))
    else:
        json_object = process_ofpt(OFPTobj_list[0], "json")

    # if args.output:
    #     f = open("ofproto_trace_output.txt", "a")
    #     f.write(str(traces)+'\n')
    print(json.dumps(json_object, indent = 4))


if __name__ == "__main__":
    main()

