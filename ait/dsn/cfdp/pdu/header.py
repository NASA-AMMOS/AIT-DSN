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

import struct
from ait.dsn.cfdp.util import string_length_in_bytes, string_to_bytes, bytes_to_string
from ait.dsn.cfdp.primitives import TransmissionMode

import ait.core


def int_to_byte_list(value):
    value_binary_str = format(value,
                                       '>0{}b'.format((value.bit_length() / 8 + 1) * 8))
    value_byte_list = []
    for index in range(len(value_binary_str) / 8):
        value_byte_list.append(int(value_binary_str[index:index + 8], 2))
    return value_byte_list

class Header(object):
    # Header Flag Values
    # TODO move where it makes more sense
    FILE_DIRECTIVE_PDU = 0
    FILE_DATA_PDU = 1
    TOWARDS_RECEIVER = 0
    TOWARDS_SENDER = 1
    CRC_NOT_PRESENT = 0
    CRC_PRESENT = 1

    TRANSACTION_SEQ_NUM_LENGTH = 4

    def __init__(self, *args, **kwargs):
        """
        Representation of PDU Fixed Header
        :param version:                         3 bit; version number 000 first version
        :type version: int
        :param pdu_type:                        1 bit; '0' for File Directive, '1' for File Data
        :type pdu_type: int
        :param direction:                       1 bit; '0' for toward file receiver, '1' for toward file sender
        :type direction: int
        :param transmission_mode:               1 bit; '0' for acknowledged, '1' for unack
        :type transmission_mode: int
        :param crc_flag:                        1 bit; '0' for CRC not present; '1' for CRC present
        :type crc_flag: int
        :param pdu_data_field_length:           16 bit; length of data field in octets
        :type pdu_data_field_length: int
        :param entity_ids_length:               3 bit; number of octets in entity ID (source or destination entity) - 1. E.g. '0' mean sequence number is 1 octet
        :type entity_ids_length: int
        :param transaction_id_length:      3 bit; number of octets in sequence number - 1
        :type transaction_id_length: int
        :param source_entity_id:                variable bit; uniquely identifies the entity that originated transaction. Unsigned binary int. See entity_ids_length for length
        :type source_entity_id: str
        :param transaction_id:             variable bit; uniquely identifies the entity that originated transaction. Unsigned binary int. See transaction_id_length for length
        :type transaction_id: str
        :param destination_entity_id:              variable bit; uniquely identifies the entity that originated transaction. Unsigned binary int. See entity_ids_length for length
        :type destination_entity_id: str
        """
        # valid flag to make sure contents are valid and of appropriate length
        self._valid = False
        self._errors = None

        # store raw header
        self.version = kwargs.get('version', 0)
        self.pdu_type = kwargs.get('pdu_type', self.FILE_DIRECTIVE_PDU)
        self.direction = kwargs.get('direction', self.TOWARDS_RECEIVER)
        self.transmission_mode = kwargs.get('transmission_mode', TransmissionMode.NO_ACK)
        self.crc_flag = kwargs.get('crc_flag', self.CRC_NOT_PRESENT)
        self.pdu_data_field_length = kwargs.get('pdu_data_field_length', None)
        self.source_entity_id = kwargs.get('source_entity_id', None)
        self.transaction_id = kwargs.get('transaction_id', None)
        self.destination_entity_id = kwargs.get('destination_entity_id', None)
        self.entity_ids_length = kwargs.get('entity_ids_length', None)
        self.transaction_id_length = kwargs.get('transaction_id_length', None)

    def __copy__(self):
        newone = type(self)()
        newone.__dict__.update(self.__dict__)
        return newone

    @property
    def length(self):
        """Byte length of Header"""
        return len(self.to_bytes())

    def is_valid(self):
        """Check if all header fields are valid length"""
        # TODO put in checks
        self._valid = True
        self._errors = None
        return self._valid

    def to_bytes(self):
        """
        Encode PDU to a raw bytes (string) format to be transmitted

        Each byte is encoded into an int representation of the binary, and added to a list of bytes in order.
        All the bytes are then packed into a struct.
        """
        if not self.is_valid():
            raise Exception('Header contents invalid. {}'.format(self._errors))

        header_bytes = []

        # --- BYTE 1 ---
        # First byte of the header comprised of:
        #   version (3)
        #   pdu_type (1)
        #   direction (1)
        #   transmission_mode (1)
        #   crc flag (1)
        #   reserved (1) (set to 0)

        # Create hex mask to encode version in first 3 bits
        # Convert version to binary string
        # Truncate at 3 bits
        bin_version = format(self.version & 0x7, '03b')
        # Right pad to 8 bits
        bin_version = format(bin_version, '<08s')
        # Convert version encoded in first 3 bits of a byte into an integer
        version_hex_int = int(bin_version, 2)
        # Start masking rest of the byte from here
        byte_1 = version_hex_int
        if self.pdu_type == self.FILE_DATA_PDU:
            byte_1 = byte_1 | 0x10
        if self.direction == self.TOWARDS_SENDER:
            byte_1 = byte_1 | 0x08
        if self.transmission_mode == TransmissionMode.NO_ACK:
            byte_1 = byte_1 | 0x04
        if self.crc_flag == self.CRC_PRESENT:
            byte_1 = byte_1 | 0x02
        # Append first byte int value. Later we will pack a struct
        header_bytes.append(byte_1)

        # --- BYTES 2 and 3 ---
        #   PDU Data Field Length (16)
        # Split value into 2 8 bit values
        bin_pdu_length = format(self.pdu_data_field_length, '016b')
        # Convert each half to and integer and append
        header_bytes.append(int(bin_pdu_length[0:8], 2))
        header_bytes.append(int(bin_pdu_length[8:], 2))

        # --- BYTE 4 ---
        # Byte comprised of:
        #   reserved (1)
        #   entity ids length (3)
        #   reserved (1)
        #   transaction seq num length (3)

        # If we were not provided a length before, do the work to calculate it
        if not self.entity_ids_length:
            # Get longer entity id length between source and destination
            if isinstance(self.source_entity_id, int):
                # calculate bit length as bytes. Round up (+1) if it's not a whole number
                source_entity_id_length = self.source_entity_id.bit_length()/8 + 1
            else:
                source_entity_id_length = string_length_in_bytes(str(self.source_entity_id))

            if isinstance(self.destination_entity_id, int):
                dest_entity_id_length = self.destination_entity_id.bit_length()/8 + 1
            else:
                dest_entity_id_length = string_length_in_bytes(str(self.destination_entity_id))

            entity_id_byte_length = source_entity_id_length \
                if source_entity_id_length > dest_entity_id_length \
                else dest_entity_id_length
            self.entity_ids_length = entity_id_byte_length

        # If we were not provided a length before, do the work to calculate it
        if not self.transaction_id_length:
            trans_seq_num_byte_len = (self.transaction_id.bit_length()/8 + 1)
            self.transaction_id_length = trans_seq_num_byte_len

        # Mask for only right 3 bits and convert to 4 bit binary string (left-most bit should be 0 for  placeholder)
        bin_entity_id_length = format(self.entity_ids_length-1 & 0x7, '04b')
        bin_trans_seq_num_len = format(self.transaction_id_length-1 & 0x7, '04b')
        byte_4 = int(bin_entity_id_length + bin_trans_seq_num_len, 2)
        header_bytes.append(byte_4)

        # --- REMAINING BYTES ---
        # Variable in size depending on the lengths defined above
        #   source entity id (variable)
        #   transaction seq num (variable)
        #   destination entity id (variable)

        if not isinstance(self.source_entity_id, int):
            source_id_bytes = string_to_bytes(str(self.source_entity_id))
            len_of_source_id_bytes = len(source_id_bytes)
        else:
            len_of_source_id_bytes = self.source_entity_id.bit_length()/8 + 1
            source_id_bytes = int_to_byte_list(self.source_entity_id)
        source_id_bytes = [0] * (self.entity_ids_length - len_of_source_id_bytes) + source_id_bytes
        header_bytes.extend(source_id_bytes)

        # Transaction ID is a number. Format as binary with minimum size caluclated above
        len_of_trans_id = self.transaction_id.bit_length() / 8 + 1
        transaction_id_bytes = int_to_byte_list(self.transaction_id)
        transaction_id_bytes = [0] * (self.transaction_id_length - len_of_trans_id) + transaction_id_bytes
        header_bytes.extend(transaction_id_bytes)

        if not isinstance(self.destination_entity_id, int):
            destination_id_binary = string_to_bytes(str(self.destination_entity_id))
            len_of_destination_id_binary = len(destination_id_binary)
        else:
            len_of_destination_id_binary = self.destination_entity_id.bit_length()/8 + 1
            destination_id_binary = int_to_byte_list(self.destination_entity_id)
        destination_id_binary = [0] * (self.entity_ids_length - len_of_destination_id_binary) + destination_id_binary
        header_bytes.extend(destination_id_binary)

        return header_bytes

    @staticmethod
    def to_object(pdu_hdr):
        """Return PDU subclass object created from given bytes of data"""

        if not isinstance(pdu_hdr, list):
            raise ValueError('pdu header should be a list of bytes represented as integers')

        if len(pdu_hdr) < 4:
            raise ValueError('pdu header should be at least 4 bytes long')

        # --- BYTE 1 ---
        # First byte of the header comprised of:
        # version (3), pdu_type (1), direction (1), transmission_mode (1), crc flag (1)
        byte_1 = pdu_hdr[0]
        # Mask first 3 bits and right shift 5 to get version
        version = (byte_1 & 0xe0) >> 5
        # If masked bit is > 0, it's a file data pdu. Otherwise bit is 0 and its file directive
        pdu_type = Header.FILE_DATA_PDU if (byte_1 & 0x10) else Header.FILE_DIRECTIVE_PDU
        direction = Header.TOWARDS_SENDER if (byte_1 & 0x08) else Header.TOWARDS_RECEIVER
        transmission_mode = TransmissionMode.NO_ACK if (byte_1 & 0x04) else TransmissionMode.ACK
        crc_flag = Header.CRC_PRESENT if (byte_1 & 0x02) else Header.CRC_NOT_PRESENT

        # --- BYTES 2 and 3 ---
        #   PDU Data Field Length (16)
        byte_2 = pdu_hdr[1]
        byte_3 = pdu_hdr[2]
        # left shift first byte 4 to get right position of bits
        pdu_data_length = byte_2 << 4
        pdu_data_length += byte_3

        # --- BYTE 4 ---
        # Byte comprised of:
        #   reserved (1), entity ids length (3), reserved (1), transaction seq num length (3)
        byte_4 = pdu_hdr[3]
        # mask the appropriate bits just for good measure
        entity_ids_length = (byte_4 & 0x70) >> 4
        # add one because value is "length less 1"
        entity_ids_length += 1
        transaction_id_length = (byte_4 & 0x7) + 1

        # Remaining bytes, use length values above to figure out
        pdu_hdr_length = len(pdu_hdr)
        expected_length = 4 + entity_ids_length*2 + transaction_id_length
        if pdu_hdr_length < expected_length:
            raise ValueError('pdu header is not big enough to contain entity ids and trans. seq. number. '
                             'header is only {0} bytes, expected {1} bytes'.format(pdu_hdr_length, expected_length))

        # source id
        start_index = 4
        end_index = start_index + entity_ids_length
        # source_entity_id = bytes_to_string(pdu_hdr[start_index:end_index])

        # convert list of bytes (as integers) to list of binary strings
        # Join into a mega-binary string and conver to into
        source_entity_id = int(''.join([format(b, '>08b') for b in pdu_hdr[start_index:end_index]]), 2)

        # tx seq num
        start_index = end_index
        end_index = start_index + transaction_id_length
        # transaction_id = bytes_to_string(pdu_hdr[start_index:end_index])
        transaction_id = int(''.join([format(b, '>08b') for b in pdu_hdr[start_index:end_index]]), 2)

        # destination id
        start_index = end_index
        end_index = start_index + entity_ids_length
        # destination_entity_id = bytes_to_string(pdu_hdr[start_index:end_index])
        destination_entity_id = int(''.join([format(b, '>08b') for b in pdu_hdr[start_index:end_index]]), 2)

        return Header(
            version=version,
            pdu_type=pdu_type,
            direction=direction,
            transmission_mode=transmission_mode,
            crc_flag=crc_flag,
            pdu_data_field_length=pdu_data_length,
            source_entity_id=source_entity_id,
            transaction_id=transaction_id,
            destination_entity_id=destination_entity_id,
            entity_ids_length = entity_ids_length,
            transaction_id_length = transaction_id_length
        )
