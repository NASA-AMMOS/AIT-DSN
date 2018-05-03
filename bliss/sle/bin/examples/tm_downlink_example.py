#!/usr/bin/env python

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

# Usage:
#   python tm_downlink_example.py
#
# You will need to setup SSPSim to use this example properly
#
# 1. Login to the SSPSim at http://atb-ocio-sspsim.jpl.nasa.gov:7070/ssp
# 2. Change the "Perspective" to "Configuration" in the navbar
# 3. In the tree structure on the left, expand "MISSION MANAGERS", then
#       expand "Test", and then double click "TEST:RAF ONLC1 - ...". A
#       tab should appear on the right pane containing config info.
# 4. Activate the service by clicking the green arrow in the top right
#       of the configuration tab.
# 5. In the tree structure on the left, expand "PRODUCTION", then double
#       click "TestBaseband1". A tab should appear on the right pane
#       containing config info.
# 6. Activate the TM Simulation data by clicking the green arrow in the top
#       right of the tab. It should say "SIM" underneath it.
#
# Run the script per the usage instructions above. You should see notifications
# as different parts of the connection happen and then you should see large
# dumps of fake data received from the service.

import struct
import socket
import fcntl
import os
import errno
import time

from pyasn1.type import univ, char, namedtype, namedval, tag, constraint, useful
from pyasn1.codec.ber.encoder import encode
from pyasn1.codec.der.encoder import encode as derencode
from pyasn1.codec.der.decoder import decode

from hexdump import hexdump

from bliss.sle.pdu.raf import *
from bliss.sle.pdu import raf

TML_CONTEXT_MSG_FORMAT = '!IIbbbbIHH'
TML_CONTEXT_MSG_TYPE = 0x02000000
TML_CONTEXT_MSG = struct.pack(
    TML_CONTEXT_MSG_FORMAT,
    TML_CONTEXT_MSG_TYPE,
    0x0000000C,
    ord('I'), ord('S'), ord('P'), ord('1'),
    0x00000001,
    25,
    25
)

TML_CONTEXT_HB_FORMAT = '!ii'
TML_CONTEXT_HEARTBEAT_TYPE = 0x03000000
TML_CONTEXT_HB_MSG = struct.pack(
        TML_CONTEXT_HB_FORMAT,
        TML_CONTEXT_HEARTBEAT_TYPE,
        0
)

TML_SLE_FORMAT = '!ii'
TML_SLE_TYPE = 0x01000000

proxy = ('atb-ocio-sspsim.jpl.nasa.gov', 5100)
buffer_size = 256000

# Setup a non-blocking socket to the sim proxy
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(proxy)
fcntl.fcntl(s, fcntl.F_SETFL, os.O_NONBLOCK)

print "Sending TML Context Message ..."
s.send(TML_CONTEXT_MSG)

###############################################################################
# Create the Bind Invocation PDU for creating a connection to the service
###############################################################################
bind_invoc = RafUsertoProviderPdu()
bind_invoc['rafBindInvocation']['invokerCredentials']['unused'] = None
bind_invoc['rafBindInvocation']['initiatorIdentifier'] = 'LSE'
bind_invoc['rafBindInvocation']['responderPortIdentifier'] = 'default'
bind_invoc['rafBindInvocation']['serviceType'] = 'rtnAllFrames'
bind_invoc['rafBindInvocation']['versionNumber'] = 4

inst_ids = 'sagr=LSE-SSC.spack=Test.rsl-fg=1.raf=onlc1'.split('.')
inst_ids = [
    st.split('=')
    for st in inst_ids
]

sii = ServiceInstanceIdentifier()
for i, iden in enumerate(inst_ids):
    identifier = getattr(raf, iden[0].replace('-', '_'))
    siae = ServiceInstanceAttributeElement()
    siae['identifier'] = identifier
    siae['siAttributeValue'] = iden[1]
    sia = ServiceInstanceAttribute()
    sia[0] = siae
    sii[i] = sia
bind_invoc['rafBindInvocation']['serviceInstanceIdentifier'] = sii


en = encode(bind_invoc)
TML_SLE_MSG = struct.pack(
        TML_SLE_FORMAT,
        TML_SLE_TYPE,
        len(en),
) + en

print "Sending Bind Invocation PDU ..."
s.send(TML_SLE_MSG)


###############################################################################
# Create the Start Invocation PDU for requesting data from the service
###############################################################################
start_invoc = RafUsertoProviderPdu()
start_invoc['rafStartInvocation']['invokerCredentials']['unused'] = None
start_invoc['rafStartInvocation']['invokeId'] = 1234

# Time() can have 'ccsdsFormat' or 'ccsdsPicoFormat' options. We're picking an
# arbitrary section of time in the sim's valid data range specified in CCSDS CDS
# format w/o P-Field.
start_time = struct.pack(
    '!HIH',
    21700,
    0,
    0
)

stop_time = struct.pack(
    '!HIH',
    22500,
    0,
    0
)

start_invoc['rafStartInvocation']['startTime']['known']['ccsdsFormat'] = start_time
start_invoc['rafStartInvocation']['stopTime']['known']['ccsdsFormat'] = stop_time
start_invoc['rafStartInvocation']['requestedFrameQuality'] = 2

en = encode(start_invoc)
TML_SLE_MSG = struct.pack(
        TML_SLE_FORMAT,
        TML_SLE_TYPE,
        len(en),
) + en
s.send(TML_SLE_MSG)

while True:
    try:
        msg = s.recv(buffer_size)
    except socket.error, e:
        err = e.args[0]
        if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
            # time.sleep(1)
            print 'No data available'
            continue
        else:
            # a "real" error occurred
            print e
            sys.exit(1)
    else:
        print '--------------'
        print hexdump(msg)
