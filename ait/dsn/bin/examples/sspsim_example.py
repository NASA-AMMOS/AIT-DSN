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
#   python sspsim_example.py
#
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
#
# You will also want to tail the sim logs to get more info about what is
#   going on with the system. Run the following commands at a prompt.
#
# > ssh atb-ocio-sspsim
# > sudo su app-srv
# > tail -f /home/app-srv/sspsim2/log/log.txt | grep "ISP1TransportMappingLayerImp"
#
# Run the script per usage instructions above and watch the tailed logs.
# Important things that you would want to look for are that the
# Context message is received and that the heartbeat and dead factor
# are inline with what you set. The script will also tell you when you should
# see the connection disconnect due to a lack of activity on the line.
import struct
import socket
import time

TML_CONTEXT_MSG_FORMAT = '!IIbbbbIHH'
TML_CONTEXT_MSG_TYPE = 0x02000000
TML_CONTEXT_MSG = struct.pack(
    TML_CONTEXT_MSG_FORMAT,
    TML_CONTEXT_MSG_TYPE,
    0x0000000C,
    ord('I'), ord('S'), ord('P'), ord('1'),
    0x00000001,
    5,
    5
)

TML_CONTEXT_HB_FORMAT = '!ii'
TML_CONTEXT_HEARTBEAT_TYPE = 0x03000000
TML_CONTEXT_HB_MSG = struct.pack(
        TML_CONTEXT_HB_FORMAT,
        TML_CONTEXT_HEARTBEAT_TYPE,
        0
)

proxy = ('atb-ocio-sspsim.jpl.nasa.gov', 5100)
buffer_size = 256000

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(proxy)
time.sleep(5)
print('Sending Context Msg')
s.send(TML_CONTEXT_MSG)

print('Beginning Heart Beat Iterations')
for i in range(50):
    print('-----------------')
    print('Iteration: ', i)
    # print 'reading'
    # print s.recv(buffer_size)
    # print 'sleeping 1 second'
    time.sleep(1)
    print('Sending Heartbeat')
    s.send(TML_CONTEXT_HB_MSG)


print('Sleeping 25 seconds ... (5 second Heartbeat time * 5 Dead Factor == 25 seconds )')
time.sleep(25)
print('SSPSim should have disconnected you in the logs ...')
print('Sleeping 60 seconds')
time.sleep(60)
print('Closing socket')
s.close()
