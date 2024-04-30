"""
Implements a plugin which converts 0158-Monitor telemetry packets
into lists of channel-measurement dictionaries.

NOTE: This plugin was refactored from an original implementation
      provided by the SunRise AIT development team.

      At the time of initial submission to AIT-DSN, there has been
      no testing performed.  We expect another team which requested
      this plugin to be included to perform its testing and provide
      feedback as necessary.
"""

from ait.core.server.plugins import Plugin
from ait.core import log
import socket
from bitstring import BitArray
from enum import Enum
import xmltodict
from functools import reduce
import traceback as tb


class Monitor_Channel:
    """
    Captures the monitor channel definition as well as functionality
    to convert raw bytes to typed values.  The internal value is updated
    with every call to decode(), while canonical_map() returns a
    dictionary of the definition and value for transmission downstream
    """
    def __init__(self, abbreviation, name, data_type, source,
                 byte_length, measurement_id,
                 title, description, categories, enum_def=None):

        self.value = None
        self.abbreviation = abbreviation
        self.name = name
        self.data_type = data_type
        self.source = source
        self.byte_length = byte_length
        self.measurement_id = measurement_id
        self.title = title
        self.description = description
        self.categories = categories
        self.enum_def = enum_def

    def __repr__(self):
        return str(self.__dict__)

    def decode(self, val_bytes):
        """
        Converts raw val_bytes to actual value based on the data_type
        :param val_bytes: Input value as bytes
        :return: Converted value, or None if error occurred
        """

        # Clear out previous value
        self.value = None

        if self.data_type == 'string':
            if isinstance(val_bytes, int):
                self.value = ''
            else:
                val_bytes = val_bytes.bytes
                self.value = val_bytes.decode('utf-8')
        elif self.data_type == 'enum':
            if not isinstance(val_bytes, int):
                val_bytes = val_bytes.bytes
                val_int = int.from_bytes(val_bytes, 'big', signed=False)
            else:
                val_int = val_bytes
            self.value = self.enum_def(val_int).name if self.enum_def else val_int
        elif self.data_type == 'float':
            if isinstance(val_bytes, int):
                self.value = float(val_bytes)
            else:
                self.value = val_bytes.f
        elif self.data_type == 'integer':
            self.value = val_bytes.int
        elif self.data_type == 'unsigned':
            if isinstance(val_bytes, int):
                self.value = val_bytes
            else:
                self.value = int(val_bytes.uint)
        else:
            log.error(f"Unknown type for {self.name}: {self.data_type}")

        return self.value

    def canonical_map(self):
        """
        Returns relevant channel definition and value state as dict
        :return: State dict
        """
        try:
            d = dict()
            d['abbreviation'] = self.abbreviation
            d['measurement_id'] = self.measurement_id
            d['title'] = self.title
            d['name'] = self.name
            d['description'] = self.description
            d['source'] = self.source
            d['categories'] = self.categories
            d['byte_length'] = self.byte_length
            d['data_type'] = self.data_type
            d['value'] = self.value
        except Exception as e:
            log.error(f"Error occurred while creating dictionary for {self.name}: {e}")
            return {}

        return d


