from ait.dsn.encrypt.encrypter import EncrypterFactory
from ait.core.server.plugins import Plugin
from ait.core import log


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
        self.encrypter = EncrypterFactory().get()

        self.encrypter.configure()
        self.encrypter.connect()

    def __del__(self):
        self.encrypter.close()
        return

    def process(self, data, topic=None):
        data = bytearray(data)
        crypt_result = self.encrypter.encrypt(data)
        if crypt_result.errors:
            msg = "Encrypter-> Got error during encryption:"
            msg += f"{crypt_result.errors}"
            log.error(msg)
        else:
            self.publish(crypt_result.result)
            return crypt_result.result
