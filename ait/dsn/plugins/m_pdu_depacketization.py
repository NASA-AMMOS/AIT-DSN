from ait.core.server.plugins import Plugin
import pickle

class m_pdu_depacketization(Plugin):

    def __init__(self, inputs=None, outputs=None, zmq_args=None, command_subscriber=None):
        super().__init__(inputs, outputs, zmq_args)
        self.bytes_from_previous_frame = None

    def process(self, input_data, topic=None):
        #input to this plugin should be of format pickle.dumps((m_pdu_hdr_pointer, m_pdu_data_zone))
        unpickled_input_data = pickle.loads(input_data)
        first_packet_header_pointer = unpickled_input_data[0]
        m_pdu_data = unpickled_input_data[1]

        remaining_bytes_to_send = m_pdu_data

        if self.bytes_from_previous_frame is not None:
            ccsds_packet_to_send = self.bytes_from_previous_frame + m_pdu_data[0:first_packet_header_pointer]
            self.send_ccsds_packet(ccsds_packet_to_send)
            self.bytes_from_previous_frame = None
            remaining_bytes_to_send = remaining_bytes_to_send[first_packet_header_pointer:]

        while remaining_bytes_to_send is not None:
            if remaining_bytes_to_send[2:5] != b"\xe0\xe0\xe0":
                length_of_next_packet = self.get_packet_length_from_header(remaining_bytes_to_send[0:6])
                if length_of_next_packet == len(remaining_bytes_to_send):
                    self.send_ccsds_packet(remaining_bytes_to_send)
                    remaining_bytes_to_send = None
                elif length_of_next_packet < len(remaining_bytes_to_send):
                    self.send_ccsds_packet(remaining_bytes_to_send[:length_of_next_packet])
                    remaining_bytes_to_send = remaining_bytes_to_send[length_of_next_packet:]
                elif length_of_next_packet > len(remaining_bytes_to_send):
                    self.bytes_from_previous_frame = remaining_bytes_to_send
                    remaining_bytes_to_send = None

    def get_packet_length_from_header(self, header_bytes):
        '''
        send this function a 6 byte header and it'll return the length of the packet as an int
        '''
        length_as_bytes = header_bytes[4:]
        length_as_int = int.from_bytes(length_as_bytes, "big") #double check that this is big endian
        #assuming no secondary header
        #length_as_int is the length of the data field - 1. Add 6 bytes for primary header
        total_packet_length = length_as_int - 1 + 6 
        return total_packet_length
    
    def send_ccsds_packet(self, ccsds_packet):
        if ccsds_packet:
            self.publish(ccsds_packet)
        
