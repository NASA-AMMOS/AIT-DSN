from ait.core.server.plugins import Plugin
from ait.core import log
from ait.dsn.sle.frames import AOSTransFrame, AOSDataFieldType
from bitstring import BitArray
from enum import Enum, auto
from collections import OrderedDict, namedtuple
from colorama import Fore, Back, Style
import time


class Packet_State(Enum):
    COMPLETE = auto()
    UNDERFLOW = auto()
    SPILLOVER = auto()
    IDLE = auto()

class HeaderKeys(Enum):
    PACKET_VERSION_NUMBER = slice(0, 3)
    PACKET_TYPE = slice(3, 4)
    SEC_HDR_FLAG = slice(4, 5)
    APPLICATION_PROCESS_IDENTIFIER = slice(5, 16)
    SEQUENCE_FLAGS = slice(16, 18)
    PACKET_SEQUENCE_OR_NAME = slice(18, 32)
    PACKET_DATA_LENGTH = slice(32, 48)


class CCSDS_Packet():

    def __init__(self, PACKET_VERSION_NUMBER=0, PACKET_TYPE=0,
                 SEC_HDR_FLAG=0, APPLICATION_PROCESS_IDENTIFIER=0,
                 SEQUENCE_FLAGS=0, PACKET_SEQUENCE_OR_NAME=0,
                 PACKET_DATA_LENGTH=0, data=b''):
        self.data = data
        self.primary_header = {}
        self.primary_header[HeaderKeys.PACKET_VERSION_NUMBER.name] = PACKET_VERSION_NUMBER
        self.primary_header[HeaderKeys.PACKET_TYPE.name] = PACKET_TYPE
        self.primary_header[HeaderKeys.SEC_HDR_FLAG.name] = SEC_HDR_FLAG
        self.primary_header[HeaderKeys.APPLICATION_PROCESS_IDENTIFIER.name] = APPLICATION_PROCESS_IDENTIFIER
        self.primary_header[HeaderKeys.SEQUENCE_FLAGS.name] = SEQUENCE_FLAGS
        self.primary_header[HeaderKeys.PACKET_SEQUENCE_OR_NAME.name] = PACKET_SEQUENCE_OR_NAME
        if not PACKET_DATA_LENGTH:
            self.primary_header[HeaderKeys.PACKET_DATA_LENGTH.name] = len(data)-1
        else:
            self.primary_header[HeaderKeys.PACKET_DATA_LENGTH.name] = PACKET_DATA_LENGTH
        self.secondary_header = {}

        self.encoded_packet = bytes()
        self.error = None

    @staticmethod
    def decode(packet_bytes):
        data_length = int.from_bytes(packet_bytes[4:6], 'big')
        if not data_length: # regular check is apid 111111....
            #log.warn("Underflow: Insufficient Data")
            return (Packet_State.UNDERFLOW, None)

        if set(packet_bytes) == {224}:
            #log.info(f"Idle Packet")
            return (Packet_State.IDLE, None)
            return

        actual_packet = packet_bytes[:6+data_length+1]
        header_bits = BitArray(actual_packet[0:6]).bin
        data = actual_packet[6:]
        decoded_header = {}
        for key in HeaderKeys:
            decoded_header[key.name] = int(header_bits[key.value], 2)

        decoded_header['data'] = data
        p = CCSDS_Packet(**decoded_header)
        p.encoded_packet = actual_packet
        #rest = packet_bytes[6+data_length+1:]
        if p.is_complete():
            return (Packet_State.COMPLETE, p)
        else:
            return (Packet_State.SPILLOVER, p)

    def is_complete(self):
        return not bool(self.get_missing())

    def get_missing(self):
        m = (g := self.primary_header[HeaderKeys.PACKET_DATA_LENGTH.name]+1) - (q := len(self.data))
        #print(f"{m=} {g=} {q=}")
        return m

    def get_next_index(self):
        return 6 + self.primary_header[HeaderKeys.PACKET_DATA_LENGTH.name] + 1

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)

    def encode(self):
        if self.encoded_packet:
            return self.encoded_packet

        new = BitArray()
        for (k, v) in self.primary_header.items():
            size = k.value.start - (k.value.stop-1)
            padded_segment = format(v, f'0{size}b')
            segment = BitArray(bin=padded_segment)
            new.append(segment)
        new.append(self.data)
        self.encoded_packet = new.bytes
        return self.encoded_packet

class AOS_to_CCSDS():
    '''
    This plugin expects a stream of whole AOS frames, and outputs CCSDS packets
    '''
    def __init__(self):
        self.bytes_from_previous_frames = bytes()
        self.happy_customers = 0

    def depacketize(self, data):
        log.debug("NEW")

        def attempt_packet(data):
            stat, p = CCSDS_Packet.decode(data)
            if stat == Packet_State.COMPLETE:
                log.debug(f"{Fore.GREEN} Got a packet! {Fore.RESET}")
                accumulated_packets.append(p.encoded_packet)
                self.bytes_from_previous_frames = bytes()
                return p.get_next_index()

            elif stat == Packet_State.SPILLOVER:
                log.debug(f"{Fore.MAGENTA} SPILLOVER missing {p.get_missing()} bytes {Fore.RESET}")
                self.bytes_from_previous_frames = data
                return None

            elif stat == Packet_State.UNDERFLOW:
                log.debug(f"{Fore.RED} UNDERFLOW {data=} {Fore.RESET}")
                self.bytes_from_previous_frames = data
                return None

            elif stat == Packet_State.IDLE:
                log.debug(f"{Fore.YELLOW} IDLE {Fore.RESET}")
                return None

        def handle_spillover_packet(data):
            p = attempt_packet(self.bytes_from_previous_frames+data)
            if p:
                log.debug(f"{Fore.CYAN} Picked up a packet! {Fore.RESET}")

        accumulated_packets = []
        AOS_frame_object = AOSTransFrame(data)

        if AOS_frame_object.is_idle_frame:
            log.debug("Dropping idle frame!")
            return accumulated_packets

        if AOS_frame_object.get('mpdu_is_idle_data'):
            print("Idle! Packet!")
            return accumulated_packets

        first_header_pointer = AOS_frame_object.get('mpdu_first_hdr_ptr')
        mpdu_packet_zone = AOS_frame_object.get('mpdu_packet_zone')

        log.debug(f"{first_header_pointer=} ")
        if first_header_pointer != 0 and self.bytes_from_previous_frames:
            log.debug(f"Handling spare packet: {first_header_pointer=}")
            handle_spillover_packet(mpdu_packet_zone[:first_header_pointer])

        pointer = first_header_pointer
        j = 1
        while (maybe_next_packet := mpdu_packet_zone[pointer:]):
            #print(maybe_next_packet.hex())
            #print(f"{j=}")
            j += 1
            next_index = attempt_packet(maybe_next_packet)
            if not next_index:
                break
            pointer += next_index

        return accumulated_packets
