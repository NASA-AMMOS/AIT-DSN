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

The ait.dsn.sle.common module provides generic SLE classes, methods and
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
import gevent.select
import gevent.monkey; gevent.monkey.patch_all()

import pyasn1.error
from pyasn1.codec.ber.encoder import encode
from pyasn1.codec.der.encoder import encode as der_encode
from pyasn1.codec.der.decoder import decode

import ait.core
import ait.core.log

from ait.dsn.sle.pdu import service_instance
from ait.dsn.sle.pdu.service_instance import *
from ait.dsn.sle.pdu.common import HashInput, ISP1Credentials
import ait.dsn.sle.utils as utils

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
 
    def __init__(self, *args, **kwargs):
        ''''''
        self._state = 'unbound'
        self._handlers = defaultdict(list)
        self._data_queue = gevent.queue.Queue()
        self._invoke_id = 0

        self._downlink_frame_type = ait.config.get('dsn.sle.downlink_frame_type',
                                                   kwargs.get('downlink_frame_type', 'TMTransFrame'))
        self._heartbeat = ait.config.get('dsn.sle.heartbeat',
                                         kwargs.get('heartbeat', 25))
        self._deadfactor = ait.config.get('dsn.sle.deadfactor',
                                          kwargs.get('deadfactor', 5))
        self._buffer_size = ait.config.get('dsn.sle.buffer_size',
                                           kwargs.get('buffer_size', 256000))
        self._initiator_id = ait.config.get('dsn.sle.initiator_id',
                                            kwargs.get('initiator_id', 'LSE'))
        self._responder_id = ait.config.get('dsn.sle.responder_id',
                                            kwargs.get('responder_id', 'SSE'))
        self._initiator_pw = ait.config.get('dsn.sle.initiator_pw',
                                            kwargs.get('initiator_pw', None))
        self._responder_pw = ait.config.get('dsn.sle.responder_pw',
                                            kwargs.get('responder_pw', None))
        self._responder_port = ait.config.get('dsn.sle.responder_port',
                                              kwargs.get('responder_port', 'default'))
        self._auth_level = ait.config.get('dsn.sle.auth_level',
                                          kwargs.get('auth_level', 'none'))

        self._conn_monitor = None
        self._data_processor = None
        self._socket = None
        self._telem_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        if not self._hostnames or not self._port:
            msg = 'Connection configuration missing hostnames ({}) or port ({})'
            msg = msg.format(self._hostnames, self._port)
            ait.core.log.error(msg)
            raise ValueError(msg)

        if self._auth_level not in ['none', 'bind', 'all']:
            raise ValueError('Authentication level must be one of: "none", "bind", "all"')

        self._local_entity_auth = {
            'local_entity_id': self._initiator_id,
            'auth_level': self._auth_level,
            'time': None,
            'random_number': None
        }

    @property
    def invoke_id(self):
        ''''''
        iid = self._invoke_id
        self._invoke_id += 1
        return iid

    def shutdown(self, unbind=True):
        # Unbind == False is a special case for CLTU which enters a bad state whenever an unbind is sent
        # RAF should always unbind when in ready state, otherwise it will enter a bad state
        if self._state == 'active':
            ait.core.log.info(f"Sending stop. Current State: {self._state}")
            self.stop()
            time.sleep(2)

        if self._state == 'ready' and unbind:
            ait.core.log.info(f"Sending unbind. Current State: {self._state}")
            self.unbind()
            time.sleep(2)

        ait.core.log.info(f"Sending disconnect. Current State: {self._state}")
        self.disconnect()

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
        if not self._socket:
            ait.core.log.warn("Socket to DSN has not been established.")
            return
        try:
            _, writeable, _ = gevent.select.select([], [self._socket], [])
            for i in writeable:
                i.sendall(data)
        except socket.error as e:
            # FYI, the way this is architected, we can't actually recover.
            # A plugin supervisor needs to reinitialize us.
            if e.errno == errno.ECONNRESET:
                # DSN slammed the phone
                ait.core.log.error('The DSN closed the connection while data was in transit.')
                self._socket.close()
            elif e.errno == errno.EPIPE:
                # DSN cut the line
                ait.core.log.error('The DSN closed the connection unexpectedly.')
                self._socket.close()
            else:
                # ???
                ait.core.log.error('Unexpected socket error encountered when sending data. Aborting ...')
            ait.core.log.warn("Restart of SLE interface is required. Data loss may have occured.")
            # Signal to plugin supervisors that we're in an undesired state
            self._state = 'ERROR: DSN HANGUP' 
            # Raise causes plugin supervisor to immediate restart
            # raise e

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
        if self._auth_level in ['bind', 'all']:
            pdu['invokerCredentials']['used'] = self.make_credentials()
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

        ait.core.log.info('Sending Bind request ...')
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
        if self._state != 'ready':
            ait.core.log.warn(f"Can not comply: Can only UNBIND in state 'ready', current state is '{self._state}'.")
            return
        if self._auth_level == 'all':
            pdu['invokerCredentials']['used'] = self.make_credentials()
        else:
            pdu['invokerCredentials']['unused'] = None

        pdu['unbindReason'] = reason

        ait.core.log.info('Sending Unbind request ...')
        self.send(self.encode_pdu(pdu))

    def connect(self):
        ''' Setup connection with DSN

        Initialize TCP connection with DSN and send context message
        to configure communication.
        '''
        if self._state != 'unbound':
            # TODO According to ICD, the result of this function puts us in 'unbound' state. Why doesn't it explicitly do so?
            ait.core.log.warn("Unexpected connect detected.")
            ait.core.log.warn(f"Expected state to be 'unbound' instead of {self._state}. We do not know if DSN received. STOP or UNBIND.")
            ait.core.log.warn("Connecting and transitioning into unbound state anyway.")
        for hostname in self._hostnames:
            try:
                # create new socket for each host attempted
                self._socket = gevent.socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._socket.settimeout(10)
                self._socket.connect((hostname, self._port))
                ait.core.log.info(f"Connection to DSN successful through {hostname}.")
                break
            except socket.error as e:
                # Log the connection error to debug
                ait.core.log.debug(f"Error occurred while connecting to {hostname}:{self._port}: {e}")

                # If socket is set, close it and cleanup before continuing
                if self._socket:
                    try:
                        self._socket.close()
                    except socket.error as cls_err:
                        ait.core.log.error(F"Error occurred while closing socket to hostname {hostname}: {cls_err}")
                    self._socket = None

                # Log general connection failure to info
                ait.core.log.info(f"Failed to connect to DSN at {hostname}. Trying next hostname.")

        if self._socket is None:
            ait.core.log.error('Connection failure with DSN. Aborting ...')
            # Signal to plugin supervisors that we're in a bad state.
            # We can't recover, plugin supervisor needs to reinitialize us
            self._state = 'ERROR: DSN SOCKET NO RESPONSE'
            # Raise causes plugin supervisior to immediate restart
            raise Exception('Unable to connect to DSN through any provided hostnames.')

        self._conn_monitor = gevent.spawn(conn_handler, self)
        self._data_processor = gevent.spawn(data_processor, self)

        context_msg = struct.pack(
            TML_CONTEXT_MSG_FORMAT,
            TML_CONTEXT_MSG_TYPE,
            0x0000000C,
            ord('I'), ord('S'), ord('P'), ord('1'),
            0x00000001,
            self._heartbeat,
            self._deadfactor
        )

        ait.core.log.info('Configuring SLE connection...')

        try:
            self.send(context_msg)
            ait.core.log.info('SLE connection configuration successful')
        except socket.error as e:
            ait.core.log.error('SLE connection configuration failed. Aborting ...')
            raise e

    def disconnect(self):
        ''' Disconnect from SLE

        Disconnect the SLE and telemetry output sockets and kill the
        greenlets for monitoring and processing data.
        '''
        if self._socket:
            self._socket.close()
        if self._telem_sock:
            self._telem_sock.close()
        if self._conn_monitor:
            self._conn_monitor.kill()
        if self._data_processor:
            self._data_processor.kill()

    def stop(self, pdu):
        ''' Send a SLE Stop PDU.

        Arguments:
            pdu:
                The PyASN1 class instance that should be configured with
                generic SLE attributes, encoded, and sent to SLE.
        '''
        if self._state != 'active':
            ait.core.log.warn(f"Can not comply: Can only STOP in state 'active', current state is '{self._state}'.")
            return
        
        if self._auth_level == 'all':
            pdu['invokerCredentials']['used'] = self.make_credentials()
        else:
            pdu['invokerCredentials']['unused'] = None

        pdu['invokeId'] = self.invoke_id

        ait.core.log.info('Sending data stop invocation ...')
        self.send(self.encode_pdu(pdu))

    def _need_heartbeat(self, time_delta):
        ''''''
        return time_delta >= self._heartbeat

    def _send_heartbeat(self):
        ''''''
        if not self._socket:
            return
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
            ait.core.log.error(err.format(pdu_key))

    def make_credentials(self):
        '''Makes credentials for the initiator'''
        now = dt.datetime.utcnow()
        ## This random number for DSN spec
        # random_number = random.randint(0, 42949667295)

        # This random number for generic
        # Taken from https://public.ccsds.org/Pubs/913x1b2.pdf 3.2.3
        random_number = random.randint(0, 2147483647)
        self._local_entity_auth['time'] = now
        self._local_entity_auth['random_number'] = random_number
        return self._generate_encoded_credentials(now, random_number, self._initiator_id, self._initiator_pw)

    def _check_return_credentials(self, responder_performer_credentials, username, password):
        decoded_credentials = decode(responder_performer_credentials.asOctets(), ISP1Credentials())[0]
        days, ms, us = struct.unpack('!HIH', bytearray(decoded_credentials['time'].asNumbers()))
        time_delta = dt.timedelta(days=days, milliseconds=ms, microseconds=us)
        cred_time = time_delta + dt.datetime(1958, 1, 1)
        random_number = decoded_credentials['randomNumber']
        performer_credentials = self._generate_encoded_credentials(cred_time,
                                                                   random_number,
                                                                   self._responder_id,
                                                                   self._responder_pw)
        return performer_credentials == responder_performer_credentials

    def _generate_encoded_credentials(self, current_time, random_number, username, password):
        '''Generates encoded ISP1 credentials

        Arguments:
            current_time:
                The datetime object representing the time to use to create the credentials.
            random_number:
                The random number to use to create the credentials.
            username:
                The username to use to create the credentials.
            password:
                The password to use to create the credentials.
        '''
        hash_input = HashInput()
        credential_time = generate_encoded_time(current_time)

        hash_input['time'] = credential_time
        hash_input['randomNumber'] = random_number
        hash_input['username'] = username
        hash_input['password'] = password
        der_encoded_hash_input = der_encode(hash_input)
        the_protected = bytearray.fromhex(hashlib.sha1(der_encoded_hash_input).hexdigest())

        isp1_creds = ISP1Credentials()
        isp1_creds['time'] = credential_time
        isp1_creds['randomNumber'] = random_number
        isp1_creds['theProtected'] = the_protected

        return encode(isp1_creds)

    def _generate_encoded_time(self, datetime_):
        return generate_encoded_time(datetime_)


