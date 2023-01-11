from gevent import time, Greenlet, monkey
monkey.patch_all()
import ait
from ait.dsn.encrypt.encrypter import EncrypterFactory
from ait.core.server.plugins import Plugin
from ait.core import log
import ait.dsn.plugins.TCTF_Manager as tctf
import ait.dsn.plugins.Graffiti as Graffiti
from ait.core.sdls_utils import SDLS_Type, get_sdls_type
from ait.core.message_types import MessageType



class Encrypter(Plugin,
                Graffiti.Graphable):
    """
    Add the following lines to config.yaml:

    - plugin:
      name: ait.dsn.plugins.Encrypter.Encrypter
      inputs:
        - TCTF_Manager

    Then configure the managed parameters in the config.yaml as
    required by the encryption service.
    """
    def __init__(self, inputs=None, outputs=None, zmq_args=None, restart_delay_s=0, report_time_s=0, **kwargs):
        super().__init__(inputs, outputs, zmq_args)
        self.restart_delay_s = restart_delay_s
        self.report_time_s = report_time_s
        self.security_risk = False
        
        # We never expected this plugin to be instantiated
        # if our intention was to run in SDLS_Type CLEAR mode.
        # We risk leaking keys and introduce unefined behavior.
        self.expecting_sdls = get_sdls_type()
        if self.expecting_sdls is SDLS_Type.CLEAR or self.expecting_sdls is SDLS_Type.FINAL:
            print(f"CRITICAL CONFIGURATION ERROR: "
                  "found parameter expected_sdls_type: {self.expecting_sdls}. "
                  "This plugin expects <AUTH|ENC>. "
                  "If this is not an error, comment out "
                  "the encrypter plugin block. "
                  "We will refuse to process TCTFs.")
            self.security_risk = True
        else:
            self.encrypter = EncrypterFactory().get()
            self.encrypter.configure()
            self.encrypter.connect()
            log.info(f"Encryption services started.")
            self.supervisor = Greenlet.spawn(self.supervisor_tree)

        Graffiti.Graphable.__init__(self)

    def __del__(self):
        self.encrypter.close()
        return

    def process(self, cmd_struct, topic=None):
        if self.security_risk or not topic == "TCTF_Manager":
            # TCTF Manager should have never published to
            # TCTFs to us since we were expecting To oeprate in CLEAR mode.
            # If another plugin is attempting to encrypt something through us,
            # we will refuse.
            print(f""
                  "Dropping clear TCTF and halting further processing. "
                  "During startup we detected configuration parameter "
                  "dsn.sle.tctf.expected_sdls_type: CLEAR. "
                  "TCTF_Manager should not have been able to "
                  "publish to us in this state. "
                  "TCTFs should only be published by TCTF_Manager, "
                  f"but we received one from {topic}. "
                  "Check configuration parameter "
                  "`dsn.sle.tctf.expected_sdls_type`.")
            return

        # Pre-encryption size checks
        if not cmd_struct:
            log.error(f"received no data from {topic}")
        # Check for pre hand off to KMC size
        if tctf.check_tctf_size(cmd_struct.payload_bytes, self.expecting_sdls):
            log.debug(f"TCTF size from {topic} is ok")
        else:
            log.error(f"Initial TCTF received from {topic}"
                      " is oversized! Undefined behavior will occur!")
            return

        # Encrypt and check
        data = bytearray(cmd_struct.payload_bytes)
        crypt_result = self.encrypter.encrypt(data)
        if crypt_result.errors:
            log.error(f"Got error during encryption:"
                      f"{crypt_result.errors}")
            return

        # Check KMC's addition of SDLS headers did not
        # violate the final desired TCTF size.
        if tctf.check_tctf_size(cmd_struct.payload_bytes, tctf.SDLS_Type.FINAL):
            log.debug(f"Encrypted TCTF is properly sized.")
            cmd_struct.frame_size_valid = True
        else:
            log.error(f"Encrypted TCTF is oversized! "
                      "Undefined behavior will occur! Dropping TCTF")
            return
        if cmd_struct.payload_bytes == crypt_result.result:
            log.error(f"Encryption result "
                      "was the same same as clear?")
            return
        else:
            # Looks good to publish
            cmd_struct.payload_bytes = crypt_result.result
            self.publish(cmd_struct)

    def graffiti(self):
        n = Graffiti.Node(self.self_name,
                          inputs=[(i, "TCTF Frame") for i in self.inputs],
                          outputs=[(MessageType.KMC_STATUS.name,
                                    MessageType.KMC_STATUS.value)],
                          label="Encrypt/Authenticate TCTF",
                          node_type=Graffiti.Node_Type.PLUGIN)
        return [n]

    def supervisor_tree(self, msg=None):

        def periodic_report(report_time=5):
            while True:
                time.sleep(report_time)
                msg = {'state': self.encrypter.is_connected()}
                self.publish(msg, MessageType.KMC_STATUS.name)
                log.debug(msg)

        def high_priority(msg):
            #self.publish(msg, "monitor_high_priority_raf")
            pass
        
        def monitor(restart_delay_s=5):
            #self.connect()
            #time.sleep(restart_delay_s)
            #while True:
            #    time.sleep(restart_delay_s)
            #    self.SLE_manager.schedule_status_report()
            #    if self.SLE_manager._state == 'active' or self.SLE_manager._state == 'ready':
            #        log.debug(f"SLE OK!")
            #    else:
            #        self.publish(f"RAF SLE Interface is not active! ",'monitor_high_priority_cltu')
            #        self.handle_restart()
            pass
        
        if msg:
            high_priority(msg)
            return
        
        if self.report_time_s:
            reporter = Greenlet.spawn(periodic_report, self.report_time_s)
        mon = Greenlet.spawn(monitor, self.restart_delay_s)
