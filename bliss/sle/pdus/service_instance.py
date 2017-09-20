from pyasn1.type import univ, char, namedtype, namedval, tag, constraint, useful


class ServiceInstanceAttributeElement(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('identifier', univ.ObjectIdentifier()),
        namedtype.NamedType('siAttributeValue', char.VisibleString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, 256)))
    )


class ServiceInstanceAttribute(univ.SetOf):
    componentType = ServiceInstanceAttributeElement()


class ServiceInstanceIdentifier(univ.SequenceOf):
    componentType = ServiceInstanceAttribute()


def _OID(*components):
    output = []
    for x in tuple(components):
        if isinstance(x, univ.ObjectIdentifier):
            output.extend(list(x))
        else:
            output.append(int(x))

    return univ.ObjectIdentifier(output)


rsp = _OID(1, 3, 112, 4, 3, 1, 2, 40)
cltu = _OID(1, 3, 112, 4, 3, 1, 2, 7)
spack = _OID(1, 3, 112, 4, 3, 1, 2, 53)
rcf = _OID(1, 3, 112, 4, 3, 1, 2, 46)
tcva = _OID(1, 3, 112, 4, 3, 1, 2, 16)
rsl_fg = _OID(1, 3, 112, 4, 3, 1, 2, 38)
raf = _OID(1, 3, 112, 4, 3, 1, 2, 22)
fsl_fg = _OID(1, 3, 112, 4, 3, 1, 2, 14)
fsp = _OID(1, 3, 112, 4, 3, 1, 2, 10)
sagr = _OID(1, 3, 112, 4, 3, 1, 2, 52)
rocf = _OID(1, 3, 112, 4, 3, 1, 2, 49)
tcf = _OID(1, 3, 112, 4, 3, 1, 2, 12)
rcfsh = _OID(1, 3, 112, 4, 3, 1, 2, 44)
