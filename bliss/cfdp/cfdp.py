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

import logging
import os
import socket
import time
import traceback

import gevent
import gevent.queue
import gevent.socket

from bliss.cfdp import settings
from bliss.cfdp.events import Event
from bliss.cfdp.machines.receiver1 import Receiver1
from bliss.cfdp.machines.sender1 import Sender1
from bliss.cfdp.mib import MIB
from bliss.cfdp.pdu import make_pdu_from_bytes, Header
from bliss.cfdp.primitives import RequestType, TransmissionMode, FileDirective, Role, IndicationType
from bliss.cfdp.request import create_request_from_type
from bliss.cfdp.util import write_pdu_to_file

logging.basicConfig(level=logging.DEBUG,
                    format='[%(asctime)s] %(levelname)-10s %(message)-100s %(filename)s:%(lineno)s',
                    datefmt='%m-%d %H:%M')

class CFDP(object):
    """
    CFDP class to manage connection handler, routing handler, Txs
    """

    mib = MIB()
    transaction_counter = 0
    outgoing_pdu_queue = gevent.queue.Queue()
    incoming_pdu_queue = gevent.queue.Queue()

    def __init__(self, entity_id, *args, **kwargs):
        # State machines for current transactions (basically just transactions. Can be Class 1 or 2 sender or receiver
        self._machines = {}
        # temporary handler for getting pdus from directory and putting into incoming queue
        self._read_pdu_handler = gevent.spawn(read_pdus, self)
        # Spawn handlers for incoming and outgoing data
        self._receiving_handler = gevent.spawn(receiving_handler, self)
        self._sending_handler = gevent.spawn(sending_handler, self)
        # cycle through transactions to progress state machines
        self._transaction_handler = gevent.spawn(transaction_handler, self)

        # set entity id in MIB
        self.mib.local_entity_id = entity_id

        # temporary list for holding PDUs that have been read from file
        self.received_pdu_files = []

    def connect(self):
        """Connect with TC here"""
        self._socket = gevent.socket.socket()

        # Connect to localhost:8000 for now
        try:
            self._socket.connect(('127.0.0.1', 8000))
            print 'Connected', self._socket
        except socket.error as e:
            raise e

    def disconnect(self):
        """Disconnect TC here"""
        self._socket.close()
        self._receiving_handler.kill()
        self._sending_handler.kill()

    def _increment_tx_counter(self):
        self.transaction_counter += 1
        return self.transaction_counter

    def send(self, pdu):
        logging.debug('Adding pdu ' + str(pdu) + ' to queue')
        self.outgoing_pdu_queue.put(pdu)

    def put(self, destination_id, source_path, destination_path, transmission_mode=None):
        """
        Initiates a Put request by invoking Transaction Start procedures and Copy File procedures
        Other parameters not yet implemented:
            - segmentation control
            - fault handler overrides
            - flow label
            - messages to user
            - filestore requests
        """
        # Do some file checks before starting anything
        if source_path.startswith('/'):
            logging.error('Source path should be a relative path.')
            return
        if destination_path.startswith('/'):
            logging.error('Destination path should be a relative path.')
            return
        # Files should be located in path specified in settings
        full_source_path = os.path.join(settings.OUTGOING_PATH, source_path)
        if not os.path.isfile(full_source_path):
            logging.error('Source file does not exist: {}'.format(full_source_path))
            return

        # (A) Transaction Start Notification Procedure
        #  1. Issue Tx ID sequentially
        transaction_num = self._increment_tx_counter()

        # (B) Copy File Procedure
        # Determine transmission mode so we know what kind of machine to make
        # Use destination id to get the default MIB setting for that entity id
        if transmission_mode is None:
            transmission_mode = self.mib.transmission_mode(destination_id)

        # Create a `Request` which contains all the parameters for a Put.request
        # This is passed to the machine to progress the state
        request = create_request_from_type(RequestType.PUT_REQUEST,
                          destination_id=destination_id,
                          source_path=full_source_path,
                          destination_path=destination_path,
                          transmission_mode=transmission_mode)
        # if transmission_mode == TransmissionMode.ACK:
        #     machine = Sender2(self, transaction_num, request=request)
        # else:
        machine = Sender1(self, transaction_num)
        # Send the Put.request `Request` to the newly created machine
        # This is where the rest of the Put request procedures are done
        machine.update_state(event=Event.RECEIVED_PUT_REQUEST, request=request)
        # Add transaction to list, indexed by Tx #
        self._machines[transaction_num] = machine

    def report(self, transaction_id):
        """Report.request -- user request for status report of transaction"""
        request = create_request_from_type(RequestType.REPORT_REQUEST, transaction_id=transaction_id)
        machine = self._machines.get(transaction_id, None)
        if machine is None:
            # TODO error
            pass
        else:
            machine.update_state(event=Event.RECEIVED_REPORT_REQUEST, request=request)

    def cancel(self, transaction_id):
        """Cancel.request -- user request to cancel transaction"""
        request = create_request_from_type(RequestType.CANCEL_REQUEST, transaction_id=transaction_id)
        machine = self._machines.get(transaction_id, None)
        if machine is None:
            # TODO error
            pass
        else:
            machine.update_state(event=Event.RECEIVED_CANCEL_REQUEST, request=request)

    def suspend(self, transaction_id):
        """Suspend.request -- user request to suspend transaction"""
        request = create_request_from_type(RequestType.SUSPEND_REQUEST, transaction_id=transaction_id)
        machine = self._machines.get(transaction_id, None)
        if machine is None:
            # TODO error
            pass
        else:
            machine.update_state(event=Event.RECEIVED_SUSPEND_REQUEST, request=request)

    def resume(self, transaction_id):
        """Resume.request -- user request to resume transaction"""
        request = create_request_from_type(RequestType.RESUME_REQUEST, transaction_id=transaction_id)
        machine = self._machines.get(transaction_id, None)
        if machine is None:
            # TODO error
            pass
        else:
            machine.update_state(event=Event.RECEIVED_RESUME_REQUEST, request=request)

