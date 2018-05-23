# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2018, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.


from pdu import PDU
from ait.dsn.cfdp.util import string_to_bytes, bytes_to_string


class FileData(PDU):

    def __init__(self, *args, **kwargs):
        super(FileData, self).__init__()
        self.header = kwargs.get('header', None)
        self.segment_offset = kwargs.get('segment_offset', None)
        self.data = kwargs.get('data', None)

    def to_bytes(self):
        bytes = []

        # Segment Offset is 32 bits
        byte_1 = format(self.segment_offset, '>032b')
        bytes.append(int(byte_1[0:8], 2))
        bytes.append(int(byte_1[8:16], 2))
        bytes.append(int(byte_1[16:24], 2))
        bytes.append(int(byte_1[24:32], 2))

        # Variable Length File Data
        # Get length of chunk
        data_in_bytes = string_to_bytes(self.data)
        bytes.extend(data_in_bytes)

        if self.header:
            header_bytes = self.header.to_bytes()
            return header_bytes + bytes
        return bytes

    @staticmethod
    def to_object(pdu_bytes):
        """Return PDU subclass object created from given bytes of data"""
        if not isinstance(pdu_bytes, list):
            raise ValueError('fd body should be a list of bytes represented as integers')

        if len(pdu_bytes) < 4:
            raise ValueError('fd should be at least 4 bytes long')

        # Extract 32 bit offset
        # convert all to 8-bit strings and append to make a full 32 bit string
        segment_offset_binary = format(pdu_bytes[0], '>08b') \
                               + format(pdu_bytes[1], '>08b') \
                               + format(pdu_bytes[2], '>08b') \
                               + format(pdu_bytes[3], '>08b')
        segment_offset = int(segment_offset_binary, 2)

        # TODO error handling if there is no file data
        file_data = None
        if len(pdu_bytes) > 4:
            # File data chunk of variable size
            file_data = bytes_to_string(pdu_bytes[4:])

        return FileData(
            segment_offset=segment_offset,
            data=file_data
        )
