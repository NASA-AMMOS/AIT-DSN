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
import socket
import time
import traceback

import gevent
import gevent.queue
import gevent.socket

from ait.dsn.cfdp.events import Event
from ait.dsn.cfdp.machines import Receiver1, Sender1
from ait.dsn.cfdp.mib import MIB
from ait.dsn.cfdp.pdu import make_pdu_from_bytes, Header
from ait.dsn.cfdp.primitives import RequestType, TransmissionMode, FileDirective, Role, ConditionCode
from ait.dsn.cfdp.request import create_request_from_type
from ait.dsn.cfdp.util import write_to_file
from exceptions import InvalidTransaction

import ait.core
import ait.core.log


class CFDP(object):
    """CFDP processor class. Handles sending and receiving of PDUs and management of transactions.
    """

    mib = MIB(ait.config.get('dsn.cfdp.mib.path', '/tmp/cfdp/mib'))
    transaction_counter = 0
    pdu_counter = 1
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
        self.mib.load()
        self.mib.local_entity_id = entity_id

        # temporary list for holding PDUs that have been read from file
        self.received_pdu_files = []

        self._data_paths = {}
        self._data_paths['pdusink'] = ait.config.get('dsn.cfdp.datasink.pdusink.path')
        self._data_paths['outgoing'] = ait.config.get('dsn.cfdp.datasink.outgoing.path')
        self._data_paths['incoming'] = ait.config.get('dsn.cfdp.datasink.incoming.path')
        self._data_paths['tempfiles'] = ait.config.get('dsn.cfdp.datasink.tempfiles.path')

        # create needed paths if they don't exist
        for name, path in self._data_paths.iteritems():
            if not os.path.exists(path):
                os.makedirs(path)

    def connect(self, host):
        """Connect with TC here"""
        self._socket = gevent.socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Connect to localhost:8000 for now
        connected = False
        while not connected:
            try:
                self._socket.bind(host)
                ait.core.log.info('Connected to socket...')
                connected = True
            except socket.error as e:
                gevent.sleep(1)

    def disconnect(self):
        """Disconnect TC here"""
        # self._socket.close()
        self._receiving_handler.kill()
        self._sending_handler.kill()
        self.mib.dump()

    def _increment_tx_counter(self):
        self.transaction_counter += 1
        return self.transaction_counter

    def send(self, pdu):
        """Send a PDU. Adds the PDU to the outbound queue.

        Arguments:
            pdu:
                An instance of a PDU subclass (EOF, MD, etc)
        """
        ait.core.log.debug('Adding pdu ' + str(pdu) + ' to queue')
        self.outgoing_pdu_queue.put(pdu)

    def put(self, destination_id, source_path, destination_path, transmission_mode=None):
        """Initiates a Put request by invoking Transaction Start procedures and Copy File procedures

        Other parameters not yet implemented:
            - segmentation control
            - fault handler overrides
            - flow label
            - messages to user
            - filestore requests
        """
        # Do some file checks before starting anything
        if source_path.startswith('/'):
            ait.core.log.error('Source path should be a relative path.')
            return
        if destination_path.startswith('/'):
            ait.core.log.error('Destination path should be a relative path.')
            return

        # (A) Transaction Start Notification Procedure
        #  1. Issue Tx ID sequentially
        transaction_num = self._increment_tx_counter()

        # (B) Copy File Procedure
        # Determine transmission mode so we know what kind of machine to make
        # Use destination id to get the default MIB setting for that entity id
        if transmission_mode is None:
            transmission_mode = self.mib.transmission_mode(destination_id)

        if transmission_mode == TransmissionMode.ACK:
            # TODO raise invalid transmission mode since we don't support ACK right now
            pass

        # Create a `Request` which contains all the parameters for a Put.request
        # This is passed to the machine to progress the state
        request = create_request_from_type(RequestType.PUT_REQUEST,
                                           destination_id=destination_id,
                                           source_path=source_path,
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

        return transaction_num

    def ingest(self, pdu_path):
        """Ingest pdu from file
        """
        if pdu_path not in self.received_pdu_files:
            ait.core.log.debug("Ingesting PDU at path: {0}".format(pdu_path))
            # cache file so that we know we read it
            self.received_pdu_files.append(pdu_path)
            # add to incoming so that receiving handler can deal with it
            with open(pdu_path, 'rb') as pdu_file:
                # add raw file contents to incoming queue
                pdu_file_bytes = pdu_file.read()
                self.incoming_pdu_queue.put(pdu_file_bytes)

    def report(self, transaction_id):
        """Report.request -- user request for status report of transaction"""
        request = create_request_from_type(RequestType.REPORT_REQUEST, transaction_id=transaction_id)
        machine = self._machines.get(transaction_id, None)
        if machine is None:
            raise InvalidTransaction(transaction_id)
        else:
            machine.update_state(event=Event.RECEIVED_REPORT_REQUEST, request=request)

    def cancel(self, transaction_id):
        """Cancel.request -- user request to cancel transaction"""
        request = create_request_from_type(RequestType.CANCEL_REQUEST, transaction_id=transaction_id)
        machine = self._machines.get(transaction_id, None)
        if machine is None:
            raise InvalidTransaction(transaction_id)
        else:
            machine.update_state(event=Event.RECEIVED_CANCEL_REQUEST, request=request)

    def suspend(self, transaction_id):
        """Suspend.request -- user request to suspend transaction"""
        request = create_request_from_type(RequestType.SUSPEND_REQUEST, transaction_id=transaction_id)
        machine = self._machines.get(transaction_id, None)
        if machine is None:
            raise InvalidTransaction(transaction_id)
        else:
            machine.update_state(event=Event.RECEIVED_SUSPEND_REQUEST, request=request)

    def resume(self, transaction_id):
        """Resume.request -- user request to resume transaction"""
        request = create_request_from_type(RequestType.RESUME_REQUEST, transaction_id=transaction_id)
        machine = self._machines.get(transaction_id, None)
        if machine is None:
            raise InvalidTransaction(transaction_id)
        else:
            machine.update_state(event=Event.RECEIVED_RESUME_REQUEST, request=request)


def read_pdus(instance):
    """Read PDUs that have been written to file (in place of receiving over socket)
    """
    while True:
        gevent.sleep(0)
        try:
            # Get files from pdusink directory in order of creation
            pdusink_path = instance._data_paths['pdusink']
            pdu_files = [os.path.join(pdusink_path, f) for f in os.listdir(pdusink_path) if f.endswith('.pdu')]
            pdu_files.sort(key=lambda x: os.path.getmtime(x))
            for pdu_filename in pdu_files:
                if pdu_filename not in instance.received_pdu_files:
                    # cache file so that we know we read it
                    instance.received_pdu_files.append(pdu_filename)
                    # add to incoming so that receiving handler can deal with it
                    pdu_full_path = os.path.join(pdusink_path, pdu_filename)
                    with open(pdu_full_path, 'rb') as pdu_file:
                        # add raw file contents to incoming queue
                        pdu_file_bytes = pdu_file.read()
                        instance.incoming_pdu_queue.put(pdu_file_bytes)
                    break
        except Exception as e:
            ait.core.log.warn("EXCEPTION: " + e.message)
            ait.core.log.warn(traceback.format_exc())
        gevent.sleep(0.2)


def receiving_handler(instance):
    """Receives incoming PDUs on `incoming_pdu_queue` and routes them to the intended state machine instance
    """

    while True:
        gevent.sleep(0)
        try:
            pdu_bytes = instance.incoming_pdu_queue.get(block=False)
            pdu = read_incoming_pdu(pdu_bytes)
            ait.core.log.debug('Incoming PDU Type: ' + str(pdu.header.pdu_type))

            if pdu.header.destination_entity_id != instance.mib.local_entity_id:
                ait.core.log.debug('Skipping PDU with mismatched destination entity id {0}'.format(pdu.header.destination_entity_id))
                continue

            transaction_num = pdu.header.transaction_id
            machine = instance._machines[transaction_num] if transaction_num in instance._machines else None

            if pdu.header.pdu_type == Header.FILE_DATA_PDU:
                # If its file data we'll concat to file
                ait.core.log.debug('Received File Data Pdu')
                if machine is None:
                    ait.core.log.info(
                        'Ignoring File Data for transaction that doesn\'t exist: {}'.format(transaction_num))
                else:
                    # Restart inactivity timer here when PDU is being given to a machine
                    machine.inactivity_timer.restart()
                    machine.update_state(Event.RECEIVED_FILEDATA_PDU, pdu=pdu)
            elif pdu.header.pdu_type == Header.FILE_DIRECTIVE_PDU:
                ait.core.log.debug('Received File Directive Pdu: ' + str(pdu.file_directive_code))
                if pdu.file_directive_code  == FileDirective.METADATA:
                    # If machine doesn't exist, create a machine for this transaction
                    transmission_mode = pdu.header.transmission_mode
                    if machine is None:
                        # if transmission_mode == TransmissionMode.NO_ACK:
                        machine = Receiver1(instance, transaction_num)
                        instance._machines[transaction_num] = machine

                    machine.update_state(Event.RECEIVED_METADATA_PDU, pdu=pdu)
                elif pdu.file_directive_code == FileDirective.EOF:
                    if machine is None:
                        ait.core.log.info('Ignoring EOF for transaction that doesn\'t exist: {}'
                                            .format(transaction_num))
                    else:
                        if pdu.condition_code == ConditionCode.CANCEL_REQUEST_RECEIVED:
                            machine.update_state(Event.RECEIVED_EOF_CANCEL_PDU, pdu=pdu)
                        elif pdu.condition_code == ConditionCode.NO_ERROR:
                            ait.core.log.debug('Received EOF with checksum: {}'.format(pdu.file_checksum))
                            machine.update_state(Event.RECEIVED_EOF_NO_ERROR_PDU, pdu=pdu)
                        else:
                            ait.core.log.warn('Received EOF with strang condition code: {}'.format(pdu.condition_code))
        except gevent.queue.Empty:
            pass
        except Exception as e:
            ait.core.log.warn("EXCEPTION: " + e.message)
            ait.core.log.warn(traceback.format_exc())
        gevent.sleep(0.2)


def read_incoming_pdu(pdu):
    """Converts PDU binary to the correct type of PDU object

    Arguments:
        pdu:
            An encoded binary string representing a CFDP PDU
    """
    # Transform into bytearray because that is how we wrote it out
    # Will make it an array of integer bytes
    pdu_bytes = [b for b in bytearray(pdu)]
    return make_pdu_from_bytes(pdu_bytes)


def write_outgoing_pdu(pdu, pdu_filename=None, output_directory=None):
    """Helper function to write pdu to file, in lieu of sending over some other transport layer

    Arguments:
        pdu:
            An instance of a PDU subclass (EOF, MD, etc)
        pdu_filename:
            Filename to which the PDU will be written. If not specified, defaults to `<dest_entity_id>_<current_time>.pdu`
    """
    # convert pdu to bytes to "deliver", i.e. write to file
    pdu_bytes = pdu.to_bytes()

    if output_directory is None:
        ait.core.log.info(str(pdu_bytes))
        return

    if pdu_filename is None:
        # make a filename of destination id + time
        pdu_filename = str(pdu.header.destination_entity_id) + '_' + str(int(time.time())) + '.pdu'
    pdu_file_path = os.path.join(output_directory, pdu_filename)
    ait.core.log.debug('PDU file path ' + str(pdu_file_path))
    # https://stackoverflow.com/questions/17349918/python-write-string-of-bytes-to-file
    # pdu_bytes is an array of integers that need to be converted to hex
    write_to_file(pdu_file_path, bytearray(pdu_bytes))


def sending_handler(instance):
    """Handler to take PDUs from the outgoing queue and send. Currently writes PDUs to file.
    """
    while True:
        gevent.sleep(0)
        try:
            pdu = instance.outgoing_pdu_queue.get(block=False)
            pdu_filename = 'entity{0}_tx{1}_{2}.pdu'.format(pdu.header.destination_entity_id, pdu.header.transaction_id, instance.pdu_counter)
            instance.pdu_counter += 1
            ait.core.log.debug('Got PDU from outgoing queue: ' + str(pdu))
            write_outgoing_pdu(pdu, pdu_filename=pdu_filename, output_directory=instance._data_paths['pdusink'])
            ait.core.log.debug('PDU transmitted: ' + str(pdu))
        except gevent.queue.Empty:
            pass
        except Exception as e:
            ait.core.log.warn('Sending handler exception: ' + e.message)
            ait.core.log.warn(traceback.format_exc())
        gevent.sleep(0.2)


def transaction_handler(instance):
    """Handler to cycle through existing transactions and check timers or prompt sending of PDUs
    """
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
        except Exception as e:
            ait.core.log.warn("EXCEPTION: " + e.message)
            ait.core.log.warn(traceback.format_exc())
        gevent.sleep(0.2)
