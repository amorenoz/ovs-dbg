class TreeElem:
    """Element in the tree
    Args:
        children (list[TreeElem]): Optional, list of children
        is_root (bool): Optional; whether this is the root elemen
    """

    def __init__(self, children=None, is_root=False):
        self.children = children or list()
        self.is_root = is_root

    def append(self, child):
        self.children.append(child)


class FlowElem(TreeElem):
    """An element that contains a flow
    Args:
        flow (Flow): The flow that this element contains
        children (list[TreeElem]): Optional, list of children
        is_root (bool): Optional; whether this is the root elemen
    """

    def __init__(self, flow, children=None, is_root=False):
        self.flow = flow
        super(FlowElem, self).__init__(children, is_root)

    def evaluate_any(self, filter):
        """Evaluate the filter on the element and all its children
        Args:
            filter(OFFilter): the filter to evaluate

        Returns:
            True if ANY of the flows (including self and children) evaluates
            true
        """
        if filter.evaluate(self.flow):
            return True

        return any([child.evaluate_any(filter) for child in self.children])


class FlowTree:
    """
    A Flow tree is a a class that processes datapath flows into a tree based
    on recirculation ids

    Args:
        flows (list[ODPFlow]): Optional, initial list of flows
        root (TreeElem): Optional, root of the tree.
    """

    def __init__(self, flows=None, root=TreeElem(is_root=True)):
        self._flows = {}
        self.root = root
        if flows:
            for flow in flows:
                self.add(flow)

    def add(self, flow):
        """Add a flow"""
        rid = flow.match.get("recirc_id") or 0
        if not self._flows.get(rid):
            self._flows[rid] = list()
        self._flows[rid].append(flow)

    def build(self):
        """Build the flow tree."""
        self._build(self.root, 0)

    def traverse(self, callback):
        """Traverses the tree calling callback on each element
        callback: callable that accepts two TreeElem, the current one being
            traversed and its parent
            func callback(elem, parent):
                ...
            Note parent can be None if it's the first element
        """
        self._traverse(self.root, None, callback)

    def _traverse(self, elem, parent, callback):
        callback(elem, parent)

        for child in elem.children:
            self._traverse(child, elem, callback)

    def _build(self, parent, recirc):
        """
        Build the subtree starting at a specific recirc_id. Recursive function.
        Args:
            parent (TreeElem): parent of the (sub)tree
            recirc(int): the recirc_id subtree to build
        """
        flows = self._flows.get(recirc)
        if not flows:
            return
        for flow in sorted(
            flows, key=lambda x: x.info.get("packets") or 0, reverse=True
        ):
            next_recircs = self._get_next_recirc(flow)

            elem = self._new_elem(flow, parent)
            parent.append(elem)

            for next_recirc in next_recircs:
                self._build(elem, next_recirc)

    def _get_next_recirc(self, flow):
        """Get the next recirc_ids from a Flow.

        The recirc_id is obtained from actions such as recirc, but also
        complex actions such as check_pkt_len and sample
        Args:
            flow (ODPFlow): flow to get the recirc_id from.
        Returns:
            set of next recirculation ids.
        """
        # Helper function to find a recirc in a dictionary of actions.
        def find_in_dict(actions_dict):
            recircs = []
            for action, value in actions_dict.items():
                if action == "recirc":
                    recircs.append(value)
                elif action == "check_pkt_len":
                    recircs.extend(find_in_dict(value.get("gt")))
                    recircs.extend(find_in_dict(value.get("le")))
                elif action == "clone":
                    recircs.extend(find_in_dict(value))
                elif action == "sample":
                    recircs.extend(find_in_dict(value.get("actions")))
            return recircs

        recircs = []
        for actions in flow.actions:
            recircs.extend(find_in_dict(actions))

        return set(recircs)

    def _new_elem(self, flow, _):
        """Creates a new TreeElem
        Default implementation is to create a FlowElem. Derived classes can
        override this method to return any derived TreeElem
        """
        return FlowElem(flow)

    def filter(self, filter):
        """Removes the first level subtrees if none of its sub-elements match
        the filter
        Args:
            filter(OFFilter): filter to apply
        """
        to_remove = list()
        for l0 in self.root.children:
            passes = l0.evaluate_any(filter)
            if not passes:
                to_remove.append(l0)
        for elem in to_remove:
            self.root.children.remove(elem)
