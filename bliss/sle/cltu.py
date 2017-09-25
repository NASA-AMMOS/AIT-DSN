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

import pyasn1.error
from pyasn1.codec.ber.encoder import encode
from pyasn1.codec.der.encoder import encode as derencode
from pyasn1.codec.der.decoder import decode

import bliss.core
import bliss.core.log

import frames
from bliss.sle.pdu.cltu import *
from bliss.sle.pdu import cltu
import util

TML_SLE_FORMAT = '!ii'
TML_SLE_TYPE = 0x01000000

TML_CONTEXT_MSG_FORMAT = '!IIbbbbIHH'
TML_CONTEXT_MSG_TYPE = 0x02000000

TML_CONTEXT_HB_FORMAT = '!ii'
TML_CONTEXT_HEARTBEAT_TYPE = 0x03000000

CCSDS_EPOCH = dt.datetime(1958, 1, 1)

class CLTU(object):
    ''''''
    # TODO: Add error checking for actions based on current state
    _state = 'unbound'
    _handlers = defaultdict(list)
    _data_queue = gevent.queue.Queue()
    _invoke_id = 0
    _cltu_id = 0
    event_invoc_id = 0

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

        self._handlers['CltuBindReturn'].append(self._bind_return_handler)
        self._handlers['CltuUnbindReturn'].append(self._unbind_return_handler)
        self._handlers['CltuStartReturn'].append(self._start_return_handler)
        self._handlers['CltuStopReturn'].append(self._stop_return_handler)
        self._handlers['CltuAsyncNotifyInvocation'].append(self._async_notify_invoc_handler)
        self._handlers['CltuTransferDataReturn'].append(self._trans_data_return_handler)
        self._handlers['CltuScheduleStatusReportReturn'].append(self._schedule_status_report_return_handler)
        self._handlers['CltuStatusReportInvocation'].append(self._status_report_invoc_handler)
        self._handlers['CltuGetParameterReturn'].append(self._get_param_return_handler)
        self._handlers['CltuPeerAbortInvocation'].append(self._peer_abort_handler)
        self._handlers['CltuThrowEventReturn'].append(self._throw_event_handler)

        self._conn_monitor = gevent.spawn(cltu_conn_handler, self)
        self._data_processor = gevent.spawn(cltu_data_processor, self)

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

    def bind(self, inst_id=None, version=5):
        bind_invoc = CltuUserToProviderPdu()

        if self._credentials:
            pass
        else:
            bind_invoc['cltuBindInvocation']['invokerCredentials']['unused'] = None

        bind_invoc['cltuBindInvocation']['initiatorIdentifier'] = 'LSE'
        bind_invoc['cltuBindInvocation']['responderPortIdentifier'] = 'default'
        bind_invoc['cltuBindInvocation']['serviceType'] = 'fwdCltu'
        bind_invoc['cltuBindInvocation']['versionNumber'] = version

        inst_id = inst_id if inst_id else self._inst_id
        if not inst_id:
            raise AttributeError('No instance id provided. Unable to bind.')

        inst_ids = [
            st.split('=')
            for st in inst_id.split('.')
        ]

        sii = ServiceInstanceIdentifier()
        for i, iden in enumerate(inst_ids):
            identifier = getattr(cltu, iden[0].replace('-', '_'))
            siae = ServiceInstanceAttributeElement()
            siae['identifier'] = identifier
            siae['siAttributeValue'] = iden[1]
            sia = ServiceInstanceAttribute()
            sia[0] = siae
            sii[i] = sia
        bind_invoc['cltuBindInvocation']['serviceInstanceIdentifier'] = sii


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
        stop_invoc = CltuUserToProviderPdu()

        if self._credentials:
            pass
        else:
            stop_invoc['cltuUnbindInvocation']['invokerCredentials']['unused'] = None

        stop_invoc['cltuUnbindInvocation']['unbindReason'] = reason
        en = encode(stop_invoc)
        TML_SLE_MSG = struct.pack(
                TML_SLE_FORMAT,
                TML_SLE_TYPE,
                len(en),
        ) + en
        bliss.core.log.info('Sending Unbind request ...')
        self.send(TML_SLE_MSG)

    def start(self):
        start_invoc = CltuUserToProviderPdu()

        if self._credentials:
            pass
        else:
            start_invoc['cltuStartInvocation']['invokerCredentials']['unused'] = None

        start_invoc['cltuStartInvocation']['invokeId'] = self.invoke_id
        start_invoc['cltuStartInvocation']['firstCltuIdentification'] = self._cltu_id

        en = encode(start_invoc)
        TML_SLE_MSG = struct.pack(
                TML_SLE_FORMAT,
                TML_SLE_TYPE,
                len(en),
        ) + en
        bliss.core.log.info('Sending data start invocation ...')
        self.send(TML_SLE_MSG)

    def stop(self):
        stop_invoc = CltuUserToProviderPdu()

        if self._credentials:
            pass
        else:
            stop_invoc['cltuStopInvocation']['invokerCredentials']['unused'] = None

        stop_invoc['cltuStopInvocation']['invokeId'] = self.invoke_id
        en = encode(stop_invoc)
        TML_SLE_MSG = struct.pack(
                TML_SLE_FORMAT,
                TML_SLE_TYPE,
                len(en),
        ) + en
        bliss.core.log.info('Sending data stop invocation ...')
        self.send(TML_SLE_MSG)

    def upload_cltu(self, tc_data, earliest_time=None, latest_time=None, delay=0, notify=False):
        ''''''
        pdu = CltuUserToProviderPdu()

        if self._credentials:
            pass
        else:
            pdu['cltuTransferDataInvocation']['invokerCredentials']['unused'] = None

        pdu['cltuTransferDataInvocation']['invokeId'] = self.invoke_id
        pdu['cltuTransferDataInvocation']['cltuIdentification'] = self._cltu_id
        self._cltu_id += 1

        if earliest_time:
            t = struct.pack('!HIH', (earliest_time - CCSDS_EPOCH).days, 0, 0)
            pdu['cltuTransferDataInvocation']['earliestTransmissionTime']['known']['ccsdsFormat'] = t
        else:
            pdu['cltuTransferDataInvocation']['earliestTransmissionTime']['undefined'] = None

        if latest_time:
            t = struct.pack('!HIH', (latest_time - CCSDS_EPOCH).days, 0, 0)
            pdu['cltuTransferDataInvocation']['latestTransmissionTime']['known']['ccsdsFormat'] = t
        else:
            pdu['cltuTransferDataInvocation']['latestTransmissionTime']['undefined'] = None

        pdu['cltuTransferDataInvocation']['delayTime'] = delay
        pdu['cltuTransferDataInvocation']['cltuData'] = tc_data

        if notify:
            pdu['cltuTransferDataInvocation']['slduRadiationNotification'] = 0
        else:
            pdu['cltuTransferDataInvocation']['slduRadiationNotification'] = 1

        en = encode(pdu)
        TML_SLE_MSG = struct.pack(
                TML_SLE_FORMAT,
                TML_SLE_TYPE,
                len(en),
        ) + en
        bliss.core.log.info('Sending TC Data ...')
        self.send(TML_SLE_MSG)

    def schedule_status_report(self, report_type='immediately', cycle=None):
        ''''''
        pdu = CltuUserToProviderPdu()

        if self._credentials:
            pass
        else:
            pdu['cltuScheduleStatusReportInvocation']['invokerCredentials']['unused'] = None

        pdu['cltuScheduleStatusReportInvocation']['invokeId'] = self.invoke_id

        if report_type == 'immediately':
            pdu['cltuScheduleStatusReportInvocation']['reportType'][report_type] = None
        elif report_type == 'periodically':
            pdu['cltuScheduleStatusReportInvocation']['reportType'][report_type] = cycle
        elif report_type == 'stop':
            pdu['cltuScheduleStatusReportInvocation']['reportType'][report_type] = None
        else:
            raise ValueError('Unknown report type: {}'.format(report_type))

        en = encode(pdu)
        TML_SLE_MSG = struct.pack(
                TML_SLE_FORMAT,
                TML_SLE_TYPE,
                len(en),
        ) + en
        bliss.core.log.info('Scheduling Status Report')
        self.send(TML_SLE_MSG)

    def get_parameter(self):
        ''''''
        #TODO: Implement
        pass

    def throw_event(self, event_id, event_qualifier):
        ''''''
        pdu = CltuUserToProviderPdu()

        if self._credentials:
            pass
        else:
            pdu['cltuThrowEventInvocation']['invokerCredentials']['unused'] = None

        pdu['cltuThrowEventInvocation']['invokeId'] = self.invoke_id
        pdu['cltuthroweventinvocation']['eventInvocationIdentification'] = self.event_invoc_id
        pdu['cltuthroweventinvocation']['eventIdentifier'] = event_id
        pdu['cltuthroweventinvocation']['eventQualifier'] = event_qualifier

    def peer_abort(self, reason=127):
        ''''''
        pdu = CltuUserToProviderPdu()
        pdu['cltuPeerAbortInvocation'] = reason

        en = encode(pdu)
        TML_SLE_MSG = struct.pack(
                TML_SLE_FORMAT,
                TML_SLE_TYPE,
                len(en),
        ) + en
        bliss.core.log.info('Sending Peer Abort')
        self.send(TML_SLE_MSG)
        self._state = 'unbound'

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
        return decode(message, asn1Spec=CltuProviderToUserPdu())

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

    def _bind_return_handler(self, pdu):
        ''''''
        result = pdu['cltuBindReturn']['result']
        if 'positive' in result:
            bliss.core.log.info('Bind successful')
            self._state = 'ready'
        else:
            bliss.core.log.info('Bind unsuccessful: {}'.format(result['negative']))
            self._state = 'unbound'

    def _unbind_return_handler(self, pdu):
        ''''''
        result = pdu['cltuUnbindReturn']['result']
        if 'positive' in result:
            bliss.core.log.info('Unbind successful')
            self._state = 'unbound'
        else:
            bliss.core.log.error('Unbind failed. Treating connection as unbound')
            self._state = 'unbound'

    def _trans_data_return_handler(self, pdu):
        ''''''
        result = pdu['cltuTransferDataReturn']['result']
        cltu_id = pdu['cltuTransferDataReturn']['cltuIdentification']
        buffer_avail = pdu['cltuTransferDataReturn']['cltuBufferAvailable']

        if 'positiveResult' in result:
            bliss.core.log.info('CLTU #{} trans. passed. Buffer avail.: {}'.format(
                cltu_id,
                buffer_avail
            ))
        else:
            result = result['negativeResult']
            if 'commmon' in result:
                opts = ['Duplicate Invoke Id', 'Other Reason']
                diag = opts[result['common']]
            else:
                opts = ['Unable to Process', 'Unable to Store', 'Out of Sequence',
                        'Inconsistent Time Range', 'Invalid Time', 'Late Sldu',
                        'Invalid Delay Time', 'CLTU Error']
                diag = opts[result['specific']]
            bliss.core.log.info('CLTU #{} trans. failed. Diag: {}. Buffer avail: {}'.format(
                cltu_id,
                diag,
                buffer_avail
            ))

    def _start_return_handler(self, pdu):
        ''''''
        result = pdu['cltuStartReturn']['result']
        if 'positiveResult' in result:
            self._start = result['positiveResult']['startRadiationTime']
            self._stop = result['positiveResult']['stopRadiationTime']
            bliss.core.log.info('Start Successful')
            self._state = 'active'
        else:
            result = result['negativeResult']
            if 'common' in result:
                diag = result['common']
            else:
                diag = result['specific']
            bliss.core.log.info('Start unsuccessful: {}'.format(diag))
            self._state = 'ready'

    def _stop_return_handler(self, pdu):
        ''''''
        result = pdu['cltuStopReturn']['result']
        if 'positiveResult' in result:
            bliss.core.log.info('Stop successful')
            self._state = 'ready'
        else:
            bliss.core.log.info('Stop unsuccessful: {}'.format(result['negativeResult']))
            self._state = 'active'

    def _async_notify_invoc_handler(self, pdu):
        pdu = pdu['cltuAsyncNotifyInvocation']

        msg = '\n'
        if 'cltuNoficiation' in pdu:
            msg += 'CLTU Notification: {}\n'.format(pdu['cltuNotification'].getName())

        if 'cltuLastProcessed' in pdu:
            if pdu['cltuLastProcessed'].getName() == 'noCltuProcessed':
                msg += 'Last Processed: None\n'
            else:
                lp = pdu['cltuLastProcessed'].getComponent()
                t = 'unknown'
                if 'known' in lp['radiationStartTime']:
                    t = binascii.hexlify(str(lp['radiationStartTime'].getComponent().getComponent()))

                msg += 'Last Processed: id: {} | rad start: {} | status: {}\n'.format(
                    lp['cltuIdentification'],
                    t,
                    lp['cltuStatus']
                )

        if 'cltuLastOk' in pdu:
            if pdu['cltuLastOk'].getName() == 'noCltuOk':
                msg += 'Last Ok: No CLTU Ok\n'
            else:
                lok = pdu['cltuLastOk'].getComponent()
                t = binascii.hexlify(str(lok['radiationStopTime'].getComponent()))

                msg += 'Last Ok: id: {} | end: {}\n'.format(lok['cltuIdentification'], t)

        if 'productionStatus' in pdu:
            prod_status = ['operational', 'configured', 'interrupted', 'halted']
            msg += 'Production Status: {}\n'.format(prod_status[pdu['productionStatus']])

        if 'uplinkStatus' in pdu:
            uplink_status = ['Status Not Avail.', 'No RF Avail.', 'No Bit Lock', 'Nominal']
            msg == 'Uplink Status: {}\n'.format(uplink_status[pdu['uplinkStatus']])

        bliss.core.log.info(msg)

    def _schedule_status_report_return_handler(self, pdu):
        ''''''
        pdu = pdu['cltuScheduleStatusReportReturn']

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

    def _status_report_invoc_handler(self, pdu):
        ''''''
        pdu = pdu['cltuStatusReportInvocation']

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

    def _get_param_return_handler(self, pdu):
        ''''''
        pdu = pdu['cltuGetParameterReturn']
    
    def _peer_abort_handler(self, pdu):
        ''''''
        pdu = pdu['cltuPeerAbortInvocation']
        opts = [
            'accessDenied', 'unexpectedResponderId', 'operationalRequirement',
            'protocolError', 'communicationsFailure', 'encodingError', 'returnTimeout',
            'endOfServiceProvisionPeriod', 'unsolicitedInvokeId', 'otherReason'
        ]
        bliss.core.log.error('Peer Abort Received. {}'.format(opts[pdu]))
        self._state = 'unbound'
        self.disconnect()

    def _throw_event_handler(self, pdu):
        ''''''
        pdu = pdu['cltuThrowEventReturn']
        eid = pdu['eventInvocationIdentification']

        if 'positiveResult' in pdu['result']:
            msg = 'Event Invocation Successful'
            self.event_invoc_id = eid
        else:
            diag = pdu['result'].getComponent()

            if diag.getName() == 'common':
                diag_options = ['duplicateInvokeId', 'otherReason']
            else:
                diag_options = [
                    'Operation Not Supported',
                    'Event Invoc Id Out of Sequence',
                    'No Such Event'
                ]
            diag = diag_options[diag]
            msg = 'Event Invocation #{} Failed. Reason: {}'.format(eid, diag)


def cltu_conn_handler(cltu_handler):
    hb_time = int(time.time())
    msg = ''

    while True:
        gevent.sleep(0)

        now = int(time.time())
        if cltu_handler._need_heartbeat(now - hb_time):
            hb_time = now
            cltu_handler.send_heartbeat()

        try:
            msg = msg + cltu_handler._socket.recv(cltu_handler._buffer_size)
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
                    cltu_handler._data_queue.put(hdr + body)
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


def cltu_data_processor(cltu_handler):
    while True:
        gevent.sleep(0)
        if cltu_handler._data_queue.empty():
            continue

        msg = cltu_handler._data_queue.get()
        hdr, body = msg[:8], msg[8:]

        try:
            decoded_pdu, remainder = CLTU.decode(body)
        except pyasn1.error.PyAsn1Error as e:
            bliss.core.log.error('Unable to decode PDU. Skipping ...')
            continue
        except TypeError as e:
            bliss.core.log.error('Unable to decode PDU due to type error ...')
            continue

        cltu_handler._handle_pdu(decoded_pdu)
