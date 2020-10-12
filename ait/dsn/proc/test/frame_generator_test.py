#!/usr/bin/env python

# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
#
import struct
import socket
import time

import ait.core
from ait.dsn.sle.frames import AOSTransFrame, AOSConfig, AOSDataFieldType

## ==================================================
## ==================================================
## ==================================================




## -----------------------------------------
## Setup the output port information
out_host = 'localhost'
out_port = 3726
out_dest = (out_host, out_port)
frame_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)



def int_to_bytes(val, num_bytes):
    return val.to_bytes(num_bytes, byteorder='big')



## -----------------------------------------

## create basic form of a CCSDS packet

## CCSDS: [header, type, shflag, apid] [seqflags, seqcount] [length]
##           constant

## version = 000, type = 0, shflag = 0, apid = 00001  (constant)
CCSDS_HDR_BYTES_0_1_INT = 0x0001
CCSDS_HDR_BYTES_0_1_BYTES = int_to_bytes(CCSDS_HDR_BYTES_0_1_INT, 2)

## seqflags = 11, seqcount = 14bits (will increment)   00111111 11111111  3FFF
CCSDS_HDR_BYTES_2_3_INT = 0xC000


## length = 0000000000000001 (constant) (num of bytes in body - 1)
CCSDS_HDR_BYTES_4_5_INT = 0x0001
CCSDS_HDR_BYTES_4_5_BYTES = int_to_bytes(CCSDS_HDR_BYTES_4_5_INT, 2)

##: 0001 0011 0111 1111
CCSDS_BODY_INT = 0x137F
CCSDS_BODY_BYTES = int_to_bytes(CCSDS_BODY_INT, 2)

## The fella we will increment
packet_seq_flags_and_count = CCSDS_HDR_BYTES_2_3_INT


def inject_seqcount(seqcount):
    seqflags = CCSDS_HDR_BYTES_2_3_INT & 0xC000
    rval = seqflags | seqcount
    return rval


def build_ccsds_packet(seqcount):
    ba = bytearray()
    ba += bytearray( CCSDS_HDR_BYTES_0_1_BYTES )
    hrd_bytes_2_3 = inject_seqcount(seqcount)
    ba += bytearray( int_to_bytes(hrd_bytes_2_3 ,2) )
    ba += bytearray(CCSDS_HDR_BYTES_4_5_BYTES)
    ba += bytearray(CCSDS_BODY_BYTES)
    return ba


def break_ccsds_packet(packet):
    pkt_len = len(packet)
    half_len = int(pkt_len / 2)
    partial_a = packet[0:half_len]
    partial_b = packet[half_len:]
    partials = (partial_a, partial_b)
    return partials

## -----------------------------------------
## Create an AOSFrame of type MPDU with packet


## ver=01, craftId = 00000001, virChanId = 000010
AOS_HDR_BYTES_0_1_INT = 0x4042
AOS_HDR_BYTES_0_1_BYTES = int_to_bytes(AOS_HDR_BYTES_0_1_INT, 2)

# framecount: 3 bytes  (increments)
AOS_HDR_BYTES_2_3_4_INT = 0x000000

# signalfield; replay: 0, vcUsage: 0, spare: 00, fc_cycle: 0000
AOS_HDR_BYTES_5_INT = 0x00
AOS_HDR_BYTES_5_BYTES = int_to_bytes(AOS_HDR_BYTES_5_INT, 1)


# spare: 00000, firstpktptr: 00000000000
MPDU_HDR_BYTES_0_1_INT = 0x0000
MPDU_HDR_BYTES_0_1_BYTES = int_to_bytes(MPDU_HDR_BYTES_0_1_INT, 2)

frame_count = AOS_HDR_BYTES_2_3_4_INT


def build_aos_frame(aos_framecount, mpdu_hdr_ptr=0):
    ba = bytearray()
    ba += bytearray(AOS_HDR_BYTES_0_1_BYTES)
    ba += bytearray( int_to_bytes(aos_framecount , 3) )
    ba += bytearray(AOS_HDR_BYTES_5_BYTES)
    ##ba += bytearray(MPDU_HDR_BYTES_0_1_BYTES)
    ba += bytearray( int_to_bytes(mpdu_hdr_ptr , 2) )
    return ba


