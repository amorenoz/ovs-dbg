.. _ofparse-reference-label:

=================================
ofparse: Flow Parsing Utility
=================================

ofparse is a tool to display the OpenFlow Flows and Datapath Flows in different formats.

It parses a list of OpenFlow commands (such as the ones that `ovs-ofproto dump-flows` or
`ovs-dpctl dump-flows` would generate) prints them back in the following formats


-----
Usage
-----

::

    Usage: ofparse [OPTIONS] TYPE

      OpenFlow Parse utility.

      It parses openflow and datapath flows (such as the output of ovs-ofctl dump-
      flows or ovs-appctl dpctl/dump-flows) and prints them in different formats.

    Options:
      -c, --config PATH     Use config file  [default: /home/amorenoz/code/ovs-
                            dbg/ovs_dbg/ofparse/etc/ofparse.conf]
      --style TEXT          Select style (defined in config file)
      -i, --input TEXT      Read flows from specified filepath. If not provided,
                            flows will be read from stdin. This option can be
                            specified multiple times. Format [alias,]FILENAME.
                            Where alias is a name that shall be used to refer to
                            this FILENAME
      -p, --paged           Page the result (uses $PAGER). If colors are not
                            disabled you might need to enable colors on your
                            PAGER, eg: export PAGER="less -r".  [default: False]
      -f, --filter TEXT     Filter flows that match the filter expression. Run
                            'ofparse filter'for a detailed description of the
                            filtering syntax
      -l, --highlight TEXT  Highlight flows that match the filter expression. Run
                            'ofparse filter'for a detailed description of the
                            filtering syntax
      -h, --help            Show this message and exit.

    Commands:
      datapath  Process DPIF Flows
      openflow  Process OpenFlow Flows


-------------------
JSON representation
-------------------

To print the json representation of a flow run:

::

    ofparse {openflow | datapath } json


The output is a json list of json objects each of one representing a individual flow. Each flow object contains the following keys:

- *orig*: contains the original flow string
- *info*: contains an object with the flow information such as: *cookie*, *duration*, *table*, *n_packets*, *n_bytes*, etc
- *match*: contains an object with the flow match. For each match, the object contains a key-value where the key is the name of the match as defined in ovs-fields_ and ovs-ofctl_ and the value represents the match value. The way each value is represented depends on its type. (See `Value representation`_ section)
- *actions*: contains a list of action objects. Each action is represented by an json object that has one key and one value. The key corresponds to the action name. The value represents the arguments of such key. See `Action representation`_ section for more details
- *ufid*: (datpath flows only) contains the ufid

Value representation
********************

Values are represented differently depending on their type:

* **Flags**: Fields that represent flags (e.g: `tcp`) are represented by boolean "true"
* **Decimal / Hexadecimal**: They are represented by their integer value. If they support masking, they are represented by a dictionary with two keys: *value* contains the field value and *mask* contains the mask. Both are integers.
* **Ethernet**: They are represented by a string: {address}[/{mask}]
* **IPv4 / IPv6**: They are represented by a string {address}[/mask]
* **Registers**: They are represented by a dictionary with three keys: *field* contains the field value (string), *start* and *end* that represent the first and last bit of the register. For example, the register

::

    NXM_NX_REG10[0..15]

is represented as:

::

    {
        "field": "NXM_NX_REG10",
        "start": 0,
        "end": 15
    },



Action representation
*********************

Actions are generally represented by an object that has a single key and a value.
The key is the action name as defined ovs-actions_.


The value of actions that have no arguments (such as 'drop') is (boolean) "true".

The value of actions that have a list of arguments (e.g: *resubmit([port],[table],[ct])*) is an object
that has the name of the argument as key. The argument names for each action is defined in ovs-actions_. For example, the action:

::

    resubmit(,10)

is represented as:

::

        {
            "redirect": {
                "port": "",
                "table": 10
            }
        }


The value of actions that have a key-word list as arguments (e.g: *ct([argument])*) is an object whose keys correspond to the keys defined in ovs-actions_. The way values are represented depends on the type of the argument ( see `Value representation`_ ). For example, the action:

::

    ct(table=14,zone=NXM_NX_REG12[0..15],nat)

is represented as:

::

            {
                "ct": {
                    "table": 14,
                    "zone": {
                        "field": "NXM_NX_REG12",
                        "start": 0,
                        "end": 15
                    },
                    "nat": true
                }
            }


----------------
Openflow parsing
----------------

The openflow flow parsing supports this extra formats:

Logic format
************

**logic**: To print the logical representation of a flow run:

::

    ofparse openflow logic

(run `ofparse openflow logic --help` for more details)


When printing a logical representation of a flow list, flows are grouped into *logical flows* that:

