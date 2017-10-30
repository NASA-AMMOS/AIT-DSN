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


class SleScheduleStatusReportReturn(univ.Sequence):
    pass


SleScheduleStatusReportReturn.componentType = namedtype.NamedTypes(
    namedtype.NamedType('performerCredentials', Credentials()),
    namedtype.NamedType('invokeId', InvokeId()),
    namedtype.NamedType('result', univ.Choice(componentType=namedtype.NamedTypes(
        namedtype.NamedType('positiveResult', univ.Null().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.NamedType('negativeResult', DiagnosticScheduleStatusReport().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1)))
    ))
    )
)


class DiagnosticRafGet(univ.Choice):
    pass


DiagnosticRafGet.componentType = namedtype.NamedTypes(
    namedtype.NamedType('common', Diagnostics().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('specific', univ.Integer(namedValues=namedval.NamedValues(('unknownParameter', 0))).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)


class RafProductionStatus(univ.Integer):
    pass


RafProductionStatus.namedValues = namedval.NamedValues(
    ('running', 0),
    ('interrupted', 1),
    ('halted', 2)
)


class RafParameterName(univ.Integer):
    pass


RafParameterName.namedValues = namedval.NamedValues(
    ('bufferSize', 4),
    ('deliveryMode', 6),
    ('latencyLimit', 15),
    ('minReportingCycle', 301),
    ('permittedFrameQuality', 302),
    ('reportingCycle', 26),
    ('requestedFrameQuality', 27),
    ('returnTimeoutPeriod', 29),
)


class SleStopInvocation(univ.Sequence):
    pass


SleStopInvocation.componentType = namedtype.NamedTypes(
    namedtype.NamedType('invokerCredentials', Credentials()),
    namedtype.NamedType('invokeId', InvokeId())
)


class Notification(univ.Choice):
    pass


Notification.componentType = namedtype.NamedTypes(
    namedtype.NamedType('lossFrameSync', LockStatusReport().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
    namedtype.NamedType('productionStatusChange', RafProductionStatus().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.NamedType('excessiveDataBacklog', univ.Null().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
    namedtype.NamedType('endOfData', univ.Null().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3)))
)


class RafGetParameterInvocation(univ.Sequence):
    pass


RafGetParameterInvocation.componentType = namedtype.NamedTypes(
    namedtype.NamedType('invokerCredentials', Credentials()),
    namedtype.NamedType('invokeId', InvokeId()),
    namedtype.NamedType('rafParameter', RafParameterName())
)


class HashInput(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('time', univ.OctetString().subtype(subtypeSpec=constraint.ValueSizeConstraint(8, 8))),
        namedtype.NamedType('randomNumber', univ.Integer().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 2147483647))),
        namedtype.NamedType('userName', char.VisibleString()),
        namedtype.NamedType('passWord', univ.OctetString())
    )


class ISP1Credentials(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('time', univ.OctetString().subtype(subtypeSpec=constraint.ValueSizeConstraint(8, 8))),
        namedtype.NamedType('randomNumber', univ.Integer().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 2147483647))),
        namedtype.NamedType('theProtected', univ.OctetString().subtype(subtypeSpec=constraint.ValueSizeConstraint(20, 30)))
    )


class RequestedFrameQuality(univ.Integer):
    pass


RequestedFrameQuality.namedValues = namedval.NamedValues(
    ('goodFramesOnly', 0),
    ('erredFrameOnly', 1),
    ('allFrames', 2)
)


class RafStartInvocation(univ.Sequence):
    pass


RafStartInvocation.componentType = namedtype.NamedTypes(
    namedtype.NamedType('invokerCredentials', Credentials()),
    namedtype.NamedType('invokeId', InvokeId()),
    namedtype.NamedType('startTime', ConditionalTime()),
    namedtype.NamedType('stopTime', ConditionalTime()),
    namedtype.NamedType('requestedFrameQuality', RequestedFrameQuality())
)


class RafUsertoProviderPdu(univ.Choice):
    pass


RafUsertoProviderPdu.componentType = namedtype.NamedTypes(
    namedtype.NamedType('rafBindInvocation', SleBindInvocation().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 100))),
    namedtype.NamedType('rafBindReturn', SleBindReturn().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 101))),
    namedtype.NamedType('rafUnbindInvocation', SleUnbindInvocation().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 102))),
    namedtype.NamedType('rafUnbindReturn', SleUnbindReturn().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 103))),
    namedtype.NamedType('rafStartInvocation', RafStartInvocation().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
    namedtype.NamedType('rafStopInvocation', SleStopInvocation().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 2))),
    namedtype.NamedType('rafScheduleStatusReportInvocation', SleScheduleStatusReportInvocation().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 4))),
    namedtype.NamedType('rafGetParameterInvocation', RafGetParameterInvocation().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 6))),
    namedtype.NamedType('rafPeerAbortInvocation', SlePeerAbort().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 104)))
)


class DiagnosticRafStart(univ.Choice):
    pass


