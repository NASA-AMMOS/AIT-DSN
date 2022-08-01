from ait.core.server.plugins import Plugin
from ait.dsn.bch.bch import BCH
import math

class BCH_plugin(Plugin):
    '''
    Applies BCH codes to incoming data and publishes the result
    '''

    def __init__(self, inputs=None, outputs=None, zmq_args=None, command_subscriber=None):
        super().__init__(inputs, outputs, zmq_args)

    def process(self, input_data, topic=None):
        number_of_chunks = math.floor(len(input_data)/7)
        remainder_bytes = len(input_data) % 7
        output_bytes = bytearray()

        for chunk_number in range(number_of_chunks):
            beginning_index = chunk_number*7
            chunk = input_data[beginning_index:beginning_index+7]
            chunk_with_BCH = BCH.generateBCH(chunk)
            output_bytes = output_bytes + chunk_with_BCH

        # handle case where number of bytes is not evenly divisible by 7
        number_of_filler_bytes = 7 - remainder_bytes
        filler_bytes = bytearray(b'\x55')*number_of_filler_bytes #CCSDS standard states add alternating 0/1 fill bits starting with 0
        last_chunk = input_data[-remainder_bytes:] + filler_bytes
        last_chunk_with_BCH = BCH.generateBCH(last_chunk)
        output_bytes = output_bytes + last_chunk_with_BCH

        self.publish(output_bytes)
