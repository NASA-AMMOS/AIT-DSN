#!/usr/bin/env python

import bliss.cfdp
import gevent
import traceback

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
