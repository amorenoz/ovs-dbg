ofparse
=======

Usage
*****

ofparse is a tool to display the OpenFlow Flows in different formats.
It parses a list of OpenFlow commands (such as the ones that `ovs-ofproto dump-flows`
would generate and prints them back in different ways.
::
	
	$ ofparse --help
	 Usage: ofparse [OPTIONS] COMMAND [ARGS]...
	 
	   OpenFlow Parse utility.
	 
	   It parses openflow flows (such as the output of ovs-ofctl 'dump-flows') and
	   prints them in different formats
	 
	 Options:
	   -f, -file PATH  Read flows from specified filepath
	   -p, --paged     Page the result (uses $PAGER). If styling is not disabled
	                   you might need to enable colors on your $PAGER, eg: export
	                   PAGER="less -r".  [default: False]
	   --no-style      Page the result (uses $PAGER)  [default: False]
	   -h, --help      Show this message and exit.
	 
	 Commands:
	   json    Print the json representation of the flow list
	   logic   Print the logical structure of the flows.
	   pprint  Pretty print the flows


