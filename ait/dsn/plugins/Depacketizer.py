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
    
        # if self.has_secondary_header:
        #     self.secondary_header = self.raw_packet_data[
        #         self.Packet_Slices.SECONDARY_HEADER]
        # else:
        #     self.secondary_header = {}

    # def adjust_for_secondary_header(self):
    #     # Adjust if secondary header is present
    #     if self.raw_packet_data[self.Primary_Packet_Header_Slices.
    #                             SECONDARY_HEADER_FLAG.value]:

    #         self.Packet_Slices.PACKET_DATA_FIELD.value = slice(
    #             self.Packet_Slices.PACKET_DATA_FIELD.value.start
    #             + self.secondary_header_length,
    #             self.Packet_Slices.PACKET_DATA_FIELD.value.stop)

    #         self.Packet_Slices.SECONDARY_HEADER.value = (
    #             slice(6 + self.secondary_header_length, None))

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

    def get_packet_length(self, primary_header):
        print(primary_header)
        index = primary_header[-2]
        return index

    def get_packet_version_number(self, primary_header):
        primary_header = bitstring.BitArray(primary_header)
        s = self.Primary_Packet_Header_Slices.PACKET_VERSION_NUMBER.value
        res = primary_header[s]
        print(res)
        return

    def get_packet_version_number(self, primary_header):
        primary_header = bitstring.BitArray(primary_header)
        s = self.Primary_Packet_Header_Slices.PACKET_VERSION_NUMBER.value
        res = primary_header[s]
        print(res)
        return


class Depacketizer(Plugin):

    def __init__(self, inputs=None, outputs=None, zmq_args=None, **kwargs):
        super().__init__(inputs, outputs, zmq_args)
        self.previous_spanning_data = None

    def process(self, AOS_Frame, topic=None):
        data_key = Space_Packet.Packet_Sections.USER_DATA_FIELD.name
        ccsds_packets = []
        dat = AOS_Frame.data_field
        if not dat:
            return
        m_pdu_header = M_PDU_HEADER(dat)

        current_spanning_pdu = m_pdu_header.get_spanning_pdu()
        if current_spanning_pdu and self.previous_spanning_data:
            # We found a spanning PDU at the front of the PDU zone
            # Append it to the previous spanning PDU, if we have one.
            # If we don't have it, we must have missed it and can
            # Never complete it.

            # If we spot another PDU start in the PDU zone, then
            # This spanning PDU must be complete.
            # Otherwise, it must still be spanning past this PDU
            #log.error(f"DEPACKET: GOT SPAN")
            # p = self.previous_spanning_data + current_spanning_pdu
            # p = Space_Packet(p).decode
            # ccsds_packets.append(p[data_key])
            pass
        
        if m_pdu_header.does_pdu_zone_have_a_packet_start():
            #log.error(f"DEPACKET: GOT PACKET")
            # TODO WE NEVER CHECKED IF WE COMPLETED THE PACKET
            # We  have a packet start
            # The overflow PDU must be complete
            self.previous_spanning_data = None
            pduz = m_pdu_header.get_pdu_zone()
            pduz_length = len(pduz)
            p = Space_Packet(pduz).decode()
            if p:
                ccsds_packets.append(p)

                next_index_key = Space_Packet.Primary_Packet_Header_Slices.PACKET_DATA_LENGTH.name
                processed = len(p[data_key])
                next_index = p[next_index_key]
                pduz = pduz[next_index:]
                while next_ < len(pduz):
                    print(next_index, len(pduz))
                    p = Space_Packet(pduz)
                    p = p.decode()
                    ccsds_packets.append(p[data_key])
                    processed += len(p[data_key])
                    next_index = p[next_index_key]
                    pduz = pduz[next_index:]
                print(pduz,len(pduz))
        else:
            # The entire PDU zone is an overflow from the last
            # We can complete it with the next m_pdu
            ait.log.error("Merging overflow")
            self.previous_spanning_data += m_pdu_header.get_pdu_zone()

        #ait.core.log.error(f"DEPACKET: {ccsds_packets}")
        for packet in ccsds_packets:
            #log.error(f"MOD: {len(packet) % 8}")
            exit()
            self.publish(packet)
            pass
        # return ccsds_packets
