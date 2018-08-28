from enum import Enum
from pdu import PDU
from ait.dsn.cfdp.primitives import FileDirective, ConditionCode, TransactionStatus, DirectiveCode

class ACK(PDU):

    file_directive_code = FileDirective.ACK

    def __init__(self, *args, **kwargs):
        super(ACK, self).__init__()
        self.header = kwargs.get('header', None)
        # directive code corresponding to the EOF or FINISHED pdu being responded to
        self.directive_code = kwargs.get('directive_code', None)
        self.directive_subtype_code = kwargs.get('directive_subtype_code', None)
        self.condition_code = kwargs.get('condition_code', None)
        self.transaction_status = kwargs.get('transaction_status', None)

    def to_bytes(self):
        bytes = []

        # File directive code
        byte_1 = self.file_directive_code.value
        bytes.append(byte_1)

        # 4-bit directive code, shift 4 bits
        byte_2 = self.directive_code.value << 4
        # Mask on 4-bit directive subtype to end
        byte_2 = byte_2 | self.directive_subtype_code
        bytes.append(byte_2)

        byte_3 = self.condition_code.value << 4
        byte_3 = byte_3 | self.transaction_status.value
        bytes.append(byte_3)

        if self.header:
            header_bytes = self.header.to_bytes()
            return header_bytes + bytes
        return bytes

    @staticmethod
    def to_object(pdu_bytes):
        """Return PDU subclass object created from given bytes of data"""
        if not isinstance(pdu_bytes, list):
            raise ValueError('ack body should be a list of bytes represented as integers')

        if len(pdu_bytes) < 3:
            raise ValueError('ack body should be at least 3 bytes long')

        if FileDirective(pdu_bytes[0]) != ACK.file_directive_code:
            raise ValueError('file directive code is not type ACK')

        # Extract 4 bit directive code and 4 bit subtype
        directive_code = DirectiveCode(pdu_bytes[1] >> 4)
        directive_subtype_code = pdu_bytes[1] & 0x0F

        # Extract 4 bit condition code, 2 bit transaction status
        condition_code = ConditionCode(pdu_bytes[2] >> 4)
        transaction_status = TransactionStatus(pdu_bytes[2] & 0x03)

        return ACK(
            directive_code=directive_code,
            directive_subtype_code=directive_subtype_code,
            condition_code=condition_code,
            transaction_status=transaction_status
        )
