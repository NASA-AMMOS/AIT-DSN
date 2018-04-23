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

''' SLE Generic Items

The bliss.sle.common module provides generic SLE classes, methods and
attributes that are used to implement other SLE interfaces.

Attributes:
    TML_SLE_FORMAT: The struct format string for pack-ing a SLE PDU
        packet header.

    TML_SLE_TYPE: The first 4 bytes of an SLE PDU packet header for
        use when struct.pack-ing.

    TML_CONTEXT_MSG_FORMAT: The struct format string for pack-ing a
        SLE Context Message PDU.

    TML_CONTEXT_MSG_TYPE: The first 4 bytes of an SLE Context Message
        PDU header for use when struct.pack-ing.

    TML_CONTEXT_HB_FORMAT: The struct format string for pack-ing a
        SLE Heartbeat message PDU.

    TML_CONTEXT_HEARTBEAT_TYPE: The first 4 bytes of an SLE Heartbeat
        message PDU header for use when struct.pack-ing.

    CCSDS_EPOCH: A datetime object pointing to the CCSDS Epoch.

Classes:
    SLE: An SLE interface "base" class that provides interface-agnostic
        methods and attributes for interfacing with SLE.
'''

import binascii
from collections import defaultdict
import datetime as dt
import errno
import fcntl
import hashlib
import random
import socket
import struct
import time

import gevent
import gevent.queue
import gevent.socket
import gevent.monkey; gevent.monkey.patch_all()

import pyasn1.error
from pyasn1.codec.ber.encoder import encode
from pyasn1.codec.der.encoder import encode as der_encode
from pyasn1.codec.der.decoder import decode

import bliss.core
import bliss.core.log

from bliss.sle.pdu import service_instance
from bliss.sle.pdu.service_instance import *
from bliss.sle.pdu.common import HashInput, ISP1Credentials
import util

TML_SLE_FORMAT = '!ii'
TML_SLE_TYPE = 0x01000000

TML_CONTEXT_MSG_FORMAT = '!IIbbbbIHH'
TML_CONTEXT_MSG_TYPE = 0x02000000

TML_CONTEXT_HB_FORMAT = '!ii'
TML_CONTEXT_HEARTBEAT_TYPE = 0x03000000

CCSDS_EPOCH = dt.datetime(1958, 1, 1)

