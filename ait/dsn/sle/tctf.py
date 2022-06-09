from enum import Enum, auto
from collections import OrderedDict, namedtuple
from ait.core import log
from bitstring import BitArray
import binascii


class HeaderKeys(Enum):
    """HeaderKeys is an Enum used as a key in TCTF hashmaps"""
    TRANSFER_FRAME_VERSION_NUM = auto()
    BYPASS_FLAG = auto()
    CONTROL_COMMAND_FLAG = auto()
    RESERVED = auto()
    SPACECRAFT_ID = auto()
    VIRTUAL_CHANNEL_ID = auto()
    FRAME_LENGTH = auto()
    FRAME_SEQ_NUM = auto()


class ICD:
    """
    Contains definitions and other useful values as defined in the CCSDS ICD, 4.1.2.1
    https://public.ccsds.org/Pubs/232x0b4.pdf
    """
    class Sizes(Enum):
        """
        Defines various useful size constants derrived from the CCSDS ICD. 
        TCTFS in the SDLS Protocol may define values smaller than the ones described here.
        """
        MAX_FRAME_OCTETS = 1024
        MAX_FRAME_BIN = MAX_FRAME_OCTETS * 8

        ECF_OCTETS = 2
        ECF_BIN = ECF_OCTETS * 8

        PRIMARY_HEADER_OCTETS = 5
        PRIMARY_HEADER_BIN = PRIMARY_HEADER_OCTETS * 8

        MAX_DATA_FIELD_NO_ECF_OCTETS = 1019
        MAX_FRAME_NO_ECF_OCTETS = PRIMARY_HEADER_OCTETS + MAX_DATA_FIELD_NO_ECF_OCTETS

        MAX_DATA_FIELD_ECF_OCTETS = MAX_DATA_FIELD_NO_ECF_OCTETS - ECF_OCTETS
        MAX_FRAME_ECF_OCTETS = PRIMARY_HEADER_OCTETS + MAX_DATA_FIELD_ECF_OCTETS + ECF_OCTETS

        MAX_DATA_FIELD_NO_ECF_BIN = MAX_DATA_FIELD_NO_ECF_OCTETS * 8
        MAX_DATA_FIELD_ECF_BIN = MAX_DATA_FIELD_ECF_OCTETS * 8

    class Header():
        """
        INFO contains a map associating a HeaderKey to a tuple of bit_size and mandatory,
        which defines the Header Field per CCSDS.
        """
        Field = namedtuple('Field', ['bit_size', 'mandatory'])
        INFO = OrderedDict()
        INFO[HeaderKeys.TRANSFER_FRAME_VERSION_NUM] = Field(2, True)
        INFO[HeaderKeys.BYPASS_FLAG] = Field(1, True)
        INFO[HeaderKeys.CONTROL_COMMAND_FLAG] = Field(1, True)
        INFO[HeaderKeys.RESERVED] = Field(2, True)
        INFO[HeaderKeys.SPACECRAFT_ID] = Field(10, True)
        INFO[HeaderKeys.VIRTUAL_CHANNEL_ID] = Field(6, True)
        INFO[HeaderKeys.FRAME_LENGTH] = Field(10, True)
        INFO[HeaderKeys.FRAME_SEQ_NUM] = Field(8, True)

    class CRC:
        """
        Contains crc_func.
        The ICD describes some variation of CRC-16-CCITT, where
        Name            Poly     Reverse  Remainder    Final XOR  Check
        crc-ccitt-false 0x11021  False    0xFFFF       0x0000     0x29B1
        Which is used for generating the ECF section of the TCTF.
        """
        crc_func = binascii.crc_hqx

    class HeaderSlices:
        """
        HeaderSlices contains SLICES, which maps a HeaderKey to a python slice.
        The slices are used to extract sections of the frame binary.

        See the TCTransFrame decode function
        """
        SLICES = OrderedDict()
        SLICES[HeaderKeys.TRANSFER_FRAME_VERSION_NUM] = slice(0, 2)
        SLICES[HeaderKeys.BYPASS_FLAG] = slice(2, 3)
        SLICES[HeaderKeys.CONTROL_COMMAND_FLAG] = slice(3, 4)
        SLICES[HeaderKeys.RESERVED] = slice(4, 6)
        SLICES[HeaderKeys.SPACECRAFT_ID] = slice(6, 16)
        SLICES[HeaderKeys.VIRTUAL_CHANNEL_ID] = slice(16, 22)
        SLICES[HeaderKeys.FRAME_LENGTH] = slice(22, 32)
        SLICES[HeaderKeys.FRAME_SEQ_NUM] = slice(32, 41)


