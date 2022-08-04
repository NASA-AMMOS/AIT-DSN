"""
A plugin which adds CLTU start and tail bytes to incoming data
"""
from ait.core.server.plugins import Plugin

class CreateCLTU(Plugin):
    """
    Adds CLTU start and tail bytes to incoming data (frames)

    The input will normally be TC frames (either with or without BCH).
    The output is CLTUs with the CCSDS standard start and tail byte sequences.
    """

    def __init__(self, inputs=None, outputs=None, zmq_args=None):
        super().__init__(inputs, outputs, zmq_args)
        self.cltu_start = bytearray(b"\xEB\x90")
        self.cltu_tail = bytearray(b"\xC5\xC5\xC5\xC5\xC5\xC5\xC5\x79")

    def process(self, input_data, topic=None):
        cltu_bytearray = self.cltu_start + input_data + self.cltu_tail
        self.publish(cltu_bytearray)