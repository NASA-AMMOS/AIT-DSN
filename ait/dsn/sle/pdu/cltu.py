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


class CurrentReportingCycle(univ.Choice):
    pass


CurrentReportingCycle.componentType = namedtype.NamedTypes(
    namedtype.NamedType('periodicReportingOff', univ.Null().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('periodicReportingOn', ReportingCycle().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)


class ProductionStatus(univ.Integer):
    pass


ProductionStatus.namedValues = namedval.NamedValues(
    ('operational', 0),
    ('configured', 1),
    ('interrupted', 2),
    ('halted', 3)
)


class SubcarrierDivisor(IntPosShort):
    pass


class CltuIdentification(IntUnsignedLong):
    pass


class CltuLastOk(univ.Choice):
    pass


CltuLastOk.componentType = namedtype.NamedTypes(
    namedtype.NamedType('noCltuOk', univ.Null().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('cltuOk', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('cltuIdentification', CltuIdentification()),
        namedtype.NamedType('radiationStopTime', Time())
    ))
    .subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1)))
)


class VcId(univ.Integer):
    pass


VcId.subtypeSpec = constraint.ValueRangeConstraint(0, 63)


class GvcId(univ.Sequence):
    pass


GvcId.componentType = namedtype.NamedTypes(
    namedtype.NamedType('spacecraftId', univ.Integer().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 1023))),
    namedtype.NamedType('versionNumber', univ.Integer().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, 3))),
    namedtype.NamedType('vcId', univ.Choice(componentType=namedtype.NamedTypes(
        namedtype.NamedType('masterChannel', univ.Null().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.NamedType('virtualChannel', VcId().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
    ))
    )
)


class ModulationFrequency(IntPosLong):
    pass


class DiagnosticCltuTransferData(univ.Choice):
    pass


DiagnosticCltuTransferData.componentType = namedtype.NamedTypes(
    namedtype.NamedType('common', Diagnostics().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('specific', univ.Integer(namedValues=namedval.NamedValues(('unableToProcess', 0), ('unableToStore', 1), ('outOfSequence', 2), ('inconsistentTimeRange', 3), ('invalidTime', 4), ('lateSldu', 5), ('invalidDelayTime', 6), ('cltuError', 7))).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)


class CltuStatus(ForwardDuStatus):
    pass


class UplinkStatus(univ.Integer):
    pass


UplinkStatus.namedValues = namedval.NamedValues(
    ('uplinkStatusNotAvailable', 0),
    ('noRfAvailable', 1),
    ('noBitLock', 2),
    ('nominal', 3)
)


class CltuData(SpaceLinkDataUnit):
    pass


class EventInvocationId(IntUnsignedLong):
    pass


class CltuNotification(univ.Choice):
    pass


CltuNotification.componentType = namedtype.NamedTypes(
    namedtype.NamedType('cltuRadiated', univ.Null().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('slduExpired', univ.Null().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.NamedType('productionInterrupted', univ.Null().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
    namedtype.NamedType('productionHalted', univ.Null().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3))),
    namedtype.NamedType('productionOperational', univ.Null().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 4))),
    namedtype.NamedType('bufferEmpty', univ.Null().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 5))),
    namedtype.NamedType('actionListCompleted', EventInvocationId().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 6))),
    namedtype.NamedType('actionListNotCompleted', EventInvocationId().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 7))),
    namedtype.NamedType('eventConditionEvFalse', EventInvocationId().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 8)))
)


class NumberOfCltusRadiated(IntUnsignedLong):
    pass


class BufferSize(IntUnsignedLong):
    pass


class CltuDeliveryMode(DeliveryMode):
    pass


class ModulationIndex(IntPosShort):
    pass


class ClcwGvcId(univ.Choice):
    pass