def build_frame(aos_framecount, ccsds_seqcount):
    mpdu_frame_head = build_aos_frame(aos_framecount)
    mpdu_frame_body =  build_ccsds_packet(ccsds_seqcount)
    aos_mpdu_full = mpdu_frame_head + mpdu_frame_body
    return aos_mpdu_full


frame_count = 0
seq_count = 0
frame_count = 3

virt_chan_map = {1: "b_pdu",
                 2: "m_pdu",
                 3: "vca_sdu",
                 4: "idle"}

# The shared AOS config, indicating which optional fields exists and the
# Virtual channel map
aos_cfg = AOSConfig(virtual_channels=virt_chan_map)

## -----------------------------------------
## Emit whole frames

def test_reset():
    print('Running test_reset(): Sending frames that will include a reset packet...')

    count_list = [0, 2, 4, 1, 3, 6, 7, 0, 1, 2]

    for i in count_list:
        print('-----------------')
        frame_data = build_frame(i, i)
        aos_frame = AOSTransFrame(config=aos_cfg, data=frame_data)
        print('Sending seqcount {} with {} bytes to frame port'.format(i, len(frame_data)))
        frame_socket.sendto(frame_data, out_dest)
        ##time.sleep(3)

## -----------------------------------------
## Emit frames with partials

def test_partials():
    print('Running test_partials(): Sending frames with partial CCSDS packets...')

    count_list = [0, 1, 2, 3, 4]

    aos_framecount = 0
    pkt_count = 0
    range_value = 5

    pkt_a = None
    pkt_b = None

    frame_data = None

    frame_list = []

    ## ---------------------------------
    ## Build an AOS frame with one full packet and one partial packet

    frame_head = build_aos_frame(aos_framecount)
    aos_framecount += 1

    packet = build_ccsds_packet(pkt_count)
    pkt_count += 1

    frame_data = frame_head + packet

    packet = build_ccsds_packet(pkt_count)
    pkt_count += 1

    (part_a,part_b) = break_ccsds_packet(packet)
    frame_data = frame_data + part_a

    frame_list.append(frame_data)


    ## ---------------------------------
    ## Frame 2: Build an AOS frame with partial packet then full packet

    mpdu_hdr_ptr = len(part_b)
    frame_head = build_aos_frame(aos_framecount, mpdu_hdr_ptr )
    aos_framecount += 1

    packet = build_ccsds_packet(pkt_count)
    pkt_count += 1

    frame_data = frame_head + part_b + packet

    frame_list.append(frame_data)


    ## ---------------------------------
    ## Frame 3: Build an AOS frame with full packet

    frame_head = build_aos_frame(aos_framecount)
    aos_framecount += 1

    packet = build_ccsds_packet(pkt_count)
    pkt_count += 1

    frame_data = frame_head + packet

    frame_list.append(frame_data)

    ## ---------------------------------
    ## Now emit the packets....

    for count, frame_data in enumerate(frame_list):
        aos_frame = AOSTransFrame(config=aos_cfg, data=frame_data)
        print('-----------------')
        print('Sending partials frame {} with {} bytes to frame port'.format(count, len(frame_data)))
        frame_socket.sendto(frame_data, out_dest)
        ##time.sleep(3)

## -----------------------------------------
## Emit whole frames with mod logic

def test_modulo():
    print('Running test_reset(): Sending frames that will include a mid-range value')

    count_list = [0, 2, 8192, 1, 8193, 8194, 7, 11100, 11101, 1,  2]

    for i in count_list:
        print('-----------------')
        frame_data = build_frame(i, i)
        aos_frame = AOSTransFrame(config=aos_cfg, data=frame_data)
        print('Sending seqcount {} with {} bytes to frame port'.format(i, len(frame_data)))
        frame_socket.sendto(frame_data, out_dest)
        ##time.sleep(3)



if __name__ == '__main__':
    #test_reset()
    #test_partials()
    test_modulo()