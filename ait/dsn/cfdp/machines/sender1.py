# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2018, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.

import copy
import os
from ait.dsn.cfdp.events import Event
from ait.dsn.cfdp.pdu import Metadata, Header, FileData, EOF
from ait.dsn.cfdp.primitives import Role, ConditionCode, IndicationType
from ait.dsn.cfdp.util import string_length_in_bytes, calc_file_size, check_file_structure, calc_checksum
from machine import Machine

import ait.core
import ait.core.log


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
        self.header.entity_ids_length = ait.config.get('dsn.cfdp.max_entity_id_length', 8) # get default entity id length, 8 bytes
        self.header.transaction_id_length = ait.config.get('dsn.cfdp.max_transaction_id_length', 8) # get default entity id length, 8 bytes
        self.header.source_entity_id = self.transaction.entity_id
        self.header.transaction_id = self.transaction.transaction_id
        self.header.destination_entity_id = request.info.get('destination_id')
        self.header.transmission_mode = request.info.get('transmission_mode')
        return self.header

    def make_metadata_pdu_from_request(self, request):
        # At this point, most if not all fields of the header should be populated. Just change the fields that need to be

        # Calculate pdu data field length for header
        # TODO double check this...
        # here the data field is size of metadata
        #   a. directive code 8 bit
        #   b. segmentation control (1 bit)
        #   c. reserved for future use (0000000) 7 zeros
        #   d. file size (32 bit)
        #   e. LVs for destination and source file
        # Start as 6 for a + b + c + d
        data_field_length_octets = 6
        # Each of these is +1 for 8 bit length field
        data_field_length_octets += (string_length_in_bytes(request.info.get('source_path')) + 1)
        data_field_length_octets += (string_length_in_bytes(request.info.get('destination_path')) + 1)
        self.header.pdu_data_field_length = data_field_length_octets

        file_size = calc_file_size(self.transaction.full_file_path)

        # Copy header
        header = copy.copy(self.header)
        header.pdu_type = Header.FILE_DIRECTIVE_PDU
        self.metadata = Metadata(
            header=header,
            source_path=request.info.get('source_path'),
            destination_path=request.info.get('destination_path'),
            file_size=file_size)
        return self.metadata

    def make_eof_pdu(self, condition_code):
        header = copy.copy(self.header)
        header.pdu_type = Header.FILE_DIRECTIVE_PDU

        # Calculate pdu data field length for EOF header
        # here the data field is size of EOF
        #   a. directive code 8 bit
        #   b. condition code 4 bits
        #   c. spare 4 bits
        #   d. file chksum 32 bits
        #   e. file size in octets 32 bits
        # Sum is 10
        data_field_length_octets = 10
        header.pdu_data_field_length = data_field_length_octets

        self.eof = EOF(
            header=header,
            condition_code=condition_code,
            file_checksum=self.transaction.filedata_checksum,
            file_size=self.metadata.file_size
        )
        return self.eof

    def make_fd_pdu(self):
        file_chunk_size = self.kernel.mib.maximum_file_segment_length(self.transaction.entity_id)
        offset = 0
        data_chunk = None
        if self.file is not None:
            offset = self.file.tell()
            data_chunk = self.file.read(file_chunk_size)
        if not data_chunk:
            # FIXME to be more accurate of an error
            return self.fault_handler(ConditionCode.FILESTORE_REJECTION)
        header = copy.copy(self.header)
        header.pdu_type = Header.FILE_DATA_PDU

        # Calculate pdu data field length for header
        # here the data field is size of FD
        #   a. segment offset (32 bits)
        #   b. File data (variable)
        data_field_length_octets = 4
        # Get file data size
        data_field_length_octets += len(data_chunk)
        header.pdu_data_field_length = data_field_length_octets

        fd = FileData(
            header=header,
            segment_offset=offset,
            data=data_chunk)
        return fd

    def update_state(self, event=None, pdu=None, request=None):
        """
        Prompt for machine to evaluate a state. Could possibly or possibly not receive an event, pdu, or request to factor into state
        """
        # TODO make DRYER -- there are some cases (sending file data/dir) that are state-independent

        if self.state == self.S1:

            # Only event in S1 with defined action is receiving a put request
            if event == Event.RECEIVED_PUT_REQUEST:
                ait.core.log.info("Sender {0}: Received PUT REQUEST".format(self.transaction.entity_id))
                self.put_request_received = True
                self.transaction.other_entity_id = request.info.get('destination_id')

                # Store the actual file path
                # Files should be located in path specified in ait.config
                outgoing_directory = self.kernel._data_paths['outgoing']
                full_source_path = os.path.join(outgoing_directory, request.info.get('source_path'))
                self.transaction.full_file_path = full_source_path

                # (A) Transaction Start Indication Procedure
                # Issue Transaction Indication
                self.indication_handler(IndicationType.TRANSACTION_INDICATION, transaction_id=self.transaction.transaction_id)

                # Seed PDU header. `self.header` is to be reused in subsequent PDUs for this transaction
                self.make_header_from_request(request)
                # Make MD PDU from request and queue it up for sending
                self.make_metadata_pdu_from_request(request)
                self.is_md_outgoing = True

                # Now that the MD PDU has been queued, state is S2
                # We are going to be sending file data PDUs from now on
                self.state = self.S2

                # Copy File Procedures if the Put.request is a file transfer
                # For now it always is because Messages to User/TLV have not been implemented
                if self.metadata.file_transfer:
                    # Retrieve the source file for Copy File procedures
                    ait.core.log.info("Sender {0}: Attempting to open file {1}"
                                 .format(self.transaction.entity_id, self.metadata.source_path))
                    try:
                        self.file = open(self.transaction.full_file_path, 'rb')
                    except IOError:
                        ait.core.log.error('Sender {0} -- could not open file {1} from outgoing path {2}'
                                      .format(self.transaction.entity_id, self.metadata.source_path, outgoing_directory))
                        return self.fault_handler(ConditionCode.FILESTORE_REJECTION)

                    # Check file structure
                    ait.core.log.info("Sender {0}: Checking file structure".format(self.transaction.entity_id))
                    if not check_file_structure(self.file, self.metadata.segmentation_control):
                        return self.fault_handler(ConditionCode.INVALID_FILE_STRUCTURE)

                    # Compute and save checksum of outgoing file to send with EOF at the end
                    self.transaction.filedata_checksum = calc_checksum(self.transaction.full_file_path)
                    ait.core.log.info('Sender {0}: Checksum of file {1}: {2}'.format(self.transaction.entity_id,
                                                                                self.metadata.source_path,
                                                                                self.transaction.filedata_checksum))
                else:
                    self.is_oef_outgoing = True
                    self.transaction.condition_code = ConditionCode.NO_ERROR
                    self.make_eof_pdu(self.transaction.condition_code)

            elif event == Event.SEND_FILE_DIRECTIVE:
                ait.core.log.debug("Sender {0}: Received SEND FILE DIRECTIVE".format(self.transaction.entity_id))
                if self.transaction.frozen or self.transaction.suspended:
                    return

                # TODO add checks to see if file directive is actually ready
                if self.is_md_outgoing is True:
                    self.kernel.send(self.metadata)
                    self.is_md_outgoing = False

                elif self.is_oef_outgoing is True:
                    ait.core.log.info("EOF TYPE: " + str(self.eof.header.pdu_type))
                    self.kernel.send(self.eof)
                    self.is_oef_outgoing = False
                    self.eof_sent = True
                    self.machine_finished = True

                    if self.kernel.mib.issue_eof_sent:
                        self.indication_handler(IndicationType.EOF_SENT_INDICATION,
                                                transaction_id=self.transaction.transaction_id)
                    self.finish_transaction()
                    self.shutdown()

            else:
                ait.core.log.debug("Sender {0}: Ignoring received event {1}".format(self.transaction.entity_id, event))
                pass

        elif self.state == self.S2:
            # Metadata has already been received
            # This is the path for ongoing file transfer

            # USER-ISSUED REQUESTS
            if event == Event.RECEIVED_REPORT_REQUEST:
                ait.core.log.info("Sender {0}: Received REPORT REQUEST".format(self.transaction.entity_id))
                # TODO logic to get report
                self.indication_handler(IndicationType.REPORT_INDICATION,
                                        status_report=None)

            elif event == Event.RECEIVED_FREEZE_REQUEST:
                ait.core.log.info("Sender {0}: Received FREEZE REQUEST".format(self.transaction.entity_id))
                self.transaction.frozen = True

            elif event == Event.RECEIVED_CANCEL_REQUEST:
                ait.core.log.info("Sender {0}: Received CANCEL REQUEST".format(self.transaction.entity_id))
                self.transaction.condition_code = ConditionCode.CANCEL_REQUEST_RECEIVED
                self.update_state(Event.NOTICE_OF_CANCELLATION) # Trigger notice of cancellation

            elif event == Event.RECEIVED_SUSPEND_REQUEST:
                ait.core.log.info("Sender {0}: Received SUSPEND REQUEST".format(self.transaction.entity_id))
                self.update_state(Event.NOTICE_OF_SUSPENSION) # Trigger notice of suspension

            elif event == Event.RECEIVED_RESUME_REQUEST:
                ait.core.log.info("Sender {0}: Received RESUME REQUEST".format(self.transaction.entity_id))
                if self.transaction.suspended is True:
                    self.transaction.suspended = False
                    self.indication_handler(IndicationType.RESUMED_INDICATION) # TODO progress param?

            elif event == Event.RECEIVED_THAW_REQUEST:
                ait.core.log.info("Sender {0}: Received THAW REQUEST".format(self.transaction.entity_id))
                self.transaction.frozen = False

            # OTHER EVENTS
            elif event == Event.ABANDON_TRANSACTION:
                ait.core.log.info("Sender {0}: Received ABANDON event".format(self.transaction.entity_id))
                self.abandon()

            elif event == Event.NOTICE_OF_CANCELLATION:
                ait.core.log.info("Sender {0}: Received NOTICE OF CANCELLATION".format(self.transaction.entity_id))
                # Set eof to outgoing to send a Cancel EOF
                self.notify_partner_of_cancel()

            elif event == Event.NOTICE_OF_SUSPENSION:
                ait.core.log.info("Sender {0}: Received NOTICE OF SUSPENSION".format(self.transaction.entity_id))
                self.suspend()

            elif event == Event.SEND_FILE_DIRECTIVE:
                if self.transaction.frozen or self.transaction.suspended:
                    return

                ait.core.log.debug("Sender {0}: Received SEND FILE DIRECTIVE".format(self.transaction.entity_id))

                if self.is_md_outgoing is True:
                    self.kernel.send(self.metadata)
                    self.is_md_outgoing = False

                elif self.is_oef_outgoing is True:
                    self.make_eof_pdu(self.transaction.condition_code)
                    ait.core.log.info("EOF TYPE: " + str(self.eof.header.pdu_type))
                    self.kernel.send(self.eof)
                    self.is_oef_outgoing = False
                    self.eof_sent = True
                    self.machine_finished = True
                    self.state = self.S1

                    if self.kernel.mib.issue_eof_sent:
                        self.indication_handler(IndicationType.EOF_SENT_INDICATION,
                                                transaction_id=self.transaction.transaction_id)
                    self.finish_transaction()
                    self.shutdown()

            elif event == Event.SEND_FILE_DATA:
                if self.transaction.frozen or self.transaction.suspended:
                    return

                ait.core.log.debug("Sender {0}: Received SEND FILE DATA".format(self.transaction.entity_id))

                if self.file is None or (not self.file.closed and self.file.tell() == self.metadata.file_size):
                    # Check if entire file is done being sent. If yes, queue up EOF
                    self.is_oef_outgoing = True
                    self.transaction.condition_code = ConditionCode.NO_ERROR
                    self.make_eof_pdu(self.transaction.condition_code)

                else:
                    # Send file data
                    fd = self.make_fd_pdu()
                    self.kernel.send(fd)

            else:
                ait.core.log.debug("Sender {0}: Ignoring received event {1}".format(self.transaction.entity_id, event))
                pass
