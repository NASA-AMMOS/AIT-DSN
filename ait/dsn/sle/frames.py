# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
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
from typing import Any

from ait.dsn.sle.util import *
from enum import Enum
import ait

class BaseTransferFrame(dict):
    ''' Transfer Frame interface "base" class

    The BaseTransformFrame class provides Transfer Frame interface-agnostic methods
    and attributes for interfacing with Frames.
    '''

    def __init__(self, data=None):
        super(BaseTransferFrame, self).__init__()

        self._data = []
        self.is_idle = False
        self.has_no_pkts = False

    @property
    def virtual_channel(self):
        ''' Returns Virtual Channel ID (integer) '''
        if 'virtual_channel_id' in self:
            return self['virtual_channel_id']
        else:
            return None

    @property
    def master_channel_id(self):
        ''' Returns Master Channel ID (integer) '''
        if 'master_channel_id' in self:
            return self['master_channel_id']
        else:
            return None

    def contains_data(self):
        ''' Returns True if frame contains data, False otherwise

        Returns:
            Boolean value indicating if frame contains data
        '''
        if self.is_idle or self.has_no_pkts:
            return False
        if len(self._data) == 0:
            return False
        return True

    @property
    def data_field(self):
        ''' Returns the data portion of the transfer frame.

        :return: The frame data portion, including potential inner-dataframe headers
        '''
        if self.contains_data():
            return self._data[0]
        else:
            return None

    @property
    def is_idle_frame(self):
        ''' Returns True if this frame is an Idle frame, as indicated by
         the special Idle virtual channel ID, False otherwise.
         (Note: This is different from an M_PDU Idle data-field section)

        Returns:
             Boolean value indicating if this is an IDLE frame.
        '''
        return self.is_idle


class TMTransFrame(BaseTransferFrame):
    def __init__(self, data=None):
        super(TMTransFrame, self).__init__()

    def decode(self, data):
        ''' Decode data as a TM Transfer Frame '''
        self['master_channel_id'] = (hexint(data[0:2]) & 0xFFF0) >> 4  # 12 bits
        self['version'] = (hexint(data[0]) & 0xC0) >> 6  # 2 bits
        self['spacecraft_id'] = (hexint(data[0:2]) & 0x3FF0) >> 4  # 10 bits
        self['virtual_channel_id'] = (hexint(data[1]) & 0x0E) >> 1  # 1 bit
        self['ocf_flag'] = hexint(data[1]) & 0x01 # 1 bit
        self['master_chan_frame_count'] = hexint(data[2])  # 8 bits
        self['virtual_chan_frame_count'] = hexint(data[3]) # 8 bits

        self['sec_header_flag'] = (hexint(data[4:6]) & 0x8000) >> 15 #1 bit
        self['sync_flag'] = (hexint(data[4:6]) & 0x4000) >> 14  # 1 bit
        self['pkt_order_flag'] = (hexint(data[4:6]) & 0x2000) >> 13  # 1 bit
        self['seg_len_id'] = (hexint(data[4:6]) & 0x1800) >> 11   # 2 bits
        self['first_hdr_ptr'] = hexint(data[4:6]) & 0x07FF


        if str(bin(self['first_hdr_ptr'])) == '0b11111111110':
            self.is_idle = True
            return

        if str(bin(self['first_hdr_ptr'])) == '0b11111111111':
            self.has_no_pkts = True
            return

        # Process the secondary header. This hasn't been tested ...
        if self['sec_header_flag']:
            self['sec_hdr_ver'] = (hexint(data[6]) & 0xC0) >> 6
            sec_hdr_len = hexint(data[6]) & 0x3F
            sec_hdr_data = data[7:7+sec_hdr_len]
            pkt_data = data[8 + sec_hdr_len:]
        else:
            pkt_data = data[6:]

        # We're assuming that we're getting CCSDS packets w/o secondary
        # headers here. All of this needs to be fleshed out more
        while True:
            if len(pkt_data) == 0:
                break

            pkt_data_len = hexint(pkt_data[4:6])

            if pkt_data_len <= len(pkt_data[6:]):
                self._data.append(pkt_data[6:6 + pkt_data_len])

                try:
                    pkt_data = pkt_data[6 + pkt_data_len:]
                except:
                    break
            # We're not handling the case where packets are split
            # across TM frames at the moment.
            else:
                # print 'Pkt split across TM frames. AAAHHHHH!!!'
                break

    def encode(self):
        pass


