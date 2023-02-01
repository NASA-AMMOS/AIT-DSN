from gevent import monkey
monkey.patch_all()

from ait.core.server.plugins import Plugin
from ait.core import log
from collections import defaultdict
from dataclasses import dataclass, field
from gevent import Greenlet, socket, select, sleep, time
import enum
import errno
import ait.dsn.plugins.Graffiti as Graffiti
from ait.core.message_types import MessageType
from sunrise.CmdMetaData import CmdMetaData

class Mode(enum.Enum):
    TRANSMIT = enum.auto()
    RECEIVE = enum.auto()


@dataclass
class Subscription:
    """
    Creates subscription.
    ip, socket, and log_header are derrived from the mandatory fields.
    """
    topic: str
    server_name: str
    mode: Mode
    hostname: str = None
    port: int = 0
    timeout_seconds: int = 5
    receive_size_bytes: int = 64000
    ip: str = field(init=False)
    socket: socket = field(init=False)
    log_header: str = field(init=False)

    def __post_init__(self):
        """
        Sets up client/server sockets.
        Derrives IP from hostname, if provided in config.
        """
        self.ip = None
        self.log_header = f":-> {self.server_name} :=>"
        if self.hostname:
            self.ip = socket.gethostbyname(self.hostname)
            self.socket = self.setup_client_socket()
        else:
            self.socket = self.setup_server_socket()
        self.mode = Mode[self.mode]
        self.sent_counter = 0
        self.receive_counter = 0

    def __del__(self):
        """
        Shutdown and close open socket, if any.
        """
        if hasattr(self, "socket") and self.socket:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()

    def status_map(self):
        m = {'topic': self.topic,
             'host': self.hostname, 
             'port': self.port,
             'mode': self.mode.name, 
             'Tx_Count': self.sent_counter,
             'Rx_Count': self.receive_counter}
        return m

    def setup_server_socket(self):
        """
        Returns a non blocking server socket.
        :returns: a non blocking server socket.
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setblocking(0)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('127.0.0.1', self.port))
            s.listen()

            log.info((f"{self.log_header} Started server "
                      f"for topic {self.topic} on port {self.port}"))

        except Exception as e:
            log.error((f"{self.log_header} Could not start "
                       f"server for topic {self.topic} "
                       f"on port {self.port}."))
            log.error(e)
        return s

    def setup_client_socket(self):
        """
        Returns non blocking client socket.
        :returns: a non blocking client socket.
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setblocking(0)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        address = (self.ip, self.port)
        try:
            s.connect(address)
            msg = (f"{self.log_header} Connected "
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
                log.error(f"{self.log_name} -> setup_client_socket => "
                          f"Unknown error: {e}")
        return s

    def client_reconnect(self):
        """
        Attempt to reestablish a client socket that has thrown
        an error.
        """
        log.info(f"{self.log_header} {self.topic} Attempting "
                 "to establish connection.")
        sleep(5)
        self.socket = self.setup_client_socket()

    def error_server_down(self):
        """
        Use to log an error when server can not be reached.
        """
        log.error((f"{self.log_header} Failed to "
                   f"process subscription {self.topic} "
                   f"to {self.hostname}. Is the server down?"))

    def error_timeout(self):
        """
        Warn user that the receiving process missed the topic data because
        the timeout has been reached. This data is considered stale and will be
        dropped.

        The receiving process has a user defined timeout to allow for
        occassions where the receiving process has backed up and not collected
        topic data.

        This is called whenever select returns without any ready sockets.

        This means the receiving process is unreachable, or
        the connection has been interrupted.
        """
        log.info((f"{self.log_header} send => We can't wait any longer! "
                  f"{self.server_name} missed their window! "
                  f"Dropping {self.topic} data!"))

    def send_as_client(self, data):
        """
        Sends data through a client socket.

        Will attempt to reconnect if the connection can not be established.
        Will attempt to reconnect if the receiving process
        does not respond before the user defined timeout is reached.
        """

        _, tx, _ = select.select([], [self.socket], [],
                                 self.timeout_seconds)
        if tx:
            try:
                self.socket.sendall(data)
                msg = (f"{self.log_header} Sending {self.topic} "
                       f"subscription to {self.hostname} {data}")
                log.debug(msg)
            except socket.error as e:
                if e.errno == errno.ECONNREFUSED:
                    self.error_timeout()
                else:
                    log.error(f"{self.log_header} received error: {e}")
                    self.client_reconnect()

    def send_as_server(self, data):
        """
        Sends data through a server socket and closes the connection.

        Will log error_timeout and drop data if the client does not
        connect before the user defined timeout is reached.
        """
        try:
            rx, tx, _ = select.select([self.socket], [self.socket], [],
                                      self.timeout_seconds)
        except ValueError:
            log.debug(f"{self.log_header} socket was "
                      "unexpectedly closed elsewhere.")
            rx = []
            tx = []
        except Exception as e:
            log.error(f"{self.log_header} received exception {e}")
            rx = []
            tx = []

        if tx or rx:
            sock, socket_info = self.socket.accept()
            sock.sendall(data)
            sock.shutdown(socket.SHUT_RDWR)
            sock.close()
            log.debug((f"{self.log_header} Pushed topic {self.topic} data "
                       f"to {socket_info}"))

        else:
            self.error_timeout()

    def send(self, data):
        """
        Decides whether to send data as a client socket or server socket.

        Path is dependant on whether a hostname is provided in the
        plugin configuration (self.ip is derrived from a hostname)
        """
        if self.ip:
            self.send_as_client(data)
        else:
            self.send_as_server(data)
        self.sent_counter += 1

    def recv_as_server(self):
        """
        Receive data as a server.

        :returns: data received from client or none

        Will return none if the user defined timeout is reached.
        """
        rx, _, _ = select.select([self.socket], [], [],
                                 self.timeout_seconds)
        if rx:
            sock, sock_info = self.socket.accept()
            data = sock.recv(self.receive_size_bytes)
            sock.close()
            log.debug(f"{self.log_header} From client {sock_info} to "
                      f"{self.topic}: (len:{len(data)}, data:{data}")
            return data

    def recv_as_client(self):
        """
        Receive data as a client.

        :returns: data received from server or none

        Will return none if the user defined timeout is reached.
        Will attempt to error_client_reconnect if server can not
        be reached.
        """
        rx, _, _ = select.select([self.socket], [], [],
                                 self.timeout_seconds)
        if rx:
            try:
                data = self.socket.recv(self.receive_size_bytes)
                if not data:
                    log.error(f"{self.log_header} received "
                              f"EOF from {self.hostname}. "
                              "Closing socket and attempting to reconnect.")
                    self.socket.shutdown(socket.SHUT_RDWR)
                    self.socket.close()
                    self.client_reconnect()
                else:
                    log.debug(f"{self.log_header} Receiving {self.topic} "
                              f"subscription from {self.hostname}: "
                              f"(len:{len(data)}, data:{data}")
                    return data

            except socket.error as e:
                if e.errno == errno.ECONNREFUSED:
                    self.error_server_down()
                else:
                    log.error(f"{self.log_header} received error {e}")
                self.client_reconnect()

    def recv(self):
        """
        Decides whether to receive data as a client socket or server socket.

        Path is dependant on whether a hostname is provided in the
        plugin configuration (self.ip is derrived from a hostname)
        """
        if self.ip:
            data = self.recv_as_client()
        else:
            data = self.recv_as_server()
        self.receive_counter += 1
        return data


class TCP_Manager(Plugin, Graffiti.Graphable):
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
            PUB_SUB_TOPIC_3_RECEIVE:
                Server_Name3:
                    port: 12345
                    receive_size_bytes: 1024
                    mode: RECEIVE
                Server_Name4:
                    port: 12346
                    host: localhost
                    receive_size_bytes: 512
                    mode: RECEIVE

    See documentation for more details.
    """

    def __init__(self, inputs=None, outputs=None, zmq_args=None,
                 subscriptions={}, report_time_s=0, **kwargs):
        """
        Create Subscriptions based on config.yaml entries.
        Forks a process to handle receiving subscriptions.
        Creates auxillary socket maps and lists.
        """
        super().__init__(inputs, outputs, zmq_args)
        self.report_time_s = report_time_s
        self.topic_subscription_map = defaultdict(list)
        self.socket_to_sub = {}
        self.rxs = []
        self.txs = []

        for (topic, servers) in subscriptions.items():
            for (server, mode_info) in servers.items():
                sub = Subscription(topic, server, **mode_info)
                self.topic_subscription_map[topic].append(sub)
                self.socket_to_sub[sub.socket] = sub
                if sub.mode is Mode.RECEIVE:
                    self.rxs.append(sub)
                if sub.mode is Mode.TRANSMIT:
                    self.txs.append(sub)

        self.glet = Greenlet.spawn(self.handle_recv)
        self.supervisor_tree = Greenlet.spawn(self.supervisor_tree)

        Graffiti.Graphable.__init__(self)


    def handle_recv(self):
        """
        Block until a receiving Subscription's socket has data
        to collect.

        :returns: data from an external process or none
        """
        while True:
            sockets = []
            socket_to_sub = {}
            for sub in self.rxs:
                sockets.append(sub.socket)
                socket_to_sub[sub.socket] = sub
            try:
                rxs, _, _ = select.select(sockets, [], [])
            except ValueError:
                log.debug(f"socket was unexpectedly closed elsewhere.")
            except Exception as e:
                log.error(f"received exception: {e}")
            finally:
                rx = []

            for rx in rxs:
                sub = socket_to_sub[rx]
                data = sub.recv()
                if data:
                    self.publish(data, sub.topic)
                    log.debug(f"Sending data to {sub.topic}")

    def process(self, data, topic=None):
        """
        Send data to the transmit Subscriptions associated with topic.

        :returns: data from topic
        """
        if not data:
            log.info('Received no data')
            return
        subs = self.topic_subscription_map[topic]
        subs = [sub for sub in subs if sub.mode is Mode.TRANSMIT]
        for sub in subs:
            if isinstance(data, CmdMetaData):
                sub.send(data.payload_bytes)
            else:
                sub.send(data)
        self.publish(data)
        if isinstance(data, CmdMetaData):
            self.publish(data, MessageType.CL_UPLINK_COMPLETE.name)
        return data

    def graffiti(self):
        nodes = []

        n = Graffiti.Node(self.self_name,
                          inputs=[(i, "PUB/SUB Message") for i in self.inputs],
                          outputs=[],
                          label="",
                          node_type=Graffiti.Node_Type.PLUGIN)

        nodes.append(n)

        for (topic, subs) in self.topic_subscription_map.items():
            for sub in subs:
                if sub.mode is Mode.TRANSMIT:
                    n = Graffiti.Node(self.self_name,
                                      inputs=[],
                                      outputs=[(sub.hostname,
                                                f"{sub.topic}\n"
                                                f"Port: {sub.port}")],
                                      label="Manage TCP Transmit and Receive",
                                      node_type=Graffiti.Node_Type.TCP_SERVER)

                else:  # sub.mode is Mode.RECEIVE:
                    n = Graffiti.Node(self.self_name,
                                      inputs=[(sub.hostname,
                                               f"{sub.topic}\n"
                                               f"Port: {sub.port}")],
                                      outputs=[(sub.topic, "Bytes"),],
                                      label="Manage TCP Transmit and Receive",
                                      node_type=Graffiti.Node_Type.TCP_CLIENT)
                nodes.append(n)
                
        n = Graffiti.Node(self.self_name,
                          inputs=[],
                          outputs=[(MessageType.TCP_STATUS.name,
                                    MessageType.TCP_STATUS.value)],
                          label="Manage TCP Transmit and Receive",
                          node_type=Graffiti.Node_Type.TCP_CLIENT)
        nodes.append(n)
        return nodes
    
    def supervisor_tree(self, msg=None):
        
        def periodic_report(report_time=5):
            while True:
                time.sleep(report_time)
                msg = []
                for sub_list in self.topic_subscription_map.values():
                    msg += [i.status_map() for i in sub_list]
                log.debug(msg)
                self.publish(msg,  MessageType.TCP_STATUS.name)

        def high_priority(msg):
            # self.publish(msg, "monitor_high_priority_cltu")
            pass
        
        def monitor(restart_delay_s=5):
            # self.connect()
            # while True:
            #     time.sleep(restart_delay_s)
            #     if self.CLTU_Manager._state == 'active':
            #         log.debug(f"SLE OK!")
            #     else:
            #         self.publish("CLTU SLE Interface is not active!", "monitor_high_priority_cltu")
            #         self.handle_restart()
            pass

        if msg:
            high_priority(msg)
            return
           
        if self.report_time_s:
            reporter = Greenlet.spawn(periodic_report, self.report_time_s)
        #mon = Greenlet.spawn(monitor, self.restart_delay_s)
     
