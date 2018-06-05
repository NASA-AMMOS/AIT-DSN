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

from ait.dsn.sle.pdu.binds import *
from ait.dsn.sle.pdu.cltu.common import *

from pyasn1.type import univ, namedtype, namedval, tag, constraint


class CltuGetParameter(univ.Choice):
    """CltuGetParameter v5"""
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


class CltuThrowEventInvocation(univ.Sequence):
    """CltuThrowEventInvocation v5"""
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
