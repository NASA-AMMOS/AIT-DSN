from ait.core.server.plugins import Plugin
from ait.core import log
from ait.dsn.sle.frames import AOSTransFrame, AOSDataFieldType


class AOS_to_CCSDS_Plugin(Plugin):
    def __init__(self, inputs=None, outputs=None, zmq_args=None, **kwargs):
        super().__init__(inputs, outputs, zmq_args)
        self.depacketizer = AOS_to_CCSDS()
        
    def process(self, data, topic=None):
        '''
        publishes a CCSDS packet to the output topic
        '''
        ccsds_packets = self.depacketizer.depacketize(data)
        for packet in ccsds_packets:
            #log.info(f"Sending CCSDS packet with bytes {bytes(packet).hex()}")
            self.publish(packet)
        
class AOS_to_CCSDS():
    '''
    This plugin expects a stream of whole AOS frames, and outputs CCSDS packets
    '''
    def __init__(self):
        self.bytes_from_previous_frames = None
        self.accumulated_packets = []

    def depacketize(self, data):
        self.accumulated_packets = []
        AOS_frame_object = AOSTransFrame(data)
        #log.info(f'incoming data to deframer of len {str(len(data))}')
        if AOS_frame_object.is_idle_frame or \
           AOS_frame_object.get('aos_data_field_type') is not AOSDataFieldType.M_PDU:
            log.debug(f"Dropping idle frame!")
            return []
        else:
            first_header_pointer = AOS_frame_object.get('mpdu_first_hdr_ptr')
            #log.info(f'first header point AOS CCSDS: {first_header_pointer}')
            #log.info(f"VC frame count: {AOS_frame_object.get('virtual_channel_frame_count')}")
            #log.info(f"VCID: {AOS_frame_object.get('virtual_channel_id')}")
            mpdu_packet_zone = AOS_frame_object.get('mpdu_packet_zone')
            mpdu_tuple = (first_header_pointer, mpdu_packet_zone)
            self.process_m_pdu_tuple(mpdu_tuple, AOS_frame_object.get('virtual_channel_id'))
        return self.accumulated_packets

    def process_m_pdu_tuple(self, input_tuple, vcid):
        # input to this function should be a tuple of format (m_pdu_hdr_pointer, m_pdu_data_zone)
        first_packet_header_pointer = input_tuple[0]
        m_pdu_data = input_tuple[1]
        remaining_bytes_to_send = m_pdu_data

        if self.bytes_from_previous_frames is not None:
            #log.info('merging with prev frame data')
            #log.info(self.bytes_from_previous_frames)
            #log.info(m_pdu_data[0:first_packet_header_pointer])
            #log.info(f'first header point: {first_packet_header_pointer}')
            ccsds_packet_to_send = self.bytes_from_previous_frames + m_pdu_data[0:first_packet_header_pointer]
 #           self.send_ccsds_packet(ccsds_packet_to_send)
            self.accumulated_packets.append(ccsds_packet_to_send)
            self.bytes_from_previous_frames = None
            remaining_bytes_to_send = remaining_bytes_to_send[first_packet_header_pointer:]
            #log.info(remaining_bytes_to_send)
            #log.info('--')

        while remaining_bytes_to_send is not None:
            #check for repeating e0 bytes
            if remaining_bytes_to_send == bytearray(b'\xe0' * len(remaining_bytes_to_send)):
                log.debug("Found repeating e0 bytes in remainder of m_pdu_zone")
                #log.info('found repeating e0 bytes')
                remaining_bytes_to_send = None
                continue

            length_of_next_packet = self.get_packet_length_from_header(remaining_bytes_to_send[0:6])
            if length_of_next_packet > 1774:
                #log.info('length of next packet > 1774')
                #log.info(remaining_bytes_to_send)
                pass
            log.debug(f"Length of next CCSDS packet is {length_of_next_packet}")
            if length_of_next_packet == len(remaining_bytes_to_send):
#                self.send_ccsds_packet(remaining_bytes_to_send)
                self.accumulated_packets.append(remaining_bytes_to_send)
                remaining_bytes_to_send = None
                continue
            elif length_of_next_packet < len(remaining_bytes_to_send):
                #self.send_ccsds_packet(remaining_bytes_to_send[:length_of_next_packet])
                self.accumulated_packets.append(remaining_bytes_to_send[:length_of_next_packet])
                remaining_bytes_to_send = remaining_bytes_to_send[length_of_next_packet:]
                continue
            elif length_of_next_packet > len(remaining_bytes_to_send):
                #log.info('saving data for next frame')
                #log.info(remaining_bytes_to_send)
                #log.info(length_of_next_packet)
                #log.info(first_packet_header_pointer)
                #log.info('***')
                self.bytes_from_previous_frames = remaining_bytes_to_send
                remaining_bytes_to_send = None
                continue

    def get_packet_length_from_header(self, header_bytes):
        '''
        send this function a 6 byte header and it'll return the length of the packet as an int
        '''
        log.debug(f"get_packet_length function recieved header {bytes(header_bytes).hex()}")
        length_as_bytes = header_bytes[4:]
        length_as_int = int.from_bytes(length_as_bytes, "big")
        # assuming no secondary header
        # length_as_int is the length of the data field + 1. Add 6 bytes for primary header
        total_packet_length = length_as_int + 7
        return total_packet_length



