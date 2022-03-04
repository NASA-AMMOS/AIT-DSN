AIT SLE User Guide
==================

The TCP forwarding plugin facilitates forwarding pipeline data over TCP.
The plugin can be configured for an arbitrary number of server or clients for each PUB/SUB topic. 

Configuration
^^^^^^^^^^^^^
Customize the template within the config.yaml plugin block:

.. code-block:: none

    - plugin:
        name: ait.dsn.plugins.TCP_Forward.TCP_Forward
        inputs:
            - PUB_SUB_TOPIC_1 # This is a subscription
            - PUB_SUB_TOPIC_2
        subscriptions:
            PUB_SUB_TOPIC_1: # This is the subscription configuration
                Server_Name1: # This is a connection.
                    port: 42401 # Mandatory
                    timeout_seconds: 1  
                Server_Name2: # Another connection for the same topic subscription.
                    port: 42401
                    host: hostname # Client mode
            PUB_SUB_TOPIC_2: # Another subscription
                Server_Name3: 
                    port: 12345 

* The value *PUB_SUB_TOPIC_1* corresponds to a PUB/SUB topic that should be subscribed to (i.e. another plugin).

* The value *Server_Name1* is an arbitrary nickname for the connection.

* The *port* option is mandatory for all connections.

* The *hostname* option is optional.
  + When defined, the plugin will attempt to establish connection to this server (Client Mode).
  + When undefined, the plugin will start its own server that clients can receieve data from (Server Mode).

* The *timeout_seconds* option specifies how long a Server Mode connection should wait for a client before giving up and dropping the data.
