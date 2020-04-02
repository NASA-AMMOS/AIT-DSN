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
#   python raf_api_test.py
#
# SSPSim Config:
# 1. Open "MISSION MANAGERS" >  "Test" > "RAF ONLC1"
# 2. Ensure that the Production Id is set to "TestBaseband1"
# 3. Ensure that GVCID is set to (250, 0, *)
# 4. Open "PRODUCTION" > "TestBaseband1"
# 5. Ensure that Spacecraft Id is set to 250
# 6. Activate the TM data flow by clicking the green arrow
#       labelled "TM"
# 7. Activate the TM simulation data creation by clicking the
#       green arrow labelled "SIM".
# 8. Activate the Mission Manager interface by clicking the
#       green arrow labelled "SVC"
#
# Run the script per the usage instructions above. You should see
# logging informing you of the various steps and data being sent
# to the telemetry output port. Note, because we're using dummy data
# we will see 0 bytes being output. This is working as expected.
# If you run into issues with decoding problems on the TM Frames this
# likely due to the TM frame size not being evenly divisible into
# CCSDS Packets. The TM Frame processor assumes the data field contains
# CCSDS Packets. Since all the dummy data is 0's, the processor
# repeatedly strips 6 bytes off the packet data to process as a CCSDS header.
# As such, (Telem Frame Length - 6 bytes for the TM Header) % 6 should be 0.
# If it's not you'll likely encounter problems.

import datetime as dt
import time

import ait.dsn.sle

raf_mngr = ait.dsn.sle.RAF(
    hostnames=['atb-ocio-sspsim.jpl.nasa.gov'],
    port=5100,
    inst_id='sagr=LSE-SSC.spack=Test.rsl-fg=1.raf=onlc1',
    spacecraft_id=250,
    trans_frame_ver_num=0,
    version=4,
    auth_level="none"
)

raf_mngr.connect()
time.sleep(2)

raf_mngr.bind()
time.sleep(2)

start = dt.datetime(2017, 1, 1)
end = dt.datetime(2021, 1, 1)
# raf_mngr.start(start, end)
raf_mngr.start(None, None)

try:
    while True:
        time.sleep(0)
except:
    pass
finally:

    raf_mngr.stop()
    time.sleep(2)

    raf_mngr.unbind()
    time.sleep(2)

    raf_mngr.disconnect()
    time.sleep(2)
