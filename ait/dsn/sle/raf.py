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

''' RAF Interface Module

The ait.dsn.sle.raf module provides SLE Return All Frames (RAF)
interface classes, methods, and attributes.

Classes:
    RAF: An extension of the generic ait.dsn.sle.common.SLE class which
        implements the RAF standard.
'''
import struct

import ait
import ait.core.log

import ait.dsn.sle.common as common
import ait.dsn.sle.frames as frames
from ait.dsn.sle.pdu.raf import *
from ait.dsn.sle.pdu import raf


class RAF(common.SLE):
    ''' SLE Return All Frames (RAF) interface class
    
    The RAF class extends the ait.dsn.sle.common.SLE base interface class
    and implements the RAF specification.

    The RAF class can respond to a number of returns from the SLE interface.
    The following are a list of the events to which handlers can be bound along
    with an explanation for when they would be encountered. The interface
    provides default handlers for each of these events which generally log
    information received via :mod:`ait.core.log`.

    Handlers will receive an instance of the received and decoded PDU. If you
    would like to see the specification for each possible you can view the
    class for each option in :class:`ait.dsn.sle.pdu.raf.RafProvidertoUserPdu`

    RafBindReturn:
        Response back from the provider after a bind request has been
        sent to the interface.

    RafUnbindReturn
        Response back from the provider after a unbind request has been
        sent to the interface.

    RafStartReturn
        Response back from the provider after a start data request has been
        sent to the interface.

    RafStopReturn
        Response back from the provider after a stop data request has been
        sent to the interface.

    RafTransferBuffer
        Response from the provider container a data transfer or notification.

    AnnotatedFrame
        A potential component of the PDU received by the RafTransferBuffer
        handler. If the provider is sending data to the user this is the handler
        that will fire to process the PDU.

    SyncNotification
        A potential component of the PDU received by the RafTransferBuffer
        handler. If the provider is sending a notification to the user this
        is the handler that will fire to process the PDU.

    RafScheduleStatusReportReturn
        Response back from the provider after a schedule status report request
        has been sent to the interface.

    RafStatusReportInvocation
        Response from the provider containing a status report.

    RafGetParameterReturn
        Response back from the provider after a Get Parameter request has been
        sent to the interface.

    RafPeerAbortInvocation
        Received from the provider to abort the connection.
    '''
    # TODO: Add error checking for actions based on current state

    def __init__(self, *args, **kwargs):
        self._inst_id = ait.config.get('dsn.sle.raf.inst_id',
                                       kwargs.get('inst_id', None))
        self._hostnames = ait.config.get('dsn.sle.raf.hostnames',
                                         kwargs.get('hostnames', None))
        self._port = ait.config.get('dsn.sle.raf.port',
                                    kwargs.get('port', None))

        super(self.__class__, self).__init__(*args, **kwargs)

        self._service_type = 'rtnAllFrames'
        self._version = ait.config.get('dsn.sle.raf.version',
                                       kwargs.get('version', 4))
        self._auth_level = ait.config.get('dsn.sle.raf.auth_level',
                                          kwargs.get('auth_level', self._auth_level))

        self.frame_output_port = int(ait.config.get('dsn.sle.frame_output_port',
                                                    kwargs.get('frame_output_port',
                                                               ait.DEFAULT_FRAME_PORT)))

        self._handlers['RafBindReturn'].append(self._bind_return_handler)
        self._handlers['RafUnbindReturn'].append(self._unbind_return_handler)
        self._handlers['RafStartReturn'].append(self._start_return_handler)
        self._handlers['RafStopReturn'].append(self._stop_return_handler)
        self._handlers['RafTransferBuffer'].append(self._data_transfer_handler)
        self._handlers['RafScheduleStatusReportReturn'].append(self._schedule_status_report_return_handler)
        self._handlers['RafStatusReportInvocation'].append(self._status_report_invoc_handler)
        self._handlers['RafGetParameterReturn'].append(self._get_param_return_handler)
        self._handlers['AnnotatedFrame'].append(self._transfer_data_invoc_handler)
        self._handlers['SyncNotification'].append(self._sync_notify_handler)
        self._handlers['RafPeerAbortInvocation'].append(self._peer_abort_handler)

    def bind(self, inst_id=None):
        ''' Bind to a RAF interface

        Arguments:
            inst_id:
                The instance id for the RAF interface to bind.
        '''
        pdu = RafUsertoProviderPdu()['rafBindInvocation']
        super(self.__class__, self).bind(pdu, inst_id=inst_id)

    def unbind(self, reason=0):
        ''' Unbind from the RAF interface
        
        Arguments:
            reason:
                An optional integer indicating the reason for the unbind. The
                valid integer values are defined in
                :class:`ait.dsn.sle.pdu.binds.UnbindReason`
        '''
        pdu = RafUsertoProviderPdu()['rafUnbindInvocation']
        super(self.__class__, self).unbind(pdu, reason=reason)

    def get_parameter(self):
        ''''''
        #TODO: Implement get parameter
        pass

    def start(self, start_time, end_time, frame_quality=2):
        ''' Send data start request to the RAF interface

        Arguments:
            start_time (:class:`datetime.datetime`):
                The start time (In ERT) for the data to be returned from the
                interface.

            end_time (:class:`datetime.datetime`):
                The end time (In ERT) for the data to be returned from the
                interface.

            frame_quality (optional integer):
                The quality of data to be returned from the interface. Valid
                options are defined in
                :class:`ait.dsn.sle.pdu.raf.RequestedFrameQuality`
        
        '''
        start_invoc = RafUsertoProviderPdu()

        if self._auth_level == 'all':
            start_invoc['rafStartInvocation']['invokerCredentials']['used'] = self.make_credentials()
        else:
            start_invoc['rafStartInvocation']['invokerCredentials']['unused'] = None

        start_invoc['rafStartInvocation']['invokeId'] = self.invoke_id

        if start_time is None:
            start_invoc['rafStartInvocation']['startTime']['undefined'] = None
        else:
            start_time = self._generate_encoded_time(start_time)
            start_invoc['rafStartInvocation']['startTime']['known']['ccsdsFormat'] = start_time

        if end_time is None:
            start_invoc['rafStartInvocation']['stopTime']['undefined'] = None
        else:
            stop_time = self._generate_encoded_time(end_time)
            start_invoc['rafStartInvocation']['stopTime']['known']['ccsdsFormat'] = stop_time

        start_invoc['rafStartInvocation']['requestedFrameQuality'] = frame_quality

        ait.core.log.info('Sending data start invocation ...')
        self.send(self.encode_pdu(start_invoc))

    def stop(self):
        ''' Send data stop request to the RAF interface '''
        pdu = RafUsertoProviderPdu()['rafStopInvocation']
        super(self.__class__, self).stop(pdu)

    def schedule_status_report(self, report_type='immediately', cycle=None):
        ''' Send a status report schedule request to the RAF interface
        
        Arguments:
            report_type (string):
                The type of report type. One of 'immediately', 'periodically',
                or 'stop'. If the report type requested is 'periodically' a
                report will be sent every 'cycle' seconds.

            cycle (integer):
                How often in seconds a report of type 'periodically' should be
                sent. This value is required if report_type is 'periodically'
                and ignored otherwise. Valid values are 2 - 600 inclusive.
        '''
        pdu = RafUsertoProviderPdu()

        if self._auth_level == 'all':
            pdu['rafScheduleStatusReportInvocation']['invokerCredentials']['used'] = self.make_credentials()
        else:
            pdu['rafScheduleStatusReportInvocation']['invokerCredentials']['unused'] = None

        pdu['rafScheduleStatusReportInvocation']['invokeId'] = self.invoke_id

        if report_type == 'immediately':
            pdu['rafScheduleStatusReportInvocation']['reportType'][report_type] = None
        elif report_type == 'periodically':
            pdu['rafScheduleStatusReportInvocation']['reportType'][report_type] = cycle
        elif report_type == 'stop':
            pdu['rafScheduleStatusReportInvocation']['reportType'][report_type] = None
        else:
            raise ValueError('Unknown report type: {}'.format(report_type))

        ait.core.log.info('Scheduling Status Report')
        self.send(self.encode_pdu(pdu))

    def peer_abort(self, reason=127):
        ''' Send a peer abort notification to the RAF interface

        Arguments:
            reason (optional integer):
                An integer representing the reason for the peer abort. Valid
                values are defined in
                :class:`ait.dsn.sle.pdu.common.PeerAbortDiagnostic`
        '''
        pdu = RafUsertoProviderPdu()
        pdu['rafPeerAbortInvocation'] = reason

        ait.core.log.info('Sending Peer Abort')
        self.send(self.encode_pdu(pdu))
        self._state = 'unbound'

    def decode(self, message):
        ''' Decode an ASN.1 encoded RAF PDU

        Arguments:
            message (bytearray):
                The ASN.1 encoded RAF PDU to decode

        Returns:
            The decoded RAF PDU as an instance of the
            :class:`ait.dsn.sle.pdu.raf.RafProvidertoUserPdu` class.
        '''
        return super(self.__class__, self).decode(message, RafProvidertoUserPdu())

    def _bind_return_handler(self, pdu):
        ''''''
        result = pdu['rafBindReturn']['result']
        responder_identifier = pdu['rafBindReturn']['responderIdentifier']

        # Check that responder_id in the response matches what we know
        if responder_identifier != self._responder_id:
            # Invoke PEER-ABORT with unexpected responder id
            self.peer_abort(1)
            self._state = 'unbound'
            return

        if 'positive' in result:
            if self._auth_level in ['bind', 'all']:
                responder_performer_credentials = pdu['rafBindReturn']['performerCredentials']['used']
                if not self._check_return_credentials(responder_performer_credentials, self._responder_id, self._peer_password):
                    # Authentication failed. Ignore processing the return
                    ait.core.log.info('Bind unsuccessful. Authentication failed.')
                    return

            if self._state == 'ready' or self._state == 'active':
                # Peer abort with protocol error (3)
                ait.core.log.info('Bind unsuccessful. State already in READY or ACTIVE.')
                self.peer_abort(3)

            ait.core.log.info('Bind successful')
            self._state = 'ready'
        else:
            ait.core.log.info('Bind unsuccessful: {}'.format(result['negative']))
            self._state = 'unbound'

    def _unbind_return_handler(self, pdu):
        ''''''
        result = pdu['rafUnbindReturn']['result']
        if 'positive' in result:
            ait.core.log.info('Unbind successful')
            self._state = 'unbound'
        else:
            ait.core.log.error('Unbind failed. Treating connection as unbound')
            self._state = 'unbound'

    def _start_return_handler(self, pdu):
        ''''''
        result = pdu['rafStartReturn']['result']
        if 'positiveResult' in result:
            ait.core.log.info('Start successful')
            self._state = 'active'
        else:
            result = result['negativeResult']
            if 'common' in result:
                diag = result['common']
            else:
                diag = result['specific']
            ait.core.log.info('Start unsuccessful: {}'.format(diag))
            self._state = 'ready'

    def _stop_return_handler(self, pdu):
        ''''''
        result = pdu['rafStopReturn']['result']
        if 'positiveResult' in result:
            ait.core.log.info('Stop successful')
            self._state = 'ready'
        else:
            ait.core.log.info('Stop unsuccessful: {}'.format(result['negativeResult']))
            self._state = 'active'

    def _data_transfer_handler(self, pdu):
        ''''''
        for data in pdu['rafTransferBuffer']:
            self._handle_pdu(data)

    def _transfer_data_invoc_handler(self, pdu):
        ''''''
        frame = pdu.getComponent()
        if 'data' in frame and frame['data'].isValue:
            tm_data = frame['data'].asOctets()
        else:
            err = (
                'RafTransferBuffer received but data cannot be located. '
                'Skipping further processing of this PDU ...'
            )
            ait.core.log.info(err)
            return
        
        tm_frame_class = getattr(frames, self._downlink_frame_type)
        tmf = tm_frame_class(tm_data)

        # Add any frame-based logic/decisions here
        if tmf.is_idle_frame:
            ait.core.log.debug('Dropping {} marked as an idle frame'.format(tm_frame_class))
            return

        ait.core.log.debug('Sending {} with {} bytes to frame port'.format(tm_frame_class, len(tm_data)))
        self._telem_sock.sendto(tm_data, ('localhost', self.frame_output_port))

    def _sync_notify_handler(self, pdu):
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

        ait.core.log.info(report)

    def _schedule_status_report_return_handler(self, pdu):
        ''''''
        pdu = pdu['rafScheduleStatusReportReturn']
        if pdu['result'].getName() == 'positiveResult':
            ait.core.log.info('Status Report Scheduled Successfully')
        else:
            diag = pdu['result'].getComponent()

            if diag.getName() == 'common':
                diag_options = ['duplicateInvokeId', 'otherReason']
            else:
                diag_options = ['notSupportedInThisDeliveryMode', 'alreadyStopped', 'invalidReportingCycle']

            reason = diag_options[int(diag.getComponent())]
            ait.core.log.warning('Status Report Scheduling Failed. Reason: {}'.format(reason))

    def _status_report_invoc_handler(self, pdu):
        ''''''
        pdu = pdu['rafStatusReportInvocation']
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
        report += 'Carrier Lock Status: {}\n'.format(carrier_lock_status[pdu['carrierLockStatus']])

        production_status = ['Running', 'Interrupted', 'Halted']
        report += 'Production Status: {}'.format(production_status[pdu['productionStatus']])

        ait.core.log.warning(report)

    def _get_param_return_handler(self, pdu):
        ''''''
        pdu = pdu['rafGetParameterReturn']
        #TODO: Implement

    def _peer_abort_handler(self, pdu):
        ''''''
        pdu = pdu['rafPeerAbortInvocation']
        opts = [
            'accessDenied', 'unexpectedResponderId', 'operationalRequirement',
            'protocolError', 'communicationsFailure', 'encodingError', 'returnTimeout',
            'endOfServiceProvisionPeriod', 'unsolicitedInvokeId', 'otherReason'
        ]
        ait.core.log.error('Peer Abort Received. {}'.format(opts[pdu]))
        self._state = 'unbound'
        self.disconnect()
