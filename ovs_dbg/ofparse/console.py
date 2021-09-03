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

    default_style = Style(color="white")

    default_style_obj = FlowStyle(
        {
            "key": Style(color="#B0C4DE"),
            "value": Style(color="#B0C4DE"),
            "delim": Style(color="#B0C4DE"),
            "value.type.IPAddress": Style(color="#008700"),
            "value.type.IPMask": Style(color="#008700"),
            "value.type.EthMask": Style(color="#008700"),
            "value.ct": Style(color="bright_black"),
            "value.ufid": Style(color="#870000"),
            "value.clone": Style(color="bright_black"),
            "value.controller": Style(color="bright_black"),
            "flag": Style(color="#875fff"),
            "key.drop": Style(color="red"),
            "key.resubmit": Style(color="#00d700"),
            "key.output": Style(color="#00d700"),
            "key.highlighted": Style(color="#f20905", underline=True),
            "value.highlighted": Style(color="#f20905", underline=True),
            "delim.highlighted": Style(color="#f20905", underline=True),
        }
    )

    def __init__(self, console=None, style_obj=None, default_style=None, **kwargs):
        super(ConsoleFormatter, self).__init__()
        self.console = console or Console(**kwargs)

    def print_flow(self, flow, style=None):
        """
        Prints a flow to the console

        Args:
            flow (ovs_dbg.OFPFlow): the flow to print
            style (dict): Optional; style dictionary to use
        """

        buf = ConsoleBuffer(Text())
        self.format_flow(buf, flow, style)
        self.console.print(buf.text)

    def format_flow(self, buf, flow, style=None):
        """
        Formats the flow into the rich.Text

        Args:
            flow (ovs_dbg.OFPFlow): the flow to format
            style (dict): Optional; style dictionary to use
            text (rich.Text): Optional; the Text object to append to
        """
        last_printed_pos = 0
        style_obj = style or self.default_style_obj

        for section in sorted(flow.sections, key=lambda x: x.pos):
            buf.append_extra(
                flow.orig[last_printed_pos : section.pos],
                style=style_obj.get("extra") or self.default_style,
            )
            self.format_kv_list(
                buf, section.data, section.string, style_obj, self.default_style
            )
            last_printed_pos = section.pos + len(section.string)


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


def print_context(console, paged=False, styles=True):
    """
    Returns a printing context

    Args:
        console: The console to print
        paged (bool): Wheter to page the output
        style (bool): Whether to force the use of styled pager
    """
    if paged:
        # Internally pydoc's pager library is used which returns a
        # plain pager if both stdin and stdout are not tty devices
        #
        # Workaround that limitation if only stdin is not a tty (e.g
        # data is piped to us through stdin)
        if not sys.stdin.isatty() and sys.stdout.isatty():
            setattr(sys.stdin, "isatty", lambda: True)

        return console.pager(styles=styles)

    return contextlib.nullcontext()
