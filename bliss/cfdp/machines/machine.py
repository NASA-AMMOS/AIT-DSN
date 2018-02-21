from bliss.cfdp.primitives import Role
from bliss.cfdp.pdu import Header
from bliss.cfdp.primitives import MachineState

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

    def __init__(self, entity_id, sequence_number):
        # Unique identifier for a transaction, the concatentation of entity id and the transaction sequence number
        self.entity_id = entity_id
        self.sequence_number = sequence_number

        # Other Tx properties
        self.abandoned = False
        self.cancelled = False
        self.condition_code = None  # condition code under which Tx was finished
        self.delivery_code = None  # can be Data Complete or Data Incomplete
        self.filedata_offset = None  # offset for last touched file data (either sent or received)
        self.filedata_length = None  # last length of above
        self.filedata_checksum = None
        self.finished = False
        self.frozen = False
        self.is_metadata_received = False
        self.metadata = None
        self.other_entity_id = None  # entity ID of other end of Tx
        self.machine = None  # state machine (role), e.g. S1, S2, R1, R2
        self.start_time = None
        self.suspended = None
        self.temp_file = None


class Machine(object):

    role = Role.UNDEFINED
    # state descriptors for the machine. override with appropriate descriptions in subclasses
    S1 = MachineState.SEND_METADATA
    S2 = MachineState.SEND_FILEDATA

    def __init__(self, cfdp, transaction_count):
        self.kernel = cfdp
        self.transaction = Transaction(cfdp.mib.get_local_entity_id(), transaction_count)
        self.state = self.S1

        # file to be sent or received
        self.file = None
        self.file_size = None
        self.file_checksum = None

        # header is re-used to make each PDU because values will mostly be the same
        self.header = None
        self.metadata = None

        # State machine flags
        self.pdu_was_received = False
        self.put_request_received = False
        self.eof_received = False
        self.eof_sent = False
        self.transaction_done = False
        self.transaction_cancelled = False
        self.is_ack_outgoing = False
        self.is_oef_outgoing = False
        self.is_find_outgoing = False
        self.is_metadata_outgoing = False
        self.is_nak_outgoing = False
        self.temp_file_exists = False
        self.open_file_exists = False

        # start up timers
        # Timers TODO
        pass

    def fault_handler(self, condition_code):
        """
        Fault Handler
        """
        raise NotImplementedError

    def update_state(self, event=None, pdu=None, request=None):
        """
        Evaluate a state change on received input
        :param event:
        :param pdu:
        :param request:
        :return:
        """
        raise NotImplementedError