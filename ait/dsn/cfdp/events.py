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

from enum import Enum

class Event(Enum):
    # USER
    RECEIVED_PUT_REQUEST = "RECEIVED_PUT_REQUEST"
    RECEIVED_SUSPEND_REQUEST = "RECEIVED_SUSPEND_REQUEST"
    RECEIVED_RESUME_REQUEST = "RECEIVED_RESUME_REQUEST"
    RECEIVED_CANCEL_REQUEST = "RECEIVED_CANCEL_REQUEST"
    RECEIVED_REPORT_REQUEST = "RECEIVED_REPORT_REQUEST"
    RECEIVED_FREEZE_REQUEST = "RECEIVED_FREEZE_REQUEST"
    RECEIVED_THAW_REQUEST = "RECEIVED_THAW_REQUEST"

    # Other events
    ABANDON_TRANSACTION = "ABANDON_TRANSACTION"
    NOTICE_OF_CANCELLATION = "NOTICE_OF_CANCELLATION"
    NOTICE_OF_SUSPENSION = "NOTICE_OF_SUSPENSION"

    # ENTITY
    RECEIVED_METADATA_PDU = "RECEIVED_METADATA_PDU"
    RECEIVED_FILEDATA_PDU = "RECEIVED_FILEDATA_PDU"
    RECEIVED_EOF_NO_ERROR_PDU = "RECEIVED_EOF_NO_ERROR_PDU"
    RECEIVED_ACK_EOF_NO_ERROR_PDU = "RECEIVED_ACK_EOF_NO_ERROR_PDU"
    RECEIVED_EOF_CANCEL_PDU = "RECEIVED_EOF_CANCEL_PDU"
    RECEIVED_ACK_EOF_CANCEL_PDU = "RECEIVED_ACK_EOF_CANCEL_PDU"
    RECEIVED_NAK_PDU = "RECEIVED_NAK_PDU"
    RECEIVED_FINISHED_NO_ERROR_PDU = "RECEIVED_FINISHED_NO_ERROR_PDU"
    RECEIVED_ACK_FIN_NO_ERROR_PDU = "RECEIVED_ACK_FIN_NO_ERROR_PDU"
    RECEIVED_FINISHED_CANCEL_PDU = "RECEIVED_FINISHED_CANCEL_PDU"
    RECEIVED_ACK_FIN_CANCEL_PDU = "RECEIVED_ACK_FIN_CANCEL_PDU"

    SEND_FILE_DIRECTIVE = "SEND_FILE_DIRECTIVE"
    SEND_FILE_DATA = "SEND_FILE_DATA"

    # TIMER
    ACK_TIMER_EXPIRED = "ACK_TIMER_EXPIRED"
    NAK_TIMER_EXPIRED = "NAK_TIMER_EXPIRED"
    INACTIVITY_TIMER_EXPIRED = "INACTIVITY_TIMER_EXPIRED"
