#!/usr/bin/env python

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

import ait.dsn.cfdp
import os
import gevent
import traceback

from ait.dsn.cfdp.primitives import TransmissionMode
import ait.core.log


if __name__ == '__main__':
    cfdp = ait.dsn.cfdp.CFDP(1)
    try:
        # cfdp.connect(('127.0.0.1', 9001))
        # # Set address of counterpart
        # cfdp.mib.set_remote('2', 'ut_address', ('127.0.0.1', 9002))

        destination_id = 2
        source_file = 'medium.txt'
        destination_file = 'my/test/blah.txt'
        cfdp.put(destination_id, source_file, destination_file, transmission_mode=TransmissionMode.NO_ACK)
        while True:
            # ait.core.log.info('Sleeping...')
            gevent.sleep(1)
    except KeyboardInterrupt:
        print "Disconnecting..."
    except Exception as e:
        print traceback.print_exc()
    finally:
        cfdp.disconnect()
