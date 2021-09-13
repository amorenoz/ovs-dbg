""" This module defines generic formatting classes
"""


class FlowStyle:
    """
    A FlowStyle determines the KVStyle to use for each key value in a flow

    Styles are internally represented by a dictionary.
    In order to determine the style for a "key", the following items in the
    dictionary are fetched:
        - key.highlighted.{key} (if key is found in hightlighted)
        - key.highlighted (if key is found in hightlighted)
        - key.{key}
        - key
        - default

    In order to determine the style for a "value", the following items in the
    dictionary are fetched:
        - value.highlighted.{key} (if key is found in hightlighted)
        - value.highlighted.type{value.__class__.__name__}
        - value.highlighted
        (if key is found in hightlighted)
        - value.{key}
        - value.type.{value.__class__.__name__}
        - value
        - default

    Additionally, the following style items can be defined:
        - delim: for delimiters
        - delim.highlighted: for delimiters of highlighted key-values
    """

    def __init__(self, initial=None):
        self._styles = initial if initial is not None else dict()

    def set_flag_style(self, kvstyle):
        self._styles["flag"] = kvstyle

    def set_delim_style(self, kvstyle, highlighted=False):
        if highlighted:
            self._styles["delim.highlighted"] = kvstyle
        else:
            self._styles["delim"] = kvstyle

    def set_default_key_style(self, kvstyle):
        self._styles["key"] = kvstyle

    def set_default_value_style(self, kvstyle):
        self._styles["value"] = kvstyle

    def set_key_style(self, key, kvstyle, highlighted=False):
        if highlighted:
            self._styles["key.highlighted.{}".format(key)] = kvstyle
        else:
            self._styles["key.{}".format(key)] = kvstyle

    def set_value_style(self, key, kvstyle, highlighted=None):
        if highlighted:
            self._styles["value.highlighted.{}".format(key)] = kvstyle
        else:
            self._styles["value.{}".format(key)] = kvstyle

    def set_value_type_style(self, name, kvstyle, highlighted=None):
        if highlighted:
            self._styles["value.highlighted.type.{}".format(name)] = kvstyle
        else:
            self._styles["value.type.{}".format(name)] = kvstyle

    def get(self, key):
        return self._styles.get(key)

    def get_delim_style(self, highlighted=False):
        delim_style_lookup = ["delim.highlighted"] if highlighted else []
        delim_style_lookup.extend(["delim", "default"])
        return next(
            (self._styles.get(s) for s in delim_style_lookup if self._styles.get(s)),
            None,
        )

    def get_flag_style(self):
        return self._styles.get("flag") or self._styles.get("default")

    def get_key_style(self, kv, highlighted=False):
        key = kv.meta.kstring

        key_style_lookup = (
            ["key.highlighted.%s" % key, "key.highlighted"] if highlighted else []
        )
        key_style_lookup.extend(["key.%s" % key, "key", "default"])

        style = next(
            (self._styles.get(s) for s in key_style_lookup if self._styles.get(s)),
            None,
        )
        if callable(style):
            return style(kv.meta.kstring)
        return style

    def get_value_style(self, kv, highlighted=False):
        key = kv.meta.kstring
        value_type = kv.value.__class__.__name__
        value_style_lookup = (
            [
                "value.highlighted.%s" % key,
                "value.highlighted.type.%s" % value_type,
                "value.highlighted",
            ]
            if highlighted
            else []
        )
        value_style_lookup.extend(
            [
                "value.%s" % key,
                "value.type.%s" % value_type,
                "value",
                "default",
            ]
        )

        style = next(
            (self._styles.get(s) for s in value_style_lookup if self._styles.get(s)),
            None,
        )
        if callable(style):
            return style(kv.meta.vstring)
        return style


