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

''' CLTU Interface Module

The ait.dsn.sle.cltu module provides SLE Forward Communications Link Transmission
Unit (CLTU) interface classes, methods, and attributes.

Classes:
    CLTU: An extension of the generic :class:`ait.dsn.sle.common.SLE` which
        implements the Forward CLTU standard.
'''
import binascii
import struct

import ait.core.log
import common

if ait.config.get('dsn.sle.version', None) == 4:
    from ait.dsn.sle.pdu.cltu.cltuv4 import *
else:
    from ait.dsn.sle.pdu.cltu.cltuv5 import *


class CLTU(common.SLE):
    ''' SLE Forward Communications Link Transmission Unit (CLTU) interface class

    The CLTU class extends the ait.dsn.sle.common.SLE base interface class
    and implements the CLTU specification.

    The CLTU class can respond to a number of returns from the SLE interface.
    The following are a list of the events to which handlers can be bound along
    with an explanation for when they would be encountered. The interface
    provides default handlers for each of these events which generally log
    information received via :mod:`ait.core.log`.

    Handlers will receive an instance of the received and decoded PDU. If you
    would like to see the specification for each possible you can view the
    class for each option in :class:`ait.dsn.sle.pdu.cltu.CltuProviderToUserPdu`

    CltuBindReturn:
        Response back from the provider after a bind request has been
        sent to the interface.

    CltuUnbindReturn
        Response back from the provider after a unbind request has been
        sent to the interface.
        
    CltuStartReturn
        Response back from the provider after a start data request has been
        sent to the interface.

    CltuStopReturn
        Response back from the provider after a stop data request has been
        sent to the interface.

    CltuScheduleStatusReportReturn
        Response back from the provider after a schedule status report request
        has been sent to the interface.

    CltuStatusReportInvocation
        Response from the provider containing a status report.

    CltuGetParameterReturn
        Response back from the provider after a Get Parameter request has been
        sent to the interface.

    CltuPeerAbortInvocation
        Received from the provider to abort the connection.

    CltuTransferDataReturn
        Response from the provider acknowledging a data upload request. This
        will contain information on the result of the request, the CLTU Id
        information, and how much buffer space the provider has remaining for
        additional transfers.

    CltuAsyncNotifyInvocation
        Received from the provider to inform the user of an event affecting
        the production of the Forward CLTU service.

    CltuThrowEventReturn
        Received from the provider after the user invokes a Throw-Event
        operation. The return will only show whether the invocation itself has
        been accepted or rejected, but not if the actions associated with the
        event have been performed successfully. The provider will invoke a
        CLTU-ASYNC-NOTIFY operation to inform the user on the outcome of the
        actions triggered by the event. 
    '''
    # TODO: Add error checking for actions based on current state
    _cltu_id = 0
    event_invoc_id = 0

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)

        self._service_type = 'fwdCltu'
        self._version = kwargs.get('version', 5)

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

    def bind(self, inst_id=None):
        ''' Bind to a CLTU interface

        Arguments:
            inst_id:
                The instance id for the CLTU interface to bind.
        '''
        pdu = CltuUserToProviderPdu()['cltuBindInvocation']
        super(self.__class__, self).bind(pdu, inst_id=inst_id)

    def unbind(self, reason=0):
        ''' Unbind from the CLTU interface
        
        Arguments:
            reason:
                An optional integer indicating the reason for the unbind. The
                valid integer values are defined in
                :class:`ait.dsn.sle.pdu.binds.UnbindReason`
        '''
        pdu = CltuUserToProviderPdu()['cltuUnbindInvocation']
        super(self.__class__, self).unbind(pdu, reason=reason)

    def start(self):
        ''' Send a data receive start request to the CLTU interface

        The user shall invoke the CLTU-START operation to request that
        the Forward CLTU service provider prepare to receive
        CLTU-TRANSFER-DATA invocations
        '''
        start_invoc = CltuUserToProviderPdu()

        if self._auth_level == 'all':
            start_invoc['cltuStartInvocation']['invokerCredentials']['used'] = self.make_credentials()
        else:
            start_invoc['cltuStartInvocation']['invokerCredentials']['unused'] = None

        start_invoc['cltuStartInvocation']['invokeId'] = self.invoke_id
        start_invoc['cltuStartInvocation']['firstCltuIdentification'] = self._cltu_id

        ait.core.log.info('Sending data start invocation ...')
        self.send(self.encode_pdu(start_invoc))

    def stop(self):
        ''' Request the provider stop radiation of received CLTUs '''
        pdu = CltuUserToProviderPdu()['cltuStopInvocation']
        super(self.__class__, self).stop(pdu)

    def upload_cltu(self, tc_data, earliest_time=None, latest_time=None, delay=0, notify=False):
        ''' Upload a CLTU to the service
        
        Arguments:
            tc_data:
                The data to transfer in the CLTU.

            earliest_time (optional :class:`datetime.datetime`):
                Specify the earliest time that the provider shall start
                processing this CLTU.

            latest_time (optional :class:`datetime.datetime`):
                 Specify the latest time at which the provider shall start
                 processing this CLTU.

            delay=0:
                The minimum radiation delay, in microseconds, between the CLTU
                transferred in this operation and the next CLTU.

            notify (optional boolean):
                Specify whether the provider shall invoke the CLTU-ASYNCNOTIFY
                operation upon completion of the radiation of the CLTU.
        '''
        pdu = CltuUserToProviderPdu()

        if self._auth_level == 'all':
            pdu['cltuTransferDataInvocation']['invokerCredentials']['used'] = self.make_credentials()
        else:
            pdu['cltuTransferDataInvocation']['invokerCredentials']['unused'] = None

        pdu['cltuTransferDataInvocation']['invokeId'] = self.invoke_id
        pdu['cltuTransferDataInvocation']['cltuIdentification'] = self._cltu_id
        self._cltu_id += 1

        if earliest_time:
            t = struct.pack('!HIH', (earliest_time - common.CCSDS_EPOCH).days, 0, 0)
            pdu['cltuTransferDataInvocation']['earliestTransmissionTime']['known']['ccsdsFormat'] = t
        else:
            pdu['cltuTransferDataInvocation']['earliestTransmissionTime']['undefined'] = None

        if latest_time:
            t = struct.pack('!HIH', (latest_time - common.CCSDS_EPOCH).days, 0, 0)
            pdu['cltuTransferDataInvocation']['latestTransmissionTime']['known']['ccsdsFormat'] = t
        else:
            pdu['cltuTransferDataInvocation']['latestTransmissionTime']['undefined'] = None

        pdu['cltuTransferDataInvocation']['delayTime'] = delay
        pdu['cltuTransferDataInvocation']['cltuData'] = tc_data

        if notify:
            pdu['cltuTransferDataInvocation']['slduRadiationNotification'] = 0
        else:
            pdu['cltuTransferDataInvocation']['slduRadiationNotification'] = 1

        ait.core.log.info('Sending TC Data ...')
        self.send(self.encode_pdu(pdu))

    def schedule_status_report(self, report_type='immediately', cycle=None):
        ''' Send a status report schedule request to the CLTU interface
        
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
        pdu = CltuUserToProviderPdu()

        if self._auth_level == 'all':
            pdu['cltuScheduleStatusReportInvocation']['invokerCredentials']['used'] = self.make_credentials()
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

        ait.core.log.info('Scheduling Status Report')
        self.send(self.encode_pdu(pdu))

    def get_parameter(self):
        ''''''
        #TODO: Implement
        pass

    def throw_event(self, event_id, event_qualifier):
        ''' Forward an event to SLE Complex Management

        The user may throw an event to SLE Complement Management that requires
        management action. An example of this would be requesting a change to
        the uplink bit rate.

        Arguments:
            event_id (integer):
                Specify the event to be forwarded to SLE Complex Management by
                the service provider.

            event_qualifier (bytearray):
                May be used to provide additional data constraining the
                actions to be performed by Complex Management in response to
                the event specified in event-identifier and shall be forwarded
                together with the event. Data may be of length 1-1024 bytes.

        '''
        pdu = CltuUserToProviderPdu()

        if self._auth_level == 'all':
            pdu['cltuThrowEventInvocation']['invokerCredentials']['used'] = self.make_credentials()
        else:
            pdu['cltuThrowEventInvocation']['invokerCredentials']['unused'] = None

        pdu['cltuThrowEventInvocation']['invokeId'] = self.invoke_id
        pdu['cltuThrowEventInvocation']['eventInvocationIdentification'] = self.event_invoc_id
        pdu['cltuThrowEventInvocation']['eventIdentifier'] = event_id
        pdu['cltuThrowEventInvocation']['eventQualifier'] = event_qualifier

        ait.core.log.info('Sending Throw Event Invocation')
        self.send(self.encode_pdu(pdu))

    def peer_abort(self, reason=127):
        ''' Send a peer abort notification to the CLTU interface

        Arguments:
            reason (optional integer):
                An integer representing the reason for the peer abort. Valid
                values are defined in
                :class:`ait.dsn.sle.pdu.common.PeerAbortDiagnostic`
        '''
        pdu = CltuUserToProviderPdu()
        pdu['cltuPeerAbortInvocation'] = reason

        ait.core.log.info('Sending Peer Abort')
        self.send(self.encode_pdu(pdu))
        self._state = 'unbound'

    def decode(self, message):
        ''' Decode an ASN.1 encoded CLTU PDU

        Arguments:
            message (bytearray):
                The ASN.1 encoded CLTU PDU to decode

        Returns:
            The decoded CLTU PDU as an instance of the
            :class:`ait.dsn.sle.pdu.cltu.CltuProvidertoUserPdu` class.
        '''
        return super(self.__class__, self).decode(message, CltuProviderToUserPdu())

    def _bind_return_handler(self, pdu):
        ''''''
        result = pdu['cltuBindReturn']['result']
        responder_identifier = pdu['cltuBindReturn']['responderIdentifier']

        # Check that responder_id in the response matches what we know
        if responder_identifier != self._responder_id:
            # Invoke PEER-ABORT with unexpected responder id
            self.peer_abort(1)
            self._state = 'unbound'
            return

        if 'positive' in result:
            if self._auth_level in ['bind', 'all']:
                responder_performer_credentials = pdu['cltuBindReturn']['performerCredentials']['used']
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
        result = pdu['cltuUnbindReturn']['result']
        if 'positive' in result:
            ait.core.log.info('Unbind successful')
            self._state = 'unbound'
        else:
            ait.core.log.error('Unbind failed. Treating connection as unbound')
            self._state = 'unbound'

    def _trans_data_return_handler(self, pdu):
        ''''''
        result = pdu['cltuTransferDataReturn']['result']
        cltu_id = pdu['cltuTransferDataReturn']['cltuIdentification']
        buffer_avail = pdu['cltuTransferDataReturn']['cltuBufferAvailable']

        if 'positiveResult' in result:
            ait.core.log.info('CLTU #{} trans. passed. Buffer avail.: {}'.format(
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
            ait.core.log.info('CLTU #{} trans. failed. Diag: {}. Buffer avail: {}'.format(
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
            ait.core.log.info('Start Successful')
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
        result = pdu['cltuStopReturn']['result']
        if 'positiveResult' in result:
            ait.core.log.info('Stop successful')
            self._state = 'ready'
        else:
            ait.core.log.info('Stop unsuccessful: {}'.format(result['negativeResult']))
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

        ait.core.log.info(msg)

    def _schedule_status_report_return_handler(self, pdu):
        ''''''
        pdu = pdu['cltuScheduleStatusReportReturn']

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

        ait.core.log.warning(report)

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
        ait.core.log.error('Peer Abort Received. {}'.format(opts[pdu]))
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
        ait.core.log.info(msg)