- have the same *priority*
- match on the same fields (regardless of the match value)
- execute the same actions (regardless of the actions' arguments, except for resubmit and output)
- Optionally, the *cookie* can be counted as part of the logical flow as well (*--cookie*)

Flows are sorted by table and then by logical flow:


::

    TABLE 1
     -> logial flow ( x n )
       -> flow 1
       -> flow 2
       ...
	

Cookie format
*************
Use **cookie** format to sort the flows by cookie and then by table

::

    Cookie 0xa
     -> TABLE 1
       -> flow 1
       -> flow 2
       ...
    -> TABLE 2
    ...


ovn-detrace integration
***********************
Both **cookie** and **logic** formats support integration with OVN, in particular with ovn-detrace
utility.

You will need a recent OVN version that contains a specific `ovn-detrace patch`_ as well as locally
accesible OVN Northbound and OVN Southbound ovsdb-server instances running.

If you have all that, you can enable ovn-detrace support and ofparse will use ovn-detrace to
extract the OVN information for each cookie and print it alogside the Openflow flows.

See help for more information:

::

    ofparse openflow cookie --help


HTML representation
*******************
Use the *html* option to print an interactive flow table in html

::

    ofparse openflow html > /myflows.html

-----------------
DPIF Flow parsing
-----------------

The openflow flow parsing supports this extra formats:

**Logic**: To print the flows sorted by `recirc_id`

::

    ofparse datapath logic


HTML representation
*******************
Use the *html* option to print an interactive flow table in html

::

    ofparse datapath html > myflows.html


Graph representation
********************
Use the *graph* option to print a graphviz graph of the datapath. Flows are
sorted by their *recirc_id* to better understand the datapath's logic.

::

    ofparse datapath graph | dot -Tsvg > myflows.svg


Use the additional **-h** flag to show the graph in a html page alongside the interactive flow table

::

    ofparse datapath graph --html > myflows.html


---------
Filtering
---------

`ofparse` support filtering the flows that get printed (regardless of the selected format).

The filtering syntax is defined as follows

::

    [! | not ] KEY[OPERATOR VALUE] [ && | and | || | or] ...

Where:

- **KEY** is a flow match or action key. Action parameters can be used by specifying the key as {ACTION_NAME}.{ARGUMENT} (e.g: `output.port`). Likewise, keys within fields that are represented by objects can be used as {FIELD_NAME}.{SUB_KEY} (e.g: masked fields such as *metadata* can be accessed as `metadata.value`)
- **OPERATOR** is one of the following
   - **"="** checks for equality
   - **"<"** numerical 'less than'
   - **">"** numerical 'greater than'
   - **"~="** mask matching (valid for fields such as IPv4, IPv6 and Ethernet)
- **VALUE**: The value to be compared against
- **&& | and**: combines the filters applying logical AND
- **|| | or**: combines the filters applying logical OR
- **! | not**: applies the logical NOT to the filter

For fields or actions that are flags (e.g: *tcp* or *drop*), the OPERATOR and VALUE can be omitted

Examples:

::

    n_bytes>0 and drop
    nw_src~=192.168.1.1 or arp.tsa=192.168.1.1
    ! tcp && output.port=2



----------
Formatting
----------
Formatting can be configured by modifying the *ofparse.conf* file provided as
part of the distribution (python egg).

Formatting options are placed under **[style.{style_name}]** section in the config file. Styles can then be selected using **--style** flag.

For instance, if you want to create your predefined style called "foo", edit
config file to show:

::

    [style.foo]
    ...

and then run:

::

    ofparse --style=foo ....


Console formatting
******************

To modify how flows are printed in the console, add configuration entries using
the following format:

::

    console.{substring_identifier}.[color | underline] = {value}

- **The substring identidier** can have the following keys:
   - *[key | value | flag | delim | default]* to select whether the key, the value, the standalone key (flag), the delimiters (such as '(') or the "rest" of the string respectively.
   - *{key_name}*: to specify a key match
   - *type.{type_name}* to specify a value type (the use of complex types such as 'IPAddress', 'IPMask', 'EthMask' are supported)
   - *highlighted* if the style is to be applied when the key is highlighted
- **color** options must have values matching CSS-style colors, eg: #ff00ff, red.
- **underline** options must have values "true" or "false"


Examples:

::

    # set default colors:
    console.key.color = #5D86BA
    console.value.color= #B0C4DE
    console.delim.color= #B0C4DE
    console.default.color= #FFFFFF
    console.flag.color = #875fff

    # defaults for special types
    console.value.type.IPAddress.color = #008700
    console.value.type.IPMask.color = #008700
    console.value.type.EthMask.color = #008700

    # dim some values that can be quite long arguments
    console.value.ct.color = bright_black
    console.value.ufid.color = #870000
    console.value.clone.color = bright_black
    console.value.controller.color = bright_black

    # show drop and recirculations
    console.key.drop.color = red
    console.key.resubmit.color = #00d700
    console.key.output.color = #00d700
    console.value.output.color = #00d700

    # highlights
    console.key.highlighted.color = #f20905
    console.key.highlighted.underline = true
    console.value.highlighted.underline = true
    console.delim.highlighted.underline = true


HTML Formatting
***************
HTML Formatting is very uses the same substring identifiers as the console formatting.

The only difference is that *underline* is not supported.

Heat Map
********
Some output commands support heat-map formatting (*--heat-map*) both in openflow and
datapath flow formats. This option changes the color of the packet and byte counters
to reflect their relative size. The color gradient goes through the following colors:

blue (coldest, lowest), cyan, green, yellow, red (hottest, highest)

Note filtering is typically applied before the range is calculated.


.. _ovs-actions: http://www.openvswitch.org/support/dist-docs/ovs-actions.7.html
.. _ovs-fields: http://www.openvswitch.org/support/dist-docs/ovs-fields.7.html
.. _ovs-ofctl: http://www.openvswitch.org/support/dist-docs/ovs-ofctl.8.txt
.. _`ovn-detrace patch`: https://github.com/ovn-org/ovn/commit/d659b6538b00bd72aeca1fc5dd3a3c337ac53f37
