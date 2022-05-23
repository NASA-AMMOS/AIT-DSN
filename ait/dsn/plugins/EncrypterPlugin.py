from ait.dsn.encrypt.encrypter import EncrypterFactory
from ait.core.server.plugins import Plugin
from ait.core import log
import ait.dsn.plugins.TCTF_Manager as tctf


class Encrypter(Plugin):
    """
    Add the following lines to config.yaml:

    - plugin:
      name: ait.dsn.plugins.Encrypter.Encrypter
      inputs:
        - TCTF_Manager

    Then configure the managed parameters in the config.yaml as
    required by the encryption service.
    """
    def __init__(self, inputs=None, outputs=None, zmq_args=None, **kwargs):
        super().__init__(inputs, outputs, zmq_args)
        self.log_header = __name__ + "->"
        self.security_risk = False

        # We never expected this plugin to be instantiated
        # if our intention was to run in SDLS_Type CLEAR mode.
        # We risk leaking keys and introduce unefined behavior.
        self.expecting_sdls = tctf.get_sdls_type()
        if self.expecting_sdls is tctf.SDLS_Type.CLEAR:
            log.error(f"{self.log_header} CRITICAL CONFIGURATION ERROR: "
                      "found parameter expected_sdls_type: CLEAR. "
                      "This plugin expects <AUTH|ENC>. "
                      "If this is not an error, comment out "
                      "the encrypter plugin block. "
                      "We will refuse to process TCTFs.")
            self.security_risk = True
        else:
            self.encrypter = EncrypterFactory().get()
            self.encrypter.configure()
            self.encrypter.connect()
            log.info(f"{self.log_header} Encryption services started.")

    def __del__(self):
        self.encrypter.close()
        return

    def process(self, data, topic=None):
        if self.security_risk or not topic == "TCTF_Manager":
            # TCTF Manager should have never published to
            # TCTFs to us since we were expecting To oeprate in CLEAR mode.
            # If another plugin is attempting to encrypt something through us,
            # we will refuse.
            log.error(f"{self.log_header} "
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
        if not data:
            log.error(f"{self.log_header} received no data from {topic}")
        # Check for pre hand off to KMC size
        if tctf.check_tctf_size(data, self.expecting_sdls):
            log.debug(f"{self.log_header} TCTF size from {topic} is ok")
        else:
            log.error(f"{self.log_header} Initial TCTF received from {topic}"
                      " is oversized! Undefined behavior will occur!")
            return

        # Encrypt and check
        data = bytearray(data)
        crypt_result = self.encrypter.encrypt(data)
        if crypt_result.errors:
            log.error(f"{self.log_header} Got error during encryption:"
                      f"{crypt_result.errors}")
            return

        # Check KMC's addition of SDLS headers did not
        # violate the final desired TCTF size.
        if tctf.check_tctf_size(crypt_result.result, tctf.SDLS_Type.FINAL):
            log.debug(f"{self.log_header} Encrypted TCTF is properly sized.")
        else:
            log.error(f"{self.log_header} Encrypted TCTF is oversized! "
                      "Undefined behavior will occur! Dropping TCTF")
            return
        if data == crypt_result.result:
            log.error(f"{self.log_header} Encryption result "
                      "was the same same as clear?")
            return
        else:
            # Looks good to publish
            self.publish(crypt_result.result)
