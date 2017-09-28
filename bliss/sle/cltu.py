import binascii
import struct

import bliss.core.log

import common
import frames
from bliss.sle.pdu.cltu import *
from bliss.sle.pdu import cltu

class CLTU(common.SLE):
    ''''''
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
        pdu = CltuUserToProviderPdu()['cltuBindInvocation']
        super(self.__class__, self).bind(pdu, inst_id=inst_id)

    def unbind(self, reason=0):
        ''''''
        pdu = CltuUserToProviderPdu()['cltuUnbindInvocation']
        super(self.__class__, self).unbind(pdu, reason=reason)

    def start(self):
        start_invoc = CltuUserToProviderPdu()

        if self._credentials:
            pass
        else:
            start_invoc['cltuStartInvocation']['invokerCredentials']['unused'] = None

        start_invoc['cltuStartInvocation']['invokeId'] = self.invoke_id
        start_invoc['cltuStartInvocation']['firstCltuIdentification'] = self._cltu_id

        bliss.core.log.info('Sending data start invocation ...')
        self.send(self.encode_pdu(start_invoc))

    def stop(self):
        pdu = CltuUserToProviderPdu()['cltuStopInvocation']
        super(self.__class__, self).stop(pdu)

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

        bliss.core.log.info('Sending TC Data ...')
        self.send(self.encode_pdu(pdu))

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

        bliss.core.log.info('Scheduling Status Report')
        self.send(self.encode_pdu(pdu))

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

        bliss.core.log.info('Sending Throw Event Invocation')
        self.send(self.encode_pdu(pdu))

    def peer_abort(self, reason=127):
        ''''''
        pdu = CltuUserToProviderPdu()
        pdu['cltuPeerAbortInvocation'] = reason

        bliss.core.log.info('Sending Peer Abort')
        self.send(self.encode_pdu(pdu))
        self._state = 'unbound'

    def decode(self, message):
        ''''''
        # return decode(message, asn1Spec=CltuProviderToUserPdu())
        return super(self.__class__, self).decode(message, CltuProviderToUserPdu())

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
