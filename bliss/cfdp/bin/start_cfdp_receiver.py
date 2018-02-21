#!/usr/bin/env python

import bliss.cfdp
import gevent
import os
import traceback

import logging
from bliss.cfdp.primitives import TransmissionMode

# Default paths for now
FILE_ROOT = '/tmp/cfdp/'
# /tmp/cfdp/outgoing for outgoing files
OUTGOING_PATH = os.path.join(FILE_ROOT, 'outgoing')
# /tmp/cfdp/incoming for incoming files
INCOMING_PATH = os.path.join(FILE_ROOT, 'incoming')


if __name__ == '__main__':

    cfdp = bliss.cfdp.CFDP('2')
    try:
        while True:
            # logging.debug('Sleeping...')
            gevent.sleep(1)
    except KeyboardInterrupt:
        print "Disconnecting..."
    except Exception as e:
        print traceback.print_exc()
