from ait.core.server.plugins import Plugin
from ait.core import log
from collections import defaultdict
from dataclasses import dataclass, field
from gevent import Greenlet, socket, select, sleep
import enum
import errno


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
    timeout_seconds: int = 5
    receive_size_bytes: int = 1024
    ip: str = field(init=False)
    socket: socket = field(init=False)
    log_name: str = field(init=False)

    def __post_init__(self):
        self.ip = None
        self.log_name = f"TCP -> {self.server_name} =>"
        if self.hostname:
            self.ip = socket.gethostbyname(self.hostname)
            self.socket = self.setup_client_socket()
        else:
            self.socket = self.setup_server_socket()
        self.mode = Mode[self.mode]

    def __del__(self):
        if hasattr(self, "socket") and self.socket:
            self.socket.close()

    def setup_server_socket(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setblocking(0)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('127.0.0.1', self.port))
            s.listen()

            msg = (f"{self.log_name} Started server "
                   f"for topic {self.topic} on port {self.port}")
            log.info(msg)

        except Exception as e:
            msg = (f"{self.log_name} Could not start "
                   f"server for topic {self.topic} "
                   f"on port {self.port}.")
            log.error(msg)
            log.error(e)
        return s

    def setup_client_socket(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setblocking(0)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        address = (self.ip, self.port)
        try:
            s.connect(address)
            msg = (f"{self.log_name} Connected "
                   f"to {self.hostname}:{self.port} "
                   f"subscribed to: {self.topic}")
            log.info(msg)

        except socket.error as e:
            if e.errno == errno.ECONNREFUSED:
                self.error_server_down()
            elif e.errno == errno.EINPROGRESS:
                # Previous connection attempt still in async progress
                pass
            else:
                log.error(f"{self.log_name} Unknown error: {e}")
        return s

    def error_client_reconnect(self):
        self.error_server_down()
        msg = f"{self.log_name} Attempting to establish connection."
        log.info(msg)
        sleep(5)
        self.socket = self.setup_client_socket()

    def error_server_down(self):
        msg = (f"{self.log_name} Failed to "
               f"send subscription {self.topic} "
               f"to {self.hostname}. Is the server down?")
        log.info(msg)
        
    def error_timeout(self):
        msg = (f"{self.log_name} send => We can't wait any longer! "
               f"{self.server_name} missed their window! "
               f"Dropping {self.topic} data!")
        log.info(msg)

    def error_timeout_reconnect(self):
        self.error_timeout()
        self.error_client_reconnect()
        
    def send_as_client(self, data):

        _, tx, _ = select.select([], [self.socket], [],
                                 self.timeout_seconds)
        if tx:
            try:
                self.socket.sendall(data)
                msg = (f"{self.log_name} Sending {self.topic} "
                       f"subscription to {self.hostname} {data}")
                log.debug(msg)

            except socket.error as e:
                if e.errno == errno.ECONNREFUSED:
                    self.error_client_reconnect()
        else:
            self.error_timeout_reconnect()
               
    def send_as_server(self, data):
        rx, tx, _ = select.select([self.socket], [self.socket], [],
                                 self.timeout_seconds)
        if tx or rx:
            sock, socket_info = self.socket.accept()
            sock.sendall(data)
            sock.close()
            msg = (f"{self.log_name} Pushed topic {self.topic} data "
                   f"to {socket_info}")
            log.debug(msg)

        else:
            self.error_timeout()
               
    def send(self, data):
        if self.ip:
            self.send_as_client(data)
        else:
            self.send_as_server(data)

    def recv_as_server(self):
        rx, _, _ = select.select([self.socket], [], [],
                                 self.timeout_seconds)
        if rx:
            sock, sock_info = self.socket.accept()
            data = sock.recv(self.receive_size_bytes)
            sock.close()
            msg = (f"{self.log_name} From client{sock_info}"
                   f"Pushed data to topic {self.topic}")
            log.debug(msg)
            return data

    def recv_as_client(self):
        rx, _, _ = select.select([self.socket], [], [],
                                 self.timeout_seconds)
        if rx:
            try:
                data = self.socket.recv(self.receive_size_bytes)
                msg = (f"{self.log_name} Receiving {self.topic} "
                       f"subscription from {self.hostname} {data}")
                log.debug(msg)
                return data

            except socket.error as e:
                if e.errno == errno.ECONNREFUSED:
                  self.error_client_reconnect()

    def recv(self):
        if self.ip:
            data = self.recv_as_client()
        else:
            data = self.recv_as_server()
        return data


class TCP_Manager(Plugin):
    """
    Customize the template within the config.yaml plugin block:

    - plugin:
        name: ait.dsn.plugins.TCP.TCP_Manager
        inputs:
            - PUB_SUB_TOPIC_1
            - PUB_SUB_TOPIC_2
        subscriptions:
            PUB_SUB_TOPIC_1:
                Server_Name1:
                    port: 42401
                    timeout: 1
                    mode: TRANSMIT
                Server_Name2:
                    port: 42401
                    hostname: someserver.xyz
                    mode: TRANSMIT
            PUB_SUB_TOPIC_2_RECEIVE:
                Server_Name3:
                    port: 12345
                    mode: RECEIVE
                Server_Name3:
                    port: 12346
                    host: localhost
                    mode: RECEIVE

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

        self.glet = Greenlet.spawn(self.handle_recv, self.rxs)

    def handle_recv(self, rxlist):
        while True:
            rxs, _, _ = select.select(rxlist, [], [])
            for rx in rxs:
                sub = self.socket_to_sub[rx]
                data = sub.recv()
                if data:
                    self.publish(data, sub.topic)
                    log.error(f"TCP=> Sending data to {sub.topic}")

    def process(self, data, topic=None):
        subs = self.topic_subscription_map[topic]
        subs = [sub for sub in subs if sub.mode is Mode.TRANSMIT]
        for sub in subs:
            sub.send(data)
        self.publish(data)
        return data
