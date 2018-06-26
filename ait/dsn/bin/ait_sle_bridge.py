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

import datetime
import socket
import time

import gevent
import gevent.socket
import gevent.monkey; gevent.monkey.patch_all()

import pyasn1.error
from pyasn1.codec.der.decoder import decode
from pyasn1.codec.native.encoder import encode

from ait.core import log

import ait.dsn.sle
import ait.dsn.sle.frames
from ait.dsn.sle.pdu.raf import *

def process_pdu(raf_mngr):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    while True:
        gevent.sleep(0)
        if raf_mngr._data_queue.empty():
            continue

        log.info('Empty {}'.format(raf_mngr._data_queue.empty()))
        pdu = raf_mngr._data_queue.get()

        try:
            decoded_pdu, remainder = raf_mngr.decode(pdu)
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

        tmf = ait.dsn.sle.frames.TMTransFrame(trans_data)
        log.info('Emitting {} bytes of telemetry to GUI'.format(len(tmf._data[0])))
        sock.sendto(tmf._data[0], ('localhost', 3076))


if __name__ == '__main__':
    raf_mngr = ait.dsn.sle.RAF(hostname='atb-ocio-sspsim.jpl.nasa.gov', port=5100,
                             auth_level="bind",
                             inst_id="sagr=LSE-SSC.spack=Test.rsl-fg=1.raf=onlc1")
    raf_mngr.connect()
    time.sleep(1)

    raf_mngr.bind()
    time.sleep(1)

    raf_mngr.start(datetime.datetime(2017, 1, 1), datetime.datetime(2018, 1, 1))

    tlm_monitor = gevent.spawn(process_pdu, raf_mngr)
    gevent.sleep(0)
    log.info('Processing telemetry. Press <Ctrl-c> to terminate connection ...')
    try:
        while True:
            gevent.sleep(0)
    except:
        pass
    finally:

        tlm_monitor.kill()

        raf_mngr.stop()
        time.sleep(1)

        raf_mngr.unbind()
        time.sleep(1)

