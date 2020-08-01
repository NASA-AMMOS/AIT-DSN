'''A class which manages multiple SLE Object instances and keeps track of states'''

import atexit
import ait
import ait.core.log
import ait.dsn.sle
import bottle
import gevent #THIS SCRIPT REQUIRES THE MOST RECENT VERSION OF GEVENT.
import geventwebsocket
from gevent.server import DatagramServer

class SLEInterfaceManager():
    '''A class which manages multiple SLE Object instances and keeps track of states'''
    #pylint:disable=too-many-instance-attributes
    def __init__(self):
        self.api = bottle.Bottle()

        self.raf_instance = ait.dsn.sle.RAF()
        self.raf_connected = False
        self.raf_bound = False
        self.raf_started = False

        self.rcf_instance = ait.dsn.sle.RCF()
        self.rcf_connected = False
        self.rcf_bound = False
        self.rcf_started = False

        self.cltu_instance = ait.dsn.sle.CLTU()
        self.cltu_connected = False
        self.cltu_bound = False
        self.cltu_started = False
        self.tc_data = None

        self._route()

        self.verbose = True

        self.raf_state = {
            'instance': self.raf_instance,
            'connected': self.raf_connected,
            'started': self.raf_started,
            'bound': self.raf_bound}

        self.rcf_state = {
            'instance': self.rcf_instance,
            'connected': self.rcf_connected,
            'started': self.rcf_started,
            'bound': self.rcf_bound}

        self.cltu_state = {
            'instance': self.cltu_instance,
            'connected': self.cltu_connected,
            'started': self.cltu_started,
            'bound': self.cltu_bound,
            'tc_data': self.tc_data}

    def _route(self):
        self.api.route('/connect/<interface>', callback=self.connect_handler)
        self.api.route('/bind/<interface>', callback=self.bind_handler)
        self.api.route('/start/<interface>', callback=self.start_handler)
        self.api.route('/stop/<interface>', callback=self.stop_handler)
        self.api.route('/unbind/<interface>', callback=self.unbind_handler)
        self.api.route('/disconnect/<interface>', callback=self.disconnect_handler)
        self.api.route('/upload/<interface>', callback=self.upload_handler)

    def get_interface_vars(self, interface):
        '''return proper state dictionary based on interface'''
        if interface.lower() == 'raf':
            return self.raf_state
        if interface.lower() == 'rcf':
            return self.rcf_state
        if interface.lower() == 'cltu':
            return self.cltu_state
        ait.core.log.error("{} is not a valid interface option".format(interface))
        bottle.response.status = 400
        return None

    def connect_handler(self, interface):
        '''
        Connect the SLE object specified by <interface> to the DSN.
        Example:
        /connect/cltu is equivalent to running cltu.connect()
        '''
        state = self.get_interface_vars(interface)
        if not state['connected']:
            if self.verbose:
                print(state)
                print("{} connecting\n".format(interface))
            state['instance'].connect()
            state['connected'] = True
            if self.verbose:
                print("{} connected\n".format(interface))
                print(state)
        else:
            ait.core.log.error("{} instance already connected".format(interface))
            bottle.response.status = 400

    def bind_handler(self, interface):
        '''
        Bind the SLE object specified by <interface> to the DSN.
        Example:
        /bind/cltu is equivalent to running cltu.bind()
        '''
        state = self.get_interface_vars(interface)
        if not state['connected']:
            ait.core.log.error("{} instance is not connected. Unable to bind.".format(interface))
            bottle.response.status = 400
        else:
            if not state['bound']:
                if self.verbose:
                    print(state)
                    print("{} binding\n".format(interface))
                state['instance'].bind()
                state['bound'] = True
                if self.verbose:
                    print(state)
                    print("{} bound\n".format(interface))
            else:
                ait.core.log.error("{} instance already bound".format(interface))
                bottle.response.status = 400

    def start_handler(self, interface):
        '''
        Start the SLE object specified by <interface>.
        Example:
        /start/cltu is equivalent to running cltu.start()
        '''
        state = self.get_interface_vars(interface)
        if not state['connected']:
            ait.core.log.error("{} instance is not connected. Unable to start.".format(interface))
            bottle.response.status = 400
        else:
            if not state['bound']:
                ait.core.log.error("{} instance is not bound. Unable to start.".format(interface))
                bottle.response.status = 400
            else:
                if not state['started']:
                    if self.verbose:
                        print(state)
                        print("{} starting\n".format(interface))
                    state['instance'].start() #need to add start and end times for raf and rcf
                    state['started'] = True
                    if self.verbose:
                        print(state)
                        print("{} started\n".format(interface))
                else:
                    ait.core.log.error("{} instance already started".format(interface))
                    bottle.response.status = 400

    def stop_handler(self, interface):
        '''
        Stop the SLE object specified by <interface>.
        Example:
        /stop/cltu is equivalent to running cltu.stop()
        '''
        state = self.get_interface_vars(interface)
        if not state['started']:
            ait.core.log.error("{} instance is not started. Unable to stop.".format(interface))
            bottle.response.status = 400
        else:
            state['instance'].stop()
            state['started'] = False
            if self.verbose:
                print(state)
                print("{} stopped\n".format(interface))

    def unbind_handler(self, interface):
        '''
        Unbind the SLE object specified by <interface>.
        Example:
        /unbind/cltu is equivalent to running cltu.unbind()
        '''
        state = self.get_interface_vars(interface)
        if not state['bound']:
            ait.core.log.error("{} instance is not bound. Unable to unbind.".format(interface))
            bottle.response.status = 400
        else:
            state['instance'].unbind()
            state['bound'] = False
            if self.verbose:
                print(state)
                print("{} unbound\n".format(interface))

    def disconnect_handler(self, interface):
        '''
        Disconnect the SLE object specified by <interface>.
        Example:
        /disconnect/cltu is equivalent to running cltu.disconnect()
        '''
        state = self.get_interface_vars(interface)
        if not state['connected']:
            ait.core.log.error("{} instance is not connected. Unable to disconnect.".format(interface)) #pylint:disable=line-too-long
            bottle.response.status = 400
        else:
            state['instance'].disconnect()
            state['connected'] = False
            if self.verbose:
                print(state)
                print("{} disconnected\n".format(interface))

    def upload_handler(self, interface):
        '''
        Only valid call is /upload/cltu
        This function will upload the tc_data attribute of the class.
        '''
        state = self.get_interface_vars(interface)
        if not state['started']:
            ait.core.log.error("CLTU instance is not started. Unable to upload CLTU.")
            bottle.response.status = 400
        else:
            self.cltu_instance.upload_cltu(state['tc_data'])
            if self.verbose:
                print("tc_data sent: {}".format(state['tc_data']))

class CLTUServer(DatagramServer):
    '''A server which listens at a specified port for data, and then updates the tx'''
    def __init__(self, sle_interfaces_class, *args, **kwargs):
        self.sle_interfaces_class = sle_interfaces_class
        gevent.server.DatagramServer.__init__(self, *args, **kwargs)
    def handle(self, data): # pylint:disable=method-hidden
        '''update tc_data attribute of of sle_interfaces_class with data sent to listener'''
        self.sle_interfaces_class.cltu_state['tc_data'] = data


if __name__ == '__main__':
    SLE_interfaces = SLEInterfaceManager()
    SLE_interfaces_server = gevent.pywsgi.WSGIServer(
        ('127.0.0.1', 7654),
        SLE_interfaces.api,
        handler_class=geventwebsocket.handler.WebSocketHandler)

    cltu_server = CLTUServer(listener=9000, sle_interfaces_class=SLE_interfaces)
    cltu_server.start()
    SLE_interfaces_server.serve_forever()


    @atexit.register
    def cleanup():
        '''function runs at exit to stop gevent servers'''
        cltu_server.stop()
        SLE_interfaces_server.stop()
