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
from ait.dsn.cfdp.primitives import FileDirective, ConditionCode


class EOF(PDU):

    file_directive_code = FileDirective.EOF

    def __init__(self, *args, **kwargs):
        super(EOF, self).__init__()
        self.header = kwargs.get('header', None)
        self.condition_code = kwargs.get('condition_code', None)
        self.file_checksum = kwargs.get('file_checksum', 0)
        self.file_size = kwargs.get('file_size', None)

    def to_bytes(self):
        bytes = []

        # File directive code
        byte_1 = self.file_directive_code.value
        bytes.append(byte_1)

        # 4-bit condition code + 4 bit spare
        byte_2 = self.condition_code.value << 4
        bytes.append(byte_2)

        # 32 bit checksum
        # if the checksum is longer than 32 bits, discard high-order bits
        checksum_binary = format(self.file_checksum, '>032b')[-32:]
        bytes.append(int(checksum_binary[0:8], 2))
        bytes.append(int(checksum_binary[8:16], 2))
        bytes.append(int(checksum_binary[16:24], 2))
        bytes.append(int(checksum_binary[24:32], 2))

        # 32 bit file size in octets
        filesize_binary = format(self.file_size, '>032b')
        bytes.append(int(filesize_binary[0:8], 2))
        bytes.append(int(filesize_binary[8:16], 2))
        bytes.append(int(filesize_binary[16:24], 2))
        bytes.append(int(filesize_binary[24:32], 2))

        if self.header:
            header_bytes = self.header.to_bytes()
            return header_bytes + bytes
        return bytes

    @staticmethod
    def to_object(pdu_bytes):
        """Return PDU subclass object created from given bytes of data"""
        if not isinstance(pdu_bytes, list):
            raise ValueError('eof body should be a list of bytes represented as integers')

        if len(pdu_bytes) < 10:
            raise ValueError('eofbody should be at least 10 bytes long')

        if FileDirective(pdu_bytes[0]) != EOF.file_directive_code:
            raise ValueError('file directive code is not type EOF')

        # Extract 4 bit condition code
        condition_code = ConditionCode(pdu_bytes[1] >> 4)

        # 32 bit checksum
        # convert all to 8-bit strings and append to make a full 32 bit string
        file_checksum_binary = format(pdu_bytes[2], '>08b') \
                           + format(pdu_bytes[3], '>08b') \
                           + format(pdu_bytes[4], '>08b') \
                           + format(pdu_bytes[5], '>08b')
        file_checksum = int(file_checksum_binary, 2)

        # 32 bit file size in octets
        file_size_binary = format(pdu_bytes[6], '>08b') \
                               + format(pdu_bytes[7], '>08b') \
                               + format(pdu_bytes[8], '>08b') \
                               + format(pdu_bytes[9], '>08b')
        file_size = int(file_size_binary, 2)

        return EOF(
            condition_code=condition_code,
            file_checksum=file_checksum,
            file_size=file_size
        )
