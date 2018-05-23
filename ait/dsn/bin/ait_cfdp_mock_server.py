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

# Mock incoming PDUs

import gevent
import gevent.server
import socket

def handle(sock, address):
    count = 0
    while True:
        sock.send('Hello {}'.format(count))
        count += 1
        gevent.sleep(2)

if __name__ == '__main__':
    server = gevent.server.StreamServer(('127.0.0.1', 8000), handle)
    server.serve_forever()
