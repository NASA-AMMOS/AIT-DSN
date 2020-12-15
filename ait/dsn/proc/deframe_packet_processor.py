#!/usr/bin/env python3

# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
#
#
# Copyright 2020, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.


from collections import defaultdict
import time
import sys
import traceback
import socket


from gevent.server import DatagramServer
import gevent.monkey; gevent.monkey.patch_all()

import ait
from ait.core import api, log, ccsds

import ait.dsn.sle.frames as frames
from ait.dsn.sle.frames import AOSTransFrame, AOSConfig, AOSDataFieldType, TMTransFrame


class Constants(object):
    """
    Class that captures the various constants used by this processor
    """
    # CCSDS header constants
    CCSDS_PRIMARY_HEADER_LEN = 6
    CCSDS_HDR_PKT_LEN_START_IDX = 4
    CCSDS_HDR_PKT_LEN_END_IDX = 6

    # SeqCount is mod'd to this value
    CCSDS_SEQCOUNT_MODULO = 16384

    # AOS FrameCount is mod'd to this value
    AOS_FRAMECOUNT_MODULO = 16777216

    # TM FrameCount is mod'd to this value
    TM_FRAMECOUNT_MODULO = 256

    # Max value allows us to perform mod-operations by default
    NO_MODULO = sys.maxsize

    # Idle TM frame first hdr ptr
    TM_FRAME_FIRST_HDR_PTR_IDLE_STR = '0b11111111110'

    # TM Frame first hdr ptr indicates no packets
    TM_FRAME_FIRST_HDR_PTR_NO_PKTS_STR = '0b11111111111'

    # Binary-String of the Idle APID
    APID_IDLE_STR = '0b11111111111'

    # Heuristic for determining when a seqcount of 0 is natural sequence
    # or a reset.
    # If recently encountered counts are within the window between the decision
    # value and the MAX value, then its natural.
    # Otherwise, it will be considered a reset.
    RESET_FUZZY_DELTA = 100
    RESET_DECISION_VALUE = CCSDS_SEQCOUNT_MODULO - RESET_FUZZY_DELTA

class ModuloList(object):
    """
    Brain-child of a desperate developer to try and maintain order
    across a bounded range with modulo values.

    The main constraint is that only up to two-thirds of the bounded range is
    active, with two gatekeeper values which affect the internal state
    of this list, which is at most two lists with their own sorted order.

    The alpha list is the active list.  The beta list is used for values that
    FOLLOW the alpha list, but likely have a value less than all of the alpha
    entry values.  There, I think that makes sense?

    Ultimately, the alpha list is always 'less-than' the beta list, despite
    the actual values in those respective lists.

    Based on the incoming value to be added and internal state, we determine
    which list the value should be added to.  We also make decisions when
    to clear-out or swap internal lists, based on gatekeeper values.
    """

    def __init__(self, modulo_val):
        self._modulo_val = modulo_val
        self._alpha_value = int(self._modulo_val / 3)
        self._beta_value = 2 * self._alpha_value

        self._alpha_list = []
        self._beta_list = None

    def reset_state(self):
        if self._alpha_list:
            self._alpha_list.clear()
        if self._beta_list:
            self._beta_list.clear()
            self._beta_list = None

    def get_alpha_value(self):
        return self._alpha_value

    def get_beta_value(self):
        return self._beta_value

    def get_size(self):
        """
        Returns the total size of this instance, across
        both internal lists.
        :return: Total number
        """
        count = len(self._alpha_list)
        if self._beta_list:
            count += len(self._beta_list)
        return count

    def add_value(self, val):
        """
        Adds a value to this list, assuming it is a legal value (non-negative
        and less than modulus-field).
        :param val: Value to be added
         :return:  True if val is added, False otherwise
        """

        if val is None:
            return False

        if val > self._modulo_val or val < 0:
            return False

        target_list = None

        # This is the special logic where we need to determine
        # to which list (alpha,beta) the val should be
        # added.
        if val < self._alpha_value:
            if self._beta_list is not None:
                target_list = self._beta_list
            else:
                target_list = self._alpha_list
        # This case we check if we reached the point of advancing
        # existing beta list as the new alpha list.  Val will
        # be added to whatever is the alpha list at the end
        elif self._alpha_value <= val < self._beta_value:
            if self._beta_list is not None:
                self.clean_alpha()
                self._alpha_list = self._beta_list
                self._beta_list = None
            target_list = self._alpha_list
        # Final case where we realize we need to prep a new
        # beta list for the future.  Val will be added to
        # the existing alpha list.
        else:
            if not self._beta_list:
                self._beta_list = []
            target_list = self._alpha_list

        # Sort is easy now that cross-range sorting is handled by this
        # class
        target_list.append(val)
        target_list.sort()
        return True

    def contains_value(self, val):
        """
        Returns True if val is found in any of the internal lists
        :param val: Value to search for
        :return: True if val found, False otherwise
        """

        return val in self._alpha_list or (self._beta_list and val in self._beta_list)

    def remove_value(self, val):
        if val in self._alpha_list:
            return self._alpha_list.remove(val)
        elif val in self._beta_list:
            return self._beta_list.remove(val)
        else:
            return False

    def clean_alpha(self):
        """
        Utility method that clears the alpha list, while perform a check
        and warning if the list was non-empty.
        """
        if len(self._alpha_list) != 0:
            log.warn("ModuloList is advancing to next state but the old alpha list is non-empty "
                                 "(maybe a result of sequence count reset?)")
            self._alpha_list.clear()

    def get_next_value(self):
        """
        Returns the next in-order value from this class, using class logic.
        :return: Next value available, or None if no value available
        """
        return self._alpha_list[0] if len(self._alpha_list) > 0 else None

    def get_values_in_order(self):
        """
        Returns a new list containing all maintained values, where values are
        sorted using the class modulo sort logic.
        :return: List of values
        """
        r_list = []
        r_list += self._alpha_list
        if self._beta_list:
            r_list += self._beta_list
        return r_list


