# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2018, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.


class PDU(object):

    def __init__(self):
        # self.header = Header()
        self._valid = False
        self._errors = None

    @property
    def length(self):
        """Byte length of Header"""
        return len(self.to_bytes())

    def is_valid(self):
        """Check if all header fields are valid length"""
        # TODO put in checks
        self._valid = True
        self._errors = None
        return self._valid

    def to_bytes(self):
        """Return array of bytes binary converted to int"""
        raise NotImplementedError

    @staticmethod
    def to_object(bytes):
        """Return PDU subclass object created from given bytes of data"""
        raise NotImplementedError