class AOSDataFieldType(Enum):
    '''
    Enumeration for AOS Data Field types
    '''
    M_PDU   = "M_PDU"    # Multiplexing Protocol Data Unit
    B_PDU   = "B_PDU"    # Bitstream Protocol Data Unit
    VCA_SDU = "VCA_SDU"  # Virtual Channel Access Service Data Unit
    IDLE    = "IDLE"     # Idle data


class AOSConfig(object):
    '''
    AOS frame configuration class.

    This configuration contains information regarding the inclusion
    of optional AOS frame fields and a dictionary of virtual channel
    values to AOS data frame types.
    '''

    def __init__(self, *args, **kwargs):

        # By default the primary header is length 6
        self.primary_header_min_len = 6

        # Default index for the data field
        self.data_field_startIndex = self.primary_header_min_len
        self.data_field_endIndex   = None  # end of data array

        # -----

        # Default lengths of optional fields
        self.frame_header_error_control_len = 0
        self.transfer_frame_insert_zone_len = 0
        self.operational_control_field_len  = 0
        self.frame_error_control_field_len  = 0

        # Start and end indices for optional fields
        self.frame_header_error_control_startIndex = None
        self.frame_header_error_control_endIndex   = None
        self.transfer_frame_insert_zone_startIndex = None
        self.transfer_frame_insert_zone_endIndex   = None
        self.operational_control_field_startIndex  = None
        self.operational_control_field_endIndex    = None
        self.frame_error_control_field_startIndex  = None
        self.frame_error_control_field_endIndex    = None

        # -----

        # AIT config section prefix
        cfg_pfx = 'dsn.sle.aos.'

        # Is frame header error control included? (2-octets)
        prop_name = 'frame_header_error_control_included'
        self.frame_header_error_control_included = \
            kwargs.get(prop_name,
            ait.config.get(cfg_pfx + prop_name, False))



        if self.frame_header_error_control_included:
            self.frame_header_error_control_len = 2
            self.frame_header_error_control_startIndex = self.primary_header_min_len
            self.frame_header_error_control_endIndex   = self.primary_header_min_len + \
                                                       self.frame_header_error_control_len

        # Is transfer frame insert zone included? If so, get its non-zero len, else 0
        prop_name = 'transfer_frame_insert_zone_len'
        self.transfer_frame_insert_zone_len = \
            kwargs.get(prop_name,
                       ait.config.get(cfg_pfx + prop_name,
                                      0))

        if self.transfer_frame_insert_zone_len > 0:
            self.transfer_frame_insert_zone_startIndex = self.primary_header_min_len + \
                                                         self.frame_header_error_control_len
            self.transfer_frame_insert_zone_endIndex = self.transfer_frame_insert_zone_startIndex + \
                                                       self.transfer_frame_insert_zone_len

        # Is operation control field  included?
        prop_name = 'operational_control_field_included'
        self.operational_control_field_included = \
            kwargs.get(prop_name,
                       ait.config.get(cfg_pfx + prop_name,
                                      False))

        # Is frame error control field  included?
        prop_name = 'frame_error_control_field_included'
        self.frame_error_control_field_included = \
            kwargs.get(prop_name,
                       ait.config.get(cfg_pfx + prop_name,
                                      False))

        # Update lengths/indices based on settings

        # operation control field length is 4 bytes (if included)
        if self.operational_control_field_included:
            self.operational_control_field_len = 4

        # frame error control field is 2 bytes (if included)
        if self.frame_error_control_field_included:
            self.frame_error_control_field_len = 2

        # calculate suffix fields indices (using offsets from the end of packet)
        if self.operational_control_field_included and self.frame_error_control_field_included:
            self.operational_control_field_startIndex = -6
            self.operational_control_field_endIndex   = -2
            self.frame_error_control_field_startIndex = -2
            self.frame_error_control_field_endIndex   = None
        elif self.operational_control_field_included:
            self.operational_control_field_startIndex = -4
            self.operational_control_field_endIndex = None
        elif self.frame_error_control_field_included:
            self.frame_error_control_field_startIndex = -2
            self.frame_error_control_field_endIndex = None

        # Calculate the indices of the data field
        self.data_field_startIndex = self.primary_header_min_len + \
                                    self.frame_header_error_control_len + \
                                    self.transfer_frame_insert_zone_len
        self.data_field_endIndex = -1 * (self.operational_control_field_len +
                                     self.frame_error_control_field_len)
        # Special case where there is no trailer sections, so force 0
        # to be None so indices work correctly
        if self.data_field_endIndex == 0:
            self.data_field_endIndex = None

        ## --------

        # Collect virtual channel information, primarily the virtual channel
        # id and to what datafield type it maps

        self.vc_to_datafield_map = {}

        # Maps property names to associated enum values
        field_type_name_to_enums = {
            "m_pdu"   : AOSDataFieldType.M_PDU,
            "b_pdu"   : AOSDataFieldType.B_PDU,
            "vca_sdu" : AOSDataFieldType.VCA_SDU,
            "idle"    : AOSDataFieldType.IDLE
        }


        # Load the virtual channel map, mapping VC Ids to type.
        # First check the kwargs, then ait config, then default
        vc_map = kwargs.get('virtual_channels', None)
        if not vc_map:
            vc_aitcfg = ait.config.get('dsn.sle.aos.virtual_channels')
            ## AitConfig instance is returned for underlying YAML
            # dict types, so we need to extract the actual dict field
            # from it (named _config). Might be nice to have a property
            # method return this at some point?
            if vc_aitcfg:
                vc_map = vc_aitcfg._config
            else:
                vc_map = {}  # empty dict is the default

        # iterate over VC config entries and create dict
        # from VC id to DataField enum type
        for vc_number in vc_map:
            vc_field_str = vc_map[vc_number].lower()
            if vc_field_str in field_type_name_to_enums:
                vc_field_type = field_type_name_to_enums[vc_field_str]
                self.vc_to_datafield_map[vc_number] = vc_field_type
            else:
                err = (
                    'Virtual channel '+str(vc_number)+' is mapped to unrecognized type: '+vc_field_str+''
                    'Skipping this configuration entry...'
                )
                ait.core.log.info(err)

        # ---------------------------------------------

    def get_data_field_type(self, vc_number):
        ''' Returns the data field type associated with a virtual
            channel id.  If the virtual channel id is undeclared,
            then None is returned.
        :param vc_number: THe virtual channel id number (int)
        :return: AOSDataFieldType enum value associated with virtual channel id
        '''
        if vc_number in self.vc_to_datafield_map:
            return self.vc_to_datafield_map[vc_number]
        return None

    def get_virtual_channel_count(self):
        '''
        Returns the size of the virtual channel data field type map
        :return: size of virtual-channel data-field-type map
        '''
        return len(self.vc_to_datafield_map)

    @property
    def transfer_frame_insert_zone_included(self):
        '''
        Returns true if Transfer Frame Insert Zone field is defined in AOS Frame, false otherwise
        :return: Flag indicating Transfer Frame Insert Zone field existence
        '''
        return self.transfer_frame_insert_zone_len > 0

    def get_frame_header_error_control_indices(self):
        '''
        Returns the slice-indices for the Frame header control field if defined,
        otherwise None is returned
        :return: Frame header error control field indices or None
        '''
        if self.frame_header_error_control_included:
            return self.frame_header_error_control_startIndex, \
                   self.frame_header_error_control_endIndex
        else:
            return None, None

    def get_transfer_frame_insert_zone_indices(self):
        '''
        Returns the slice-indices for the transfer frame insert zone if defined,
        otherwise None is returned
        :return: Transfer frame insert zone indices or None
        '''
        if self.transfer_frame_insert_zone_included:
            return self.transfer_frame_insert_zone_startIndex, \
                   self.transfer_frame_insert_zone_endIndex
        else:
            return None, None

    def get_operational_control_field_indices(self):
        '''
        Returns the slice-indices for the operational control field if defined,
        otherwise None is returned
        :return: Operation control field indices or None
        '''
        if self.operational_control_field_included:
            return self.transfer_frame_insert_zone_startIndex, \
                   self.transfer_frame_insert_zone_endIndex
        else:
            return None, None

    def get_frame_error_control_field_indices(self):
        '''
        Returns the slice-indices for the frame error control field if defined,
        otherwise None is returned
        :return: Frame error control field indices or None
        '''
        if self.frame_error_control_field_included:
            return self.frame_error_control_field_startIndex, \
                   self.frame_error_control_field_endIndex
        else:
            return None, None

    def get_data_field_indices(self):
        '''
        Returns the slice-indices for the data field in AOS frame
        :return: Data field indices
        '''
        return self.data_field_startIndex, self.data_field_endIndex


