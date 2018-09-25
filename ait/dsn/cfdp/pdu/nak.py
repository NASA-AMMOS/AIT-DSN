from enum import Enum
from pdu import PDU
from ait.dsn.cfdp.primitives import FileDirective, ConditionCode, TransactionStatus

class NAK(PDU):

    file_directive_code = FileDirective.NAK

    def __init__(self, *args, **kwargs):
        super(NAK, self).__init__()
        self.header = kwargs.get('header', None)
        # 4.1.6.4.2.3
        # Each NAK PDU shall identify the subset of file data to which it pertains, i.e., the scope of the NAK PDU.
        # The scope of a NAK PDU is expressed as two offsets within  the file, indicating the start and end of the scope.
        self.start_of_scope = kwargs.get('start_of_scope', None)
        self.end_of_scope = kwargs.get('end_of_scope', None)

        # In addition to its scope, each NAK PDU shall contain zero or more segment requests.
        # The segment request(s) in a NAK PDU shall identify the start offsets and end offsets
        # of all extents of file data within its scope which have not yet been received, and shall
        # also identify missing metadata if any. TODO
        self.segment_requests = kwargs.get('segment_requests', [])

    def to_bytes(self):
        bytes = []

        # File directive code
        byte_1 = self.file_directive_code.value
        bytes.append(byte_1)

        # 32-bit start of scope
        byte_2 = format(self.start_of_scope, '>032b')
        bytes.append(int(byte_2[0:8], 2))
        bytes.append(int(byte_2[8:16], 2))
        bytes.append(int(byte_2[16:24], 2))
        bytes.append(int(byte_2[24:32], 2))

        # 32 bit end of scope
        byte_3 = format(self.end_of_scope, '>032b')
        bytes.append(int(byte_3[0:8], 2))
        bytes.append(int(byte_3[8:16], 2))
        bytes.append(int(byte_3[16:24], 2))
        bytes.append(int(byte_3[24:32], 2))

        # 32 * N segment requests
        for segment in self.segment_requests:
            start = segment[0]
            start_byte = format(start, '>032b')
            bytes.append(int(start_byte[0:8], 2))
            bytes.append(int(start_byte[8:16], 2))
            bytes.append(int(start_byte[16:24], 2))
            bytes.append(int(start_byte[24:32], 2))

            end = segment[1]
            end_byte = format(end, '>032b')
            bytes.append(int(end_byte[0:8], 2))
            bytes.append(int(end_byte[8:16], 2))
            bytes.append(int(end_byte[16:24], 2))
            bytes.append(int(end_byte[24:32], 2))

        if self.header:
            header_bytes = self.header.to_bytes()
            return header_bytes + bytes
        return bytes

    @staticmethod
    def to_object(pdu_bytes):
        """Return PDU subclass object created from given bytes of data"""
        if not isinstance(pdu_bytes, list):
            raise ValueError('nak body should be a list of bytes represented as integers')

        if len(pdu_bytes) < 9:
            raise ValueError('nak body should be at least 9 bytes long')

        if FileDirective(pdu_bytes[0]) != NAK.file_directive_code:
            raise ValueError('file directive code is not type NAK')

        # 32 bit start of scope
        # convert all to 8-bit strings and append to make a full 32 bit string
        start_scope_bin = format(pdu_bytes[1], '>08b') \
                               + format(pdu_bytes[2], '>08b') \
                               + format(pdu_bytes[3], '>08b') \
                               + format(pdu_bytes[4], '>08b')
        start_of_scope = int(start_scope_bin, 2)

        # 32 bit end of scope
        end_scope_bin = format(pdu_bytes[5], '>08b') \
                           + format(pdu_bytes[6], '>08b') \
                           + format(pdu_bytes[7], '>08b') \
                           + format(pdu_bytes[8], '>08b')
        end_of_scope = int(end_scope_bin, 2)

        # 32 * N segment requests
        segments = []
        for index in range(9, len(pdu_bytes), 8):
            start = int(format(pdu_bytes[index], '>08b') \
                           + format(pdu_bytes[index + 1], '>08b') \
                           + format(pdu_bytes[index + 2], '>08b') \
                           + format(pdu_bytes[index + 3], '>08b'), 2)
            end = int(format(pdu_bytes[index + 4], '>08b') \
                    + format(pdu_bytes[index + 5], '>08b') \
                    + format(pdu_bytes[index + 6], '>08b') \
                    + format(pdu_bytes[index + 7], '>08b'), 2)
            segments.append((start, end))

        return NAK(
            start_of_scope=start_of_scope,
            end_of_scope=end_of_scope,
            segment_requests=segments
        )
