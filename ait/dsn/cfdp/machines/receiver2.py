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
import shutil
import os
import gevent.queue

from ait.dsn.cfdp.events import Event
from ait.dsn.cfdp.pdu import Metadata, NAK, ACK, Finished, Header
from ait.dsn.cfdp.primitives import Role, ConditionCode, IndicationType, DeliveryCode, FileDirective, TransactionStatus, FinishedPduFileStatus
from ait.dsn.cfdp.util import write_to_file, calc_checksum
from ait.dsn.cfdp.timer import Timer
from receiver1 import Receiver1

import ait.core
import ait.core.log

class Receiver2(Receiver1):

    S1 = "WAIT_FOR_EOF"
    S2 = "GET_MISSING_DATA"
    S3 = "SEND_FINISHED_CONFIRM_DELIVERY"
    S4 = "TRANSACTION_CANCELLED"

    def __init__(self, cfdp, transaction_id, *args, **kwargs):
        super(Receiver2, self).__init__(cfdp, transaction_id, *args, **kwargs)
        # start up timers
        self.ack_timer = Timer()
        self.nak_timer = Timer()
        self.last_nak_start_scope = 0
        self.last_nak_end_scope = 0
        self.nak_list = None
        self.ack_list = gevent.queue.Queue()
        self.finished_list = gevent.queue.Queue()

    def enter_s2_state(self):
        """
        Procedures for entering the S2 state: Get Missing Data
        This is where we beginning transmitting NAKs to get gaps in the file data
        """
        self.state = self.S2
        if not self.transaction.suspended and not self.transaction.frozen:
            # Now that we've received EOF and entered S2 (get missing data), we go through the received list and report any gaps
            self.transmit_naks()
        self.nak_timer.start(self.kernel.mib.nak_timeout(self.transaction.entity_id))

    def enter_s3_state(self):
        """
        Procedures for entering the S3 state: Send Finished PDU and Confirm delivery
        Compares the received file size to the expected file size from the MD PDU
        and compares the calculated checksum to the expected checksum from the EOF PDU.
        Then finalizes the file by saving the temp file to the final destination.
        """
        self.state = self.S3
        # At this point, all missing data should be resolved
        self.transaction.delivery_code = DeliveryCode.DATA_COMPLETE
        self.nak_timer.cancel()

        if self.metadata.file_transfer:
            # Close temp file
            if self.temp_file is not None and not self.temp_file.closed:
                self.temp_file.close()

            # Check received vs. reported file size
            if self.transaction.recv_file_size != self.metadata.file_size:
                ait.core.log.error('Receiver {0} -- file size fault. Received: {1}; Expected: {2}'
                                   .format(self.transaction.entity_id, self.transaction.recv_file_size, self.metadata.file_size))
                self.fault_handler(ConditionCode.FILE_SIZE_ERROR)

            # Check checksum on the temp file before we save it to the actual destination
            temp_file_checksum = calc_checksum(self.temp_path)
            if temp_file_checksum != self.eof.file_checksum:
                ait.core.log.error('Receiver {0} -- file checksum fault. Received: {1}; Expected: {2}'
                                   .format(self.transaction.entity_id, temp_file_checksum,
                                           self.eof.file_checksum))
                self.fault_handler(ConditionCode.FILE_CHECKSUM_FAILURE)

        # Copy temp file to destination path
        destination_directory_path = os.path.dirname(self.file_path)
        if not os.path.exists(destination_directory_path):
            os.makedirs(destination_directory_path)
        try:
            shutil.copy(self.temp_path, self.file_path)
            file_status_code = FinishedPduFileStatus.FILE_RETAINED_SUCCESSFUL
        except IOError:
            self.fault_handler(ConditionCode.FILESTORE_REJECTION)
            file_status_code = FinishedPduFileStatus.FILE_DISCARDED_FILESTORE_REJECTION

        # TODO Filestore requests, not yet implemented
        # TODO 4.1.6.3.2 Unacknowledged Mode Procedures at the Receiving Entity check timer?

        self.make_finished_pdu(condition_code=ConditionCode.NO_ERROR, delivery_code=Finished.COMPLETE, file_status=file_status_code)
        self.ack_timer.start(self.kernel.mib.ack_timeout(self.transaction.entity_id))

    def enter_s4_state(self):
        """
        Procedures for entering the S4 state: Transaction Cancelled
        """
        if self.state == self.S3:
            # Possibly retain tmp file
            pass
        self.state = self.S4
        self.transaction.suspended = False
        self.transaction.cancelled = True
        self.make_finished_pdu(condition_code=ConditionCode.CANCEL_REQUEST_RECEIVED, delivery_code=Finished.COMPLETE,
                               file_status=FinishedPduFileStatus.FILE_STATUS_UNREPORTED)
        self.finish_transaction()
        self.ack_timer.start(self.kernel.mib.ack_timeout(self.transaction.entity_id))

    def transmit_naks(self):
        """
        Constructs and transmits NAK PDUs based off the contents of `self.received_map`.
        `self.received_map` contains the offset and length of each FileData PDU received. This procedure
        iterates through and determines the gaps in order to construct the NAK sequence.

        The end of scope is the entire length of the file if the EOF PDU has been received. Otherwise, it is the current
        reception progress (case of NAK timeout, e.g.)
        """
        # If we have already transmitted a NAK sequence, last_nak_end_scope will be > 0. Set our start scope to be
        # where we left off before
        start_scope = self.last_nak_start_scope
        if self.last_nak_end_scope > 0:
            start_scope = self.last_nak_end_scope

        # If we have received the EOF, the end scope is the full file length
        # Else, end scope is the current progress of received file
        if self.eof and self.eof_received:
            end_scope = self.metadata.file_size
            self.last_nak_end_scope = end_scope
        else:
            end_scope = self.transaction.recv_file_size

        header = copy.copy(self.header)
        header.pdu_type = Header.FILE_DIRECTIVE_PDU
        header.pdu_data_field_length = 9 + 8 * len(self.nak_list)  # NAK pdu is 9 octects + n * 64 bits (8 octets) for segment requests
        nak = NAK(header=header, start_of_scope=start_scope, end_of_scope=end_scope, segment_requests=self.nak_list)
        self.kernel.send(nak)

    def get_nak_list_from_received(self):
        # Sort the list by offset
        received_list = []
        for offset, length in self.received_map.iteritems():
            received_list.append({'offset': offset, 'length': length})
        received_list = sorted(received_list, key=lambda x: x.get('offset'))

        self.nak_list = []
        for index, item in enumerate(received_list):
            if index == 0 and item.get('offset') != 0:
                # Check the first received and figure out if we are missing the first FileData PDU (if offset != 0)
                start = 0
                end = item.get('offset')
                self.nak_list.append((start, end))
            elif index == len(received_list) - 1 and item.get('offset') + item.get(
                    'length') + 1 < self.metadata.file_size:
                # Check the last received and figure out if we are missing the last FileData PDU (if offset != file size)
                start = item.get('offset') + item.get('length')
                end = self.metadata.file_size
                self.nak_list.append((start, end))
            else:
                # Compare the item to the previous item to figure out if there is a gap between contiguous items
                prev_item = received_list[index - 1]
                if prev_item.get('offset') + prev_item.get('length') + 1 < item.get('offset'):
                    start = prev_item.get('offset') + prev_item.get('length')
                    end = item.get('offset')
                    self.nak_list.append((start, end))

        if self.metadata is None and not self.md_received:
            # Missing metadata start and end offset is 0
            self.nak_list.append((0, 0))

        return self.nak_list

    def make_ack_eof_pdu(self, condition_code):
        """
        :param directive_code: FileDirective type of PDU being ACKed
        :param condition_code: ConditionCode of the ACKed PDU
        :return:
        """
        header = copy.copy(self.header)
        header.pdu_type = Header.FILE_DIRECTIVE_PDU
        header.pdu_data_field_length = 3  # ACK pdu is 3 octets long
        directive_subtype_code = 0b0000
        ack = ACK(directive_code=FileDirective.EOF,
                  directive_subtype_code=directive_subtype_code,
                  condition_code=condition_code,
                  transaction_status=TransactionStatus.UNDEFINED,
                  header=header)
        self.ack_list.put(ack)

    def make_finished_pdu(self, condition_code, delivery_code, file_status):
        header = copy.copy(self.header)
        header.pdu_type = Header.FILE_DIRECTIVE_PDU
        header.pdu_data_field_length = 2 # finished pdu is 2 octets long
        finished = Finished(condition_code=condition_code,
                            end_system_status=Finished.END_SYSTEM,
                            delivery_code=delivery_code,
                            file_status=file_status,
                            header=header)
        self.finished_list.put(finished)

    def update_state(self, event=None, pdu=None, request=None):
        if self.state == self.S1:
            if event == Event.E5_SUSPEND_TIMERS:
                self.inactivity_timer.pause()

            elif event == Event.E6_RESUME_TIMERS:
                self.inactivity_timer.resume()

            elif event == Event.E12_RECEIVED_EOF_NO_ERROR_PDU:
                # Received EOF before receiving metadata
                ait.core.log.info("Receiver {0}: Received EOF NO ERROR PDU event".format(self.transaction.entity_id))
                assert (pdu)
                assert (type(pdu) == ait.dsn.cfdp.pdu.EOF)

                self.eof_received = True
                self.eof = pdu
                self.make_ack_eof_pdu(ConditionCode.NO_ERROR)

                # Write EOF to temp path
                incoming_pdu_path = os.path.join(self.kernel._data_paths['tempfiles'],
                                                 'eof_' + str(pdu.header.destination_entity_id) + '.pdu')
                ait.core.log.info('Writing EOF to path: ' + incoming_pdu_path)
                write_to_file(incoming_pdu_path, bytearray(pdu.to_bytes()))

                if self.metadata.file_transfer:
                    # Check received vs. reported file size
                    if self.transaction.recv_file_size != pdu.file_size:
                        ait.core.log.error('Receiver {0} -- file size fault. Received: {1}; Expected: {2}'
                                           .format(self.transaction.entity_id, self.transaction.recv_file_size,
                                                   pdu.file_size))
                        self.fault_handler(ConditionCode.FILE_SIZE_ERROR)

                if len(self.get_nak_list_from_received()) > 0:
                    self.enter_s2_state()
                else:
                    # if nak list empty, state = s3
                    ait.core.log.info('Receiver {0} -- NAK list is empty. Finishing and confirming delivery'.format(self.transaction.entity_id))
                    self.enter_s3_state()

            elif event == Event.E18_RECEIVED_ACK_FIN_NO_ERROR_PDU or event == Event.E18_RECEIVED_ACK_FIN_CANCEL_PDU:
                #: N/A
                return

            elif event == Event.E25_ACK_TIMER_EXPIRED:
                #: N/A
                return


        elif self.state == self.S2:
            if event == Event.E5_SUSPEND_TIMERS:
                self.inactivity_timer.pause()

            elif event == Event.E6_RESUME_TIMERS:
                self.inactivity_timer.resume()

            elif event == Event.E12_RECEIVED_EOF_NO_ERROR_PDU:
                self.make_ack_eof_pdu(ConditionCode.NO_ERROR)

            elif event == Event.E18_RECEIVED_ACK_FIN_NO_ERROR_PDU or event == Event.E18_RECEIVED_ACK_FIN_CANCEL_PDU:
                #: N/A
                return

            elif event == Event.E25_ACK_TIMER_EXPIRED:
                #: N/A
                return

            elif event == Event.E26_NAK_TIMER_EXPIRED:
                self.nak_count += 1  # increment NAK limit
                self.nak_timer.start(self.kernel.mib.nak_timeout(self.transaction.entity_id))
                self.get_nak_list_from_received()
                if len(self.nak_list) == 0:
                    ait.core.log.info("Receiver {0}: NAK Timer expired. Entering S3".format(self.transaction.entity_id))
                    self.enter_s3_state()
                elif not self.transaction.suspended and not self.transaction.frozen:
                    if self.nak_count >= self.kernel.mib.nak_limit(self.transaction.entity_id):
                        self.fault_handler(ConditionCode.NAK_LIMIT_REACHED)
                    ait.core.log.info("Receiver {0}: NAK Timer expired. NAK List {1}".format(self.transaction.entity_id, self.nak_list))
                    self.transmit_naks()

        elif self.state == self.S3:
            if event == Event.E5_SUSPEND_TIMERS:
                self.inactivity_timer.pause()
                self.ack_timer.pause()

            elif event == Event.E6_RESUME_TIMERS:
                self.inactivity_timer.resume()
                self.ack_timer.resume()

            elif event == Event.E10_RECEIVED_METADATA_PDU:
                #: N/A
                return

            elif event == Event.E11_RECEIVED_FILEDATA_PDU:
                #: N/A
                return

            elif event == Event.E12_RECEIVED_EOF_NO_ERROR_PDU:
                self.make_ack_eof_pdu(ConditionCode.NO_ERROR)

            elif event == Event.E18_RECEIVED_ACK_FIN_NO_ERROR_PDU or event == Event.E18_RECEIVED_ACK_FIN_CANCEL_PDU:
                self.finish_transaction()
                self.shutdown()

            elif event == Event.E25_ACK_TIMER_EXPIRED:
                self.ack_count += 1
                self.ack_timer.start(self.kernel.mib.ack_timeout(self.transaction.entity_id))
                if self.ack_count >= self.kernel.mib.ack_limit(self.transaction.entity_id):
                    self.fault_handler(ConditionCode.POSITIVE_ACK_LIMIT_REACHED)
                self.make_finished_pdu(ConditionCode.NO_ERROR, delivery_code=Finished.COMPLETE, file_status=FinishedPduFileStatus.FILE_RETAINED_SUCCESSFUL)

        elif self.state == self.S4:
            if event == Event.E3_NOTICE_OF_CANCELLATION:
                # N/A
                return

            elif event == Event.E5_SUSPEND_TIMERS:
                self.inactivity_timer.pause()
                self.ack_timer.pause()

            elif event == Event.E10_RECEIVED_METADATA_PDU:
                #: N/A
                return

            elif event == Event.E11_RECEIVED_FILEDATA_PDU:
                #: N/A
                return

            elif event == Event.E12_RECEIVED_EOF_NO_ERROR_PDU:
                #: N/A
                return

            elif event == Event.E18_RECEIVED_ACK_FIN_NO_ERROR_PDU:
                self.finish_transaction()
                self.shutdown()

            elif event == Event.E25_ACK_TIMER_EXPIRED:
                self.ack_count += 1
                self.ack_timer.start(self.kernel.mib.ack_timeout(self.transaction.entity_id))
                if self.ack_count >= self.kernel.mib.ack_limit(self.transaction.entity_id):
                    self.update_state(Event.E2_ABANDON_TRANSACTION)
                else:
                    self.make_finished_pdu(ConditionCode.CANCEL_REQUEST_RECEIVED, delivery_code=Finished.INCOMPLETE,
                                       file_status=FinishedPduFileStatus.FILE_STATUS_UNREPORTED)

            elif event == Event.E33_RECEIVED_CANCEL_REQUEST:
                #: N/A
                return

        # General events that apply to several states
        if event == Event.E0_SEND_FILE_DIRECTIVE:
            ait.core.log.debug("Receiver {0}: Received SEND FILE DIRECTIVE".format(self.transaction.entity_id))
            if self.transaction.frozen or self.transaction.suspended:
                return

            if len(self.ack_list) > 0:
                self.kernel.send(self.ack_list.get())

            elif len(self.finished_list) > 0:
                self.kernel.send(self.finished_list.get())

        elif event == Event.E2_ABANDON_TRANSACTION:
            self.abandon()

        elif event == Event.E3_NOTICE_OF_CANCELLATION:
            self.enter_s4_state()

        elif event == Event.E4_NOTICE_OF_SUSPENSION:
            self.suspend()
            if not self.transaction.frozen:
                self.suspend_timers()

        elif event == Event.E10_RECEIVED_METADATA_PDU:
            # S1 and S2
            ait.core.log.info("Receiver {0}: Received METADATA PDU event".format(self.transaction.entity_id))
            if self.md_received:
                return

            assert (pdu)
            assert (type(pdu) == ait.dsn.cfdp.pdu.Metadata)

            if not self.header:
                self.header = copy.copy(pdu.header)
            # Set id of the sender
            self.transaction.other_entity_id = pdu.header.source_entity_id
            # Save transaction metadata
            # Per blue book, receiving entity shall store
            #   - fault handler overrides
            #   - file size
            #   - flow label
            #   - file name information
            # all from the MD pdu. So we just store the MD pdu
            self.md_received = True
            self.metadata = pdu

            # Write out the MD pdu to the temp directory for now
            incoming_pdu_path = os.path.join(self.kernel._data_paths['tempfiles'],
                                             'md_' + str(pdu.header.destination_entity_id) + '.pdu')
            ait.core.log.info('Writing MD to path: ' + incoming_pdu_path)
            write_to_file(incoming_pdu_path, bytearray(pdu.to_bytes()))

            if self.metadata.file_transfer:
                # File transfer -- we will eventually received file data,
                # so we arrange for the eventual arrival of the file.
                # Get the file path of the final destination file
                # Get the absolute directory path so we can check if it exists,
                # and store the full file path for later use
                self.file_path = os.path.join(
                    os.path.join(self.kernel._data_paths['incoming'], pdu.destination_path))
                ait.core.log.info('File Destination Path: ' + self.file_path)

                # Open a temp file for incoming file data to go to
                # File name will be entity id and transaction id
                # Once the file transfer is done, this file will be removed
                temp_file_path = os.path.join(
                    self.kernel._data_paths['tempfiles'],
                    'tmp_transfer_{0}_{1}'.format(self.transaction.entity_id, self.transaction.transaction_id)
                )
                self.temp_path = temp_file_path
                try:
                    self.temp_file = open(temp_file_path, 'wb')
                except IOError:
                    ait.core.log.error('Receiver {0} -- could not open file: {1}'
                                       .format(self.transaction.entity_id, temp_file_path))
                    self.fault_handler(ConditionCode.FILESTORE_REJECTION)

            # Send MD Received Indication
            self.indication_handler(IndicationType.METADATA_RECV_INDICATION,
                                    transaction_id=self.transaction.transaction_id,
                                    source_entity_id=self.transaction.other_entity_id,
                                    source_path=pdu.source_path,
                                    destination_path=pdu.destination_path,
                                    messages_to_user=None)

            # TODO Process TLVs, not yet implemented
            # Messages to user, filestore requests, ...

        elif event == Event.E11_RECEIVED_FILEDATA_PDU:
            # S1 and S2
            ait.core.log.debug("Receiver {0}: Received FILE DATA PDU event".format(self.transaction.entity_id))
            # File data received before Metadata has been received
            assert (pdu)
            assert (type(pdu) == ait.dsn.cfdp.pdu.FileData)

            if not self.md_received or not self.metadata or not isinstance(self.metadata, Metadata):
                # Received a file data PDU before receiving metadata
                # Start & end offset of MD is 0
                pass

            # Store file data to temp file
            # Check that temp file is still open
            if self.temp_file is None or self.temp_file.closed:
                try:
                    self.temp_file = open(self.temp_path, 'wb')
                except IOError:
                    ait.core.log.error('Receiver {0} -- could not open file: {1}'
                                       .format(self.transaction.entity_id, self.temp_path))
                    return self.fault_handler(ConditionCode.FILESTORE_REJECTION)

            # Process FD if we have not received it yet
            if pdu.segment_offset not in self.received_map.keys():
                # Update file size
                self.transaction.recv_file_size += len(pdu.data)
                self.received_map[pdu.segment_offset] = len(pdu.data)

                incoming_pdu_path = os.path.join(self.kernel._data_paths['tempfiles'],
                                                 'fd_' + str(pdu.header.destination_entity_id) + '_{}.pdu'.format(pdu.segment_offset))
                ait.core.log.debug('Writing FD to path: ' + incoming_pdu_path)
                write_to_file(incoming_pdu_path, bytearray(pdu.to_bytes()))

                ait.core.log.debug('Writing file data: offset {0}, length {1}'.format(pdu.segment_offset, len(pdu.data)))
                # Seek offset to write in file if provided
                if pdu.segment_offset is not None:
                    self.temp_file.seek(pdu.segment_offset)
                self.temp_file.write(pdu.data)
                # Issue file segment received
                if self.kernel.mib.issue_file_segment_recv:
                    self.indication_handler(IndicationType.FILE_SEGMENT_RECV_INDICATION,
                                            transaction_id=self.transaction.transaction_id,
                                            offset=pdu.segment_offset,
                                            length=len(pdu.data))

        elif event == Event.E13_RECEIVED_EOF_CANCEL_PDU:
            self.transaction.condition_code = ConditionCode.CANCEL_REQUEST_RECEIVED
            self.make_ack_eof_pdu(ConditionCode.CANCEL_REQUEST_RECEIVED)
            self.finish_transaction()
            self.shutdown()

        elif event == Event.E27_INACTIVITY_TIMER_EXPIRED:
            # S1 - S3 only
            self.inactivity_timer.restart()
            self.fault_handler(ConditionCode.INACTIVITY_DETECTED)

        elif event == Event.E31_RECEIVED_SUSPEND_REQUEST:
            self.update_state(Event.E4_NOTICE_OF_SUSPENSION)

        elif event == Event.E32_RECEIVED_RESUME_REQUEST:
            if self.transaction.suspended is True:
                self.transaction.suspended = False
                self.indication_handler(IndicationType.RESUMED_INDICATION)
                if self.transaction.frozen is False:
                    self.update_state(Event.E6_RESUME_TIMERS)

        elif event == Event.E33_RECEIVED_CANCEL_REQUEST:
            self.transaction.condition_code = ConditionCode.CANCEL_REQUEST_RECEIVED
            self.update_state(Event.E3_NOTICE_OF_CANCELLATION)

        elif event == Event.E34_RECEIVED_REPORT_REQUEST:
            # User-issued report request
            self.indication_handler(IndicationType.REPORT_INDICATION)

        elif event == Event.E40_RECEIVED_FREEZE_REQUEST:
            if self.transaction.frozen is False:
                self.transaction.frozen = True
                if self.transaction.suspended is False:
                    self.update_state(Event.E5_SUSPEND_TIMERS)

        elif event == Event.E41_RECEIVED_THAW_REQUEST:
            if self.transaction.frozen is True:
                self.transaction.frozen = False
                if self.transaction.suspended is False:
                    self.update_state(Event.E6_RESUME_TIMERS)
