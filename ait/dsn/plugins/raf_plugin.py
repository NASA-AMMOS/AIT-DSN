"""
A plugin which creates an RAF connection with the DSN.
Frames received via the RAF connection are sent to the output stream
"""
import time
import ait
from ait.dsn.sle import RAF
from ait.core.server.plugins import Plugin

class RAFPlugin(Plugin):
    """
    A plugin which creates a RAF instance using the SLE parameters specified in config.yaml.
    All received frames are published to the output topic.
    """
    def __init__(self, inputs=None, outputs=None, zmq_args=None):
        super().__init__(inputs, outputs, zmq_args)
        self.raf_object = RAF()
        self.raf_object._handlers['AnnotatedFrame']=[self._transfer_data_invoc_handler]
        self.raf_object.connect()
        time.sleep(2)
        self.raf_object.bind()
        time.sleep(2)
        self.raf_object.start(None, None)
        time.sleep(2)

    def process(self, input_data, topic = None):
        pass

    def __del__(self):
        self.raf_object.stop()
        self.raf_object.unbind()
        self.raf_object.disconnect()

    def _transfer_data_invoc_handler(self, pdu):
        """"""
        frame = pdu.getComponent()
        if "data" in frame and frame["data"].isValue:
            tm_data = frame["data"].asOctets()
        else:
            err = (
                "RafTransferBuffer received but data cannot be located. "
                "Skipping further processing of this PDU ..."
            )
            ait.core.log.info(err)
            return

        self.publish(tm_data)