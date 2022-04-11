AOS_to_CCSDS
============

The AOS to CCSDS plugin extracts CCSDS packets from AOS frames.
The DSN frames services returns either AOS or TM Transfer Frames.

The AIT DSN interface outputs the frames depending on the following
config.yaml snippet:

.. code-block:: none

sle:
  frame_output_port: 2568

  
Since the DSN interface does not publish to the PUB/SUB network,
you will need to configure a UDP port to loop the frame back into AIT.

.. code-block:: none
				
   - stream:
	   name: telemetry_stream
       input: 
           - 2568

Next, the AOS configuration must be added, as shown in the example below.
.. code-block:: none

		dsn:
			sle:
				aos:
				    frame_header_error_control_included: false
                    transfer_frame_insert_zone_len: 0
                    operational_control_field_included: false
                    frame_error_control_field_included: false
                    virtual_channels:
                        1: "m_pdu"
                        2: "m_pdu"
                        4: "m_pdu"
                       63: "idle"

					   
Finally, the AOS_to_CCSDS must be configured.
.. code-block:: none

            - plugin:
                name: ait.dsn.plugins.AOS_to_CCSDS.AOS_to_CCSDS
                inputs:
                    - telemetry_stream
