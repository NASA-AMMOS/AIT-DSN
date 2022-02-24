import datetime as dt
import itertools
import math
import os.path
import os
from pathlib import Path
import json

import ait
import ait.dsn.util.utils
from ait.core import cfg, log
from ait.dsn.encrypt.encrypter import EncryptResult, EncryptMode, BaseEncrypter

# Using these Alias fields to indicate if appropriate respective classes were loaded from KMC third-party import
KMC_Error_Alias = Exception
KMC_Class_Alias = None
try:
    from gov.nasa.jpl.ammos.kmc.sdlsclient.KmcSdlsClient import KmcSdlsClient, SdlsClientException
    KMC_Error_Alias = SdlsClientException
    KMC_Class_Alias = KmcSdlsClient
except ModuleNotFoundError as mnfer:
    err_mesg = f"Unable to load the KmcSdlsClient library: {mnfer}"
    log.error(err_mesg)

"""
AIT Encryption extension using the MGSS KMC SDLS Encryption client

"""

'''
Config:

default:
    dsn:
        encryption:
            vcid_filter: [list of vcids for which encryption applies]  (None means all VCIDs included, empty list means No VCID's allowed)
            client:
                name: ait.dsn.encrypt.kmc_encrypter.KmcSdlsEncrypter
                config:
                    kmc_properties:
                      - property1=value1  ( or 'property1 = value1' ? or 'property1: value1' ? ) 
                      - property2=value2
                         ...
                      - propertyN=valueN
                    kmc_property_file: None or location of file

'''


