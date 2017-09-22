import binascii
from collections import defaultdict
import datetime as dt
import errno
import fcntl
import socket
import struct
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

import frames
from bliss.sle.pdu.rcf import *
from bliss.sle.pdu import rcf
import util

TML_SLE_FORMAT = '!ii'
TML_SLE_TYPE = 0x01000000

TML_CONTEXT_MSG_FORMAT = '!IIbbbbIHH'
TML_CONTEXT_MSG_TYPE = 0x02000000

TML_CONTEXT_HB_FORMAT = '!ii'
TML_CONTEXT_HEARTBEAT_TYPE = 0x03000000

CCSDS_EPOCH = dt.datetime(1958, 1, 1)


class RCF(object):
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
        self._inst_id = kwargs.get('inst_id', None)

        if not self._hostname or not self._port:
            msg = 'Connection configuration missing hostname ({}) or port ({})'
            msg = msg.format(self._hostname, self._port)
            bliss.core.log.error(msg)
            raise ValueError(msg)

        self._handlers['RcfBindReturn'].append(self._bind_return_handlers)
        self._handlers['RcfUnbindReturn'].append(self._unbind_return_handlers)
        self._handlers['RcfStartReturn'].append(self._start_return_handlers)
        self._handlers['RcfStopReturn'].append(self._stop_return_handlers)
        self._handlers['RcfTransferBuffer'].append(self._data_transfer_handlers)
        self._handlers['RcfScheduleStatusReportReturn'].append(self._schedule_status_report_return_handlers)
        self._handlers['RcfStatusReportInvocation'].append(self._status_report_invoc_handlers)
        self._handlers['RcfGetParameterReturn'].append(self._get_param_return_handlers)
        self._handlers['AnnotatedFrame'].append(self._transfer_data_invoc_handlers)
        self._handlers['SyncNotification'].append(self._sync_notify_handlers)

        self._conn_monitor = gevent.spawn(rcf_conn_handler, self)
        self._data_processor = gevent.spawn(rcf_data_processor, self)

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

    def bind(self, inst_id=None):
        ''''''
        bind_invoc = RcfUsertoProviderPdu()

        if self._credentials:
            pass
        else:
            bind_invoc['rcfBindInvocation']['invokerCredentials']['unused'] = None

        bind_invoc['rcfBindInvocation']['initiatorIdentifier'] = 'LSE'
        bind_invoc['rcfBindInvocation']['responderPortIdentifier'] = 'default'
        bind_invoc['rcfBindInvocation']['serviceType'] = 'rtnChFrames'
        bind_invoc['rcfBindInvocation']['versionNumber'] = 5

        inst_id = inst_id if inst_id else self._inst_id
        if not inst_id:
            raise AttributeError('No instance id provided. Unable to bind.')

        inst_ids = [
            st.split('=')
            for st in inst_id.split('.')
        ]

        sii = ServiceInstanceIdentifier()
        for i, iden in enumerate(inst_ids):
            identifier = getattr(rcf, iden[0].replace('-', '_'))
            siae = ServiceInstanceAttributeElement()
            siae['identifier'] = identifier
            siae['siAttributeValue'] = iden[1]
            sia = ServiceInstanceAttribute()
            sia[0] = siae
            sii[i] = sia
        bind_invoc['rcfBindInvocation']['serviceInstanceIdentifier'] = sii


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
        stop_invoc = RcfUsertoProviderPdu()

        if self._credentials:
            pass
        else:
            stop_invoc['rcfUnbindInvocation']['invokerCredentials']['unused'] = None

        stop_invoc['rcfUnbindInvocation']['unbindReason'] = reason
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
        self._conn_monitor.kill()
        self._data_processor.kill()
        self._socket.close()
        self._telem_sock.close()

    def get_parameter(self):
        ''''''
        #TODO: Implement get parameter
        pass

    def start(self, start_time, end_time, spacecraft_id, version, master_channel=False, virtual_channel=None):
        #TODO: Should likely move some of the attributes to optional config on __init__
        if not master_channel and not virtual_channel:
            err = (
                'Transfer start invocation requires a master channel or '
                'virtual channel from which to receive frames.'
            )
            raise AttributeError(err)

        start_invoc = RcfUsertoProviderPdu()

        if self._credentials:
            pass
        else:
            start_invoc['rcfStartInvocation']['invokerCredentials']['unused'] = None

        start_invoc['rcfStartInvocation']['invokeId'] = self.invoke_id
        start_time = struct.pack('!HIH', (start_time - CCSDS_EPOCH).days, 0, 0)
        stop_time = struct.pack('!HIH', (end_time - CCSDS_EPOCH).days, 0, 0)

        start_invoc['rcfStartInvocation']['startTime']['known']['ccsdsFormat'] = None
        start_invoc['rcfStartInvocation']['startTime']['known']['ccsdsFormat'] = start_time
        start_invoc['rcfStartInvocation']['stopTime']['known']['ccsdsFormat'] = None
        start_invoc['rcfStartInvocation']['stopTime']['known']['ccsdsFormat'] = stop_time

        req_gvcid = GvcId()
        req_gvcid['spacecraftId'] = spacecraft_id
        req_gvcid['versionNumber'] = version

        if master_channel:
            req_gvcid['vcId']['masterChannel'] = None
        else:
            req_gvcid['vcId']['virtualChannel'] = virtual_channel

        start_invoc['rcfStartInvocation']['requestedGvcId'] = req_gvcid

        en = encode(start_invoc)
        TML_SLE_MSG = struct.pack(
                TML_SLE_FORMAT,
                TML_SLE_TYPE,
                len(en),
        ) + en
        bliss.core.log.info('Sending data start invocation ...')
        self.send(TML_SLE_MSG)

    def stop(self):
        stop_invoc = RcfUsertoProviderPdu()

        if self._credentials:
            pass
        else:
            stop_invoc['rcfStopInvocation']['invokerCredentials']['unused'] = None

        stop_invoc['rcfStopInvocation']['invokeId'] = self.invoke_id
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
        return decode(message, asn1Spec=RcfProvidertoUserPdu())

    def _handle_pdu(self, pdu):
        ''''''
        pdu_key = pdu.getName()
        pdu_key = pdu_key[:1].upper() + pdu_key[1:]
        if pdu_key in self._handlers:
            pdu_handlerss = self._handlers[pdu_key]
            for h in pdu_handlerss:
                h(pdu)
        else:
            err = (
                'PDU of type {} has no associated handlers. '
                'Unable to process further and skipping ...'
            )
            bliss.core.log.error(err.format(pdu_key))

    def _bind_return_handlers(self, pdu):
        ''''''
        result = pdu['rcfBindReturn']['result']
        if 'positive' in result:
            bliss.core.log.info('Bind successful')
            self._state = 'ready'
        else:
            bliss.core.log.info('Bind unsuccessful: {}'.format(result['negative']))
            self._state = 'unbound'

    def _unbind_return_handlers(self, pdu):
        ''''''
        result = pdu['rcfUnbindReturn']['result']
        if 'positive' in result:
            bliss.core.log.info('Unbind successful')
            self._state = 'unbound'
        else:
            bliss.core.log.error('Unbind failed. Treating connection as unbound')
            self._state = 'unbound'

    def _start_return_handlers(self, pdu):
        ''''''
        result = pdu['rcfStartReturn']['result']
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
        result = pdu['rcfStopReturn']['result']
        if 'positiveResult' in result:
            bliss.core.log.info('Stop successful')
            self._state = 'ready'
        else:
            bliss.core.log.info('Stop unsuccessful: {}'.format(result['negativeResult']))
            self._state = 'active'

    def _data_transfer_handlers(self, pdu):
        ''''''
        self._handle_pdu(pdu['rcfTransferBuffer'][0])

    def _transfer_data_invoc_handlers(self, pdu):
        ''''''
        frame = pdu.getComponent()
        if 'data' in frame and frame['data'].isValue:
            tm_data = frame['data'].asOctets()

        else:
            err = (
                'RcfTransferBuffer received but data cannot be located. '
                'Skipping further processing of this PDU ...'
            )
            bliss.core.log.info(err)
            return

        tmf = frames.TMTransFrame(tm_data)
        bliss.core.log.info('Sending {} bytes to telemetry port'.format(len(tmf._data[0])))
        self._telem_sock.sendto(tmf._data[0], ('localhost', 3076))

    def _sync_notify_handlers(self, pdu):
        ''''''
        notification_name = pdu.getComponent()['notification'].getName()
        notification = pdu.getComponent()['notification'].getComponent()

        if notification_name == 'lossFrameSync':
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
        elif notification_name == 'productionStatusChange':
            prod_status_labels = ['running', 'interrupted', 'halted']
            report = 'Production Status Report: {}'.format(
                prod_status_labels[int(notification)]
            )
        elif notification_name == 'excessiveDataBacklog':
            report = 'Excessive Data Backlog Detected'
        elif notification_name == 'endOfData':
            report = 'End of Data Received'
        else:
            report = 'Received unknown sync notification: {}'.format(notification_name)

        bliss.core.log.info(report)

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


def rcf_conn_handler(rcf_handler):
    hb_time = int(time.time())
    msg = ''

    while True:
        gevent.sleep(0)

        now = int(time.time())
        if rcf_handler._need_heartbeat(now - hb_time):
            hb_time = now
            rcf_handler.send_heartbeat()

        try:
            msg = msg + rcf_handler._socket.recv(rcf_handler._buffer_size)
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
                    rcf_handler._data_queue.put(hdr + body)
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


def rcf_data_processor(rcf_handler):
    while True:
        gevent.sleep(0)
        if rcf_handler._data_queue.empty():
            continue

        msg = rcf_handler._data_queue.get()
        hdr, body = msg[:8], msg[8:]

        try:
            decoded_pdu, remainder = RCF.decode(body)
        except pyasn1.error.PyAsn1Error as e:
            bliss.core.log.error('Unable to decode PDU. Skipping ...')
            continue
        except TypeError as e:
            bliss.core.log.error('Unable to decode PDU due to type error ...')
            continue

        rcf_handler._handle_pdu(decoded_pdu)