ClcwGvcId.componentType = namedtype.NamedTypes(
    namedtype.NamedType('congigured', GvcId().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
    namedtype.NamedType('notConfigured', univ.Null().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)


class CltuParameterName(ParameterName):
    pass


class DiagnosticCltuGetParameter(univ.Choice):
    pass


DiagnosticCltuGetParameter.componentType = namedtype.NamedTypes(
    namedtype.NamedType('common', Diagnostics().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('specific', univ.Integer(namedValues=namedval.NamedValues(('unknownParameter', 0))).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)


class DiagnosticCltuStart(univ.Choice):
    pass


DiagnosticCltuStart.componentType = namedtype.NamedTypes(
    namedtype.NamedType('common', Diagnostics().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('specific', univ.Integer(namedValues=namedval.NamedValues(('outOfService', 0), ('unableToComply', 1), ('productionTimeExpired', 2), ('invalidCltuId', 3))).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)


class CltuLastProcessed(univ.Choice):
    pass


CltuLastProcessed.componentType = namedtype.NamedTypes(
    namedtype.NamedType('noCltuProcessed', univ.Null().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('cltuProcessed', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('cltuIdentification', CltuIdentification()),
        namedtype.NamedType('radiationStartTime', ConditionalTime()),
        namedtype.NamedType('cltuStatus', CltuStatus())
    ))
    .subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1)))
)


class NumberOfCltusProcessed(IntUnsignedLong):
    pass


class NumberOfCltusReceived(IntUnsignedLong):
    pass


class ClcwPhysicalChannel(univ.Choice):
    pass


ClcwPhysicalChannel.componentType = namedtype.NamedTypes(
    namedtype.NamedType('configured', char.VisibleString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, 32)).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('notConfigured', univ.Null().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)


class TimeoutPeriod(univ.Integer):
    pass


TimeoutPeriod.subtypeSpec = constraint.ValueRangeConstraint(1, 600)


class DiagnosticCltuThrowEvent(univ.Choice):
    pass


DiagnosticCltuThrowEvent.componentType = namedtype.NamedTypes(
    namedtype.NamedType('common', Diagnostics().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('specific', univ.Integer(namedValues=namedval.NamedValues(('operationNotSupported', 0), ('eventInvocIdOutOfSequence', 1), ('noSuchEvent', 2))).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)


class CltuGetParameter(univ.Choice):
    pass

CltuGetParameter.componentType = namedtype.NamedTypes(
    namedtype.NamedType('parAcquisitionSequenceLength', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', IntUnsignedShort())
    )).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),

    namedtype.NamedType('parBitLockRequired', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', univ.Integer().subtype(namedValues=namedval.NamedValues(
            ('yes', 0),
            ('no', 1)
        )))
    )).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1))),

    namedtype.NamedType('parClcwGlobalVcId', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', ClcwGvcId())
    )).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 2))),

    namedtype.NamedType('parClcwPhysicalChannel', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', ClcwPhysicalChannel())
    )).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 3))),

    namedtype.NamedType('parDeliveryMode', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', CltuDeliveryMode())
    )).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 4))),

    namedtype.NamedType('parCltuIdentification', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', CltuIdentification())
    )).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 5))),

    namedtype.NamedType('parEventInvocationIdentification', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', CltuIdentification())
    )).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 6))),

    namedtype.NamedType('parMaximumCltuLength', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', EventInvocationId())
    )).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 7))),

    namedtype.NamedType('parMinimumDelayTime', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', Duration())
    )).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 8))),

    namedtype.NamedType('parMinReportingCycle', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', IntPosShort())
    )).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 19))),

    namedtype.NamedType('parModulationFrequency', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', ModulationFrequency())
    )).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 9))),

    namedtype.NamedType('parModulationIndex', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', ModulationIndex())
    )).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 10))),

    namedtype.NamedType('parNotificationMode', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', univ.Integer().subtype(namedValues=namedval.NamedValues(
            ('deffered', 0),
            ('immediate', 1)
        )))
    )).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 11))),

    namedtype.NamedType('parPlop1IdleSequenceLength', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', IntUnsignedShort())
    )).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 12))),

    namedtype.NamedType('parPlopInEffect', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', univ.Integer().subtype(namedValues=namedval.NamedValues(
            ('plop1', 0),
            ('plop2', 1)
        )))
    )).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 13))),

    namedtype.NamedType('parProtocolAbortMode', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', univ.Integer().subtype(namedValues=namedval.NamedValues(
            ('abort', 0),
            ('continue', 1)
        )))
    )).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 14))),

    namedtype.NamedType('parReportingCycle', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', CurrentReportingCycle())
    )).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 15))),

    namedtype.NamedType('parReturnTimeout', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', TimeoutPeriod())
    )).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 16))),

    namedtype.NamedType('parRfAvailableRequired', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', univ.Integer().subtype(namedValues=namedval.NamedValues(
            ('yes', 0),
            ('no', 1)
        )))
    )).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 17))),

    namedtype.NamedType('parSubcarrierToBitRateRatio', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('parameterName', ParameterName()),
        namedtype.NamedType('parameterValue', SubcarrierDivisor())
    )).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 18)))
)


