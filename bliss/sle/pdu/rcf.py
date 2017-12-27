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

from binds import *
from common import *

from pyasn1.type import univ, char, namedtype, namedval, tag, constraint, useful


class DiagnosticRcfGet(univ.Choice):
    pass


DiagnosticRcfGet.componentType = namedtype.NamedTypes(
    namedtype.NamedType('common', Diagnostics().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('specific', univ.Integer(namedValues=namedval.NamedValues(('unknownParameter', 0))).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)


class DiagnosticRcfStart(univ.Choice):
    pass


DiagnosticRcfStart.componentType = namedtype.NamedTypes(
    namedtype.NamedType('common', Diagnostics().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('specific', univ.Integer(namedValues=namedval.NamedValues(('outOfService', 0), ('unableToComply', 1), ('invalidStartTime', 2), ('invalidStopTime', 3), ('missingTimeValue', 4))).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)


class VcId(univ.Integer):
    subtypeSpec = constraint.ValueRangeConstraint(0, 63)


class GvcId(univ.Sequence):
    pass


GvcId.componentType = namedtype.NamedTypes(
    namedtype.NamedType('spacecraftId', univ.Integer().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 1023))),
    namedtype.NamedType('versionNumber', univ.Integer().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 3))),
    namedtype.NamedType('vcId', univ.Choice(componentType=namedtype.NamedTypes(
        namedtype.NamedType('masterChannel', univ.Null().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.NamedType('virtualChannel', VcId().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    )))
)


class MasterChannelComposition(univ.Sequence):
    pass


MasterChannelComposition.componentType = namedtype.NamedTypes(
    namedtype.NamedType('spacecraftId', univ.Integer().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 1023))),
    namedtype.NamedType('versionNumber', univ.Integer().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 3))),
    namedtype.NamedType('mcOrVcList', univ.Choice(componentType=namedtype.NamedTypes(
        namedtype.NamedType('masterChannel', univ.Null().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.NamedType('vcList', univ.SetOf(componentType=VcId().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))))
    )))
)


class GvcIdSet(univ.SetOf):
    componentType = MasterChannelComposition()


class RequestedGvcId(univ.Choice):
    pass


RequestedGvcId.componentType = namedtype.NamedTypes(
    namedtype.NamedType('gvcid', GvcId().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('undefined', univ.Null().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
)


class RcfDeliveryMode(DeliveryMode):
    pass


class RcfGetParameter(univ.Choice):
    pass

RcfGetParameter.componentType = namedtype.NamedTypes(
    namedtype.NamedType('parBufferSize', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', IntPosShort())
    )).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),

    namedtype.NamedType('parDeliveryMode', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', RcfDeliveryMode())
    )).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1))),

    namedtype.NamedType('parLatencyLimit', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', univ.Choice(componentType=namedtype.NamedTypes(
            namedtype.NamedType('online', IntPosShort().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
            namedtype.NamedType('offline', univ.Null().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
        )))
    )).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 2))),

    namedtype.NamedType('parMinReportingCycle', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', IntPosShort())
    )).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 7))),

    namedtype.NamedType('parPermittedGvcidSet', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', GvcIdSet())
    )).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 3))),

    namedtype.NamedType('parReportingCycle', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', CurrentReportingCycle())
        
    )).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 4))),

    namedtype.NamedType('parReqGvcId', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', RequestedGvcId())
    )).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 5))),

    namedtype.NamedType('parReqGvcId', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', TimeoutPeriod())
    )).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 6))),
)


class RcfParameterName(univ.Integer):
    pass


RcfParameterName.namedValues = namedval.NamedValues(
    ('bufferSize', 4),
    ('deliveryMode', 6),
    ('latencyLimit', 15),
    ('minReportingCycle', 301),
    ('reportingCycle', 26),
    ('returnTimeoutPeriod', 29),
    ('permittedGvcidSet', 24),
    ('requestedGvcid', 28)
)


class RcfProductionStatus(univ.Integer):
    pass


RcfProductionStatus.namedValues = namedval.NamedValues(
    ('running', 0),
    ('interrupted', 1),
    ('halted', 2)
)


class Notification(univ.Choice):
    pass


Notification.componentType = namedtype.NamedTypes(
    namedtype.NamedType('lossFrameSync', LockStatusReport().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
    namedtype.NamedType('productionStatusChange', RcfProductionStatus().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.NamedType('excessiveDataBacklog', univ.Null().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
    namedtype.NamedType('endOfData', univ.Null().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3)))
)


class RcfGetParameterInvocation(univ.Sequence):
    pass


RcfGetParameterInvocation.componentType = namedtype.NamedTypes(
    namedtype.NamedType('invokerCredentials', Credentials()),
    namedtype.NamedType('invokeId', InvokeId()),
    namedtype.NamedType('rcfParameter', RcfParameterName())
)


class RcfStartInvocation(univ.Sequence):
    pass


RcfStartInvocation.componentType = namedtype.NamedTypes(
    namedtype.NamedType('invokerCredentials', Credentials()),
    namedtype.NamedType('invokeId', InvokeId()),
    namedtype.NamedType('startTime', ConditionalTime()),
    namedtype.NamedType('stopTime', ConditionalTime()),
    namedtype.NamedType('requestedGvcId', GvcId())
)


class RcfGetParameterReturn(univ.Sequence):
    pass

RcfGetParameterReturn.componentType = namedtype.NamedTypes(
    namedtype.NamedType('performerCredentials', Credentials()),
    namedtype.NamedType('invokeId', InvokeId()),
    namedtype.NamedType('result', univ.Choice(componentType=namedtype.NamedTypes(
        namedtype.NamedType('positiveResult', RcfGetParameter().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
        namedtype.NamedType('negativeResult', DiagnosticRcfGet().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1)))
    )))
)


