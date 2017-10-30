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

from pyasn1.type import univ, char, namedtype, namedval, tag, constraint, useful

from common import *
from service_instance import *


class ApplicationIdentifier(univ.Integer):
    pass


ApplicationIdentifier.namedValues = namedval.NamedValues(
    ('rtnAllFrames', 0),
    ('rtnInsert', 1),
    ('rtnChFrames', 2),
    ('rtnChFsh', 3),
    ('rtnChOcf', 4),
    ('rtnBitstr', 5),
    ('rtnSpacePkt', 6),
    ('fwdAosSpacePkt', 7),
    ('fwdAosVca', 8),
    ('fwdBitstr', 9),
    ('fwdProtoVcdu', 10),
    ('fwdInsert', 11),
    ('fwdCVcdu', 12),
    ('fwdTcSpacePkt', 13),
    ('fwdTcVca', 14),
    ('fwdTcFrame', 15),
    ('fwdCltu', 16)
)


class IdentifierString(char.VisibleString):
    pass


class AuthorityIdentifier(IdentifierString):
    pass


class BindDiagnostic(univ.Integer):
    pass


BindDiagnostic.namedValues = namedval.NamedValues(
    ('accessDenied', 0),
    ('serviceTypeNotSupported', 1),
    ('versionNotSupported', 2),
    ('noSuchServiceInstance', 3),
    ('alreadyBound', 4),
    ('siNotAccessibleToThisInitiator', 5),
    ('inconsistentServiceType', 6),
    ('invalidTime', 7),
    ('outOfService', 8),
    ('otherReason', 127)
)


class LogicalPortName(IdentifierString):
    pass


class PeerAbortDiagnostic(univ.Integer):
    pass


PeerAbortDiagnostic.namedValues = namedval.NamedValues(
    ('accessDenied', 0),
    ('unexpectedResponderId', 1),
    ('operationalRequirement', 2),
    ('protocolError', 3),
    ('communicationsFailure', 4),
    ('encodingError', 5),
    ('returnTimeout', 6),
    ('endOfServiceProvisionPeriod', 7),
    ('unsolicitedInvokeId', 8),
    ('otherReason', 127)
)


class SlePeerAbort(PeerAbortDiagnostic):
    pass


class PortId(LogicalPortName):
    pass


class UnbindReason(univ.Integer):
    pass


UnbindReason.namedValues = namedval.NamedValues(
    ('end', 0),
    ('suspend', 1),
    ('versionNotSupported', 2),
    ('other', 127)
)


class VersionNumber(IntPosShort):
    pass


class SleBindInvocation(univ.Sequence):
    pass


SleBindInvocation.componentType = namedtype.NamedTypes(
    namedtype.NamedType('invokerCredentials', Credentials()),
    namedtype.NamedType('initiatorIdentifier', AuthorityIdentifier()),
    namedtype.NamedType('responderPortIdentifier', PortId()),
    namedtype.NamedType('serviceType', ApplicationIdentifier()),
    namedtype.NamedType('versionNumber', VersionNumber()),
    namedtype.NamedType('serviceInstanceIdentifier', ServiceInstanceIdentifier())
)


class SleBindReturn(univ.Sequence):
    pass


SleBindReturn.componentType = namedtype.NamedTypes(
    namedtype.NamedType('performerCredentials', Credentials()),
    namedtype.NamedType('responderIdentifier', AuthorityIdentifier()),
    namedtype.NamedType('result', univ.Choice(componentType=namedtype.NamedTypes(
        namedtype.NamedType('positive', VersionNumber().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.NamedType('negative', BindDiagnostic().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
    )))
)


class SleUnbindInvocation(univ.Sequence):
    pass


SleUnbindInvocation.componentType = namedtype.NamedTypes(
    namedtype.NamedType('invokerCredentials', Credentials()),
    namedtype.NamedType('unbindReason', UnbindReason())
)


class SleUnbindReturn(univ.Sequence):
    pass


SleUnbindReturn.componentType = namedtype.NamedTypes(
    namedtype.NamedType('responderCredentials', Credentials()),
    namedtype.NamedType('result', univ.Choice(componentType=namedtype.NamedTypes(
        namedtype.NamedType('positive', univ.Null().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)))
    ))
    )
)
