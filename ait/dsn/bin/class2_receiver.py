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
import binascii
import json
import gevent
import traceback
import requests
import SimpleHTTPServer

import ait.core.log


"""
This is setting up a little bit of infrastructure to be able to test against the AMPCS CFDP implementation:

SET UP:

Values updated in ammos/ampcs/cfdp_processor/config.properties:

    cfdp.processor.inbound.pdu.from.linksim=true
    cfdp.processor.outbound.pdu.sink.type=uri
    cfdp.processor.outbound.pdu.uri=http\://localhost\:8099/linksim/send_pdu

Update ammos/ampcs/cfdp_processor/mib.properties:

    cfdp.processor.mib.remote.2.add.pdu.crc=false


In your CFDP directory CFDP/UPLINK, add any tests files that the cfdp processor can send. There are some lorem ipsum files of different sizes in ait/dsn/cfdp/test/testdata

config.yaml - updated these values to work with the AMPCS verisons

     datasink:
                 outgoing:
                    path: /CFDP/UPLINK
                 pdusink:
                    path: /CFDP/PDUSINK
             max_file_name_length: 64
            max_entity_id_length: 1
            max_transaction_id_length: 1


TO RUN:

In Terminal #1:
> chill_cfdp_linksim -url http://localhost:9001

    -url specifies where to send outbound PDUs. Below in __main__, the CFDP instance is configured to connect a TCPServer to (localhost, 9001).
     The CFDPRequestHandler below is the beginnings of dealing with incoming PDUs.

In Terminal #2:
> chill_cfdp_processor -l 1 -p 8080

In Terminal #3:
> python class2_receiver.py

Then do a put request:
> chill_cfdp put -sf small.txt -d 2 -cp 8080


NOTES:

- The CFDP entity can both send and receive MD, EOF, and FD pdus successfully. I suspect there is something off with the
    ACK PDUs because I had some ACK PDU files lying around that was messing things up and giving errors, but I haven't explored that yet.

TODOS:
- Debug ACK and FINISHED pdu encoding/decoding against AMPCS implementation
- Finish setting up the CFDPRequestHandler below to route PDUs to the appropriate machine.
    The PDUs just need to be added to `incoming_pdu_queue` of the CFDP instance, and then the `receiving_handler` plucks the PDUs from that queue and routes them
"""

URL = 'http://localhost:8099/linksim/send_pdu'

class CFDPRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):

    def do_POST(self):
        content_length = self.headers.get('Content-Length')
        if content_length:
            content_length = int(content_length)
            data = json.loads(self.rfile.read(content_length))

            self.send_response(200)
            self.end_headers()

            pdu_data = data.get('pduData', None)
            print bytearray(binascii.a2b_base64(pdu_data))
        else:
            self.send_response(400)


def sending_handler(instance):
    while True:
        gevent.sleep(1)
        try:
            pdu = instance.outgoing_pdu_queue.get(block=False)

            data = binascii.b2a_base64(bytearray(pdu.to_bytes())).rstrip()
            ait.core.log.info('Outgoing PDU: ' + str(data))

            body = {
                "metadata": {},
                "pduData": data,
                "destinationEntityId": 1
            }

            headers = {
                'Accept': 'text/plain, application/json, application/*+json, */*',
                'Content-Type': "application/json;charset=UTF-8"
            }

            r = requests.Request('POST', URL, json=body, headers=headers)
            req = r.prepare()
            # print('{}\n{}\n{}\n\n{}\n{}'.format(
            #     '-----------START-----------',
            #     req.method + ' ' + req.url,
            #     '\n'.join('{}: {}'.format(k, v) for k, v in req.headers.items()),
            #     req.body,
            #     '-----------END-----------',
            # ))
            s = requests.Session()
            res = s.send(req)

            if res.status_code == 200:
                print 'Successfully transmitted PDU'
            else:
                raise Exception('Couldn\'t send PDU. Response code {}'.format(res.status_code))
        except gevent.queue.Empty:
            pass
        except Exception as e:
            ait.core.log.warn('Sending handler exception: ' + e.message)
            ait.core.log.warn(traceback.format_exc())
        gevent.sleep(0.2)


if __name__ == '__main__':
    cfdp = ait.dsn.cfdp.CFDP(2, sending_handler=sending_handler, read_pdus=read_pdus_from_socket, server_handler=CFDPRequestHandler)
    try:
        cfdp.connect(('127.0.0.1', 9001))
        # # Set address of counterpart
        # cfdp.mib.set_remote('2', 'ut_address', ('127.0.0.1', 9002))

        ## Uncomment this stuff down here to make it a sender
        # destination_id = 1
        # source_file = 'small.txt'
        # destination_file = 'mysmall.txt'
        # cfdp.put(destination_id, source_file, destination_file, transmission_mode=TransmissionMode.ACK)
        while True:
            # ait.core.log.info('Sleeping...')
            gevent.sleep(1)
    except KeyboardInterrupt:
        print "Disconnecting..."
    except Exception as e:
        print traceback.print_exc()
    finally:
        cfdp.disconnect()
