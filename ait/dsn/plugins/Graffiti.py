import graphviz
import ait.core
from ait.core.server.plugins import Plugin
import pprint
from gevent import Greenlet, sleep
from enum import Enum

ready = False


def wait(callback):
    Greenlet.spawn(recall, callback)
    return


def recall(callback):
    if not Graffiti.ready:
        sleep(1)
        Graffiti.ready = True

    data = callback.graffiti()
    callback.publish(data, 'Graffiti')


class Node_Type(Enum):
    UDP_SOCKET = 'circle'
    PLUGIN = 'box'
    TCP_SERVER = 'diamond'
    TCP_CLIENT = 'rectangle'
    NONE = 'oval'


class Node():
    def __init__(self, name=None, inputs=[], outputs=[],
                 label=None, node_type=Node_Type.NONE):
        self.name = name
        self.inputs = inputs
        self.outputs = outputs
        self.label = label
        self.node_type = node_type


class Graffiti(Plugin):
    def __init__(self, inputs=None, outputs=None,
                 zmq_args=None, popup=False, **kwargs):

        self.graph = graphviz.Digraph('data-flow', comment='data-flow')

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

        self.graph.render(directory='data-flow', view=False)

    def visit_node(self, node):
        label = pprint.pformat(node.label, width=-1)
        self.graph.node(node.name, node.name +
                        "\n\n" + label,
                        shape=node.node_type.value)

        for target in node.inputs:
            target = str(target)
            self.graph.node(target, target)
            self.graph.edge(target, node.name)

        for target in node.outputs:
            target = str(target)
            self.graph.node(target, target)
            self.graph.edge(node.name, target)

    def process(self, data, topic, name, inputs=[], outputs=[],
                label=None, node_type=Node_Type.NONE):
        node = Node(name, inputs, outputs, label, node_type)
        self.visit_node(node)
        self.graph.render(directory='data-flow', view=False)
