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

import os
import shutil

import ait.dsn.cfdp.pdu
from ait.dsn.cfdp.events import Event
from ait.dsn.cfdp.primitives import ConditionCode, IndicationType, DeliveryCode
from ait.dsn.cfdp.timer import Timer
from ait.dsn.cfdp.util import write_to_file, calc_checksum
from machine import Machine

import ait.core
import ait.core.log


class Receiver1(Machine):
    """
    Class 1 Receiver state machine
    """

    # State 1, waiting for metadata
    S1 = "WAIT_FOR_METADATA"
    # State 2, has received MD, waiting for EOF
    S2 = "WAIT_FOR_EOF"

    def __init__(self, cfdp, transaction_id, *args, **kwargs):
        super(Receiver1, self).__init__(cfdp, transaction_id, *args, **kwargs)
        # start up timers
        self.inactivity_timer = Timer()
        self.inactivity_timer.start(self.kernel.mib.inactivity_timeout(0))

    def update_state(self, event=None, pdu=None, request=None):
        """
        Evaluate a state change on received input
        """

        # Receiver is waiting for metadata
        if self.state == self.S1:

            # USER-ISSUED REQUESTS (Rx)
            if event == Event.RECEIVED_CANCEL_REQUEST:
                ait.core.log.info("Receiver {0}: Received CANCEL REQUEST".format(self.transaction.entity_id))
                # User-issued request to cancel
                self.transaction.condition_code = ConditionCode.CANCEL_REQUEST_RECEIVED
                self.update_state(Event.NOTICE_OF_CANCELLATION)

            elif event == Event.RECEIVED_REPORT_REQUEST:
                ait.core.log.info("Receiver {0}: Received REPORT REQUEST".format(self.transaction.entity_id))
                # User-issued report request
                self.indication_handler(IndicationType.REPORT_INDICATION)
                pass

            # NON-USER ISSUED
            elif event == Event.ABANDON_TRANSACTION:
                ait.core.log.info("Receiver {0}: Received ABANDON event".format(self.transaction.entity_id))
                self.shutdown()

            elif event == Event.NOTICE_OF_CANCELLATION:
                ait.core.log.info("Receiver {0}: Received NOTICE OF CANCELLATION".format(self.transaction.entity_id))
                self.cancel()
                self.finish_transaction()
                self.shutdown()

            elif event == Event.RECEIVED_METADATA_PDU:
                ait.core.log.info("Receiver {0}: Received METADATA PDU event".format(self.transaction.entity_id))
                assert(pdu)
                assert(type(pdu) == ait.dsn.cfdp.pdu.Metadata)

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
                incoming_pdu_path = os.path.join(self.kernel._data_paths['tempfiles'], 'md_' + str(pdu.header.destination_entity_id) + '.pdu')
                ait.core.log.info('Writing MD to path: ' + incoming_pdu_path)
                write_to_file(incoming_pdu_path, bytearray(pdu.to_bytes()))

                if self.metadata.file_transfer:
                    # File transfer -- we will eventually received file data,
                    # so we arrange for the eventual arrival of the file.
                    # Get the file path of the final destination file
                    # Get the absolute directory path so we can check if it exists,
                    # and store the full file path for later use
                    self.file_path = os.path.join(os.path.join(self.kernel._data_paths['incoming'], pdu.destination_path))
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

                # Set state to be awaiting EOF
                self.state = self.S2

            elif event == Event.RECEIVED_EOF_NO_ERROR_PDU:
                ait.core.log.info("Receiver {0}: Received EOF NO ERROR PDU event".format(self.transaction.entity_id))
                # Received EOF PDU before Metadata
                self.finish_transaction()

            elif event == Event.RECEIVED_EOF_CANCEL_PDU:
                ait.core.log.info("Receiver {0}: Received EOF CANCEL PDU event".format(self.transaction.entity_id))
                # This is a cancel PDU event from the other entity, so we just closed out the transaction
                self.finish_transaction()

            elif event == Event.INACTIVITY_TIMER_EXPIRED:
                ait.core.log.info("Receiver {0}: Received INACTIVITY TIMER EXPIRED event".format(self.transaction.entity_id))
                # Raise inactivity fault
                self.inactivity_timer.restart()
                self.fault_handler(ConditionCode.INACTIVITY_DETECTED)

            else:
                ait.core.log.debug("Receiver {0}: Ignoring received event {1}".format(self.transaction.entity_id, event))
                pass

        elif self.state == self.S2:
            # Metadata has already been received
            # This is the path for ongoing file transfer, awaiting EOF

            # USER-ISSUED REQUESTS (Rx)
            if event == Event.RECEIVED_CANCEL_REQUEST:
                ait.core.log.info("Receiver {0}: Received CANCEL REQUEST".format(self.transaction.entity_id))
                # User-issued request to cancel
                # Set the condition code of the transaction and close it out
                self.transaction.condition_code = ConditionCode.CANCEL_REQUEST_RECEIVED
                self.update_state(Event.NOTICE_OF_CANCELLATION)

            elif event == Event.RECEIVED_REPORT_REQUEST:
                ait.core.log.info("Receiver {0}: Received REPORT REQUEST".format(self.transaction.entity_id))
                # User-issued report request
                self.indication_handler(IndicationType.REPORT_INDICATION)
                pass

            # NON-USER ISSUED
            elif event == Event.ABANDON_TRANSACTION:
                ait.core.log.info("Receiver {0}: Received ABANDON event".format(self.transaction.entity_id))
                self.shutdown()

            elif event == Event.NOTICE_OF_CANCELLATION:
                ait.core.log.info("Receiver {0}: Received NOTICE OF CANCELLATION".format(self.transaction.entity_id))
                self.cancel()
                self.finish_transaction()
                self.shutdown()

            elif event == Event.RECEIVED_FILEDATA_PDU:
                ait.core.log.info("Receiver {0}: Received FILE DATA PDU event".format(self.transaction.entity_id))
                # File data received before Metadata has been received
                assert(pdu)
                assert(type(pdu) == ait.dsn.cfdp.pdu.FileData)

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

            elif event == Event.RECEIVED_EOF_NO_ERROR_PDU:
                ait.core.log.info("Receiver {0}: Received EOF NO ERROR PDU event".format(self.transaction.entity_id))
                assert(pdu)
                assert(type(pdu) == ait.dsn.cfdp.pdu.EOF)

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
                                      .format(self.transaction.entity_id, self.transaction.recv_file_size, pdu.file_size))
                        return self.fault_handler(ConditionCode.FILE_SIZE_ERROR)

                    # Check checksum on the temp file before we save it to the actual destination
                    temp_file_checksum = calc_checksum(self.temp_path)
                    if temp_file_checksum != pdu.file_checksum:
                        ait.core.log.error('Receiver {0} -- file checksum fault. Received: {1}; Expected: {2}'
                                             .format(self.transaction.entity_id, temp_file_checksum,
                                                     pdu.file_checksum))
                        return self.fault_handler(ConditionCode.FILE_CHECKSUM_FAILURE)

                self.transaction.delivery_code = DeliveryCode.DATA_COMPLETE

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

                # Issue EOF received indication
                if self.kernel.mib.issue_eof_recv:
                    self.indication_handler(IndicationType.EOF_RECV_INDICATION,
                                            transaction_id=self.transaction.transaction_id)
                self.finish_transaction()

            elif event == Event.RECEIVED_EOF_CANCEL_PDU:
                ait.core.log.info("Receiver {0}: Received EOF CANCEL PDU event".format(self.transaction.entity_id))
                # Cancel PDU from other entity
                self.finish_transaction()

            elif event == Event.INACTIVITY_TIMER_EXPIRED:
                ait.core.log.info("Receiver {0}: Received INACTIVITY TIMER EXPIRED event"
                                    .format(self.transaction.entity_id))
                self.inactivity_timer.restart()
                self.fault_handler(ConditionCode.INACTIVITY_DETECTED)

            else:
                ait.core.log.debug("Receiver {0}: Ignoring received event {1}".format(self.transaction.entity_id, event))
                pass
