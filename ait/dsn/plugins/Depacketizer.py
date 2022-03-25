import ait
from ait.core.server.plugins import Plugin
from ait.core import log
from collections import defaultdict, namedtuple, OrderedDict
import pickle
from ait.core import tlm, log
import ait.dsn.sle.frames as frames
from enum import auto, Enum
import bitstring


class M_PDU_HEADER():
    RSVD_SPARE_SLICE = slice(0, 5)
    FIRST_HEADER_POINTER_SLICE = slice(5, 16)
    IDLE_PATTERN = '0x\xe0\xe0\xe0'

    def __init__(self, data):
        self.data = bitstring.BitArray(data)
        if not self.data:
            return
        
    def does_pdu_zone_have_a_packet_start(self):
        return not (self.data[self.FIRST_HEADER_POINTER_SLICE] ==
                    bitstring.BitArray(bin='11111'))

    def does_pdu_zone_contain_overflow(self):
        return (self.data[self.FIRST_HEADER_POINTER_SLICE] ==
                bitstring.BitArray(bin='00000'))

    def is_pdu_zone_only_idle(self):
        val = (self.data[self.FIRST_HEADER_POINTER_SLICE] ==
               bitstring.BitArray(bin='11110'))
        if val:
            log.error(f"M_PDU_HEADER: VAL: {val} Only idle {self.data}")
        return val

    def is_packet_idle_data(self):
        return  # if find idle_pattern

    def is_first_packet_first_pdu(self):
        return (self.data[self.FIRST_HEADER_POINTER_SLICE] == 0)

    def get_first_header_pointer(self):
        hptr = (self.data[self.FIRST_HEADER_POINTER_SLICE])
        log.error(f"{self.data}, {hptr}")
        hptr = int(hptr.bin, 2)
        return hptr

    def get_spanning_pdu(self):
        if self.does_pdu_zone_contain_overflow():
            hptr = self.get_first_header_pointer()+1
            log.error(f"M_PDU_HEADER: Found spanning PDU at index {hptr} {self.data}")
            return self.data[:hptr]
        else:
            return []

    def get_pdu_zone(self):
        if self.is_pdu_zone_only_idle():
            log.error(f"M_PDU_HEADER: Could only find idle {self.data}")
            return []
        elif self.does_pdu_zone_have_a_packet_start():
            log.error(f"M_PDU_HEADER: Found starting packet {self.data}")
            hptr = self.get_first_header_pointer()
            return self.data[hptr:]
        else:
            dat = self.data[16:]
            log.error(f"M_PDU_HEADER: Found overflowing packet {dat}")
            return dat


