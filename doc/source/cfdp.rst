Overview of CFDP
================

`CFDP <https://public.ccsds.org/pubs/727x0b4.pdf>`_ (`CCSDS <https://public.ccsds.org/default.aspx>`_ File Delivery Protocol) defines a standard for space-to-ground, ground-to-space, and space-to-space file transfer, which may be initiated by a file sending or receiving entity. Using CFDP allows for communication between spacecraft or instruments through files rather than packets, which may simplify Ground Data System and Flight Software processes. Here we provide an overview of the protocol, including terms and concepts that will be helpful to know in using AIT's CFDP implementation. 

Entities & File Delivery Units
------------------------------
A **CFDP protocol entity** is a functioning instance of a CFDP implementation, such as AIT's :mod:`ait.dsn.cfdp.cfdp.CFDP`. A **transaction** is the end-to-end transmission of a single **File Delivery Unit (FDU)** between CFDP entities, where a FDU is a functional concatenation of a file and related **metadata**. The metadata is typically either additional application data (e.g. a "message to user") or data to aid the recipient entity in utilizing the file (e.g. file name). It is possible for an FDU to consist of only metadata. A single transaction has a **source** and a **destination** entity, which are also the only **sender** and only **receiver** in the case of a single file copy operation per transaction.


Protocol Data Units
-------------------
FDUs are usually transmitted in multiple **protocol data units (PDUs)**, which will all by tagged with the same **transaction ID**, which uniquely identifieds a single instance of FDU delivery and contains the ID of the source CFDP entity together with a sequence number specific to that entity. 

A PDU can be one of three types - a **file data PDU**, a **file directive PDU**, or a **metadata PDU**. A file data PDU contains the contents of the file being delivered, while a file directive PDU contains only metadata and other non-file information for the protocol. A metadata PDU contains the following:

1. an indication of whether the file contains records with boundaries to be respected when the file is segmented for transmission in file data PDUs;

2. the size of the file if known;

3. the source and destination path names of the file;

4. optional fault handler overrides, messages to user, filestore requests, and/or flow label.


Progress of a transaction
-------------------------
The **offset** of a given octet of file data is the number of data octets that precede this octet in the file. The **progress** of a given file data PDU is the sume of the offset of the PDU's file data content (i.e., the offset of the content's first octet) and the length of that file data content. The **transmission progress** of a given transaction delivering a file is the maximum progression value over all file data PDUs *sent* so far in the transaction. The **reception progress** of a given transaction is the maximum progress value over all file data PDUs *received* so far in the transaction. If and only if no data are lost in transmission is reception progress equal to the number of file data octets received. If data has been lost, reception progress will be greater than the number of octets received.


Configuration & Transmission Modes
----------------------------------
The **management information base (MIB)** contains protocol configurations such as default values for user communications requirements and for communication timer settings. It is stored within CFDP entities as system tables. For instructions on configuring AIT's MIB, see :ref:`this section <MIB_>`. One of CFDPs configurable settings is the **transmission mode**, which can be either **unacknowledged**, meaning data delivery failures are not reported to the sender and therefore can't be repaired, or **acknowledged**, where the receiver informs the sender of any undelivered file segments of ancillary data, which are then retransmitted, thereby guaranteeing complete file delivery.

AIT currently provides an implementation of CFDP **Class 1** for *unreliable transfer* with a transmission mode of unacknowledged. An implementation of the protocol's **Class 2**, for *reliable transfer* with an acknowledged transmission mode, is in the works.