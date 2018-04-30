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

The bliss.sle.raf module provides SLE Return All Frames (RAF)
interface classes, methods, and attributes.

Classes:
    RAF: An extension of the generic bliss.sle.common.SLE class which
        implements the RAF standard.
'''
import struct

import bliss.core.log

import common
import frames
from bliss.sle.pdu.raf import *
from bliss.sle.pdu import raf


class RAF(common.SLE):
    ''' SLE Return All Frames (RAF) interface class
    
    The RAF class extends the bliss.sle.common.SLE base interface class
    and implements the RAF specification.

    The RAF class can respond to a number of returns from the SLE interface.
    The following are a list of the events to which handlers can be bound along
    with an explanation for when they would be encountered. The interface
    provides default handlers for each of these events which generally log
    information received via :mod:`bliss.core.log`.

    Handlers will receive an instance of the received and decoded PDU. If you
    would like to see the specification for each possible you can view the
    class for each option in :class:`bliss.sle.pdu.raf.RafProvidertoUserPdu`

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
        super(self.__class__, self).__init__(*args, **kwargs)

        self._service_type = 'rtnAllFrames'
        self._version = kwargs.get('version', 5)

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
                :class:`bliss.sle.pdu.binds.UnbindReason`
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
                :class:`bliss.sle.pdu.raf.RequestedFrameQuality`
        
        '''
        start_invoc = RafUsertoProviderPdu()

        if self._auth_level == 'all':
            start_invoc['rafStartInvocation']['invokerCredentials']['used'] = self.make_credentials()
        else:
            start_invoc['rafStartInvocation']['invokerCredentials']['unused'] = None

        start_invoc['rafStartInvocation']['invokeId'] = self.invoke_id
        start_time = struct.pack('!HIH', (start_time - common.CCSDS_EPOCH).days, 0, 0)
        stop_time = struct.pack('!HIH', (end_time - common.CCSDS_EPOCH).days, 0, 0)

        start_invoc['rafStartInvocation']['startTime']['known']['ccsdsFormat'] = start_time
        start_invoc['rafStartInvocation']['stopTime']['known']['ccsdsFormat'] = stop_time
        start_invoc['rafStartInvocation']['requestedFrameQuality'] = frame_quality

        bliss.core.log.info('Sending data start invocation ...')
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

        bliss.core.log.info('Scheduling Status Report')
        self.send(self.encode_pdu(pdu))

    def decode(self, message):
        ''' Decode an ASN.1 encoded RAF PDU

        Arguments:
            message (bytearray):
                The ASN.1 encoded RAF PDU to decode

        Returns:
            The decoded RAF PDU as an instance of the
            :class:`bliss.sle.pdu.raf.RafProvidertoUserPdu` class.
        '''
        return super(self.__class__, self).decode(message, RafProvidertoUserPdu())

    def peer_abort(self, reason=127):
        ''' Send a peer abort notification to the RAF interface

        Arguments:
            reason (optional integer):
                An integer representing the reason for the peer abort. Valid
                values are defined in
                :class:`bliss.sle.pdu.common.PeerAbortDiagnostic`
        '''
        pdu = RafUsertoProviderPdu()
        pdu['rafPeerAbortInvocation'] = reason
        super(self.__class__, self).peer_abort(pdu)

    def _bind_return_handler(self, pdu):
        ''''''
        super(self.__class__, self)._bind_return_handler(pdu, provider_key='rafBindReturn')

    def _unbind_return_handler(self, pdu):
        ''''''
        super(self.__class__, self)._unbind_return_handler(pdu, provider_key='rafUnbindReturn')

    def _start_return_handler(self, pdu):
        ''''''
        super(self.__class__, self)._start_return_handler(pdu, provider_key='rafStartReturn')

    def _stop_return_handler(self, pdu):
        ''''''
        super(self.__class__, self)._stop_return_handler(pdu, provider_key='rafStopReturn')

    def _schedule_status_report_return_handler(self, pdu):
        ''''''
        super(self.__class__, self)._schedule_status_report_return_handler(pdu,
                                                                           provider_key='rafScheduleStatusReportReturn')

    def _status_report_invoc_handler(self, pdu):
        ''''''
        super(self.__class__, self)._status_report_invoc_handler(pdu, provider_key='rafStatusReportInvocation')

    def _peer_abort_handler(self, pdu):
        ''''''
        super(self.__class__, self)._peer_abort_handler(pdu, provider_key='rafPeerAbortInvocation')

    def _data_transfer_handler(self, pdu):
        ''''''
        self._handle_pdu(pdu['rafTransferBuffer'][0])

    def _get_param_return_handler(self, pdu):
        ''''''
        super(self.__class__, self)._get_param_return_handler(pdu, provider_key='rafGetParameterReturn')

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
            bliss.core.log.info(err)
            return

        tmf = frames.TMTransFrame(tm_data)
        bliss.core.log.info('Sending {} bytes to telemetry port'.format(len(tmf._data[0])))
        self._telem_sock.sendto(tmf._data[0], ('localhost', 3076))

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

        bliss.core.log.info(report)
