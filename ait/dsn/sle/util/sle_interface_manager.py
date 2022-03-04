#!/usr/bin/env python

'''A class which manages multiple SLE Object instances and keeps track of states'''


import atexit
import ait
from ait.core.log import logger
import ait.core.dmc
import ait.dsn.sle
from ait.core import dmc
import socket


import bottle
from enum import Enum
import gevent #THIS SCRIPT REQUIRES THE MOST RECENT VERSION OF GEVENT.
import geventwebsocket
import datetime
from gevent.server import DatagramServer


class ServiceType(Enum):
    '''
    Enumeration for SLE interface service types
    '''
    NONE = 0
    RAF = 1
    RCF = 2
    CLTU = 3


class ServiceState(Enum):
    '''
    Enumeration for SLE interface service states
    '''
    ##ERROR = 0 #Do we need this?
    DISCONNECTED = 1
    CONNECTED = 2
    BOUND = 3
    STARTED = 4


class StatefulService(object):
    """
    Data structure for a service, including state and type information.
    """

    def __init__(self, service, type):
        """
        Constructor
        :param service: Service instance
        :param type: ServiceType value
        """
        self._service = service

        self._type = type if isinstance(type, ServiceType) else ServiceType.NONE

        #Data array, mostly applicable for upload services
        self._data = []

        #Current lifecycle state of the service
        self._state = ServiceState.DISCONNECTED

    @property
    def service(self):
        """Returns the service of this struct."""
        return self._service

    @property
    def type(self):
        """Returns the service type of this struct."""
        return self._type

    @property
    def state(self):
        """Returns the service state of this struct."""
        return self._state

    @state.setter
    def state(self, value):
        #Ensure value is legal ServiceState
        if isinstance(value, ServiceState):
            self._state = value

    @property
    def data(self):
        """Returns the service data array of this struct."""
        return self._data


