import ait.core
from ait.core.server.plugins import Plugin
from ait.core import log
from ait.dsn.sle.frames import AOSTransFrame
from binascii import crc_hqx
from dataclasses import dataclass
import ait.dsn.plugins.Graffiti as Graffiti
import ait
from ait.core.message_types import MessageType as MT

STRICT = False


@dataclass
class TaggedFrame:
    frame: bytearray
    vcid: int
    channel_counter: int = 0
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
               'is_idle': self.idle,
               'frame': self.frame.hex()}
        return res


class AOS_Tagger():
    crc_func = crc_hqx
    frame_counter_modulo = 16777216  # As defined in CCSDS ICD: https://public.ccsds.org/Pubs/732x0b4.pdf

    def __init__(self, publish):
        self.publish = publish
        self.absolute_counter = 0
        vcids = ait.config.get('dsn.sle.aos.virtual_channels')._config  # what a low IQ move...
        vcids['Unknown'] = None
        self.vcid_sequence_counter = {i: 0 for i in vcids.keys()}
        self.vcid_loss_count = {**self.vcid_sequence_counter}
        self.vcid_corrupt_count = {**self.vcid_sequence_counter}
        self.hot = {i: False for i in self.vcid_sequence_counter.keys()}
        return

    def tag_frame(self, raw_frame):

        def tag_corrupt():
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
            tagged_frame.corrupt_frame = corrupt

            if tagged_frame.corrupt_frame:
                log.error(f"Expected ECF {expected_ecf} did not match actual ecf.")
                if tagged_frame.vcid not in self.vcid_corrupt_count:
                    self.vcid_corrupt_count['Unknown'] += 1
                else:
                    self.vcid_corrupt_count[tagged_frame.vcid] += 1
                self.publish(self.vcid_corrupt_count, MT.CHECK_FRAME_ECF_MISMATCH.name)
            return

        def tag_out_of_sequence():
            if tagged_frame.vcid not in self.vcid_sequence_counter:
                # Junk Frame
                tagged_frame.out_of_sequence = True
                tagged_frame.absolute_counter += 1
                return 
            expected_vcid_count = (self.vcid_sequence_counter[tagged_frame.vcid] % self.frame_counter_modulo) + 1

            #rint(f"{tagged_frame.vcid=} {expected_vcid_count=} {tagged_frame.channel_counter=} {self.hot[tagged_frame.vcid]=}")
            #print(self.hot[tagged_frame.vcid] and not tagged_frame.idle and not tagged_frame.channel_counter == expected_vcid_count)

            if self.hot[tagged_frame.vcid] and not tagged_frame.idle and not tagged_frame.channel_counter == expected_vcid_count:
                tagged_frame.out_of_sequence = True
                log.warn(f"Out of Sequence Frame VCID {tagged_frame.vcid}: expected {expected_vcid_count} but got {tagged_frame.channel_counter}")
                self.vcid_loss_count[tagged_frame.vcid] += 1
                self.publish(self.vcid_loss_count, MT.CHECK_FRAME_OUT_OF_SEQUENCE.name)

            self.hot[tagged_frame.vcid] = True
            self.vcid_sequence_counter[tagged_frame.vcid] = tagged_frame.channel_counter
            self.absolute_counter += 1
            tagged_frame.absolute_counter = self.absolute_counter
            return

        frame = AOSTransFrame(raw_frame)
        vcid = int(frame.virtual_channel)
        idle = frame.is_idle_frame
        channel_counter = int.from_bytes(frame.get('virtual_channel_frame_count'), 'big')
        tagged_frame = TaggedFrame(frame=raw_frame,
                                   vcid=vcid,
                                   idle=idle,
                                   channel_counter=channel_counter)

        tag_corrupt()
        tag_out_of_sequence()

        return tagged_frame


class AOS_FEC_Check_Plugin(Plugin, Graffiti.Graphable):
    '''
    Check if a AOS frame fails a Forward Error Correction Check
    '''
    def __init__(self, inputs=None, outputs=None, zmq_args=None, **kwargs):
        super().__init__(inputs, outputs, zmq_args)
        self.tagger = AOS_Tagger(self.publish)
        Graffiti.Graphable.__init__(self)

    def process(self, data, topic=None):
        if not data:
            log.error("received no data!")
            return

        tagged_frame = self.tagger.tag_frame(data)
        self.publish(tagged_frame)
        return tagged_frame

    def graffiti(self):
        n = Graffiti.Node(self.self_name,
                          inputs=[(i, "Raw AOS Frames") for i in self.inputs],
                          outputs=[],
                          label="Check Forward Error Correction Field",
                          node_type=Graffiti.Node_Type.PLUGIN)
        return [n]
