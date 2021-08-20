""" OVS Log parser
"""

import datetime


class OVSLog:
    """Parses and stores information of a OVS FLow.

    The logs have the following standard format:

    2016-03-08T02:10:01.155Z|01417|vlog|INFO|opened log file /var/log/openvswitch/ovs-vswitchd.log
    2016-03-08T02:20:05.425Z|01418|connmgr|INFO|br0<->unix: 1 flow_mods in the last 0 s (1 adds)
    2016-03-08T02:20:10.160Z|01419|connmgr|INFO|br0<->unix: 1 flow_mods in the last 0 s (1 deletes)
    2016-03-08T11:30:52.206Z|00013|fatal_signal|WARN|terminating with signal 15 (Terminated)

    Attributes:
        timestamp: the UTC time stamp
        sequence: the sequence number of this message
        module: the module in vlog that emitted this error
        level: the level of error
        message: the rest of the message
        raw_message: the raw string
    """

    time_format = "%Y-%m-%dT%H:%M:%S.%fZ"
    _fields = ["timestamp", "sequence", "module", "level", "message"]

    def __init__(self, string):
        """Constructor"""
        self.raw_string = string
        fields = string.split("|", 4)
        if len(fields) != len(self._fields):
            raise Exception("Not a valid OVS Flow: %s" & string)

        self.timestamp = datetime.datetime.strptime(fields[0], self.time_format)
        self.sequence = int(fields[1])
        self.module = fields[2]
        self.level = fields[3]
        self.message = fields[4].strip()