class Monitor_Channel_Config:
    """
    Configuration of monitor channels, populated from an
    AMPCS MON-0158 multimission monitor channel dictionary.
    """
    # Paths used to crawl the parsed XML-doc
    PATH_ENUM_TABLE = 'telemetry_dictionary.enum_definitions.enum_table'
    PATH_ENUM = 'values.enum'
    PATH_TELEMETRY = 'telemetry_dictionary.telemetry_definitions.telemetry'
    PATH_CATEGORY = 'categories.category'

    def __init__(self, config_file=None):
        """
        Constructor
        :param config_file: Location of monitor channel file
        """
        self.config_file = config_file
        self.enum_table = {}
        self.channel_types = {}
        self.load_config()

    @staticmethod
    def deep_get(dictionary, keys, default=None):
        """
        Utility method for crawling XML doc using period-delimited paths
        :param dictionary: Dictionary to be crawled
        :param keys: Period-delimited string denoting path
        :param default: Default value
        :return: Result of document crawl
        """
        return reduce(lambda d, key: d.get(key, default) if isinstance(d, dict) else default,
                      keys.split("."), dictionary)

    def load_config(self):
        """
        Loads and parses the monitor channel dictionary, extracting
        enum and telemetry channel definitions
        """
        tlm_dict = None
        if self.config_file:
            with open(self.config_file, 'rb') as f_strm:
                tlm_dict = xmltodict.parse(f_strm)

        # Nothing to extract so log issue and return
        if tlm_dict is None:
            if self.config_file:
                log.error(f"Unable to parse monitor channel file {self.config_file}")
            else:
                log.error("No monitor channel file was provided.")
            return

        # Convert telem-dict 'enum_table's to dict of Enum's
        for cfg_enum_tbl_def in self.deep_get(tlm_dict, self.PATH_ENUM_TABLE):
            enum_defn_dict = {}
            for cfg_en_def in self.deep_get(cfg_enum_tbl_def, self.PATH_ENUM):
                if isinstance(cfg_en_def, str):
                    cfg_en_def = {'@symbol': 'None', '@numeric': '0'}
                enum_defn_dict[cfg_en_def['@symbol']] = int(cfg_en_def['@numeric'])
            enum_def = Enum(cfg_enum_tbl_def['@name'], enum_defn_dict)
            self.enum_table[enum_def.__name__] = enum_def

        # Convert telem-dict 'telemetry's to dict of Monitor_Channel's
        for cfg_tlm_def in self.deep_get(tlm_dict, self.PATH_TELEMETRY):
            m_id = cfg_tlm_def.get('measurement_id', None)
            if not m_id:
                continue
            measurement_id = int(m_id)
            byte_length = int(cfg_tlm_def['@byte_length'])
            tlm_name = cfg_tlm_def['@name']
            tlm_abbrv = cfg_tlm_def['@abbreviation']
            tlm_type = cfg_tlm_def['@type']

            # print(i.keys())
            cfg_tlm_def_cats = self.deep_get(cfg_tlm_def, self.PATH_CATEGORY)
            tlm_cats = {}
            # print(d)
            for cat_def in cfg_tlm_def_cats:
                tlm_cats[cat_def['@name']] = cat_def['@value']

            # Check if type is 'enum', if so then lookup the associated
            # enum definition from the enum_table and provide it to
            # Monitor_Channel constructor
            tlm_enum = None
            if tlm_type == 'enum':
                enum_lookup = f'Enum_{tlm_abbrv}'  # Map tlm abbrv to enum name
                tlm_enum = self.enum_table[enum_lookup]
                # If enum was not found, report the error
                if tlm_enum is None:
                    log.error(f"Telemetry definition for {tlm_name} refers to undeclared enum {enum_lookup}")

            self.channel_types[measurement_id] = \
                Monitor_Channel(tlm_abbrv,
                                tlm_name,
                                tlm_type,
                                cfg_tlm_def['@source'],
                                byte_length,
                                measurement_id,
                                cfg_tlm_def['title'],
                                cfg_tlm_def['description'].strip("'"),
                                tlm_cats,
                                tlm_enum)

    def get_channel(self, measurement_id):
        """
        Returns the Monitor_Channel instance associated by the measurement_id
        :param measurement_id: Measurement identifier for channel
        :return: Monitor_Channel, or None if not found
        """
        return self.channel_types[measurement_id]


