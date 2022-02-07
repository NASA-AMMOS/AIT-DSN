
from abc import ABCMeta, abstractmethod
import importlib
import copy
from enum import Enum

import ait
import ait.core.cfg
import ait.core.log

"""
AIT Encryption Classes and Functions

The ait.dsn.encrypt.encrypter module provides the API for encryption.
"""

'''
AIT Yaml Config Layout:

default:
    dsn:
        encryption:
            vcid_filter: [list of vcids for which encryption applies]  #None means all VCIDs included, empty list means No VCID's allowed
            client:
                name: ait.dsn.encrypt.module.class
                config:
                    <client-specific-config, parsed by impl>

'''

class EncryptMode(Enum):
    '''
    Enumeration for Encryption modes / directions
    '''
    ENCRYPT = 0
    DECRYPT = 1

class EncryptResult():
    '''AIT Encryption result wrapper.

    :class:`EncryptResult` is a minimal wrapper around encryption/decryption results /
    errors. All AIT encryption APIs that execute a encrypt and decrypt will return their results
    wrapped in an :class:`EncryptResult` object.

    :class:`EncryptResult` tracks four main attributes. Generally, an unused attribute
    will be None.

    **mode**
        Enumeration of EncryptMode.  Value is either ENCRYPT or DECRYPT

    **input**
        The input bytearray.

    **result**
        The result of the encryption/decryption request, as bytearray.

    **errors**
        An iterator of errors encountered during transformation execution.

    '''

    def __init__(self, mode=EncryptMode.ENCRYPT, input=None, result=None, errors=None):
        self._mode = mode
        self._input = input
        self._result = result
        self._errors = errors

    @property
    def mode(self):
        return self._mode

    @property
    def input(self):
        return self._input

    @property
    def errors(self):
        return self._errors

    @property
    def result(self):
        return self._result

    @property
    def has_result(self):
        return self._result is not None

    @property
    def has_errors(self):
        return self._errors is not None and len(self._errors) > 0

    def __repr__(self):
        return (
            f"EncryptResult("
            f"mode: {self._mode.name.lower()}, "
            f"has_input: {self._input is not None}, "
            f"has_result: {self._result is not None}, "
            f"has_errors: {self.has_errors})"
        )


class BaseEncrypter(object):
    ''' Generic enrypter abstraction

    BaseEncrypter attempts to adequately abstract encryption operations into
    a small set of common methods. Not all methods will be useful for every
    encrypter type and additional methods may need to be added for future
    encryption support.

    Generally, the expected method functionality should be

        configure
            Configure the instance, loading all necessary settings and
            preparing for connection

        connect
            Connect to instance of the encryption service.

        encrypt
            Encrypt a payload

        decrypt
            Decrypt a payload

        show_config
            Method that displays the service configuration, useful for development/debugging.

        close
            Close the connection to the encryption service and handle any cleanup

        is_connected
            Returns True if encrypter is connected, False otherwise

        is_configured
            Returns True if encrypter is configured, False otherwise
    '''

    # Allows this class to be meta (as an abstract base class)
    __metaclass__ = ABCMeta

    prop_vcid_filter = 'vcid_filter'
    prop_debug_enabled = 'debug_enabled'

    cfg_prefix = "dsn.encryption."
    cfg_client_name = cfg_prefix+"client.name"
    cfg_client_config = cfg_prefix+"client.config"

    def __init__(self):
        self._vcids_filter = None
        self._debug_enabled = False
        self._configured = False


    def configure(self, **kwargs):
        '''Setup the configuration for this instance.'''

        # Check if debug flag is included and set
        self._debug_enabled = kwargs.get(BaseEncrypter.prop_debug_enabled,
                                         ait.config.get(
                                             f"{BaseEncrypter.cfg_prefix}{BaseEncrypter.prop_debug_enabled}",
                                             False))

        # Pull in the list of VCID's for which encryption/decryption should be applied
        lcl_vcid_list = kwargs.get(BaseEncrypter.prop_vcid_filter,
                                   ait.config.get(
                                       f"{BaseEncrypter.cfg_prefix}{BaseEncrypter.prop_vcid_filter}", None))

        # If not None but not a list, so a scalar, then convert to a list
        if lcl_vcid_list is not None and not isinstance(lcl_vcid_list, list):
            lcl_vcid_list = [lcl_vcid_list]

        # None means no filtering applied, empty list means filter out all,
        # otherwise filter contains list of VCID's for which encryption is allowed
        self._vcids_filter = lcl_vcid_list

        self._configured = True

    @abstractmethod
    def connect(self):
        '''Connect to a backend's encryption instance.'''
        pass

    @abstractmethod
    def encrypt(self, input_bytes):
        ''' Encrypts a byte-array

            :param: input_bytes Original byte-array to be encrypted
            :returns: EncryptResult object with result or errors
        '''
        pass

    @abstractmethod
    def decrypt(self, input_bytes):
        ''' Decrypts a byte-array

            :param: input_bytes Original byte-array to be decrypted
            :returns: EncryptResult object with result or errors
        '''
        pass

    @abstractmethod
    def show_config(self):
        ''' Returns any configuration information as a str

            :returns: Configuration info string
        '''
        pass

    def vcid_is_supported(self, vcid):
        ''' Returns True if vcid is registered to be encrypted or filter is None

            :param: vcid VCID
            :returns: True if vcid is supported, False otherwise
        '''
        return self._vcids_filter is None or vcid in self.supported_vcids

    @abstractmethod
    def close(self):
        '''Connect to a backend's encryption instance, releases resources.'''
        pass

    @abstractmethod
    def is_connected(self):
        '''Returns True if encrypter is connected, False otherwise'''
        pass

    def is_configured(self):
        '''Returns True if encrypter has been configured, False otherwise'''
        return self._configured

