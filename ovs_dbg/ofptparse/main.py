#!/bin/env python
"""
To Do:
    other formats than json (ovn detrace option?)

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


def extract_ofpt_output(FILE):
    # Check for recirc. If so, process each trace individually
    traces = parse_for_recirc(FILE.read())
    # Convert strings to a list of OFPTTrace objects
    OFPTobj_list = list ()
    for trace in traces:
        OFPTobj_list.append(OFPTTrace(trace))
    return OFPTobj_list


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("-o", "--output", help="Output result to a file.")
    parser.add_argument("-i", "--input", help=
        "Read flows from specified filepath."
        "If not provided, flows will be read from stdin")
    parser.add_argument("-r", "--raw", action='store_true', help="Include raw ofprototrace as a KV pair in output")

    args = parser.parse_args()

    if args.input:
        FILE = open(args.input)
    else: 
        FILE = sys.stdin

    OFPTobj_list = extract_ofpt_output(FILE)
    ofpt_out = process_ofpt(OFPTobj_list, 'json', args.raw)

    if args.output:
        f = open(args.output, "a")
        f.write(ofpt_out)
        f.close()
    else:
        print(ofpt_out, file = sys.stdout)

        


if __name__ == "__main__":
    main()

