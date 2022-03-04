from ait.core.server.plugins import Plugin
import ait.core
from collections import defaultdict
import socket
from dataclasses import dataclass, field


@dataclass
class Subscription:
    topic: str
    server_name: str
    hostname: str = None
    port: int = 0
    timeout_seconds: int = 1
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

    def __del__(self):
        if self.socket:
            self.socket.close()

    def setup_server_mode(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('127.0.0.1', self.port))
            s.settimeout(self.timeout_seconds)
            s.listen()

            msg = f"{self.log_name} Started server "
            msg += f"for topic {self.topic} on port {self.port} "
            ait.core.log.debug(msg)

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
                ait.core.log.debug(msg)

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
            ait.core.log.debug(msg)

        except socket.timeout:
            msg = f"{self.log_name} We can't wait any longer! "
            msg += f"{self.server_name} missed their window! "
            msg += f"Dropping {self.topic} data!"
            ait.core.log.info(msg)

    def send(self, data):
        if self.ip:
            self.process_as_client(data)
        else:
            self.process_as_server(data)


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

        for (topic, servers) in subscriptions.items():
            for (server, mode_info) in servers.items():
                hostname = mode_info.get('hostname', None)
                port = mode_info['port']
                timeout_seconds = mode_info.get('timeout_seconds')
                sub = Subscription(topic, server, hostname,
                                   port, timeout_seconds)
                self.topic_subscription_map[topic].append(sub)

    def process(self, data, topic=None):
        subs = self.topic_subscription_map[topic]
        for sub in subs:
            sub.send(data)

        self.publish(data)
        return data