class CltuGetParameterReturn(univ.Sequence):
    pass


CltuGetParameterReturn.componentType = namedtype.NamedTypes(
    namedtype.NamedType('performerCredentials', Credentials()),
    namedtype.NamedType('invokeId', InvokeId()),
    namedtype.NamedType('result', univ.Choice(componentType=namedtype.NamedTypes(
        namedtype.NamedType('positiveResult', CltuGetParameter().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.NamedType('negativeResult', DiagnosticCltuGetParameter().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
    ))
    )
)


class CltuAsyncNotifyInvocation(univ.Sequence):
    pass


CltuAsyncNotifyInvocation.componentType = namedtype.NamedTypes(
    namedtype.NamedType('invokerCredentials', Credentials()),
    namedtype.NamedType('cltuNotification', CltuNotification()),
    namedtype.NamedType('cltuLastProcessed', CltuLastProcessed()),
    namedtype.NamedType('cltuLastOk', CltuLastOk()),
    namedtype.NamedType('productionStatus', ProductionStatus()),
    namedtype.NamedType('uplinkStatus', UplinkStatus())
)


class CltuTransferDataReturn(univ.Sequence):
    pass


CltuTransferDataReturn.componentType = namedtype.NamedTypes(
    namedtype.NamedType('performerCredentials', Credentials()),
    namedtype.NamedType('invokeId', InvokeId()),
    namedtype.NamedType('cltuIdentification', CltuIdentification()),
    namedtype.NamedType('cltuBufferAvailable', BufferSize()),
    namedtype.NamedType('result', univ.Choice(componentType=namedtype.NamedTypes(
        namedtype.NamedType('positiveResult', univ.Null().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.NamedType('negativeResult', DiagnosticCltuTransferData().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
    ))
    )
)


class CltuGetParameterInvocation(univ.Sequence):
    pass


CltuGetParameterInvocation.componentType = namedtype.NamedTypes(
    namedtype.NamedType('invokerCredentials', Credentials()),
    namedtype.NamedType('invokeId', InvokeId()),
    namedtype.NamedType('cltuParameter', CltuParameterName())
)


class CltuStartInvocation(univ.Sequence):
    pass


CltuStartInvocation.componentType = namedtype.NamedTypes(
    namedtype.NamedType('invokerCredentials', Credentials()),
    namedtype.NamedType('invokeId', InvokeId()),
    namedtype.NamedType('firstCltuIdentification', CltuIdentification())
)


class CltuTransferDataInvocation(univ.Sequence):
    pass


CltuTransferDataInvocation.componentType = namedtype.NamedTypes(
    namedtype.NamedType('invokerCredentials', Credentials()),
    namedtype.NamedType('invokeId', InvokeId()),
    namedtype.NamedType('cltuIdentification', CltuIdentification()),
    namedtype.NamedType('earliestTransmissionTime', ConditionalTime()),
    namedtype.NamedType('latestTransmissionTime', ConditionalTime()),
    namedtype.NamedType('delayTime', Duration()),
    namedtype.NamedType('slduRadiationNotification', SlduStatusNotification()),
    namedtype.NamedType('cltuData', CltuData())
)


class CltuThrowEventInvocation(univ.Sequence):
    pass


CltuThrowEventInvocation.componentType = namedtype.NamedTypes(
    namedtype.NamedType('invokerCredentials', Credentials()),
    namedtype.NamedType('invokeId', InvokeId()),
    namedtype.NamedType('eventInvocationIdentification', EventInvocationId()),
    namedtype.NamedType('eventIdentifier', IntPosShort()),
    namedtype.NamedType('eventQualifier', univ.OctetString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, 1024)))
)


class CltuUserToProviderPdu(univ.Choice):
    pass


CltuUserToProviderPdu.componentType = namedtype.NamedTypes(
    namedtype.NamedType('cltuBindInvocation', SleBindInvocation().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 100))),
    namedtype.NamedType('cltuUnbindInvocation', SleUnbindInvocation().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 102))),
    namedtype.NamedType('cltuStartInvocation', CltuStartInvocation().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
    namedtype.NamedType('cltuStopInvocation', SleStopInvocation().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
    namedtype.NamedType('cltuScheduleStatusReportInvocation', SleScheduleStatusReportInvocation().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 4))),
    namedtype.NamedType('cltuGetParameterInvocation', CltuGetParameterInvocation().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 6))),
    namedtype.NamedType('cltuThrowEventInvocation', CltuThrowEventInvocation().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 8))),
    namedtype.NamedType('cltuTransferDataInvocation', CltuTransferDataInvocation().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 10))),
    namedtype.NamedType('cltuPeerAbortInvocation', SlePeerAbort().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 104)))
)


