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


class MachineState(Enum):
    SEND_METADATA = "SEND_METADATA"
    SEND_FILEDATA = "SEND_FILEDATA"


class TransmissionMode(Enum):
    ACK = "ACK"
    NO_ACK = "NO_ACK"


class RequestType(Enum):
    """
    Request primitives that CFDP service consumes
    """
    PUT_REQUEST = "PUT_REQUEST"
    REPORT_REQUEST = "REPORT_REQUEST"
    CANCEL_REQUEST = "CANCEL_REQUEST"
    SUSPEND_REQUEST = "SUSPEND_REQUEST"
    RESUME_REQUEST = "RESUME_REQUEST"


class IndicationType(Enum):
    """
    Request primitives that CFDP service Delivers
    """

    TRANSACTION_INDICATION = "TRANSACTION_INDICATION"
    EOF_SENT_INDICATION = "EOF_SENT_INDICATION"
    TRANSACTION_FINISHED_INDICATION = "TRANSACTION_FINISHED_INDICATION"
    METADATA_RECV_INDICATION = "METADATA_RECV_INDICATION"
    FILE_SEGMENT_RECV_INDICATION = "FILE_SEGMENT_RECV_INDICATION"
    REPORT_INDICATION = "REPORT_INDICATION"
    SUSPENDED_INDICATION = "SUSPENDED_INDICATION"
    RESUMED_INDICATION = "RESUMED_INDICATION"
    FAULT_INDICATION = "FAULT_INDICATION"
    ABANDONED_INDICATION = "ABANDONED_INDICATION"
    EOF_RECV_INDICATION = "EOF_RECV_INDICATION"


class Role(Enum):
    UNDEFINED = "UNDEFINED"
    CLASS_1_RECEIVER = "CLASS_1_RECEIVER"
    CLASS_1_SENDER = "CLASS_1_SENDER"
    CLASS_2_RECEIVER = "CLASS_2_RECEIVER"
    CLASS_2_SENDER = "CLASS_2_SENDER"


class FileDirective(Enum):
    EOF = 0x4
    FINISHED = 0x5
    ACK = 0x6
    METADATA = 0x7
    NAK = 0x8
    PROMPT = 0x9
    KEEP_ALIVE = 0xC


class ConditionCode(Enum):
    NO_ERROR = 0
    POSITIVE_ACK_LIMIT_REACHED = 1
    KEEP_ALIVE_LIMIT_REACHED = 2
    INVALID_TRANSMISSION_MODE = 3
    FILESTORE_REJECTION = 4
    FILE_CHECKSUM_FAILURE = 5
    FILE_SIZE_ERROR = 6
    NAK_LIMIT_REACHED = 7
    INACTIVITY_DETECTED = 8
    INVALID_FILE_STRUCTURE = 9
    CHECK_LIMIT_REACHED = 10
    SUSPEND_REQUEST_RECEIVED = 14
    CANCEL_REQUEST_RECEIVED = 15


class HandlerCode(Enum):
    """0, 5 - 15 are reserved"""
    CANCEL = 1
    SUSPEND = 2
    IGNORE = 3
    ABANDON = 4


class DeliveryCode(Enum):
    DATA_COMPLETE = "DATA_COMPLETE"
    DATA_INCOMPLETE = "DATA_INCOMPLETE"


class FinalStatus(Enum):
    FINAL_STATUS_UNKNOWN = "FINAL_STATUS_UNKNOWN"
    FINAL_STATUS_SUCCESSFUL = "FINAL_STATUS_SUCCESSFUL"
    FINAL_STATUS_CANCELLED = "FINAL_STATUS_CANCELLED"
    FINAL_STATUS_ABANDONED = "FINAL_STATUS_ABANDONED"
    FINAL_STATUS_NO_METADATA = "FINAL_STATUS_NO_METADATA"


class TimerType(Enum):
    NO_TIMER = "NO_TIMER"
    ACK_TIMER = "ACK_TIMER"
    NAK_TIMER = "NAK_TIMER"
    INACTIVITY_TIMER = "INACTIVITY_TIMER"
