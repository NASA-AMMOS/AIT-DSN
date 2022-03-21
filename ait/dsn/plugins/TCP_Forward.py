from ait.core.server.plugins import Plugin
import ait.core
from collections import defaultdict
import socket
from dataclasses import dataclass, field
from gevent import Greenlet
import select
import enum


class Mode(enum.Enum):
    TRANSMIT = enum.auto()
    RECEIVE = enum.auto()


@dataclass
class Subscription:
    topic: str
    server_name: str
    mode: Mode 
    hostname: str = None
    port: int = 0
    timeout_seconds: int = 10
    ip: str = field(init=False)
    socket: socket = field(init=False)
    log_name: str = field(init=False)

    def __post_init__(self):
        self.ip = None
        self.log_name = f"TCP_Forward -> {self.server_name} =>"
        if self.hostname:
            self.ip = socket.gethostbyname(self.hostname)
            self.socket = self.setup_client_mode()
        else:
            self.socket = self.setup_server_mode()
        self.mode = Mode[self.mode]

    def __del__(self):
        if hasattr(self, "socket") and self.socket:
            print(f"CLOSING {self}")
            self.socket.close()

    def setup_server_mode(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('127.0.0.1', self.port))
            # s.setblocking(False)
            s.settimeout(self.timeout_seconds)
            s.listen()

            msg = f"{self.log_name} Started server "
            msg += f"for topic {self.topic} on port {self.port} "
            ait.core.log.error(msg)

        except Exception as e:
            msg = f"{self.log_name} Could not start "
            msg += f"server for topic {self.topic} "
            msg += f"on port {self.port}."
            ait.core.log.error(msg)
            ait.core.log.error(e)
        return s

    def setup_client_mode(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # s.setblocking(False)
        address = (self.ip, self.port)
        try:
            s.connect(address)
            ait.core.log.info(f"{self.log_name} Connected "
                              f"to {self.hostname}:{self.port} "
                              f"subscribed to: {self.topic}")

        except Exception as e:
            msg = "Failed to "
            msg += f"connect to {self.hostname} on {address}. "
            msg += "Is the server down? "
            ait.core.log.error(f"{self.log_name} {msg}")
            ait.core.log.error(f"{self.log_name} {e}")
        return s

    def process_as_client(self, data):
        if self.socket:
            try:
                self.socket.sendall(data)
                msg = f"{self.log_name} Sending {self.topic} "
                msg += f"subscription to {self.hostname} {data}"
                ait.core.log.error(msg)

            except Exception as e:
                msg = f"{self.log_name} Failed to send subscription {self.topic} "
                msg += f"to {self.hostname}. Is the server down?"
                ait.core.log.error(f"{self.log_name} {msg} {e}")
                self.socket = self.setup_client_mode()
        else:
            msg = f"{self.log_name} Could not find socket "
            msg += f"for {self.hostname}:{self.port}. "
            msg += "Unable to initialize a connection!"
            ait.core.log.error(msg)
            self.socket = self.setup_client_mode()

    def process_as_server(self, data):
        try:
            client, client_info = self.socket.accept()
            client.sendall(data)
            client.close()
            msg = f"{self.log_name} Pushed topic {self.topic} data "
            msg += f"to {client_info}"
            ait.core.log.error(msg)

        except socket.timeout:
            msg = f"{self.log_name}=>PROCESS We can't wait any longer! "
            msg += f"{self.server_name} missed their window! "
            msg += f"Dropping {self.topic} data!"
            # ait.core.log.info(msg)

    def send(self, data):
        if self.ip:
            self.process_as_client(data)
        else:
            self.process_as_server(data)

    def recv_as_server(self):
        data = None
        if not self.socket:
            print("LAMAO")
            return data
        try:
            client, client_info = self.socket.accept()
            data = client.recv(4790)
            client.close()
            msg = f"{self.log_name} From client{client_info}"
            msg = f"Pushed data to topic {self.topic}"
            ait.core.log.debug(msg)

        except socket.timeout:
            msg = f"{self.log_name}=RECV We can't wait any longer! "
            msg += f"{self.server_name}=>RECV missed their window! "
            msg += f"Dropping {self.topic} data!"
            ait.core.log.info(msg)

        # except Exception as e:
        #     msg = f"{self.log_name}=RECV Encountered error. "
        #     msg += f"{self.server_name} {e}"
        #     ait.core.log.error(msg)
            
        return data

    def recv_as_client(self):
        data = None
        if self.socket:
            try:
                data = self.socket.recv(4790) #CONFIG VAL
                msg = f"{self.log_name} Receiving {self.topic} "
                msg += f"subscription from {self.hostname} {data}"
                ait.core.log.debug(msg)

            except Exception as e:
                msg = f"{self.log_name} Failed to recieve subscription {self.topic} "
                msg += f"to {self.hostname}. Is the server down?"
                ait.core.log.error(f"{self.log_name} {msg} {e}")
                self.socket = self.setup_client_mode()
        else:
           msg = f"{self.log_name} Could not find socket "
           msg += f"for {self.hostname}:{self.port}. "
           msg += "Unable to initialize a connection!"
           ait.core.log.error(msg)
           self.socket = self.setup_client_mode()

        return data
    
    def recv(self):
        if self.ip:
            data = self.recv_as_client()
        else:
            data = self.recv_as_server()
        if data:
            #print ("RECV ", data)
            pass
        return data

class TCP_Forward(Plugin):
    """
    Customize the template within the config.yaml plugin block:

    - plugin:
        name: ait.dsn.plugins.TCP_Forward.TCP_Forward
        inputs:
            - PUB_SUB_TOPIC_1
            - PUB_SUB_TOPIC_2
        subscriptions:
            PUB_SUB_TOPIC_1:
                Server_Name1:
                    port: 42401
                    timeout: 1
                Server_Name2:
                    port: 42401
                    ip: 127.0.0.1
            PUB_SUB_TOPIC_2:
                Server_Name3:
                    port: 12345

    See documentation for more details.
    """

    def __init__(self, inputs=None, outputs=None, zmq_args=None,
                 subscriptions={}, *kwargs):
        super().__init__(inputs, outputs, zmq_args)
        self.topic_subscription_map = defaultdict(list)
        self.socket_to_sub = {}
        self.rxs = []

        for (topic, servers) in subscriptions.items():
            for (server, mode_info) in servers.items():
                sub = Subscription(topic, server, **mode_info)
                self.topic_subscription_map[topic].append(sub)
                self.socket_to_sub[sub.socket] = sub
                if sub.mode is Mode.RECEIVE:
                    self.rxs.append(sub.socket)
                print(type(sub.mode))
                print(self.rxs)
        
        self.glet = Greenlet.spawn(self.handle_recv, self.rxs)
        Greenlet.spawn(self.graffiti)
                    
    def handle_recv(self, rxlist):
        while True:
            rxs, txs, errs = select.select(rxlist, [], [])
            for rx in rxs:
                #ait.core.log.error(f"GOT A SIGNAL!")
                sub = self.socket_to_sub[rx]
                data = sub.recv()
                if data:
                    self.publish(data, sub.topic)
                    #ait.core.log.error(f"Sending data to {sub.topic}")

    def handle_transmit(self, data, txsubs):
        # txlist = [sub.socket for ub in txsubs]
        # print("LOL")
        # print(txlist)
        # _, txs, _ = select.select([], txlist, [])
        # print("LOLOLOL")
        # for tx in txs:
        #     sub = self.socket_to_sub[tx]
        #     sub.send(data)
        #     print("LOLAPALOOZA") #TODO BLOCKS FOREVER LOL!
        for tx in txsubs:
            tx.send(data)
                    
    def process(self, data, topic=None):
        subs = self.topic_subscription_map[topic]
        subs = [sub for sub in subs if sub.mode is Mode.TRANSMIT]
        self.handle_transmit(data, subs)
        self.publish(data)
        return data

    def graffiti(self):
        # x=DFG.Node(name=TCP_Forward, inputs=[], outputs=[], label="TEST", node_type=DFG.Node_Type.PLUGIN)
        # self.publish(x, 'Graffiti')
        pass
