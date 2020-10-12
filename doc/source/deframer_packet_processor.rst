AIT Deframer/Packet Processor
=============================

This is a guide for AIT's base implementation for the Deframer and Packet Processor.

The processor receives transfer frames (AOS or TM), extracts CCSDS packets from those frames, and then organizes and emits those packets downstream.

The base implementation handles AOS tansfer frames containing partials and will create full packets from partials when possible.
AIT does not currently support partials from TMTransferFrames, so they are not handled in this implementation either.


Configuration
^^^^^^^^^^^^^

The necessary configuration parameters can be added to the **config.yaml**.
Optionally, many of them can also be passed in at runtime for greater flexibility.
Below is an example configuration which can be used as a reference, in addition to the default configuration available in the repository.


.. code-block:: yaml

    dsn:
        proc:
            timer_poll: 15                # How long to poll for new telemetry, seconds
            cleanup_poll: 300             # How often to check for cleanup, seconds
            max_gap: 100                  # If 0, do not allow gaps in packet downstream
            packet_output_port: 3076      # The UDP port used for emitting CCSDS packets
        sle:
            downlink_frame_type: TMTransFrame  # or AOSTransFrame
            frame_output_port: 3726    # The incoming UDP port for transfer frames

     Note: If max_gap is set to 0, then any gaps in incoming packets with the same APID will necessarily prevent emission of packets until the gap is resolved.
     As such, it would only be recommended for use during playback of complete telemetry.

    Any of the above base keywords can also be set using a kwargs that is passed into the Processor.

Running the Processor
^^^^^^^^^^^^^^^^^^^^^

The processor can be run as a command line:

::

    python ait/dsn/proc/deframe_packet_processor.py


or be used by Python code:

::

    import ait.dsn.proc.deframe_packet_processor
      ...
    processor = Processor()
    try:
        processor.run()
    except Exception as e:
        print(traceback.print_exc())
    finally:
        processor.stop()


Design/Architecture
^^^^^^^^^^^^^^^^^^^

The Processor is the primary controller, it creates data structures, services, and connects the flow of data.

The Processor creates Frame_Service instance which listens for Transfer Frames on an incoming UDP port.  (This port can be specified by the dsn.sle.proc.frame_output_port, which controls an upstream AIT DSN service which emits frames, hence 'output' in the name.)

These frame bytes are parsed into the appropriate AIT Transfer Frame instance, per the downlink_frame_type config.

For each frame, the Processor examines the header and frame data section for a sequence CCSDS packets.  Any frames marked as idle are dropped automatically.

Partial CCSDS packets are maintained in a PartialsLookup, which will track partials and create whole packets from complementary pairs.

For a given whole packet, the APID is extracted from the header, and the packet is a stored in an ApidInfo datastore.

The ApidInfo is responsible for ensuring packets with a shared APID are sorted and tracking when a packet would be ready to be emitted.
The ApidInfo class maintains the seqcount of the 'last sent packet' and will await for the following seqcount'ed packet to send.
Any packets with a seqcount greater than the expected will be queued.

Each time the Processor adds a packet to an ApidInfo, it checks to decide when the ApidInfo has a packet that should be pushed downstream.

Assumptions/Decisions
^^^^^^^^^^^^^^^^^^^^^^


1. Partial Packets

    At the time of implementation, TMTransferFrames did not support the associated specification document for containing partials packets.  As such partials are not supported for those frames.
    AOSTransferFrames themselves do not yet handle this internally, but we can access the raw data section and handle partials ourselves.
    Some point in the future, the partials handling should be pushed to the transfer frame classes.


2. Sorting Packets

    Packet sequence count is bounded by a max value, and rollover needs to be considered when sorting.
    While timing information can be encoded in the CCSDS packet via a secondary header, there is no requirement for this, and currently no support for extracting this information in AIT.
    As such, the software makes no assumptions about this type of timing information in the packet.
    Instead, it uses an internal data structure to keep track of sorting with rollover.


3. Dealing with Packet Gaps

    When gaps are allowed per the configuration, the software will queue packets while it awaits the packet that should be emitted next.
    If the number of packets in the queue reaches a threshold (as specifed by max_gap), then those missing packets will be skipped over and the first packet in the queue will be the next available to be emitted.


4. Scheduled Cleanup

    There are two areas that can perform periodic cleanup: 1) partials lookup; and 2) APIDInfo instances.

    A single partials lookup is maintained for the Processor.  The partials lookup keeps track of the sequence order in which partial are added.
    When the partials lookup reaches a certain size, then a selection of the oldest entries will be purged.

    There is an APIDInfo instance per unique CCSDS header APID value.  As mentioned above, it maintains a max_gap, which can be 0 - meaning no gaps allowed.
    If gaps are allowed, then the APIDInfo will collect and store packets while it awaits for the next packet to send.
    If the size of the wait-queue reaches the max_gap value, then the ApidInfo will abandon waiting and advance itself such that the first queued packet becomes the next available.

    If gaps are not allowed, then no skipping will ever take place.  As such, no gaps should only be used for telemetry playback that is known to have no missing packets.

    Partials cleanup is part of the scheduled cleanup as controlled by cleanup_poll.  ApidInfo cleanup is handled as packets are added to the instance.

