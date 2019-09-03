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
#   python rcf_api_test.py
#
# SSPSim Config:
# 1. Open "MISSION MANAGERS" >  "Test" > "RCFv2 ONLC2"
# 2. Ensure that the Production Id is set to "TestBaseband2"
# 3. Ensure that GVCID is set to (250, 0, *)
# 4. Open "PRODUCTION" > "TestBaseband1"
# 5. Ensure that Spacecraft Id is set to 250
# 6. Ensure that VCID is checked and set to 6
# 7. Ensure the Source field is set to DUMMY. **NOTE**, the
#       generated data will not contain the VCID you set unless
#       you use the DUMMY data source.
# 8. Activate the TM data flow by clicking the green arrow
#       labelled "TM"
# 9. Activate the TM simulation data creation by clicking the
#       green arrow labelled "SIM".
# 10. Activate the Mission Manager interface by clicking the
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
#
# You can confirm that virtual channels are working by using the commented
# out start call in the script instead. Try changing the virtual_channel
# parameter to a number that doesn't match the VCID you set in step 6 above.
# You should see the connection go through but no data will be received.

import datetime as dt
import time

import ait.dsn.sle

# runtime parameters will override config file defaults
rcf_mngr = ait.dsn.sle.RCF(
    hostname='atb-ocio-sspsim.jpl.nasa.gov',
    port=5100,
    inst_id='sagr=LSE-SSC.spack=Test.rsl-fg=1.rcf=onlc2',
    spacecraft_id=250,
    trans_frame_ver_num=0,
    version=4,
    auth_level="none"
)

rcf_mngr.connect()
time.sleep(2)

rcf_mngr.bind()
time.sleep(2)

start = dt.datetime(2017, 01, 01)
end = dt.datetime(2019, 01, 01)
# rcf_mngr.start(start, end, 250, 0, virtual_channel=6)
rcf_mngr.start(start, end, 250, 0, master_channel=True)

try:
    while True:
        time.sleep(0)
except:
    pass
finally:

    rcf_mngr.stop()
    time.sleep(2)

    rcf_mngr.unbind()
    time.sleep(2)

    rcf_mngr.disconnect()
    time.sleep(2)
