from ait.core.server.plugins import Plugin
from ait.core import log
from ait.dsn.sle.frames import AOSTransFrame, AOSDataFieldType
from bitstring import BitArray
from enum import Enum, auto
from collections import OrderedDict, namedtuple
from colorama import Fore, Back, Style
import time

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

    @staticmethod
    def decode(packet_bytes):
        #print()
        #print(f"{packet_bytes=}")
        data_length = int.from_bytes(packet_bytes[4:6], 'big') 
        #print(f"{data_length=}")
        if not data_length: # regular check is apid 111111....
            return None
        
        actual_packet = packet_bytes[:6+data_length+1]
        #print(f"{actual_packet=}")
        
        header_bits = BitArray(actual_packet[0:6]).bin
        #print(f"{header_bits=}")
        
        data = actual_packet[6:]
        decoded_header = {}
        for key in HeaderKeys:
            decoded_header[key.name] = int(header_bits[key.value], 2)

        decoded_header['data'] = data
        p = CCSDS_Packet(**decoded_header)
        p.encoded_packet = actual_packet
        #print(p)
        #print("\n")
        rest = packet_bytes[6+data_length+1:]
        if set(rest) == {224}:
            #print(f"{Fore.RED} \n{rest=}\n {Fore.RESET}")
            pass
        else:
            #print(f"\n{rest=}\n")
            pass
        #print("\n")
        return p
        
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
        accumulated_packets = []
        AOS_frame_object = AOSTransFrame(data)

        if AOS_frame_object.is_idle_frame or \
           AOS_frame_object.get('aos_data_field_type') is not AOSDataFieldType.M_PDU:
            #log.debug("Dropping idle frame!")
            print("Drop Idle Frame!")
            return accumulated_packets
            
        if AOS_frame_object.get('mpdu_is_idle_data'):
            print("Idle! Packet!")
            return accumulated_packets
             
        first_header_pointer = AOS_frame_object.get('mpdu_first_hdr_ptr')
        mpdu_packet_zone = AOS_frame_object.get('mpdu_packet_zone')
        
        def handle_spillover_packet():
            #print(f"{Fore.GREEN} {first_header_pointer} {Fore.RESET}")
            if first_header_pointer == 0:
                return True
            
            if first_header_pointer and self.bytes_from_previous_frames:
                #print("REEEEEEE SPILLOVER!")
                #print(f"{first_header_pointer}")
                q = self.bytes_from_previous_frames + mpdu_packet_zone[:first_header_pointer] # First Header Pointer may be completely  outof frame
                p = CCSDS_Packet.decode(q)
                if not p:
                    log.debug(f"{Fore.CYAN} UNDERFLOW???? {Fore.RESET}")
                    self.bytes_from_previous_frames += mpdu_packet_zone
                    return False
                if p.is_complete():
                    #print("Completed a spare!")
                    accumulated_packets.append(p.encoded_packet)
                    self.bytes_from_previous_frames = bytes()
                    return True
                else:
                    log.debug(f"{Fore.MAGENTA} Overflow??????{Fore.RESET}")
                    self.bytes_from_previous_frames += mpdu_packet_zone
                    return False
            return True
        
        def handle_first_packet():
            first_packet_bytes = mpdu_packet_zone[first_header_pointer:]
            #print(f'{first_header_pointer=}')
            p = CCSDS_Packet.decode(first_packet_bytes)
            if not p: # We don't have enough data to even try a packet
                log.debug(f"{Fore.CYAN} UNDERFLOW!!!!! {Fore.RESET}")
                self.bytes_from_previous_frames += first_packet_bytes
                return None
            elif p.is_complete():
                #print("First Packet Good!")
                accumulated_packets.append(p.encoded_packet)
                return p
            else:
                #print(f"{Fore.MAGENTA} Overflow !!!!!!{Fore.RESET}")
                self.bytes_from_previous_frames = p.encoded_packet
                return None

        r = handle_spillover_packet()
        if not r:
            log.debug(f'{Fore.YELLOW} SPILLOVER PACKET ERROR! {Fore.RESET}')
        #     #return accumulated_packets
        
        p = handle_first_packet()
        if not p:
            #print(f'{Fore.BLUE} FIRST PACKET ERROR! {Fore.RESET}')
            return accumulated_packets
            
        j = 1
        next_index = first_header_pointer + p.get_next_index()
        maybe_next_packet = mpdu_packet_zone[next_index:]
        
        if set(maybe_next_packet) == {224}:
            #print("SUNRISE!!!!!!!1")
            return accumulated_packets
            
        while maybe_next_packet:
            if set(maybe_next_packet) == {224}: # Idle mpdu, special sunrise case
                #print("SUNRISE")
                return accumulated_packets
                
            #print(f"{j=}")
            j += 1

            #print(f"{maybe_next_packet=}")
            p = CCSDS_Packet.decode(maybe_next_packet)
            if not p:
                log.debug(f"{Fore.CYAN} UNDERFLOW******* {Fore.RESET}")
                self.bytes_from_previous_frames += maybe_next_packet
                break
            if p.is_complete():
                #print("GOTTEM")
                accumulated_packets.append(p.encoded_packet)
            else:
                log.debug(f"{Fore.MAGENTA} Overflow*****{Fore.RESET}")
                #print(f"{p.get_missing()=}")
                self.bytes_from_previous_frames += p.encoded_packet
                break
                
            next_index += p.get_next_index()
            #print(f'next index: {next_index=}')
            maybe_next_packet = mpdu_packet_zone[next_index:]
            #print(f"{maybe_next_packet=}")

        return accumulated_packets
