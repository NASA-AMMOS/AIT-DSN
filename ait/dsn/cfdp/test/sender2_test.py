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
import glob
import shutil
import unittest
import copy
import mock
from random import randint

import gevent

import ait.core
import ait.core.log
from ait.dsn.cfdp import CFDP
from ait.dsn.cfdp.events import Event
from ait.dsn.cfdp.machines import Sender2
from ait.dsn.cfdp.request import create_request_from_type
from ait.dsn.cfdp.util import string_length_in_bytes, calc_file_size, calc_checksum
from ait.dsn.cfdp.pdu import Header, Metadata, EOF, FileData, ACK, NAK, Finished
from ait.dsn.cfdp.primitives import ConditionCode, FinishedPduFileStatus, TransmissionMode, RequestType, DeliveryCode


TEST_DIRECTORY = os.path.join(os.path.dirname(__file__), '.pdusink')
def setUpModule():
    if not os.path.exists(TEST_DIRECTORY):
        os.makedirs(TEST_DIRECTORY)

def tearDownModule():
    if os.path.exists(TEST_DIRECTORY):
        shutil.rmtree(TEST_DIRECTORY)


class Sender2AckTest(unittest.TestCase):

    full_source_path = None

    def setUp(self):
        self.cfdp = CFDP(1)
        self.source_path = 'medium.txt'
        self.destination_path = 'test/path/med.txt'
        self.full_source_path = os.path.join(self.cfdp._data_paths['outgoing'], self.source_path)
        self.full_dest_path = os.path.join(self.cfdp._data_paths['incoming'], self.destination_path)

        self.sender = Sender2(self.cfdp, 1)
        # give sender a received list to keep track of PDUs to nak in the patched send method
        self.sender._received_list = []
        self.cfdp._machines[1] = self.sender

        # MAKE HEADER
        self.header = Header()
        self.header.direction = Header.TOWARDS_RECEIVER
        self.header.entity_ids_length = 8
        self.header.transaction_id_length = 8
        self.header.source_entity_id = 1
        self.header.transaction_id = 1
        self.header.destination_entity_id = 2
        self.header.transmission_mode = TransmissionMode.ACK

        # MAKE METADATA
        data_field_length_octets = 6
        # Each of these is +1 for 8 bit length field
        data_field_length_octets += (string_length_in_bytes(self.source_path) + 1)
        data_field_length_octets += (string_length_in_bytes(self.destination_path) + 1)
        self.header.pdu_data_field_length = data_field_length_octets

        file_size = calc_file_size(self.full_source_path)

        # Copy header
        header = copy.copy(self.header)
        header.pdu_type = Header.FILE_DIRECTIVE_PDU
        self.metadata = Metadata(
            header=header,
            source_path=self.source_path,
            destination_path=self.destination_path,
            file_size=file_size)

        # MAKE EOF
        header = copy.copy(self.header)
        header.pdu_type = Header.FILE_DIRECTIVE_PDU
        data_field_length_octets = 10
        header.pdu_data_field_length = data_field_length_octets

        self.eof = EOF(
            header=header,
            condition_code=ConditionCode.NO_ERROR,
            file_checksum=calc_checksum(self.full_source_path),
            file_size=self.metadata.file_size
        )

    def tearDown(self):
        self.fixture = None
        for f in glob.glob(os.path.join(TEST_DIRECTORY, '*')):
            os.remove(f)

        self.cfdp.disconnect()

        # clear data from datasink
        if os.path.exists(self.cfdp._data_paths['incoming']):
            shutil.rmtree(self.cfdp._data_paths['incoming'])
            os.makedirs(self.cfdp._data_paths['incoming'])

        if os.path.exists(self.cfdp._data_paths['tempfiles']):
            shutil.rmtree(self.cfdp._data_paths['tempfiles'])
            os.makedirs(self.cfdp._data_paths['tempfiles'])

        if os.path.exists(self.cfdp._data_paths['pdusink']):
            shutil.rmtree(self.cfdp._data_paths['pdusink'])
            os.makedirs(self.cfdp._data_paths['pdusink'])

    def _test_ack_finished(self, header, condition_code):
        self.sender._sent_ack = False
        original_send = self.cfdp.send
        def send(self, pdu):
            sender = self._machines[1]
            if type(pdu) == ACK:
                sender._sent_ack = True
            else:
                original_send(pdu)

        with mock.patch.object(ait.dsn.cfdp.CFDP, 'send', send):
            finished = Finished(condition_code=condition_code,
                                end_system_status=Finished.END_SYSTEM,
                                delivery_code=DeliveryCode.DATA_INCOMPLETE,
                                file_status=FinishedPduFileStatus.FILE_STATUS_UNREPORTED)
            finished.header = header
            self.cfdp.send(finished)

            gevent.sleep(5)

            # Markers to check that transaction was finished out
            self.assertTrue(self.sender.transaction.finished)
            self.assertTrue(self.sender.is_shutdown)
            self.assertEqual(self.sender.file, None)
            self.assertEqual(self.sender.temp_file, None)
            self.assertTrue(self.sender._sent_ack)

    def test_sends_ack_finished_cancel_s2(self):
        """Ensure sender sends Ack-Finished PDU when a Finished (Cancel) PDU is received in S2 state"""

        request = create_request_from_type(RequestType.PUT_REQUEST,
                                           destination_id=2,
                                           source_path=self.source_path,
                                           destination_path=self.destination_path,
                                           transmission_mode=TransmissionMode.ACK)
        self.sender.update_state(event=Event.E30_RECEIVED_PUT_REQUEST, request=request)
        gevent.sleep(1)

        # Make copy of header going from Receiver to Sender to mock finished PDU
        header = copy.copy(self.header)
        header.source_entity_id = 2
        header.destination_entity_id = 1

        self.sender.state = self.sender.S2
        self._test_ack_finished(header, ConditionCode.CANCEL_REQUEST_RECEIVED)

    def test_sends_ack_finished_cancel_s3(self):
        """Ensure sender sends Ack-Finished PDU when a Finished (Cancel) PDU is received in S3 state"""

        request = create_request_from_type(RequestType.PUT_REQUEST,
                                           destination_id=2,
                                           source_path=self.source_path,
                                           destination_path=self.destination_path,
                                           transmission_mode=TransmissionMode.ACK)
        self.sender.update_state(event=Event.E30_RECEIVED_PUT_REQUEST, request=request)
        gevent.sleep(1)

        # Make copy of header going from Receiver to Sender to mock finished PDU
        header = copy.copy(self.header)
        header.source_entity_id = 2
        header.destination_entity_id = 1

        self.sender.state = self.sender.S3
        self._test_ack_finished(header, ConditionCode.CANCEL_REQUEST_RECEIVED)

    def test_sends_ack_finished_cancel_s4(self):
        """Ensure sender sends Ack-Finished PDU when a Finished (Cancel) PDU is received in S4 state"""

        request = create_request_from_type(RequestType.PUT_REQUEST,
                                           destination_id=2,
                                           source_path=self.source_path,
                                           destination_path=self.destination_path,
                                           transmission_mode=TransmissionMode.ACK)
        self.sender.update_state(event=Event.E30_RECEIVED_PUT_REQUEST, request=request)
        gevent.sleep(1)

        # Make copy of header going from Receiver to Sender to mock finished PDU
        header = copy.copy(self.header)
        header.source_entity_id = 2
        header.destination_entity_id = 1

        self.sender.state = self.sender.S4
        self._test_ack_finished(header, ConditionCode.CANCEL_REQUEST_RECEIVED)

    def test_sends_ack_finished_no_error(self):
        """Ensure sender sends Ack-Finished PDU when a Finished (No error) PDU is received in S3 state"""

        request = create_request_from_type(RequestType.PUT_REQUEST,
                                           destination_id=2,
                                           source_path=self.source_path,
                                           destination_path=self.destination_path,
                                           transmission_mode=TransmissionMode.ACK)
        self.sender.update_state(event=Event.E30_RECEIVED_PUT_REQUEST, request=request)
        gevent.sleep(1)

        # Make copy of header going from Receiver to Sender to mock finished PDU
        header = copy.copy(self.header)
        header.source_entity_id = 2
        header.destination_entity_id = 1

        self.sender.state = self.sender.S3
        self._test_ack_finished(header, ConditionCode.NO_ERROR)

    def test_ack_timeout_s3(self):
        """Ensure that Sender sends EOF when ack timeout is reached in S3"""
        self.sender._sent_eof = False
        self.sender._ack_timeout_reached = False
        def send(self, pdu):
            sender = self._machines[1]
            # set flag to True to denote that we resent the already stored EOF (sender.eof) after the timeout was reached
            if type(pdu) == EOF and sender._ack_timeout_reached is True and sender.eof is not None and type(sender.eof) == EOF:
                sender._sent_eof = True

        original_update_state = self.sender.update_state
        def update_state(self, event=None, pdu=None, request=None):
            """Intercept the ACK TIME EXPIRED event of Sender 2"""
            if self.state == self.S3 and event == Event.E25_ACK_TIMER_EXPIRED:
                self._ack_timeout_reached = True
            original_update_state(event=event, pdu=pdu, request=request)

        with mock.patch.object(ait.dsn.cfdp.CFDP, 'send', send):
            with mock.patch.object(ait.dsn.cfdp.machines.Sender2, 'update_state', update_state):
                request = create_request_from_type(RequestType.PUT_REQUEST,
                                                   destination_id=2,
                                                   source_path=self.source_path,
                                                   destination_path=self.destination_path,
                                                   transmission_mode=TransmissionMode.ACK)
                self.sender.update_state(event=Event.E30_RECEIVED_PUT_REQUEST, request=request)

                gevent.sleep(20) # wait for ACK timeout

                # Markers to check that transaction was finished out
                self.assertTrue(self.sender._ack_timeout_reached)
                self.assertTrue(self.sender._sent_eof)

    def test_sender2_resends_segment_requests(self):
        """Ensure that sender received list if complete when simulating re-transmission of FD PDUs when NAK is received"""

        def send(self, pdu):
            """Mock CFDP.send() to catch the Sender's pdus"""
            sender = self._machines[1]
            if type(pdu) == FileData:
                if sender.state == sender.S2:
                    # In the initial File Sending state (sending file for the first time)
                    # skip random file data and mock receipt by adding to _received_list
                    if randint(0, 9) % 2 == 0:
                        sender._received_list.append({'offset': pdu.segment_offset, 'length': len(pdu.data)})
                elif sender.state == sender.S3:
                    # In the second File Sending state (Send EOF and fill gaps after receiving NAK)
                    # Add them to _received_list to mock receipt of the re-sent pdus
                    sender._received_list.append({'offset': pdu.segment_offset, 'length': len(pdu.data)})

            elif type(pdu) == EOF:
                # Received EOF, so evaluate the missed PDUs and create a NAK sequence
                received_list = sorted(sender._received_list, key=lambda x: x.get('offset'))
                nak_list = []
                for index, item in enumerate(received_list):
                    if index == 0 and item.get('offset') != 0:
                        # Check the first received and figure out if we are missing the first FileData PDU (if offset != 0)
                        start = 0
                        end = item.get('offset')
                        nak_list.append((start, end))
                    elif index == len(received_list) - 1 and item.get('offset') + item.get(
                            'length') + 1 < sender.metadata.file_size:
                        # Check the last received and figure out if we are missing the last FileData PDU (if offset != file size)
                        start = item.get('offset') + item.get('length')
                        end = sender.metadata.file_size
                        nak_list.append((start, end))
                    else:
                        # Compare the item to the previous item to figure out if there is a gap between contiguous items
                        prev_item = received_list[index - 1]
                        if prev_item.get('offset') + prev_item.get('length') + 1 < item.get('offset'):
                            start = prev_item.get('offset') + prev_item.get('length')
                            end = item.get('offset')
                            nak_list.append((start, end))

                # create the NAK pdu
                start_scope = 0
                end_scope = sender.metadata.file_size
                nak = NAK(header=sender.header, start_of_scope=start_scope, end_of_scope=end_scope,
                          segment_requests=nak_list)
                sender.kernel.send(nak)

            elif type(pdu) == NAK:
                # Catch the sending of the NAK and treat is as if receiving NAK from the receiver. Transmit the missing data
                sender.update_state(Event.E15_RECEIVED_NAK_PDU, pdu=pdu)

        with mock.patch.object(ait.dsn.cfdp.CFDP, 'send', send):
            request = create_request_from_type(RequestType.PUT_REQUEST,
                                               destination_id=2,
                                               source_path=self.source_path,
                                               destination_path=self.destination_path,
                                               transmission_mode=TransmissionMode.ACK)
            self.sender.update_state(event=Event.E30_RECEIVED_PUT_REQUEST, request=request)

            gevent.sleep(5)

            # Ensure _received_list contains full set of pdus
            received = sorted(self.sender._received_list, key=lambda x: x.get('offset'))
            received_length = 0  # pointer to contiguous segment in file
            for segment in received:
                if received_length != segment.get('offset'):
                    self.assertTrue(False, "Received file data are not contiguous")
                received_length += segment.get('length')

            self.assertEqual(received_length, self.sender.metadata.file_size, 'File size is same as total length of contiguous received data')
            self.assertEqual(len(self.sender.nak_queue), 0)

    def test_initiate_cancel_sends_eof_cancel(self):
        """Test sender initiated cancel. When cancel request is received, sender should send an EOF (cancel)"""
        self.sender._eof_sent = False
        def send(self, pdu):
            sender = self._machines[1]
            if type(pdu) == EOF and pdu.condition_code == ConditionCode.CANCEL_REQUEST_RECEIVED:
                sender._sent_eof = True

        with mock.patch.object(ait.dsn.cfdp.CFDP, 'send', send):
            request = create_request_from_type(RequestType.PUT_REQUEST,
                                               destination_id=2,
                                               source_path=self.source_path,
                                               destination_path=self.destination_path,
                                               transmission_mode=TransmissionMode.ACK)
            self.sender.update_state(event=Event.E30_RECEIVED_PUT_REQUEST, request=request)

            gevent.sleep(2)

            request = create_request_from_type(RequestType.CANCEL_REQUEST, transaction_id=self.sender.transaction.transaction_id)
            self.sender.update_state(event=Event.E33_RECEIVED_CANCEL_REQUEST, request=request)

            gevent.sleep(2)

            self.assertEqual(self.sender.state, self.sender.S4)
            self.assertTrue(self.sender._eof_sent)
