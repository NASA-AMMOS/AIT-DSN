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
#   python cltu_api_test.py
#
# SSPSim Config:
# 1. Open "MISSION MANAGERS" >  "Test" > "FCLTU - PLOP1"
# 2. Open "PRODUCTION" > "TestBaseband2"
# 3. Activate the production interface by clicking the
#       green arrow labelled "TC"
# 4. Activate the Mission Manager interface by clicking the
#       green arrow labelled "SVC"
# 5. Set dsn.sle.version in config.yaml to the desire version to test (4 or 5). See note below for expected behavior.
#
# Run the script per the usage instructions above. You should see
# logging informing you of the various steps in the script. If all
# runs as expected you should see confirmations back from the sim
# indicating which cltu id was last processed. These will also be
# mirrored in the sim GUI where you'll be informed when a particular
# cltu id has been successfully radiated.
#
# NOTE: If the version is set to 4, this test should print a ValueConstraintError
# (after the finally block) when sending the throw event. This is because the V4 throw-event
# event qualifier has a max length is 128. If the class replacement from v5 to v4 doesn't work (or version is set of 5),
# this test will finish without errors.

import time

import ait.dsn.sle

cltu_mngr = ait.dsn.sle.CLTU(
    hostnames=['atb-ocio-sspsim.jpl.nasa.gov'],
    port=5100,
    inst_id='sagr=LSE-SSC.spack=Test.fsl-fg=1.cltu=cltu1',
    auth_level="none"
)

try:
    cltu_mngr.connect()
    time.sleep(2)

    cltu_mngr.bind()
    time.sleep(2)

    cltu_mngr.start()
    time.sleep(2)

    junk_data = bytearray('\x00'*129)
    cltu_mngr.throw_event(4, junk_data)
    time.sleep(4)
finally:
    cltu_mngr.stop()
    time.sleep(2)

    cltu_mngr.unbind()
    time.sleep(2)

    cltu_mngr.disconnect()
    time.sleep(2)
