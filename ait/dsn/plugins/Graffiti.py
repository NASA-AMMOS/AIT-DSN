import graphviz
import ait.core
from ait.core.server.plugins import Plugin
from gevent import Greenlet, sleep
from enum import Enum
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class Node_Type(Enum):
    UDP_SOCKET = 'circle'
    PLUGIN = 'box'
    TCP_SERVER = 'diamond'
    TCP_CLIENT = 'rectangle'
    NONE = 'oval'


@dataclass
class Node():
    name: str = ""
    inputs: list = field(default_factory=list)
    outputs: list = field(default_factory=list)
    label: str = ""
    node_type: Node_Type = Node_Type.NONE


class Graffiti(Plugin):
    def __init__(self, inputs=None, outputs=None,
                 zmq_args=None, popup=False, **kwargs):
        inputs = ["Graffiti"]
        super().__init__(inputs, outputs, zmq_args)

        self.graph = graphviz.Digraph('data-flow',
                                      comment='data-flow',
                                      strict=True)
        self.graph.ratio = 'expand'

        self.telem_api_stream = ait.config.get(
             "server.api-telemetry-streams", [])
        for stream in self.telem_api_stream:
            for item in self.telem_api_stream:
                self.graph.node("API: " + item,
                                "API: " + item,
                                shape='octagon')

        self.node_map = {}
        get_plugin_name = (lambda plugin: plugin['name'].split('.')[-1])
        get_stream_name = (lambda stream: stream['name'].split('.')[-1])

        plugins = ait.config.get('server.plugins', [])
        in_streams = ait.config.get('server.inbound-streams', [])
        out_streams = ait.config.get('server.outbound-streams', [])

        nodes = {}

        for plugin in plugins:
            t = Node_Type.PLUGIN
            plugin = plugin['plugin']
            pname = get_plugin_name(plugin)
            node = Node(name=pname,
                        inputs=plugin.get("inputs", []),
                        outputs=plugin.get("outputs", []),
                        label="",
                        node_type=t)
            nodes[pname] = node

        for stream in in_streams:
            t = Node_Type.UDP_SOCKET
            stream = stream['stream']
            sname = get_stream_name(stream)
            node = Node(name=sname,
                        inputs=stream.get("inputs", []),
                        outputs=stream.get("outputs", []),
                        label="",
                        node_type=t)
            nodes[pname] = node

        for stream in out_streams:
            t = Node_Type.UDP_SOCKET
            stream = stream['stream']
            sname = get_stream_name(stream)
            node = Node(name=sname,
                        inputs=stream.get("inputs", []),
                        outputs=stream.get("outputs", []),
                        label="",
                        node_type=t)
            nodes[pname] = node

        for name, node in nodes.items():
            self.visit_node(node)

        self.graph.render(directory='data-flow', view=popup)

    def visit_node(self, node):
        label = node.label
        self.graph.node(node.name, node.name +
                        "\n\n" + label,
                        shape=node.node_type.value)

        for target in node.inputs:
            if isinstance(target, tuple):
                target, label = target
                label = str(label)
            else:
                label = None
            target = str(target)
            self.graph.edge(target, node.name, label)

        for target in node.outputs:
            if isinstance(target, tuple):
                target, label = target
                label = str(label)
            else:
                label = None
            target = str(target)
            self.graph.edge(node.name, target, label)

    def process(self, node, topic):
        self.visit_node(node)
        self.graph.render(directory='data-flow', view=False)


class Graphable(ABC):

    def __init__(self, name="Missing Name!", delay=1, graffiti_object=None):
        self.self_name = self.__class__.__name__
        self.graffiti_object = graffiti_object
        self.delay = delay

        if self.graffiti_object:
            method = self.graffiti_direct
        else:
            method = self.graffiti_via_plugin

        method()

    def graffiti_direct(self):
        nodes = self.graffiti()
        for node in nodes:
            self.graffiti_object.add_node()

    def graffiti_via_plugin(self):

        def recall():
            sleep(2)
            node_list = self.graffiti()
            for node in node_list:
                self.publish(node, 'Graffiti')

        Greenlet.spawn(recall)

    @abstractmethod
    def graffiti():
        pass
