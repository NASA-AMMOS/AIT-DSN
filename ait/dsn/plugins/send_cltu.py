"""
Creates a FCLTU instance and uploads any incoming CLTUs to the DSN via SLE
"""

import time
from ait.core.server.plugins import Plugin
import ait.core
from ait.dsn.sle import CLTU

class SendCLTU(Plugin):
    """
    Creates a FCLTU instance and uploads any incoming CLTUs to the DSN via SLE

    The input stream should consist of CLTUs (with appropriate start and tail sequences).
    """

    def __init__(self, inputs=None, outputs=None, zmq_args=None):
        super().__init__(inputs, outputs, zmq_args)
        self.cltu_manager = CLTU()
        self.cltu_manager.connect()
        time.sleep(2)
        self.cltu_manager.bind()
        time.sleep(2)
        self.cltu_manager.start()
        time.sleep(2)

    def process(self, input_data, topic=None):
        if self.cltu_manager._state == "ready":
            self.cltu_manager.upload_cltu(input_data)
            self.publish(input_data)
            ait.core.log.debug("uploaded CLTU")
        else:
            ait.core.log.error("CLTU Manager is not in ready state– check DSN connection")
        return input_data

    def __del__(self):
        self.cltu_manager.stop()
        self.cltu_manager.unbind()
        self.cltu_manager.disconnect()