class Space_Packet():

    class Packet_Type(Enum):
        TELECOMMAND = 0
        TELEMETRY = 1

    class Sequence_Type(Enum):
        CONTINUATION = bitstring.BitArray(bin='00')
        FIRST_SEGMENT = bitstring.BitArray(bin='01')
        LAST_SEGMENT = bitstring.BitArray(bin='10')
        UNSEGMENTED = bitstring.BitArray(bin='11')

    class Packet_Sections(Enum):
        PACKET_PRIMARY_HEADER_SLICE = auto()
        PACKET_DATA_FIELD = auto()
        USER_DATA_FIELD = auto()
        # def __new__(cls, value, secondary_header_flag):
        #     obj = bytes.__new__(cls, value)
        #     obj._value_ = value
        #     return obj

    class Primary_Packet_Header_Slices(Enum):
        PACKET_VERSION_NUMBER = slice(0, 3)

        # Packet Identification
        PACKET_IDENTIFICATION = slice(3, 16)
        PACKET_TYPE = slice(3, 4)
        SECONDARY_HEADER_FLAG = slice(4, 5)
        APPLICATION_PROCESS_IDENTIFIER = slice(5, 16)

        # Packet Sequence Control
        PACKET_SEQUENCE_CONTROL = slice(16, 32)
        SEQUENCE_FLAGS = slice(16, 18)
        PACKET_SEQUENCE_COUNT_OR_NAME = slice(18, 32)

        # C = (Total Number of Octets in the Packet Data Field) – 1
        PACKET_DATA_LENGTH = slice(32, 48)

    class Packet_Secondary_Header(Enum):
        TIME_CODE_FIELD = 0  # GET
        ANCILLARY_DATA_FIELD = 0

    def __init__(self, packet_bytes):
        #self.secondary_header_length = 0  # get

        self.raw_packet_data = packet_bytes
        self.primary_header = self.raw_packet_data.bytes[0:6] #OK
        self.packet_length = self.get_packet_length(self.primary_header) #OK
        self.user_data_field = self.raw_packet_data[6:self.packet_length] #ok
        self.residue = self.raw_packet_data[self.packet_length:]

        self.res = {slice_name.name:
                    self.raw_packet_data[slice_name.value] for
                    slice_name in self.Primary_Packet_Header_Slices}
        
        key = self.Primary_Packet_Header_Slices.PACKET_TYPE.name
        self.res[key] = self.Packet_Type(self.res[key])

        key = self.Primary_Packet_Header_Slices.SEQUENCE_FLAGS.name
        self.res[key] = self.Sequence_Type(self.res[key])

        self.res[self.Packet_Sections.USER_DATA_FIELD.name] = self.user_data_field
        key = self.Primary_Packet_Header_Slices.PACKET_DATA_LENGTH.name
        self.res[key] = self.get_packet_length(self.primary_header)
        # print()
        # print(z)
        # print(len(z))
        # print()
        # exit()
        return

    def is_idle_packet(self, primary_header):
        primary_header = bitstring.BitArray(primary_header)
        res = (self.res[Space_Packet.Primary_Packet_Header_Slices.
                        APPLICATION_PROCESS_IDENTIFIER.name] ==
               bitstring.BitArray(bin='111111111'))
        
        res *= (self.res[Space_Packet.Primary_Packet_Header_Slices.
                         PACKET_IDENTIFICATION.name]
                ==
                bitstring.BitArray(b'\xe0\xe0\xe0'))
        if res:
            log.error("IT'S IDLE!")
        return res

    def decode(self):
        return self.res

    def get_residue(self):
        return self.residue_user_data_field

    def get_data_field(self):
        return self.user_data_field

    def get_packet_length(self, primary_header):
        #print(primary_header)
        index = primary_header[-2]
        return index

    def get_packet_version_number(self, primary_header):
        primary_header = bitstring.BitArray(primary_header)
        s = self.Primary_Packet_Header_Slices.PACKET_VERSION_NUMBER.value
        res = primary_header[s]
        #print(res)
        return

    def get_packet_version_number(self, primary_header):
        primary_header = bitstring.BitArray(primary_header)
        s = self.Primary_Packet_Header_Slices.PACKET_VERSION_NUMBER.value
        res = primary_header[s]
        #print(res)
        return


class Partial_Payload():
    def __init__(self, partial, expected_payload_length):
        self.partial = partial
        self.expected_payload_length = expected_payload_length

    def merge(self, partial):
        self.partial += partial
        if len(self.partial) == self.expected_payload_length:
        #len(self.partial) == self.expected_payload_length:
            #print("PARTIAL COMPLETE!")
            return self.partial
        else:
            #print(len(self.partial) - self.expected_payload_length)
            return
        

class CCSDS_Depacketizer():
    def __init__(self, data):
        self.data = data
        self.partial = None
        self.packets = []

    def handle_partial(self, partial, expected_payload_length=None):
        if expected_payload_length:
            self.partial = Partial_Payload(partial)
            self.expected_payload_length = expected_payload_length
        else:
            res = self.partial.merge(partial)
            if res:
                p = Space_Packet(res)
                self.packets.append(p)
                self.partial = None
        
    def handle_perfect(self, packet):
        self.packets.append(packet)
        
    def handle_depacket(self, data):
        p = Space_Packet(data)
        expected_payload_length = p.get_packet_length()
        payload = p.get_data_field()
        res = p.get_residue()

        if len(payload) == expected_payload_length:
            self.handle_perfect(p)
        elif len(payload) < expected_payload_length and self.partial:
            self.handle_partial(payload)
        elif len(payload) < expected_payload_length and not self.partial:
            self.handle_partial(payload, expected_payload_length)
 
        if res:
            self.handle_depacket(res)

        res = self.packets
        self.packets = []
        return res

            
class Depacketizer(Plugin):

    def __init__(self, inputs=None, outputs=None, zmq_args=None, **kwargs):
        super().__init__(inputs, outputs, zmq_args)
        self.partial = None
        self.ccsds_depack = CCSDS_Depacketizer()

    def process(self, AOS_Frame, topic=None):

        fhp = AOS_Frame.get('mpdu_first_hdr_ptr')
        pduz = AOS_Frame.get('mpdu_packet_zone')
    
        payload = pduz[fhp:]

        res = self.ccsds_depack(payload)
        print(res)


​
