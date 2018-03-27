# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2017, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.

import binascii
import os

def string_length_in_bytes(s):
    if not isinstance(s, str):
        s = str(s)
    return len(s.encode('utf-8'))

def string_to_bytes(value):
    """
    Converts string value to binary of num_bytes length
    :param value:       value to convert
    :type value: str
    :param num_bytes:   byte length of value
    :type num_bytes: int
    :return: list of byte-chunks of binary string value
    """
    value = str(value)
    bytes_list = [int(binascii.hexlify(c), 16) for c in value]
    return bytes_list

def bytes_to_string(data_bytes):
    # convert int to hex
    hex_values = [format(b, '>02x') for b in data_bytes]
    str_values = [binascii.unhexlify(b) for b in hex_values]
    return ''.join(str_values)


def write_pdu_to_file(out_path, contents, offset=None):
    with open(out_path, 'wb') as f:
        if offset is not None and offset > 0:
            f.seek(offset)
        f.write(contents)


def calc_file_size(filepath):
    statinfo = os.stat(filepath)
    return statinfo.st_size


def check_file_structure(target_file, segmentation_control):
    # TODO implement segmentation control check
    return True


def checksum_of_word(word_list):
    """
    Returns of the value of a 4-byte word to be added to the running checksum.
    `word_list` should be an array of integers with max length 4 (more will be ignored),
    each integer representing a byte
    """
    if len(word_list) < 4:
        word_list.append(0)
    word = word_list[0] << 24
    word += word_list[1] << 16
    word += word_list[2] << 8
    word += word_list[3]
    return word

def calc_checksum(filename):
    try:
        checksum = 0
        open_file = open(filename, 'rb')
        file_size = calc_file_size(filename)

        # Checksum procedure
        # Mod 2^32 of 4 bytes words, aligned from start of file
        # Copy 1 byte of file data whose offset is mult of 4 (0, 4, 8, ...) into 1st higher order octet of word,
        # then copy  next 3 octets of file data into next 3 octets of word

        # Read file 4 bytes at a time while there is still data left to read
        # We want to pack each of the 4 bytes in order from high-order to low-order
        # E.g. if the four bytes read are 00 01 02 03, they will be packed into the first word as
        # 00010203 and summed which each subsequent similar word
        while open_file.tell() != file_size:
            # Convert file contents to list of bytes represented as integers
            # If there are less than 4 bytes, make it 4 by adding 0
            # Need to mash the bytes in the list into a single word
            byte_list = string_to_bytes(open_file.read(4))
            checksum += checksum_of_word(byte_list)
        open_file.close()

        # Must truncate it to 32 bits
        return checksum & 0xFFFFFFFF
    except IOError:
        return None