def read_pdus(instance):
    while True:
        gevent.sleep(0)
        try:
            # logging.debug('Looking for PDUs to read with entity id ' + str(instance.mib.get_local_entity_id()))
            for pdu_filename in os.listdir(settings.PDU_PATH):
                if pdu_filename.startswith(instance.mib.local_entity_id + '_'):
                    if pdu_filename not in instance.received_pdu_files:
                        # cache file so that we know we read it
                        instance.received_pdu_files.append(pdu_filename)
                        # add to incoming so that receiving handler can deal with it
                        pdu_full_path = os.path.join(settings.PDU_PATH, pdu_filename)
                        logging.debug('Possible file ' + pdu_filename)
                        with open(pdu_full_path, 'rb') as pdu_file:
                            # add raw file contents to incoming queue
                            pdu_file_bytes = pdu_file.read()
                            instance.incoming_pdu_queue.put(pdu_file_bytes)
                        break
        except Exception as e:
            pass
            # logging.debug("EXCEPTION: " + e.message)
            # logging.debug(traceback.format_exc())
        gevent.sleep(2)


def receiving_handler(instance):
    """
    GREENLET: Handles routing of incoming PDUs
    :param instance: CFDP instance
    :return:
    """

    # For now, read PDUs from ROOT directory and route to transactions
    while True:
        gevent.sleep(0)
        try:
            # data = instance._socket.recv(8)
            # print "Current Data:", data

            pdu_bytes = instance.incoming_pdu_queue.get(block=False)
            pdu = read_incoming_pdu(pdu_bytes)
            logging.debug('Incoming PDU Type: ' + str(pdu.header.pdu_type))

            transaction_num = pdu.header.transaction_id
            machine = instance._machines[transaction_num] if transaction_num in instance._machines else None

            if pdu.header.pdu_type == Header.FILE_DATA_PDU:
                # If its file data we'll concat to file
                logging.debug('Received File Data Pdu')
                if machine is None:
                    logging.debug(
                        'Ignoring File Data for transaction that doesn\'t exist: {}'.format(transaction_num))
                else:
                    # Restart inactivity timer here when PDU is being given to a machine
                    machine.inactivity_timer.restart()
                    machine.update_state(Event.RECEIVED_FILEDATA_PDU, pdu=pdu)
            elif pdu.header.pdu_type == Header.FILE_DIRECTIVE_PDU:
                logging.debug('Received File Directive Pdu: ' + str(pdu.file_directive_code))
                if pdu.file_directive_code  == FileDirective.METADATA:
                    # If machine doesn't exist, create a machine for this transaction
                    transmission_mode = pdu.header.transmission_mode
                    if machine is None:
                        # if transmission_mode == TransmissionMode.NO_ACK:
                        machine = Receiver1(instance, transaction_num)
                        instance._machines[transaction_num] = machine

                    machine.update_state(Event.RECEIVED_METADATA_PDU, pdu=pdu)
                elif pdu.file_directive_code  == FileDirective.EOF:
                    if machine is None:
                        logging.debug('Ignoring EOF for transaction that doesn\'t exist: {}'.format(transaction_num))
                    else:
                        logging.debug('Received EOF with checksum: {}'.format(pdu.file_checksum))
                        machine.update_state(Event.RECEIVED_EOF_NO_ERROR_PDU, pdu=pdu)
        except gevent.queue.Empty:
            pass
        except Exception as e:
            logging.debug("EXCEPTION: " + e.message)
            logging.debug(traceback.format_exc())
        gevent.sleep(1)


