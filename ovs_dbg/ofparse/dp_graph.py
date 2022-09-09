""" Defines a Datapath Graph based on graphviz
"""
import graphviz
from ovs.flow.filter import OFFilter


class DatapathGraph:
    """
    A DatapathGraph is a class that renders a set of datapath flows into
    graphviz graphs

    Args:
        flows(dict[int, list(Flow)]): Dictionary of lists of flows indexed by
            recirc_id
    """

    node_styles = {
        OFFilter("ct and (ct_state or ct_label or ct_mark)"): {
            "color": "#ff00ff"
        },
        OFFilter("ct_state or ct_label or ct_mark"): {"color": "#0000ff"},
        OFFilter("ct"): {"color": "#ff0000"},
    }

    def __init__(self, flows):
        self._flows = flows

        self._output_nodes = []
        self._graph = graphviz.Digraph(
            "DP flows", node_attr={"shape": "rectangle"}
        )
        self._graph.attr(compound="true")
        self._graph.attr(rankdir="LR")

        self._populate_graph()

    def source(self):
        """
        Return the graphviz source representation of the graph
        """
        return self._graph.source

    def pipe(self, *args, **kwargs):
        """
        Output the graph based on arguments given to graphviz.pipe
        """
        return self._graph.pipe(*args, **kwargs)

    @classmethod
    def recirc_cluster_name(cls, recirc_id):
        return "cluster_recirc_{}".format(hex(recirc_id))

    @classmethod
    def inport_cluster_name(cls, inport):
        return "cluster_inport_{}".format(inport)

    @classmethod
    def invis_node_name(cls, cluster_name):
        return "invis_{}".format(cluster_name)

    @classmethod
    def output_node_name(cls, port):
        return "output_{}".format(port)

    def _flow_node(self, flow, name):
        """
        Returns the dictionary of attributes of a graphviz node that represents
        the flow with a given name
        """
        summary = "Line: {} \n".format(flow.id)
        summary += "\n".join(
            [
                flow.section("info").string,
                ",".join(flow.match.keys()),
                "actions: "
                + ",".join(list(a.keys())[0] for a in flow.actions),
            ]
        )
        attr = (
            self.node_styles.get(
                next(
                    filter(lambda f: f.evaluate(flow), self.node_styles), None
                )
            )
            or {}
        )

        return {
            "name": name,
            "label": summary,
            "_attributes": attr,
            "fontsize": "8",
            "nojustify": "true",
            "URL": "#flow_{}".format(flow.id),
        }

    def _create_flow_cluster(self, cluster_name, label, flows, parent=None):
        """Create a flow cluster
        Args:
            cluster_name(str): the name of the new cluster
            label(str): the label of the subgraph
            flows([Flow]): list of flows to add to the cluster
            parent(Graph): Optional, another subgraph this one should be under
        """
        parent = parent or self._graph
        cluster = parent.subgraph(name=cluster_name, comment=label)

        with cluster as sg:
            sg.attr(rankdir="TB")
            sg.attr(ranksep="0.02")
            sg.attr(label=label)
            # Create an invisible node so that we can point to subgraphs
            invis = self.invis_node_name(cluster_name)
            sg.node(
                invis,
                color="white",
                len="0",
                shape="point",
                width="0",
                height="0",
            )
            previous = None
            for flow in flows:
                name = "Flow_{}".format(flow.id)
                sg.node(**self._flow_node(flow, name))
                # Connect to previous so that dot rendering places them one
                # after the other
                if previous:
                    sg.edge(previous, name, color="white")
                else:
                    sg.edge(invis, name, color="white", length="0")
                previous = name

                # determine next hop
                self._set_next_node(name, flow)

        return cluster

    def _set_next_node(self, name, flow):
        """
        Determine the next node and add edges to it
        """
        created = False

        for kv in flow.actions_kv:
            if kv.key == "check_pkt_len":
                for subname, subvalue in kv.value.get("gt").items():
                    created = self._set_next_node_action(
                        name, subname, subvalue
                    )
                for subname, subvalue in kv.value.get("le").items():
                    created = self._set_next_node_action(
                        name, subname, subvalue
                    )
            elif kv.key == "sample":
                for subname, subvalue in kv.value.get("actions").items():
                    created = self._set_next_node_action(
                        name, subname, subvalue
                    )
            else:
                created = self._set_next_node_action(name, kv.key, kv.value)

        if not created:
            # Add to a generic "End" if no other action was detected
            self._graph.edge(name, "end")

    def _set_next_node_action(self, name, action_name, action_obj):
        """
        Based on the action object, set the next node
        """
        if action_name == "recirc":
            cname = self.recirc_cluster_name(action_obj)
            self._graph.edge(
                name,
                self.invis_node_name(cname),
                lhead=cname,
                _attributes={"weight": "20"},
            )
            return True
        elif action_name == "output":
            port = action_obj.get("port")
            if port not in self._output_nodes:
                self._graph.node(
                    self.output_node_name(port),
                    shape="Msquare",
                    label="Port {}".format(port),
                    rank="sink",
                )
                self._output_nodes.append(port)
            self._graph.edge(
                name, self.output_node_name(port), _attributes={"weight": "1"}
            )
            return True
        elif action_name in ["drop", "userspace"]:
            if action_name not in self._output_nodes:
                self._graph.node(action_name, shape="Msquare", rank="sink")
                self._output_nodes.append(action_name)
                self._graph.edge(
                    name, action_name, _attributes={"weight": "1"}
                )
            return True
        return False

    def _populate_graph(self):
        """Populate the the internal graph"""

        self._graph.node("end", shape="Msquare")

        for recirc, flows in self._flows.items():
            if recirc == 0:
                # Deal with input ports
                flows_per_inport = {}
                free_flows = []
                for flow in flows:
                    port = flow.match.get("in_port")
                    if port:
                        if not flows_per_inport.get(port):
                            flows_per_inport[port] = list()
                        flows_per_inport[port].append(flow)
                    else:
                        free_flows.append(flow)

                # Build base graph with free flows
                cluster_name = self.recirc_cluster_name(recirc)
                label = "recirc {}".format(recirc)
                sg = self._create_flow_cluster(cluster_name, label, free_flows)

                # Íf there are free_flows, create a dummy inport port
                if free_flows:
                    self._graph.edge(
                        "start",
                        self.invis_node_name(self.recirc_cluster_name(0)),
                        lhead=self.recirc_cluster_name(0),
                    )
                    self._graph.node("start", shape="Mdiamond")

                for inport, flows in flows_per_inport.items():
                    # Build a subgraph per input port
                    cluster_name = self.inport_cluster_name(inport)
                    label = "input port: {}".format(inport)

                    with sg as parent:
                        self._create_flow_cluster(
                            cluster_name, label, flows, parent
                        )

                    # Make an Input node point to each subgraph
                    node_name = "input_{}".format(inport)
                    self._graph.node(
                        node_name,
                        shape="Mdiamond",
                        label="input port {}".format(inport),
                    )
                    self._graph.edge(
                        node_name,
                        self.invis_node_name(cluster_name),
                        lhead=cluster_name,
                    )

            else:
                cluster_name = self.recirc_cluster_name(recirc)
                label = "recirc {}".format(recirc)
                self._create_flow_cluster(cluster_name, label, flows)
