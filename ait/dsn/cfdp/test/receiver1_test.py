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

import gevent

from ait.dsn.cfdp import CFDP
from ait.dsn.cfdp.events import Event
from ait.dsn.cfdp.machines import Receiver1
from ait.dsn.cfdp.util import string_length_in_bytes, calc_file_size, calc_checksum
from ait.dsn.cfdp.pdu import Header, Metadata, EOF, FileData
from ait.dsn.cfdp.primitives import ConditionCode, TransmissionMode


TEST_DIRECTORY = os.path.join(os.path.dirname(__file__), '.pdusink')
def setUpModule():
    if not os.path.exists(TEST_DIRECTORY):
        os.makedirs(TEST_DIRECTORY)

def tearDownModule():
    if os.path.exists(TEST_DIRECTORY):
        shutil.rmtree(TEST_DIRECTORY)


class Receiver1Test(unittest.TestCase):

    full_source_path = None

    def setUp(self):
        self.cfdp = CFDP(2)
        self.source_path = 'medium.txt'
        self.destination_path = 'test/path/med.txt'
        self.full_source_path = os.path.join(self.cfdp._data_paths['outgoing'], self.source_path)
        self.full_dest_path = os.path.join(self.cfdp._data_paths['incoming'], self.destination_path)

        self.receiver = Receiver1(self.cfdp, 1)
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
            os.makedirs(self.cfdp._data_paaths['pdusink'])

    def test_receive_file_data(self):
        """Ensure receiver receives all file data"""
        self.receiver.update_state(event=Event.E10_RECEIVED_METADATA_PDU, pdu=self.metadata)
        for i in range(0, len(self.pdus)):
            self.receiver.update_state(event=Event.E11_RECEIVED_FILEDATA_PDU, pdu=self.pdus[i])
        self.receiver.update_state(event=Event.E12_RECEIVED_EOF_NO_ERROR_PDU, pdu=self.eof)

        gevent.sleep(5)

        # Assert nak list is 0 because we received everything
        self.assertEqual(filecmp.cmp(self.full_source_path, self.full_dest_path, shallow=True), True,
                         'Source and destination files are equal.')


