import os
from machine import Machine
from bliss.cfdp.events import Event
from bliss.cfdp.primitives import ConditionCode, IndicationType
from bliss.cfdp.util import write_pdu_to_file
from bliss.cfdp.timer import Timer


import logging

class Receiver1(Machine):
    """
    Class 1 Receiver state machine
    """

    # State 1, waiting for metadata
    S1 = "WAIT_FOR_METADATA"
    # State 2, has received MD, waiting for EOF
    S2 = "WAIT_FOR_EOF"

    def __init__(self, cfdp, transaction_count, *args, **kwargs):
        super(Receiver1, self).__init__(cfdp, transaction_count, *args, **kwargs)
        # start up timers
        self.inactivity_timer = Timer()
        # TODO add MIB timer value
        self.inactivity_timer.start(30)

    def save_file_data(self, contents, offset=None):
        # Writes file data to the open destination file
        if self.file is None or self.file.closed:
            # TODO raise fault
            return
        if offset is not None and offset >= 0:
            self.file.seek(offset)
        self.file.write(contents)

    def update_state(self, event=None, pdu=None, request=None):
        """
        Evaluate a state change on received input
        """

        # Receiver is waiting for metadata
        if self.state == self.S1:

            # USER-ISSUED REQUESTS (Rx)
            if event == Event.RECEIVED_CANCEL_REQUEST:
                logging.info("Receiver {0}: Received CANCEL REQUEST".format(self.transaction.entity_id))
                # User-issued request to cancel
                # TODO trigger NOTICE OF CANCELLATION
                self.transaction.condition_code = ConditionCode.CANCEL_REQUEST_RECEIVED
                self.cancel()
                self.finish_transaction()

            elif event == Event.RECEIVED_REPORT_REQUEST:
                logging.info("Receiver {0}: Received REPORT REQUEST".format(self.transaction.entity_id))
                # User-issued report request
                self.indication_handler(IndicationType.REPORT_INDICATION)
                pass


            # NON-USER ISSUED
            elif event == Event.ABANDON_TRANSACTION:
                logging.info("Receiver {0}: Received ABANDON event".format(self.transaction.entity_id))
                self.shutdown()

            elif event == Event.NOTICE_OF_CANCELLATION:
                logging.info("Receiver {0}: Received NOTICE OF CANCELLATION".format(self.transaction.entity_id))
                # Set eof to outgoing to send a Cancel EOF
                self.transaction.cancelled = True
                self.indication_handler(IndicationType.TRANSACTION_FINISHED_INDICATION)
                # Shutdown
                self.shutdown()

            elif event == Event.RECEIVED_METADATA_PDU:
                logging.info("Receiver {0}: Received METADATA PDU event".format(self.transaction.entity_id))
                # We got a Metadata PDU, and so transaction starts
                assert(pdu)

                self.transaction.other_entity_id = pdu.header.source_entity_id
                self.transaction.transaction_id = pdu.header.transaction_id

                # For now, write to file
                dest_directory = os.path.join('/tmp/cfdp/incoming', os.path.dirname(pdu.destination_path))
                logging.debug('File Directory: ' + dest_directory)
                # TODO ensure path is relative

                # this is the file path of destination path
                self.file_path = os.path.join(os.path.join('/tmp/cfdp/incoming', pdu.destination_path))

                # Create destination directions -- this is where we will write from now on
                if not os.path.exists(dest_directory):
                    os.makedirs(dest_directory)

                # Open a file to write to
                self.file = open(self.file_path, 'wb')
                # Write out metadata to incoming
                incoming_pdu_path = os.path.join(dest_directory, 'md_' + pdu.header.destination_entity_id + '.pdu')
                # Store path for future use
                logging.debug('Writing MD to path: ' + incoming_pdu_path)
                write_pdu_to_file(incoming_pdu_path, bytearray(pdu.to_bytes()))

                self.indication_handler(IndicationType.METADATA_RECV_INDICATION,
                                        transaction_id=self.transaction.transaction_id,
                                        source_entity_id=self.transaction.other_entity_id,
                                        source_path=pdu.source_path,
                                        destination_path=pdu.destination_path,
                                        messages_to_user=None)

                # Set state to be awaiting EOF
                self.state = self.S2

            elif event == Event.RECEIVED_EOF_NO_ERROR_PDU:
                logging.info("Receiver {0}: Received EOF NO ERROR PDU event".format(self.transaction.entity_id))
                # Received EOF PDU before Metadata
                self.finish_transaction()

            elif event == Event.RECEIVED_EOF_CANCEL_PDU:
                logging.info("Receiver {0}: Received EOF CANCEL PDU event".format(self.transaction.entity_id))
                # Cancel PDU from other entity
                self.finish_transaction()

            elif event == Event.INACTIVITY_TIMER_EXPIRED:
                logging.info("Receiver {0}: Received INACTIVITY TIMER EXPIRED event".format(self.transaction.entity_id))
                pass

            else:
                logging.debug("Receiver {0}: Ignoring received event {1}".format(self.transaction.entity_id, event))
                pass

        elif self.state == self.S2:
            # Metadata has already been received
            # This is the path for ongoing file transfer, awaiting EOF

            # USER-ISSUED REQUESTS (Rx)
            if event == Event.RECEIVED_CANCEL_REQUEST:
                logging.info("Receiver {0}: Received CANCEL REQUEST".format(self.transaction.entity_id))
                # User-issued request to cancel
                self.transaction.condition_code = ConditionCode.CANCEL_REQUEST_RECEIVED
                self.cancel()
                self.finish_transaction()

            elif event == Event.RECEIVED_REPORT_REQUEST:
                logging.info("Receiver {0}: Received REPORT REQUEST".format(self.transaction.entity_id))
                # User-issued report request
                self.indication_handler(IndicationType.REPORT_INDICATION)
                pass

            # NON-USER ISSUED
            elif event == Event.ABANDON_TRANSACTION:
                logging.info("Receiver {0}: Received ABANDON event".format(self.transaction.entity_id))
                self.shutdown()

            elif event == Event.RECEIVED_FILEDATA_PDU:
                logging.info("Receiver {0}: Received FILE DATA PDU event".format(self.transaction.entity_id))
                # File data received before Metadata has been received
                assert(pdu)
                # Write file data to file
                logging.debug('Writing file data to file {0} with offset {1}'.format(self.file_path, pdu.segment_offset))
                self.save_file_data(pdu.data, offset=pdu.segment_offset)
                self.indication_handler(IndicationType.FILE_SEGMENT_RECV_INDICATION,
                                        transaction_id=self.transaction.transaction_id,
                                        offset=pdu.segment_offset,
                                        length=len(pdu.data))

            elif event == Event.RECEIVED_EOF_NO_ERROR_PDU:
                logging.info("Receiver {0}: Received EOF NO ERROR PDU event".format(self.transaction.entity_id))
                # Nominal case
                # Make the destination directory for the file
                dest_directory = os.path.dirname(self.file_path)
                logging.debug('File Directory: ' + dest_directory)
                # Write out metadata to incoming
                incoming_pdu_path = os.path.join(dest_directory, 'eof_' + pdu.header.destination_entity_id + '.pdu')
                logging.debug('Writing EOF to path: ' + incoming_pdu_path)
                write_pdu_to_file(incoming_pdu_path, bytearray(pdu.to_bytes()))
                # TODO other checks, see cfs
                self.indication_handler(IndicationType.EOF_RECV_INDICATION,
                                        transaction_id=self.transaction.transaction_id)
                self.finish_transaction()

            elif event == Event.RECEIVED_EOF_CANCEL_PDU:
                logging.info("Receiver {0}: Received EOF CANCEL PDU event".format(self.transaction.entity_id))
                # Cancel PDU from other entity
                self.finish_transaction()

            elif event == Event.INACTIVITY_TIMER_EXPIRED:
                logging.info("Receiver {0}: Received INACTIVITY TIMER EXPIRED event".format(self.transaction.entity_id))
                pass

            else:
                logging.debug("Receiver {0}: Ignoring received event {1}".format(self.transaction.entity_id, event))
                pass