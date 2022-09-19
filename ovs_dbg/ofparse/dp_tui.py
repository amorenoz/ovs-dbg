from dataclasses import dataclass
from functools import lru_cache

from typing import Type

from textual.widgets import TreeControl, TreeClick, TreeNode, NodeID, ScrollView
from textual.reactive import Reactive
from textual.app import App
from textual.driver import Driver
from rich.console import RenderableType
from rich.text import Text
from textual import events

from ovs.flow.odp import ODPFlow
from ovs_dbg.ofparse.dp_tree import FlowTree, FlowElem
from ovs_dbg.ofparse.console import ConsoleFormatter, ConsoleBuffer
from ovs_dbg.ofparse.process import FlowProcessor

@dataclass
class FlowEntry:
    flow_elem: FlowElem

#class FileClick(Message, bubble=True):
#    def __init__(self, sender: MessageTarget, flow: ODPFlow) -> None:
#        self.flow = flow
#        super().__init__(sender)

class IFlowTree(TreeControl[FlowEntry]):
    def __init__(self, flow_tree:FlowTree, formatter:ConsoleFormatter) -> None:
        data = FlowEntry(flow_tree.root)
        self.formatter = formatter
        super().__init__(label="root", name="Flow Tree", data=data)
        self.root.tree.guide_style = "black"

    has_focus: Reactive[bool] = Reactive(False)

    def on_focus(self) -> None:
        self.has_focus = True

    def on_blur(self) -> None:
        self.has_focus = False

    def render_node(self, node: TreeNode[FlowEntry]) -> RenderableType:
        return self.render_tree_label(
            node,
            node.expanded,
            node.is_cursor,
            node.id == self.hover_node,
            self.has_focus,
        )

    @lru_cache(maxsize=1024 * 1024 * 4)
    def render_tree_label(
        self,
        node: TreeNode[FlowEntry],
        expanded: bool,
        is_cursor: bool,
        is_hover: bool,
        has_focus: bool,
    ) -> RenderableType:

        meta = {
            "@click": f"click_label({node.id})",
            "tree_node": node.id,
            "cursor": node.is_cursor,
        }
        #self.console.log("rendering {}".format(node.id))
        elem = node.data.flow_elem
        if len(elem.children) == 0:
            icon = "📄"
        else:
            icon = "📂" if expanded else "📁"

        if elem.is_root:
            return Text(f"{icon} ") + "Datapath Flows"

        buf = ConsoleBuffer(Text())
        self.formatter.format_flow(buf, elem.flow, None)

        if is_hover:
            buf.text.stylize("underline")

        if is_cursor and has_focus:
            buf.text.stylize("reverse")

        icon_label = Text(f"{icon}") + buf.text
        icon_label.apply_meta(meta)
        return icon_label

    async def on_mount(self, event: events.Mount) -> None:
        await self.load_subflows(self.root)

    async def load_subflows(self, node: TreeNode[FlowEntry]):
        for elem in node.data.flow_elem.children:
            await node.add(elem.flow.orig, FlowEntry(elem))

        node.loaded = True
        await node.expand()
        self.refresh()

    async def handle_tree_click(self, message: TreeClick[FlowEntry]) -> None:
        elem = message.node.data.flow_elem
#        if len(elem.children) == 0:
#            await self.emit(FileClick(self, dir_entry.path))
#        else:
        if not message.node.loaded:
            await self.load_subflows(message.node)
            await message.node.expand()
        else:
            await message.node.toggle()

class FlowApp(App):
    def __init__(
        self,
        screen: bool = True,
        title: str = "Textual Application",
        log: str = "",
        log_verbosity: int = 1,
        driver_class: Type[Driver] | None = None,
        opts: dict = {}
    ):
        super().__init__(screen=screen, driver_class=driver_class)
        self.opts = opts
        ofconsole = ConsoleFormatter(self.opts)
        ofconsole.console.print("Processing...")
        processor = ITreeProcessor(self.opts, ODPFlow)
        processor.process()
        ofconsole.console.print("... Done!")
        self.itree = IFlowTree(processor.tree, ofconsole)

    async def on_load(self) -> None:
        await self.bind("q", "quit", "Quit")
        await self.bind("down", "key_down", "Down")
        await self.bind("up", "key_up", "Up")

    async def on_mount(self) -> None:
        await self.view.dock(ScrollView(self.itree), edge="left",
                             name="flowtree")
        # In this a scroll view for the code and a directory tree

class ITreeProcessor(FlowProcessor):
    def __init__(self, opts, factory):
        super().__init__(opts, factory)

    def start_file(self, name, filename):
        self.tree = FlowTree()

    def process_flow(self, flow, name):
        self.tree.add(flow)

    def process(self):
        super().process(False)

    def stop_file(self, name, filename):
        self.tree.build()
        #self.data[name] = self.tree

