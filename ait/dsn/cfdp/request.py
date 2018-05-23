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

from collections import namedtuple
from primitives import RequestType

Request = namedtuple('Request', [
    'type',
    'info'
])


def create_request_from_type(request_type, *args, **kwargs):
    if request_type == RequestType.PUT_REQUEST:
        destination_id = kwargs.get('destination_id', None)
        source_path = kwargs.get('source_path', None)
        destination_path = kwargs.get('destination_path', None)
        transmission_mode = kwargs.get('transmission_mode', None)

        info = {
            'destination_id': destination_id,
            'source_path': source_path,
            'destination_path': destination_path,
            'transmission_mode': transmission_mode
        }
        return Request(request_type, info)
    elif request_type == RequestType.REPORT_REQUEST:
        transaction_id = kwargs.get('transaction_id', None)
        info = {
            'transaction_id': transaction_id
        }
        return Request(request_type, info)
    elif request_type == RequestType.CANCEL_REQUEST:
        transaction_id = kwargs.get('transaction_id', None)
        info = {
            'transaction_id': transaction_id
        }
        return Request(request_type, info)
    elif request_type == RequestType.SUSPEND_REQUEST:
        transaction_id = kwargs.get('transaction_id', None)
        info = {
            'transaction_id': transaction_id
        }
        return Request(request_type, info)
    elif request_type == RequestType.RESUME_REQUEST:
        transaction_id = kwargs.get('transaction_id', None)
        info = {
            'transaction_id': transaction_id
        }
        return Request(request_type, info)