class CltuStartReturn(univ.Sequence):
    pass


CltuStartReturn.componentType = namedtype.NamedTypes(
    namedtype.NamedType('performerCredentials', Credentials()),
    namedtype.NamedType('invokeId', InvokeId()),
    namedtype.NamedType('result', univ.Choice(componentType=namedtype.NamedTypes(
        namedtype.NamedType('positiveResult', univ.Sequence(componentType=namedtype.NamedTypes(
            namedtype.NamedType('startRadiationTime', Time()),
            namedtype.NamedType('stopRadiationTime', ConditionalTime())
        ))
        .subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
        namedtype.NamedType('negativeResult', DiagnosticCltuStart().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
    ))
    )
)


class CltuStatusReportInvocation(univ.Sequence):
    pass


CltuStatusReportInvocation.componentType = namedtype.NamedTypes(
    namedtype.NamedType('invokerCredentials', Credentials()),
    namedtype.NamedType('cltuLastProcessed', CltuLastProcessed()),
    namedtype.NamedType('cltuLastOk', CltuLastOk()),
    namedtype.NamedType('cltuProductionStatus', ProductionStatus()),
    namedtype.NamedType('uplinkStatus', UplinkStatus()),
    namedtype.NamedType('numberOfCltusReceived', NumberOfCltusReceived()),
    namedtype.NamedType('numberOfCltusProcessed', NumberOfCltusProcessed()),
    namedtype.NamedType('numberOfCltusRadiated', NumberOfCltusRadiated()),
    namedtype.NamedType('cltuBufferAvailable', BufferSize())
)


class CltuThrowEventReturn(univ.Sequence):
    pass


CltuThrowEventReturn.componentType = namedtype.NamedTypes(
    namedtype.NamedType('performerCredentials', Credentials()),
    namedtype.NamedType('invokeId', InvokeId()),
    namedtype.NamedType('eventInvocationIdentification', EventInvocationId()),
    namedtype.NamedType('result', univ.Choice(componentType=namedtype.NamedTypes(
        namedtype.NamedType('positiveResult', univ.Null().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.NamedType('negativeResult', DiagnosticCltuThrowEvent().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
    ))
    )
)


class CltuProviderToUserPdu(univ.Choice):
    pass


CltuProviderToUserPdu.componentType = namedtype.NamedTypes(
    namedtype.NamedType('cltuBindReturn', SleBindReturn().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 101))),
    namedtype.NamedType('cltuUnbindReturn', SleUnbindReturn().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 103))),
    namedtype.NamedType('cltuStartReturn', CltuStartReturn().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1))),
    namedtype.NamedType('cltuStopReturn', SleAcknowledgement().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3))),
    namedtype.NamedType('cltuScheduleStatusReportReturn', SleScheduleStatusReportReturn().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 5))),
    namedtype.NamedType('cltuGetParameterReturn', CltuGetParameterReturn().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 7))),
    namedtype.NamedType('cltuThrowEventReturn', CltuThrowEventReturn().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 9))),
    namedtype.NamedType('cltuTransferDataReturn', CltuTransferDataReturn().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 11))),
    namedtype.NamedType('cltuAsyncNotifyInvocation', CltuAsyncNotifyInvocation().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 12))),
    namedtype.NamedType('cltuStatusReportInvocation', CltuStatusReportInvocation().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 13))),
    namedtype.NamedType('cltuPeerAbortInvocation', SlePeerAbort().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 104)))
)
