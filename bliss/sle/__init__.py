import binascii
import datetime as dt
import errno
import fcntl
import socket
import struct
import sys
import time

import gevent
import gevent.queue
import gevent.socket
import gevent.monkey; gevent.monkey.patch_all()

import hexdump

from pyasn1.codec.ber.encoder import encode
from pyasn1.codec.der.encoder import encode as derencode
from pyasn1.codec.der.decoder import decode

import bliss.core
import bliss.core.log
from bliss.sle.pdus.raf import *
from bliss.sle.pdus import raf

TML_SLE_FORMAT = '!ii'
TML_SLE_TYPE = 0x01000000

TML_CONTEXT_MSG_FORMAT = '!IIbbbbIHH'
TML_CONTEXT_MSG_TYPE = 0x02000000

TML_CONTEXT_HB_FORMAT = '!ii'
TML_CONTEXT_HEARTBEAT_TYPE = 0x03000000

CCSDS_EPOCH = dt.datetime(1958, 1, 1)

DATA_QUEUE = gevent.queue.Queue()

def _hexint(b):
    return int(binascii.hexlify(b), 16)

class TMTransFrame(dict):
    def __init__(self, data=None):
        super(TMTransFrame, self).__init__()

        self._data = []
        self.is_idle = False
        self.has_no_pkts = False
        if data:
            self.decode(data)

    def decode(self, data):
        ''' Decode data as a TM Transfer Frame '''
        self['version'] = _hexint(data[0]) & 0xA0
        self['spacecraft_id'] = _hexint(data[0:2]) & 0x3F00
        self['virtual_channel_id'] = _hexint(data[1]) & 0x0E
        self['ocf_flag'] = _hexint(data[1]) & 0x01
        self['master_chan_frame_count'] = data[2]
        self['virtual_chan_frame_count'] = data[3]
        self['sec_header_flag'] = _hexint(data[4:6]) & 0x8000
        self['sync_flag'] = _hexint(data[4:6]) & 0x4000
        self['pkt_order_flag'] = _hexint(data[4:6]) & 0x2000
        self['seg_len_id'] = _hexint(data[4:6]) & 0x1800
        self['first_hdr_ptr'] = _hexint(data[4:6]) & 0x07FF

        if self['first_hdr_ptr'] == b'11111111110':
            self.is_idle = True
            return

        if self['first_hdr_ptr'] == b'11111111111':
            self.has_no_pkts = True
            return

        # Process the secondary header. This hasn't been tested ...
        if self['sec_header_flag']:
            self['sec_hdr_ver'] = _hexint(data[6]) & 0xC0
            sec_hdr_len = _hexint(data[6]) & 0x3F
            sec_hdr_data = data[7:7+sec_hdr_len]
            pkt_data = data[8 + sec_hdr_len:]
        else:
            pkt_data = data[6:]

        # We're assuming that we're getting CCSDS packets w/o secondary
        # headers here. All of this needs to be fleshed out more
        while True:
            if len(pkt_data) == 0:
                break

            pkt_data_len = _hexint(pkt_data[4:6])

            if pkt_data_len <= len(pkt_data[6:]):
                self._data.append(pkt_data[6:6 + pkt_data_len])

                try:
                    pkt_data = pkt_data[6 + pkt_data_len:]
                except:
                    break
            # We're not handling the case where packets are split
            # across TM frames at the moment.
            else:
                # print 'Pkt split across TM frames. AAAHHHHH!!!'
                break

    def encode(self):
        pass


class SLE(object):
    def __init__(self, *args, **kwargs):

        self._hostname = bliss.config.get('sle.hostname',
                                          kwargs.get('hostname', None))
        self._port = bliss.config.get('sle.port',
                                      kwargs.get('port', None))
        self._heartbeat = bliss.config.get('sle.heartbeat',
                                           kwargs.get('heartbeat', 25))
        self._deadfactor = bliss.config.get('sle.deadfactor',
                                            kwargs.get('deadfactor', 5))
        self._buffer_size = bliss.config.get('sle.buffer_size',
                                             kwargs.get('buffer_size', 256000))

        if not self._hostname or not self._port:
            msg = 'Connection configuration missing hostname ({}) or port ({})'
            msg = msg.format(self._hostname, self._port)
            bliss.core.log.error(msg)
            raise ValueError(msg)

    def connect(self):
        ''' Setup connection with DSN 
        
        Initialize TCP connection with DSN and send context message
        to configure communication.
        '''
        self._socket = gevent.socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((self._hostname, self._port))

        context_msg = struct.pack(
            TML_CONTEXT_MSG_FORMAT,
            TML_CONTEXT_MSG_TYPE,
            0x0000000C,
            ord('I'), ord('S'), ord('P'), ord('1'),
            0x00000001,
            self._heartbeat,
            self._deadfactor
        )
        bliss.core.log.info('Connecting to SLE ...')
        self.send(context_msg)

    def send(self, data):
        ''' Send supplied data to DSN '''
        self._socket.send(data)

    def send_heartbeat(self):
        ''''''
        hb = struct.pack(
                TML_CONTEXT_HB_FORMAT,
                TML_CONTEXT_HEARTBEAT_TYPE,
                0
        )
        self.send(hb)

