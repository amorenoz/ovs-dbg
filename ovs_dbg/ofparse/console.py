""" This module defines console formatting
"""

import colorsys
import contextlib
import itertools
import sys
import zlib
from rich.console import Console
from rich.text import Text
from rich.style import Style
from rich.color import Color

from ovs_dbg.ofparse.format import FlowFormatter, FlowBuffer, FlowStyle


class ConsoleBuffer(FlowBuffer):
    """ConsoleBuffer implements FlowBuffer to provide console-based text
    formatting based on rich.Text

    Append functions accept a rich.Style

    Args:
        rtext(rich.Text): Optional; text instance to reuse
    """

    def __init__(self, rtext):
        self._text = rtext or Text()

    @property
    def text(self):
        return self._text

    def _append(self, string, style):
        """Append to internal text"""
        return self._text.append(string, style)

    def append_key(self, kv, style):
        """Append a key
        Args:
            kv (KeyValue): the KeyValue instance to append
            style (rich.Style): the style to use
        """
        return self._append(kv.meta.kstring, style)

    def append_delim(self, kv, style):
        """Append a delimiter
        Args:
            kv (KeyValue): the KeyValue instance to append
            style (rich.Style): the style to use
        """
        return self._append(kv.meta.delim, style)

    def append_end_delim(self, kv, style):
        """Append an end delimiter
        Args:
            kv (KeyValue): the KeyValue instance to append
            style (rich.Style): the style to use
        """
        return self._append(kv.meta.end_delim, style)

    def append_value(self, kv, style):
        """Append a value
        Args:
            kv (KeyValue): the KeyValue instance to append
            style (rich.Style): the style to use
        """
        return self._append(kv.meta.vstring, style)

    def append_extra(self, extra, style):
        """Append extra string
        Args:
            kv (KeyValue): the KeyValue instance to append
            style (rich.Style): the style to use
        """
        return self._append(extra, style)


class ConsoleFormatter(FlowFormatter):
    """
    Args:
        console (rich.Console): Optional, an existing console to use
        max_value_len (int): Optional; max length of the printed values
        kwargs (dict): Optional; Extra arguments to be passed down to
            rich.console.Console()
    """

    def __init__(self, opts=None, console=None, **kwargs):
        super(ConsoleFormatter, self).__init__()
        style = self.style_from_opts(opts)
        self.console = console or Console(no_color=(style is None), **kwargs)
        self.style = style or FlowStyle()

    def style_from_opts(self, opts):
        return self._style_from_opts(opts, "console", Style)

    def print_flow(self, flow, highlighted=None):
        """
        Prints a flow to the console

        Args:
            flow (ovs_dbg.OFPFlow): the flow to print
            style (dict): Optional; style dictionary to use
            highlighted (list): Optional; list of KeyValues to highlight
        """

        buf = ConsoleBuffer(Text())
        self.format_flow(buf, flow, highlighted)
        self.console.print(buf.text)

    def format_flow(self, buf, flow, highlighted=None):
        """
        Formats the flow into the provided buffer as a rich.Text

        Args:
            buf (FlowBuffer): the flow buffer to append to
            flow (ovs_dbg.OFPFlow): the flow to format
            style (FlowStyle): Optional; style object to use
            highlighted (list): Optional; list of KeyValues to highlight
        """
        return super(ConsoleFormatter, self).format_flow(
            buf, flow, self.style, highlighted
        )


def hash_pallete(hue, saturation, value):
    """Generates a color pallete with the cartesian product
    of the hsv values provided and returns a callable that assigns a color for
    each value hash
    """
    HSV_tuples = itertools.product(hue, saturation, value)
    RGB_tuples = map(lambda x: colorsys.hsv_to_rgb(*x), HSV_tuples)
    styles = [
        Style(color=Color.from_rgb(r * 255, g * 255, b * 255)) for r, g, b in RGB_tuples
    ]

    def get_style(string):
        hash_val = zlib.crc32(bytes(str(string), "utf-8"))
        print(hash_val)
        print(hash_val % len(styles))
        print(len(styles))
        return styles[hash_val % len(styles)]

    return get_style


def print_context(console, opts):
    """
    Returns a printing context

    Args:
        console: The console to print
        paged (bool): Wheter to page the output
        style (bool): Whether to force the use of styled pager
    """
    if opts.get("paged"):
        # Internally pydoc's pager library is used which returns a
        # plain pager if both stdin and stdout are not tty devices
        #
        # Workaround that limitation if only stdin is not a tty (e.g
        # data is piped to us through stdin)
        if not sys.stdin.isatty() and sys.stdout.isatty():
            setattr(sys.stdin, "isatty", lambda: True)

        with_style = opts.get("style") is not None

        return console.pager(styles=with_style)

    return contextlib.nullcontext()
