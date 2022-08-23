"""
A plugin which applies BCH codes to incoming data and publishes the result.
"""

import math
from ait.core.server.plugins import Plugin
from ait.dsn.bch.bch import BCH

class BCHPlugin(Plugin):
    """
    Applies BCH codes (per the CCSDS spec) to incoming data and publishes the result.

    The input will normally be TC frames (either with or without SDLS).
    The output will be the same TC frames, but with additional BCH code block bytes.
    """

    def __init__(self, inputs=None, outputs=None, zmq_args=None):
        super().__init__(inputs, outputs, zmq_args)

    def process(self, input_data, topic=None):
        number_of_chunks = math.floor(len(input_data)/7)
        remainder_bytes = len(input_data) % 7
        output_bytes = bytearray()

        for chunk_number in range(number_of_chunks):
            beginning_index = chunk_number*7
            chunk = input_data[beginning_index:beginning_index+7]
            chunk_with_bch = BCH.generateBCH(chunk)
            output_bytes = output_bytes + chunk_with_bch

        # handle case where number of bytes is not evenly divisible by 7
        # CCSDS standard states add alternating 0/1 fill bits starting with 0
        if remainder_bytes != 0:
            number_of_filler_bytes = 7 - remainder_bytes
            filler_bytes = bytearray(b"\x55")*number_of_filler_bytes
            last_chunk = input_data[-remainder_bytes:] + filler_bytes
            last_chunk_with_bch = BCH.generateBCH(last_chunk)
            output_bytes = output_bytes + last_chunk_with_bch

        self.publish(output_bytes)
