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

from ait.dsn.sle.pdu.common import *

from pyasn1.type import univ, char, namedtype, namedval, tag, constraint


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
