from enum import Enum
from pdu import PDU
from ait.dsn.cfdp.primitives import FileDirective, ConditionCode, TransactionStatus

class NAK(PDU):

    file_directive_code = FileDirective.NAK

    def __init__(self, *args, **kwargs):
        super(NAK, self).__init__()
        self.header = kwargs.get('header', None)
        self.start_of_scope = kwargs.get('start_of_scope', None)
        self.end_of_scope = kwargs.get('end_of_scope', None)
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

        # N x 64 segment requests
        # TODO after receiver 2

        if self.header:
            header_bytes = self.header.to_bytes()
            return header_bytes + bytes
        return bytes

    @staticmethod
    def to_object(pdu_bytes):
        """Return PDU subclass object created from given bytes of data"""
        if not isinstance(pdu_bytes, list):
            raise ValueError('nak body should be a list of bytes represented as integers')

        if len(pdu_bytes) < 3:
            raise ValueError('nak body should be at least 3 bytes long')

        if FileDirective(pdu_bytes[0]) != NAK.file_directive_code:
            raise ValueError('file directive code is not type NAK')

        # Extract 4 bit directive code and 4 bit subtype
        directive_code = FileDirective(pdu_bytes[1] >> 4)
        directive_subtype_code = pdu_bytes[1] & 0x0F

        # Extract 4 bit condition code, 2 bit transaction status
        condition_code = ConditionCode(pdu_bytes[1] >> 4)
        transaction_status = TransactionStatus(pdu_bytes[1] & 0x03)

        return NAK(
            directive_code=directive_code,
            directive_subtype_code=directive_subtype_code,
            condition_code=condition_code,
            transaction_status=transaction_status
        )
