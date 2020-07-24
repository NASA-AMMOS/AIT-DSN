import ait
import ait.core.log
import ait.dsn.sle
import bottle
import gevent
import geventwebsocket
import atexit

class DSN_server_class():
    def __init__(self):
        self.DSN_api = bottle.Bottle()

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

        self._route()

    def _route(self):
        self.DSN_api.route('/connect/RAF', method="PUT", callback=self.raf_connect_handler)
        self.DSN_api.route('/bind/RAF', method="PUT", callback=self.raf_bind_handler)
        self.DSN_api.route('/start/RAF', method="PUT", callback=self.raf_start_handler)
        self.DSN_api.route('/stop/RAF', method="PUT", callback=self.raf_stop_handler)
        self.DSN_api.route('/unbind/RAF', method="PUT", callback=self.raf_unbind_handler)
        self.DSN_api.route('/disconnect/RAF', method="PUT", callback=self.raf_disconnect_handler)
        self.DSN_api.route('/connect/RCF', method="PUT", callback=self.rcf_connect_handler)
        self.DSN_api.route('/bind/RCF', method="PUT", callback=self.rcf_bind_handler)
        self.DSN_api.route('/start/RCF', method="PUT", callback=self.rcf_start_handler)
        self.DSN_api.route('/stop/RCF', method="PUT", callback=self.rcf_stop_handler)
        self.DSN_api.route('/unbind/RCF', method="PUT", callback=self.rcf_unbind_handler)
        self.DSN_api.route('/disconnect/RCF', method="PUT", callback=self.rcf_disconnect_handler)
        self.DSN_api.route('/connect/CLTU', method="PUT", callback=self.cltu_connect_handler)
        self.DSN_api.route('/bind/CLTU', method="PUT", callback=self.cltu_bind_handler)
        self.DSN_api.route('/start/CLTU', method="PUT", callback=self.cltu_start_handler)
        self.DSN_api.route('/stop/CLTU', method="PUT", callback=self.cltu_stop_handler)
        self.DSN_api.route('/unbind/CLTU', method="PUT", callback=self.cltu_unbind_handler)
        self.DSN_api.route('/disconnect/CLTU', method="PUT", callback=self.cltu_disconnect_handler)
        self.DSN_api.route('/upload/CLTU', method="PUT", callback=self.cltu_upload_handler)

    def raf_connect_handler(self):
        if (not self.raf_connected):
            print("raf connecting")
            self.raf_instance.connect()
            self.raf_connected = True
        else:
            ait.core.log.error("RAF instance already connected")
            bottle.response.status = 400

    def rcf_connect_handler(self):
        if (not self.rcf_connected):
            self.rcf_instance.connect()
            self.rcf_connected = True
        else:
            ait.core.log.error("RCF instance already connected")
            bottle.response.status = 400

    def cltu_connect_handler(self):
        if (not self.rcf_connected):
            self.rcf_instance.connect()
            self.rcf_connected = True
        else:
            ait.core.log.error("CLTU instance already connected")
            bottle.response.status = 400

    def raf_bind_handler(self):
        if (not self.raf_connected):
            ait.core.log.error("RAF instance is not connected. Unable to bind.")
            bottle.response.status = 400
        else:
            if (not self.raf_bound):
                self.raf_instance.bind()
                self.raf_bound = True
            else:
                ait.core.log.error("RAF instance already bound")
                bottle.response.status = 400

    def rcf_bind_handler(self):
        if (not self.rcf_connected):
            ait.core.log.error("RCF instance is not connected. Unable to bind.")
            bottle.response.status = 400
        else:
            if (not self.rcf_bound):
                self.rcf_instance.bind()
                self.rcf_bound = True
            else:
                ait.core.log.error("RCF instance already bound")
                bottle.response.status = 400

    def cltu_bind_handler(self):
        if (not self.cltu_connected):
            ait.core.log.error("CLTU instance is not connected. Unable to bind.")
            bottle.response.status = 400
        else:
            if (not self.cltu_bound):
                self.cltu_instance.bind()
                self.cltu_bound = True
            else:
                ait.core.log.error("CLTU instance already bound")
                bottle.response.status = 400

    def raf_start_handler(self):
        if (not self.raf_connected):
            ait.core.log.error("RAF instance is not connected. Unable to start.")
            bottle.response.status = 400
        else:
            if (not self.raf_bound):
                ait.core.log.error("RAF instance is not bound. Unable to start.")
                bottle.response.status = 400
            else:
                if (not self.raf_started):
                    self.raf_instance.start() #need to add start and end times
                    self.raf_started = True
                else:
                    ait.core.log.error("RAF instance already started")
                    bottle.response.status = 400

    def rcf_start_handler(self):
        if (not self.rcf_connected):
            ait.core.log.error("RCF instance is not connected. Unable to start.")
            bottle.response.status = 400
        else:
            if (not self.rcf_bound):
                ait.core.log.error("RCF instance is not bound. Unable to start.")
                bottle.response.status = 400
            else:
                if (not self.rcf_started):
                    self.rcf_instance.start() #need to add start and end times
                    self.rcf_started = True
                else:
                    ait.core.log.error("RCF instance already started")
                    bottle.response.status = 400
                
    def cltu_start_handler(self):
        if (not self.cltu_connected):
            ait.core.log.error("CLTU instance is not connected. Unable to start.")
            bottle.response.status = 400
        else:
            if (not self.cltu_bound):
                ait.core.log.error("CLTU instance is not bound. Unable to start.")
                bottle.response.status = 400
            else:
                if (not self.cltu_started):
                    self.cltu_instance.start()
                    self.cltu_started = True
                else:
                    ait.core.log.error("CLTU instance already started")
                    bottle.response.status = 400

    def raf_stop_handler(self):
        if (not self.raf_started):
            ait.core.log.error("RAF instance is not started. Unable to stop.")
            bottle.response.status = 400
        else:
            self.raf_instance.stop()
            self.raf_started = False

    def rcf_stop_handler(self):
        if (not self.rcf_started):
            ait.core.log.error("RAF instance is not started. Unable to stop.")
            bottle.response.status = 400
        else:
            self.rcf_instance.stop()
            self.rcf_started = False

    def cltu_stop_handler(self):
        if (not self.cltu_started):
            ait.core.log.error("CLTU instance is not started. Unable to stop.")
            bottle.response.status = 400
        else:
            self.cltu_instance.stop()
            self.cltu_started = False

    def raf_unbind_handler(self):
        if (not self.raf_bound):
            ait.core.log.error("RAF instance is not bound. Unable to unbind.")
            bottle.response.status = 400
        else:
            self.raf_instance.unbind()
            self.raf_bound = False

    def rcf_unbind_handler(self):
        if (not self.rcf_bound):
            ait.core.log.error("RCF instance is not bound. Unable to unbind.")
            bottle.response.status = 400
        else:
            self.rcf_instance.unbind()
            self.rcf_bound = False

    def cltu_unbind_handler(self):
        if (not self.cltu_bound):
            ait.core.log.error("CLTU instance is not bound. Unable to unbind.")
            bottle.response.status = 400
        else:
            self.cltu_instance.unbind()
            self.cltu_bound = False

    def raf_disconnect_handler(self):
        if (not self.raf_connected):
            ait.core.log.error("RAF instance is not connected. Unable to disconnect.")
            bottle.response.status = 400
        else:
            self.raf_instance.disconnect()
            self.raf_connected = False

    def rcf_disconnect_handler(self):
        if (not self.rcf_connected):
            ait.core.log.error("RCF instance is not connected. Unable to disconnect.")
            bottle.response.status = 400
        else:
            self.rcf_instance.disconnect()
            self.rcf_connected = False

    def cltu_disconnect_handler(self):
        if (not self.cltu_connected):
            ait.core.log.error("CLTU instance is not connected. Unable to disconnect.")
            bottle.response.status = 400
        else:
            self.cltu_instance.disconnect()
            self.cltu_connected = False

    def cltu_upload_handler(self):
        wsock = bottle.request.environ.get('wsgi.websocket')
        if not wsock:
            ait.core.log.error("Expected WebSocket request")
            bottle.abort(400, 'Expected WebSocket request.')
        while True:
            try:
                tc_data = wsock.receive()
                self.cltu_instance.upload_cltu(tc_data)
            except geventwebsocket.WebSocketError:
                break


if __name__ == '__main__':
    DSN_server = DSN_server_class()

    Servers = []
    Greenlets = []

    Servers.append( gevent.pywsgi.WSGIServer(
    ('127.0.0.1', 7654),
    DSN_server.DSN_api,
    handler_class = geventwebsocket.handler.WebSocketHandler)
    )

    for s in Servers:
        s.serve_forever()

    @atexit.register
    def cleanup():
        
        for s in Servers:
            s.stop()

        gevent.killall(Greenlets)