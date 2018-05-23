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
from ait.dsn.cfdp.cfdp import CFDP
from ait.dsn.cfdp.machines import Sender1
from ait.dsn.cfdp.primitives import ConditionCode, IndicationType


# Supress logging because noisy
patcher = mock.patch('ait.core.log.info')
patcher.start()


class CFDPPutTest(unittest.TestCase):

    def setUp(self):
        # Set up a CFDP entity with ID 1
        self.cfdp = CFDP('1')
        # Patch outgoing path with testdata path
        self.cfdp._data_paths['outgoing'] = os.path.join(os.path.dirname(__file__), 'testdata')

    def tearDown(self):
        self.cfdp.disconnect()
        self.cfdp = None

    def test_put(self):
        destination_id = '2'
        source_file = 'small.txt'
        destination_file = 'small.txt'

        transaction_id = self.cfdp.put(destination_id, source_file, destination_file)

        self.assertEqual(len(self.cfdp._machines), 1, 'New machine is created after put request')

        machine = self.cfdp._machines[transaction_id]
        self.assertTrue(isinstance(machine, Sender1), 'Entity type is Sender 1 (UNACK, unreliable)')


class CFDPCommandTest(unittest.TestCase):

    def setUp(self):
        # Set up a CFDP entity with ID 1
        self.cfdp = CFDP('1')
        # Patch outgoing path with testdata path
        self.cfdp._data_paths['outgoing'] = os.path.join(os.path.dirname(__file__), 'testdata')

        destination_id = '2'
        source_file = 'small.txt'
        destination_file = 'small.txt'

        self.transaction_id = self.cfdp.put(destination_id, source_file, destination_file)
        self.machine = self.cfdp._machines[self.transaction_id]

        self.machine.indication_handler = mock.MagicMock()

    def tearDown(self):
        self.cfdp.disconnect()
        self.cfdp = None

    def test_cmd_invalid_tx(self):
        invalid_tx = 5
        import ait.dsn.cfdp.exceptions
        with self.assertRaises(ait.dsn.cfdp.exceptions.InvalidTransaction):
            self.cfdp.report(invalid_tx)
        with self.assertRaises(ait.dsn.cfdp.exceptions.InvalidTransaction):
            self.cfdp.cancel(invalid_tx)
        with self.assertRaises(ait.dsn.cfdp.exceptions.InvalidTransaction):
            self.cfdp.suspend(invalid_tx)
        with self.assertRaises(ait.dsn.cfdp.exceptions.InvalidTransaction):
            self.cfdp.resume(invalid_tx)

    def test_report(self):
        self.cfdp.report(self.transaction_id)
        # Assert that indication handler was called at all with REPORT_INDICATION
        self.machine.indication_handler.assert_any_call(IndicationType.REPORT_INDICATION, status_report=None)

    def test_cancel(self):
        self.cfdp.cancel(self.transaction_id)
        self.assertEqual(self.machine.transaction.condition_code, ConditionCode.CANCEL_REQUEST_RECEIVED,
                         'Transaction condition code is set to CANCEL_REQUEST_RECEIVED')

    def test_suspend(self):
        self.cfdp.suspend(self.transaction_id)
        # Suspend will called `machine.suspend` to be called, which should mean the following conditions are satisfied
        self.assertTrue(self.machine.transaction.suspended, 'Suspended flag true on the transaction data')
        # Assert timers are reset
        import ait.dsn.cfdp.timer
        if self.machine.inactivity_timer:
            self.assertEqual(self.machine.inactivity_timer.timer_mode, ait.dsn.cfdp.timer.TimerMode.TIMER_PAUSED,
                            "Inactivity timer is paused")
        if self.machine.ack_timer:
            self.assertEqual(self.machine.ack_timer.timer_mode, ait.dsn.cfdp.timer.TimerMode.TIMER_PAUSED,
                             "Ack timer is paused")
        if self.machine.nak_timer:
            self.assertEqual(self.machine.inactivity_timer.nak_timer, ait.dsn.cfdp.timer.TimerMode.TIMER_PAUSED,
                             "Nak timer is paused")
        # Assert indication was sent for suspention
        self.machine.indication_handler.assert_any_call(IndicationType.SUSPENDED_INDICATION,
                                                        transaction_id=self.transaction_id,
                                                        condition_code=ConditionCode.SUSPEND_REQUEST_RECEIVED)

    def test_resume(self):
        # Set suspended to True as if the transaction had already been suspended
        self.machine.transaction.suspended = True
        self.cfdp.resume(self.transaction_id)
        # Suspend will called `machine.suspend` to be called, which should mean the following conditions are satisfied
        self.assertFalse(self.machine.transaction.suspended, 'Suspended flag false on the transaction data')
        # Assert indication was sent for suspention
        self.machine.indication_handler.assert_any_call(IndicationType.RESUMED_INDICATION)
