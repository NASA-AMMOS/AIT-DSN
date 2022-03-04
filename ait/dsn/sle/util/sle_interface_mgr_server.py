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

import datetime as dt
import time
import sys
import requests
import socket

import geventwebsocket

import ait.dsn.sle
from ait.core import dmc

from ait.dsn.sle.util.sle_interface_manager import SLEInterfaceManager, CLTUServer, ServiceType, ServiceState


class SleMgrServers(gevent.Greenlet):

    default_sle_mgr_host = '127.0.0.1'  # Localhost
    default_sle_mgr_udp_port = 9000     # UDP Port: 9000
    default_sle_mgr_rest_port = 7654    # REST Port: 7654

    sle_mgr_host = default_sle_mgr_host
    sle_mgr_udp_port = default_sle_mgr_udp_port
    sle_mgr_rest_port = default_sle_mgr_rest_port

    def service_names_to_enums(names):
        '''
        Utility method that returns list of service type enumbs based on list of names passed in
        '''
        filt = list(filter(lambda key: key in ServiceType.__members__, map(lambda name: name.upper(), names)))
        return list(map(lambda x: ServiceType[x], filt))

    """
    Class that holds SLEInterfaceManager and its servers
    """

    def __init__(self, services, **kwargs):
        '''
        Constructor creates SLEInterfaceManager, attaches handlers,
        and builds servers.
        :param services: List of ServiceType enums
        :param kwargs: Keyword arg values
        '''
        self._services = services

        self._rest_port = kwargs.get('rest_port', SleMgrServers.default_sle_mgr_rest_port)
        self._udp_port = kwargs.get('udp_port', SleMgrServers.default_sle_mgr_udp_port)
        self._host = kwargs.get('host', SleMgrServers.default_sle_mgr_host)
        self._verbose = kwargs.get('verbose', False)

        self.rest_url_base = f"http://{self._host}:{self._rest_port}"
        self.udp_dest = (self._host, self._udp_port)

        if ServiceType.NONE in self._services:
            self._services.remove(ServiceType.NONE)

        self._service_names = list(map(lambda x: x.name.lower(), self._services))

        self.sle_mgr = SLEInterfaceManager()
        self.sle_mgr.verbose = self._verbose



        self.build_servers()

        gevent.Greenlet.__init__(self)



    def build_servers(self):
        '''
        Builds the REST and UDP servers
        '''
        if self._verbose:
            ait.core.log.info(f'Building server...\n')

        self.rest_server = gevent.pywsgi.WSGIServer(
            (self._host, self._rest_port),
            self.sle_mgr.api,
            handler_class=geventwebsocket.handler.WebSocketHandler)

        self.cltu_udp_server = CLTUServer(listener=self._udp_port, sle_interfaces=self.sle_mgr)

        self.cltu_udp_socket = None

    def run_servers(self):
        '''
        Run the REST and UDP services.
        Creates a UDP socket for data upload
        '''
        if self._verbose:
            ait.core.log.info(f"Starting SLE Manager servers...\n")

        try:
            self.cltu_udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        except:
            ait.core.log.error(f"Socket creation unsuccessful.\n")
            self.cltu_udp_socket = None

        self.rest_server.start()
        if self._verbose:
            ait.core.log.info(f"REST Server Started...\n")

        self.cltu_udp_server.start()
        if self._verbose:
            ait.core.log.info(f"UDP Server Started...\n")

        if self._verbose:
            ait.core.log.info(f"SLE Manager Servers started.\n")

    def _run(self):
        self.run_servers()

    def kill_servers(self):
        '''
        Close the socket and bring down the UDP and REST servers
        '''
        #Currently we can rely if socket was created or not
        if self.cltu_udp_socket:
            self.cltu_udp_socket.close()
            self.cltu_udp_socket = None

            self.cltu_udp_server.stop()
            self.rest_server.stop()

    def bring_up_services(self):
        '''
        Runs the up-start service life cycle (connect,bind,start) for each service
        '''
        if self._verbose:
            ait.core.log.info(f"Bringing up SLE services...")

        services_started = 0

        for service_name in self._service_names: #all_services:

            service_info = self.sle_mgr.get_service(service_name)

            if self._verbose:
                ait.core.log.info(f"Bringing up '{service_name}' interface...")

            response = requests.get(f"{self.rest_url_base}/connect/{service_name}")
            time.sleep(2)

            if self.sle_mgr.get_service(service_name).state != ServiceState.CONNECTED:
                ait.core.log.error(f"Service '{service_name}' did not successfully connect!")
                continue

            response = requests.get(f"{self.rest_url_base}/bind/{service_name}")
            time.sleep(2)

            if self.sle_mgr.get_service(service_name).state != ServiceState.BOUND:
                ait.core.log.error(f"Service '{service_name}' did not successfully bind!")
                continue

            # Service start requests *may* require query params (i.e. RCF)
            query_params = self.get_service_start_parms(service_info.type)
            response = requests.get(f"{self.rest_url_base}/start/{service_name}", query_params)
            time.sleep(2)

            if self.sle_mgr.get_service(service_name).state != ServiceState.STARTED:
                ait.core.log.error(f"Service '{service_name}' did not successfully start!")
                continue

            services_started = services_started + 1
            if self._verbose:
                ait.core.log.info(f"SLE interface for '{service_name}' brought up.")


        if services_started == 0 and ServiceType.NONE not in self._services:
            ait.core.log.info(f"No services were successfully started.  Aborting...")
            self.tear_down_services()
            self.kill_servers()
            ait.core.log.info(f"Exiting...")
            sys.exit()

    def get_service_start_parms(self, service_type):
        '''
        Returns a dictionary that will be converted into a set of REST query parameters
        for a given service type.
        :param service_type:  ServiceType enumeration
        :return: dict of service values
        '''
        query_params = {}
        if service_type == ServiceType.RCF:
            stime = dmc.GPS_Epoch.strftime(dmc.RFC3339_Format)
            etime = dt.datetime.utcnow().strftime(dmc.RFC3339_Format)
            master_chan_flag = True
            query_params = {'master_channel': master_chan_flag, 'start': stime, 'end': etime}
            if self._verbose:
                ait.core.log.info(f"RCF params: {query_params}")
        return query_params

    def tear_down_services(self):
        '''
        For each active service, calls the teardown lifecycle (stop,unbind,disconnect)
        '''
        if self._verbose:
            ait.core.log.info(f"Tearing down SLE services...")

        for service_name in self._service_names:

            if self.sle_mgr.get_service(service_name).state == ServiceState.STARTED:
                response = requests.get(f"{self.rest_url_base}/stop/{service_name}")
                time.sleep(2)

            if self.sle_mgr.get_service(service_name).state == ServiceState.BOUND:
                response = requests.get(f"{self.rest_url_base}/unbind/{service_name}")
                time.sleep(2)

            if self.sle_mgr.get_service(service_name).state == ServiceState.CONNECTED:
                response = requests.get(f"{self.rest_url_base}/disconnect/{service_name}")
                time.sleep(2)

            if self._verbose:
                ait.core.log.info(f"SLE interface for {service_name} torn down.")

    def upload_data(self, data, num_uploads=1):
        '''
        Uploads data to the CLTU service.
        First a number of upload to to UDP calls are made followed by a final
        REST call to perform CLTU upload
        :param data: byte-array data to be uploaded
        :param num_uploads: Number of data uploads to run
        '''
        if not self.cltu_udp_socket:
            ait.core.log.info(f"Rejecting request to upload data as UDP socket is dead.")
            return

        if not data:
            ait.core.log.info(f"Rejecting request to upload as data is empty.")
            return

        if self._verbose:
            ait.core.log.info(f"Uploading data {num_uploads} time(s) via CLTU interface:")

        for _ in range(num_uploads):

            if self._verbose:
                ait.core.log.info(f"Pushing data to UDP port...")
            try:
                self.cltu_udp_socket.sendto(data, self.udp_dest)
                time.sleep(2)
            except Exception as e:
                ait.core.log.error(f"Error occurred while sending data to socket: {e}")
                ait.core.log.error(f"Closing socket.")
                try:
                    self.cltu_udp_socket.close()
                except:
                    pass
                self.cltu_udp_socket = None

        if self._verbose:
            ait.core.log.info(f"Requesting data uploaded via REST...")
        response = requests.get(f"{self.rest_url_base}/upload/cltu")
        time.sleep(2)

        if self._verbose:
            ait.core.log.info(f"Upload complete.")


    def xfer_bffr_log_handler(self, pdu):
        '''
        Simple handler that prints the PDU event name to the logger
        :param pdu: PDU event
        '''
        pdu_key = pdu.getName()
        ait.core.log.info(f"Received a data transfer PDU for event {pdu_key}")

    ## Attach handlers that report they received something (either from RAF or RCF) via the logger
    def attach_downlink_transfer_handler(self, handler):
        '''
        Attaches the log handler to the RAF and RCF services for TransferBuffer events
        '''
        self.sle_mgr.raf_service.service.add_handler("RafTransferBuffer", self.xfer_bffr_log_handler)
        self.sle_mgr.rcf_service.service.add_handler("RcfTransferBuffer", self.xfer_bffr_log_handler)
