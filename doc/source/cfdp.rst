AIT's CFDP Implementation
=========================

The CFDP (`CCSDS <https://public.ccsds.org/default.aspx>`_ File Delivery Protocol) defines a standard for space-to-ground, ground-to-space, and space-to-space file transfer, which may be initiated by the file sending or receiving entity. This documentation of AIT's CFDP implementation assumes some familiarity with the `CFDP standard <https://public.ccsds.org/pubs/727x0b4.pdf>`_. The implementation closely follows the `Implementer's Guide<https://public.ccsds.org/Pubs/720x2g3ec1.pdf>`_.

Transmission Modes
------------------
AIT currently provides an implementation of CFDP **Class 1** for *unreliable transfer* with a transmission mode of *unacknowledged*. An implementation of the protocol's **Class 2**, for *reliable transfer* with an *acknowledged* transmission mode, is in the works. Currently the toolkit will use **Class 1** no matter what transmission mode is requested. In the future, either **Class 1** or **Class 2** will be used based on the transmission mode specified in the :ref:`MIB configuration <MIB>`

.. _MIB:
The MIB
--------
The MIB, or Management Information Base, is where configurations for the protocol, such as the transmission mode, timeouts and limits, are specified, stored and accessed. The default MIB contents are stored in :mod:`ait.dsn.cfdp.mib`.

Custom MIB Files
^^^^^^^^^^^^^^^^^
When a CFDP entity (:mod:`ait.dsn.cfdp.cfdp.CFDP`) is instantiated, it will look for custom MIB files in the directory specified by `dsn.cfdp.mib.path` in the AIT configuration file whose location is indicated by the `AIT_CONFIG` `environment variable<https://ait-core.readthedocs.io/en/master/installation.html#environment-configuration>`_ set during installation. If you have AIT-Core installed, the `AIT_CONFIG` will likely point to `/path/to/ait-core/config/config.yaml`, and if you have not changed `dsn.cfdp.mib.path` in this file, it will likely point to `/path/to/ait-core/config/mib`. If you would like to store your MIB files elsewhere, update this configuration. If `dsn.cfdp.mib.path` is not present in the config.yaml, the MIB location will default to `/tmp/cfdp/mib`.

If no custom MIB files are found in the specified location, the default MIB contents will be used. When an entity is disconnected, it will dump both its local and remote MIB contents to the MIB directory described above.


