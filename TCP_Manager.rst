AIT SLE User Guide
==================

The TCP forwarding plugin facilitates forwarding pipeline data over TCP.
The plugin can be configured for an arbitrary number of server or clients for each PUB/SUB topic. 

Configuration
^^^^^^^^^^^^^
Customize the template within the config.yaml plugin block:

.. code-block:: none

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
                Server_Name4:
                    port: 12346
                    host: localhost
                    mode: RECEIVE

* The value *PUB_SUB_TOPIC_1* corresponds to a PUB/SUB topic that should be subscribed to (i.e. another plugin).

* The value *Server_Name1* is an arbitrary nickname for the connection.

* The *port* option is mandatory for all connections.  

* The *hostname* field is optional.
  + When defined, the plugin will attempt to establish connection to this server (Client Mode).
  + When undefined, the plugin will start its own server that clients can receieve data from (Server Mode).

* The *mode* field is mandatory.
  + *mode:TRANSMIT* specifies that the connection will forward data from the PUB/SUB topic to the specified TCP client/server.
  + *mode:RECEIVE* specifies that the connection will forward data from the specified TCP client/server to the specified PUB/SUB topic.
* The *timeout_seconds* option specifies how long a Server Mode connection should wait for a client before giving up and dropping the data.

  
