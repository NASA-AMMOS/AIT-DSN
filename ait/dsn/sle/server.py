import ait
import ait.core.log
import ait.dsn.sle
import bottle

DSN_harness = {
    'RAF': {
        'instance': ait.dsn.sle.RAF,
        'connected': False,
        'bound': False, #change to binded?
        'started': False
    },
    'RCF': {
        'instance': ait.dsn.sle.RCF,
        'connected': False,
        'bound': False,
        'started': False
    },
    'CLTU': {
        'instance': ait.dsn.sle.CLTU,
        'connected': False,
        'bound': False,
        'started': False
    },
}

DSN_api = bottle.Bottle()

@DSN_api.route('/<interface>/connect', method='PUT')
def connect_handler(interface):
    current_interface = DSN_harness[interface]
    instance = current_interface['instance']
    
    if (not current_interface['connected']):
        instance.connect()
        current_interface['connected'] = True
    else:
        ait.core.log.error("{} instance already connected".format(interface))
        bottle.response.status = 400

@DSN_api.route('/<interface>/bind', method='PUT')
def bind_handler(interface):
    current_interface = DSN_harness[interface]
    instance = current_interface['instance']
    
    if (not current_interface['connected']):
        ait.core.log.error("{} instance is not connected. Unable to bind.".format(interface))
        bottle.response.status = 400
    else:
        if (not current_interface['bound']):
            instance.bind()
            current_interface['bound'] = True
        else:
            ait.core.log.error("{} instance already bound".format(interface))
            bottle.response.status = 400

@DSN_api.route('/<interface>/start', method='PUT')
def start_handler(interface):
    current_interface = DSN_harness[interface]
    instance = current_interface['instance']
    
    if (not current_interface['connected']):
        ait.core.log.error("{} instance is not connected. Unable to start.".format(interface))
        bottle.response.status = 400
    else:
        if (not current_interface['bound']):
            ait.core.log.error("{} instance is not bound. Unable to start.".format(interface))
            bottle.response.status = 400
        else:
            if (not current_interface['started']):
                instance.start()
                current_interface['started'] = True
            else:
                ait.core.log.error("{} instance already started".format(interface))
                bottle.response.status = 400

#Ask Michael if instance must be stopped before unbinding and unbound before disconnecting

@DSN_api.route('/<interface>/stop', method='PUT')
def stop_handler(interface):
    current_interface = DSN_harness[interface]
    instance = current_interface['instance']
    
    if (not current_interface['started']):
        ait.core.log.error("{} instance is not started. Unable to stop.".format(interface))
        bottle.response.status = 400
    else:
        instance.stop()
        current_interface['started'] = False

@DSN_api.route('/<interface>/unbind', method='PUT')
def unbind_handler(interface):
    current_interface = DSN_harness[interface]
    instance = current_interface['instance']
    
    if (not current_interface['bound']):
        ait.core.log.error("{} instance is not bound. Unable to unbind.".format(interface))
        bottle.response.status = 400
    else:
        instance.unbind()
        current_interface['bound'] = False

@DSN_api.route('/<interface>/disconnect', method='PUT')
def disconnect_handler(interface):
    current_interface = DSN_harness[interface]
    instance = current_interface['instance']
    
    if (not current_interface['connected']):
        ait.core.log.error("{} instance is not connected. Unable to disconnect.".format(interface))
        bottle.response.status = 400
    else:
        instance.disconnect()
        current_interface['connected'] = False

#need to flesh this out
Servers = []
if __name__ == '__main__':
    Servers.append( gevent.pywsgi.WSGIServer(
    ('0.0.0.0', port),
    DSN_api,
    handler_class = geventwebsocket.handler.WebSocketHandler)
    )

    for s in Servers:
        s.start()

    #bottle.run(host = '127.0.0.1', port = 8000)
