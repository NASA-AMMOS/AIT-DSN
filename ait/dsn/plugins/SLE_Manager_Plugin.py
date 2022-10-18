from gevent import time, Greenlet, monkey
monkey.patch_all()
import ait.core
import ait.dsn.sle
from ait.core.server.plugins import Plugin
from ait.core.message_types import MessageType
from ait.core import log
import ait.dsn.plugins.Graffiti as Graffiti
import ait
from ait.dsn.sle import RAF


"""
A plugin which creates an RAF connection with the DSN.
Frames received via the RAF connection are sent to the output stream
"""


class SLE_Manager_Plugin(Plugin, Graffiti.Graphable):
    def __init__(self, inputs=None, outputs=None,
                 zmq_args=None, report_time_s=0, **kwargs):
        inputs = ['SLE_RAF_RESTART']
        super().__init__(inputs, outputs, zmq_args)
        
        self.restart_delay_s = 5
        self.supervisor = Greenlet.spawn(self.supervisor_tree)
        self.report_time_s = report_time_s
        Graffiti.Graphable.__init__(self)
        self.receive_counter = 0
        self.raf_object = None

    def connect(self):
        log.info("Starting SLE interface.")
        try:
            self.raf_object = RAF()
            self.raf_object._handlers['AnnotatedFrame']=[self._transfer_data_invoc_handler]
            self.raf_object.connect()
            time.sleep(3)

            self.raf_object.bind()
            time.sleep(3)

            self.raf_object.start(None, None)
            time.sleep(3)

            log.info(f"New Connection: RAF interface is {self.raf_object._state}!")

        except Exception as e:
            msg = f"RAF SLE Interface Encountered exception {e}."
            log.error(msg)
            self.supervisor_tree(msg)

    def handle_restart(self):
        if self.raf_object:
            self.raf_object.shutdown()
        self.connect()

    def supervisor_tree(self, msg=None):

        def periodic_report(report_time=5):
            msg = {'state': None,
                   'total_received': None}
            while True:
                time.sleep(self.report_time_s)
                msg['total_received'] = self.receive_counter
                if self.raf_object:
                   msg['state']: self.raf_object._state
                self.publish(msg, MessageType.RAF_STATUS.name)
                log.debug(f"{msg}")

        def high_priority(msg):
            self.publish(msg, MessageType.HIGH_PRIORITY_RAF_STATUS.name)

        def monitor(restart_delay_s=5):
            log.info("Initial start of RAF interface")
            self.handle_restart()
            while True:
                time.sleep(self.report_time_s)
                # self.raf_object.schedule_status_report()
                if self.raf_object._state == 'active' or self.raf_object._state == 'ready':
                    log.debug(f"SLE OK!")
                else:
                    high_priority(f"RAF interface is {self.raf_object._state}!")
                    log.info("Monitor restarting interface!")
                    self.handle_restart()

        if msg:
            high_priority(msg)
            return

        if self.report_time_s:
            reporter = Greenlet.spawn(periodic_report, self.report_time_s)
        mon = Greenlet.spawn(monitor, self.restart_delay_s)

    def process(self, data=None, topic=None):
        if topic == "SLE_RAF_RESTART":
            log.info("Received RAF restart directive!")
            self.handle_restart()
            return

    def graffiti(self):
        n = Graffiti.Node(self.self_name,
                          inputs=[(i, "AOS Telemetry Frame")
                                  for i in self.inputs],
                          outputs=[MessageType.RAF_DATA.to_tuple(),
                                   MessageType.RAF_STATUS.to_tuple(),
                                   MessageType.HIGH_PRIORITY_RAF_STATUS.to_tuple()],
                          label=("Forwards AOS Frames from SLE interface"),
                          node_type=Graffiti.Node_Type.PLUGIN)
        return [n]

    def _transfer_data_invoc_handler(self, pdu):
        """"""
        frame = pdu.getComponent()
        if "data" in frame and frame["data"].isValue:
            tm_data = frame["data"].asOctets()
        else:
            err = (
                "RafTransferBuffer received but data cannot be located. "
                "Skipping further processing of this PDU ..."
            )
            ait.core.log.info(err)
            return

        self.receive_counter += 1
        self.publish(tm_data, MessageType.RAF_DATA.name)