class ApidInfo(object):
    """
    A class to represent the set of CCSDS packets for a given APID.
    Packets are collected to form contiguous chunks which can then
    be emitted downstream.
    If gaps are permitted by the processor, this class will also
    keep track of situations when the gap exceeds the max, which
    forces us to jump ahead to the next available packet.
    """

    # The length of the sliding window
    DEFAULT_MAX_GAP = 100

    def __init__(self, apid, max_gap=DEFAULT_MAX_GAP):
        """
        Constructor
        :param apid: Application id, unique to this instance
        :param max_gap: Control max value, 0 indicates no packets will be skipped
        """
        self.apid = apid
        self._lastSeqCountSent = None
        self._lastEmitTime = None
        self._max_gap = max_gap

        ## When non-null, then we are in a reset-state
        self._reset_packet = None

        # Create data structures
        self._seq_counts = ModuloList(Constants.CCSDS_SEQCOUNT_MODULO)
        self._packet_dict = {}


    @staticmethod
    def get_sequence_count(packet):
        """
        Extracts the sequence count of a packet from its header
        :param packet: Packet to be inspected
        :return: packet sequence count if found, else None
        """
        if len(packet) < Constants.CCSDS_PRIMARY_HEADER_LEN:
            return None
        ccsds_hdr = ccsds.CcsdsHeader(packet[0:7])
        return ccsds_hdr.seqcount


    def should_skip_packet(self, seq_count):
        """
        Examines packet to determine if it should be skipped, mainly
        by comparing it to recent packets that have been processed.
        If configured to prevent gaps, then always returns False.
        :param seq_count:  Sequence count of the packet
        :return: True if packet should be skipped, False otherwise.
        """
        # Indicates that we will not allow any gaps, and thus no skips
        if self._max_gap == 0:
            return False

        # Case where seq_count is 'older' but has higher value compared to 'latest'
        # use the same heuristic as the ModuloList
        ##print(" last sent = " + str(self._lastSeqCountSent) + " alpha = "+str(self._seq_counts.get_alpha_value())+"; beta = "+str(self._seq_counts.get_beta_value()) )

        if self._lastSeqCountSent < self._seq_counts.get_alpha_value() and \
                seq_count > self._seq_counts.get_beta_value():
            return True
        elif self._lastSeqCountSent > self._seq_counts.get_beta_value() and \
                seq_count < self._seq_counts.get_alpha_value():
            return False
        elif seq_count < self._lastSeqCountSent:
            return True

        ## By default return False
        return False

    def get_packet(self, seq_count):
        """
        Returns packet associated with seq_count
        :param seq_count: sequence count of the packet
        :return: Associated packet if found, else None
        """
        if seq_count in self._packet_dict:
            return self._packet_dict[seq_count]
        return None

    def remove_packet(self, seq_count):
        """
        Removes packet associates with seq_count
        :param seq_count: Sequence count
        :return: True if packet was removed, False otherwise
        """

        if self._seq_counts.contains_value(seq_count):
            self._seq_counts.remove_value(seq_count)
            self._packet_dict.pop(seq_count)
            return True
        return False

    def lastSeqCountSent(self):
        """ Returns Last Sequence Count sent (integer) """
        return self._lastSeqCountSent

    def lastPacketEmitTime(self):
        """ Returns time of the most recent packet emit """
        return self._lastEmitTime

    def setLastPacketEmitTime(self, eTime):
        self._lastEmitTime = eTime

    def setLastSeqCountSent(self, sTime):
        self._lastSeqCountSent = sTime

    @staticmethod
    def mod(value):
        """Perform mod on value, using CSSDS Sequence Count max as the modulus"""
        return value % Constants.CCSDS_SEQCOUNT_MODULO

    def add_packet(self, packet):
        """
        Performs checks on the packet, such as: packet length too shot or packet
        appears to be have arrived to late, and drops it those cases.
        Also checks for whether the packet indicates a RESET, and sets state
        accordingly.
        Finally adds the packet to our internal records
        :param packet: Packet to be added
        """
        # If packet length doesn't even cover the header, then its a problem
        if len(packet) < Constants.CCSDS_PRIMARY_HEADER_LEN:
            log.error("Packet is not legal CCSDS-packet")
            return

        seq_count = ApidInfo.get_sequence_count(packet)

        # Check cases where:
        # 1) there is no lastSent,
        # 2) where the seq_count appears to be a reset
        if self._lastSeqCountSent is None:
            self._lastSeqCountSent = ApidInfo.mod(seq_count - 1)
        elif seq_count == 0 and \
                self._lastSeqCountSent  < Constants.RESET_DECISION_VALUE:
            log.warn("Received a packet with an apparent sequence count RESET (0).")
            self._reset_packet = packet

        ## The cached reset packet will be held onto while we clear out
        ## pre-existing packet
        if self._reset_packet:
            return

        # We may have received a packet AFTER we decided to skip it, so perform a check
        if self.should_skip_packet(seq_count):
            log.error("CCSDS packet with APID '"+str(self.apid)+"' and SeqCount '"+str(seq_count)+" arrived too late to process, dropping it.")
            return

        # All is well, add seq_count and packet
        self._seq_counts.add_value(seq_count)
        self._packet_dict[seq_count] = packet

        # Skip gap check if in reset state
        self.check_gap()

    def is_reset_state(self):
        return self._reset_packet is not None

    def clear_reset_state(self):

        ## if we have a cached reset packet, add it to our data structs
        ## and clear it
        if self._reset_packet:
            reset_seq_count = ApidInfo.get_sequence_count(self._reset_packet)
            self._seq_counts.add_value(reset_seq_count)
            self._packet_dict[reset_seq_count] = self._reset_packet
            self._reset_packet = None

    def check_gap(self):
        """
        If configured to allow for gaps in the sequence of packets, check
        if conditions are met such that we can skip over packets.
        """

        # Mode where we will not ever drop packets
        if self._max_gap == 0:
            return

        # We have not reached the threshold size yet
        if self._seq_counts.get_size() < self._max_gap:
            return
        else:
            self.skip_to_next_available()

    def ready_for_emit(self):
        """
        Returns True if we are ready to emit packets downstream, false
        if we are either waiting for packets and waiting for a gap to fill
        """
        if self._seq_counts.get_size() == 0:
            return False
        seq_count = self.get_ready_seq_count()
        return seq_count is not None


    def get_ready_seq_count(self):
        """
        Returns the seqcount for the packet that is ready for transmission
        This is determined by examining the value of the next seqcount
        and whether its value is 1 greater than the lastSeqCount sent
        :return: Sequence count for the packet ready for transit, or None
        """
        seq_count = self._seq_counts.get_next_value()
        prev_seq_count  = ApidInfo.mod(seq_count - 1)

        if self._lastSeqCountSent == prev_seq_count:
            return seq_count
        else:
            return None

    def skip_to_next_available(self):
        """
        Advances internal lastSeqCount to be relative to the next
        available packet, potentially jumping over gaps
        """
        seq_count = self._seq_counts.get_next_value()
        if seq_count is not None:
            self._lastSeqCountSent = ApidInfo.mod(seq_count - 1)


