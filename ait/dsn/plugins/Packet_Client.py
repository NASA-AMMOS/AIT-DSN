from ait.core.server.plugins import Plugin
from ait.core import log


class Packet_Client(Plugin):

    def __init__(self, inputs=None, outputs=None, zmq_args=None, **kwargs):
        super().__init__(inputs, outputs, zmq_args)
        # Anything initalized here will be available for the life of the plugin
        # and whenever process is triggered.
        # extra arguments from the yaml are inside **kwargs;
        # you can also specify the actual keyword to catch
        self.nice = "nice data"
        return
   
    def process(self, some_data, topic=None):
        # This runs any time something gets published onto a topic
        # you specified as an input. In my branch, you can publish
        # and subscribe to arbitrary topic names

        # You'll be receiving from TCP_Forward -> DeSyncByte -> Packet_Client
        processed_data = some_data[::-1]
        log.error(f"Packet Plugin {self.nice}: { some_data}")
        # Publishes to whoever set you as their input
        # You can publish to an arbitrary topic, but you might not need to.
        self.publish(processed_data)
