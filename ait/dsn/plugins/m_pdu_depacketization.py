from ait.core.server.plugins import Plugin
from ait.core import log
import pickle

class m_pdu_depacketization(Plugin):

    def __init__(self, inputs=None, outputs=None, zmq_args=None, command_subscriber=None):
        super().__init__(inputs, outputs, zmq_args)
        self.bytes_from_previous_frame = None

    def process(self, input_data, topic=None):
        #input to this plugin should be of format pickle.dumps((m_pdu_hdr_pointer, m_pdu_data_zone))
        log.info(input_data)
        log.info(len(input_data))
        unpickled_input_data = input_data
        aos_frame_offset = 6
        #first_packet_header_pointer = unpickled_input_data[0]
        first_packet_header_pointer = unpickled_input_data[aos_frame_offset:aos_frame_offset+2]
        log.info(unpickled_input_data)
        #m_pdu_data = unpickled_input_data[1]
        m_pdu_data = unpickled_input_data[aos_frame_offset+2:]
        #print(f"m_pdu_depacketization plugin recieved {unpickled_input_data}")
        #print(f"first packet header pointer is {first_packet_header_pointer} and m_pdu_data_zone is {bytes(m_pdu_data).hex()}")

        remaining_bytes_to_send = m_pdu_data

        if self.bytes_from_previous_frame is not None:
            #print(f"found bytes from previous frame: {bytes(self.bytes_from_previous_frame).hex()}")
            ccsds_packet_to_send = self.bytes_from_previous_frame + m_pdu_data[0:first_packet_header_pointer]
            self.send_ccsds_packet(ccsds_packet_to_send)
            self.bytes_from_previous_frame = None
            remaining_bytes_to_send = remaining_bytes_to_send[first_packet_header_pointer:]

        while remaining_bytes_to_send is not None:

            #print(f"starting at top of while loop. Remaining bytes to send has length {len(remaining_bytes_to_send)} and contains {bytes(remaining_bytes_to_send).hex()}")

            #check for empty e0 bytes
            #print(f"Checking for idle bytes. First 3 bytes of remaining_bytes_to_send is {remaining_bytes_to_send[0:3]}.")
            if remaining_bytes_to_send[0:3] == bytearray(b'\xe0\xe0\xe0'):
                #print("Found repeating e0 bytes in remainder of m_pdu_zone")
                remaining_bytes_to_send = None
                continue

            length_of_next_packet = self.get_packet_length_from_header(remaining_bytes_to_send[0:6])
            #print(f"Length of next CCSDS packet is {length_of_next_packet}")
            if length_of_next_packet == len(remaining_bytes_to_send):
                #print("length of remaining bytes in m_pdu_zone is equal to packet length")
                self.send_ccsds_packet(remaining_bytes_to_send)
                #print("setting remaining_bytes_to_send to None")
                remaining_bytes_to_send = None
                continue
            elif length_of_next_packet < len(remaining_bytes_to_send):
                #print(f"length of packet is less than number of remaining bytes in remaining_bytes_to_send")
                self.send_ccsds_packet(remaining_bytes_to_send[:length_of_next_packet])
                remaining_bytes_to_send = remaining_bytes_to_send[length_of_next_packet:]
                continue
            elif length_of_next_packet > len(remaining_bytes_to_send):
                #print("found spanning packet: length of next packet is longer than remaining_bytes_to_send")
                self.bytes_from_previous_frame = remaining_bytes_to_send
                #print(f"setting self.bytes_from_previous_frame to {self.bytes_from_previous_frame}")
                remaining_bytes_to_send = None
                continue
    
    def get_packet_length_from_header(self, header_bytes):
        '''
        send this function a 6 byte header and it'll return the length of the packet as an int
        '''
        #print(f"get_packet_length function recieved header {bytes(header_bytes).hex()}")
        length_as_bytes = header_bytes[4:]
        length_as_int = int.from_bytes(length_as_bytes, "big") #double check that this is big endian
        #assuming no secondary header
        #length_as_int is the length of the data field + 1. Add 6 bytes for primary header
        total_packet_length = length_as_int + 7
        return total_packet_length
    
    def send_ccsds_packet(self, ccsds_packet):
        #print(f"Sending CCSDS packet with bytes {bytes(ccsds_packet).hex()}")
        self.publish(ccsds_packet)
        
