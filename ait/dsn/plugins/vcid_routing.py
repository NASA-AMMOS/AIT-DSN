'''
Implements a plugin which routes AOS frames by VCID
'''
from gevent import time, Greenlet, monkey
monkey.patch_all()
import os
import yaml
import ait
from ait.core.server.plugins import Plugin
from ait.core import log

from collections import defaultdict
from ait.dsn.sle.frames import AOSTransFrame
from ait.dsn.plugins.AOS_FEC_Check import TaggedFrame
from ait.core.message_types import MessageType


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
    def __init__(self, inputs=None, outputs=None, zmq_args=None,
                 routing_table=None, default_topic=None, report_time_s=0):
        
        super().__init__(inputs, outputs, zmq_args)

        self.report_time_s = report_time_s
        self.default_topic = default_topic
        if routing_table:
            self.path = routing_table['path']
        else:
            self.path = "No Routing Table Specified"
        if 'path' in routing_table:
            self.routing_table_object = self.load_table_yaml(self.path)
        else:
            self.routing_table_object = None
            log.error("no path specified for routing table")
        if self.routing_table_object is None:
            log.error("Unable to load routing table .yaml file")
        self.vcid_counter = defaultdict(int)

        if self.report_time_s:
            self.supervisor_glet = Greenlet.spawn(self.supervisor_tree, self.report_time_s)

    def supervisor_tree(self, report_time_s=5):
        while True:
            time.sleep(report_time_s)
            log.debug(self.vcid_counter)
            if self.vcid_counter:
                self.publish(self.vcid_counter, "monitor_vcid")
                self.publish(self.vcid_counter, MessageType.VCID_COUNT.name)

    def process(self, tagged_frame: TaggedFrame, topic=None):
        '''
        publishes incoming AOS frames to the routes specified in the routing table

        :param input_data: AOS frame as bytes
        :type input_data: bytes, bytearray 
        '''
        #frame_vcid = self.get_frame_vcid(input_data)
        frame_vcid = tagged_frame.vcid
        if frame_vcid in self.routing_table_object:
            topics = self.routing_table_object[frame_vcid]
            self.vcid_counter[frame_vcid] += 1
            tagged_frame.channel_counter = self.vcid_counter[frame_vcid]
            log.debug(f"Found routing table: "
                      f"{topics} for {tagged_frame}")
            for route in topics:
                self.publish(tagged_frame, route)
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
        vcid = AOSTransFrame(frame).virtual_channel
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