def read_incoming_pdu(pdu):
    # Transform into bytearray because that is how we wrote it out
    # Will make it an array of integer bytes
    pdu_bytes = [b for b in bytearray(pdu)]
    return make_pdu_from_bytes(pdu_bytes)


def write_outgoing_pdu(pdu, pdu_filename=None, output_directory=settings.PDU_PATH):
    """
    Temporary fcn to write pdu to file, in lieu of sending over some TC
    :param pdu:
    :param destination_id:
    :return:
    """
    # encode pdu to bits or something and deliver
    # in actuality, for now we will just write to file
    pdu_bytes = pdu.to_bytes()
    # make a filename of destination id + time
    if pdu_filename is None:
        pdu_filename = pdu.header.destination_entity_id + '_' + str(int(time.time())) + '.pdu'
    pdu_file_path = os.path.join(output_directory, pdu_filename)
    logging.debug('PDU file path ' + str(pdu_file_path))
    # https://stackoverflow.com/questions/17349918/python-write-string-of-bytes-to-file
    # pdu_bytes is an array of integers that need to be converted to hex
    write_pdu_to_file(pdu_file_path, bytearray(pdu_bytes))


def sending_handler(instance):
    """
    GREENLET: Handles sending PDUs over UT layer
    :param instance: CFDP instance
    :return:
    """
    # For now, write PDUs to ROOT directory
    while True:
        gevent.sleep(0)
        try:
            pdu = instance.outgoing_pdu_queue.get(block=False)
            logging.debug('Got PDU from outgoing queue: ' + str(pdu))
            write_outgoing_pdu(pdu)
            logging.debug('PDU transmitted: ' + str(pdu))
        except gevent.queue.Empty:
            pass
        except Exception as e:
            logging.debug('Sending handler exception: ' + e.message)
            logging.debug(traceback.format_exc())
        gevent.sleep(1)


def transaction_handler(instance):
    while True:
        gevent.sleep(0)
        try:
            # Loop through once to prioritize sending file directives
            # Check is inactivity timer expired. Later add ack/nak timers
            for trans_num, machine in instance._machines.items():
                if hasattr(machine, 'inactivity_timer') and machine.inactivity_timer is not None \
                        and machine.inactivity_timer.expired():
                    machine.inactivity_timer.cancel()
                    machine.update_state(Event.INACTIVITY_TIMER_EXPIRED)
                elif machine.role != Role.CLASS_1_RECEIVER:
                    # Let 1 file directive go per machine. R1 doesn't output PDUs
                    machine.update_state(Event.SEND_FILE_DIRECTIVE)

            # Loop again to send file data
            for trans_num, machine in instance._machines.items():
                if machine.role == Role.CLASS_1_SENDER:
                    machine.update_state(Event.SEND_FILE_DATA)
        except:
            pass
        # Evaluate every 3 sec
        gevent.sleep(3)

