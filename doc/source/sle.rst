Overview of SLE
===============

CCSDS Space Link Extension (SLE) defines a standardized set of SLE Transfer Services that enable missions to send forward space link data units to a spacecraft and to receive return space link data units from a spacecraft.

Downlink
--------
There are two different procedures available for downlink of data from your spacecraft or instrument, "Return All Frames" (RAF) and "Return Channel Frames" (RCF). AIT provides interfaces for both, and which one you use will depend on the needs of your specific project.


Return All Frames (RAF) 
^^^^^^^^^^^^^^^^^^^^^^^
The SLE standard for RAF is available online `here <https://public.ccsds.org/Pubs/911x1b4.pdf>`_. RAF is an SLE transfer service that delivers to a mission user all telemetry frames from one space link physical channel.

Return Channel Frames (RCF)
^^^^^^^^^^^^^^^^^^^^^^^^^^^
The SLE standard for RCF is available online `here <https://public.ccsds.org/Pubs/911x2b3.pdf>`_. RCF is an SLE transfer service that delivers to a mission user all telemetry frames from one master channel or one virtual channel. It define one
service that provides the functionality for both Return Master Channel Frames (Rtn MC Frames) and Return Virtual Channel Frames (Rtn VC Frames).

Uplink
------

Forward Communications Link Transmission Unit (F-CLTU)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The SLE standard for F-CLTU is available online `here <https://public.ccsds.org/Pubs/912x1b4.pdf>`_. The Forward CLTU service is a SLE transfer service that enables a mission to send Communications Link Transmission Units (CLTU) PDUs to a spacecraft. 