class PartialsLookup(object):
    """
    Maintains a lookup of start and end packet partials extracted from Frames.
    Note: The primary key is the uniqueId (Frame masterId + virtualChannelId)
    """

    # Type/Keys used for identifying partials type
    TYPE_START = 'starts'
    TYPE_END = 'ends'

    HISTORY_MAX = 1500
    HISTORY_RATIO_CLEANUP = 0.25

    DEFAULT_HOUSEKEEPING = True
    DEFAULT_MODULUS = Constants.NO_MODULO

    def __init__(self, housekeeping=DEFAULT_HOUSEKEEPING, modulus=DEFAULT_MODULUS):
        """
        Constructor
        :param housekeeping: Flag indicating if we will perform internal house-keeping
        :param modulus: Frame-specific modulo value
        """
        # The topmost dictionary for storing partials
        self._lookup = {}

        # History list contains tuples of entries so we can track
        # the order of when partials were added
        self._history = []

        # If true, when number of remaining partials exceeds an amount, perform cleanup
        self._perform_housekeeping =  housekeeping

        # Frame-specific modulus value, needed when calculating relative
        # partials indices, since previous/next partials may cross the
        # mod-boundary
        self._frame_modulus = modulus if modulus > 0 else PartialsLookup.DEFAULT_MODULUS

    def add_partial(self, primaryId, partialId, type, partial):
        """
        Adds a partial, passing in needed index values and partial type
        :param primaryId: Frame unique id
        :param partialId: Frame count associated with packet
        :param type: Partial type, START or END
        :param partial: The partial instance
        """
        # If first time seeing uniqueId add basic lookup info
        if primaryId not in self._lookup:
            temp_dict = {PartialsLookup.TYPE_START: {},
                         PartialsLookup.TYPE_END: {}}
            self._lookup[primaryId] = temp_dict

        the_dict = self._lookup[primaryId]
        inner_dict = the_dict[type]
        inner_dict[partialId] = partial

        # Add history entry
        history_entry = (primaryId, partialId, type, time.time())
        self._history.append(history_entry)


    def remove_partial(self, primaryId, partialId, type):
        """
        Removes a partial entry
        :param primaryId: Frame unique id
        :param partialId: Frame count associated with packet
        :param type: Partial type, START or END
        :return: True if partial removed, False otherwise
        """
        if primaryId not in self._lookup:
            return False
        the_dict = self._lookup[primaryId]
        inner_dict = the_dict[type]

        if partialId not in inner_dict:
            return False

        inner_dict.pop(partialId, None)

        # Remove history entry (todo smarter way to do this?)
        history_entries = [entry for entry in self._history if entry[0] == primaryId and
                           entry[1] == partialId and entry[2] == type]
        for entry in history_entries:
            self._history.remove(entry)

        return True

    def get_partial(self, primaryId, partialId, type):
        """
        Returns a partial entry
        :param primaryId: Frame unique id
        :param partialId: Frame count associated with packet
        :param type: Partial type, START or END
        :return: Partial mapped by the provided arguments, or None
        """

        if primaryId not in self._lookup:
            return None
        the_dict = self._lookup[primaryId]
        inner_dict = the_dict[type]

        if partialId not in inner_dict:
            return None

        return inner_dict[partialId]

    def contains_partial(self, primaryId, partialId, type):
        """
        Returns whether a partial is found in this instanc
        :param primaryId: Frame unique id
        :param partialId: Frame count associated with packet
        :param type: Partial type, START or END
        :return: True if partial if managed by this instance, False otherwise
        """
        if primaryId not in self._lookup:
            return False
        the_dict = self._lookup[primaryId]
        inner_dict = the_dict[type]

        if partialId not in inner_dict:
            return False

        return True


    def perform_cleanup(self):
        """
        Perform cleanup if enabled and if the number of entries
        exceeds the maximum number of entries.
        """
        if not self._perform_housekeeping:
            return

        if len(self._history) >= PartialsLookup.HISTORY_MAX:
            remove_count = int(PartialsLookup.HISTORY_MAX * PartialsLookup.HISTORY_RATIO_CLEANUP)
            log.debug("PartialsLookup is performing cleanup by removing the "+str(remove_count)+" oldest entries")
            for idx in range(remove_count):
                if idx < len(self._history):
                    entry = self._history[0]
                    self.remove_partial(entry[0],entry[1],entry[2])

    def mod(self, value):
        """
        Returns the value % frame_modulos, typically the same value except for boundary cases
        :param value: Value to be mod'd
        :return: Mod'd value
        """
        return value % self._frame_modulus

    def contains_complement_for(self, primaryId, partialId, type):
        """
        Returns True if complementary partial is being managed, False otherwise
        """
        (lookup_index, lookup_type) = PartialsLookup.get_complement_fields(partialId, type)
        return self.contains_partial(primaryId, lookup_index, lookup_type)

    def get_complement_fields(self, partialId, type):
        """
        Returns a tuple representing the complementary partial to the
        input arguments
        """
        lookup_type = PartialsLookup.TYPE_START if type == PartialsLookup.TYPE_END else PartialsLookup.TYPE_END
        lookup_index = (partialId - 1) if partialId == PartialsLookup.TYPE_END else (partialId + 1)
        lookup_index = self.mod(lookup_index)
        return (lookup_index, lookup_type)


