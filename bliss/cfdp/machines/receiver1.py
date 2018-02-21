import os
from machine import Machine
from bliss.cfdp.events import Event
from bliss.cfdp.util import write_pdu_to_file

import logging

class Receiver1(Machine):
    """
    Class 1 Receiver state machine
    """

    # State 1, waiting for metadata
    S1 = "WAIT_FOR_METADATA"
    # State 2, has received MD, waiting for EOF
    S2 = "WAIT_FOR_EOF"

    def update_state(self, event=None, pdu=None, request=None):
        """
        Evaluate a state change on received input
        :param event:
        :param pdu:
        :param request:
        :return:
        """

        # Receiver is waiting for metadata
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


            # NON-USER ISSUED
            elif event == Event.RECEIVED_METADATA_PDU:
                # We got a Metadata PDU, and so transaction starts
                assert(pdu)

                # For now, write to file
                dest_directory = os.path.join('/tmp/cfdp/incoming', os.path.dirname(pdu.destination_path))
                logging.debug('File Directory: ' + dest_directory)
                # TODO ensure path is relative
                self.file_path = os.path.join(os.path.join('/tmp/cfdp/incoming', pdu.destination_path))

                # Create destination directions -- this is where we will write from now on
                if not os.path.exists(dest_directory):
                    os.makedirs(dest_directory)

                # Write out metadata to incoming
                incoming_pdu_path = os.path.join(dest_directory, 'md_' + pdu.header.destination_entity_id + '.pdu')
                # Store path for future use
                logging.debug('Writing MD to path: ' + incoming_pdu_path)
                write_pdu_to_file(incoming_pdu_path, bytearray(pdu.to_bytes()))

                # Set state to be awaiting EOF
                self.state = self.S2
                pass
                # TODO ...
            elif event == Event.RECEIVED_FILEDATA_PDU:
                # File data received before Metadata has been received
                pass
            elif event == Event.RECEIVED_EOF_NO_ERROR_PDU:
                # Received EOF PDU before Metadata
                pass
            elif event == Event.RECEIVED_EOF_CANCEL_PDU:
                # Cancel PDU from other entity
                pass
            elif event == Event.INACTIVITY_TIMER_EXPIRED:
                pass
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

            # NON-USER ISSUED
            elif event == Event.RECEIVED_FILEDATA_PDU:
                # File data received before Metadata has been received
                assert(pdu)
                # Write file data to file
                logging.debug('Writing file data to file {0} with offset {1}'.format(self.file_path, pdu.segment_offset))
                write_pdu_to_file(self.file_path, pdu.data, offset=pdu.segment_offset)
            elif event == Event.RECEIVED_EOF_NO_ERROR_PDU:
                # Nominal case
                # Make the destination directory for the file
                dest_directory = os.path.dirname(self.file_path)
                logging.debug('File Directory: ' + dest_directory)
                # Write out metadata to incoming
                incoming_pdu_path = os.path.join(dest_directory, 'eof_' + pdu.header.destination_entity_id + '.pdu')
                logging.debug('Writing EOF to path: ' + incoming_pdu_path)
                write_pdu_to_file(incoming_pdu_path, bytearray(pdu.to_bytes()))
            elif event == Event.RECEIVED_EOF_CANCEL_PDU:
                # Cancel PDU from other entity
                pass
            elif event == Event.INACTIVITY_TIMER_EXPIRED:
                pass
            else:
                print "Ignoring received event: {}".format(event)
                pass