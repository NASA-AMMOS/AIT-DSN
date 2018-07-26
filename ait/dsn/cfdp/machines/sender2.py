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
import gevent.queue

from ait.dsn.cfdp.events import Event
from ait.dsn.cfdp.pdu import Metadata, Header, FileData, EOF
from ait.dsn.cfdp.primitives import Role, ConditionCode, IndicationType
from ait.dsn.cfdp.util import string_length_in_bytes, calc_file_size, check_file_structure, calc_checksum
from sender1 import Sender1

import ait.core
import ait.core.log

class Sender2(Sender1):

    role = Role.CLASS_2_SENDER

    # Additional states for Class 2
    S3 = "SEND_EOF_FILL_GAPS"
    S4 = "TRANSACTION_CANCELLED"

    nak_queue = gevent.queue.Queue()

    def enter_s3_state(self, condition_code=None):
        """S3 : Send EOF, fill any gaps"""
        self.state = self.S3
        self.is_eof_outgoing = True
        self.transaction.condition_code = ConditionCode.NO_ERROR if condition_code is None else condition_code
        self.make_eof_pdu(self.transaction.condition_code)
        # Start ack and inactivity timers
        self.inactivity_timer.start()
        self.ack_timer.start()

    def enter_s4_state(self, condition_code=None):
        """S4 : Transaction cancelled"""
        self.state = self.S4
        self.transaction.suspended = False
        self.is_eof_outgoing = True
        self.transaction.condition_code = ConditionCode.CANCEL_REQUEST_RECEIVED if condition_code is None else condition_code
        self.make_eof_pdu(self.transaction.condition_code)
        # Start ack and inactivity timers
        self.ack_timer.start()


    def handle_file_transfer(self, outgoing_directory):
        '''Handles state transition from after receiving the MD PDU for copy file procedures'''

        # Copy File Procedures if the Put.request is a file transfer
        # For now it always is because Messages to User/TLV have not been implemented
        if self.metadata.file_transfer:
            self.enter_s2_state(outgoing_directory)
        else:
            self.enter_s3_state()

    def make_ack_finished_pdu(self):
        # TODO make ack finished
        pass

    def update_state(self, event=None, pdu=None, request=None):
        """
        Prompt for machine to evaluate a state. Could possibly or possibly not receive an event, pdu, or request to factor into state
        """

        if self.state == self.S1:

            # Only event in S1 with defined action is receiving a put request
            if event == Event.E30_RECEIVED_PUT_REQUEST:
                self.handle_put_request(request)

            # elif event == Event.E2_ABANDON_TRANSACTION:
            #     # E2: N/A
            #     pass
            #
            # elif event == Event.E3_NOTICE_OF_CANCELLATION:
            #     # E3 : N/A
            #     pass
            #
            # elif event == Event.E4_NOTICE_OF_SUSPENSION:
            #     # E4 : N/A
            #     pass
            #
            # elif event == Event.E5_SUSPEND_TIMERS:
            #     # E5 : N/A
            #     pass
            #
            # elif event == Event.E6_RESUME_TIMERS:
            #     # E6 : N/A
            #     pass
            #
            # elif event == Event.E14_RECEIVED_ACK_EOF_CANCEL_PDU or event == Event.E14_RECEIVED_ACK_EOF_NO_ERROR_PDU:
            #     # E14
            #     pass
            #
            # elif event == Event.E15_RECEIVED_NAK_PDU:
            #     # E15 : N/A
            #     pass
            #
            # elif event == Event.E17_RECEIVED_FINISHED_CANCEL_PDU:
            #     # E17
            #     pass
            #
            # elif event == Event.E25_ACK_TIMER_EXPIRED:
            #     # E25
            #     pass
            #
            # elif event == Event.E31_RECEIVED_SUSPEND_REQUEST:
            #     # E31: N/A
            #     pass
            #
            # elif event == Event.E32_RECEIVED_RESUME_REQUEST:
            #     # E32: N/A
            #     pass
            #
            # elif event == Event.E33_RECEIVED_CANCEL_REQUEST:
            #     # E33: N/A
            #     pass
            #
            # elif event == Event.E34_RECEIVED_REPORT_REQUEST:
            #     # E34: N/A
            #     pass
            #
            # elif event == Event.E40_RECEIVED_FREEZE_REQUEST:
            #     # E40: N/A
            #     pass
            #
            # elif event == Event.E41_RECEIVED_THAW_REQUEST:
            #     # #41: N/A
            #     pass
            #
            # elif event == Event.E1_SEND_FILE_DATA:
            #     # E1
            #     pass
            #
            # elif event == Event.E4_NOTICE_OF_SUSPENSION:
            #     pass
            #
            # elif event == Event.E17_RECEIVED_FINISHED_CANCEL_PDU:
            #     pass

            else:
                ait.core.log.debug("Sender {0}: Ignoring received event {1}".format(self.transaction.entity_id, event))
                pass

        elif self.state == self.S2:
            # Metadata has already been received
            # This is the path for ongoing file transfer (AKA "Send file once" for Class 2)

            # if event == Event.E15_RECEIVED_NAK_PDU:
            #     # E15
            #     pass
            #
            # elif event == Event.E5_SUSPEND_TIMERS:
            #     # E5 : N/A
            #     pass
            #
            # elif event == Event.E6_RESUME_TIMERS:
            #     # E6 : Trigger send file data (N/A)
            #     pass
            #
            # elif event == Event.E14_RECEIVED_ACK_EOF_CANCEL_PDU or event == Event.E14_RECEIVED_ACK_EOF_NO_ERROR_PDU:
            #     # E14
            #     pass

            if event == Event.E15_RECEIVED_NAK_PDU:
                # E15
                if self.transaction.suspended or self.transaction.frozen:
                    return
                # TODO queue nakked data

            elif event == Event.E25_ACK_TIMER_EXPIRED:
                # E25
                pass

            elif event == Event.E1_SEND_FILE_DATA:
                # E1: Please send file data
                if self.transaction.frozen or self.transaction.suspended:
                    return

                if self.nak_queue.empty():
                    return

                ait.core.log.debug("Sender {0}: Received SEND FILE DATA".format(self.transaction.entity_id))
                # Check if entire file is done being sent. If yes, queue up EOF
                # Send file data
                fd = self.nak_queue.get(block=False)
                self.kernel.send(fd)

            else:
                ait.core.log.debug("Sender {0}: Ignoring received event {1}".format(self.transaction.entity_id, event))
                pass

        elif self.state == self.S3:

            if event == Event.E14_RECEIVED_ACK_EOF_CANCEL_PDU or event == Event.E14_RECEIVED_ACK_EOF_NO_ERROR_PDU:
                ait.core.log.info("Sender {0}: Received CANCEL PDU event".format(self.transaction.entity_id))
                self.ack_timer.cancel()

            elif event == Event.E15_RECEIVED_NAK_PDU:
                ait.core.log.info("Sender {0}: Received NAK PDU event".format(self.transaction.entity_id))
                if not self.transaction.suspended and not self.transaction.frozen:
                    self.nak_queue.put() # TODO put data

            elif event ==  Event.E16_RECEIVED_FINISHED_NO_ERROR_PDU:
                # E14
                ait.core.log.info("Sender {0}: Received FINISH NO ERROR PDU event".format(self.transaction.entity_id))
                self.finish_transaction()

            elif event == Event.E15_RECEIVED_NAK_PDU:
                # E15
                if self.transaction.suspended or self.transaction.frozen:
                    return
                # TODO queue nakked data, trigger E1

            elif event == Event.E16_RECEIVED_FINISHED_NO_ERROR_PDU:
                # E16
                # transmit Ack Finished
                self.is_ack_outgoing = True
                self.make_ack_finished_pdu()
                # Issue Transaction finished
                # shutdown
                pass

            elif event == Event.E25_ACK_TIMER_EXPIRED:
                # E25
                # start ack time
                self.ack_timer.start()
                # FIXME if ack limit reached:
                self.fault_handler(ConditionCode.POSITIVE_ACK_LIMIT_REACHED)
                self.is_eof_outgoing = True
                self.make_eof_pdu(ConditionCode.POSITIVE_ACK_LIMIT_REACHED)

            elif event == Event.E27_INACTIVITY_TIMER_EXPIRED:
                # E27
                self.inactivity_timer.start()
                self.fault_handler(ConditionCode.INACTIVITY_DETECTED)

            elif event == Event.E1_SEND_FILE_DATA:
                # E1: Please send file data (S2 and S3 only)
                if self.transaction.frozen or self.transaction.suspended:
                    return

                if self.nak_queue.empty():
                    return

                ait.core.log.debug("Sender {0}: Received SEND FILE DATA".format(self.transaction.entity_id))
                # Check if entire file is done being sent. If yes, queue up EOF
                # Send file data
                fd = self.nak_queue.get(block=False)
                self.kernel.send(fd)

            else:
                ait.core.log.debug("Sender {0}: Ignoring received event {1}".format(self.transaction.entity_id, event))
                pass

        elif self.state == self.S4:

            # if event == Event.E3_NOTICE_OF_CANCELLATION:
            #     # E3 : N/A
            #     pass
            #
            # elif event == Event.E15_RECEIVED_NAK_PDU:
            #     # E15 n/a
            #     pass

            if event == Event.E14_RECEIVED_ACK_EOF_NO_ERROR_PDU:
                # E14
                self.finish_transaction()
                self.shutdown()

            elif event == Event.E25_ACK_TIMER_EXPIRED:
                # E25
                # start ack time
                self.ack_timer.start()
                if True:
                    # Trigger e2
                    self.update_state(Event.E2_ABANDON_TRANSACTION)
                else:
                    # Tx EOF
                    self.is_eof_outgoing = True
                    self.make_eof_pdu(ConditionCode.POSITIVE_ACK_LIMIT_REACHED)

            elif event == Event.E27_INACTIVITY_TIMER_EXPIRED:
                # E27
                self.abandon()
                self.shutdown()


        # COMMON EVENTS THAT ARE SHARED BY S2 - S4
        if event == Event.E2_ABANDON_TRANSACTION:
            # E2
            ait.core.log.info("Sender {0}: Received ABANDON event".format(self.transaction.entity_id))
            self.abandon()

        elif event == Event.E3_NOTICE_OF_CANCELLATION:
            # E3 (S2 and S3 only)
            ait.core.log.info("Sender {0}: Received NOTICE OF CANCELLATION".format(self.transaction.entity_id))
            # Set eof to outgoing to send a Cancel EOF
            self.enter_s4_state()

        elif event == Event.E4_NOTICE_OF_SUSPENSION:
            # E4
            ait.core.log.info("Sender {0}: Received NOTICE OF SUSPENSION".format(self.transaction.entity_id))
            self.suspend()
            if not self.transaction.frozen:
                self.suspend_timers()

        elif event == Event.E5_SUSPEND_TIMERS:
            # E5
            self.suspend_timers()

        elif event == Event.E6_RESUME_TIMERS:
            # E6
            self.resume_timers()

        elif event == Event.E16_RECEIVED_FINISHED_NO_ERROR_PDU:
            # E16 n/a
            pass

        elif event == Event.E17_RECEIVED_FINISHED_CANCEL_PDU:
            # E17
            # FIXME update with correct condition code
            self.transaction.condition_code = ConditionCode.NO_ERROR
            # issue transaction finished
            # shutdown

        elif event == Event.E17_RECEIVED_FINISHED_CANCEL_PDU:
            # E17
            if self.state == self.S1:
                return
            ait.core.log.info("Sender {0}: Received FINISH CANCEL PDU event".format(self.transaction.entity_id))
            self.transaction.condition_code = ConditionCode.CANCEL_REQUEST_RECEIVED
            self.finish_transaction()

        elif event == Event.E31_RECEIVED_SUSPEND_REQUEST:
            # E31
            ait.core.log.info("Sender {0}: Received SUSPEND REQUEST".format(self.transaction.entity_id))
            self.update_state(Event.E4_NOTICE_OF_SUSPENSION) # Trigger notice of suspension

        elif event == Event.E32_RECEIVED_RESUME_REQUEST:
            # E32
            ait.core.log.info("Sender {0}: Received RESUME REQUEST".format(self.transaction.entity_id))
            if self.transaction.suspended is True:
                self.transaction.suspended = False
                self.indication_handler(IndicationType.RESUMED_INDICATION) # TODO progress param?
                if self.transaction.frozen is False:
                    self.update_state(Event.E6_RESUME_TIMERS)

        elif event == Event.E33_RECEIVED_CANCEL_REQUEST:
            # E33 (S2 and S3 only)
            ait.core.log.info("Sender {0}: Received CANCEL REQUEST".format(self.transaction.entity_id))
            self.transaction.condition_code = ConditionCode.CANCEL_REQUEST_RECEIVED
            self.update_state(Event.E3_NOTICE_OF_CANCELLATION) # Trigger notice of cancellation

        elif event == Event.E34_RECEIVED_REPORT_REQUEST:
            # E34
            ait.core.log.info("Sender {0}: Received REPORT REQUEST".format(self.transaction.entity_id))
            # TODO logic to get report
            self.indication_handler(IndicationType.REPORT_INDICATION,
                                    status_report=None)

        elif event == Event.E40_RECEIVED_FREEZE_REQUEST:
            # E40
            ait.core.log.info("Sender {0}: Received FREEZE REQUEST".format(self.transaction.entity_id))
            if self.transaction.frozen is False:
                self.transaction.frozen = True
                if self.transaction.suspended is False:
                    self.update_state(Event.E5_SUSPEND_TIMERS)

        elif event == Event.E41_RECEIVED_THAW_REQUEST:
            # E41
            ait.core.log.info("Sender {0}: Received THAW REQUEST".format(self.transaction.entity_id))
            if self.transaction.frozen is True:
                self.transaction.frozen = False
                if self.transaction.suspended is False:
                    self.update_state(Event.E6_RESUME_TIMERS)
