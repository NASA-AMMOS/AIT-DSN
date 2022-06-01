from ait.core.server.plugins import Plugin
import ait.core
from ait.dsn.sle import CLTU
import time

class send_CLTU(Plugin):
    '''
    Creates a FCLTU instance and uploads any incoming CLTUs to the DSN via SLE
    '''

    def __init__(self, inputs=None, outputs=None, zmq_args=None, command_subscriber=None):
        super().__init__(inputs, outputs, zmq_args)
        self.CLTU_manager = CLTU()
        self.CLTU_manager.connect()
        time.sleep(2)
        self.CLTU_manager.bind()
        time.sleep(2)
        self.CLTU_manager.start()
        time.sleep(2)

    def process(self, input_data, topic=None):
        if self.CLTU_manager._state == "ready":
            self.CLTU_manager.upload_cltu(input_data)
            self.publish(input_data)
            ait.core.log.debug("uploaded CLTU")
        else:
            ait.core.log.error("CLTU Manager is not in ready state– check DSN connection")
        return input_data

    def __del__(self):
        self.CLTU_manager.stop()
        self.CLTU_manager.unbind()
        self.CLTU_manager.disconnect()
