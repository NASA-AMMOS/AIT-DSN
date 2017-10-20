#!/usr/bin/env python

import datetime
import socket
import time

import gevent
import gevent.socket
import gevent.monkey; gevent.monkey.patch_all()

import pyasn1.error
from pyasn1.codec.der.decoder import decode
from pyasn1.codec.native.encoder import encode

from bliss.core import log

import bliss.sle
from bliss.sle.pdu.raf import *

def process_pdu():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    while True:
        gevent.sleep(0)
        if bliss.sle.DATA_QUEUE.empty():
            continue

        hdr, body = bliss.sle.DATA_QUEUE.get()

        try:
            decoded_pdu, remainder = bliss.sle.RAF.decode(body)
        except pyasn1.error.PyAsn1Error as e:
            log.error('Unable to decode PDU. Skipping ...')
            continue
        except TypeError as e:
            log.error('Unable to decode PDU due to type error ...')
            continue

        if ('data' in decoded_pdu['rafTransferBuffer'][0]['annotatedFrame'] and
            decoded_pdu['rafTransferBuffer'][0]['annotatedFrame']['data'].isValue):
            # Data is present and initialized. Processing telemetry ...
            trans_data = decoded_pdu['rafTransferBuffer'][0]['annotatedFrame']['data'].asOctets()
        else:
            # Object does not contain data or data is not initalized. Skipping ...
            continue

        tmf = bliss.sle.TMTransFrame(trans_data)
        log.info('Emitting {} bytes of telemetry to GUI'.format(len(tmf._data[0])))
        sock.sendto(tmf._data[0], ('localhost', 3076))


if __name__ == '__main__':
    raf_mngr = bliss.sle.RAF(hostname='atb-ocio-sspsim.jpl.nasa.gov', port=5100)
    raf_mngr.connect()
    time.sleep(1)

    raf_mngr.bind()
    time.sleep(1)

    raf_mngr.send_start_invocation(datetime.datetime(2017, 1, 1), datetime.datetime(2018, 1, 1))

    tlm_monitor = gevent.spawn(process_pdu)
    gevent.sleep(0)
    # log.info('Processing telemetry. Press <Ctrl-c> to terminate connection ...')
    try:
        while True:
            gevent.sleep(0)
    except:
        pass

    tlm_monitor.kill()

    raf_mngr.stop()
    time.sleep(1)

    raf_mngr.unbind()
    time.sleep(1)

