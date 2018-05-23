# -*- coding: utf-8 -*-

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

''' RCF Interface Module

The ait.dsn.sle.raf module provides SLE Return Channel Frames (RCF) class,
methods, and attributes.

Classes:
    RCF: An extension of the generic ait.dsn.sle.common.SLE class which
        implements the RCF standard.
'''
import struct

import ait.core.log

import common
import frames
from ait.dsn.sle.pdu.rcf import *
from ait.dsn.sle.pdu import rcf


class RCF(common.SLE):
    ''' SLE Return Channel Frames (RCF) interface class

    The RCF class extends the ait.dsn.sle.common.SLE base insterface class
    and implements the RCF specification.

    The RCF class can respond to a number of returns from the SLE interface.
    The following are a list of the events to which handlers can be bound along
    with an explanation for when they would be encountered. The interface
    provides default handlers for each of these events which generally log
    information received via :mod:`ait.core.log`.

    Handlers will receive an instance of the received and decoded PDU. If you
    would like to see the specification for each possible you can view the
    class for each option in :class:`ait.dsn.sle.pdu.rcf.RcfProvidertoUserPdu`

    RcfBindReturn:
        Response back from the provider after a bind request has been
        sent to the interface.

    RcfUnbindReturn
        Response back from the provider after a unbind request has been
        sent to the interface.

    RcfStartReturn
        Response back from the provider after a start data request has been
        sent to the interface.

    RcfStopReturn
        Response back from the provider after a stop data request has been
        sent to the interface.

    RcfTransferBuffer
        Response from the provider container a data transfer or notification.

    AnnotatedFrame
        A potential component of the PDU received by the RcfTransferBuffer
        handler. If the provider is sending data to the user this is the handler
        that will fire to process the PDU.

    SyncNotification
        A potential component of the PDU received by the RcfTransferBuffer
        handler. If the provider is sending a notification to the user this
        is the handler that will fire to process the PDU.

    RcfScheduleStatusReportReturn
        Response back from the provider after a schedule status report request
        has been sent to the interface.

    RcfStatusReportInvocation
        Response from the provider containing a status report.

    RcfGetParameterReturn
        Response back from the provider after a Get Parameter request has been
        sent to the interface.

    RcfPeerAbortInvocation
        Received from the provider to abort the connection.
    '''
    # TODO: Add error checking for actions based on current state

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self._service_type = 'rtnChFrames'
        self._version = kwargs.get('version', 5)
        self._scid = kwargs.get('spacecraft_id', None)
        self._tfvn = kwargs.get('trans_frame_ver_num', None)

        self._handlers['RcfBindReturn'].append(self._bind_return_handler)
        self._handlers['RcfUnbindReturn'].append(self._unbind_return_handler)
        self._handlers['RcfStartReturn'].append(self._start_return_handler)
        self._handlers['RcfStopReturn'].append(self._stop_return_handler)
        self._handlers['RcfTransferBuffer'].append(self._data_transfer_handler)
        self._handlers['RcfScheduleStatusReportReturn'].append(self._schedule_status_report_return_handler)
        self._handlers['RcfStatusReportInvocation'].append(self._status_report_invoc_handler)
        self._handlers['RcfGetParameterReturn'].append(self._get_param_return_handler)
        self._handlers['AnnotatedFrame'].append(self._transfer_data_invoc_handler)
        self._handlers['SyncNotification'].append(self._sync_notify_handler)
        self._handlers['RcfPeerAbortInvocation'].append(self._peer_abort_handler)

    def bind(self, inst_id=None):
        ''' Bind to a RCF interface

        Arguments:
            inst_id:
                The instance id for the RCF interface to bind.
        '''
        pdu = RcfUsertoProviderPdu()['rcfBindInvocation']
        super(self.__class__, self).bind(pdu, inst_id=inst_id)

    def unbind(self, reason=0):
        ''' Unbind from the RCF interface

        Arguments:
            reason:
                An optional integer indicating the reason for the unbind. The
                valid integer values are defined in
                :class:`ait.dsn.sle.pdu.binds.UnbindReason`
        '''
        pdu = RcfUsertoProviderPdu()['rcfUnbindInvocation']
        super(self.__class__, self).unbind(pdu, reason=reason)

    def get_parameter(self):
        ''''''
        #TODO: Implement get parameter
        pass

    def start(self, start_time, end_time, spacecraft_id=None,
              trans_frame_ver_num=None, master_channel=False,
              virtual_channel=None):
        ''' Send data start request to the RAF interface

        Arguments:
            start_time (:class:`datetime.datetime`):
                The start time (In ERT) for the data to be returned from the
                interface.

            end_time (:class:`datetime.datetime`):
                The end time (In ERT) for the data to be returned from the
                interface.

            spacecraft_id (integer):
                The spacecraft id to use when constructing the GVCId. This
                parameter is optional assuming that the parameter was supplied
                to __init__ on object creation.

            trans_frame_ver_num (integer):
                The transfer frame version number (TFVN) to use when
                constructing the GVCId. This parameter is optional assuming
                that the parameter was supplied to __init__ on object creation.
                At the time of issuance of the RCF Recommended Standard, the
                only valid TFVN were ‘0’ (version 1) and ‘1’ (version 2).

            master_channel (boolean):
                A flag indicating whether the master channel or virtual
                channel(s) should be used. If master_channel is True then
                virtual_channel should be None. Otherwise, master_channel
                should be False and virtual_channel should be not None.

            virtual_channel (integer):
                An integer representing which virtual_channel will be used
                with this connection. Value constraints are specified in the
                implementation class :class:`ait.dsn.sle.pdu.rcf.VcId`. If
                virtual_channel is not None, then master_channel should be
                False. Otherwise, master_channel should be True and
                virtual_channel should be None.
        '''
        if not master_channel and not virtual_channel:
            err = (
                'Transfer start invocation requires a master channel or '
                'virtual channel from which to receive frames.'
            )
            raise AttributeError(err)

        spacecraft_id = spacecraft_id if spacecraft_id is not None else self._scid
        if spacecraft_id is None:
            err = (
                'Transfer start invocation requires a spacecraft id '
                'to specify the VCID from which to receive frames.'
            )
            raise AttributeError(err)

        trans_frame_ver_num = trans_frame_ver_num if trans_frame_ver_num is not None else self._tfvn
        if trans_frame_ver_num is None:
            err = (
                'Transfer start invocation requires a transfer frame '
                'version number to specify the VCID from which to '
                'receive frames.'
            )
            raise AttributeError(err)

        start_invoc = RcfUsertoProviderPdu()

        if self._auth_level == 'all':
            start_invoc['rcfStartInvocation']['invokerCredentials']['used'] = self.make_credentials()
        else:
            start_invoc['rcfStartInvocation']['invokerCredentials']['unused'] = None

        start_invoc['rcfStartInvocation']['invokeId'] = self.invoke_id
        start_time = struct.pack('!HIH', (start_time - common.CCSDS_EPOCH).days, 0, 0)
        stop_time = struct.pack('!HIH', (end_time - common.CCSDS_EPOCH).days, 0, 0)

        start_invoc['rcfStartInvocation']['startTime']['known']['ccsdsFormat'] = start_time
        start_invoc['rcfStartInvocation']['stopTime']['known']['ccsdsFormat'] = stop_time

        req_gvcid = GvcId()
        req_gvcid['spacecraftId'] = spacecraft_id
        req_gvcid['versionNumber'] = trans_frame_ver_num

        if master_channel:
            req_gvcid['vcId']['masterChannel'] = None
        else:
            req_gvcid['vcId']['virtualChannel'] = virtual_channel

        start_invoc['rcfStartInvocation']['requestedGvcId'] = req_gvcid

        ait.core.log.info('Sending data start invocation ...')
        self.send(self.encode_pdu(start_invoc))

    def stop(self):
        ''' Send data stop request to the RCF interface '''
        pdu = RcfUsertoProviderPdu()['rcfStopInvocation']
        super(self.__class__, self).stop(pdu)

    def schedule_status_report(self, report_type='immediately', cycle=None):
        ''' Send a status report schedule request to the RCF interface

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
        pdu = RcfUsertoProviderPdu()

        if self._auth_level == 'all':
            pdu['rcfScheduleStatusReportInvocation']['invokerCredentials']['used'] = self.make_credentials()
        else:
            pdu['rcfScheduleStatusReportInvocation']['invokerCredentials']['unused'] = None

        pdu['rcfScheduleStatusReportInvocation']['invokeId'] = self.invoke_id

        if report_type == 'immediately':
            pdu['rcfScheduleStatusReportInvocation']['reportType'][report_type] = None
        elif report_type == 'periodically':
            pdu['rcfScheduleStatusReportInvocation']['reportType'][report_type] = cycle
        elif report_type == 'stop':
            pdu['rcfScheduleStatusReportInvocation']['reportType'][report_type] = None
        else:
            raise ValueError('Unknown report type: {}'.format(report_type))

        ait.core.log.info('Scheduling Status Report')
        self.send(self.encode_pdu(pdu))

    def peer_abort(self, reason=127):
        ''' Send a peer abort notification to the RCF interface

        Arguments:
            reason (optional integer):
                An integer representing the reason for the peer abort. Valid
                values are defined in
                :class:`ait.dsn.sle.pdu.common.PeerAbortDiagnostic`
        '''
        pdu = RcfUsertoProviderPdu()
        pdu['rcfPeerAbortInvocation'] = reason

        ait.core.log.info('Sending Peer Abort')
        self.send(self.encode_pdu(pdu))
        self._state = 'unbound'

    def decode(self, message):
        ''' Decode an ASN.1 encoded RCF PDU

        Arguments:
            message (bytearray):
                The ASN.1 encoded RCF PDU to decode

        Returns:
            The decoded RCF PDU as an instance of the
            :class:`ait.dsn.sle.pdu.rcf.RcfProvidertoUserPdu` class.
        '''
        return super(self.__class__, self).decode(message, RcfProvidertoUserPdu())

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
            ait.core.log.error(err.format(pdu_key))

    def _bind_return_handler(self, pdu):
        ''''''
        result = pdu['rcfBindReturn']['result']
        responder_identifier = pdu['rcfBindReturn']['responderIdentifier']

        # Check that responder_id in the response matches what we know
        if responder_identifier != self._responder_id:
            # Invoke PEER-ABORT with unexpected responder id
            self.peer_abort(1)
            self._state = 'unbound'
            return

        if 'positive' in result:
            if self._auth_level in ['bind', 'all']:
                responder_performer_credentials = pdu['rcfBindReturn']['performerCredentials']['used']
                if not self._check_return_credentials(responder_performer_credentials, self._responder_id,
                                                  self._peer_password):
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
        result = pdu['rcfUnbindReturn']['result']
        if 'positive' in result:
            ait.core.log.info('Unbind successful')
            self._state = 'unbound'
        else:
            ait.core.log.error('Unbind failed. Treating connection as unbound')
            self._state = 'unbound'

    def _start_return_handler(self, pdu):
        ''''''
        result = pdu['rcfStartReturn']['result']
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
        result = pdu['rcfStopReturn']['result']
        if 'positiveResult' in result:
            ait.core.log.info('Stop successful')
            self._state = 'ready'
        else:
            ait.core.log.info('Stop unsuccessful: {}'.format(result['negativeResult']))
            self._state = 'active'

    def _data_transfer_handler(self, pdu):
        ''''''
        self._handle_pdu(pdu['rcfTransferBuffer'][0])

    def _transfer_data_invoc_handler(self, pdu):
        ''''''
        frame = pdu.getComponent()
        if 'data' in frame and frame['data'].isValue:
            tm_data = frame['data'].asOctets()

        else:
            err = (
                'RcfTransferBuffer received but data cannot be located. '
                'Skipping further processing of this PDU ...'
            )
            ait.core.log.info(err)
            return

        tmf = frames.TMTransFrame(tm_data)
        ait.core.log.info('Sending {} bytes to telemetry port'.format(len(tmf._data[0])))
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

        ait.core.log.info(report)

    def _schedule_status_report_return_handler(self, pdu):
        ''''''
        pdu = pdu['rcfScheduleStatusReportReturn']
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
        pdu = pdu['rcfStatusReportInvocation']
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

        ait.core.log.warning(report)

    def _get_param_return_handler(self, pdu):
        ''''''
        pdu = pdu['rcfGetParameterReturn']
        #TODO: Implement

    def _peer_abort_handler(self, pdu):
        ''''''
        pdu = pdu['rcfPeerAbortInvocation']
        opts = [
            'accessDenied', 'unexpectedResponderId', 'operationalRequirement',
            'protocolError', 'communicationsFailure', 'encodingError', 'returnTimeout',
            'endOfServiceProvisionPeriod', 'unsolicitedInvokeId', 'otherReason'
        ]
        ait.core.log.error('Peer Abort Received. {}'.format(opts[pdu]))
        self._state = 'unbound'
        self.disconnect()
