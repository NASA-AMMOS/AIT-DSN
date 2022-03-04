#!/usr/bin/env python

# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2021, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.

# Usage:
#   python run_sle_interface_mgr_server.py [-h] [--type TYPE [TYPE ...]] [--host HOST]
#                                    [--udp UDP] [--rest REST] [--verbose] [--sim]
#
#   where 'TYPE' is one of:  raf, rcf, cltu
#
# SSPSim Config:
# Please refer to the config setup as documented in
# the respective API test of each service:
#
# - RAF: raf_api_test.py
# - RCF: rcf_api_test.py
# - CLTU: cltu_api_test.py
#
#
# Some potentially pertient info form the RAF test class that may
# apply generally:
#
# Run the script per the usage instructions above. You should see
# logging informing you of the various steps and data being sent
# to the telemetry output port. Note, because we're using dummy data
# we will see 0 bytes being output. This is working as expected.
# If you run into issues with decoding problems on the TM Frames this
# likely due to the TM frame size not being evenly divisible into
# CCSDS Packets. The TM Frame processor assumes the data field contains
# CCSDS Packets. Since all the dummy data is 0's, the processor
# repeatedly strips 6 bytes off the packet data to process as a CCSDS header.
# As such, (Telem Frame Length - 6 bytes for the TM Header) % 6 should be 0.
# If it's not you'll likely encounter problems.

import gevent
import gevent.monkey; gevent.monkey.patch_all()

import time
import sys

import argparse
from collections import OrderedDict
import ait.dsn.sle

from ait.dsn.sle.util.sle_interface_manager import ServiceType
from ait.dsn.sle.util.sle_interface_mgr_server import SleMgrServers

cltu_junk_data = bytearray('\x00' * 79, 'utf-8')  # Junk data used for uploading to CLTU
uploads_per_request = 3  # Number of times to upload CLTU data before service upload request

def get_service_type_names():
    return list(map(lambda x: x.name.lower(), ServiceType))

def create_parser():
    '''
    Configures and returns CLI parser for this script
    '''

    descr = "Runs the SLE Manager service suite with some basic setup."

    parser = argparse.ArgumentParser(

        description=descr,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    arg_defns = OrderedDict({
        '--type': {
            'type': str,
            'action' : 'append',
            'nargs' : '+',
            'default': [],
            'help': f"Type of service to run: '+ {get_service_type_names()}"
        },
        '--host': {
            'type': str,
            'default': SleMgrServers.default_sle_mgr_host,
            'help': 'Host from which services will be accessed.'
        },
        '--udp': {
            'type': int,
            'default': SleMgrServers.default_sle_mgr_udp_port,
            'help': 'UDP port for sending uplink data.'
        },
        '--rest': {
            'type': int,
            'default': SleMgrServers.default_sle_mgr_rest_port,
            'help': 'REST port for accessing service endpoints.'
        },
        '--verbose': {
            'action': 'store_true',
            'default': False,
            'help': 'Print debug messages.'
        },
        '--sim': {
            'action': 'store_true',
            'default': False,
            'help': 'Simulates uplink of arbitrary bytes to CLTU layer.'
        },
    })

    ## Push argument defs to the parser
    for name, params in arg_defns.items():
        parser.add_argument(name, **params)

    return parser

if __name__ == '__main__':

    cli_args = sys.argv[1:]

    ## Get arg results of the parser
    parser = create_parser()
    args = parser.parse_args()

    type_lists = args.type
    rest_port = args.rest
    udp_port = args.udp
    host = args.host
    verbose = args.verbose
    sim_uplink = args.sim

    # Convert nested lists to one flat list
    flat_type_list = [item for sublist in type_lists for item in sublist]

    #Parse arguments to get list of service interfaces to run
    if flat_type_list is None:
        ait.core.log.error(f"Expected service arguments: any of {get_service_type_names()}")
        sys.exit()

    # Convert CLI args to list of active services
    active_services = SleMgrServers.service_names_to_enums(flat_type_list)
    if not active_services:
        ait.core.log.error(f"No legal service arguments were provided: {flat_type_list}")
        ait.core.log.error(f"Expected service arguments: any of {get_service_type_names()}")
        sys.exit()

    # Instantiate mgr interface with list of services
    sle_mgr_srvs = SleMgrServers(active_services, rest_port=rest_port, udp_port=udp_port,
                                 host=host, verbose=verbose)

    # Attach simple hanlder to downlink services
    sle_mgr_srvs.attach_downlink_transfer_handler(SleMgrServers.xfer_bffr_log_handler)

    ##Start the web and UDP servers
    sle_mgr_srvs.run_servers()
    time.sleep(2)

    #Bring up the SLE interface services (using rest API)
    sle_mgr_srvs.bring_up_services()
    time.sleep(2)

    # Continue running until interrupted.
    # If CLTU service is running, then periodically upload data
    try:
        while True:
            time.sleep(5)
            if sim_uplink and ServiceType.CLTU in active_services:
                sle_mgr_srvs.upload_data(cltu_junk_data, uploads_per_request)
    except KeyboardInterrupt:
        pass  # Gracefully handle Ctrl-C
    except Exception as e:
        ait.core.log.error(f"Error occurred while uploading data forever...")
        ait.core.log.error(e)
    finally:
        sle_mgr_srvs.tear_down_services()
        sle_mgr_srvs.kill_servers()

