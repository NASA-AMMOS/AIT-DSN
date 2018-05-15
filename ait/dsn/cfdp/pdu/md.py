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
from ait.dsn.cfdp.primitives import FileDirective
from ait.dsn.cfdp.util import string_length_in_bytes, string_to_bytes, bytes_to_string

class Metadata(PDU):

    SEGMENTATION_CONTROL_BOUNDARIES_RESPECTED = 0
    SEGMENTATION_CONTROL_BOUNDARIES_NOT_RESPECTED = 1

    file_directive_code = FileDirective.METADATA

    def __init__(self, *args, **kwargs):
        super(Metadata, self).__init__()
        self.header = kwargs.get('header', None)
        self.file_transfer = kwargs.get('file_transfer', True) # TODO need to implement PDU TLV to get this
        self.segmentation_control = kwargs.get('segmentation_control', self.SEGMENTATION_CONTROL_BOUNDARIES_NOT_RESPECTED)
        self.file_size = kwargs.get('file_size', 0)
        self.source_path = kwargs.get('source_path', None)
        self.destination_path = kwargs.get('destination_path', None)

    def to_bytes(self):
        md_bytes = []

        # File directive code
        byte_1 = self.file_directive_code.value
        md_bytes.append(byte_1)

        # This is seg. control + 7 reserved 0s
        byte_2 = self.segmentation_control << 7
        md_bytes.append(byte_2)

        # bytes 3 - 6
        # 32 bits (4 bytes) of file size in all zeroes
        # convert int value to a 32 bit binary string
        file_size_binary = format(self.file_size, '>032b')
        # split it into 4 1-byte int values
        md_bytes.append(int(file_size_binary[0:8], 2))
        md_bytes.append(int(file_size_binary[8:16], 2))
        md_bytes.append(int(file_size_binary[16:24], 2))
        md_bytes.append(int(file_size_binary[24:32], 2))

        # LVs for length and file names
        # Get length of the path in bytes
        source_file_length = string_length_in_bytes(self.source_path)
        md_bytes.append(source_file_length)
        # Convert actual string to bytes
        md_bytes.extend(string_to_bytes(self.source_path))

        dest_file_length = string_length_in_bytes(self.destination_path)
        md_bytes.append(dest_file_length)
        md_bytes.extend(string_to_bytes(self.destination_path))

        if self.header:
            header_bytes = self.header.to_bytes()
            return header_bytes + md_bytes
        return md_bytes

    @staticmethod
    def to_object(pdu_bytes):
        """Return PDU subclass object created from given bytes of data"""
        if not isinstance(pdu_bytes, list):
            raise ValueError('metadata body should be a list of bytes represented as integers')

        if len(pdu_bytes) < 8:
            raise ValueError('metadata body should be at least 8 bytes long')

        if FileDirective(pdu_bytes[0]) != Metadata.file_directive_code:
            raise ValueError('file directive code is not type METADATA')

        # Extract segmentation control, which is 1 bit + 7 reserved 0s
        segmentation_control = pdu_bytes[1] >> 7

        # convert all to 8-bit strings and append to make a full 32 bit string
        file_size_binary = format(pdu_bytes[2], '>08b') \
                           + format(pdu_bytes[3], '>08b') \
                           + format(pdu_bytes[4], '>08b') \
                           + format(pdu_bytes[5], '>08b')
        file_size = int(file_size_binary, 2)

        source_file_length = pdu_bytes[6]
        start_index = 7
        end_index = start_index + source_file_length
        source_path = bytes_to_string(pdu_bytes[start_index:end_index])

        dest_file_length = pdu_bytes[end_index]
        start_index = end_index + 1
        end_index = start_index + dest_file_length
        dest_path = bytes_to_string(pdu_bytes[start_index:end_index])

        return Metadata(
            segmentation_control=segmentation_control,
            file_size=file_size,
            source_path=source_path,
            destination_path=dest_path
        )
