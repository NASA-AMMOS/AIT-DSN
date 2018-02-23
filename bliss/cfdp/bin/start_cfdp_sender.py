#!/usr/bin/env python

import bliss.cfdp
import gevent
import traceback

import logging
from bliss.cfdp.primitives import TransmissionMode
from bliss.cfdp import settings

if __name__ == '__main__':

    cfdp = bliss.cfdp.CFDP('1')
    try:
        destination_id = '2'
        source_file = 'test.txt'
        destination_file = 'my/test/blah.txt'
        cfdp.put(destination_id, source_file, destination_file, transmission_mode=TransmissionMode.NO_ACK)
        while True:
            # logging.debug('Sleeping...')
            gevent.sleep(1)
    except KeyboardInterrupt:
        print "Disconnecting..."
    except Exception as e:
        print traceback.print_exc()