class SLEInterfaceManager():
    '''A class which manages multiple SLE Object instances and keeps track of states'''
    #pylint:disable=too-many-instance-attributes
    def __init__(self):
        self.api = bottle.Bottle()

        self.raf_service = None
        self.rcf_service = None
        self.cltu_service = None

        try:
            self.raf_service = StatefulService(ait.dsn.sle.RAF(), ServiceType.RAF)
        except Exception as e:
            logger.warning(f"Unable to instantiate RAF Service.  Error: {e}")

        try:
            self.rcf_service = StatefulService(ait.dsn.sle.RCF(), ServiceType.RCF)
        except Exception as e:
            logger.warning(f"Unable to instantiate RCF Service.  Error: {e}")

        try:
            self.cltu_service = StatefulService(ait.dsn.sle.CLTU(), ServiceType.CLTU)
        except Exception as e:
            logger.warning(f"Unable to instantiate CLTU Service.  Error: {e}")

        # Ensure that at least one service was created, else raise an error
        if self.raf_service is None and self.rcf_service is None and self.cltu_service is None:
            raise Exception("No service instance (RAF,RCF,CLTU) was instantiated")


        # Even if the service is None, we rely on the key to determine
        # if service type is known.
        self.service_map = {ServiceType.RAF  : self.raf_service,
                            ServiceType.RCF  : self.rcf_service,
                            ServiceType.CLTU : self.cltu_service}

        # List seems kinda pointless since CLTU is the only service that supports upload
        # and has non-generic method call to invoke it...
        self.upload_service_types = [ ServiceType.CLTU ]

        self._route()

    def _route(self):
        '''
        Perform the Bottle routing.
        '''
        self.api.route('/connect/<interface>',    callback=self.connect_handler)
        self.api.route('/bind/<interface>',       callback=self.bind_handler)
        self.api.route('/start/<interface>',      callback=self.start_handler)
        self.api.route('/stop/<interface>',       callback=self.stop_handler)
        self.api.route('/unbind/<interface>',     callback=self.unbind_handler)
        self.api.route('/disconnect/<interface>', callback=self.disconnect_handler)
        self.api.route('/upload/<interface>',     callback=self.upload_handler)

    def get_service(self, interface, silence_errors=False):
        '''
        Utility method that returns proper service instance based on interface name
        :param interface:  Interface name ('raf','rcf','cltu')
        :param silence_errors: Flag indicating when errors should not be logged
        '''
        srvc_val = None
        srvc_key = interface.upper()
        srvc_type = ServiceType[srvc_key]
        if srvc_type is not None:
            srvc_val = self.service_map.get(srvc_type)
            if srvc_val is None:
                if not silence_errors:
                    logger.error(f"{interface} interface was not successfully instantiated")
                    bottle.response.status = 400
        else:
            if not silence_errors:
                logger.error(f"{interface} is not a valid interface option")
                bottle.response.status = 400
        return srvc_val

    def connect_handler(self, interface):
        '''
        Connect the SLE object specified by <interface> to the DSN.
        Example:
        /connect/cltu is equivalent to running cltu.connect()
        :param interface:  Interface name ('raf','rcf','cltu')
        '''
        srvc_info = self.get_service(interface)

        if srvc_info is None:
            return None

        # Legal pre-state: DISCONNECTED

        if srvc_info.state == ServiceState.DISCONNECTED:
            if self.verbose:
                ait.core.log.info(f"{interface} connecting...")
            try:
                srvc_info.service.connect()
                srvc_info.state = ServiceState.CONNECTED
                if self.verbose:
                    ait.core.log.info(f"{interface} connected.")

            except socket.error as e:
                #srvc_info.state = ServiceState.ERROR
                logger.error(f"Error occurred while attempting to connect {interface} instance")
                bottle.response.status = 400
        else:
            logger.error(f"{interface} instance already connected")
            bottle.response.status = 400

    def bind_handler(self, interface):
        '''
        Bind the SLE object specified by <interface> to the DSN.
        Example:
        /bind/cltu is equivalent to running cltu.bind()
        :param interface:  Interface name ('raf','rcf','cltu')
        '''
        srvc_info = self.get_service(interface)

        if srvc_info is None:
            return None

        # Legal pre-state: CONNECTED

        if srvc_info.state == ServiceState.DISCONNECTED:
            logger.error(f"{interface} instance is not connected. Unable to bind.")
            bottle.response.status = 400
        elif srvc_info.state == ServiceState.BOUND or srvc_info.state == ServiceState.STARTED:
            logger.error(f"{interface} instance already bound")
            bottle.response.status = 400
        else:
            if self.verbose:
                ait.core.log.info(f"{interface} binding...")

            try:
                srvc_info.service.bind()
                srvc_info.state = ServiceState.BOUND

                if self.verbose:
                    ait.core.log.info(f"{interface} bound.")

            except Exception as e:  #Handles AttributeError and socket.error
                #srvc_info.state = ServiceState.ERROR
                logger.error(f"Error occurred while attempting to bind {interface} instance")
                bottle.response.status = 400
                return None

    def start_handler(self, interface):
        '''
        Start the SLE object specified by <interface>.
        Example:
        /start/cltu is equivalent to running cltu.start()

        **Query parameters:

         NOTE: All datetime values as expected to format using ait.core.dmc.RFC3339_Format ( '%Y-%m-%dT%H:%M:%S.%fZ' )

         + CLTU: {none}
         + RAF:
             - start: start-time, defaults to None
             - end: end-time, defaults to None
         + RCF:
             - start: start-time, required
             - end: end-time, required
             - spacecraft_id: int value of spacecraft; optional when included in service creation
             - trans_frame_ver_num: int value of transfer frame version number, optional
             - master_channel: boolean flag indicating master channel
             - virtual_channel: int value of the virtual channel
             * NOTE: One of master_channel or virtual_channel must be provided

        :param interface:  Interface name ('raf','rcf','cltu')
        '''

        srvc_info = self.get_service(interface)
        if srvc_info is None:
            return None

        #Legal pre-state: BOUND

        if srvc_info.state == ServiceState.DISCONNECTED:
            logger.error(f"{interface} instance is not connected. Unable to start.")
            bottle.response.status = 400
            return None
        elif srvc_info.state == ServiceState.CONNECTED:
            logger.error(f"{interface} instance is not bound. Unable to start.")
            bottle.response.status = 400
            return None
        elif srvc_info.state == ServiceState.STARTED:
            logger.error(f"{interface} instance already started")
            bottle.response.status = 400
            return None

        if self.verbose:
            ait.core.log.info(f"{interface} starting...")

        if srvc_info.type == ServiceType.CLTU:
            try:
                srvc_info.service.start()
                srvc_info.state = ServiceState.STARTED
            except socket.error as e:
                #srvc_info.state = ServiceState.ERROR
                logger.error(f"Error occurred while attempting to start {interface} instance")
                bottle.response.status = 400
                return None
        else:

            #Both RAF and RCF accept start and end datetimes (or None)
            start = None
            end = None

            if 'start' in bottle.request.query:
                try:
                    start_str = bottle.request.query['start']
                    start = datetime.datetime.strptime(start_str, dmc.RFC3339_Format)
                except ValueError as ve:
                    logger.error(f"Value of 'start' ({start_str}) parameter does not adhere to datetime ISO format: {ve}")
                    bottle.response.status = 400
                    return None

            if 'end' in bottle.request.query:
                try:
                    end_str = bottle.request.query['end']
                    end = datetime.datetime.strptime(end_str, dmc.RFC3339_Format)
                except ValueError as ve:
                    logger.error(f"Value of 'end' ({end_str}) parameter does not adhere to datetime ISO format: {ve}")
                    bottle.response.status = 400
                    return None


            # If RAF, we are ready to go
            if srvc_info.type == ServiceType.RAF:

                try:
                    srvc_info.service.start(start, end)
                    srvc_info.state = ServiceState.STARTED
                except Exception as e:
                    ait.core.log.error(f"Error occurred while attempting to start {interface} instance")
                    bottle.response.status = 400
                    return None

            else: #Must be RCF, we need more info...

                master_channel = None
                virtual_channel = None
                spacecraft_id = None
                trans_frame_ver_num = None

                if start is None or end is None:
                    ait.core.log.error(f"RCF start request requires an explicit 'start' and 'end' query parameters")
                    bottle.response.status = 400
                    return None

                if 'master_channel' in bottle.request.query:
                    try:
                        mc_str = bottle.request.query['master_channel']
                        master_channel = bool(mc_str)
                    except ValueError as ve:
                        logger.error(f"Value of 'master_channel' ({mc_str}) parameter must be a boolean: {ve}")
                        bottle.response.status = 400
                        return None

                if 'virtual_channel' in bottle.request.query:
                    try:
                        vc_str = bottle.request.query['virtual_channel']
                        virtual_channel = int(vc_str)
                    except ValueError as ve:
                        logger.error(f"Value of 'virtual_channel' ({vc_str}) parameter must be an integer: {ve}")
                        bottle.response.status = 400
                        return None

                if 'spacecraft_id' in bottle.request.query:
                    try:
                        si_str = bottle.request.query['spacecraft_id']
                        spacecraft_id = int(si_str)
                    except ValueError as ve:
                        logger.error(f"Value of 'spacecraft_id' ({si_str}) parameter must be an integer: {ve}")
                        bottle.response.status = 400
                        return None

                if 'trans_frame_ver_num' in bottle.request.query:
                    try:
                        tfvn_str = bottle.request.query['trans_frame_ver_num']
                        trans_frame_ver_num = int(tfvn_str)
                    except ValueError as ve:
                        logger.error(f"Value of 'trans_frame_ver_num' ({tfvn_str}) parameter must be an integer: {ve}")
                        bottle.response.status = 400
                        return None

                if not master_channel and virtual_channel is None:
                    ait.core.log.error(f"RCF start request requires one of 'master_channel' or 'virtual_channel' "
                                       f"query parameters")
                    bottle.response.status = 400
                    return None

                if spacecraft_id is None and srvc_info.service._scid is None:
                    ait.core.log.error(f"RCF start request requires 'spacecraft_id' query parameter since it "
                                       f"was not provided at service instantiation")
                    bottle.response.status = 400
                    return None

                try:
                    srvc_info.service.start(start, end, spacecraft_id, trans_frame_ver_num,
                                            master_channel, virtual_channel)
                    srvc_info.state = ServiceState.STARTED
                except Exception as e:  ##General handler for socket.error, AttributeError
                    ait.core.log.error(f"Error occurred while attempting to start {interface} instance")
                    bottle.response.status = 400
                    return None

            if srvc_info.state == ServiceState.STARTED and self.verbose:
                ait.core.log.info(f"{interface} started.")

    def stop_handler(self, interface):
        '''
        Stop the SLE object specified by <interface>.
        Example:
        /stop/cltu is equivalent to running cltu.stop()
        :param interface:  Interface name ('raf','rcf','cltu')
        '''

        srvc_info = self.get_service(interface)
        if srvc_info is None:
            return None

        # Legal pre-state: STARTED

        if srvc_info.state != ServiceState.STARTED:
            ait.core.log.error(f"{interface} instance is not started. Unable to stop.")
            bottle.response.status = 400
        else:
            try:
                srvc_info.service.stop()
                srvc_info.state = ServiceState.BOUND

                if self.verbose:
                    ait.core.log.info(f"{interface} stopped.")

            except socket.error as e:
                ait.core.log.error(f"Error occurred while attempting to stop {interface} instance")
                bottle.response.status = 400
                return None



    def unbind_handler(self, interface):
        '''
        Unbind the SLE object specified by <interface>.
        Example:
        /unbind/cltu is equivalent to running cltu.unbind()
        :param interface:  Interface name ('raf','rcf','cltu')
        '''
        srvc_info = self.get_service(interface)
        if srvc_info is None:
            return None

        # Legal pre-state: BOUND

        if srvc_info.state != ServiceState.BOUND:
            ait.core.log.error(f"{interface} instance is not bound. Unable to unbind.")
            bottle.response.status = 400
        else:

            try:
                srvc_info.service.unbind()
                srvc_info.state = ServiceState.CONNECTED

                if self.verbose:
                    ait.core.log.info(f"{interface} unbound.")

            except Exception as e:
                ait.core.log.error(f"Error occurred while attempting to unbind {interface} instance")
                bottle.response.status = 400
                return None



    def disconnect_handler(self, interface):
        '''
        Disconnect the SLE object specified by <interface>.
        Example:
        /disconnect/cltu is equivalent to running cltu.disconnect()
        :param interface:  Interface name ('raf','rcf','cltu')
        '''
        srvc_info = self.get_service(interface)
        if srvc_info is None:
            return None

        # Legal pre-state: CONNECTED

        if srvc_info.state != ServiceState.CONNECTED:
            ait.core.log.error(f"{interface} instance is not connected. Unable to disconnect.")
            bottle.response.status = 400
        else:

            try:
                srvc_info.service.disconnect()
                srvc_info.state = ServiceState.DISCONNECTED

                if self.verbose:
                    ait.core.log.info(f"{interface} disconnected.")

            except socket.error as e:
                ait.core.log.error(f"Error occurred while attempting to unbind {interface} instance")
                bottle.response.status = 400
                return None


    def upload_handler(self, interface):
        '''
        Only valid call is /upload/cltu
        This function will upload the tc_data attribute of the class.
        :param interface:  Interface name ('cltu')
        '''
        srvc_info = self.get_service(interface)
        if srvc_info is None:
            return None
        if srvc_info.type not in self.upload_service_types:
            ait.core.log.error(f"{interface} instance does not support upload.")
            bottle.response.status = 400
            return None

        # Legal pre-state: STARTED

        if srvc_info.state != ServiceState.STARTED:
            ait.core.log.error(f"{interface} instance is not started. Unable to upload.")
            bottle.response.status = 400

        if srvc_info.type == ServiceType.CLTU:
            proceed = True
            data_len = len(srvc_info.data)

            if self.verbose:
                if data_len == 0:
                    ait.core.log.info("No CLTU data to push.")
                else:
                    ait.core.log.info(f"Pushing {data_len} chunks of CLTU data")

            while srvc_info.data and proceed:
                data_to_push = srvc_info.data[0]
                try:
                    self.cltu_service.service.upload_cltu(data_to_push)
                    del srvc_info.data[0]
                    if self.verbose:
                        ait.core.log.info(f"tc_data sent: {data_to_push}")
                except Exception as e:
                    ait.core.log.error(f"Error occurred while uploading CLTU data: {e}")
                    bottle.response.status = 400
                    proceed = False


    def append_cltu_data(self, data):
        '''
        Appends the data entry into the CLTU's data array
        :param data: Data to be appended
        '''
        interface = 'cltu'
        srvc_info = self.get_service(interface)
        if srvc_info is None:
            return None

        # no multithreads so this should be safe
        srvc_info.data.append(data)

        if self.verbose:
            ait.core.log.info(f"Data appended to CLTU data queue.")

class CLTUServer(DatagramServer):
    '''
    A server which listens at a specified port for data, and then updates the CLTU
    service
    '''

    def __init__(self, sle_interfaces, *args, **kwargs):
        self._sle_interfaces = sle_interfaces
        gevent.server.DatagramServer.__init__(self, *args, **kwargs)

    def handle(self, data, address): # pylint:disable=method-hidden
        '''
        Pass data to the SLE services CLTU service
        '''
        self._sle_interfaces.append_cltu_data(data)



