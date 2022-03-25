import ait
from ait.core.server.plugins import Plugin
from ait.core import log
from collections import defaultdict
import pickle
from ait.core import tlm, log
import ait.dsn.sle.frames as frames


class AOTS_to_CCSDS(Plugin):
    def __init__(self, inputs=None, outputs=None, zmq_args=None, **kwargs):
        super().__init__(inputs, outputs, zmq_args)
        self._downlink_frame_type = ait.config.get('dsn.sle.downlink_frame_type',
                                                   kwargs.get('downlink_frame_type', 'AOSTransFrame'))
        self.tm_frame_class = getattr(frames, self._downlink_frame_type)
        return

    def process(self, data, topic=None):
        tmf = self.tm_frame_class(data)
        #log.info(f"GOT DAT {data}")
        if tmf.is_idle_frame:
            #log.info(f"Dropping idle frame!")
            return
        else:
            #log.info(f"Frame OK!")
            #log.info(data)
            fhp = tmf.get('mpdu_first_hdr_ptr')
            #fhp = int.from_bytes(fhp, 'big')
            pduz = tmf.get('mpdu_packet_zone')
            res = pickle.dumps((fhp, pduz))
            self.publish(res)
            return res
