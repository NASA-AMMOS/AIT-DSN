AIT SLE User Guide
==================

This user guide for AIT's SLE implementation assumes some familiarity with the SLE standards for `RAF <https://public.ccsds.org/Pubs/911x1b4.pdf>`_, `RCF <https://public.ccsds.org/Pubs/911x2b3.pdf>`_, and `F-CLTU <https://public.ccsds.org/Pubs/912x1b4.pdf>`_. An overview of these specs can be found in the AIT docs `here <https://ait-core.readthedocs.io/en/master/sle.html>`_. 

Downlink (RAF and RCF) 
^^^^^^^^^^^^^^^^^^^^^^

The :mod:`ait.dsn.sle.raf` module implements the `SLE Return All Frames (RAF) standard <https://public.ccsds.org/Pubs/911x1b4.pdf>`_, while the :mod:`ait.dsn.sle.rcf` module implements the `SLE Return Channel Frames (RCF) standard <https://public.ccsds.org/Pubs/911x2b3.pdf>`_. Both are extensions of the generic :mod:`ait.dsn.sle.common.SLE` class. An example script for using :mod:`ait.dsn.sle.raf`'s API is available in the AIT-DSN repository `here <https://github.com/NASA-AMMOS/AIT-DSN/blob/master/ait/dsn/bin/examples/rcf_api_test.py>`_. The :mod:`ait.dsn.sle.rcf` API is nearly identical and can be used in the same manner.

Online/Offline Connection
--------------------------


Uplink (F-CLTU)
^^^^^^^^^^^^^^^

The :mod:`ait.dsn.sle.cltu` module implements the `SLE Forward Communications Link Transmission Unit (F-CLTU) standard <https://public.ccsds.org/Pubs/912x1b4.pdf>`_ , and is an extension of the generic :class:`ait.dsn.sle.common.SLE` class. 

IMPORTANT NOTE: This is not the same functionality as outlined starting at Page 3-1 of the `CCSDS specification <https://public.ccsds.org/Pubs/201x0b3s.pdf>`_.