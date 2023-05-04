
import ait.core
import ait.dsn.sle.tctf as tctf
from ait.core.server.plugins import Plugin
from ait.core import log
from enum import Enum, auto
from ait.core.sdls_utils import SDLS_Type, get_sdls_type

config_prefix = 'dsn.sle.tctf.'


# class SDLS_Type(Enum):
#     CLEAR = auto()
#     ENC = auto()  # Authenticated Encryption (SDLS)
#     AUTH = auto()  # Authentication Only (SDLS)
#     # FINAL is for internal use.
#     # It is treated the same as CLEAR
#     # Used by Encrypter to signify that TCTF size check
#     # should be done against final TCTF size instead of
#     # the KMC hand off size that it must necessarily violate.
#     FINAL = auto()


class TCTF_Manager(Plugin):
    """
    Data Processing Pipeline that encodes payloads in TCTF protocol as described by CCSDS standards.
    https://public.ccsds.org/Pubs/232x0b4.pdf

    The managed parameters are loaded from the AIT config.yaml
    See CCSDS Blue Book for information regarding managed parameters.


    Sample Configuration Part I:
    ----------------------------
    server:
        plugins:
            - plugin:
                name: ait.dsn.plugins.TCTF_Manager.TCTF_Manager
                inputs:
                    - command_stream

    Sample Configuration Part II:
    -----------------------------
    default:
        dsn:
            tctf:
                transfer_frame_version_number: 0
                bypass_flag: 0
                control_command_flag: 0
                reserved: 0
                uplink_spacecraft_id: 123
                virtual_channel_id: 0
                frame_sequence_number: 0
                apply_error_correction_field: True
    """
    
    def __init__(self, inputs=None, outputs=None, zmq_args=None,
                 command_subscriber=None, managed_parameters=None, **kwargs):
        super().__init__(inputs, outputs, zmq_args)

        self.tf_version_num = ait.config.get(config_prefix+'transfer_frame_version_number', None)
        self.bypass = ait.config.get(config_prefix+'bypass_flag', None)
        self.cc = ait.config.get(config_prefix+'control_command_flag', None)
        self.rsvd = ait.config.get(config_prefix+'reserved', None)
        self.scID = ait.config.get(config_prefix+'uplink_spacecraft_id', None)
        self.vcID = ait.config.get(config_prefix+'virtual_channel_id', None)
        self.frame_seq_num = ait.config.get(config_prefix+'frame_sequence_number', None)
        self.apply_ecf = ait.config.get(config_prefix+'apply_error_correction_field', None)
        self.expecting_sdls = get_sdls_type()

        if self.expecting_sdls is SDLS_Type.ENC:
            log.info(f"expecting to perform ENCRYPTED operations.")
        elif self.expecting_sdls is SDLS_Type.AUTH:
            log.info(f"expecting to perform AUTH operations.")
        else:
            log.info(f"expecting to process CLEAR TCTFs only.")

    def process(self, cmd_struct, topic=None):
        if not cmd_struct:
            log.error(f"Received no data from {topic}")
            return
        if not check_data_field_size(cmd_struct.payload_bytes):
            log.error(f"Failed payload check from {topic}")
            cmd_struct.payload_size_valid = False
        else:
            log.debug(f"Passed payload check")
        frame = tctf.TCTransFrame(tf_version_num=self.tf_version_num,
                                  bypass=self.bypass, cc=self.cc,
                                  rsvd=self.rsvd, scID=self.scID,
                                  vcID=self.vcID,
                                  frame_seq_num=self.frame_seq_num,
                                  data_field=cmd_struct.payload_bytes,
                                  apply_ecf=self.apply_ecf)

        try:
            encoded_frame = frame.encode()
        except Exception as e:
            log.error(e)
            log.error("Abandoning frame")
            return
        
        log.debug(f"{encoded_frame}")

        cmd_struct.payload_bytes = encoded_frame
        if check_tctf_size(encoded_frame):
            log.debug("TCTF passed size check.")
            cmd_struct.payload_size_valid = True
        else:
            log.info("Failed TCTF size check.")
            cmd_struct.payload_size_valid = False
        
        self.publish(cmd_struct)
        self.frame_seq_num = (self.frame_seq_num + 1) % 255
        return encoded_frame