class AOSTransFrame(BaseTransferFrame):
    '''
    Implementation of the AOS transfer frame.

    The AOSTransFrame class decodes data packets to extract information from header,
    data-field, and trailer.  An instance of AOSConfig guides the process by indicating
    which optional fields are included, as well as determining the type of the datafield
    via the virtual channel id.
    '''

    # Class level config for default
    defaultConfig = AOSConfig()

    def __init__(self, data=None, config=None):
        super(AOSTransFrame, self).__init__()

        # Use passed-in config or default
        if config is None:
            self.aosConfig = AOSTransFrame.defaultConfig
        else:
            self.aosConfig = config

        if data:
            self.decode(data)


    def decode(self, data):
        ''' Decode data as a AOS Transfer Frame '''
        self['master_channel_id'] = (hexint(data[0:2]) & 0xFFC0) >> 6  #10 bits
        self['version'] = (hexint(data[0]) & 0xC0) >> 6 #bits 0:1
        self['spacecraft_id'] = (hexint(data[0:2]) & 0x3FC0) >> 6 #bits 2:9
        self['virtual_channel_id'] = hexint(data[1]) & 0x3F #bits 10:15
        self['virtual_channel_frame_count'] = data[2:5]

        signaling_field = hexint(data[5])
        self['replay_flag'] = (signaling_field & 0x80)  >> 7 # 1 bit
        self['virtual_channel_frame_count_cycle_use_flag'] = (signaling_field & 0x40) >> 6  # 1 bit
        self['signal_field_reserved'] = (signaling_field & 0x30) >> 4 # 2 bits, should be '00'
        self['virtual_channel_frame_count_cycle'] = (signaling_field & 0x0F)  # 4 bits

        # check if frame header error control section is included
        if self.aosConfig.frame_header_error_control_included:
            beg_idx, end_idx = self.aosConfig.get_frame_header_error_control_indices()
            self['frame_header_error_control'] = data[beg_idx:end_idx]
        else:
            self['frame_header_error_control'] = None

        # check if transfer frame insert zone section is included
        if self.aosConfig.transfer_frame_insert_zone_included:
            beg_idx, end_idx = self.aosConfig.get_transfer_frame_insert_zone_indices()
            self['transfer_frame_insert_zone'] = data[beg_idx:end_idx]
        else:
            self['transfer_frame_insert_zone'] = None

        # Check for special IDLE virtual channel ID (0x3F indicates idle AOS transfer frames)
        if str(bin(self['virtual_channel_id'])) == '0b111111':
            self.is_idle = True
            self.has_no_pkts = True
            self['aos_data_field_type'] = None
            return

        # Per AOS documentation, if only one Virtual Channel is used, then
        # the bits are set to 'all-zeros'
        # Question: is all-zeros but more than one VCs an issue?
        if str(bin(self['virtual_channel_id'])) == '0b000000':
            if self.aosConfig.get_virtual_channel_count() == 1:
                pass
            else:
                pass  # For now just proceed

        ## Get the general data field body
        beg_idx, end_idx = self.aosConfig.get_data_field_indices()

        data_field =  data[beg_idx:end_idx]
        #self._data = data_field
        self._data.append(data_field)

        # Decode the contents of the data field
        self.decode_data_field(data_field)

        # check if operational control field is included
        if self.aosConfig.operational_control_field_included:
            beg_idx, end_idx = self.aosConfig.get_operational_control_field_indices()
            self['operational_control_field'] = data[beg_idx:end_idx]
        else:
            self['operational_control_field'] = None

        # check if frame error control field is included
        if self.aosConfig.frame_error_control_field_included:
            beg_idx, end_idx = self.aosConfig.get_frame_error_control_field_indices()
            self['frame_error_control_field'] = data[beg_idx:end_idx]
        else:
            self['frame_error_control_field'] = None


    def decode_data_field(self, datafield):
        ''' Decode the data-field section of the data, using the virtual
        channel id which indicates that data field type

        :param datafield: Data-field section of the AOS frame
        '''
        vc_key = self.virtual_channel
        vc_df_type = self.aosConfig.get_data_field_type(vc_key)

        if vc_df_type is None:
            err = (
                'AOSTransFrame received data with undeclared virtual channel ('+str(vc_key)+'). '
                'Skipping further processing of this AOS transfer frame data field...'
            )
            ait.core.log.info(err)
            pass
        elif vc_df_type == AOSDataFieldType.M_PDU:
            self.decode_dataField_MPDU(datafield)
        elif vc_df_type == AOSDataFieldType.B_PDU:
            self.decode_dataField_BPDU(datafield)
        elif vc_df_type == AOSDataFieldType.VCA_SDU:
            self.decode_dataField_VCASDU(datafield)
        elif vc_df_type == AOSDataFieldType.IDLE:
            self.decode_dataField_Idle(datafield)
        else:
            err = (
                    'AOSTransFrame received data with unknown virtual channel type (' + str(vc_df_type) + '). '
                    'Skipping further processing of this AOS transfer frame data field...'
            )
            ait.core.log.info(err)
            pass

    def decode_dataField_MPDU(self, datafield):
        ''' Decodes the M_PDU datafield

        :param datafield: AOS datafield to be decoded
        '''
        self['aos_data_field_type'] = AOSDataFieldType.M_PDU

        # M_PDU header: 5 bits reserved, 11 first header pointer: 07FF
        # Note: If all ones, then datafield does not contain a start of a packet
        self['mpdu_first_hdr_ptr'] = hexint(datafield[0:2]) & 0x07FF

        # Remaining: M_PDU packet zone
        # In general, this may contain a series of CCSDS packets,
        # but for now, someone downstream will handle processing it
        self['mpdu_packet_zone'] = datafield[2:]


        # AOS Spec 4.1.4.2.3.5 If the M_PDU Packet Zone contains only Idle Data,
        # the First Header Pointer
        # shall be set to 'all ones minus one'.
        self['mpdu_is_idle_data'] = (str(bin(self['mpdu_first_hdr_ptr'])) == '0b11111111110')

        self['mpdu_contains_idle_data'] = (str(bin(self['mpdu_first_hdr_ptr'])) == '0b11111111110')

    def decode_dataField_BPDU(self, datafield):
        ''' Decodes the B_PDU datafield

        :param datafield: AOS datafield to be decoded
         '''
        self['aos_data_field_type'] = AOSDataFieldType.B_PDU

        # B_PDU header: 2 bits reserved, 14 bitstream data pointer: 3FFF
        self['bpdu_bitstream_data_ptr'] = hexint(datafield[0:2]) & 0x3FFF

        # Remaining: B_PDU bitstream data zone
        self['bpdu_data_zone'] = datafield[2:]

        # AOS Spec 4.1.4.3.3.4 If there are no valid user data in the Bitstream
        # Data Zone (i.e., the B_PDU contains only idle data), the Bitstream
        # Data Pointer shall be set to the value 'all ones minus one'.
        self['bpdu_contains_idle_data'] = (self['bpdu_bitstream_data_ptr'] == b'11111111111110')

    def decode_dataField_VCASDU(self, datafield):
        ''' Decodes the VCA_SDU datafield

        :param datafield: AOS datafield to be decoded
        '''
        self['aos_data_field_type'] = AOSDataFieldType.VCA_SDU
        self['vcasdu_data_zone'] = datafield[None:None]

    def decode_dataField_Idle(self, datafield):
        ''' Decodes the IDLE datafield

        :param datafield: AOS datafield to be decoded
        '''
        self['aos_data_field_type'] = AOSDataFieldType.IDLE
        self['idle_data_zone'] = datafield[None:None]

    def encode(self):
        pass
