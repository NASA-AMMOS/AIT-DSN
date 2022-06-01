from ait.core.server.plugins import Plugin

class create_CLTU(Plugin):
    '''
    Adds CLTU start and tail bytes to incoming data (frames)
    '''

    def __init__(self, inputs=None, outputs=None, write_to_file = False, zmq_args=None, command_subscriber=None):
        super().__init__(inputs, outputs, zmq_args)
        self.CLTU_start = bytearray(b'\xEB\x90')
        self.CLTU_tail = bytearray(b'\xC5\xC5\xC5\xC5\xC5\xC5\xC5\x79')

    def process(self, input_data, topic=None):
        CLTU_bytearray = self.CLTU_start + input_data + self.CLTU_tail
        self.publish(CLTU_bytearray)