class FlowFormatter:
    """FlowFormatter is a base class for Flow Formatters"""

    def __init__(self):
        self._highlighted = list()

    def _style_from_opts(self, opts, opts_key, style_constructor):
        """Create style object from options

        Args:
            opts (dict): Options dictionary
            opts_key (str): The options style key to extract (e.g: console or html)
            style_constructor(callable): A callable that creates a derived style object
        """
        if not opts or not opts.get("style"):
            return None

        section_name = ".".join(["styles", opts.get("style")])
        if section_name not in opts.get("config").sections():
            raise Exception("Style not present in config file")

        config = opts.get("config")[section_name]
        style = {}
        for key in config:
            (_, console, style_full_key) = key.partition(opts_key + ".")
            if not console:
                continue

            (style_key, _, prop) = style_full_key.rpartition(".")
            if not prop or not style_key:
                raise Exception("malformed style config: {}".format(key))

            if not style.get(style_key):
                style[style_key] = {}
            style[style_key][prop] = config[key]

        return FlowStyle({k: style_constructor(**v) for k, v in style.items()})

    def format_flow(self, buf, flow, style_obj=None, highlighted=None):
        """
        Formats the flow into the provided buffer

        Args:
            buf (FlowBuffer): the flow buffer to append to
            flow (ovs_dbg.OFPFlow): the flow to format
            style_obj (FlowStyle): Optional; style to use
            highlighted (list): Optional; list of KeyValues to highlight
        """
        last_printed_pos = 0
        style_obj = style_obj or FlowStyle()

        for section in sorted(flow.sections, key=lambda x: x.pos):
            buf.append_extra(
                flow.orig[last_printed_pos : section.pos],
                style=style_obj.get("default"),
            )
            self.format_kv_list(
                buf, section.data, section.string, style_obj, highlighted
            )
            last_printed_pos = section.pos + len(section.string)

    def format_kv_list(self, buf, kv_list, full_str, style_obj, highlighted):
        """
        Format a KeyValue List

        Args:
            buf (FlowBuffer): a FlowBuffer to append formatted KeyValues to
            kv_list (list[KeyValue]: the KeyValue list to format
            full_str (str): the full string containing all k-v
            style_obj (FlowStyle): a FlowStyle object to use
            highlighted (list): Optional; list of KeyValues to highlight
        """
        for i in range(len(kv_list)):
            kv = kv_list[i]
            written = self.format_kv(
                buf, kv, style_obj=style_obj, highlighted=highlighted
            )

            end = kv_list[i + 1].meta.kpos if i < (len(kv_list) - 1) else len(full_str)

            buf.append_extra(
                full_str[(kv.meta.kpos + written) : end].rstrip("\n\r"),
                style=style_obj.get("default"),
            )

    def format_kv(self, buf, kv, style_obj, highlighted=None):
        """Format a KeyValue

        A formatted keyvalue has the following parts:
            {key}{delim}{value}[{delim}]

        Args:
            buf (FlowBuffer): buffer to append the KeyValue to
            kv (KeyValue): The KeyValue to print
            style_obj (FlowStyle): The style object to use
            highlighted (list): Optional; list of KeyValues to highlight

        Returns the number of printed characters
        """
        ret = 0
        key = kv.meta.kstring
        is_highlighted = key in [k.key for k in highlighted] if highlighted else False

        key_style = style_obj.get_key_style(kv, is_highlighted)
        buf.append_key(kv, key_style)  # format value
        ret += len(key)

        if not kv.meta.vstring:
            return ret

        if kv.meta.delim not in ("\n", "\t", "\r", ""):
            buf.append_delim(kv, style_obj.get_delim_style(is_highlighted))
            ret += len(kv.meta.delim)

        value_style = style_obj.get_value_style(kv, is_highlighted)

        buf.append_value(kv, value_style)  # format value
        ret += len(kv.meta.vstring)

        if kv.meta.end_delim:
            buf.append_end_delim(kv, style_obj.get_delim_style(is_highlighted))
            ret += len(kv.meta.end_delim)

        return ret


class FlowBuffer:
    """A FlowBuffer is a base class for format buffers.
    Childs must implement the following methods:
        append_key(self, kv, style)
        append_value(self, kv, style)
        append_delim(self, delim, style)
        append_end_delim(self, delim, style)
        append_extra(self, extra, style)
    """

    def append_key(self, kv, style):
        """Append a key
        Args:
            kv (KeyValue): the KeyValue instance to append
            style (Any): the style to use
        """
        raise Exception("Not implemented")

    def append_delim(self, kv, style):
        """Append a delimiter
        Args:
            kv (KeyValue): the KeyValue instance to append
            style (Any): the style to use
        """
        raise Exception("Not implemented")

    def append_end_delim(self, kv, style):
        """Append an end delimiter
        Args:
            kv (KeyValue): the KeyValue instance to append
            style (Any): the style to use
        """
        raise Exception("Not implemented")

    def append_value(self, kv, style):
        """Append a value
        Args:
            kv (KeyValue): the KeyValue instance to append
            style (Any): the style to use
        """
        raise Exception("Not implemented")

    def append_extra(self, extra, style):
        """Append extra string
        Args:
            kv (KeyValue): the KeyValue instance to append
            style (Any): the style to use
        """
        raise Exception("Not implemented")
