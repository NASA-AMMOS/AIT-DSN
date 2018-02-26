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