class KmcSdlsEncrypter(BaseEncrypter):
    ''' KMC SDLS Backend Encrypter

    This requires the SdlsClient Python library to be installed and KMC
    to be installed.
    '''
    kmclib_envvar_required = False
    kmclib_envvar = 'KMC_HOME'

    prop_kmc_properties = 'kmc_properties'
    prop_kmc_property_file = 'kmc_property_file'

    def __init__(self):
        '''
        Constructor for KmcSdlsEncrypter
        '''
        super().__init__()

        # KMC Client instance
        self._client = None

        # Points to the KMC properties file (maybe)
        self._kmc_properties_file = None

        # Newer approach of passing config to client via list
        self._kmc_config_list = []

        # Controls whether missing config file is error or warning (for now the latter)
        self.abort_on_missing_file = False

    def configure(self, **kwargs):
        '''
        Configures this encrypter instance.

        Checks for KMC properties as provided via the kwargs or AIT configuration.
        :param kwargs: Optional keyword arguments
        '''
        super().configure(**kwargs)

        if KmcSdlsEncrypter.kmclib_envvar_required:
            kmclib_envval = os.environ[KmcSdlsEncrypter.kmclib_envvar]
            if not kmclib_envval:
                err_mesg = f"KMC library requires environment variable to be set: {KmcSdlsEncrypter.kmclib_envvar}"
                log.error(err_mesg)
                raise cfg.AitConfigError(err_mesg)
            else:
                kmclib_path = Path(kmclib_envval)
                if not kmclib_path.is_dir():
                    err_mesg = f"KMC library environment variable {KmcSdlsEncrypter.kmclib_envvar} " \
                               f" is set to a directory that does not exist: {kmclib_path}"
                    log.error(err_mesg)
                    raise cfg.AitConfigError(err_mesg)

        # Pull config from the AIT config or keyword args
        lcl_config_list = kwargs.get(KmcSdlsEncrypter.prop_kmc_properties,
                                    ait.config.get(
                                        KmcSdlsEncrypter.cfg_client_config+"."+KmcSdlsEncrypter.prop_kmc_properties, []))

        # May need to format the properties
        self._kmc_config_list = self.format_config_list(lcl_config_list)

        # KMC-specific properties file
        kmc_props_file = kwargs.get(KmcSdlsEncrypter.prop_kmc_property_file,
                             ait.config.get(
                                 KmcSdlsEncrypter.cfg_client_config+"."+KmcSdlsEncrypter.prop_kmc_property_file, None))

        if kmc_props_file:
            expanded_props_file = ait.dsn.util.utils.expand_path(kmc_props_file)
            kmc_props_path = Path(expanded_props_file)
            if kmc_props_path.is_file():
                self._kmc_properties_file = expanded_props_file
                # KMC isn't accepting files, so we have to parse to config list
                file_config_list = []
                with open(self._kmc_properties_file) as props_file:
                    for line in props_file:
                        line = line.strip()
                        if line and (not line.startswith("#")): #skip comments and empty lines
                            file_config_list.append(line.rstrip())

                self._kmc_config_list = self.format_config_list(file_config_list)
            else:
                err_mesg = f"KMC Properties File does not exist: {kmc_props_file}"
                if self.abort_on_missing_file:
                    log.error(err_mesg)
                    raise cfg.AitConfigError(err_mesg)
                else:
                    log.warn(err_mesg)
                    log.warn(f"Defaulting to the embedded property list for configuration.")

        if self._debug_enabled:
            log.info(f"KmcSdlsEncrypter: KMC property file is: {self._kmc_properties_file}")
            log.info(f"KmcSdlsEncrypter: KMC property list is: {self._kmc_config_list}")

    def connect(self):
        '''
            Connect to an KMC SDSL service instance
            During the configure() step, configuration information was retrieved.
            If properties file was provided, then it will be used.
            Else the property list (potentially empty) will be used.

            :except: SdlsClientException if SDLS Client error occurs
            :except: Exception if other error occurs
        '''

        # Current attempt at checking if KMC library was loaded, probably something better out there
        if KMC_Class_Alias is None:
            err_mesg = f"KmcSdlsClient library was not loaded"
            log.error(err_mesg)
            return

        try:
            self._client = KmcSdlsClient(self._kmc_config_list)
        except KMC_Error_Alias as scex:
            log.error(f"SDLS Client Error occurred while instantiating KMC Client: '{scex}'")
            raise scex
        except Exception as ex:
            log.error(f"Error occurred while instantiating KMC Client: '{ex}'")
            raise ex

    def encrypt(self, input_bytes):
        ''' Encrypts a byte-array using the KMC Encrypter

            :param: input_bytes Original byte-array to be encrypted
            :returns: EncryptResult object with result or errors
        '''

        if not self._client:
            err_msg = "KMC SDLS Client is not connected"
            return EncryptResult(mode=EncryptMode.ENCRYPT, input=input_bytes, errors=[str(err_msg)])

        try:
            output_bytes = self._client.apply_security_tc(input_bytes)
            return EncryptResult(mode=EncryptMode.ENCRYPT, input=input_bytes, result=output_bytes)
        except SdlsClientException as sc_ex:
            return EncryptResult(mode=EncryptMode.ENCRYPT, input=input_bytes, errors=[str(sc_ex)])

    def decrypt(self, input_bytes):
        ''' Decrypts a byte-array using the KMC Encryption client.

            Per the KMC specification, the result of the successful decryption
            is only the user-data/payload/PDU portion of the whole Telecommand

            :param: input_bytes Original byte-array to be decrypted
            :returns: EncryptResult object with result or errors
        '''

        if not self._client:
            err_msg = "KMC SDLS Client is not connected"
            return EncryptResult(mode=EncryptMode.DECRYPT, input=input_bytes, errors=[str(err_msg)])

        try:

            # process_security_tc() returns:
            #        class TC(NamedTuple):
            #            tc_header: TC_FramePrimaryHeader
            #            tc_security_header: TC_FrameSecurityHeader
            #            tc_pdu: bytearray  (the decrypted payload)
            #            tc_security_trailer: TC_FrameSecurityTrailer

            tc_result = self._client.process_security_tc(input_bytes)
            if tc_result.tc_pdu is None:
                tc_err_msg = "Decryption returned with empty result"
                return EncryptResult(mode=EncryptMode.DECRYPT, input=input_bytes, errors=[tc_err_msg])
            else:
                if self._debug_enabled:
                    log.info(f"KmcSdlsEncrypter:decrypt(): Decryption TC result: {tc_result}")
                output_bytes = tc_result.tc_pdu
                return EncryptResult(mode=EncryptMode.DECRYPT, input=input_bytes, result=output_bytes)

        except SdlsClientException as sc_ex:
            return EncryptResult(mode=EncryptMode.DECRYPT, input=input_bytes, errors=[str(sc_ex)])

    def show_config(self):
        '''
        Return encrypter name and associated configuration
        :return: Configuration information
        '''
        if self._client:
            if self._kmc_properties_file:
                return f"KmcSdlsEncrypter[property_file: {self._kmc_properties_file}]"
            elif self._kmc_config_list:
                return f"KmcSdlsEncrypter[property_list: {self._kmc_config_list}]"
            else:
                return "KmcSdlsEncrypter[no configuration]"

    def close(self):
        '''
        Release the reference to the KMC client
        '''
        if self._client:
            self._client = None

    def is_connected(self):
        '''
        Returns True if connected, False otherwise
        '''
        return self._client is not None

    def format_config_list(self, cfg_list):
        '''
        Applies formatting to the incoming list of configuration properties.
        Currently, it just expands values for envVars and ~
        :param cfg_list: Input config list
        :return: Formatted version of config list
        '''
        # expand any path values
        formatted_list = []
        for cfg_line in cfg_list:
            if "=" in cfg_line:
                cfg_pair = cfg_line.split('=', 1)
                cfg_val = ait.dsn.util.utils.expand_path(cfg_pair[1], False)
                formatted_list.append(f"{cfg_pair[0]}={cfg_val}")
        return formatted_list
