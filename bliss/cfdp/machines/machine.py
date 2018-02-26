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

from bliss.cfdp.primitives import Role, MachineState, FinalStatus, IndicationType

import logging

class ID(object):
    """
    CFDP entity ID. Unsigned binary integer
    Entity ID length is 3 bits, value can be up to 8 octets (bytes) long
    Entity ID is packed in PDUs by octet length less 1 (e.g. 0 for 1 octet length)
    """

    # TODO figure out 3 bit length, 8 byte value restriction
    def __init__(self, length, value):
        # store raw value
        self._length = length
        self._value = value

    @property
    def length(self):
        return self._length

    @length.setter
    def length(self, l):
        if not l: raise ValueError('length cannot be empty')
        if l > 8:
            raise ValueError('id length cannot exceed 8 bytes')
        self._length = l

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        if not v: raise ValueError('value cannot be empty')
        self._value = v


class Transaction(object):

    def __init__(self, entity_id, transaction_id):
        # Unique identifier for a transaction, the concatentation of entity id and the transaction sequence number
        self.entity_id = entity_id
        self.transaction_id = transaction_id

        # Other Tx properties
        self.abandoned = False
        self.cancelled = False
        self.condition_code = None  # condition code under which Tx was finished
        self.delivery_code = None  # can be Data Complete or Data Incomplete
        self.filedata_offset = None  # offset for last touched file data (either sent or received)
        self.filedata_length = None  # last length of above
        self.filedata_checksum = None
        self.final_status = None
        self.finished = False
        self.frozen = False
        self.is_metadata_received = False
        self.metadata = None
        self.other_entity_id = None  # entity ID of other end of Tx
        self.start_time = None
        self.suspended = False

        self.recv_file_size = 0
        self.file_checksum = None


class Machine(object):

    role = Role.UNDEFINED
    # state descriptors for the machine. override with appropriate descriptions in subclasses
    S1 = MachineState.SEND_METADATA
    S2 = MachineState.SEND_FILEDATA

    def __init__(self, cfdp, transaction_id, *args, **kwargs):
        self.kernel = cfdp
        self.transaction = Transaction(cfdp.mib.local_entity_id, transaction_id)
        self.state = self.S1

        # Set up fault and indication handlers
        self.indication_handler = kwargs.get('indication_handler', self._indication_handler)
        self.fault_handler = kwargs.get('fault_handler', self._fault_handler)

        # Open file being sent or received (final file, not temp)
        self.file = None
        # Path of source or destination file (depending on role)
        self.file_path = None

        # Open temp file for receiving file data
        self.temp_file = None
        self.temp_path = None

        # header is re-used to make each PDU because values will mostly be the same
        self.header = None
        self.metadata = None
        self.eof = None

        # State machine flags
        self.pdu_received = False
        self.put_request_received = False
        self.eof_received = False
        self.eof_sent = False
        self.transaction_done = False
        self.transaction_cancelled = False
        self.is_ack_outgoing = False
        self.is_oef_outgoing = False
        self.is_fin_outgoing = False
        self.is_md_outgoing = False
        self.is_nak_outgoing = False
        self.is_shutdown = False

        self.inactivity_timer = None
        self.ack_timer = None
        self.nak_timer = None

    def _indication_handler(self, indication_type, *args, **kwargs):
        """
        Default indication handler, which is just to log a message
        Indication type is primitive type `IndicationType`
        """
        logging.info('INDICATION: ' + str(indication_type))

    def _fault_handler(self, fault_type, *args, **kwargs):
        """
        Default fault handler, which is just to log a message
        Fault type is primitive type `ConditionCode`
        """
        logging.info('FAULT: ' + str(fault_type))

    def update_state(self, event=None, pdu=None, request=None):
        """
        Evaluate a state change on received input
        :param event:
        :param pdu:
        :param request:
        :return:
        """
        raise NotImplementedError

    def cancel(self):
        self.is_oef_outgoing = False
        self.is_ack_outgoing = False
        self.is_fin_outgoing = False
        self.is_md_outgoing = False
        self.is_nak_outgoing = False

        self.transaction.cancelled = True

        if self.inactivity_timer:
            self.inactivity_timer.cancel()
        if self.ack_timer:
            self.ack_timer.cancel()
        if self.nak_timer:
            self.nak_timer.cancel()

    def finish_transaction(self):
        """Closes out a transaction. Sends the appropriate Indication and resets instance variables"""
        logging.debug("Machine {} finishing transaction...".format(self.transaction.transaction_id))
        self.is_oef_outgoing = False
        self.is_ack_outgoing = False
        self.is_fin_outgoing = False
        self.is_md_outgoing = False
        self.is_nak_outgoing = False

        if self.inactivity_timer:
            self.inactivity_timer.cancel()
        if self.ack_timer:
            self.ack_timer.cancel()
        if self.nak_timer:
            self.nak_timer.cancel()

        self.transaction.finished = True
        if self.role == Role.CLASS_1_RECEIVER and not self.transaction.is_metadata_received:
            self.transaction.final_status = FinalStatus.FINAL_STATUS_NO_METADATA
        elif self.transaction.cancelled:
            self.transaction.final_status = FinalStatus.FINAL_STATUS_CANCELLED
        else:
            self.transaction.final_status = FinalStatus.FINAL_STATUS_SUCCESSFUL

        self.indication_handler(IndicationType.TRANSACTION_FINISHED_INDICATION,
                                transaction_id=self.transaction.transaction_id)

    def shutdown(self):
        logging.debug("Machine {} shutting down...".format(self.transaction.transaction_id))
        if self.file is not None and not self.file.closed:
            self.file.close()
            self.file = None

        if self.temp_file is not None and not self.temp_file.closed:
            self.temp_file.close()
            self.temp_file = None
        # If transaction was unsuccesful, delete tmp file

        # TODO issue Tx indication (finished, abandoned, etc)

        self.transaction.finish = True
        self.is_shutdown = True