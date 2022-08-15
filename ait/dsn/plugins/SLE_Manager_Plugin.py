from gevent import time, Greenlet, monkey
monkey.patch_all()
import ait.core
import ait.dsn.sle
from ait.core.server.plugins import Plugin
from ait.core.message_types import MessageType
from ait.core import log
import ait.dsn.plugins.Graffiti as Graffiti

class SLE_Manager_Plugin(Plugin, Graffiti.Graphable):
    def __init__(self, inputs=None, outputs=None,
                 zmq_args=None, report_time_s=0, **kwargs):
        super().__init__(inputs, outputs, zmq_args)
        self.restart_delay_s = 5
        self.SLE_manager = None
        self.supervisor = Greenlet.spawn(self.supervisor_tree)
        self.report_time_s = report_time_s
        Graffiti.Graphable.__init__(self)

    def connect(self):
        log.info(f"Starting SLE interface.")
        try:
            self.SLE_manager = ait.dsn.sle.RAF()

            self.SLE_manager.connect()
            time.sleep(2)

            self.SLE_manager.bind()
            time.sleep(2)

            self.SLE_manager.start(None, None)
            
            log.info("SLE Interface is up!")

        except Exception as e:
            msg = f"RAF SLE Interface Encountered exception {e}."
            log.error(msg)
            self.supervisor_tree(msg)
            self.handle_restart()

    def handle_restart(self):
        msg = f"Restarting RAF SLE Interface in {self.restart_delay_s} seconds."
        log.error(msg)
        self.supervisor_tree(msg)
        time.sleep(self.restart_delay_s)
        self.connect()

    def supervisor_tree(self, msg=None):

        def periodic_report(report_time=5):
            while True:
                time.sleep(report_time)
                msg = {'state': self.SLE_manager._state,
                       'report': self.SLE_manager.last_status_report_pdu,
                       'total_received': self.SLE_manager.receive_counter}
                self.publish(msg, MessageType.RAF_STATUS.name)
                log.debug(f"{msg}")

        def high_priority(msg):
            self.publish(msg, MessageType.HIGH_PRIORITY_RAF_STATUS.name)

        def monitor(restart_delay_s=5):
            self.connect()
            time.sleep(restart_delay_s)
            while True:
                time.sleep(restart_delay_s)
                self.SLE_manager.schedule_status_report()
                if self.SLE_manager._state == 'active' or self.SLE_manager._state == 'ready':
                    log.debug(f"SLE OK!")
                else:
                    high_priority(f"RAF SLE Interface is {self.SLE_manager._state}!")
                    self.handle_restart()

        if msg:
            high_priority(msg)
            return
        
        if self.report_time_s:
            reporter = Greenlet.spawn(periodic_report, self.report_time_s)
        mon = Greenlet.spawn(monitor, self.restart_delay_s)

    def handle_kill(self):
        try:
            self.SLE_manager.stop()
            time.sleep(2)

            self.SLE_manager.unbind()
            time.sleep(2)

            self.SLE_manager.disconnect()
            time.sleep(2)

        except:
            log.error(f"Encountered exception {e} while killing SLE manager")

    def process(self, topic=None):
        try:
            pass

        except Exception as e:
            log.error(f"Encountered exception {e}.")
            self.handle_restart()

    def graffiti(self):
        n = Graffiti.Node(self.self_name,
                          inputs=[(i, "AOS Telemetry Frame")
                                  for i in self.inputs],
                          outputs=[(MessageType.RAF_DATA.name, MessageType.RAF_DATA.value),
                                   (MessageType.RAF_STATUS.name, MessageType.RAF_STATUS.value),
                                   (MessageType.HIGH_PRIORITY_RAF_STATUS.name, MessageType.HIGH_PRIORITY_RAF_STATUS.value)],
                          label=("Forwards AOS Frames from SLE interface"),
                          node_type=Graffiti.Node_Type.PLUGIN)
        return [n]