class RAF(SLE):
    def __init__(self, *args, **kwargs):
        super(RAF, self).__init__(*args, **kwargs)
        self._credentials = bliss.config.get('sle.credentials', None)

    def connect(self):
        super(RAF, self).connect()
        # self._conn_monitor = gevent.spawn(monitor_data, self)
        # self._conn_monitor = gevent.spawn(drop_handler, self)
        self._conn_monitor = gevent.spawn(jason3_handler, self)

    def bind(self):
        bind_invoc = RafUsertoProviderPdu()

        if self._credentials:
            pass
        else:
            bind_invoc['rafBindInvocation']['invokerCredentials']['unused'] = None

        bind_invoc['rafBindInvocation']['initiatorIdentifier'] = 'LSE'
        bind_invoc['rafBindInvocation']['responderPortIdentifier'] = 'default'
        bind_invoc['rafBindInvocation']['serviceType'] = 'rtnAllFrames'
        bind_invoc['rafBindInvocation']['versionNumber'] = 5

        inst_ids = 'sagr=LSE-SSC.spack=Test.rsl-fg=1.raf=onlc1'.split('.')
        inst_ids = [
            st.split('=')
            for st in inst_ids
        ]

        sii = ServiceInstanceIdentifier()
        for i, iden in enumerate(inst_ids):
            identifier = getattr(raf, iden[0].replace('-', '_'))
            siae = ServiceInstanceAttributeElement()
            siae['identifier'] = identifier
            siae['siAttributeValue'] = iden[1]
            sia = ServiceInstanceAttribute()
            sia[0] = siae
            sii[i] = sia
        bind_invoc['rafBindInvocation']['serviceInstanceIdentifier'] = sii


        en = encode(bind_invoc)
        TML_SLE_MSG = struct.pack(
                TML_SLE_FORMAT,
                TML_SLE_TYPE,
                len(en),
        ) + en

        bliss.core.log.info('Binding to RAF interface ...')
        self.send(TML_SLE_MSG)

    def unbind(self, reason=0):
        stop_invoc = RafUsertoProviderPdu()

        if self._credentials:
            pass
        else:
            stop_invoc['rafUnbindInvocation']['invokerCredentials']['unused'] = None

        stop_invoc['rafUnbindInvocation']['unbindReason'] = reason
        en = encode(stop_invoc)
        TML_SLE_MSG = struct.pack(
                TML_SLE_FORMAT,
                TML_SLE_TYPE,
                len(en),
        ) + en
        bliss.core.log.info('Unbinding from RAF interface ...')
        self.send(TML_SLE_MSG)

    def send_start_invocation(self, start_time, end_time):
        start_invoc = RafUsertoProviderPdu()

        if self._credentials:
            pass
        else:
            start_invoc['rafStartInvocation']['invokerCredentials']['unused'] = None

        start_invoc['rafStartInvocation']['invokeId'] = 12345
        start_time = struct.pack('!HIH', (start_time - CCSDS_EPOCH).days, 0, 0)
        stop_time = struct.pack('!HIH', (end_time - CCSDS_EPOCH).days, 0, 0)

        start_invoc['rafStartInvocation']['startTime']['known']['ccsdsFormat'] = None
        start_invoc['rafStartInvocation']['startTime']['known']['ccsdsFormat'] = start_time
        start_invoc['rafStartInvocation']['stopTime']['known']['ccsdsFormat'] = None
        start_invoc['rafStartInvocation']['stopTime']['known']['ccsdsFormat'] = stop_time
        start_invoc['rafStartInvocation']['requestedFrameQuality'] = 2

        en = encode(start_invoc)
        TML_SLE_MSG = struct.pack(
                TML_SLE_FORMAT,
                TML_SLE_TYPE,
                len(en),
        ) + en
        bliss.core.log.info('Sending data start invocation ...')
        self.send(TML_SLE_MSG)

    def stop(self):
        stop_invoc = RafUsertoProviderPdu()

        if self._credentials:
            pass
        else:
            stop_invoc['rafStopInvocation']['invokerCredentials']['unused'] = None

        stop_invoc['rafStopInvocation']['invokeId'] = 12345
        en = encode(stop_invoc)
        TML_SLE_MSG = struct.pack(
                TML_SLE_FORMAT,
                TML_SLE_TYPE,
                len(en),
        ) + en
        bliss.core.log.info('Sending data stop invocation ...')
        self.send(TML_SLE_MSG)

    @staticmethod
    def decode(message):
        decoded_msg, remainder = decode(message, asn1Spec=RafProvidertoUserPdu())
        return (decoded_msg, remainder)

