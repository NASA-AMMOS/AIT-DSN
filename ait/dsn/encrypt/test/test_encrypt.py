# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2016, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.

import datetime as dt
import inspect
import os
import unittest
import binascii

import nose.tools
from unittest import mock

import ait.core.cfg as cfg
import ait.core.db as db
import ait.core.dmc as dmc
import ait.core.tlm as tlm
from ait.dsn.encrypt.encrypter import EncryptMode, EncryptResult, EncrypterFactory, NullEncrypter


tc4_1_hexstr =  "2003009e00ff000100001880d037008c197f0b000100840000344892bbc54f5395297d4c371" \
                "72f2a3c46f6a81c1349e9e26ac80985d8bbd55a5814c662e49fba52f99ba09558cd21cf268b" \
                "8e50b2184137e80f76122034c580464e2f06d2659a50508bdfe9e9a55990ba4148af896d8a6" \
                "eebe8b5d2258685d4ce217a20174fdd4f0efac62758c51b04e55710a47209c923b641d19a39" \
                "001f9e986166f5ffd95555"
## tc4_1_bytes = bytes.fromhex(tc4_1_hexstr)
tc4_1_byte_arr = bytearray(binascii.unhexlify(tc4_1_hexstr))

class TestEncryptResultObject(unittest.TestCase):
    def test_default_init(self):
        res = EncryptResult()
        assert res.input is None
        assert res.result is None
        assert res.errors is None
        assert res.mode == EncryptMode.ENCRYPT

        input = 'foobar'
        result = [1, 2, 3]
        errors = ['error1', 'error2']
        res = EncryptResult(input=input, result=result, errors=errors)
        assert res.input == input
        assert res.result == result
        assert res.errors == errors
        assert res.mode == EncryptMode.ENCRYPT

        res = EncryptResult(mode=EncryptMode.DECRYPT, input=input, result=result, errors=errors)
        assert res.input == input
        assert res.result == result
        assert res.errors == errors
        assert res.mode == EncryptMode.DECRYPT

class TestFactory(unittest.TestCase):
    def test_factory(self):

        encr = EncrypterFactory().get()
        assert isinstance(encr, NullEncrypter)

        null_classname = "ait.dsn.encrypt.encrypter.NullEncrypter"
        invalid_classname = "i.do.not.exist"

        encr = EncrypterFactory().get(null_classname)
        assert isinstance(encr, NullEncrypter)

        with nose.tools.assert_raises(ImportError):
            EncrypterFactory().get(invalid_classname)

class TestNullEncrypter(unittest.TestCase):
    def test_null_encrypter(self):
        encr_clz = 'ait.dsn.encrypt.encrypter.NullEncrypter'
        encr = EncrypterFactory().get(encr_clz)
        assert isinstance(encr, NullEncrypter)
        assert not encr.is_connected()

        # encrypt should fail since not connected generally, but not for Null
        ait_result = encr.encrypt(tc4_1_byte_arr)
        assert ait_result.has_errors

        encr.configure()
        assert not encr.is_connected()
        assert not encr._debug_enabled
        assert encr._vcids_filter is None

        vcid_list = [3, 6, 9]
        enc_cfg = {'vcid_filter': vcid_list, 'debug_enabled' : True}
        encr.configure(**enc_cfg)
        assert encr._debug_enabled
        assert encr._vcids_filter == vcid_list

        ait_result = encr.encrypt(tc4_1_byte_arr)
        assert ait_result.has_errors

        encr.connect()
        assert encr.is_connected()

        ait_result = encr.encrypt(tc4_1_byte_arr)
        assert ait_result.mode == EncryptMode.ENCRYPT
        assert not ait_result.has_errors
        assert ait_result.has_result
        assert ait_result.result == tc4_1_byte_arr

        ait_result = encr.decrypt(tc4_1_byte_arr)
        assert ait_result.mode == EncryptMode.DECRYPT
        assert not ait_result.has_errors
        assert ait_result.has_result
        assert ait_result.result == tc4_1_byte_arr

        encr.close()
        assert not encr.is_connected()
        ait_result = encr.encrypt(tc4_1_byte_arr)
        assert ait_result.has_errors


class TestKmcEncrypter(unittest.TestCase):
    '''
    Unit test assumes we cannot load the KMC Encrypter dependencies
    '''
    def test_kmc_encrypter(self):
        encr_mod_name = 'ait.dsn.encrypt.kmc_encrypter'
        encr_clz_name = 'KmcSdlsEncrypter'
        encr_full_clz = encr_mod_name + "." + encr_clz_name
        encr = EncrypterFactory().get(encr_full_clz)

        assert type(encr).__name__ == encr_clz_name

        # encrypt should fail since not configured nor connected
        ait_result = encr.encrypt(tc4_1_byte_arr)
        assert ait_result.mode == EncryptMode.ENCRYPT
        assert ait_result.has_errors

        encr.configure()
        ait_result = encr.encrypt(tc4_1_byte_arr)
        assert ait_result.mode == EncryptMode.ENCRYPT
        assert ait_result.has_errors

        # Failed import of KMC lib results in a Name error
        #with nose.tools.assert_raises(NameError):
        #    encr.connect()
        encr.connect()
        assert not encr.is_connected()

        ait_result = encr.encrypt(tc4_1_byte_arr)
        assert ait_result.mode == EncryptMode.ENCRYPT
        assert ait_result.has_errors


        ait_result = encr.decrypt(tc4_1_byte_arr)
        assert ait_result.mode == EncryptMode.DECRYPT
        assert ait_result.has_errors

        encr.close()
        ait_result = encr.encrypt(tc4_1_byte_arr)
        assert ait_result.has_errors