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
import mock

import gevent

import ait.core
import ait.core.log
from ait.dsn.cfdp import CFDP
from ait.dsn.cfdp.events import Event
from ait.dsn.cfdp.machines import Sender1
from ait.dsn.cfdp.pdu import FileData, Metadata, EOF, Header
from ait.dsn.cfdp.request import create_request_from_type
from ait.dsn.cfdp.util import string_length_in_bytes, calc_file_size, calc_checksum
from ait.dsn.cfdp.primitives import ConditionCode, TransmissionMode, RequestType


TEST_DIRECTORY = os.path.join(os.path.dirname(__file__), '.pdusink')
def setUpModule():
    if not os.path.exists(TEST_DIRECTORY):
        os.makedirs(TEST_DIRECTORY)

def tearDownModule():
    if os.path.exists(TEST_DIRECTORY):
        shutil.rmtree(TEST_DIRECTORY)


class Sender1Test(unittest.TestCase):

    full_source_path = None

    def setUp(self):
        self.cfdp = CFDP(1)
        self.source_path = 'medium.txt'
        self.destination_path = 'test/path/med.txt'
        self.full_source_path = os.path.join(self.cfdp._data_paths['outgoing'], self.source_path)
        self.full_dest_path = os.path.join(self.cfdp._data_paths['incoming'], self.destination_path)

        self.sender = Sender1(self.cfdp, 1)
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

    def test_send_file_data(self):
        """Test that sender sends PDUs for all contiguous pieces of file data"""
        original_send = self.cfdp.send
        def send(self, pdu):
            """Mock CFDP.send() to catch the Sender's pdus"""
            sender = self._machines[1]
            if type(pdu) == FileData:
                sender._received_list.append({'offset': pdu.segment_offset, 'length': len(pdu.data), 'type': 'FD'})
            elif type(pdu) == EOF:
                # Received EOF, so evaluate the missed PDUs and create a NAK sequence
                sender._received_list.append({'offset': 0, 'length': 0, 'type': 'EOF'})
            elif type(pdu) == Metadata:
                sender._received_list.append({'offset': 0, 'length': 0, 'type': 'MD'})
            original_send(pdu)

        with mock.patch.object(ait.dsn.cfdp.CFDP, 'send', send):
            self.sender._received_list = []  # give sender a received list to keep track of received PDUs
            request = create_request_from_type(RequestType.PUT_REQUEST,
                                               destination_id=2,
                                               source_path=self.source_path,
                                               destination_path=self.destination_path,
                                               transmission_mode=TransmissionMode.NO_ACK)
            self.sender.update_state(event=Event.E30_RECEIVED_PUT_REQUEST, request=request)

            gevent.sleep(5)

            # Ensure _received_list contains full set of pdus
            received = sorted(self.sender._received_list, key=lambda x: x.get('offset'))
            received_length = 0  # pointer to contiguous segment in file
            received_md = False
            received_eof = False
            for segment in received:
                if segment.get('type') == 'MD':
                    received_md = True
                elif segment.get('type') == 'EOF':
                    received_eof = True
                elif received_length != segment.get('offset'):
                    self.assertTrue(False, "Received file data are not contiguous")
                received_length += segment.get('length')

            self.assertEqual(received_length, self.sender.metadata.file_size,
                             'File size is same as total length of contiguous received data')
            self.assertTrue(received_md)
            self.assertTrue(received_eof)
            self.assertTrue(self.sender.eof_sent)
            self.assertTrue(self.sender.md_sent)

    def test_cancel(self):
        original_send = self.cfdp.send

        def send(self, pdu):
            """Mock CFDP.send() to catch the Sender's pdus"""
            sender = self._machines[1]
            if type(pdu) == EOF and pdu.condition_code == ConditionCode.CANCEL_REQUEST_RECEIVED:
                sender._eof_cancel_sent = True
            original_send(pdu)

        with mock.patch.object(ait.dsn.cfdp.CFDP, 'send', send):
            self.sender._eof_cancel_sent = False
            request = create_request_from_type(RequestType.PUT_REQUEST,
                                               destination_id=2,
                                               source_path=self.source_path,
                                               destination_path=self.destination_path,
                                               transmission_mode=TransmissionMode.NO_ACK)
            self.sender.update_state(event=Event.E30_RECEIVED_PUT_REQUEST, request=request)

            gevent.sleep(2)
            self.sender.update_state(event=Event.E33_RECEIVED_CANCEL_REQUEST)
            gevent.sleep(2)

            self.assertTrue(self.sender._eof_cancel_sent, 'EOF Cancel was sent')
            self.assertTrue(self.sender.is_shutdown, 'Sender is shutdown')
            self.assertTrue(self.sender.transaction.finished, 'Transaction is finished')