class Processor(object):

    """
    The main class which sets up and connects components to receive incoming
    frames, deframe those into packets for collection, and sequentially emits
    packets downstream when appropriate.
    """

    def __init__(self, *args, **kwargs):

        # Frame type expected from the DSN services
        self._downlink_frame_type = ait.config.get('dsn.sle.downlink_frame_type',
                                                   kwargs.get('downlink_frame_type',
                                                              ait.DEFAULT_FRAME_TYPE))

        # Modulus associated with frame type
        self._frame_modulus = Processor.get_modulus_for_frame(self._downlink_frame_type)

        # how long do we wait for each data queue poll (seconds)
        self._timer_poll = ait.config.get('dsn.proc.timer_poll',
                                         kwargs.get('timer_poll', 15))

        # how long do we wait before forcing a cleanup session (seconds)
        self._clean_up_interval = ait.config.get('dsn.proc.cleanup_poll',
                                         kwargs.get('cleanup_pool', 300))


        # When true, the processor will assume that no packet will
        # ever be lost, and will not perform any packet dropping
        self._gap_max = ait.config.get('dsn.proc.gap_max',
                                       kwargs.get('gap_max', 100))

        # UDP Destination settings, and create output socket
        self._packet_dest_host = "localhost"
        self._packet_dest_port = ait.config.get('dsn.proc.packet_output_port',
                                         kwargs.get('packet_output_port', 3076))
        self._packet_dest = (self._packet_dest_host, self._packet_dest_port)
        self._packet_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Keep track of last time cleanup was performed
        self._last_cleanup_time = time.time()

        # Queue for incoming transfer frames
        self._frame_queue = api.GeventDeque(maxlen=1000)

        # The APID info structs registry, with apid value mapping to ApidInfo instances
        self._apid_lookup = {}

        # Partials manager, handles partials extracted from transfer frames
        t_partials_housecleaning = self._gap_max > 0
        t_frame_mod = Processor.get_modulus_for_frame(self._downlink_frame_type)
        self._partials_lookup = PartialsLookup(housekeeping=t_partials_housecleaning,
                                               modulus=t_frame_mod)

        # The AIT TMFrame parser currently makes no attempt to handle partial packets.
        # We have some code that handles either, and this flag indicates which
        # path to follow
        self._handle_tmframe_partials = False

        # Frame service (listens to incoming port and populates queue with transfer frames)
        self._frame_service = Frame_Service(self._frame_queue, **kwargs)

    @staticmethod
    def get_modulus_for_frame(frame_name):
        """
        Frame modulus value is dependent on the frame type, this
        method returns the appropriate value for a given frame name
        :param frame_name: Frame class name
        :return: Modulus value for frame class, or 0 if unknown
        """
        if not frame_name:
            return Constants.NO_MODULO
        elif frame_name == "TMTransFrame":
            return Constants.TM_FRAMECOUNT_MODULO
        elif frame_name == "AOSTransFrame":
            return Constants.AOS_FRAMECOUNT_MODULO
        else:
            return Constants.NO_MODULO

    def mod(self, value):
        return value % self._frame_modulus

    @staticmethod
    def is_aos_type_supported(aosType):
        """
        Returns True if AOS frame type is supported by the processor, False otherise
        :param aosType: AOS frame type
        :return: True if AOS type supported, False otherwise
        """
        return aosType == AOSDataFieldType.M_PDU

    def perform_cleanup_check(self):
        """
        Check if cleanup should be performed, using set time intervals
        :return: Return True if cleanup was performed, False otherwise
        """

        ## Examine if we should perform a cleanup based on time/size?
        now = time.time()
        if now - self._last_cleanup_time < self._clean_up_interval:
            return False

        self._partials_lookup.perform_cleanup()

        self._last_cleanup_time = now
        return True


    def handle_full_packet(self, packet):
        """
        Takes a full CCSDS packet and routes it to the appropriate APID record.
        If packet has IDLE apid, it is dropped.
        :param packet: CCSDS packet
        :return: True if packet as processed, False if packet was rejected
        """

        if len(packet) < Constants.CCSDS_PRIMARY_HEADER_LEN + 1:
            log.error("Received CCSDS packet that is too short. Dropping it.")
            return False

        # Get packet header and create CCSDS header
        pkt_hdr = packet[0:7]
        ccsds_hdr = ccsds.CcsdsHeader(pkt_hdr)

        apid = ccsds_hdr.apid

        # Check for Idle APID
        apid_bin_str = str(bin(apid))
        if apid_bin_str == Constants.APID_IDLE_STR:
            log.debug("Received an Idle CCSDS packet. Dropping it.")
            return False

        seq_count = ccsds_hdr.seqcount
        data_len = ccsds_hdr.length + 1

        ccsds_pkt_len = data_len + Constants.CCSDS_PRIMARY_HEADER_LEN

        if not apid in self._apid_lookup.keys():
            tmp_lookup = ApidInfo(apid, self._gap_max)
            self._apid_lookup[apid] = tmp_lookup

        apid_info = self._apid_lookup.get(apid)

        apid_info.add_packet(packet)

        ## Special Check if we should purge all packets (i.e. a RESET was sent)
        if apid_info.is_reset_state():
            self.handle_apid_reset(apid_info)


        if apid_info.ready_for_emit():
            self.process_apid_packets(apid_info)

        return True

    def handle_apid_reset(self, apid_info):
        """
        Processes all the packets that are stored in the apid_info, when we have
        run out, then we are done, and can restore the reset state, leaving the
        reset packet as the next packet to emit
        """

        if not apid_info.is_reset_state():
            return

        ## Force the ready for emit state
        apid_info.skip_to_next_available()

        while apid_info.ready_for_emit():
            next_seqcnt_to_send = apid_info.get_ready_seq_count()

            if next_seqcnt_to_send is None:
                break

            ## Process packet normally
            self.emit_apid_packet_by_seqcount(apid_info, next_seqcnt_to_send)

            ## We are in reset mode force to next available
            apid_info.skip_to_next_available()

        ## All other packets have been processed so restore the cached reset packet
        apid_info.clear_reset_state()
        apid_info.skip_to_next_available()


    def process_apid_packets(self, apid_info):
        """Process/emit sequential packets while they are available"""

        while apid_info.ready_for_emit():
            next_seqcnt_to_send = apid_info.get_ready_seq_count()
            self.emit_apid_packet_by_seqcount(apid_info, next_seqcnt_to_send)


    def emit_apid_packet_by_seqcount(self, apid_info, seqcount):
        """Given an apid info and seqcount, retrieves packet, emits and updates apid info"""

        packet = apid_info.get_packet(seqcount)
        if not packet:
            return

        apid_info.remove_packet(seqcount)
        l_now = time.time()
        apid_info.setLastPacketEmitTime(l_now)
        apid_info.setLastSeqCountSent(seqcount)

        print("Emitting CCSDS packet with APID "+str(apid_info.apid)+" and SeqCount "+str(seqcount)+" downstream")
        self.emit_packet(packet)

    def emit_packet(self, packet):
        """Pushes packet to downstream UDP socket"""
        try:
            self._packet_socket.sendto(packet, self._packet_dest)
        except socket.error as e:
            log.error("Socket error error: {0}".format(e))
        except IOError as e:
            log.error("IO error: {0}".format(e))


    def handle_partial_packet(self, uniqueId, partialId, type, partial_pkt):
        """
        Given partial, look up if complement is available.  If so, create a full
        packet and process that, updating the records in the process.  Otherwise,
        add the partial for future use.
        :param uniqueId: Id of the channel (master + virtual) for the packet
        :param partialId: Numerical id of the partial packet
        :param type: Type of the partial PartialsLookup.{TYPE_START,TYPE_END}
        :param partial_pkt: The partial packet
        """

        ## Does lookup have our counterpart?
        #if self._partials_lookup.contains_partial(uniqueId, partialId, type):

        (lookup_id, lookup_type) = self._partials_lookup.get_complement_fields(partialId, type)
        if self._partials_lookup.contains_partial(uniqueId, lookup_id, lookup_type):

            complement = self._partials_lookup.get_partial(uniqueId, lookup_id, lookup_type)
            if not complement:
                log.error("Missing expected component partial for {}-{}-{}".format(
                                   str(uniqueId),str(partialId),str(type)))
                return

            # Cleanup the lookup by removing the complement partial
            self._partials_lookup.remove_partial(uniqueId, lookup_id, lookup_type)

            #  Create the full combined packet
            if type == PartialsLookup.TYPE_START:
                full_pkt = partial_pkt + complement
            else:
                full_pkt = complement + partial_pkt

            self.handle_full_packet(full_pkt)

        else:
            # Can't create full packet, so save this partial and await its complement
            self._partials_lookup.add_partial(uniqueId, partialId, type, partial_pkt)


    def handle_frame(self, frame):
        """
        Given a frame object, determines if it is supported and if so, processes it.
        Otherwise the frame will be dropped with message indicating such.
        :param frame: Frame object
        """
        if isinstance(frame, frames.AOSTransFrame):
            self.handle_aos_frame(frame)
        elif isinstance(frame, frames.TMTransFrame):
            self.handle_tm_frame(frame)
        else:
            frame_class = frame.__class__.__name__
            log.warn("Received frame with unsupported type '"+frame_class+"', dropping it.")
            return

    def handle_aos_frame(self, aos_frame):
        """
        AOS Frame handling, checks that frame is support, then grabs needed
        header information to process it.
        :param aos_frame: AOS Frame
        :return: True of AOS frame was processed, False otherwise
        """

        # Currently only support MPDU types
        aos_type = aos_frame['aos_data_field_type']
        if aos_type != AOSDataFieldType.M_PDU:
            log.debug("Processor only handles AOS frames of type M_PDU. "
                               "Dropping frame of type "+str(aos_type))
            return False

        # Create the unique ID by combining master + virtual channel id
        frame_id = str(aos_frame.master_channel_id) + '-' + str(aos_frame.virtual_channel)

        # Retrieve frame count
        frame_ct_bytes = aos_frame['virtual_channel_frame_count']
        frame_ct = int.from_bytes(frame_ct_bytes, byteorder='big')

        pkt_hdr_ptr = aos_frame['mpdu_first_hdr_ptr']
        pkt_zone = aos_frame['mpdu_packet_zone']
        pkt_zone_end = len(pkt_zone)

        # These are the partial IDs relative to our frame count
        previous_partial_id = self.mod(frame_ct - 1)
        next_partial_id = self.mod(frame_ct + 1)

        current_start_idx = 0
        current_end_idx = None


        # Indicates an 'end' partial (missing its beginning)
        if pkt_hdr_ptr != 0:
            previous_partial = pkt_zone[0:pkt_hdr_ptr]

            self.handle_partial_packet(frame_id, previous_partial_id,
                                       PartialsLookup.TYPE_END, previous_partial)

        # Init start index
        current_start_idx = pkt_hdr_ptr

        # Iterate while start index less than end of packet zone
        while current_start_idx < pkt_zone_end:

            # Determine if next available is full packet or partial
            (pkt_length, pkt_is_partial) = self.examine_next_cssds_packet(pkt_zone, current_start_idx)

            # Indicates a 'start' partial (missing its ending)
            if pkt_is_partial:
                next_partial = pkt_zone[current_start_idx:pkt_zone_end]
                self.handle_partial_packet(frame_id, next_partial_id,
                                           PartialsLookup.TYPE_START, next_partial)
                current_start_idx = pkt_zone_end
            else:
                current_end_idx = current_start_idx + pkt_length
                current_packet = pkt_zone[current_start_idx:current_end_idx]

                self.handle_full_packet(current_packet)

                # Alert partials lookup of this full packet (supports cleanup)
                # self._partials_lookup.set_last_full_frame_count(frame_id, frame_ct)

                current_start_idx += pkt_length

        return True


    def handle_tm_frame(self, tm_frame):
        """
        TM Frame handling, checks that frame is supported, then grabs needed
        header information to process it.
        :param tm_frame: TM Frame instance
        :return: True if TM frame was processed, False otherwise
        """

        # Create the unique ID by combining master + virtual channel id
        frame_id = tm_frame.master_channel_id + tm_frame.virtual_channel

        # Retrieve frame count
        frame_ct = tm_frame['virtual_chan_frame_count']

        pkt_hdr_ptr = tm_frame['first_hdr_ptr']
        pkt_hdr_ptr_str = str(bin(pkt_hdr_ptr))

        if pkt_hdr_ptr_str == Constants.TM_FRAME_FIRST_HDR_PTR_IDLE_STR:
            log.debug("Processor received IDLE TM frame, dropping it.")
            return False
        elif pkt_hdr_ptr_str == Constants.TM_FRAME_FIRST_HDR_PTR_NO_PKTS_STR:
            log.debug("Processor received TM frame with no packets, dropping it.")
            return False


        ## Currently, TMFrame handles the breakup of packets internally
        ## So processing here will differ from AOS where we have to
        ## get the CCSDS packets ourselves
        pkt_array = tm_frame._data
        pkt_array_len = 0 if not pkt_array else len(pkt_array)

        if pkt_array_len == 0:
            return False

        if not self._handle_tmframe_partials:
            for current_packet in pkt_array:
                self.handle_full_packet(current_packet)
        else:

            ## These are the partial IDs relative to our frame count
            previous_partial_id = self.mod(frame_ct - 1)
            next_partial_id = self.mod(frame_ct + 1)

            ## Assume first packet is complete
            current_pkt_idx = 0
            last_pkt_idx = pkt_array_len - 1

            ## Indicates an 'end' partial (missing its beginning)
            if pkt_hdr_ptr != 0:
                previous_partial = pkt_array[0]
                self.handle_partial_packet(frame_id, previous_partial_id,
                                           PartialsLookup.TYPE_END, previous_partial)
                ## First full packet at index 1
                current_pkt_idx = 1

            ## Process the full packets
            for index in range(current_pkt_idx, last_pkt_idx):
                current_packet = pkt_array[index]
                self.handle_full_packet(current_packet)

            ## Last packet might be partial, might be complete.
            ## Check and handle appropriately
            last_packet = pkt_array[last_pkt_idx]
            (pkt_length, pkt_is_partial) = self.examine_next_cssds_packet(last_packet, 0)
            if pkt_is_partial:
                self.handle_partial_packet(frame_id, next_partial_id,
                                           PartialsLookup.TYPE_START, last_packet)
            else:
                self.handle_full_packet(last_packet)

        return True

    def examine_next_cssds_packet(self, bytes, start_idx):
        """
        Helper method that examines a set of bytes from the 'bytes' starting
        from start_idx and determines if the full packet can be extracted or
        of only a partial exists.
        :param bytes: A byte array
        :param start_idx: Start index of the potential packet
        :return: Tuple capturing 1) the affected packets length and 2) if it is a partial
        """

        ccsds_pkt_len = None
        ccsds_pkt_partial = False

        total_bytes = len(bytes)

        len_start_idx = start_idx + Constants.CCSDS_HDR_PKT_LEN_START_IDX  #inclusive
        len_end_idx = start_idx + Constants.CCSDS_HDR_PKT_LEN_END_IDX    #non-inclusive

        if len_end_idx > total_bytes:
            ccsds_pkt_partial = True
        else:
            pkt_len_bytes = bytes[len_start_idx:len_end_idx]
            pkt_len = int.from_bytes(pkt_len_bytes, byteorder='big') + 1
            ccsds_pkt_len = pkt_len + Constants.CCSDS_PRIMARY_HEADER_LEN
            if (start_idx + ccsds_pkt_len) > total_bytes:
                ccsds_pkt_partial = True

        rtn_val = (ccsds_pkt_len, ccsds_pkt_partial)
        return rtn_val


    def run(self):
        """
        The entry point of the processor.  Starts the frame service to accept incoming
        frames and checks queue for available results.  If timeout occurs with no
        results, a cleanup check if performed
        """
        self._frame_service.start()

        while not self._frame_service.closed:
            try:
                log.debug("Polling frame queue...")
                frame, timestamp = self._frame_queue.popleft(timeout=self._timer_poll)

                if frame is not None:
                    self.handle_frame(frame)

            except IndexError:
                # If no frame has been received by the serice
                # server after timeout seconds, perform a cleanup
                # check.
                clean_msg = "Frame queue is empty, performing cleanup check."
                log.debug(clean_msg)
                print(clean_msg)

                self.perform_cleanup_check()

        ait.info("Incoming-frame service is now closed.")

    def stop(self):
        """
        Stops and closes the frame service
        """
        if self._frame_service:
            self._frame_service.stop()
            self._frame_service.close()

