import binascii
from collections import defaultdict
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


class AOSTransFrame(object):
    ''''''
    pass


class RAF(object):
    ''''''
    # TODO: Add error checking for actions based on current state
    _state = 'unbound'
    _handlers = defaultdict(list)
    _data_queue = gevent.queue.Queue()
    _invoke_id = 0

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
        self._credentials = bliss.config.get('sle.credentials', None)
        self._telem_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        if not self._hostname or not self._port:
            msg = 'Connection configuration missing hostname ({}) or port ({})'
            msg = msg.format(self._hostname, self._port)
            bliss.core.log.error(msg)
            raise ValueError(msg)

        self._handlers['SleBindReturn'].append(self._bind_return_handlers)
        self._handlers['SleUnbindReturn'].append(self._unbind_return_handlers)
        self._handlers['RafStartReturn'].append(self._start_return_handlers)
        self._handlers['RafStopReturn'].append(self._stop_return_handlers)
        self._handlers['RafTransferBuffer'].append(self._data_transfer_handlers)
        self._handlers['SleScheduleStatusReportReturn'].append(self._schedule_status_report_return_handlers)
        self._handlers['RafStatusReportInvocation'].append(self._status_report_invoc_handlers)
        self._handlers['RafGetParameterReturn'].append(self._get_param_return_handlers)
        self._handlers['RafTransferDataInvocation'].append(self._transfer_data_invoc_handlers)
        self._handlers['RafSyncNotifiyInvocation'].append(self._sync_notify_handlers)

        self._conn_monitor = gevent.spawn(raf_conn_handler, self)
        self._data_processor = gevent.spawn(raf_data_processor, self)

    @property
    def invoke_id(self):
        iid = self._invoke_id
        self._invoke_id += 1
        return iid

    def add_handlers(self, event, handler):
        ''''''
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

    def bind(self):
        ''''''
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

        bliss.core.log.info('Sending Bind request ...')
        self.send(TML_SLE_MSG)

    def unbind(self, reason=0):
        ''''''
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
        bliss.core.log.info('Sending Unbind request ...')
        self.send(TML_SLE_MSG)

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
        ''''''
        pass

    def start(self, start_time, end_time):
        start_invoc = RafUsertoProviderPdu()

        if self._credentials:
            pass
        else:
            start_invoc['rafStartInvocation']['invokerCredentials']['unused'] = None

        start_invoc['rafStartInvocation']['invokeId'] = self.invoke_id
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

        stop_invoc['rafStopInvocation']['invokeId'] = self.invoke_id
        en = encode(stop_invoc)
        TML_SLE_MSG = struct.pack(
                TML_SLE_FORMAT,
                TML_SLE_TYPE,
                len(en),
        ) + en
        bliss.core.log.info('Sending data stop invocation ...')
        self.send(TML_SLE_MSG)

    def _need_heartbeat(self, time_delta):
        ''''''
        return time_delta >= self._heartbeat

    def send_heartbeat(self):
        ''''''
        hb = struct.pack(
                TML_CONTEXT_HB_FORMAT,
                TML_CONTEXT_HEARTBEAT_TYPE,
                0
        )
        self.send(hb)

    @staticmethod
    def decode(message):
        ''''''
        return decode(message, asn1Spec=RafProvidertoUserPdu())

    def _handle_pdu(self, pdu):
        ''''''
        try:
            pdu_handlerss = self._handlers[pdu.getComponent().__class__.__name__]
            for h in pdu_handlerss:
                h(pdu)
        except KeyError as e:
            err = (
                'PDU of type {} has no associated handlers. '
                'Unable to process further and skipping ...'
            )
            bliss.core.log.error(err.format(pdu.getName()))

    def _bind_return_handlers(self, pdu):
        ''''''
        result = pdu['rafBindReturn']['result']
        if 'positive' in result:
            bliss.core.log.info('Bind successful')
            self._state = 'ready'
        else:
            bliss.core.log.info('Bind unsuccessful: {}'.format(result['negative']))
            self._state = 'unbound'

    def _unbind_return_handlers(self, pdu):
        ''''''
        result = pdu['rafUnbindReturn']['result']
        if 'positive' in result:
            bliss.core.log.info('Unbind successful')
            self._state = 'unbound'
        else:
            bliss.core.log.error('Unbind failed. Treating connection as unbound')
            self._state = 'unbound'

    def _start_return_handlers(self, pdu):
        ''''''
        result = pdu['rafStartReturn']['result']
        if 'positiveResult' in result:
            bliss.core.log.info('Start successful')
            self._state = 'active'
        else:
            result = result['negativeResult']
            if 'common' in result:
                diag = result['common']
            else:
                diag = result['specific']
            bliss.core.log.info('Start unsuccessful: {}'.format(diag))
            self._state = 'ready'

    def _stop_return_handlers(self, pdu):
        ''''''
        result = pdu['rafStopReturn']['result']
        if 'positiveResult' in result:
            bliss.core.log.info('Stop successful')
            self._state = 'ready'
        else:
            bliss.core.log.info('Stop unsuccessful: {}'.format(result['negativeResult']))
            self._state = 'active'

    def _data_transfer_handlers(self, pdu):
        ''''''
        self._handle_pdu(pdu['rafTransferBuffer'][0])

    def _transfer_data_invoc_handlers(self, pdu):
        ''''''
        frame = pdu.getComponent()
        if 'data' in frame and frame['data'].isValue:
            tm_data = frame['data'].asOctets()

        else:
            err = (
                'RafTransferBuffer received but data cannot be located. '
                'Skipping further processing of this PDU ...'
            )
            bliss.core.log.info(err)
            return

        bliss.core.log.info('We got some data. Length: {}'.format(len(tm_data)))
        tmf = bliss.sle.TMTransFrame(tm_data)
        self._telem_sock.sendto(tmf._data[0], ('localhost', 3076))

    def _sync_notify_handlers(self, pdu):
        ''''''
        notification_name = pdu['notification'].getName()
        notification = pdu['notification'].getComponent()

        if notification_name() == 'lossFrameSync':
            report = (
                'Frame Sync has been lost. See report below ... \n\n'
                'Lock Status Report\n'
                'Lock Time: {}\n'
                'Carrier Lock Status: {}\n'
                'Sub-Carrier Lock Status: {}\n'
                'Symbol Sync Lock Status: {}'
            ).format(
                notification['time'],
                notification['carrierLockStatus'],
                notification['subcarrierLockStatus'],
                notification['symbolSynclockStatus']
            )
        elif notification_name() == 'productionStatusChange':
            prod_status_labels = ['running', 'interrupted', 'halted']
            report = 'Production Status Report: {}'.format(
                prod_status_labels[int(notification)]
            )
        elif notification_name() == 'excessiveDataBacklog':
            report = 'Excessive Data Backlog Detected'
        elif notification_name() == 'endOfData':
            report = 'End of Data Received'
        else:
            report = 'Received unknown sync notification: {}'.format(notification_name)

        bliss.core.log.warn(report)

    def _schedule_status_report_return_handlers(self, pdu):
        ''''''
        if pdu['result'].getName() == 'positiveResult':
            bliss.core.log.info('Status Report Scheduled Successfully')
        else:
            diag = pdu['result'].getComponent()

            if diag.getName() == 'common':
                diag_options = ['duplicateInvokeId', 'otherReason']
            else:
                diag_options = ['notSupportedInThisDeliveryMode', 'alreadyStopped', 'invalidReportingCycle']

            reason = diag_options[int(diag.getComponent())]
            bliss.core.log.warning('Status Report Scheduling Failed. Reason: {}'.format(reason))

    def _status_report_invoc_handlers(self, pdu):
        ''''''
        report = 'Status Report\n'
        report += 'Number of Error Free Frames: {}\n'.format(pdu['errorFreeFrameNumber'])
        report += 'Number of Delivered Frames: {}\n'.format(pdu['deliveredFrameNumber'])

        frame_lock_status = ['In Lock', 'Out of Lock', 'Unknown']
        report += 'Frame Sync Lock Status: {}\n'.format(frame_lock_status[pdu['frameSyncLockStatus']])

        symbol_lock_status = ['In Lock', 'Out of Lock', 'Unknown']
        report += 'Symbol Sync Lock Status: {}\n'.format(symbol_lock_status[pdu['symbolSyncLockStatus']])

        lock_status = ['In Lock', 'Out of Lock', 'Not In Use', 'Unknown']
        report += 'Subcarrier Lock Status: {}\n'.format(lock_status[pdu['subcarrierLockStatus']])

        carrier_lock_status = ['In Lock', 'Out of Lock', 'Unknown']
        report += 'Carrier Lock Status: {}\n'.format(lock_status[pdu['carrierLockStatus']])

        production_status = ['Running', 'Interrupted', 'Halted']
        report += 'Production Status: {}'.format(production_status[pdu['productionStatus']])

        bliss.core.log.warning(report)

    def _get_param_return_handlers(self, pdu):
        ''''''
        pass


