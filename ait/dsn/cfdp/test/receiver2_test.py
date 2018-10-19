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

import gevent
import traceback

import ait.core
import ait.core.log
from ait.dsn.cfdp import CFDP
from ait.dsn.cfdp.events import Event
from ait.dsn.cfdp.machines import Receiver2
from ait.dsn.cfdp.request import create_request_from_type
from ait.dsn.cfdp.cfdp import read_incoming_pdu, write_outgoing_pdu
from ait.dsn.cfdp.util import string_length_in_bytes, calc_file_size, check_file_structure, calc_checksum
from ait.dsn.cfdp.pdu import Header, Metadata, EOF, FileData, ACK, NAK, Finished
from ait.dsn.cfdp.primitives import ConditionCode, TransactionStatus, FileDirective, FinishedPduFileStatus, TransmissionMode, RequestType


TEST_DIRECTORY = os.path.join(os.path.dirname(__file__), '.pdusink')
def setUpModule():
    if not os.path.exists(TEST_DIRECTORY):
        os.makedirs(TEST_DIRECTORY)

def tearDownModule():
    if os.path.exists(TEST_DIRECTORY):
        shutil.rmtree(TEST_DIRECTORY)


class Receiver2AckTest(unittest.TestCase):

    full_source_path = None

    def setUp(self):
        self.cfdp = CFDP(1)
        self.source_path = 'medium.txt'
        self.destination_path = 'test/path/med.txt'
        self.full_source_path = os.path.join(self.cfdp._data_paths['outgoing'], self.source_path)
        self.full_dest_path = os.path.join(self.cfdp._data_paths['incoming'], self.destination_path)

        self.receiver = Receiver2(self.cfdp, 1)
        # setting the source path on this adhoc attribute so we can access it later in the mock
        self.receiver._full_source_path = self.full_source_path
        self.cfdp._machines[1] = self.receiver

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

    def test_sends_finished_no_error(self):
        """Test that after receiver has all retransmited data, it enters s3 and sends a Finished (no error) PDU"""

        def send(self, pdu):
            """Mock CFDP.send() for below test to catch when the receiver sends the NAK sequence. Then we can mimic the retransmission"""
            receiver = self._machines[1]
            full_source_path = receiver._full_source_path
            if type(pdu) == NAK:
                with open(full_source_path, 'rb') as file:
                    for segment in pdu.segment_requests:
                        offset = segment[0]
                        length = segment[1] - segment[0]
                        file.seek(offset)
                        chunk = file.read(length)
                        header = copy.copy(receiver.header)
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
                        receiver.update_state(event=Event.E11_RECEIVED_FILEDATA_PDU, pdu=fd)
            elif type(pdu) == Finished:
                # Mark that receiver sent a Fnished NO ERROR pdu
                receiver._finished_sent = (pdu.condition_code == ConditionCode.NO_ERROR)

        with mock.patch.object(ait.dsn.cfdp.CFDP, 'send', send):
            self.receiver._finished_sent = False
            my_nak_list = []
            self.receiver.update_state(event=Event.E10_RECEIVED_METADATA_PDU, pdu=self.metadata)
            for i in range(0, len(self.pdus)):
                # Only send every other file
                if i % 2 == 0:
                    self.receiver.update_state(event=Event.E11_RECEIVED_FILEDATA_PDU, pdu=self.pdus[i])
                else:
                    my_nak_list.append((self.pdus[i].segment_offset, self.pdus[i].segment_offset + len(self.pdus[i].data)))
            self.receiver.update_state(event=Event.E12_RECEIVED_EOF_NO_ERROR_PDU, pdu=self.eof)

            gevent.sleep(20) # sleep to await a few NAK timeouts to finish receiving pdus

            self.assertEqual(len(self.receiver.nak_list), 0)
            self.assertEqual(filecmp.cmp(self.full_source_path, self.full_dest_path, shallow=True), True, 'Source and destination files are equal.')
            self.assertEqual(self.receiver.state, self.receiver.S3)
            self.assertTrue(self.receiver._finished_sent)

    def test_transaction_notice_of_cancellation(self):
        """Ensure that when notice of cancellation is received, receiver enters S4 state and sends Finished (cancel) pdu"""
        self.receiver._sent_finished_cancel = False

        # Intercept sending of Finished (Cancel) pdu
        original_send = self.cfdp.send
        def send(self, pdu):
            receiver = self._machines[1]
            if type(pdu) == Finished and pdu.condition_code == ConditionCode.CANCEL_REQUEST_RECEIVED and receiver.state == receiver.S4:
                receiver._sent_finished_cancel = True
            else:
                original_send(pdu)

        with mock.patch.object(ait.dsn.cfdp.CFDP, 'send', send):
            self.receiver.update_state(event=Event.E10_RECEIVED_METADATA_PDU, pdu=self.metadata)
            self.receiver.update_state(event=Event.E3_NOTICE_OF_CANCELLATION)

            gevent.sleep(5)

            self.assertTrue(self.receiver._sent_finished_cancel)

    def test_send_ack_eof(self):
        """Ensure that receiver sends ACK EOF when receiving EOF no error"""
        self.receiver._send_ack_eof = False

        # Intercept sending of ACK EOF (No error) pdu
        original_send = self.cfdp.send
        def send(self, pdu):
            receiver = self._machines[1]
            if type(pdu) == ACK and pdu.directive_code == FileDirective.EOF and pdu.condition_code == ConditionCode.NO_ERROR and receiver.state == receiver.S1:
                receiver._send_ack_eof = True
            else:
                original_send(pdu)

        with mock.patch.object(ait.dsn.cfdp.CFDP, 'send', send):
            # Send all file PDUs as the sender
            self.receiver.update_state(event=Event.E10_RECEIVED_METADATA_PDU, pdu=self.metadata)
            for i in range(0, len(self.pdus)):
                self.receiver.update_state(event=Event.E11_RECEIVED_FILEDATA_PDU, pdu=self.pdus[i])
            self.receiver.update_state(event=Event.E12_RECEIVED_EOF_NO_ERROR_PDU, pdu=self.eof)

            gevent.sleep(5)

            self.assertTrue(self.receiver._send_ack_eof)

    def test_receives_all_file_data(self):
        """Ensure that receiver nak list is empty when all file data is received and that the source and destination files are equal"""

        self.receiver.update_state(event=Event.E10_RECEIVED_METADATA_PDU, pdu=self.metadata)
        for i in range(0, len(self.pdus)):
            self.receiver.update_state(event=Event.E11_RECEIVED_FILEDATA_PDU, pdu=self.pdus[i])
        self.receiver.update_state(event=Event.E12_RECEIVED_EOF_NO_ERROR_PDU, pdu=self.eof)

        gevent.sleep(5)

        # Assert nak list is 0 because we received everything
        self.assertEqual(len(self.receiver.nak_list), 0, 'No naks to be processed because all data is received.')
        self.assertEqual(filecmp.cmp(self.full_source_path, self.full_dest_path, shallow=True), True, 'Source and destination files are equal.')
        checksum = calc_checksum(self.full_dest_path)
        self.assertEqual(self.eof.file_checksum, checksum)

    def test_creates_naks_for_missing_data(self):
        """Ensure that receiver nak list is empty when all file data is received and that the source and destination files are equal"""

        my_nak_list = []
        self.receiver.update_state(event=Event.E10_RECEIVED_METADATA_PDU, pdu=self.metadata)
        for i in range(0, len(self.pdus)):
            # Only send every other file
            if i % 2 == 0:
                self.receiver.update_state(event=Event.E11_RECEIVED_FILEDATA_PDU, pdu=self.pdus[i])
            else:
                my_nak_list.append((self.pdus[i].segment_offset, self.pdus[i].segment_offset + len(self.pdus[i].data)))
        self.receiver.update_state(event=Event.E12_RECEIVED_EOF_NO_ERROR_PDU, pdu=self.eof)

        gevent.sleep(5)

        # Assert nak list is 0 because we received everything
        my_nak_list = sorted(my_nak_list, key=lambda x: x[0])
        self.assertItemsEqual(my_nak_list, self.receiver.nak_list, 'Receiver NAK list and recorded missed PDUs match')

    def test_receives_retransmitted_data(self):
        """Test that receiver appropriate receives the retransmitted missing data"""

        def send(self, pdu):
            """Mock CFDP.send() for below test to catch when the receiver sends the NAK sequence. Then we can mimic the retransmission"""
            receiver = self._machines[1]
            full_source_path = receiver._full_source_path
            if type(pdu) == NAK:
                with open(full_source_path, 'rb') as file:
                    for segment in pdu.segment_requests:
                        offset = segment[0]
                        length = segment[1] - segment[0]
                        file.seek(offset)
                        chunk = file.read(length)
                        header = copy.copy(receiver.header)
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
                        receiver.update_state(event=Event.E11_RECEIVED_FILEDATA_PDU, pdu=fd)

        with mock.patch.object(ait.dsn.cfdp.CFDP, 'send', send):
            my_nak_list = []
            self.receiver.update_state(event=Event.E10_RECEIVED_METADATA_PDU, pdu=self.metadata)
            for i in range(0, len(self.pdus)):
                # Only send every other file
                if i % 2 == 0:
                    self.receiver.update_state(event=Event.E11_RECEIVED_FILEDATA_PDU, pdu=self.pdus[i])
                else:
                    my_nak_list.append((self.pdus[i].segment_offset, self.pdus[i].segment_offset + len(self.pdus[i].data)))
            self.receiver.update_state(event=Event.E12_RECEIVED_EOF_NO_ERROR_PDU, pdu=self.eof)

            gevent.sleep(20) # sleep to await a few NAK timeouts

            self.assertEqual(len(self.receiver.nak_list), 0)
            self.assertEqual(filecmp.cmp(self.full_source_path, self.full_dest_path, shallow=True), True, 'Source and destination files are equal.')

    def test_initiate_cancel_sends_finished_cancel(self):
        """Test receiver initiated cancel. When cancel request is received, sender should send an Finished (cancel)"""
        self.receiver._finished_sent = False
        def send(self, pdu):
            receiver = self._machines[1]
            if type(pdu) == Finished and pdu.condition_code == ConditionCode.CANCEL_REQUEST_RECEIVED:
                receiver._finished_sent = True

        with mock.patch.object(ait.dsn.cfdp.CFDP, 'send', send):
            self.receiver.update_state(event=Event.E10_RECEIVED_METADATA_PDU, pdu=self.metadata)
            request = create_request_from_type(RequestType.CANCEL_REQUEST, transaction_id=self.receiver.transaction.transaction_id)
            self.receiver.update_state(event=Event.E30_RECEIVED_PUT_REQUEST, request=request)

            gevent.sleep(2)

            self.assertEqual(self.receiver.state, self.receiver.S4)
            self.assertTrue(self.receiver._finished_sent)

    def test_shutdown_on_ack_finished(self):
        """Test that when receiver receives ACK-Finished, the machine shuts down"""
        self.receiver._ack_fin = False
        self.receiver.update_state(event=Event.E10_RECEIVED_METADATA_PDU, pdu=self.metadata)
        gevent.sleep(1)

        self.receiver.state = self.receiver.S3
        header = copy.copy(self.header)
        header.source_entity_id = 2
        header.destination_entity_id = 1
        header.pdu_data_field_length = 3  # ACK pdu is 3 octets long
        ack_fin = ACK(header=header, directive_code=FileDirective.FINISHED, directive_subtype_code=0b0001, condition_code=ConditionCode.CANCEL_REQUEST_RECEIVED, transaction_status=TransactionStatus.TERMINATED)
        self.cfdp.send(ack_fin)

        gevent.sleep(10)

        self.assertTrue(self.receiver.transaction.finished)
        self.assertTrue(self.receiver.is_shutdown)
