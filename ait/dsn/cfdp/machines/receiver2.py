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
from ait.dsn.cfdp.pdu import Metadata, Header, FileData, EOF
from ait.dsn.cfdp.primitives import Role, ConditionCode, IndicationType, DeliveryCode
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

    def enter_s2_state(self):
        """Get Missing Data state"""
        self.state = self.S2
        if not self.transaction.suspended and not self.transaction.frozen:
            # TODO transmit nak
            pass
        self.nak_timer.start()

    def enter_s3_state(self, event=None, pdu=None):
        """Send Finished PDU and COnfirm Delivery"""
        self.state = self.S3
        # At this point, all missing data should be resolved
        self.transaction.delivery_code = DeliveryCode.DATA_COMPLETE
        self.nak_timer.cancel()

        if self.metadata.file_transfer:
            # Close temp file
            if self.temp_file is not None and not self.temp_file.closed:
                self.temp_file.close()

            # Check received vs. reported file size
            if self.transaction.recv_file_size != pdu.file_size:
                ait.core.log.error('Receiver {0} -- file size fault. Received: {1}; Expected: {2}'
                                   .format(self.transaction.entity_id, self.transaction.recv_file_size, pdu.file_size))
                return self.fault_handler(ConditionCode.FILE_SIZE_ERROR)

            # Check checksum on the temp file before we save it to the actual destination
            temp_file_checksum = calc_checksum(self.temp_path)
            if temp_file_checksum != pdu.file_checksum:
                ait.core.log.error('Receiver {0} -- file checksum fault. Received: {1}; Expected: {2}'
                                   .format(self.transaction.entity_id, temp_file_checksum,
                                           pdu.file_checksum))
                return self.fault_handler(ConditionCode.FILE_CHECKSUM_FAILURE)

        # Copy temp file to destination path
        destination_directory_path = os.path.dirname(self.file_path)
        if not os.path.exists(destination_directory_path):
            os.makedirs(destination_directory_path)
        try:
            shutil.copy(self.temp_path, self.file_path)
        except IOError:
            return self.fault_handler(ConditionCode.FILESTORE_REJECTION)

        # TODO Filestore requests, not yet implemented
        # TODO 4.1.6.3.2 Unacknowledged Mode Procedures at the Receiving Entity check timer?

        # TODO Issue Finished No Error
        self.ack_timer.start()

    def enter_s4_state(self):
        if self.state == self.S3:
            # Possibly retain tmp file
            pass
        self.state = self.S4
        self.transaction.suspended = False
        self.transaction.cancelled = True
        self.finish_transaction()
        self.ack_timer.start()


    def update_state(self, event=None, pdu=None, request=None):
        if self.state == self.S1:
            if event == Event.E5_SUSPEND_TIMERS:
                self.inactivity_timer.pause()

            elif event == Event.E6_RESUME_TIMERS:
                self.inactivity_timer.resume()

            elif event == Event.E12_RECEIVED_EOF_NO_ERROR_PDU:
                ait.core.log.info("Receiver {0}: Received EOF NO ERROR PDU event".format(self.transaction.entity_id))
                assert (pdu)
                assert (type(pdu) == ait.dsn.cfdp.pdu.EOF)

                # TODO update nak list
                # TODO transmit ack eof

                # Write EOF to temp path
                incoming_pdu_path = os.path.join(self.kernel._data_paths['tempfiles'],
                                                 'eof_' + str(pdu.header.destination_entity_id) + '.pdu')
                ait.core.log.info('Writing EOF to path: ' + incoming_pdu_path)
                write_to_file(incoming_pdu_path, bytearray(pdu.to_bytes()))

                if self.metadata.file_transfer:
                    # Close temp file
                    if self.temp_file is not None and not self.temp_file.closed:
                        self.temp_file.close()

                    # Check received vs. reported file size
                    if self.transaction.recv_file_size != pdu.file_size:
                        ait.core.log.error('Receiver {0} -- file size fault. Received: {1}; Expected: {2}'
                                           .format(self.transaction.entity_id, self.transaction.recv_file_size,
                                                   pdu.file_size))
                        return self.fault_handler(ConditionCode.FILE_SIZE_ERROR)

                    # Check checksum on the temp file before we save it to the actual destination
                    temp_file_checksum = calc_checksum(self.temp_path)
                    if temp_file_checksum != pdu.file_checksum:
                        ait.core.log.error('Receiver {0} -- file checksum fault. Received: {1}; Expected: {2}'
                                           .format(self.transaction.entity_id, temp_file_checksum,
                                                   pdu.file_checksum))
                        return self.fault_handler(ConditionCode.FILE_CHECKSUM_FAILURE)

                # Copy temp file to destination path
                destination_directory_path = os.path.dirname(self.file_path)
                if not os.path.exists(destination_directory_path):
                    os.makedirs(destination_directory_path)
                try:
                    shutil.copy(self.temp_path, self.file_path)
                except IOError:
                    return self.fault_handler(ConditionCode.FILESTORE_REJECTION)

                # TODO if nak list empty, state = s3
                # TODO else state = s2

            elif event == Event.E18_RECEIVED_ACK_FIN_NO_ERROR_PDU or event == Event.E18_RECEIVED_ACK_FIN_CANCEL_PDU:
                return

            elif event == Event.E25_ACK_TIMER_EXPIRED:
                return


        elif self.state == self.S2:
            if event == Event.E5_SUSPEND_TIMERS:
                self.inactivity_timer.pause()

            elif event == Event.E6_RESUME_TIMERS:
                self.inactivity_timer.resume()

            elif event == Event.E12_RECEIVED_EOF_NO_ERROR_PDU:
                # TODO transmit ack eof
                pass

            elif event == Event.E18_RECEIVED_ACK_FIN_NO_ERROR_PDU or event == Event.E18_RECEIVED_ACK_FIN_CANCEL_PDU:
                return

            elif event == Event.E25_ACK_TIMER_EXPIRED:
                return

            elif event == Event.E26_NAK_TIMER_EXPIRED:
                self.nak_timer.start()
                # TODO if nak list empty, S3
                if not self.transaction.suspended and not self.transaction.frozen:
                    # TODO If nak limit reached, fault nak limit
                    pass
                # TODO fault transmit nak

        elif self.state == self.S3:
            if event == Event.E5_SUSPEND_TIMERS:
                self.inactivity_timer.pause()
                self.ack_timer.pause()

            elif event == Event.E6_RESUME_TIMERS:
                self.inactivity_timer.resume()
                self.ack_timer.resume()

            elif event == Event.E10_RECEIVED_METADATA_PDU:
                return

            elif event == Event.E11_RECEIVED_FILEDATA_PDU:
                return

            elif event == Event.E12_RECEIVED_EOF_NO_ERROR_PDU:
                # TODO transmit ack eof
                pass

            elif event == Event.E18_RECEIVED_ACK_FIN_NO_ERROR_PDU or event == Event.E18_RECEIVED_ACK_FIN_CANCEL_PDU:
                self.finish_transaction()
                self.shutdown()

            elif event == Event.E25_ACK_TIMER_EXPIRED:
                self.ack_timer.start()
                # TODO if ack limit reached, ack fault
                # TODO transmit finished

        elif self.state == self.S4:
            if event == Event.E3_NOTICE_OF_CANCELLATION:
                # N/A
                return

            elif event == Event.E5_SUSPEND_TIMERS:
                self.inactivity_timer.pause()
                self.ack_timer.pause()

            elif event == Event.E10_RECEIVED_METADATA_PDU:
                return

            elif event == Event.E11_RECEIVED_FILEDATA_PDU:
                return

            elif event == Event.E12_RECEIVED_EOF_NO_ERROR_PDU:
                return

            elif event == Event.E18_RECEIVED_ACK_FIN_NO_ERROR_PDU:
                self.finish_transaction()
                self.shutdown()

            elif event == Event.E25_ACK_TIMER_EXPIRED:
                self.ack_timer.start()
                # TODO if ack limit reached, E2
                # TODO else transmit finished

            elif event == Event.E33_RECEIVED_CANCEL_REQUEST:
                return

        # General events that apply to several states
        if event == Event.E2_ABANDON_TRANSACTION:
            self.abandon()

        elif event == Event.E3_NOTICE_OF_CANCELLATION:
            self.update_state(Event.E4_NOTICE_OF_SUSPENSION)

        elif event == Event.E4_NOTICE_OF_SUSPENSION:
            self.suspend()
            if not self.transaction.frozen:
                self.suspend_timers()

        elif event == Event.E10_RECEIVED_METADATA_PDU:
            # S1 and S2
            ait.core.log.info("Receiver {0}: Received METADATA PDU event".format(self.transaction.entity_id))
            if self.transaction.is_metadata_received:
                return

            assert (pdu)
            assert (type(pdu) == ait.dsn.cfdp.pdu.Metadata)

            self.transaction.is_metadata_received = True
            # Set id of the sender
            self.transaction.other_entity_id = pdu.header.source_entity_id
            # Save transaction metadata
            # Per blue book, receiving entity shall store
            #   - fault handler overrides
            #   - file size
            #   - flow label
            #   - file name information
            # all from the MD pdu. So we just store the MD pdu
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

            # TODO update nak list?

            # TODO Process TLVs, not yet implemented
            # Messages to user, filestore requests, ...

            # Set state to be awaiting EOF
            self.enter_s2_state()

        elif event == Event.E11_RECEIVED_FILEDATA_PDU:
            ait.core.log.info("Receiver {0}: Received FILE DATA PDU event".format(self.transaction.entity_id))
            # File data received before Metadata has been received
            assert (pdu)
            assert (type(pdu) == ait.dsn.cfdp.pdu.FileData)

            if self.metadata.file_transfer:
                # Store file data to temp file
                # Check that temp file is still open
                if self.temp_file is None or self.temp_file.closed:
                    try:
                        self.temp_file = open(self.temp_path, 'wb')
                    except IOError:
                        ait.core.log.error('Receiver {0} -- could not open file: {1}'
                                           .format(self.transaction.entity_id, self.temp_path))
                        return self.fault_handler(ConditionCode.FILESTORE_REJECTION)

                ait.core.log.info(
                    'Writing file data to file {0} with offset {1}'.format(self.temp_path, pdu.segment_offset))
                # Seek offset to write in file if provided
                if pdu.segment_offset is not None and pdu.segment_offset >= 0:
                    self.temp_file.seek(pdu.segment_offset)
                self.temp_file.write(pdu.data)
                # Update file size
                self.transaction.recv_file_size += len(pdu.data)
                # Issue file segment received
                if self.kernel.mib.issue_file_segment_recv:
                    self.indication_handler(IndicationType.FILE_SEGMENT_RECV_INDICATION,
                                            transaction_id=self.transaction.transaction_id,
                                            offset=pdu.segment_offset,
                                            length=len(pdu.data))
                # TODO updated nak list

        elif event == Event.E13_RECEIVED_EOF_CANCEL_PDU:
            self.transaction.condition_code = ConditionCode.CANCEL_REQUEST_RECEIVED
            # TODO transmit ack eof
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
