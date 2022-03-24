from ait.core.server.plugins import Plugin
from ait.core import log
from collections import defaultdict
from ait.core import tlm, log


class apid_router(Plugin):
    tlm_dict = tlm.getDefaultDict()

    def __init__(self, inputs=None, outputs=None, zmq_args=None, routes=None):
        super().__init__(inputs, outputs, zmq_args)
        log.error(routes)
        self.routes = defaultdict(set)
        for r, interval in routes.items():
            low = interval['start']
            high = interval['stop'] + 1

            for i in range(low, high):
                self.routes[i].add(r)
        #log.error(self.routes)
        return

    def process(self, data, topic=None, *argv,  **kwargs):
        pass
        # frame = data
        # if frame.uid not in self.routes:
        #     log.error(f"Apid {frame.uid} has no route!")
        # else:
        #     for route in self.routes.get(frame.uid):
        #         self.publish(data, route)
        #         print("LOL")
