from ait.dsn.sle import RAF
import ait
import time
import ait.dsn.sle.frames as frames
from ait.core.server.plugins import Plugin
from ait.core import log

class RAF_modified(RAF):
    '''
    A modified version of the RAF class which publishes received frames to a plugin's output topic instead of sending them to a UDP socket
    '''
    def __init__(self, publish_function, *args, **kwargs):
        self._inst_id = ait.config.get('dsn.sle.raf.inst_id',
                                       kwargs.get('inst_id', None))
        self._hostnames = ait.config.get('dsn.sle.raf.hostnames',
                                         kwargs.get('hostnames', None))
        self._port = ait.config.get('dsn.sle.raf.port',
                                    kwargs.get('port', None))

        super(self.__class__, self).__init__(*args, **kwargs)

        self._service_type = 'rtnAllFrames'
        self._version = ait.config.get('dsn.sle.raf.version',
                                       kwargs.get('version', 4))
        self._auth_level = ait.config.get('dsn.sle.raf.auth_level',
                                          kwargs.get('auth_level', self._auth_level))

        self.frame_output_port = int(ait.config.get('dsn.sle.frame_output_port',
                                                    kwargs.get('frame_output_port',
                                                               ait.DEFAULT_FRAME_PORT)))

        self._handlers['RafBindReturn'].append(self._bind_return_handler)
        self._handlers['RafUnbindReturn'].append(self._unbind_return_handler)
        self._handlers['RafStartReturn'].append(self._start_return_handler)
        self._handlers['RafStopReturn'].append(self._stop_return_handler)
        self._handlers['RafTransferBuffer'].append(self._data_transfer_handler)
        self._handlers['RafScheduleStatusReportReturn'].append(self._schedule_status_report_return_handler)
        self._handlers['RafStatusReportInvocation'].append(self._status_report_invoc_handler)
        self._handlers['RafGetParameterReturn'].append(self._get_param_return_handler)
        self._handlers['AnnotatedFrame'].append(self._transfer_data_invoc_handler)
        self._handlers['SyncNotification'].append(self._sync_notify_handler)
        self._handlers['RafPeerAbortInvocation'].append(self._peer_abort_handler)
        self.publish = publish_function

    def _transfer_data_invoc_handler(self, pdu):
        ''''''
        frame = pdu.getComponent()
        if 'data' in frame and frame['data'].isValue:
            tm_data = frame['data'].asOctets()
        else:
            err = (
                'RafTransferBuffer received but data cannot be located. '
                'Skipping further processing of this PDU ...'
            )
            ait.core.log.info(err)
            return
        
        tm_frame_class = getattr(frames, self._downlink_frame_type)
        tmf = tm_frame_class(tm_data)

        self.publish(tm_data)

class RAFPlugin(Plugin):
    '''
    A plugin which creates a RAF instance using the SLE parameters specified in config.yaml, and publishes all received frames
    '''
    def __init__(self, inputs=None, outputs=None, zmq_args=None, command_subscriber=None):
        super().__init__(inputs, outputs, zmq_args)
        self.RAF_object = RAF_modified(publish_function= self.publish)
        self.RAF_object.connect()
        time.sleep(2)
        self.RAF_object.bind()
        time.sleep(2)
        self.RAF_object.start(None, None)
        time.sleep(2)

    def process(self, input_data, topic = None):
        pass

    def __del__(self):
        self.RAF_object.stop()
        self.RAF_object.unbind()
        self.RAF_object.disconnect()