def get_tctf_size(sdls_type=SDLS_Type.ENC):
    log_header = __name__ + "-> get_tctf_size=>"
    if not isinstance(sdls_type, SDLS_Type):
        log.error(f"caller error {sdls_type} is not {log_header}.SDLS_Type")
    if sdls_type is SDLS_Type.CLEAR or sdls_type is SDLS_Type.FINAL:
        maximum = ait.config.get(config_prefix+'max_tctf_size_final_octets', None)
    elif sdls_type is SDLS_Type.AUTH:
        maximum = ait.config.get(config_prefix+'max_tctf_size_auth_octets', None)
    elif sdls_type is SDLS_Type.ENC:
        maximum = ait.config.get(config_prefix+'max_tctf_size_enc_octets', None)

    # Error check maximum
    if not maximum:
        maximum = tctf.ICD.Sizes.MAX_FRAME_OCTETS.value
        log.error(f"parameter maximum TCTF Size for max_tctf_size_octets_"
                  f"{str(sdls_type)} was not found. Assuming maximum of {maximum} octets.")
        
    if maximum <= 0:
        maximum = tctf.ICD.Sizes.MAX_FRAME_OCTETS.value
        log.error(f"parameter maximum TCTF Size for max_tctf_size_octets_"
                  f"{str(sdls_type)}: {maximum} must be a positive integer of octets. "
                  "Assuming maximum of {maximum} octets.")

    return maximum


def check_tctf_size(tctf, sdls_type=None):
    if not sdls_type: # Caller deferring SDLS type to config.yaml
        sdls_type = get_sdls_type()

    else:
        sdls_type = SDLS_Type(sdls_type)
        
    if not isinstance(sdls_type, SDLS_Type): # Caller didn't provide a valid type
        log.error(f"SDLS Type {sdls_type} is not TCTF_Manager.SDLS_Type.")

    maximum = get_tctf_size(sdls_type)

    res = len(tctf)  <= maximum
    if res:
        log.debug(f"{res}. TCTF passed size check.")
    else:
        log.error(f"{res}. Got size {len(tctf)} but expected <= {maximum} ")
    return res
    
def get_max_data_field_size(sdls_type=None):
    maximum = None
    if not isinstance(sdls_type, SDLS_Type):
        sdls_type = get_sdls_type()
    if sdls_type is SDLS_Type.CLEAR:
        maximum = ait.config.get(config_prefix+'max_user_data_field_size_clear_octets', None)
    elif sdls_type is SDLS_Type.AUTH:
        maximum = ait.config.get(config_prefix+'max_user_data_field_size_auth_octets', None)
    elif sdls_type is SDLS_Type.ENC:
        maximum = ait.config.get(config_prefix+'max_user_data_field_size_enc_octets', None)
            # Error Check maximum
    fault = False
    
    if not maximum: # Couldn't find a value in config
        fault = True
        log.error(f"Parameter maximum max_user_data_field_size_"
                  f"{str(sdls_type)}_octets was not found.")
        maximum = 0

    if maximum <= 0: 
        log.error(f"Parameter maximum max_user_data_field_size_"
                  f"{str(sdls_type)}_octets: {maximum} must be a positive integer of octets. "
                  f"Assuming maximum of {maximum} octets.")
        fault = True

    if fault:        
        use_ecf = ait.config.get(config_prefix+'apply_error_correction_field', None)

        if use_ecf is None:
            log.error(f"Could not find parameter apply_error_correction_field."
                      "Assuming true.")
            use_ecf = True
        if use_ecf:
            maximum = tctf.ICD.Sizes.MAX_DATA_FIELD_ECF_OCTETS.value
        else:
            maximum = tctf.ICD.Sizes.MAX_DATA_FIELD_NO_ECF_OCTETS.value
    return maximum

def check_data_field_size(user_data_field, sdls_type=None):
    if not sdls_type: # Caller deferring SDLS type to config.yaml
        sdls_type = get_sdls_type()
    else:
        sdls_type = SDLS_Type(sdls_type)
    
    if not isinstance(sdls_type, SDLS_Type): # Caller didn't provide a valid type
        log.error(f"SDLS Type {sdls_type} is not an SDLS_Type.")
    maximum = get_max_data_field_size(sdls_type)

    res = len(user_data_field) <= maximum
    if not res:
        log.error(f"{res}. Got size {len(user_data_field)} but expected <= {maximum} ")
    return res


# TODO Just pass length
