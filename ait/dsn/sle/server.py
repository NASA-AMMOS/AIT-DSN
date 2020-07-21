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
        ait.core.log.error("Instance already connected")
        bottle.response.status = 400

@DSN_api.route('/<interface>/bind', method='PUT')
def bind_handler(interface):
    current_interface = DSN_harness[interface]
    instance = current_interface['instance']
    
    if (not current_interface['connected']):
        ait.core.log.error("Instance is not connected. Unable to bind.")
        bottle.response.status = 400
    else:
        if (not current_interface['bound']):
            instance.bind()
            current_interface['bound'] = True
        else:
            ait.core.log.error("Instance already bound")
            bottle.response.status = 400

@DSN_api.route('/<interface>/start', method='PUT')
def start_handler(interface):
    current_interface = DSN_harness[interface]
    instance = current_interface['instance']
    
    if (not current_interface['connected']):
        ait.core.log.error("Instance is not connected. Unable to start.")
        bottle.response.status = 400
    else:
        if (not current_interface['bound']):
            ait.core.log.error("Instance is not bound. Unable to start.")
            bottle.response.status = 400
        else:
            if (not current_interface['started']):
                instance.start()
                current_interface['started'] = True
            else:
                ait.core.log.error("Instance already started")
                bottle.response.status = 400

#Ask Michael if instance must be stopped before unbinding and unbound before disconnecting

@DSN_api.route('/<interface>/stop', method='PUT')
def stop_handler(interface):
    current_interface = DSN_harness[interface]
    instance = current_interface['instance']
    
    if (not current_interface['started']):
        ait.core.log.error("Instance is not started. Unable to stop.")
        bottle.response.status = 400
    else:
        instance.stop()
        current_interface['started'] = False

@DSN_api.route('/<interface>/unbind', method='PUT')
def unbind_handler(interface):
    current_interface = DSN_harness[interface]
    instance = current_interface['instance']
    
    if (not current_interface['bound']):
        ait.core.log.error("Instance is not bound. Unable to unbind.")
        bottle.response.status = 400
    else:
        instance.unbind()
        current_interface['bound'] = False

@DSN_api.route('/<interface>/disconnect', method='PUT')
def disconnect_handler(interface):
    current_interface = DSN_harness[interface]
    instance = current_interface['instance']
    
    if (not current_interface['connected']):
        ait.core.log.error("Instance is not connected. Unable to disconnect.")
        bottle.response.status = 400
    else:
        instance.disconnect()
        current_interface['connected'] = False

#need to flesh this out
bottle.run(host='localhost', port=8080)
