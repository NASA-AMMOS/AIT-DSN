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

import os

PROJECT_PATH = '/Users/lsposto/PycharmProjects/bliss-cfdp'

MIB_PATH = os.path.join(PROJECT_PATH, "tmp/mib/")

BASE_PATH = os.path.join(PROJECT_PATH, "tmp/cfdp/")
OUTGOING_PATH = os.path.join(BASE_PATH, "outgoing")
INCOMING_PATH = os.path.join(BASE_PATH, "incoming")
TEMP_PATH = os.path.join(BASE_PATH, "tmp")
PDU_PATH = os.path.join(BASE_PATH, "pdu")