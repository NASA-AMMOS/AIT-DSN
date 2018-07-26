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

import copy
import os
import gevent.queue

from ait.dsn.cfdp.events import Event
from ait.dsn.cfdp.pdu import Metadata, Header, FileData, EOF
from ait.dsn.cfdp.primitives import Role, ConditionCode, IndicationType
from ait.dsn.cfdp.util import string_length_in_bytes, calc_file_size, check_file_structure, calc_checksum
from receiver1 import Receiver1

import ait.core
import ait.core.log

class Receiver2(Receiver1):

    S1 = "WAIT_FOR_EOF"
    S2 = "GET_MISSING_DATA"
    S3 = "SEND_FINISHED_CONFIRM_DELIVERY"
    S4 = "TRANSACTION_CANCELLED"

    def update_state(self, event=None, pdu=None, request=None):
        if self.state == self.S1:
            pass
        elif self.state == self.S2:
            pass
        elif self.state == self.S3:
            pass
        elif self.state == self.S4:
            pass

        if event == Event.E2_ABANDON_TRANSACTION:
            pass