DiagnosticRafStart.componentType = namedtype.NamedTypes(
    namedtype.NamedType('common', Diagnostics().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('specific', univ.Integer(namedValues=namedval.NamedValues(('outOfService', 0), ('unableToComply', 1), ('invalidStartTime', 2), ('invalidStopTime', 3), ('missingTimeValue', 4))).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)


class FrameQuality(univ.Integer):
    pass


FrameQuality.namedValues = namedval.NamedValues(
    ('good', 0),
    ('erred', 1),
    ('undetermined', 2)
)


class RafTransferDataInvocation(univ.Sequence):
    pass


RafTransferDataInvocation.componentType = namedtype.NamedTypes(
    namedtype.NamedType('invokerCredentials', Credentials()),
    namedtype.NamedType('earthReceiveTime', Time()),
    namedtype.NamedType('antennaId', AntennaId()),
    namedtype.NamedType('dataLinkContinuity', univ.Integer().subtype(subtypeSpec=constraint.ValueRangeConstraint(-1, 16777215))),
    namedtype.NamedType('deliveredFrameQuality', FrameQuality()),
    namedtype.NamedType('privateAnnotation', univ.Choice(componentType=namedtype.NamedTypes(
        namedtype.NamedType('null', univ.Null().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.NamedType('notNull', univ.OctetString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, 128)).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
    ))
    ),
    namedtype.NamedType('data', SpaceLinkDataUnit())
)


class RafSyncNotifyInvocation(univ.Sequence):
    pass


RafSyncNotifyInvocation.componentType = namedtype.NamedTypes(
    namedtype.NamedType('invokerCredentials', Credentials()),
    namedtype.NamedType('notification', Notification())
)


class FrameOrNotification(univ.Choice):
    pass


FrameOrNotification.componentType = namedtype.NamedTypes(
    namedtype.NamedType('annotatedFrame', RafTransferDataInvocation().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
    namedtype.NamedType('syncNotification', RafSyncNotifyInvocation().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1)))
)


class RafTransferBuffer(univ.SequenceOf):
    pass


RafTransferBuffer.componentType = FrameOrNotification()


class RafStartReturn(univ.Sequence):
    pass


RafStartReturn.componentType = namedtype.NamedTypes(
    namedtype.NamedType('performerCredentials', Credentials()),
    namedtype.NamedType('invokeId', InvokeId()),
    namedtype.NamedType('result', univ.Choice(componentType=namedtype.NamedTypes(
        namedtype.NamedType('positiveResult', univ.Null().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.NamedType('negativeResult', DiagnosticRafStart().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1)))
    ))
    )
)


class RafStatusReportInvocation(univ.Sequence):
    pass


RafStatusReportInvocation.componentType = namedtype.NamedTypes(
    namedtype.NamedType('invokerCredentials', Credentials()),
    namedtype.NamedType('errorFreeFrameNumber', IntUnsignedLong()),
    namedtype.NamedType('deliveredFrameNumber', IntUnsignedLong()),
    namedtype.NamedType('frameSyncLockStatus', FrameSyncLockStatus()),
    namedtype.NamedType('symbolSyncLockStatus', SymbolLockStatus()),
    namedtype.NamedType('subcarrierLockStatus', LockStatus()),
    namedtype.NamedType('carrierLockStatus', CarrierLockStatus()),
    namedtype.NamedType('productionStatus', RafProductionStatus())
)


class PermittedFrameQualitySet(univ.SetOf):
    pass


PermittedFrameQualitySet.componentType = RequestedFrameQuality()
PermittedFrameQualitySet.subtypeSpec=constraint.ValueSizeConstraint(1, 3)


class RafDeliveryMode(DeliveryMode):
    pass


class RafGetParameter(univ.Choice):
    pass

RafGetParameter.componentType = namedtype.NamedTypes(
    namedtype.NamedType('parBufferSize', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', IntPosShort())
    )).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),

    namedtype.NamedType('parDeliveryMode', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', RafDeliveryMode())
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

    namedtype.NamedType('parPermittedFrameQuality', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', PermittedFrameQualitySet())
    )).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 6))),

    namedtype.NamedType('parReportingCycle', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', CurrentReportingCycle())
    )).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 3))),

    namedtype.NamedType('parReqFrameQuality', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', univ.Integer().subtype(namedValues=namedval.NamedValues(
            ('goodFrameOnly', 0),
            ('erredFrameOnly', 1),
            ('allFrames', 2)
        )))
    )).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 4))),
    namedtype.NamedType('parReportingCycle', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', TimeoutPeriod())
    )).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 5))),
)


class RafGetParameterReturn(univ.Sequence):
    pass

RafGetParameterReturn.componentType = namedtype.NamedTypes(
    namedtype.NamedType('performerCredentials', Credentials()),
    namedtype.NamedType('invokeId', InvokeId()),
    namedtype.NamedType('result', univ.Choice(componentType=namedtype.NamedTypes(
        namedtype.NamedType('positiveResult', RafGetParameter().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
        namedtype.NamedType('negativeResult', DiagnosticRafGet().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1)))
    )))
)

class RafProvidertoUserPdu(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('rafBindInvocation', SleBindInvocation().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 100))),
        namedtype.NamedType('rafBindReturn', SleBindReturn().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 101))),
        namedtype.NamedType('rafUnbindInvocation', SleUnbindInvocation().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 102))),
        namedtype.NamedType('rafUnbindReturn', SleUnbindReturn().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 103))),
        namedtype.NamedType('rafStartReturn', RafStartReturn().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1))),
        namedtype.NamedType('rafStopReturn', SleAcknowledgement().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 3))),
        namedtype.NamedType('rafTransferBuffer', RafTransferBuffer().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 8))),
        namedtype.NamedType('rafScheduleStatusReportReturn', SleScheduleStatusReportReturn().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 5))),
        namedtype.NamedType('rafStatusReportInvocation', RafStatusReportInvocation().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 9))),
        namedtype.NamedType('rafGetParameterReturn', RafGetParameterReturn().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 7))),
        namedtype.NamedType('rafPeerAbortInvocation', SlePeerAbort().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 104)))
    )
