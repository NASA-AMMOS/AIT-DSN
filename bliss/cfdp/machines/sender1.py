import copy
from machine import Machine
from bliss.cfdp.events import Event
from bliss.cfdp.primitives import Role, ConditionCode
from bliss.cfdp.pdu import Metadata, Header, FileData, EOF
from bliss.cfdp.util import string_length_in_bytes
from bliss.cfdp.filestore import calc_file_size

import logging

class Sender1(Machine):
    """
    Class 1 Receiver state machine
    """

    role = Role.CLASS_1_SENDER
    # State 1, waiting to send metadata on Put request

    def make_header_from_request(self, request):
        self.header = Header()
        # direction is always towards receiver because we are a sender
        self.header.direction = Header.TOWARDS_RECEIVER
        self.header.source_entity_id = self.transaction.entity_id
        self.header.transaction_seq_num = self.transaction.sequence_number
        self.header.destination_entity_id = request.info.get('destination_id')

    def make_metadata_pdu_from_request(self, request):
        # At this point, most if not all fields of the header should be populated. Just change the fields that need to be
        # Update header pdu_type. Metadata is always file directive
        header = self.header
        header.pdu_type = Header.FILE_DIRECTIVE_PDU
        logging.debug('Making METADATA; PDU TYPE: ' + str(header.pdu_type))
        # Calculate pdu data field length for header
        # TODO double check this...
        # here the data field is size of metadata
        #   a. segmentation control (1 bit)
        #   b. reserved for future use (0000000) 7 zeros
        #   c. file size (32 bit)
        #   d. LVs for destination and source file
        # Start as 5 for a + b + c
        data_field_length_octets = 5
        # Each of these is +1 for 8 bit length field
        data_field_length_octets += (string_length_in_bytes(request.info.get('source_path')) + 1)
        data_field_length_octets += (string_length_in_bytes(request.info.get('destination_path')) + 1)
        header.pdu_data_field_length = data_field_length_octets

        self.file_size = calc_file_size(request.info.get('source_path'))
        metadata = Metadata(
            header=header,
            source_path=request.info.get('source_path'),
            destination_path=request.info.get('destination_path'),
            file_size=self.file_size)
        return metadata

    def make_eof_pdu(self, condition_code):
        header = self.header
        header.pdu_type = Header.FILE_DIRECTIVE_PDU
        logging.debug('Making EOF; PDU TYPE: ' + str(header.pdu_type))
        eof = EOF(
            header=header,
            condition_code=condition_code,
            file_checksum=0, # TODO checksum?
            file_size=self.file_size
        )
        return eof

    def make_fd_pdu(self):
        # Set type to file data
        header = self.header
        header.pdu_type = Header.FILE_DATA_PDU
        logging.debug('Making FD; PDU TYPE: ' + str(header.pdu_type))

        # Bytes to read TODO move to MIB
        TMP_FILE_CHUNK_SIZE = 128
        # This means a file buffer is open (ideally)
        offset = 0
        data_chunk = None
        if self.file is not None:
            offset = self.file.tell()
            data_chunk = self.file.read(TMP_FILE_CHUNK_SIZE)
        if not data_chunk:
            # TODO error handling
            logging.debug('No data read from file')
            raise Exception('No data read from file')
        fd = FileData(
            header=header,
            segment_offset=offset,
            data=data_chunk)
        return fd

    def update_state(self, event=None, pdu=None, request=None):
        """
        Prompt for machine to evaluate a state. Could possibly or possibly not receive an event, pdu, or request to factor into state
        :param event:
        :param pdu:
        :param request:
        :return:
        """

        # Sender is for Put request to start sending
        # logging.debug('Sender 1 {0} state: {1}'.format(self.transaction.entity_id, self.state))
        if self.state == self.S1:

            # USER-ISSUED REQUESTS (Rx)
            if event == Event.RECEIVED_CANCEL_REQUEST:
                # User-issued request to cancel
                pass
            elif event == Event.RECEIVED_ABANDONED_REQUEST:
                # User-issued abandon request
                pass
            elif event == Event.RECEIVED_REPORT_REQUEST:
                # User-issued report request
                pass
            elif event == Event.RECEIVED_PUT_REQUEST:
                logging.debug("Received put request")
                # Received Put Request
                self.put_request_received = True
                # Use request to populate reused header. This populates direction, entity ids, and tx number
                self.make_header_from_request(request)
                # First we build and send metadata PDU
                metadata = self.make_metadata_pdu_from_request(request)
                self.kernel.send(metadata)
                self.is_metadata_outgoing = True
                # Save the file buffer
                self.file = open(metadata.source_path, 'rb')
                # Then set state to the file transfer state
                self.state = self.S2
            elif event == Event.SEND_FILE_DIRECTIVE:
                pass
                # if self.is_metadata_outgoing is True:
                #     eof = self.make_eof_pdu(ConditionCode.NO_ERROR)
                #     self.kernel.send(eof)
            else:
                print "Ignoring received event: {}".format(event)
                pass

        elif self.state == self.S2:
            # Metadata has already been received
            # This is the path for ongoing file transfer, awaiting EOF

            # USER-ISSUED REQUESTS (Rx)
            if event == Event.RECEIVED_CANCEL_REQUEST:
                # User-issued request to cancel
                pass
            elif event == Event.RECEIVED_ABANDONED_REQUEST:
                # User-issued abandon request
                pass
            elif event == Event.RECEIVED_REPORT_REQUEST:
                # User-issued report request
                pass
            elif event == Event.RECEIVED_FREEZE_REQUEST:
                # Received Freeze request
                pass
            elif event == Event.RECEIVED_RESUME_REQUEST:
                # Received Resume request
                pass
            elif event == Event.RECEIVED_SUSPEND_REQUEST:
                # Received suspend request
                pass
            elif event == Event.RECEIVED_THAW_REQUEST:
                # Received thaw request
                pass
            elif event == Event.SEND_FILE_DIRECTIVE:
                if self.is_oef_outgoing is True:
                    eof = self.make_eof_pdu(ConditionCode.NO_ERROR)
                    logging.debug("EOF TYPE: " + str(eof.header.pdu_type))
                    self.kernel.send(eof)
                    self.is_oef_outgoing = False
                    self.state = self.S1
            elif event == Event.SEND_FILE_DATA:
                # Check if entire file is done being sent. If yes, queue up EOF
                logging.debug("Sending file data...")
                if self.file is None or self.file.closed:
                    logging.debug('No file data to send')
                elif self.file is not None and not self.file.closed and self.file.tell() == self.file_size:
                    logging.debug('File is finished. is_eof_outgoing = True. Closing file...')
                    self.is_oef_outgoing = True
                    self.file.close()
                    self.file = None
                else:
                    # Send file data
                    fd = self.make_fd_pdu()
                    # TODO want to add this to a queue to be sent instead of calling directly
                    # so that directives can get priority...
                    self.kernel.send(fd)
            else:
                print "Ignoring received event: {}".format(event)
                pass