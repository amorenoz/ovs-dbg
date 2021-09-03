""" Defines the Flow class
"""

from ovs_dbg.kv import KeyValue


class Section(object):
    """A section within a Flow

    Attributes:
        name (str): name of the section
        pos (int): position within the overall flow string
        string (str): section string
        data (list[KeyValue]): parsed data of the section
        is_list (bool): whether the key-values shall be expressed as a list
            (e.g: it allows repeated keys)
    """

    def __init__(self, name, pos, string, data, is_list=False):
        self.name = name
        self.pos = pos
        self.string = string
        self.data = data
        self.is_list = is_list

    def __str__(self):
        return "{} (at {}): {}".format(self.name, self.pos, self.string)

    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, self)

    def dict(self):
        return {self.name: self.format_data()}

    def format_data(self):
        if self.is_list:
            return [{item.key: item.value} for item in self.data]
        else:
            return {item.key: item.value for item in self.data}


class Flow(object):
    """The Flow class is a base class for other types of concrete flows
    (such as OFproto Flows or DPIF Flows)

    For each section provided, the object will have the following attributes
    {section} will return the sections data in a formatted way
    {section}_kv will return the sections data as a list of KeyValues

    Args:
        sections (list[Section]): list of sections that comprise the flow
        orig (str): Original flow string
        id (Any): Identifier
    """

    def __init__(self, sections, orig="", id=None):
        self._sections = sections
        self._orig = orig
        self._id = id
        for section in sections:
            setattr(self, section.name, self.section(section.name).format_data())
            setattr(self, "{}_kv".format(section.name), self.section(section.name).data)

    def section(self, name):
        """Return the section by name"""
        return next((sect for sect in self._sections if sect.name == name), None)

    @property
    def id(self):
        """Return the Flow ID"""
        return self._id

    @property
    def sections(self):
        """Return the section by name"""
        return self._sections

    @property
    def orig(self):
        return self._orig

    def dict(self):
        """Returns the Flow information in a dictionary"""
        flow_dict = {"orig": self.orig}
        for section in self.sections:
            flow_dict.update(section.dict())

        return flow_dict