class NullEncrypter(BaseEncrypter):
    ''' Null enrypter

    NullEncrypter implements the GenericEncrypter interface while providing no actual
    encryption or decryption.  Calls to either method will result in output
    that is a copy of the input.
    '''

    def __init__(self):
        '''No backend to load, so do not call the parent impl '''
        self._is_connected = False

    def configure(self,  **kwargs):
        super().configure(**kwargs)

    def connect(self):
        '''No connection is needed for this instance.'''
        self._is_connected = True

    def encrypt(self, input_bytes):
        '''
            Dummy implementation of encryption

            :param: input_bytes Original byte-array to be encrypted
            :returns: EncryptResult object with result or errors
        '''
        if self._is_connected:
            return EncryptResult(mode=EncryptMode.ENCRYPT, input=input_bytes, result=copy.copy(input_bytes))
        else:
            err_msg = "Client is not connected"
            return EncryptResult(mode=EncryptMode.ENCRYPT, input=input_bytes, errors=[str(err_msg)])

    def decrypt(self, input_bytes):
        '''
             Dummy implementation of decryption

             :param: input_bytes Original byte-array to be encrypted
             :returns: EncryptResult object with result or errors
        '''
        if self._is_connected:
            return EncryptResult(mode=EncryptMode.DECRYPT, input=input_bytes, result=copy.copy(input_bytes))
        else:
            err_msg = "Client is not connected"
            return EncryptResult(mode=EncryptMode.DECRYPT, input=input_bytes, errors=[str(err_msg)])

    def show_config(self):
        '''
             Returns config info for this instance

             :returns: Config info as string
        '''
        return "NullEncrypter[no configuration]"

    def close(self):
        '''No connection or cleanup required for this instance.'''
        self._is_connected = False

    def is_connected(self):
        '''
             Returns True if this instance is connected, False otherwise

             :returns: Conencted state
        '''
        return self._is_connected


class EncrypterFactory:

    default_clazz = 'ait.dsn.encrypt.encrypter.NullEncrypter'

    def __init__(self):
        pass

    @staticmethod
    def get(encrypter_class_name=None):
        '''
        Returns an instance of an Encrypter, based on argument or AIT configuration.
        If None is specified, then the AIT configuration is queried.
        If the config results in None, then a default implementation that performs no
        encryption is returned.

        The returned Encrypter has not yet been configured.

        :param: encrypter_class_name Optional encrypter class name
        :return: New instance of Encrypter
        :except: ImportError if specified encryption client is not found
        :except: AitConfigError for errors that occur during configuration
        '''

        full_class_name = encrypter_class_name
        lcl_instance = None
        if encrypter_class_name is None:
            cfg_class_name = ait.config.get(BaseEncrypter.cfg_client_name, None)
            if cfg_class_name:
                full_class_name = cfg_class_name

        if full_class_name is None:
            ait.core.log.error(f"No encryption client name specified, using a default")
            lcl_instance = NullEncrypter()
        else:
            try:
                mod, cls = full_class_name.rsplit('.', 1)
                lcl_instance = getattr(importlib.import_module(mod), cls)()
            except ImportError as ie:
                ait.core.log.error(f"Could not import specified encryption client '{full_class_name}'")
                raise ie

        return lcl_instance