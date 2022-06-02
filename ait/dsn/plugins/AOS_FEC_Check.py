from ait.core.server.plugins import Plugin
from ait.core import log
from ait.dsn.sle.frames import AOSTransFrame, AOSDataFieldType
from binascii import crc_hqx
from dataclasses import dataclass
import ait.dsn.plugins.Graffiti as Graffiti


@dataclass
class TaggedFrame:
    frame: bytearray
    vcid: int = None
    absolute_counter: int = None
    corrupt_frame: bool = False
    channel_counter: int = None


class AOS_FEC_Check():
    crc_func = crc_hqx
    log_header = "AOS_FEC_CHECK =>"
    vcid_counter = {}

    def __init__(self):
        return

    @classmethod
    def tag_fec(cls, raw_frame):
        if not raw_frame:
            log.error(f"{cls.log_header} I was sent no data!")
            return

        corrupt_frame, vcid = cls.isCorrupt(raw_frame)
        if corrupt_frame:
            log.error(f"{cls.log_header} FEC NOT OKAY! {raw_frame}")
            exit()
        else:
            log.debug(f"{cls.log_header} Ok")
        tagged_frame = TaggedFrame(frame=raw_frame,
                                   vcid=vcid,
                                   corrupt_frame=corrupt_frame)
        return tagged_frame

    @classmethod
    def isCorrupt(cls, data):
        try:
            AOS_frame_object = AOSTransFrame(data)
            vcid = AOS_frame_object.virtual_channel
            data_field_end_index = AOS_frame_object.defaultConfig.data_field_endIndex
        except Exception as e:
            log.error(f"{cls.log_header} Could not decode AOS Frame!: {e}")
            log.error(f"{cls.log_header} Assuming frame is corrupted.")
            vcid = None
            corrupt = True
            return (corrupt, vcid)

        expected_ecf = data[-2:]
        block = data[:data_field_end_index]
        actual_ecf = cls.crc_func(block, 0xFFFF).to_bytes(2, 'big')
        corrupt = actual_ecf != expected_ecf

        if corrupt:
            log.error(f"{cls.log_header} "
                      f"Expected ECF {expected_ecf} did not match "
                      f"actual ecf {actual_ecf}")
        return (corrupt, vcid)


class AOS_FEC_Check_Plugin(Plugin, Graffiti.Graphable):
    '''
    Check if a AOS frame fails a Forward Error Correction Check
    '''
    def __init__(self, inputs=None, outputs=None, zmq_args=None, **kwargs):
        super().__init__(inputs, outputs, zmq_args)
        self.checker = AOS_FEC_Check()
        self.absolute_counter = 0
        Graffiti.Graphable.__init__(self)

    def process(self, data, topic=None):
        tagged_frame = self.checker.tag_fec(data)
        self.absolute_counter += 1
        tagged_frame.absolute_counter = self.absolute_counter
        
        self.publish(tagged_frame)
        return tagged_frame

    def graffiti(self):
        n = Graffiti.Node(self.self_name,
                          inputs=[(i, "Raw AOS Frames") for i in self.inputs],
                          outputs=[],
                          label="Check Forward Error Correction Field",
                          node_type=Graffiti.Node_Type.PLUGIN)
        return [n]