def raf_conn_handler(raf_handler):
    hb_time = int(time.time())
    msg = ''

    while True:
        gevent.sleep(0)

        now = int(time.time())
        if raf_handler._need_heartbeat(now - hb_time):
            hb_time = now
            raf_handler.send_heartbeat()

        try:
            msg = msg + raf_handler._socket.recv(raf_handler._buffer_size)
        except:
            gevent.sleep(1)

        while len(msg) >= 8:
            hdr, rem = msg[:8], msg[8:]

            # PDU Received
            if binascii.hexlify(hdr[:4]) == '01000000':
                # Get length of body
                body_len = _hexint(hdr[4:])
                # Check if the entirety of the body has been received
                if len(rem) < body_len:
                    # If it hasn't, break
                    break
                else:
                    # If it has, read the body
                    body = rem[:body_len]
                    # Write out the hdr + body to the data queue
                    raf_handler._data_queue.put(hdr + body)
                    # import hexdump 
                    # hexdump.hexdump(hdr + body)
                    # DATA_QUEUE.put(hdr + body)
                    # shrink msg by the expected size
                    # msg = msg[:len(hdr) + len(body)]
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
                sys.exit(1)


def raf_data_processor(raf_handler):
    while True:
        gevent.sleep(0)
        if raf_handler._data_queue.empty():
            continue

        msg = raf_handler._data_queue.get()
        hdr, body = msg[:8], msg[8:]

        try:
            decoded_pdu, remainder = bliss.sle.RAF.decode(body)
        except pyasn1.error.PyAsn1Error as e:
            bliss.core.log.error('Unable to decode PDU. Skipping ...')
            continue
        except TypeError as e:
            bliss.core.log.error('Unable to decode PDU due to type error ...')
            continue

        raf_handler._handle_pdu(decoded_pdu)
