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

import os
import unittest
import mock

import ait.core
from ait.dsn.bch.bch import BCH

# Supress logging because noisy
patcher = mock.patch('ait.core.log.info')
patcher.start()


class BCHTest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_success_encode(self):

        input_bytearr_1 = bytearray(b'\x00\x01\x02\x03\x04\x05\x06')
        input_bytearr_2 = bytearray(b'\xA0\xB1\xC2\xD3\xE4\xF5\x06')

        expect_out_bytearr_1 = bytearray(b'\x00\x01\x02\x03\x04\x05\x06\xC6')
        expect_out_bytearr_2 = bytearray(b'\xA0\xB1\xC2\xD3\xE4\xF5\x06\x7A')

        output_bytearr_1 = BCH.generateBCH(input_bytearr_1)
        output_bytearr_2 = BCH.generateBCH(input_bytearr_2)

        self.assertEqual(len(expect_out_bytearr_1), len(output_bytearr_1))
        self.assertEqual(expect_out_bytearr_1, output_bytearr_1)

        self.assertEqual(len(expect_out_bytearr_2), len(output_bytearr_2))
        self.assertEqual(expect_out_bytearr_2, output_bytearr_2)


    def test_reject_encode(self):
        input_bytearr_1 = None
        input_bytearr_2 = bytearray(b'\x00\x01\x02\x03\x04\x05')
        input_bytearr_3 = bytearray(b'\x00\x01\x02\x03\x04\x05\x06\x07')

        expect_out_bytearr_1 = None
        expect_out_bytearr_2 = None
        expect_out_bytearr_3 = None

        output_bytearr_1 = BCH.generateBCH(input_bytearr_1)
        output_bytearr_2 = BCH.generateBCH(input_bytearr_2)
        output_bytearr_3 = BCH.generateBCH(input_bytearr_3)


        self.assertIsNone(output_bytearr_1)
        self.assertIsNone(output_bytearr_2)
        self.assertIsNone(output_bytearr_3)
