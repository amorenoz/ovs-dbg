""" Defines common flow processing functionality
"""
import sys
import json
import click

from ovs.flow.decoders import FlowEncoder
from ovs_dbg.ofparse.console import (
    ConsoleFormatter,
    print_context,
    heat_pallete,
    file_header,
)


class FlowProcessor(object):
    """Base class for file-based Flow processing. It is able to create flows
    from strings found in a file (or stdin).

    The process of parsing the flows is extendable in many ways by deriving
    this class.

    When process() is called, the base class will:
        - call self.start_file() for each new file that get's processed
        - call self.create_flow() for each flow line
        - apply the filter defined in opts if provided (can be optionally
            disabled)
        - call self.process_flow() for after the flow has been filtered
        - call self.stop_file() after the file has been processed entirely

    In the case of stdin, the filename and file alias is 'stdin'

    Args:
        opts (dict): Options dictionary
        factory (object): Factory object to use to build flows
            The factory object must have a function as:
                from_string(line, idx)
    """

    def __init__(self, opts, factory):
        self.opts = opts
        self.factory = factory

    # Methods that must be implemented by derived classes
    def init(self):
        """Called before the flow processing begins"""
        pass

    def start_file(self, alias, filename):
        """Called before the processing of a file begins
        Args:
            alias(str): The alias name of the filename
            filename(str): The filename string
        """
        pass

    def create_flow(self, line, idx):
        """Called for each line in the file
        Args:
            line(str): The flow line
            idx(int): The line index

        Returns a Flow
        """
        return self.factory(line, idx)

    def process_flow(self, flow, name):
        """Called for built flow (after filtering)
        Args:
            flow(Flow): The flow created by create_flow
            name(str): The name of the file from which the flow comes
        """
        pass

    def stop_file(self, alias, filename):
        """Called after the processing of a file ends
        Args:
            alias(str): The alias name of the filename
            filename(str): The filename string
        """
        pass

    def end(self):
        """Called after the processing ends"""
        pass

    def process(self, do_filter=True):
        idx = 0
        filenames = self.opts.get("filename")
        filt = self.opts.get("filter") if do_filter else None
        self.init()
        if filenames:
            for alias, filename in filenames:
                try:
                    with open(filename) as f:
                        self.start_file(alias, filename)
                        for line in f:
                            flow = self.create_flow(line, idx)
                            idx += 1
                            if not flow or (filt and not filt.evaluate(flow)):
                                continue
                            self.process_flow(flow, alias)
                        self.stop_file(alias, filename)
                except IOError as e:
                    raise click.BadParameter(
                        "Failed to read from file {} ({}): {}".format(
                            filename, e.errno, e.strerror
                        )
                    )
        else:
            data = sys.stdin.read()
            self.start_file("stdin", "stdin")
            for line in data.split("\n"):
                line = line.strip()
                if line:
                    flow = self.create_flow(line, idx)
                    idx += 1
                    if (
                        not flow
                        or not getattr(flow, "_sections", None)
                        or (filt and not filt.evaluate(flow))
                    ):
                        continue
                    self.process_flow(flow, "stdin")
            self.stop_file("stdin", "stdin")
        self.end()


class JSONProcessor(FlowProcessor):
    """A generic JsonProcessor"""

    def __init__(self, opts, factory):
        super().__init__(opts, factory)
        self.flows = dict()

    def start_file(self, name, filename):
        self.flows_list = list()

    def stop_file(self, name, filename):
        self.flows[name] = self.flows_list

    def process_flow(self, flow, name):
        self.flows_list.append(flow)

    def json_string(self):
        if len(self.flows.keys()) > 1:
            return json.dumps(
                [
                    {"name": name, "flows": [flow.dict() for flow in flows]}
                    for name, flows in self.flows.items()
                ],
                indent=4,
                cls=FlowEncoder,
            )
        return json.dumps(
            [flow.dict() for flow in self.flows_list],
            indent=4,
            cls=FlowEncoder,
        )


class ConsoleProcessor(FlowProcessor):
    """A generic Console Processor that prints flows into the console"""

    def __init__(self, opts, factory, heat_map=[]):
        super().__init__(opts, factory)
        self.heat_map = heat_map
        self.console = ConsoleFormatter(opts)
        self.flows = dict()

    def start_file(self, name, filename):
        self.flows_list = list()

    def stop_file(self, name, filename):
        self.flows[name] = self.flows_list

    def process_flow(self, flow, name):
        self.flows_list.append(flow)

    def print(self):
        with print_context(self.console.console, self.opts):
            for name, flows in self.flows.items():
                self.console.console.print("\n")
                self.console.console.print(file_header(name))

                if len(self.heat_map) > 0 and len(self.flows) > 0:
                    for field in self.heat_map:
                        values = [f.info.get(field) or 0 for f in flows]
                        self.console.style.set_value_style(
                            field, heat_pallete(min(values), max(values))
                        )

                for flow in flows:
                    high = None
                    if self.opts.get("highlight"):
                        result = self.opts.get("highlight").evaluate(flow)
                        if result:
                            high = result.kv
                    self.console.print_flow(flow, high)
