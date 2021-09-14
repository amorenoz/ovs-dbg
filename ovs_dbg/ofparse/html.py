from ovs_dbg.ofparse.format import FlowFormatter, FlowBuffer, FlowStyle


class HTMLStyle(FlowStyle):
    """HTMLStyle defines a style for html-formatted flows

    Args:
        color(str): Optional; a string representing the CSS color to use
        anchor_gen(callable): Optional; a callable to be used to generate the
            href
    """

    def __init__(self, color=None, anchor_gen=None):
        self.color = color
        self.anchor_gen = anchor_gen


class HTMLBuffer(FlowBuffer):
    """HTMLBuffer implementes FlowBuffer to provide html-based flow formatting

    Each flow gets formatted as:
        <div><span>...</span></div>
    """

    def __init__(self):
        self._text = ""

    @property
    def text(self):
        return self._text

    def _append(self, string, color, href):
        """Append a key a string"""
        style = ' style="color:{}"'.format(color) if color else ""
        self._text += "<span{}>".format(style)
        if href:
            self._text += "<a href={}>".format(href)
        self._text += string
        if href:
            self._text += "</a>"
        self._text += "</span>"

    def append_key(self, kv, style):
        """Append a key
        Args:
            kv (KeyValue): the KeyValue instance to append
            style (HTMLStyle): the style to use
        """
        href = style.anchor_gen(kv) if (style and style.anchor_gen) else ""
        return self._append(kv.meta.kstring, style.color if style else "", href)

    def append_delim(self, kv, style):
        """Append a delimiter
        Args:
            kv (KeyValue): the KeyValue instance to append
            style (HTMLStyle): the style to use
        """
        href = style.anchor_gen(kv) if (style and style.anchor_gen) else ""
        return self._append(kv.meta.delim, style.color if style else "", href)

    def append_end_delim(self, kv, style):
        """Append an end delimiter
        Args:
            kv (KeyValue): the KeyValue instance to append
            style (HTMLStyle): the style to use
        """
        href = style.anchor_gen(kv) if (style and style.anchor_gen) else ""
        return self._append(kv.meta.end_delim, style.color if style else "", href)

    def append_value(self, kv, style):
        """Append a value
        Args:
            kv (KeyValue): the KeyValue instance to append
            style (HTMLStyle): the style to use
        """
        href = style.anchor_gen(kv) if (style and style.anchor_gen) else ""
        return self._append(kv.meta.vstring, style.color if style else "", href)

    def append_extra(self, extra, style):
        """Append extra string
        Args:
            kv (KeyValue): the KeyValue instance to append
            style (HTMLStyle): the style to use
        """
        return self._append(extra, style.color if style else "", "")


class HTMLFormatter(FlowFormatter):
    """
    Formts a flow in HTML Format
    """

    default_style_obj = FlowStyle(
        {
            "value.resubmit": HTMLStyle(
                anchor_gen=lambda x: "#table_{}".format(x.value["table"])
            ),
            "default": HTMLStyle(),
        }
    )

    def __init__(self, opts=None):
        super(HTMLFormatter, self).__init__()
        self.style = self._style_from_opts(opts, "html", HTMLStyle) or FlowStyle()
        self.style.set_value_style(
            "resubmit",
            HTMLStyle(
                self.style.get("value.resubmit"),
                anchor_gen=lambda x: "#table_{}".format(x.value["table"]),
            ),
        )

    def format_flow(self, buf, flow, highlighted=None):
        """
        Formats the flow into the provided buffer as a html object

        Args:
            buf (FlowBuffer): the flow buffer to append to
            flow (ovs_dbg.OFPFlow): the flow to format
            highlighted (list): Optional; list of KeyValues to highlight
        """
        return super(HTMLFormatter, self).format_flow(
            buf, flow, self.style, highlighted
        )
