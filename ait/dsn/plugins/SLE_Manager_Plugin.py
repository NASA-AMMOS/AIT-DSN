from gevent import time, Greenlet, monkey
monkey.patch_all()
import ait.core
import ait.dsn.sle
from ait.core.server.plugins import Plugin
from ait.core import log

class SLE_Manager_Plugin(Plugin):
    def __init__(self, inputs=None, outputs=None,
                 zmq_args=None, **kwargs):
        super().__init__(inputs, outputs, zmq_args)
        self.restart_delay_s = 5
        self.SLE_manager = None
        self.supervisor = Greenlet.spawn(self.supervisor_tree)

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
            log.error(f"Encountered exception {e}.")
            self.handle_restart()

    def handle_restart(self):
            log.error(f"Restarting SLE Interface in {self.restart_delay_s} seconds.")
            time.sleep(self.restart_delay_s)
            self.connect()

    def supervisor_tree(self):
        self.connect()
        while True:
            time.sleep(self.restart_delay_s)
            if self.SLE_manager._state == 'active':
                log.debug(f"SLE OK!")
            else:
                self.handle_restart()

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

    def process(self):
        try:
            while True:
                time.sleep(0)

        except Exception as e:
            log.error(f"Encountered exception {e}.")
            self.handle_restart()

        finally:
            self.handle_kill()
            self.handle_restart()
