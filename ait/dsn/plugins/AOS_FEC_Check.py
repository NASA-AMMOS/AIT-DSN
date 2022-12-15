import ait.core
from ait.core.server.plugins import Plugin
from ait.core import log
from ait.dsn.sle.frames import AOSTransFrame
from binascii import crc_hqx
from dataclasses import dataclass
import ait.dsn.plugins.Graffiti as Graffiti
import ait

STRICT = False


@dataclass
class TaggedFrame:
    frame: bytearray
    vcid: int
    channel_counter: int
    absolute_counter: int = 0
    corrupt_frame: bool = False
    out_of_sequence: bool = False
    idle: bool = False

    def get_map(self):
        res = {'channel_counter': self.channel_counter,
               'absolute_counter': self.absolute_counter,
               'vcid': self.vcid,
               'corrupt_frame': self.corrupt_frame,
               'out_of_sequence': self.out_of_sequence,
               'is_idle': self.is_idle,
               'frame': self.frame.hex()}
        return res


class AOS_FEC_Check():
    crc_func = crc_hqx
    vcid_counter = {}

    def __init__(self):
        return

    def tag_fec(self, raw_frame):

        def isCorrupt(frame):
            try:
                data_field_end_index = frame.defaultConfig.data_field_endIndex
            except Exception as e:
                log.error(f"Could not decode AOS Frame!: {e}")
                log.error(f"Assuming frame is corrupted.")
                return True

            expected_ecf = raw_frame[-2:]
            block = raw_frame[:data_field_end_index]
            actual_ecf = self.crc_func(block, 0xFFFF).to_bytes(2, 'big')
            corrupt = actual_ecf != expected_ecf

            if corrupt:
                log.error(f""
                          f"Expected ECF {expected_ecf} did not match "
                          f"actual ecf {actual_ecf}")
            return corrupt
        
        if not raw_frame:
            log.error(f"I was sent no data!")
            return

        frame = AOSTransFrame(raw_frame)
        vcid = int(frame.virtual_channel)
        channel_counter = int.from_bytes(frame.get('virtual_channel_frame_count'), 'big') # Gee, thanks for the help...

        corrupt_frame = isCorrupt(frame)
        if corrupt_frame:
            log.error(f"FEC NOT OKAY! {raw_frame}")
            if STRICT:
                exit()
        else:
            log.debug(f"Ok")
        tagged_frame = TaggedFrame(frame=raw_frame,
                                   vcid=vcid,
                                   corrupt_frame=corrupt_frame,
                                   channel_counter=channel_counter,
                                   idle=frame.is_idle)
        return tagged_frame


class AOS_FEC_Check_Plugin(Plugin, Graffiti.Graphable):
    '''
    Check if a AOS frame fails a Forward Error Correction Check
    '''
    def __init__(self, inputs=None, outputs=None, zmq_args=None, **kwargs):
        super().__init__(inputs, outputs, zmq_args)
        self.checker = AOS_FEC_Check()
        self.absolute_counter = 0
        Graffiti.Graphable.__init__(self)
        vcids = ait.config.get('dsn.sle.aos.virtual_channels')._config  # what a low IQ move...
        self.vcid_sequence_counter = {i: 0 for i in vcids.keys()}
        self.vcid_loss_count = {**self.vcid_sequence_counter}
        self.hot = {i: False for i in self.vcid_sequence_counter.keys()}

    def process(self, data, topic=None):
        if not data:
            log.error("received no data!")
            return

        tagged_frame = self.checker.tag_fec(data)
        expected_vcid_count = self.vcid_sequence_counter[tagged_frame.vcid] + 1
        #print(self.hot[tagged_frame.vcid] and not tagged_frame.idle and not tagged_frame.channel_counter == expected_vcid_count)
        if self.hot[tagged_frame.vcid] and not tagged_frame.idle and not tagged_frame.channel_counter == expected_vcid_count:
            tagged_frame.out_of_sequence = True
            log.warn(f"Out of Sequence Frame VCID {tagged_frame.vcid}: expected {expected_vcid_count} but got {tagged_frame.channel_counter}")
            self.vcid_loss_count[tagged_frame.vcid] += 1
        self.hot[tagged_frame.vcid] = True
        
        self.vcid_sequence_counter[tagged_frame.vcid] = tagged_frame.channel_counter
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
