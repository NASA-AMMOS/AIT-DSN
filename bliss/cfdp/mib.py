import os
import copy
import yaml
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
    'inactivity_timeout': 30,               # inactivity time limit for a transaction
    'nak_timeout': 10,                      # time interval for NAK
    'nak_limit': 3,                        # limit on number of NAK expirations
    'maximum_file_segment_length': 128,      # in octets
}

class MIB(object):
    """Management Information Base"""

    def __init__(self):
        """Initialize MIB for a local entity"""
        # TODO allow persistence in a file
        self._local = copy.deepcopy(local_mib_fields)
        # use default values for remote entities unless specifically set
        self._remote = defaultdict(lambda : copy.deepcopy(remote_mib_fields))

    # Local getters as properties
    @property
    def local_entity_id(self):
        return self._local.get('entity_id')

    @local_entity_id.setter
    def local_entity_id(self, value):
        self._local['entity_id'] = value

    @property
    def issue_eof_sent(self):
        return self._local.get('issue_eof_sent')

    @property
    def issue_eof_recv(self):
        return self._local.get('issue_eof_recv')

    @property
    def issue_file_segment_recv(self):
        return self._local.get('issue_file_segment_recv')

    @property
    def issue_transaction_finished(self):
        return self._local.get('issue_transaction_finished')

    @property
    def issue_suspended(self):
        return self._local.get('issue_suspended')

    @property
    def issue_resumed(self):
        return self._local.get('issue_resumed')

    # Remote Getters
    def ut_address(self, entity_id):
        return self._remote[entity_id].get('ut_address')

    def ack_limit(self, entity_id):
        return self._remote[entity_id].get('ack_limit')

    def ack_timeout(self, entity_id):
        return self._remote[entity_id].get('ack_timeout')

    def inactivity_timeout(self, entity_id):
        return self._remote[entity_id].get('inactivity_timeout')

    def nak_timeout(self, entity_id):
        return self._remote[entity_id].get('nak_timeout')

    def nak_limit(self, entity_id):
        return self._remote[entity_id].get('nak_limit')

    def maximum_file_segment_length(self, entity_id):
        return self._remote[entity_id].get('maximum_file_segment_length')

    def set_local(self, parameter, value):
        # TODO verification/validation
        if parameter in self._local:
            self._local[parameter] = value

    def dump(self, path):
        """Write MIB to yaml"""
        local_file_path = os.path.join(path, 'local.yaml')
        with open(local_file_path, 'w') as mib_file:
            yaml.dump(self._local, mib_file, default_flow_style=False)

        remote_file_path = os.path.join(path, 'remote.yaml')
        with open(remote_file_path, 'w') as mib_file:
            yaml.dump(self._local, mib_file, default_flow_style=False)

    def load(self, path):
        """Write MIB to yaml"""
        local_file_path = os.path.join(path, 'local.yaml')
        with open(local_file_path, 'r') as mib_file:
            self._local = yaml.load(mib_file)

        # TODO load to defaultdict
        # remote_file_path = os.path.join(path, 'remote.yaml')
        # with open(remote_file_path, 'w') as mib_file:
        #     self._remote = yaml.load(mib_file)
