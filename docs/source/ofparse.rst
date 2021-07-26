=================================
ofparse: Openflow Parsing Utility
=================================

ofparse is a tool to display the OpenFlow Flows in different formats.
It parses a list of OpenFlow commands (such as the ones that `ovs-ofproto dump-flows`
would generate and prints them back in the following formats:


-------------------
JSON representation
-------------------

To print the json representation of a flow run:

::

    ofparse json


The output is a json list of json objects each of one representing a individual flow. Each flow object contains the following keys:

- *raw*: contains the original flow string
- *info*: contains an object with the flow information such as: *cookie*, *duration*, *table*, *n_packets*, *n_bytes*, etc
- *match*: contains an object with the flow match. For each match, the object contains a key-value where the key is the name of the match as defined in ovs-fields_ and ovs-ofctl_ and the value represents the match value. The way each value is represented depends on its type. (See `Value representation`_ section)
- *actions*: contains a list of action objects. Each action is represented by an json object that has one key and one value. The key corresponds to the action name. The value represents the arguments of such key. See `Action representation`_ section for more details


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


----------------------
Logical representation
----------------------

To print the logical representation of a flow run:

::

    ofparse logic

(run `ofparse --help` for more details)


When printing a logical representation of a flow list, flows are grouped into *logical flows* that:

- have the same *cookie* and *priority*
- match on the same fields (regardless of the match value)
- execute the same actions (regardless of the actions' arguments)


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



.. _ovs-actions: http://www.openvswitch.org/support/dist-docs/ovs-actions.7.html 
.. _ovs-fields: http://www.openvswitch.org/support/dist-docs/ovs-fields.7.html
.. _ovs-ofctl: http://www.openvswitch.org/support/dist-docs/ovs-ofctl.8.txt
