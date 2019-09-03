AIT SLE User Guide
==================

This user guide for AIT's SLE implementation assumes some familiarity with the SLE standards for `RAF <https://public.ccsds.org/Pubs/911x1b4.pdf>`_, `RCF <https://public.ccsds.org/Pubs/911x2b3.pdf>`_, and `F-CLTU <https://public.ccsds.org/Pubs/912x1b4.pdf>`_. An overview of these specs can be found in the AIT docs `here <https://ait-core.readthedocs.io/en/master/sle.html>`_. 

Configuration
^^^^^^^^^^^^^

The necessary configuration parameters for all protocols can be added to the **config.yaml**. Optionally, many of them can also be passed in at runtime for greater flexibility. Below is an example configuration which can be used as a reference, in addition to the default configuration available in the repository.

AIT will attempt connection to all of the provided hostnames and use whichver successfully connects first.

.. code-block:: yaml

    dsn:
        sle:
            initiator_id: LSE
            password: lse_pw
            responder_id: SSE
            peer_password: sse_pw
            version: 5
            downlink_frame_type: TMTransFrame
            heartbeat: 25
            deadfactor: 5
            buffer_size: 256000
            responder_port: 'default'
            auth_level: 'none'
            rcf:
                inst_id: sagr=LSE-SSC.spack=Test.rsl-fg=1.rcf=onlc2
                hostnames:
                    - example.hostname.1
                    - example.hostname.2
                port: 5111
            raf:
                inst_id: None
                hostnames:
                    - example.hostname.1
                    - example.hostname.2
                port: None
            fcltu:
                inst_id: None
                hostnames:
                    - example.hostname.1
                    - example.hostname.2
                port: None


Downlink (RAF and RCF) 
^^^^^^^^^^^^^^^^^^^^^^

The :mod:`ait.dsn.sle.raf` module implements the `SLE Return All Frames (RAF) standard <https://public.ccsds.org/Pubs/911x1b4.pdf>`_, while the :mod:`ait.dsn.sle.rcf` module implements the `SLE Return Channel Frames (RCF) standard <https://public.ccsds.org/Pubs/911x2b3.pdf>`_. Both are extensions of the generic :mod:`ait.dsn.sle.common.SLE` class. 

An example script for using AIT's RCF API is shown below and available in the AIT-DSN repository `here <https://github.com/NASA-AMMOS/AIT-DSN/blob/master/ait/dsn/bin/examples/rcf_api_test.py>`_. AIT's RAF API is nearly identical and can be used in the same manner. The only differences are the parameters for the ``start`` call as shown in the the documentation for :meth:`ait.dsn.sle.raf.start` vs :meth:`ait.dsn.sle.rcf.start`.

.. code-block:: python

    import datetime as dt
    import time

    import ait.dsn.sle

    rcf_mngr = ait.dsn.sle.RCF(
        hostname='atb-ocio-sspsim.jpl.nasa.gov',
        port=5100,
        inst_id='sagr=LSE-SSC.spack=Test.rsl-fg=1.rcf=onlc2',
        spacecraft_id=250,
        trans_frame_ver_num=0,
        version=4,
        auth_level="none"
    )

    rcf_mngr.connect()
    time.sleep(2)

    rcf_mngr.bind()
    time.sleep(2)

    start = dt.datetime(2017, 01, 01)
    end = dt.datetime(2019, 01, 01)
    rcf_mngr.start(start, end, 250, 0, virtual_channel=6)
    time.sleep(2)

    rcf_mngr.stop()
    time.sleep(2)

    rcf_mngr.unbind()
    time.sleep(2)

    rcf_mngr.disconnect()
    time.sleep(2)



Online vs. Offline Connection
-----------------------------

An online connection to RAF or RCF delivers telemetry in realtime, while an offline connection delivers telemetry between a start time and an end time. An offline connection can also be used to receive realtime data if a start time in the past and an end time in the future are used.

.. list-table::  
    :widths: 25 25 50
    :header-rows: 1

    * - 
      - Online
      - Offline 
    * - Use
      - Realtime
      - Historical
    * - Start/End times 
      - ``None`` types
      - ``datetime.datetime`` 's


Uplink (F-CLTU)
^^^^^^^^^^^^^^^

The :mod:`ait.dsn.sle.cltu` module implements the `SLE Forward Communications Link Transmission Unit (F-CLTU) standard <https://public.ccsds.org/Pubs/912x1b4.pdf>`_ , and is an extension of the generic :class:`ait.dsn.sle.common.SLE` class. 

An example script for using AIT's F-CLTU API is shown below and available in the AIT-DSN repository `here <https://github.com/NASA-AMMOS/AIT-DSN/blob/master/ait/dsn/bin/examples/cltu_api_test.py>`_.

.. code-block:: python

    import datetime as dt
    import time

    import ait.dsn.sle

    cltu_mngr = ait.dsn.sle.CLTU(
        hostname='atb-ocio-sspsim.jpl.nasa.gov',
        port=5100,
        inst_id='sagr=LSE-SSC.spack=Test.fsl-fg=1.cltu=cltu1',
        auth_level="bind")

    cltu_mngr.connect()
    time.sleep(2)

    cltu_mngr.bind()
    time.sleep(2)

    cltu_mngr.start()
    time.sleep(2)

    junk_data = bytearray('\x00'*79)
    cltu_mngr.upload_cltu(junk_data)
    time.sleep(2)

    cltu_mngr.stop()
    time.sleep(2)

    cltu_mngr.unbind()
    time.sleep(2)

    cltu_mngr.disconnect()
    time.sleep(2)


IMPORTANT NOTE: The F-CLTU transfer service is not the same functionality as creating a CLTU PDU, which is outlined starting at Page 3-1 of the `CCSDS specification <https://public.ccsds.org/Pubs/201x0b3s.pdf>`_.