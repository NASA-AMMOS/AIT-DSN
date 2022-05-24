import pytest
import ait.dsn.sle.common as common
import datetime as dt
import struct


def test_generate_encoded_time():
    datetime_ = dt.datetime(1958, 1, 1) + dt.timedelta(days=10000, milliseconds=3308, microseconds=721)
    encoded_time = common.generate_encoded_time(datetime_)
    days, ms, us = struct.unpack('!HIH', bytearray(encoded_time))
    assert days == 10000
    assert ms == 3308
    assert us == 721
