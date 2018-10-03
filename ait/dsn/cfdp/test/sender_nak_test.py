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
from ait.dsn.cfdp.pdu import FileData, Metadata, EOF, NAK
from ait.dsn.cfdp.cfdp import read_incoming_pdu, write_outgoing_pdu
from ait.dsn.cfdp.request import create_request_from_type
from ait.dsn.cfdp.util import string_length_in_bytes, calc_file_size, check_file_structure, calc_checksum
from ait.dsn.cfdp.pdu import Header, Metadata, EOF, FileData, ACK, NAK, Finished
from ait.dsn.cfdp.primitives import ConditionCode, TransactionStatus, DirectiveCode, FinishedPduFileStatus, TransmissionMode, RequestType


TEST_DIRECTORY = os.path.join(os.path.dirname(__file__), '.pdusink')
def setUpModule():
    if not os.path.exists(TEST_DIRECTORY):
        os.makedirs(TEST_DIRECTORY)

def tearDownModule():
    if os.path.exists(TEST_DIRECTORY):
        shutil.rmtree(TEST_DIRECTORY)


class Sender2NakTest(unittest.TestCase):

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

    def send(self, pdu):
        """Mock CFDP.send() to catch the Sender's pdus"""
        sender = self._machines[1]
        print '\n***CAUGHT SEND OF PDU***\n', pdu
        if type(pdu) == FileData:
            # skip random file data
            if randint(0, 9) % 2 == 0:
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


    @unittest.skip('TODO finish test implementation when ACK procedures are implemented')
    @mock.patch.object(ait.dsn.cfdp.CFDP, 'send', send)
    def test_sender2_resends_segment_requests(self):
        """Ensure that sender nak list is empty when all file data is received and that the source and destination files are equal"""

        request = create_request_from_type(RequestType.PUT_REQUEST,
                                           destination_id=2,
                                           source_path=self.source_path,
                                           destination_path=self.destination_path,
                                           transmission_mode=TransmissionMode.ACK)
        self.sender.update_state(event=Event.E30_RECEIVED_PUT_REQUEST, request=request)

        gevent.sleep(10)
