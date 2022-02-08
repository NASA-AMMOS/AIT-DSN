import ait.core
import ait.dsn.sle.tctf as tctf
from ait.core.server.plugins import Plugin


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
                 command_subscriber=None, managed_parameters=None):
        super().__init__(inputs, outputs, zmq_args)

        config_prefix = 'dsn.sle.tctf.'
        self.tf_version_num = ait.config.get(config_prefix+'transfer_frame_version_number', None)
        self.bypass = ait.config.get(config_prefix+'bypass_flag', None)
        self.cc = ait.config.get(config_prefix+'control_command_flag', None)
        self.rsvd = ait.config.get(config_prefix+'reserved', None)
        self.scID = ait.config.get(config_prefix+'uplink_spacecraft_id', None)
        self.vcID = ait.config.get(config_prefix+'virtual_channel_id', None)
        self.frame_seq_num = ait.config.get(config_prefix+'frame_sequence_number', None)
        self.apply_ecf = ait.config.get(config_prefix+'apply_error_correction_field', None)

    def process(self, data_field_byte_array, topic=None):
        frame = tctf.TCTransFrame(tf_version_num=self.tf_version_num,
                                  bypass=self.bypass, cc=self.cc,
                                  rsvd=self.rsvd, scID=self.scID,
                                  vcID=self.vcID,
                                  frame_seq_num=self.frame_seq_num,
                                  data_field=data_field_byte_array,
                                  apply_ecf=self.apply_ecf)

        encoded_frame = frame.encode()
        ait.core.log.debug(f"TCTF_Manager: {encoded_frame}")

        self.publish(encoded_frame)
        self.frame_seq_num = (self.frame_seq_num + 1) % 255
        return encoded_frame