class DSN_Monitor():
    """
    DSN monitor receives standard DSN blocks and processes them
    to extract and publish monitor-channel data-dicts.
    """
    def __init__(self, channel_config):
        """
        Constructor
        :param channel_config: Monitor_Channel_Config instance
        """
        self.channel_config = channel_config

        # Create lookup for CHDO-28 data quality
        self.chdo_28_data_qual = dict()
        self.chdo_28_data_qual[0] = "No error, not filler."
        self.chdo_28_data_qual[1] = "The decom map tried to make a channel, but the record " \
                                    "had no data at that location."
        self.chdo_28_data_qual[2] = "Filler data was decommutated."
        self.chdo_28_data_qual[3] = "Stale"

    def process_sdb(self, sdb):
        """
        Process standard DSN block
        """
        sdb_sections = {'DDD_HEADER': sdb[0:20],
                        'SFDU': sdb[20:-2],
                        'DDD_TRAILER': sdb[-2:None]}
        res = self.process_sfdu(sdb_sections['SFDU'])
        return res

    def process_sfdu(self, sfdu):
        """
        Process SFDU section
        """
        # https://jaguar.jpl.nasa.gov/SW_detail.php?modid=2403

        # Note: We're working in 16 bits here
        processed = {}
        sfdu_label = sfdu[0:20]
        processed['SFDU_LABEL'] = self.process_sfdu_label(sfdu_label)

        aggregation_chdo = BitArray(sfdu[20:24])
        processed['AGGREGATION_CHDO'] = self.process_chdo_01(aggregation_chdo)
        aggr_chdo_chdo_len = processed['AGGREGATION_CHDO']['CHDO_LENGTH']

        primary_chdo = BitArray(sfdu[24:32])
        processed['PRIMARY_CHDO'] = self.process_chdo_02(primary_chdo)

        secondary_chdo = BitArray(sfdu[32:54])
        processed['SECONDARY_CHDO'] = self.process_chdo_73(secondary_chdo)

        tertiary_chdo = BitArray(sfdu[54:58])
        processed['TERTIARY_CHDO'] = self.process_chdo_000(tertiary_chdo)

        quaternary_chdo = BitArray(sfdu[58:68])
        processed['QUATERNARY_CHDO'] = self.process_chdo_27(quaternary_chdo)
        num_channels = processed['QUATERNARY_CHDO']['NUMBER_CHANNELS']

        chd0_index = aggr_chdo_chdo_len + 24  # 68
        data_chdo = BitArray(sfdu[chd0_index:])
        processed['DATA_CHDO'] = self.process_chdo_28(data_chdo, num_channels)

        chdo_data = processed['DATA_CHDO']['data']
        res = []
        for chdo_channel in chdo_data:
            # Retrieve the channel from its channel_number
            channel_number = chdo_channel['CHANNEL_NUMBER']
            channel = self.channel_config.get_channel(channel_number)

            if channel is None:
                log.error(f"Channel M-{channel_number} is not in the dictionary.")
                continue

            # Value comes from LC_VALUE (if not None) else from LENGTH_VALUE
            if chdo_channel['LC_VALUE']:
                val = chdo_channel['LC_VALUE']
            else:
                val = chdo_channel['LENGTH_VALUE']

            # Decode the val (based on internal data_type) and append
            # channel-as-list to results
            try:
                channel.decode(val)
                res.append(channel.canonical_map())
            except Exception as e:
                log.error(f"Error occurred while decoding channel {channel}: {e}")
                tb.print_exc()
                return res

        return res

    def process_chdo_28(self, dat, num_channels):
        # Channelized Data Area
        # https://jaguar.jpl.nasa.gov/SW_detail.php
        # Note: LV_FLAG - This flag identifies whether bits 8 through
        #       15(length_value) contain the actual value of
        #       the channel(if it will fit in a single byte),
        #       or the length of the actual value in 16-bit words.

        res = {}
        dat_bytes = dat.bytes
        res["CHDO_TYPE"] = int.from_bytes(dat_bytes[0:2], 'big', signed=False)
        res["CHDO_LENGTH"] = int.from_bytes(dat_bytes[2:4], 'big', signed=False)

        decoded = []

        # Create BitArray 4-bytes *after* the original dat_bytes start
        # This explains the offsets used (including '32' for magic_offset)
        dat = BitArray(dat_bytes[4:])
        dat_data_offset = 32
        for i in range(1, num_channels):
            chan_res = {}
            chan_res["SOURCE"] = chr(ord('@')+dat[0:5].uint)
            chan_res["LV_FLAG"] = bool(dat[5:6])
            chan_res["DATA_QUAL"] = self.chdo_28_data_qual[dat[6:7].uint]
            chan_res['LENGTH_VALUE'] = dat[7:16].uint
            chan_res['FILLER_LENGTH'] = dat[16:20].uint
            chan_res['CHANNEL_NUMBER'] = dat[20:32].uint
            if not chan_res['LV_FLAG']:
                filler = chan_res['FILLER_LENGTH']
                dat_beg_idx = filler + dat_data_offset
                dat_end_idx = (chan_res['LENGTH_VALUE'] * 16) + dat_data_offset
                chan_res['LC_VALUE'] = (dat[dat_beg_idx:dat_end_idx])
                consume = chan_res['LENGTH_VALUE'] * 16
            else:
                chan_res['LC_VALUE'] = None
                consume = 0
            decoded.append(chan_res)
            dat = BitArray(dat[consume + dat_data_offset:])
        res['data'] = decoded
        return res

    def process_chdo_27(self, dat):
        # Quarternary
        # 10 bytes
        dat = dat.bytes
        res = {}
        res["CHDO_TYPE"] = dat[0:2]
        res["CHDO_LENGTH"] = dat[2:4]
        res["DECOM_FLAGS"] = dat[4:5]
        res["FILLER_LENGTH"] = dat[5:6]
        res["NUMBER_CHANNELS"] = dat[6:8]

        res = {k: int.from_bytes(v, 'big', signed=False)
               for (k, v) in res.items()}
        res["MAP_ID"] = dat[8:10].hex()
        res["DECOM_FLAGS"] = None  # Per Spec
        return res

    def process_chdo_000(self, dat):
        # Tertiary
        # 4 Bytes
        dat = dat.bytes
        res = {}
        res['CHDO_TYPE'] = dat[0:2]
        res['CHDO_LENGTH'] = dat[2:4]
        res = {k: int.from_bytes(v, 'big', signed=False)
               for (k, v) in res.items()}
        return res

    def process_chdo_73(self, dat):
        # Secondary
        # 22 Bytes
        dat = dat.bytes
        res = {}
        res["CHDO_TYPE"] = dat[0:2]
        res["CHDO_LENGTH"] = dat[2:4]
        res["ORIGINATOR"] = dat[4:5]
        res["LAST_MODIFIER"] = dat[5:6]
        res["8B_SCFT_ID"] = dat[6:7]
        res["DATA_SOURCE"] = dat[7:8]
        res["SCFT_ID"] = dat[8:10]
        res["MST"] = dat[10:16]
        res["SPARE"] = dat[17:18]
        res["SCFT_ID"] = dat[18:20]
        res["SPARE_2"] = dat[20:22]

        res = {k: int.from_bytes(v, 'big', signed=False)
               for (k, v) in res.items()}
        return res

    def process_chdo_02(self, dat):
        # Primary
        # 8 bytes
        dat = dat.bytes
        res = {}
        res['CHDO_TYPE'] = int.from_bytes(dat[0:2], 'big', signed=False)
        res['CHDO_LENGTH'] = int.from_bytes(dat[2:4], 'big', signed=False)
        record_id = dat[4:8]
        res['MAJOR'] = record_id[0]
        res['MINOR'] = record_id[1]
        res['MISSION'] = record_id[2]
        res['FORMAT'] = record_id[3]
        return res

    def process_chdo_01(self, dat):
        # Aggregation
        # 4 Bytes
        dat = dat.bytes
        res = {}
        res["CHDO_TYPE"] = int.from_bytes(dat[0:2], 'big', signed=False)
        res["CHDO_LENGTH"] = int.from_bytes(dat[2:4], 'big', signed=False)
        # res["CHDO_VALUE"] = dat[4:]  ##Leaving in for now?
        return res

    def process_sfdu_label(self, dat):
        # https://jaguar.jpl.nasa.gov/SW_detail.php?modid=2137
        res = {}
        res["CONTROL_AUTHORITY"] = dat[0:4].decode("ASCII")
        res["VERSION_ID"] = dat[4:5].decode("ASCII")
        res["CLASS_ID"] = dat[5:6].decode("ASCII")
        res["SPARE"] = dat[6:8].decode("ASCII")
        res["DATA_DESCRIPTION_ID"] = dat[8:12].decode("ASCII")
        res["LENGTH_ATTRIBUTE"] = int.from_bytes(dat[12:20], 'big', signed=False)
        return res


