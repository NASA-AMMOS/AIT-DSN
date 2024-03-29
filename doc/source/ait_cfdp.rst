AIT CFDP User Guide
====================

This user guide for AIT's CFDP implementation assumes some familiarity with the `CFDP standard <https://public.ccsds.org/pubs/727x0b4.pdf>`_. An overview can be found in the AIT docs `here <https://ait-core.readthedocs.io/en/master/cfdp.html>`_. The implementation closely follows the `Implementer's Guide <https://public.ccsds.org/Pubs/720x2g3ec1.pdf>`_.

Creating a CFDP Entity
^^^^^^^^^^^^^^^^^^^^^^
CFDP entities are implemented by the :mod:`ait.dsn.cfdp.cfdp.CFDP` class. CFDP entities must be instantiated with an entity ID. To connect an entity to a socket, call the ``connect`` method of the CFDP object, passing in the a tuple of the host and port to connect to (example below). The ``put`` method can be used to initiate a transaction with destination ID, source path, destination path, and optional transmission mode parameters (example below). More complete examples can be found in **ait/dsn/bin**.

.. code-block:: python

    import ait.dsn.cfdp
    from ait.dsn.cfdp.primitives import TransmissionMode

    cfdp = ait.dsn.cfdp.CFDP(1)

    cfdp.connect(('127.0.0.1', 9001))

    cfdp.put(2, 'path/to/sourcefile', 'path/to/destfile', transmission_mode=TransmissionMode.NO_ACK)

    cfdp.disconnect()



Transmission Modes
^^^^^^^^^^^^^^^^^^
AIT currently provides an implementation of CFDP **Class 1** for *unreliable transfer* with a transmission mode of *unacknowledged*. An implementation of the protocol's **Class 2**, for *reliable transfer* with an *acknowledged* transmission mode, is in the works. Currently the toolkit will use **Class 1** no matter what transmission mode is requested. In the future, either **Class 1** or **Class 2** will be used based on the transmission mode specified in the :ref:`MIB configuration <MIB>`.

.. _MIB:
The MIB
^^^^^^^
The MIB, or Management Information Base, is where configurations for the protocol, such as the transmission mode, timeouts and limits, are specified, stored and accessed. The default MIB contents are stored in :mod:`ait.dsn.cfdp.mib`.

Custom MIB Files
""""""""""""""""
When a CFDP entity (:mod:`ait.dsn.cfdp.cfdp.CFDP`) is instantiated, it will look for custom MIB files in the directory specified by :mod:`dsn.cfdp.mib.path` in the AIT configuration file whose location is indicated by the **AIT_CONFIG** `environment variable <https://ait-core.readthedocs.io/en/master/installation.html#environment-configuration>`_ set during installation. If you have AIT-Core installed, the **AIT_CONFIG** will likely point to **/path/to/ait-core/config/config.yaml**, and if you have not changed :mod:`dsn.cfdp.mib.path` in this file, it will likely point to **/path/to/ait-core/config/mib**. If you would like to store your MIB files elsewhere, update this configuration. If :mod:`dsn.cfdp.mib.path` is not present in the config.yaml, the MIB location will default to **/tmp/cfdp/mib**.

If no custom MIB files are found in the specified location, the default MIB contents will be used. When an entity is disconnected, it will dump both its local and remote MIB contents to the MIB directory described above.

MIB Configuration
"""""""""""""""""
The local and remote configurable MIB fields and their defaults are described below.

**Local MIB Fields**

* ``'entity_id'`` - the local CFDP entity ID; defaults to 1.

* ``'issue_eof_sent'`` - whether or not to issue an end-of-file sent indication; defaults to True.

* ``'issue_eof_recv'`` - whether or not to issue an end-of-file received indication; defaults to False.

* ``'issue_file_segment_recv'`` - whether or not to issue a file data segment received indication; defaults to False.

* ``'issue_transaction_finished'`` - whether or not to issue a transaction finished indication; defaults to False.

* ``'issue_suspended'`` - whether or not to issue a transaction suspended indication; defaults to True.

* ``'issue_resumed'`` - whether or not to issue a transaction resumed indication; defaults to True.

* ``'fault_handlers'`` - fault handler overwritten by the metadata PDU of a transaction; defaults to Ignore.

**Remote MIB Fields**

* ``'entity_id'`` - the remote CFDP entity ID; defaults to None.

* ``'ut_address'`` - the UT address for transmitting to this remote entity; defaults to None.

* ``'ack_limit'`` - the positive ACK count limit (number of expirations); defaults to 3.

* ``'ack_timeout'`` - the ACK timeout time in seconds; defaults to 10.

* ``'inactivity_timeout'`` - the inactivity time limit for a transaction; defaults to 30.

* ``'nak_timeout'`` - the time interval for NAK; defaults to 10.

* ``'nak_limit'`` - the limit on number of NAK expirations; defaults to 3.

* ``'maximum_file_segment_length'`` - the maximum file segment length in octets; defaults to 4096.

* ``'transmission_mode'`` - the transmission mode; defaults to NO_ACK.

* ``'crc_required_on_transmission'`` - whether a CRC is required on each transmission; defaults to False.
