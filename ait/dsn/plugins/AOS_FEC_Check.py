from ait.core.server.plugins import Plugin
from ait.core import log
from ait.dsn.sle.frames import AOSTransFrame, AOSDataFieldType
from binascii import crc_hqx

class AOS_FEC_Check(Plugin):
    '''
    Check if a AOS frame fails a Forward Error Correction Check
    '''
    def __init__(self, inputs=None, outputs=None, zmq_args=None, **kwargs):
        super().__init__(inputs, outputs, zmq_args)
        self.bytes_from_previous_frame = None
        self.crc_func = crc_hqx
        self.log_header = "AOS_FEC_CHECK =>" 

    def process(self, data, topic=None):
        if not data:
            log.error(f"{self.log_header} I was sent no data!")
            return
        if self.isCorrupt(data):
            log.error(f"{self.log_header} FEC NOT OKAY! Dicarding Frame!")
            log.error(f"{self.log_header} Discard: {data}")
            return None
        
        log.debug(f"{self.log_header} Ok")
        self.publish(data)
        return data
            
    def isCorrupt(self, data):
        try:
            AOS_frame_object = AOSTransFrame(data)
        except:
            log.error(f"{self.log_header} Could not decode AOS Frame!")
            log.error(f"{self.log_header} Assuming frame is corrupted.")
            return True
        data_field_end_index = AOS_frame_object.defaultConfig.data_field_endIndex        

        expected_ecf = data[-2:]
        block = data[:data_field_end_index]
    
        actual_ecf = self.crc_func(block, 0xFFFF).to_bytes(2,'big')
        
        corrupt = actual_ecf != expected_ecf

        if corrupt:
            log.error(f"{self.log_header} "
                      f"Expected ECF {expected_ecf} did not match "
                      f"actual ecf {actual_ecf}")
        return corrupt 
