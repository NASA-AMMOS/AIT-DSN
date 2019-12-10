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


from .md import Metadata
from .eof import EOF
from .filedata import FileData
from .header import Header
from ait.dsn.cfdp.primitives import FileDirective
import ait.core
import ait.core.log


def split_multiple_pdu_byte_array(pdu_bytes):
    """
    Splits single byte array list into list of multiple byte array lists
    corresponding to individual PDUs.
    """
    pdus_list = []
    pdu_start_index = 0
    while pdu_bytes:
        try:
            # get header, it will ignore extra bytes that do not belong to header
            header = Header.to_object(pdu_bytes)
            pdu_length = header.header_length + header.pdu_data_field_length
            # append list of only relevant bytes
            pdus_list.append(pdu_bytes[pdu_start_index:pdu_start_index + pdu_length])
            # set starting point for next PDU
            pdu_start_index = pdu_start_index + pdu_length
            # discard already used bytes
            pdu_bytes = pdu_bytes[pdu_start_index:]
        except Exception as e:
            ait.core.log.info('Unexpected error during CFDP PDU decoding. '
                              'Returning current PDU byte array list. \n {}'.format(e))
            return pdus_list

    return pdus_list


def make_pdu_from_bytes(pdu_bytes):
    """
    Figure out which type of PDU and return the appropriate class instance
    :param pdu_bytes:
    :return:
    """
    # get header, it will ignore extra bytes that do not belong to header
    header = Header.to_object(pdu_bytes)
    pdu_body = pdu_bytes[header.length:]
    if header.pdu_type == Header.FILE_DIRECTIVE_PDU:
        # make a file directive pdu by reading the directive code and making the appropriate object
        directive_code = FileDirective(pdu_body[0])
        if directive_code == FileDirective.METADATA:
            md = Metadata.to_object(pdu_body)
            md.header = header
            return md
        elif directive_code == FileDirective.EOF:
            eof = EOF.to_object(pdu_body)
            eof.header = header
            return eof
        elif directive_code == FileDirective.FINISHED:
            pass
        elif directive_code == FileDirective.ACK:
            pass
        elif directive_code == FileDirective.NAK:
            pass
        elif directive_code == FileDirective.PROMPT:
            pass
        elif directive_code == FileDirective.KEEP_ALIVE:
            pass
    elif header.pdu_type == Header.FILE_DATA_PDU:
        fd = FileData.to_object(pdu_body)
        fd.header = header
        return fd

    # TODO for now
    return header