class SLE(object):
    ''' SLE interface "base" class

    The SLE class provides SLE interface-agnostic methods and attributes
    for interfacing with SLE.

    '''
    _state = 'unbound'
    _handlers = defaultdict(list)
    _data_queue = gevent.queue.Queue()
    _invoke_id = 0

    def __init__(self, *args, **kwargs):
        ''''''
        self._hostname = bliss.config.get('dsn.sle.hostname',
                                          kwargs.get('hostname', None))
        self._port = bliss.config.get('dsn.sle.port',
                                      kwargs.get('port', None))
        self._heartbeat = bliss.config.get('dsn.sle.heartbeat',
                                           kwargs.get('heartbeat', 25))
        self._deadfactor = bliss.config.get('dsn.sle.deadfactor',
                                            kwargs.get('deadfactor', 5))
        self._buffer_size = bliss.config.get('dsn.sle.buffer_size',
                                             kwargs.get('buffer_size', 256000))
        self._credentials = bliss.config.get('dsn.sle.credentials', None)
        self._initiator_id = bliss.config.get('dsn.sle.initiator_id',
                                              kwargs.get('initiator_id', 'LSE'))
        self._responder_port= bliss.config.get('dsn.sle.responder_port',
                                               kwargs.get('responder_port', 'default'))
        self._telem_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._inst_id = kwargs.get('inst_id', None)

        if not self._hostname or not self._port:
            msg = 'Connection configuration missing hostname ({}) or port ({})'
            msg = msg.format(self._hostname, self._port)
            bliss.core.log.error(msg)
            raise ValueError(msg)

        self._conn_monitor = gevent.spawn(conn_handler, self)
        self._data_processor = gevent.spawn(data_processor, self)

    @property
    def invoke_id(self):
        ''''''
        iid = self._invoke_id
        self._invoke_id += 1
        return iid

    def add_handler(self, event, handler):
        ''' Add a "handler" function for an "event"

        Arguments:
            event:
                A string of the PDU name for which the handler function
                should e called.

            handler:
                The function that should be called for the specified event.
                The function will be passed the decoded PyASN1 PDU as its
                only argument.
        '''
        self._handlers[event].append(handler)

    def send(self, data):
        ''' Send supplied data to DSN '''
        try:
            self._socket.send(data)
        except socket.error as e:
            if e.errno == errno.ECONNRESET:
                bliss.core.log.error('Socket connection lost to DSN')
                s.close()
            else:
                bliss.core.log.error('Unexpected error encountered when sending data. Aborting ...')
                raise e

    def decode(self, message, asn1Spec):
        ''' Decode a chunk of ASN.1 data

        Arguments:
            message:
                A bytestring of data that contains an encoded ASN.1 PDU to
                be decoded.

            asn1Spec:
                An instance of a PyASN1 class that the data should be
                decoded against.

        Returns:
            The decoded PyASN1 object containing the message data.

        Raises:
            pyasn1.error.PyAsn1Error
            TypeError
        '''
        return decode(message, asn1Spec=asn1Spec)

    def encode_pdu(self, pdu):
        ''' Encode a SLE PDU

        Arguments:
            pdu: The PyASN1 class instance to encode

        Returns:
            The ASN.1 encoded PDU struct.pack-ed into the SLE PDU packet
            structure.
        '''
        en = encode(pdu)
        return struct.pack(
                TML_SLE_FORMAT,
                TML_SLE_TYPE,
                len(en),
        ) + en

    def bind(self, pdu, **kwargs):
        ''' Bind to an SLE Interface

        Arguments:
            pdu:
                The PyASN1 class instance that should be configured with
                generic SLE attributes, encoded, and sent to SLE.
        '''
        if self._credentials:
            pdu['invokerCredentials']['used'] = self._generate_encoded_credentials()
        else:
            pdu['invokerCredentials']['unused'] = None

        pdu['initiatorIdentifier'] = self._initiator_id
        pdu['responderPortIdentifier'] = self._responder_port
        pdu['serviceType'] = self._service_type
        pdu['versionNumber'] = self._version

        inst_id = kwargs['inst_id'] if kwargs.get('inst_id') else self._inst_id
        if not inst_id:
            raise AttributeError('No instance id provided. Unable to bind.')

        inst_ids = [
            st.split('=')
            for st in inst_id.split('.')
        ]

        sii = ServiceInstanceIdentifier()
        for i, iden in enumerate(inst_ids):
            identifier = getattr(service_instance, iden[0].replace('-', '_'))
            siae = ServiceInstanceAttributeElement()
            siae['identifier'] = identifier
            siae['siAttributeValue'] = iden[1]
            sia = ServiceInstanceAttribute()
            sia[0] = siae
            sii[i] = sia
        pdu['serviceInstanceIdentifier'] = sii

        bliss.core.log.info('Sending Bind request ...')
        self.send(self.encode_pdu(pdu))

    def unbind(self, pdu, reason=0):
        ''' Unbind from the SLE Interface

        Arguments:
            pdu:
                The PyASN1 class instance that should be configured with
                generic SLE attributes, encoded, and sent to SLE.
            reason:
                The reason code for why the unbind is happening.
        '''
        if self._credentials:
            pdu['invokerCredentials']['used'] = self._generate_encoded_credentials()
        else:
            pdu['invokerCredentials']['unused'] = None

        pdu['unbindReason'] = reason
              
        bliss.core.log.info('Sending Unbind request ...')
        self.send(self.encode_pdu(pdu))

    def connect(self):
        ''' Setup connection with DSN 
        
        Initialize TCP connection with DSN and send context message
        to configure communication.
        '''
        self._socket = gevent.socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            self._socket.connect((self._hostname, self._port))
            bliss.core.log.info('Connection to DSN Successful')
        except socket.error as e:
            bliss.core.log.error('Connection failure with DSN. Aborting ...')
            raise e

        context_msg = struct.pack(
            TML_CONTEXT_MSG_FORMAT,
            TML_CONTEXT_MSG_TYPE,
            0x0000000C,
            ord('I'), ord('S'), ord('P'), ord('1'),
            0x00000001,
            self._heartbeat,
            self._deadfactor
        )

        bliss.core.log.info('Configuring SLE connection')

        try:
            self.send(context_msg)
            bliss.core.log.info('Connection configuration successful')
        except socket.error as e:
            bliss.core.log.error('Connection configuration failed. Aborting ...')
            raise e

    def disconnect(self):
        ''' Disconnect from SLE

        Disconnect the SLE and telemetry output sockets and kill the
        greenlets for monitoring and processing data.
        '''
        self._socket.close()
        self._telem_sock.close()
        self._conn_monitor.kill()
        self._data_processor.kill()

    def stop(self, pdu):
        ''' Send a SLE Stop PDU.

        Arguments:
            pdu:
                The PyASN1 class instance that should be configured with
                generic SLE attributes, encoded, and sent to SLE.
        '''
        if self._credentials:
            pdu['invokerCredentials']['used'] = self._generate_encoded_credentials()
        else:
            pdu['invokerCredentials']['unused'] = None

        pdu['invokeId'] = self.invoke_id

        bliss.core.log.info('Sending data stop invocation ...')
        self.send(self.encode_pdu(pdu))
    

    def _need_heartbeat(self, time_delta):
        ''''''
        return time_delta >= self._heartbeat

    def _send_heartbeat(self):
        ''''''
        hb = struct.pack(
                TML_CONTEXT_HB_FORMAT,
                TML_CONTEXT_HEARTBEAT_TYPE,
                0
        )
        self.send(hb)

    def _handle_pdu(self, pdu):
        ''''''
        pdu_key = pdu.getName()
        pdu_key = pdu_key[:1].upper() + pdu_key[1:]
        if pdu_key in self._handlers:
            pdu_handlers = self._handlers[pdu_key]
            for h in pdu_handlers:
                h(pdu)
        else:
            err = (
                'PDU of type {} has no associated handlers. '
                'Unable to process further and skipping ...'
            )
            bliss.core.log.error(err.format(pdu_key))

    def _generate_encoded_credentials(self):
        ''''''
        hash_input = HashInput()
        now = dt.datetime.utcnow()
        days = (now - dt.datetime(1958, 1, 1)).days
        millisecs = (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds() * 1000
        credential_time = struct.pack('!HIH', days, millisecs, 0)

        ## This random number for DSN spec
        # random_number = random.randint(0, 42949667295)

        # This random number of SSPSIM
        random_number = random.randint(0, 2147483647)

        hash_input['time'] = credential_time
        hash_input['randomNumber'] = random_number
        hash_input['username'] = self._credentials['username']
        hash_input['password'] = self._credentials['password']
        der_encoded_hash_input = der_encode(hash_input)
        the_protected = bytearray.fromhex(hashlib.sha1(der_encoded_hash_input).hexdigest())

        isp1_creds = ISP1Credentials()
        isp1_creds['time'] = credential_time
        isp1_creds['randomNumber'] = random_number
        isp1_creds['theProtected'] = the_protected

        return encode(isp1_creds)
        # return hashlib.sha1(self._credentials['username'] + '736C6574657365720A')


def conn_handler(handler):
    ''' Handler for processing data received from the DSN into PDUs'''
    hb_time = int(time.time())
    msg = ''

    while True:
        gevent.sleep(0)

        now = int(time.time())
        if handler._need_heartbeat(now - hb_time):
            hb_time = now
            handler._send_heartbeat()

        try:
            msg = msg + handler._socket.recv(handler._buffer_size)
        except:
            gevent.sleep(1)

        while len(msg) >= 8:
            hdr, rem = msg[:8], msg[8:]

            # PDU Received
            if binascii.hexlify(hdr[:4]) == '01000000':
                # Get length of body and check if the entirety of the
                # body has been received. If we can, process the message(s)
                body_len = util.hexint(hdr[4:])
                if len(rem) < body_len:
                    break
                else:
                    body = rem[:body_len]
                    handler._data_queue.put(hdr + body)
                    msg = msg[len(hdr) + len(body):]
            # Heartbeat Received
            elif binascii.hexlify(hdr[:8]) == '0300000000000000':
                msg = rem
            else:
                err = (
                    'Received PDU with unexpected header. '
                    'Unable to parse data further.\n'
                )
                bliss.core.log.error(err)
                bliss.core.log.error('\n'.join([msg[i:i+16] for i in range(0, len(msg), 16)]))
                raise ValueError(err)


def data_processor(handler):
    ''' Handler for decoding ASN.1 encoded PDUs '''
    while True:
        gevent.sleep(0)
        if handler._data_queue.empty():
            continue

        msg = handler._data_queue.get()
        hdr, body = msg[:8], msg[8:]

        try:
            decoded_pdu, remainder = handler.decode(body)
        except pyasn1.error.PyAsn1Error as e:
            bliss.core.log.error('Unable to decode PDU. Skipping ...')
            continue
        except TypeError as e:
            bliss.core.log.error('Unable to decode PDU due to type error ...')
            continue

        handler._handle_pdu(decoded_pdu)