class TCTransFrame():
    """
    An instance of TCTransFrame fully defines a TCTF. 
    Encoding is deferred until the encode method is called.
    
    The static decode method will translate a TCTF binary into a named tuple.

    apply_ecf defines whether the ECF field should be calculated and attached to the TCTF. 

    Parameters are expected to comply with CCSDS standard, and no validation is done on them.
    """
    DecodedTCTF = namedtuple('DecodedTCTF', ["header_map", "payload", "ecf"])

    @staticmethod
    def decode(data, has_ecf=None):
        if has_ecf:
            payload = data[5:-2].hex()
            ecf = data[-2:].hex()
        else:
            payload = data[5:].hex()
            ecf = None

        header_hex = data[0:5]
        header = BitArray(header_hex).bin

        decoded_header = OrderedDict()
        for key in HeaderKeys:
            slice = ICD.HeaderSlices.SLICES[key]
            val_bin = header[slice]
            val_eng = int(val_bin, 2)
            decoded_header[key] = val_eng
            log.debug(f"TCTransFrame => decode -> {key}, {slice}, Val_Bin:{val_bin}, bin_len={len(val_bin)}, decode={val_eng}")

        decoded_header['HEADER_HEX'] = header_hex.hex()
        return TCTransFrame.DecodedTCTF(decoded_header, payload, ecf)

    def __init__(self, tf_version_num, bypass, cc, rsvd, scID, vcID,
                 frame_seq_num, data_field, apply_ecf=False):

        """
        Initialize a TCTF.
        Encoding the value is deferred until the encode method is called.

        Parameters
        ----------
        tf_version_num : TeleCommand Transfer Version Number*
        bypass : Bypass Flag*
        cc : Control Command Flag*
        rsvd : Reserved Space*
        scID : Spacecraft Identifier*
        vcID : Virtual Channel Identifier*
        frame_seq_num : Frame Sequence Number*
        data_field : Transfer Frame Data Field*, a bytearray representing the TCTF payload.
        apply_ecf : Flag used to apply ECF frames.

        * See CCSDS ICD for more information regarding parameter meaning and usage.
        """
        # Header Data
        self.primary_header = OrderedDict()

        # Data Field
        self.encoded_data_field = data_field
        self.size_data_field_bin = len(self.encoded_data_field) * 8

        # ECF Data
        self.apply_ecf = apply_ecf
        self.encoded_crc = None
        # Finalize ecf size
        if self.apply_ecf:
            self.size_ecf_bin = ICD.Sizes.ECF_BIN.value
        else:
            self.size_ecf_bin = 0

        # Final Frame Data
        self.encoded_frame = None
        self.size_frame_bin = sum([ICD.Sizes.PRIMARY_HEADER_BIN.value,
                                   self.size_data_field_bin,
                                   self.size_ecf_bin])
        # Set Primary Header and defer encoding
        self.set_primary_header(tf_version_num, bypass, cc, rsvd, scID, vcID,
                                frame_seq_num)

    def encode(self):
        """
        When called, returns bytes representing the TCTF.
        If called a second time, returns the previously computed TCTF.
        """
        # Exit early if we have previously encoded
        if self.encoded_frame:
            return self.encoded_frame

        # Finalize primaryheader per ICD
        self.encode_primary_header()

        #  Attach Payload
        frame_no_crc_bytes = self.encoded_primary_header + self.encoded_data_field

        # Attach CRC as ECF
        self.encode_ecf(frame_no_crc_bytes)
        self.encoded_frame = frame_no_crc_bytes + self.encoded_crc

        return self.encoded_frame

    def set_primary_header(self, tf_version_num, bypass, cc, rsvd, scID, vcID,
                           frame_seq_num):
        """
        Prepares the TCTF instance for generating the TCTF.
        """
        # Finalize frame size
        frame_len = int(self.size_frame_bin / 8)-1
        log.debug((f"TCTransFrame => set_primary_header -> "
                   f"FRAMELENGTH: {frame_len}"))

        # Insertion order is critical. Must match ICD order.
        self.primary_header[HeaderKeys.TRANSFER_FRAME_VERSION_NUM] = tf_version_num
        self.primary_header[HeaderKeys.BYPASS_FLAG] = bypass
        self.primary_header[HeaderKeys.CONTROL_COMMAND_FLAG] = cc
        self.primary_header[HeaderKeys.RESERVED] = rsvd
        self.primary_header[HeaderKeys.SPACECRAFT_ID] = scID
        self.primary_header[HeaderKeys.VIRTUAL_CHANNEL_ID] = vcID
        self.primary_header[HeaderKeys.FRAME_LENGTH] = frame_len
        self.primary_header[HeaderKeys.FRAME_SEQ_NUM] = frame_seq_num

    def encode_primary_header(self):
        """
        Returns bytes representing the primary header.
        """
        new_header = BitArray()
        for header_field, header_data in self.primary_header.items():
            size = ICD.Header.INFO[header_field].bit_size
            padded_segment = format(header_data, f'0{size}b')
            segment = BitArray(bin=padded_segment)
            new_header.append(segment)
            log.debug((f"TCTransFrame => encode_primary_header -> "
                       f"{header_field} ::=> "
                       f"Encoding: {segment},  "
                       f"Length: {len(segment)}"))
        self.encoded_primary_header = new_header.bytes
        log.debug((f"TCTransFrame => encode_primary_header -> "
                   f"Header= {new_header}, "
                   f"Size= {len(new_header)}"))
        return self.primary_header

    def encode_ecf(self, frame_no_crc_bytes):
        """
        Returns bytes representing the ECF segment of the TCTF.
        If the apply_ecf flag is not set, an empty bytearray is returned.
        """
        if self.apply_ecf:
            crc_val = ICD.CRC.crc_func(frame_no_crc_bytes, 0xFFFF)
            self.encoded_crc = crc_val.to_bytes(ICD.Sizes.ECF_OCTETS.value,
                                                byteorder="big")
        else:
            self.encoded_crc = bytes()
        log.debug((f"TCTransFrame => encode_ecg -> Encoded CRC: "
                   f"{self.encoded_crc}"))
        return self.encoded_crc