class Frame_Service(DatagramServer):
    """
  	UDP Datagram server that handles incoming messages TMFrames/AOSFrames from frame
  	output port of the upstream service (AIT DSN RAF/RCF server?)
   	"""
    def __init__(self, framequeue, *args, **kwargs):
        """
        Constructor
        :param framequeue: The frame queue to which frames from ports will be added
        :param args: Arguments
        :param kwargs: Keyword arguments
        """

        self._frame_queue = framequeue

        # Incoming port for the frames from DSN services
        self._listening_host = '127.0.0.1'
        self._listening_port = int(ait.config.get('dsn.sle.frame_output_port',
                                                    kwargs.get('frame_output_port',
                                                               ait.DEFAULT_FRAME_PORT)))

        # Frame type expected from the DSN services
        self._downlink_frame_type = ait.config.get('dsn.sle.downlink_frame_type',
                                                   kwargs.get('downlink_frame_type',
                                                              ait.DEFAULT_FRAME_TYPE))

        # Grab the class from frames only once
        self._tm_frame_class = getattr(frames, self._downlink_frame_type)

        # Inform server of the address to listen
        listener = (self._listening_host, self._listening_port)
        super(Frame_Service, self).__init__(listener)

    def handle(self, data, address):
        """
        This handler is called whenever a message is received by the DatagramServer;
        capturing that message data and putting it into the field queue for downstream
        processing
        :param data: The data of the message received
        :param address: The address that sent the message
        """

        in_frame = self._tm_frame_class(data)

        # Add any frame-based logic/decisions here
        if in_frame.is_idle_frame:
            log.debug('Dropping {} marked as an idle frame'.format(self._tm_frame_class))
            return

        self._frame_queue.append( ( in_frame, ( int(time.time())) ) )

    def start(self):
        """Starts this Frame_Service."""
        values = self._downlink_frame_type, self._listening_host, self._listening_port
        log.info('Listening for %s frames on %s:%d (UDP)' % values)
        super(Frame_Service, self).start()

    def stop(self):
        """Stop this Frame_Service."""
        values = self._downlink_frame_type, self._listening_host, self._listening_port
        log.info('Stop listener for %s frames on %s:%d (UDP)' % values)
        super(Frame_Service, self).stop(timeout=5)

if __name__ == '__main__':

    processor = Processor()
    try:
        processor.run()
        while True:
            ait.core.log.info('Sleeping...')
            gevent.sleep(1)
    except KeyboardInterrupt:
        print('Disconnecting...')
    except Exception as e:
        print(traceback.print_exc())
    finally:
        processor.stop()
        time.sleep(2)
