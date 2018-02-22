from machine import Machine
from bliss.cfdp.events import Event
from bliss.cfdp.primitives import Role, ConditionCode, IndicationType
from bliss.cfdp.pdu import Metadata, Header, FileData, EOF
from bliss.cfdp.util import string_length_in_bytes, calc_file_size

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
        self.header.transaction_id = self.transaction.transaction_id
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
        """

        # Sender is for Put request to start sending
        if self.state == self.S1:

            # Only event in S1 with defined action is receiving a put request
            if event == Event.RECEIVED_PUT_REQUEST:
                logging.info("Sender {0}: Received PUT REQUEST".format(self.transaction.entity_id))
                # Received Put Request
                self.put_request_received = True
                self.transaction.other_entity_id = request.get('destination_id')
                # Use request to populate reused header. This populates direction, entity ids, and tx number
                self.make_header_from_request(request)
                # First we build and send metadata PDU
                metadata = self.make_metadata_pdu_from_request(request)
                self.kernel.send(metadata)
                self.is_md_outgoing = True
                # Save the file buffer
                self.file = open(metadata.source_path, 'rb')
                # Then set state to the file transfer state
                self.state = self.S2
            else:
                logging.debug("Sender {0}: Ignoring received event {1}".format(self.transaction.entity_id, event))
                pass

        elif self.state == self.S2:
            # Metadata has already been received
            # This is the path for ongoing file transfer

            # USER-ISSUED REQUESTS
            if event == Event.RECEIVED_REPORT_REQUEST:
                logging.info("Sender {0}: Received REPORT REQUEST".format(self.transaction.entity_id))
                # TODO logic to get report
                self.indication_handler(IndicationType.REPORT_INDICATION,
                                        status_report=None)

            elif event == Event.RECEIVED_FREEZE_REQUEST:
                logging.info("Sender {0}: Received FREEZE REQUEST".format(self.transaction.entity_id))
                self.transaction.frozen = True

            elif event == Event.RECEIVED_CANCEL_REQUEST:
                logging.info("Sender {0}: Received CANCEL REQUEST".format(self.transaction.entity_id))
                self.transaction.condition_code = ConditionCode.CANCEL_REQUEST_RECEIVED
                self.update_state(Event.NOTICE_OF_CANCELLATION) # Trigger notice of cancellation

            elif event == Event.RECEIVED_SUSPEND_REQUEST:
                logging.info("Sender {0}: Received SUSPEND REQUEST".format(self.transaction.entity_id))
                self.update_state(Event.NOTICE_OF_SUSPENSION) # Trigger notice of suspension

            elif event == Event.RECEIVED_RESUME_REQUEST:
                logging.info("Sender {0}: Received RESUME REQUEST".format(self.transaction.entity_id))
                if self.transaction.suspended is True:
                    self.transaction.suspended = False
                    self.indication_handler(IndicationType.RESUMED_INDICATION) # TODO progress param?
                    if self.transaction.frozen is False:
                        # Trigger file data event
                        self.update_state(Event.SEND_FILE_DATA)

            elif event == Event.RECEIVED_THAW_REQUEST:
                logging.info("Sender {0}: Received THAW REQUEST".format(self.transaction.entity_id))
                if self.transaction.frozen is True:
                    self.transaction.frozen = False
                    if self.transaction.suspended is False:
                        # Trigger file data event
                        self.update_state(Event.SEND_FILE_DATA)

            # OTHER EVENTS
            elif event == Event.ABANDON_TRANSACTION:
                logging.info("Sender {0}: Received ABANDON event".format(self.transaction.entity_id))
                self.transaction.abandoned = True
                self.transaction.finished = True
                self.indication_handler(IndicationType.ABANDONED_INDICATION)
                self.shutdown()

            elif event == Event.NOTICE_OF_CANCELLATION:
                logging.info("Sender {0}: Received NOTICE OF CANCELLATION".format(self.transaction.entity_id))
                # Set eof to outgoing to send a Cancel EOF
                self.is_oef_outgoing = True
                self.transaction.cancelled = True
                self.indication_handler(IndicationType.TRANSACTION_FINISHED_INDICATION,
                                        transaction_id=self.transaction.transaction_id)
                # Shutdown
                self.shutdown()

            elif event == Event.NOTICE_OF_SUSPENSION:
                logging.info("Sender {0}: Received NOTICE OF SUSPENSION".format(self.transaction.entity_id))
                if self.transaction.suspended is False:
                    self.transaction.suspended = True
                    self.indication_handler(IndicationType.SUSPENDED_INDICATION,
                                            transaction_id=self.transaction.transaction_id,
                                            condition_code=ConditionCode.SUSPEND_REQUEST_RECEIVED)

            elif event == Event.SEND_FILE_DIRECTIVE:
                logging.info("Sender {0}: Received SEND FILE DIRECTIVE".format(self.transaction.entity_id))
                if self.is_oef_outgoing is True:
                    eof = self.make_eof_pdu(self.transaction.condition_code)
                    logging.debug("EOF TYPE: " + str(eof.header.pdu_type))
                    self.kernel.send(eof)
                    self.is_oef_outgoing = False
                    self.eof_sent = True
                    self.transaction_done = True
                    self.state = self.S1

                    self.indication_handler(IndicationType.EOF_SENT_INDICATION,
                                            transaction_id=self.transaction.transaction_id)
                    self.finish_transaction()

            elif event == Event.SEND_FILE_DATA:
                # Check if entire file is done being sent. If yes, queue up EOF
                logging.info("Sender {0}: Received SEND FILE DATA".format(self.transaction.entity_id))
                if self.file is None or self.file.closed:
                    logging.debug('No file data to send')
                elif self.file is not None and not self.file.closed and self.file.tell() == self.file_size:
                    logging.debug('File is finished. is_eof_outgoing = True. Closing file...')
                    self.is_oef_outgoing = True
                    self.transaction.condition_code = ConditionCode.NO_ERROR
                    # Shutdown
                    self.shutdown()
                else:
                    # Send file data
                    fd = self.make_fd_pdu()
                    # TODO want to add this to a queue to be sent instead of calling directly
                    # so that directives can get priority...
                    self.kernel.send(fd)

            else:
                logging.debug("Sender {0}: Ignoring received event {1}".format(self.transaction.entity_id, event))
                pass