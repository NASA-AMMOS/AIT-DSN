'''
Implements a plugin which routes AOS frames by VCID
'''
import os
import yaml
import ait

import gevent
import gevent.monkey

gevent.monkey.patch_all()

from ait.core.server.plugins import Plugin
from ait.core import log

class AOSFrameRouter(Plugin):
    '''
    Routes AOS frames by VCID according to a routing table defined by a yaml file.
    Arguments to the range operator are inclusive.
    (i.e. range[40,50] adds VCIDs 40-50 inclusive to the topic, not 40-49)
    The exclude operator must come after the range operator.

    example in config.yaml:

    - plugin:
        name: ait.dsn.plugins.vcid_routing.AOSFrameRouter
        inputs:
            - __telempkts__
        default_topic: default_AOS_topic
        routing_table: 
            path: aos_routing_table.yaml

    example routing table .yaml file:

    output_topics:
        - file_frame_handler:
            - 1
        - realtime_housekeeping_telemetry:
            - 2
            - 4
        - science_data:
            - 5
        - file_sink:
            - range:
                - 1
                - 5
            - exclude:
                - 3
        - idle_handler:
            - 63
    '''
    def __init__(self, inputs=None, outputs=None, zmq_args=None, routing_table=None, default_topic=None):
        
        super().__init__(inputs, outputs, zmq_args)

        self.default_topic = default_topic

        if 'path' in routing_table:
            self.routing_table_object = self.load_table_yaml(routing_table['path'])
        else:
            self.routing_table_object = None
            log.error("no path specified for routing table")
        if self.routing_table_object is None:
            log.error("Unable to load routing table .yaml file")

    def process(self, input_data):
        '''
        publishes incoming AOS frames to the routes specified in the routing table

        :param input_data: AOS frame as bytes
        :type input_data: bytes, bytearray 
        '''
        frame_vcid = self.get_frame_vcid(input_data)
        if frame_vcid in self.routing_table_object:
            topics = self.routing_table_object[frame_vcid]
            for route in topics:
                self.publish(input_data, route)
        else:
            log.error(f"No routes specified for VCID {frame_vcid}")

    def get_frame_vcid(self, frame):
        '''
        Returns the VCID (as integer) for a given frame (bytearray)
        Assumes that the VCID is bits 10:15

        :param frame: AOS frame as bytes
        :type frame: bytes, bytearray
        :returns: frame VCID
        :rtype: int
        '''
        vcid_bits = bytearray(b1 & b2 for b1, b2 in zip(frame[1], bytearray(b'\x3f')))
        vcid = int.from_bytes(vcid_bits, byteorder='big')
        return vcid

    def add_topic_to_table(self, routing_table, vcid, topic_name):
        '''
        Returns an updated table with the topic_name added to the entry for the specified vcid

        :param routing_table: routing table to be updated
        :param vcid: entry in routing table
        :param topic_name: topic name to add to entries in routing table
        :type routing_table: dict
        :type vcid: int
        :type topic_name: string
        :returns: updated routing table
        :rtype: dict
        '''
        temp_entry = routing_table[vcid]
        temp_entry.append(topic_name)
        routing_table[vcid] = temp_entry
        return routing_table

    def add_range_to_table(self, routing_table, range_array, topic_name):
        '''
        Adds a range of VCIDs to the routing table.
        The range_array argument is an array of form [beginning, end].
        This function is inclusive of all values.
        I.e. if range_array is [5, 9], VCIDs 5-9 inclusive will be added (not 5-8).

        :param routing_table: routing table to be updated
        :param range_array: list containing beginning and end values for entries to update
        :param topic_name: topic name to add to entry in routing table
        :type routing_table: dict
        :type range_array: list
        :type topic_name: string
        :returns: updated routing table
        :rtype: dict
        '''
        beginning = range_array[0]
        end = range_array[1]
        for vcid in range(beginning, end + 1):
            routing_table = self.add_topic_to_table(routing_table, vcid, topic_name)
        return routing_table

    def remove_from_table(self, routing_table, vcid_array, topic_name):
        '''
        Removes a topic name from all the VCIDs in the vcid_array argument.

        :param routing_table: routing table to be updated
        :param vcid_array: list containing entries to update
        :param topic_name: topic name to remove from entries in routing table
        :type routing_table: dict
        :type vcid_array: list
        :type topic_name: string
        :returns: updated routing table
        :rtype: dict
        '''
        for vcid in vcid_array:
            temp_entry = routing_table[vcid]
            if topic_name in temp_entry:
                temp_entry.remove(topic_name)
            routing_table[vcid] = temp_entry
        return routing_table

    def load_table_yaml(self, routing_table_path):
        '''
        Reads a .yaml file and returns a dictionary of format {vcid1: [streams], vcid2: [streams]}

        :param routing_table_path: path to yaml file containing routing table
        :type routing_table_path: string
        :returns: routing table
        :rtype: dict
        '''
        routing_table = {}
        error = None

        vc_config_dict = ait.config.get('dsn.sle.aos.virtual_channels')._config
        for vcid in vc_config_dict.keys():
            routing_table[vcid] = [self.default_topic]

        if routing_table_path is None:
            error = "No path specified for routing_table_path parameter"
            log.error(error)
            return None

        if os.path.isfile(routing_table_path):
            with open(routing_table_path, "rb") as stream:
                yaml_file_as_dict = yaml.load(stream, Loader=yaml.Loader)
        else:
            error = f"File path {routing_table_path} does not exist"
            log.error(error)
            return None

        for telem_stream_entry in yaml_file_as_dict["output_topics"]:
            #telem_stream_entry is a dict with one entry
            for telem_stream_name in telem_stream_entry:
                for value in telem_stream_entry[telem_stream_name]:
                    if isinstance(value, int): #assume integer value is vcid
                        vcid = value
                        routing_table = self.add_topic_to_table(routing_table, vcid, telem_stream_name)
                    elif isinstance(value, dict):
                        for operator in value:
                            if operator == "range":
                                routing_table = self.add_range_to_table(routing_table, value["range"], telem_stream_name)
                            if operator == "exclude":
                                routing_table = self.remove_from_table(routing_table, value["exclude"], telem_stream_name)
                    else:
                        log.error("Error while parsing table.yaml: encountered a value which is neither an integer nor a dictionary")

        return routing_table
