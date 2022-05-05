from ovs_dbg.ofp import OFPFlow

def string_to_dict(string, section_type):
    """Parse a section of ofproto flow string

    section_type specifies the sections of an ofpf string being handed
    'info' 'match' 'action'

    :param ofp_string section: info, match or action string as would
    be dumped by ovs-ofctl tool 
    * action does not contain "action="
    * whitespace formatting not included

    :return: a dictionary of the original string parsed using ofp.py
    """
    buf_dict = {
        'info' : "cookie=0x95721583",
        'match' : "arp",
        'actions' : "1"
    }
    buf_dict[section_type] = string

    # ofpflow format: <infokv>, <matchkvstring> actions=<actionstring>\n
    buffer = (
            buf_dict['info'] + ', ' + 
            buf_dict['match'] + ' actions=' + 
            buf_dict['actions']
        )
    
    try:
        ofp = OFPFlow.from_string(buffer)
        dict = ofp.dict()
    except:
        raise ValueError("invalid OFPFlow syntax: ", string)
    
    return dict[section_type]