class RcfStatusReportInvocation(univ.Sequence):
    pass


RcfStatusReportInvocation.componentType = namedtype.NamedTypes(
    namedtype.NamedType('invokerCredentials', Credentials()),
    namedtype.NamedType('deliveredFrameNumber', IntUnsignedLong()),
    namedtype.NamedType('frameSyncLockStatus', FrameSyncLockStatus()),
    namedtype.NamedType('symbolSyncLockStatus', SymbolLockStatus()),
    namedtype.NamedType('subcarrierLockStatus', LockStatus()),
    namedtype.NamedType('carrierLockStatus', CarrierLockStatus()),
    namedtype.NamedType('productionStatus', RcfProductionStatus())
)


class RcfSyncNotifyInvocation(univ.Sequence):
    pass


RcfSyncNotifyInvocation.componentType = namedtype.NamedTypes(
    namedtype.NamedType('invokerCredentials', Credentials()),
    namedtype.NamedType('notification', Notification())
)


class RcfStartReturn(univ.Sequence):
    pass


RcfStartReturn.componentType = namedtype.NamedTypes(
    namedtype.NamedType('performerCredentials', Credentials()),
    namedtype.NamedType('invokeId', InvokeId()),
    namedtype.NamedType('result', univ.Choice(componentType=namedtype.NamedTypes(
        namedtype.NamedType('positiveResult', univ.Null().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.NamedType('negativeResult', DiagnosticRcfStart().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1)))
    ))
    )
)


class RcfTransferDataInvocation(univ.Sequence):
    pass


RcfTransferDataInvocation.componentType = namedtype.NamedTypes(
    namedtype.NamedType('invokerCredentials', Credentials()),
    namedtype.NamedType('earthReceiveTime', Time()),
    namedtype.NamedType('antennaId', AntennaId()),
    namedtype.NamedType('dataLinkContinuity', univ.Integer().subtype(subtypeSpec=constraint.ValueRangeConstraint(-1, 16777215))),
    namedtype.NamedType('privateAnnotation', univ.Choice(componentType=namedtype.NamedTypes(
        namedtype.NamedType('null', univ.Null().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.NamedType('notNull', univ.OctetString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, 128)).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
    ))
    ),
    namedtype.NamedType('data', SpaceLinkDataUnit())
)


class FrameOrNotification(univ.Choice):
    pass


FrameOrNotification.componentType = namedtype.NamedTypes(
    namedtype.NamedType('annotatedFrame', RcfTransferDataInvocation().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
    namedtype.NamedType('syncNotification', RcfSyncNotifyInvocation().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1)))
)


class RcfTransferBuffer(univ.SequenceOf):
    pass


RcfTransferBuffer.componentType = FrameOrNotification()


class RcfUsertoProviderPdu(univ.Choice):
    pass


RcfUsertoProviderPdu.componentType = namedtype.NamedTypes(
    namedtype.NamedType('rcfBindInvocation', SleBindInvocation().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 100))),
    namedtype.NamedType('rcfBindReturn', SleBindReturn().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 101))),
    namedtype.NamedType('rcfUnbindInvocation', SleUnbindInvocation().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 102))),
    namedtype.NamedType('rcfUnbindReturn', SleUnbindReturn().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 103))),
    namedtype.NamedType('rcfStartInvocation', RcfStartInvocation().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
    namedtype.NamedType('rcfStopInvocation', SleStopInvocation().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 2))),
    namedtype.NamedType('rcfScheduleStatusReportInvocation', SleScheduleStatusReportInvocation().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 4))),
    namedtype.NamedType('rcfGetParameterInvocation', RcfGetParameterInvocation().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 6))),
    namedtype.NamedType('rcfPeerAbortInvocation', SlePeerAbort().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 104)))
)


class RcfProvidertoUserPdu(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('rcfBindInvocation', SleBindInvocation().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 100))),
        namedtype.NamedType('rcfBindReturn', SleBindReturn().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 101))),
        namedtype.NamedType('rcfUnbindInvocation', SleUnbindInvocation().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 102))),
        namedtype.NamedType('rcfUnbindReturn', SleUnbindReturn().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 103))),
        namedtype.NamedType('rcfStartReturn', RcfStartReturn().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1))),
        namedtype.NamedType('rcfStopReturn', SleAcknowledgement().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 3))),
        namedtype.NamedType('rcfTransferBuffer', RcfTransferBuffer().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 8))),
        namedtype.NamedType('rcfScheduleStatusReportReturn', SleScheduleStatusReportReturn().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 5))),
        namedtype.NamedType('rcfStatusReportInvocation', RcfStatusReportInvocation().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 9))),
        namedtype.NamedType('rcfGetParameterReturn', RcfGetParameterReturn().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 7))),
        namedtype.NamedType('rcfPeerAbortInvocation', SlePeerAbort().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 104)))
    )
