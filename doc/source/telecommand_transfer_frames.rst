AIT Telecommand Transfer Frames
===============================


Introduction
^^^^^^^^^^^^

AIT DSN provides the capability to package a payload as a Telecommand Transfer Frame as described by CCSDS Blue Book:
https://public.ccsds.org/Pubs/232x0b4.pdf

The TCTF_Manager plugin is provided as a way to configure managed parameters and provide the capability to
add TCTF Framing as part of a command processing pipeline.

Configuration: Managed Parameters and Command Processing Pipelines
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
A working configuration is provided in the below snippets.
Part I configures TCTF as part of the command processing pipeline.
Part II configures the TCTF managed parameters.
All fields are mandatory unless otherwise stated (i.e. commented fields are optional).

::

	Sample Configuration Part I:
    ----------------------------
    server:
        plugins:
            - plugin:
                name: ait.dsn.plugins.TCTF_Manager.TCTF_Manager
                inputs:
                    - command_stream

    Sample Configuration Part II:
    -----------------------------
    default:
        dsn:
            tctf:
                transfer_frame_version_number: 0
                bypass_flag: 0
                control_command_flag: 0
                reserved: 0
                uplink_spacecraft_id: 123
                virtual_channel_id: 0
                frame_sequence_number: 0
                apply_error_correction_field: True
                add_frame_segmentation_byte: False				

Pipeline Configuration
----------------------

In Sample Configuration Part II, the resulting Command Processing Pipeline will have the following effects:

1. The TCTF_Manager plugin will receive a payload from the *command_stream* topic, whenever a message is published on the *command_stream* tpoic on the PUB/SUB network. Plugins can be configured to subscribe to other plugins by replacing *command_stream* with the plugins PUB/SUB topic.
2. The TCTF_manager plugin will encode the payload as a CCSDS Telecommand Transfer Frame and increment its internal frame_sequence number.
3. The TCTF_Manager plugin will publish the encoded TCTF on the *TCTF_Manager* topic of the PUB/SUB network. When a plugin is loaded, a PUB/SUB topic with the name of the plugin is automatically created. 
4. Plugins downstream of the TCTF_Manager_Plugin may be configured as the next receiving plugin in the command processing pipeline by subscribing to the *TCTF_Manager* topic on the PUB/SUB network. To do so, the next plugin in the pipeline must to contain the following snippet in their config.yaml block:

   ::
	  inputs:
          - TCTF_Manager # This is the upstream plugin's PUB/SUB topic

5. Finally, if defined, the encoded TCTF is published on the 667 UDP stream as defined in the *outbound streams* section of the configuration file. The *outputs* field only supports UDP ports; It is a mistake to specify a plugin or TCP port in this field.

Managed Parameters
------------------

Sample Configuration Part I shows how managed parameters can be configured.

When *apply_error_correction_field: True*, the CRC of the TCTF will be calculated and appended to the the rear of the frame as per
CCSDS standards. 

*uplink_spacecraft_id* is referred to as *spacecraft_id* in CCSDS documentation.
This naming deviation is to differentiate uplink and downlink spacecraft ids.
The usage of the *uplink_spacecraft_id* remains the same as in CCSDS documentation.

The remaining managed parameter names and usages reflect those found in CCSDS documentation.
   
Validation
^^^^^^^^^^

Validation of managed parameters or payload size is currently not available.
Errors in managed parameter values or payload size may have undefined behavior on TCTF encoding.
See the CCSDS documentation for proper managed parameter usage and valid ranges.

The included TCTF unit tests may be useful examples for creating quick tests for managed parameters.

Payload Sizes
^^^^^^^^^^^^^

Since payload size requirements may vary by platform and mission, payload length is not validated:

Generally speaking:
1. The payload size must at least conform to the CCSDS defined maximum TCTF payload size.
2. For TCTFs that are to be encrypted, SDLS has its own payload size requirement.
3. Some platforms may require that the payload be padded to a certain length.

Manipulation and validation of payload attributes such as payload size, padding, and packing, are best performed by other plugins upstream of the TCTF_Manager plugin.
