from enum import Enum
from pdu import PDU
from ait.dsn.cfdp.primitives import FileDirective, FinishedPduFileStatus, ConditionCode

class Finished(PDU):
    """
    End system status: 0 -- waypoint; 1 -- end system
    Delivery code: 0 -- complete; 1 -- incomplete
    """

    file_directive_code = FileDirective.FINISHED
    WAYPOINT = 0
    END_SYSTEM = 1
    COMPLETE = 0
    INCOMPLETE = 1

    def __init__(self, *args, **kwargs):
        super(Finished, self).__init__()
        self.header = kwargs.get('header', None)
        self.condition_code = kwargs.get('condition_code', None)
        self.end_system_status = kwargs.get('end_system_status', 1)
        self.delivery_code = kwargs.get('delivery_code', 0)
        self.file_status = kwargs.get('file_status', None)

        # TODO TLV responses (TLV not implemented)

    def to_bytes(self):
        bytes = []

        # File directive code
        byte_1 = self.file_directive_code.value
        bytes.append(byte_1)

        # 4-bit directive code, shift 4 bits
        byte_2 = self.condition_code.value << 4
        # 5th bit
        if self.end_system_status == Finished.END_SYSTEM:
            byte_2 = byte_2 | 0x08
        # 6th bit
        if self.delivery_code == Finished.INCOMPLETE:
            byte_2 = byte_2 | 0x04
        # Mask on 2-bit directive subtype to end (bit 7-8)
        byte_2 = byte_2 | self.file_status.value
        bytes.append(byte_2)

        if self.header:
            header_bytes = self.header.to_bytes()
            return header_bytes + bytes
        return bytes

    @staticmethod
    def to_object(pdu_bytes):
        """Return PDU subclass object created from given bytes of data"""
        if not isinstance(pdu_bytes, list):
            raise ValueError('finished body should be a list of bytes represented as integers')

        if len(pdu_bytes) < 2:
            raise ValueError('finished body should be at least 3 bytes long')

        if FileDirective(pdu_bytes[0]) != Finished.file_directive_code:
            raise ValueError('file directive code is not type Finished')

        # Extract 4 bit directive code and 4 bit subtype
        condition_code = ConditionCode(pdu_bytes[1] >> 4)
        end_system_status = Finished.END_SYSTEM if (pdu_bytes[1] & 0x08) else Finished.WAYPOINT
        delivery_code = Finished.INCOMPLETE if (pdu_bytes[1] & 0x04) else Finished.COMPLETE
        file_status = FinishedPduFileStatus(pdu_bytes[1] & 0x03)

        return Finished(
            condition_code=condition_code,
            end_system_status=end_system_status,
            delivery_code=delivery_code,
            file_status=file_status
        )