class DSN_Monitor_Plugin(Plugin):
    """
    Plugin converts 0158-Monitor telemetry packets streaming from
    a UDP socket into channel records (dictionaries).
    It first populates a configuration from a channel monitor definition
    XML file, which is used for the conversion process.
    """
    def __init__(self, inputs=None, outputs=None,
                 zmq_args=None,
                 host='0.0.0.0', port=8001,
                 monitor_channel_file=None, **kwargs):

        super().__init__(inputs, outputs, zmq_args)

        self.host = host
        self.port = port

        # Check if config file was specified, if not print error but continue
        if monitor_channel_file is None:
            log.error("No monitor channel configuration file was specified.")

        # Instantiate new config instance
        mntr_chnl_cfg = Monitor_Channel_Config(monitor_channel_file)

        # Instantiate processor, passing in the config
        self.processor = DSN_Monitor(mntr_chnl_cfg)

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        log.info(f'Starting station monitor server on: {self.host}:{self.port}')
        s.bind((self.host, self.port))

        while True:
            data, _ = s.recvfrom(60000)
            self.process(data)

    def process(self, data, topic=None):
        """
        Process the data and publish result
        :param data: Byte array of standard DSN block
        :param topic: Topic parameter which is ignored
        """
        pub_res = self.processor.process_sdb(bytearray(data))
        if pub_res:
            self.publish(pub_res)