def monitor_data(RafHandler):
    tmp_hdr = None
    tmp_bdy = ''
    hb_time = int(time.time())
    read_msgs = 0
    while True:
        gevent.sleep(0)

        now = int(time.time())
        if now - hb_time >= RafHandler._heartbeat:
            hb_time = now
            RafHandler.send_heartbeat()

        try:
            msg = RafHandler._socket.recv(RafHandler._buffer_size)
            if len(msg) > 0:
                read_msgs += 1
                print 'Receiving message: {}, {}'.format(len(msg), read_msgs)
        except socket.error, e:
            err = e.args[0]
            if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
                continue
            else:
                # a "real" error occurred
                print e
                sys.exit(1)
        else:
            if not tmp_hdr:
                if msg[:4] != '\x01\x00\x00\x00':
                    continue
            
                tmp_hdr = msg[:8]

                if len(msg) > 8:
                    msg = tmp_bdy + msg[8:]
                else:
                    msg = ''
            elif tmp_hdr and tmp_bdy:
                msg = tmp_bdy + msg

            exp_body_len = int(binascii.hexlify(bytearray(tmp_hdr)[4:]), 16)

            if exp_body_len == len(msg):
                DATA_QUEUE.put((tmp_hdr, msg))
                tmp_hdr = None
                tmp_bdy = ''
            elif exp_body_len < len(msg):
                exp_body_len = int(binascii.hexlify(bytearray(tmp_hdr)[4:]), 16)
                if tmp_bdy:
                    msg = tmp_bdy + msg

                while len(msg) > exp_body_len:
                    body = msg[:exp_body_len]
                    msg = msg[exp_body_len:]
                    DATA_QUEUE.put((tmp_hdr, body))

                    if len(msg) >= 8:
                        tmp_hdr = msg[:8]
                        exp_body_len = int(binascii.hexlify(bytearray(tmp_hdr)[4:]), 16)
                    elif len(msg) == 0:
                        tmp_body = None
                        tmp_hdr = ''
                        break
                else:
                    if len(msg) != 0:
                        tmp_bdy = msg
            else:
                tmp_bdy = msg

def drop_handler(RafHandler):
    ignore_init = True
    msg = ''
    hb_time = int(time.time())
    cnt = 0
    while True:
        gevent.sleep(0)

        now = int(time.time())
        if now - hb_time >= RafHandler._heartbeat:
            hb_time = now
            RafHandler.send_heartbeat()

        msg = msg + RafHandler._socket.recv(RafHandler._buffer_size)

        if ignore_init and len(msg) > 56:
            msg = msg[56:]
            ignore_init = False

        while len(msg) > 1576:
            print 'Processing msg(s): {}'.format(len(msg))
            pdu = msg[:1576]
            hdr = pdu[:8]
            body = pdu[8:]

            if binascii.hexlify(hdr[:4]) == '01000000':
                DATA_QUEUE.put((hdr, body))
                cnt += 1
                print "Wrote {} pdu".format(cnt)
                msg = msg[1576:]
            elif binascii.hexlify(hdr[:8]) == '0300000000000000':
                msg = msg[8:]
            else:
                print 'What does this start with. No one knows'
                print binascii.hexlify(hdr)


def jason3_handler(RafHandler):
    ignore_init = True
    msg = ''
    hb_time = int(time.time())
    cnt = 0
    while True:
        gevent.sleep(0)

        now = int(time.time())
        if now - hb_time >= RafHandler._heartbeat:
            hb_time = now
            RafHandler.send_heartbeat()

        read = RafHandler._socket.recv(RafHandler._buffer_size)
        msg = msg + read

        if ignore_init and len(msg) > 56:
            msg = msg[56:]
            ignore_init = False

        while len(msg) > 251:
            pdu = msg[:251]
            hdr = pdu[:8]
            body = pdu[8:]

            if binascii.hexlify(hdr[:4]) == '01000000':
                DATA_QUEUE.put((hdr, body))
                cnt += 1
                msg = msg[251:]
            elif binascii.hexlify(hdr[:8]) == '0300000000000000':
                msg = msg[8:]
            else:
                bliss.core.log.error('Unexpected packet header ...')

