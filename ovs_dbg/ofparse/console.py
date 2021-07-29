""" This module defines OFConsole class
"""

import sys
import contextlib
from rich.console import Console
from rich.text import Text
from rich.style import Style


class OFConsole:
    """OFConsole is a class capable of printing flows in a rich console format

    Args:
        console (rich.Console): Optional, an existing console to use
        max_value_len (int): Optional; max length of the printed values
        kwargs (dict): Optional; Extra arguments to be passed down to
            rich.console.Console()
    """

    default_style = {
        "key": Style(color="steel_blue"),
        "delim": Style(color="steel_blue"),
        "value": Style(color="medium_orchid"),
        "value.type.IPAddress": Style(color="green4"),
        "value.type.IPMask": Style(color="green4"),
        "value.type.EthMask": Style(color="green4"),
        "value.ct": Style(color="bright_black"),
        "value.ufid": Style(color="dark_red"),
        "value.clone": Style(color="bright_black"),
        "value.controller": Style(color="bright_black"),
        "flag": Style(color="slate_blue1"),
        "key.drop": Style(color="red"),
        "key.resubmit": Style(color="green3"),
        "key.output": Style(color="green3"),
    }

    def __init__(self, console=None, max_value_length=-1, **kwargs):
        self.console = console or Console(**kwargs)
        self.max_value_length = max_value_length

    def print_flow(self, flow, style=None):
        """
        Prints a flow to the console

        Args:
            flow (ovs_dbg.OFPFlow): the flow to print
            style (dict): Optional; style dictionary to use
        """

        text = Text()
        self.format_flow(flow, style, text)
        self.console.print(text)

    def format_flow(self, flow, style=None, text=None):
        """
        Formats the flow into the rich.Text

        Args:
            flow (ovs_dbg.OFPFlow): the flow to format
            style (dict): Optional; style dictionary to use
            text (rich.Text): Optional; the Text object to append to
        """
        text = text if text is not None else Text()

        last_printed_pos = 0
        for section in sorted(flow.sections, key=lambda x: x.pos):
            text.append(
                flow.orig[last_printed_pos : section.pos],
                Style(color="white"),
            )
            self.format_kv_list(section.data, section.string, style, text)
            last_printed_pos = section.pos + len(section.string)

    def format_info(self, flow, style=None, text=None):
        """
        Formats the flow information into the rich.Text

        Args:
            flow (ovs_dbg.OFPFlow): the flow to format
            style (dict): Optional; style dictionary to use
            text (rich.Text): Optional; the Text object to append to
        """
        self.format_kv_list(flow.info_kv, flow.meta.istring, style, text)

    def format_matches(self, flow, style=None, text=None):
        """
        Formats the flow information into the rich.Text

        Args:
            flow (ovs_dbg.OFPFlow): the flow to format
            style (dict): Optional; style dictionary to use
            text (rich.Text): Optional; the Text object to append to
        """
        self.format_kv_list(flow.match_kv, flow.meta.mstring, style, text)

    def format_actions(self, flow, style=None, text=None):
        """
        Formats the action into the rich.Text

        Args:
            flow (ovs_dbg.OFPFlow): the flow to format
            style (dict): Optional; style dictionary to use
            text (rich.Text): Optional; the Text object to append to
        """
        self.format_kv_list(flow.actions_kv, flow.meta.astring, style, text)

    def format_kv_list(self, kv_list, full_str, style=None, text=None):
        """
        Formats the list of KeyValues into the rich.Text

        Args:
            kv_list (list[KeyValue]): the flow to format
            full_str (str): the full string containing all k-v
            style (dict): Optional; style dictionary to use
            text (rich.Text): Optional; the Text object to append to
        """
        text = text if text is not None else Text()
        for i in range(len(kv_list)):
            kv = kv_list[i]
            written = self.format_kv(kv, style=style, text=text)

            # print kv separators
            end = kv_list[i + 1].meta.kpos if i < (len(kv_list) - 1) else len(full_str)
            text.append(
                full_str[(kv.meta.kpos + written) : end].rstrip("\n\r"),
                style=Style(color="white"),
            )

    def format_kv(self, kv, style=None, text=None, highlighted=[]):
        """Format a KeyValue

        A formatted keyvalue has the following parts:
            {key}{delim}{value}[{delim}]

        The following keys are fetched in style dictionary to determine the
        style to use for the key section:
            - key.highlighted.{key} (if key is found in hightlighted)
            - key.highlighted (if key is found in hightlighted)
            - key.{key}
            - key

        The following keys are fetched in style dictionary to determine the
        style to use for the value section of a specific key:
            - value.highlighted.{key} (if key is found in hightlighted)
            - value.highlighted.type{value.__class__.__name__}
            - value.highlighted
                (if key is found in hightlighted)
            - value.{key}
            - value.type.{value.__class__.__name__}
            - value

        The following keys are fetched in style dictionary to determine the
        style to use for the delim section
            - delim

        Args:
            kv (KeyValue): The KeyValue to print
            text (rich.Text): Optional; Text instance to append the text to
            style (dict): The style dictionary
            highlighted(list): A list of keys that shall be highlighted

        Returns the number of printed characters
        """
        ret = 0
        text = text if text is not None else Text()
        styles = style or self.default_style
        meta = kv.meta
        key = meta.kstring

        if kv.value is True and not kv.meta.vstring:
            text.append(key, styles.get("flag"))
            return len(key)

        key_style_lookup = (
            ["key.highlighted.%s" % key, "key.highlighted"]
            if key in highlighted
            else []
        )
        key_style_lookup.extend(["key.%s" % key, "key"])
        key_style = next(styles.get(s) for s in key_style_lookup if styles.get(s))

        text.append(key, key_style)
        ret += len(key)

        if kv.meta.vstring:
            if kv.meta.delim not in ("\n", "\t", "\r", ""):
                text.append(kv.meta.delim, styles.get("delim"))
                ret += len(kv.meta.delim)

            value_style_lookup = (
                [
                    "value.highlighted.%s" % key,
                    "value.highlighted.type.%s" % kv.value.__class__.__name__,
                    "value.highlighted",
                ]
                if key in highlighted
                else []
            )
            value_style_lookup.extend(
                [
                    "value.%s" % key,
                    "value.type.%s" % kv.value.__class__.__name__,
                    "value",
                ]
            )
            value_style = next(
                styles.get(s) for s in value_style_lookup if styles.get(s)
            )

            if (
                self.max_value_length >= 0
                and len(kv.meta.vstring) > self.max_value_length
            ):
                value_str = kv.meta.vstring[0 : self.max_value_length] + "..."
            else:
                value_str = kv.meta.vstring

            text.append(value_str, style=value_style)
            ret += len(kv.meta.vstring)
        if meta.end_delim:
            text.append(meta.end_delim, styles.get("delim"))
            ret += len(kv.meta.end_delim)

        return ret


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
