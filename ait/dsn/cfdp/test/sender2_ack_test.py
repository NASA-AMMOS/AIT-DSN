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
from functools import partial
import filecmp
import mock
from random import randint

import gevent
import traceback

import ait.core
import ait.core.log
from ait.dsn.cfdp import CFDP
from ait.dsn.cfdp.events import Event
from ait.dsn.cfdp.machines import Sender2
from ait.dsn.cfdp.pdu import FileData, Metadata, EOF, NAK, ACK, Finished
from ait.dsn.cfdp.cfdp import read_incoming_pdu, write_outgoing_pdu
from ait.dsn.cfdp.request import create_request_from_type
from ait.dsn.cfdp.util import string_length_in_bytes, calc_file_size, check_file_structure, calc_checksum
from ait.dsn.cfdp.pdu import Header, Metadata, EOF, FileData, ACK, NAK, Finished
from ait.dsn.cfdp.primitives import ConditionCode, TransactionStatus, FileDirective, FinishedPduFileStatus, TransmissionMode, RequestType, DeliveryCode


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

        # CREATE PDUS
        self.pdus = []

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

        # MAKE FILE DATA PDUS
        with open(self.full_source_path, 'rb') as file:
            for chunk in iter(partial(file.read, 1024), ''):
                offset = file.tell() - len(chunk)
                header = copy.copy(self.header)
                header.pdu_type = Header.FILE_DATA_PDU

                # Calculate pdu data field length for header
                data_field_length_octets = 4
                # Get file data size
                data_field_length_octets += len(chunk)
                header.pdu_data_field_length = data_field_length_octets

                fd = FileData(
                    header=header,
                    segment_offset=offset,
                    data=chunk)
                self.pdus.append(fd)

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
