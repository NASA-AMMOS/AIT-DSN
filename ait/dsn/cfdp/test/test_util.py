# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2022, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.
import os

from ait.dsn.cfdp.util import calc_checksum
from ait.dsn.cfdp.util import checksum_of_word


def test_checksum_of_word_pads_a_short_word():
    assert checksum_of_word([1, 2, 3, 4]) == 0x01020304
    assert checksum_of_word([1, 2, 3]) == 0x01020300
    assert checksum_of_word([1, 2]) == 0x01020000
    assert checksum_of_word([1]) == 0x01000000


def test_calc_checksum_handles_every_tail_length(tmpdir):
    for size in range(1, 9):
        path = os.path.join(str(tmpdir), "f{}.bin".format(size))
        with open(path, "wb") as fh:
            fh.write(bytes(range(1, size + 1)))
        assert calc_checksum(path) is not None
