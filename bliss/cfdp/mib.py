import copy
from collections import defaultdict
# Default MIB values

local_mib_fields = {
    # local entity id
    'entity_id': 1,
    # Indication flags (whether or not to send)
    'issue_eof_sent': True,
    'issue_eof_recv': False,
    'issue_file_segment_recv': False,
    'issue_transaction_finished': False,
    'issue_suspended': True,
    'issue_resumed': True,
    # Default handlers
    'handlers': []
}

# Remote entity id stored by id
remote_mib_fields = {
    'entity_id': None,                        # remote entity id
    'ut_address': None,                       # UT address for transmitting to this remote entity
    'ack_limit': 3,                        # positive ack count limit (number of expirations)
    'ack_timeout': 10,                      #
    'inactivity_timeout': 10,               # inactivity time limit for a transaction
    'nak_timeout': 10,                      # time interval for NAK
    'nak_limit': 3,                        # limit on number of NAK expirations
    'maximum_file_segment_length': 100,      # in octets
}

class MIB(object):
    """Management Information Base"""

    def __init__(self):
        """Initialize MIB for a local entity"""
        # TODO allow persistence in a file
        self.local = copy.deepcopy(local_mib_fields)
        # use default values for remote entities unless specifically set
        self.remote = defaultdict(lambda : copy.deepcopy(remote_mib_fields))

    def get_local_entity_id(self):
        return self.local['entity_id']

    def set_local_entity_id(self, entity_id):
        self.local['entity_id'] = entity_id
