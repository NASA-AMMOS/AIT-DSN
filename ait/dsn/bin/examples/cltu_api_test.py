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

# SSPSim Config:
# 1. Open "MISSION MANAGERS" >  "Test" > "RAF ONLC1"
# 2. Ensure that the Production Id is set to "TestBaseband1"
# 4. Open "PRODUCTION" > "TestBaseband1"
# 5. Ensure that Spacecraft Id is set to 250
# 6. Activate the TC data flow by clicking the green arrow
#       labelled "TC"
# 7. Activate the TM simulation data creation by clicking the
#       green arrow labelled "SIM".
# 8. Activate the Mission Manager interface by clicking the
#       green arrow labelled "SVC"

import datetime as dt
import time

import ait.dsn.sle

# CLTU pulls parameters from config file by default
cltu_mngr = ait.dsn.sle.CLTU()

cltu_mngr.connect()
time.sleep(2)

cltu_mngr.bind()
time.sleep(2)

cltu_mngr.start()
time.sleep(2)

junk_data = bytearray('\x00'*79, 'utf-8')
cltu_mngr.upload_cltu(junk_data)
time.sleep(4)
cltu_mngr.upload_cltu(junk_data)
time.sleep(4)
cltu_mngr.upload_cltu(junk_data)
time.sleep(4)

cltu_mngr.stop()
time.sleep(2)

cltu_mngr.unbind()
time.sleep(2)

cltu_mngr.disconnect()
time.sleep(2)