def conn_handler(handler):
    ''' Handler for processing data received from the DSN into PDUs'''
    hb_time = int(time.time())
    msg = b''

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
            if binascii.hexlify(hdr[:4]) == b'01000000':
                # Get length of body and check if the entirety of the
                # body has been received. If we can, process the message(s)
                body_len = utils.hexint(hdr[4:])
                if len(rem) < body_len:
                    break
                else:
                    body = rem[:body_len]
                    handler._data_queue.put(hdr + body)
                    msg = msg[len(hdr) + len(body):]
            # Heartbeat Received
            elif binascii.hexlify(hdr[:8]) == b'0300000000000000':
                msg = rem
            else:
                err = (
                    'Received PDU with unexpected header. '
                    'Unable to parse data further.\n'
                )
                ait.core.log.error(err)
                ait.core.log.error('\n'.join([msg[i:i+16] for i in range(0, len(msg), 16)]))
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
            ait.core.log.error('Unable to decode PDU. Skipping ...')
            continue
        except TypeError as e:
            ait.core.log.error('Unable to decode PDU due to type error ...')
            continue

        handler._handle_pdu(decoded_pdu)


def generate_encoded_time(datetime_):
        days = (datetime_ - CCSDS_EPOCH).days
        millisecs = (datetime_ - datetime_.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds() * 1000
        microsecs = int(round(millisecs % 1 * 1000))
        millisecs = int(millisecs)
        return struct.pack('!HIH', (datetime_ - CCSDS_EPOCH).days, millisecs, microsecs)
