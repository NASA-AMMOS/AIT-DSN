AIT Encryption
================

This guide covers AIT's encryption support as provided by the AIT-DSN repository.

AIT offers an encryption API with some supported implementations, and to which extensions can be added.
The default implementation, *NullEncrypter*, supports the API but performs no encryption/decryption.

For projects which utilize the MGSS KMC SDLS Encryption service, AIT offers a wrapper for that service, :ref:`KmcSdlsEncrypter<kmc-client-label>`.


Encryption is currently limited to support command uplink (TC Frames), though may be expanded for downlink at some future date.


Configuration
-------------

The necessary configuration parameters can be added to the **config.yaml**; under 'dsn:encryption'.
Optionally, many of the same parameters can also be passed in at runtime as keyword arguments for greater flexibility.
Below demonstrates the structure of the encryption configuration section:


::

    dsn:
        encryption:
            vcid_filter: [list of vcids for which encryption applies]  #None means all VCIDs included, empty list means No VCID's allowed)
            client:
                name: ait.dsn.encrypt.module.class
                config:
                    <client-specific-config, parsed by Encrypter implementation>


Using the Encryption API
------------------------

First, an encrypter instance must be created.  AIT provides a factory that instantiates the encrypter instance.
The factory can be provided with the full classname of the desired instance, or rely on the AIT config.
If no class is specified in either case, then the default implementation returned will be the NullEncrypter.

::

    # Import the encrypter module
    from ait.dsn.encrypt.encrypter import EncryptMode, EncryptResult, EncrypterFactory, BaseEncrypter

    # 1) Rely on AIT configuration for encrypter instance, or return default
    encrypter = EncrypterFactory().get()

    # ...or 2) Specify the desired class to be used via argument
    encrypter_cls = 'extended.encryption.module.class'
    encrypter = EncrypterFactory().get(encrypter_cls)


Next, the instance must be configured and connected.

By default, configuration can rely solely on the AIT config. The Encrypter API supports keyword arguments for the configure() method, which would override values specified in the AIT config.

::

    # 1) Configure, rely solely on AIT config
    encrypter.configure()

    # ...or 2) configure passing in keyword arguments, will override AIT config
    encrypter.configure(**kwargs)

    # Connect the instance
    encrypter.connect()


Now the encrypter instance can be used to encrypt and decrypt *bytearrays* .

::

    in_bytearray = bytearray(input_bytes)
    out_bytes = None

    # For encryption
    crypt_result = encrypter.encrypt(in_bytearray)

    # - or -

    # For decryption
    crypt_result = encrypter.decrypt(in_bytearray)

    if crypt_result.has_errors:
        for e in crypt_result.errors:
            ait.core.log.error(f"Error occurred during processing {e}")
    elseif crypt_result.has_result:
        out_bytearray = crypt_result.result
        out_bytes = bytes(out_bytearray)


When processing is complete, you can close the encrypter instance:

::

    # Close the encrypter, releasing any resources
    encrypter.close()


.. _kmc-client-label:

AIT Encryption using MGSS KMC SDSL Client
-----------------------------------------


Setting up the environment
^^^^^^^^^^^^^^^^^^^^^^^^^^

MGSS provides the KMC SDLS client for which AIT offers a wrapper.

The KMC client should already have been installed in your environment.
Otherwise, you may install it locally via an expanded tar-ball distribution.
In either situation, the client contains shared libraries and Python wrappers.


Notes
^^^^^

- This document provides :ref:`example configurations<kmc-config-label>` only. For the proper set of KMC properties to include for your particular environment, please contact your project GDS or KMC-deployment representative.

- While AIT typically recommends Python 3.7, MGSS is currently supporting only Python 3.6, 3.8 and 3.9.  As such, we recommend users switch to Python 3.8 for combined AIT tools and KMC Client. No compatibility issues have been found using this version, thus far.


Installing Extra Dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The KMC client relies on the **cffi** ('C Foreign Function Interface for Python') library, which is not automatically imported by AIT-DSN's installation step.

As such, you will need to install this library manually, preferably within your virtual environment.
This step should occur once, as an extra step after installing AIT-DSN:

::

    pip install cffi



Environment Variables Setup
^^^^^^^^^^^^^^^^^^^^^^^^^^^

AIT continues to recommend the use of virtual environments when using its tools.
However, further manual steps involving environmental variables are required to ensure that AIT can find and load the KMC client.
Below are setup steps used to integrate this client with your AIT repository.

We recommend that these steps be captured in a environment setup script.

::

    ## Standard steps:
    # Set some environment variables pointing to your expanded KMC tarball
    setenv KMC_CLIENT_HOME /path/to/installed/kmc/client/
    setenv KMC_PYTHON_VERSION python3.8

    setenv LD_LIBRARY_PATH ${KMC_CLIENT_HOME}/lib/:${LD_LIBRARY_PATH}
    setenv PYTHONPATH ${KMC_CLIENT_HOME}/lib/${KMC_PYTHON_VERSION}/site-packages/


    ## Special step for Conda 8:
    ## There is a known bug with Conda8 that requires this envVar be set.
    ## Without this, we get error along lines of:
    ## /lib64/libk5crypto.so.3: undefined symbol: EVP_KDF_ctrl, version OPENSSL_1_1_1b
    ## ..when loading the KMC Client.
    setenv LD_PRELOAD = /usr/lib64/libcrypto.so.1.1

From this point, the AIT KMC wrapper should be able to load all libraries and Python modules.


Check Installation
^^^^^^^^^^^^^^^^^^

Now that your installation has finished let's check that everything works as expected.

.. code-block:: bash

   # Test that you can properly import the KMC client package.
   > python -c "import gov.nasa.jpl.ammos.kmc.sdlsclient.KmcSdlsClient"

If the last command **doesn't** generate any errors your installation is all set!

If you see an error as shown below make sure to activate your virtual environment first, and set the required environment variables.

.. code-block:: bash

   > python -c "import gov.nasa.jpl.ammos.kmc.sdlsclient.KmcSdlsClient"
    Traceback (most recent call last):
      File "<string>", line 1, in <module>
    ModuleNotFoundError: No module named 'gov.nasa.jpl.ammos.kmc.sdlsclient.KmcSdlsClient'


.. _kmc-config-label:

Example AIT Configuration for KMC
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

An *example* of a configuration that uses the KMC SDLS encrypter for Spacecraft ID (SCID) 44 and Virtual Channel IDs (VCIDs) 0-3:

::

    dsn:
        encryption:
            vcid_filter: [ 0, 1, 2, 3]
            client:
                name: ait.dsn.encrypt.kmc_encrypter.KmcSdlsEncrypter
                config:
                    kmc_properties:
                        - cryptolib.sadb.type=mariadb
                        - cryptolib.crypto.type=kmccryptoservice
                        - cryptolib.process_tc.ignore_antireplay=true
                        - cryptolib.process_tc.ignore_sa_state=true
                        - cryptolib.process_tc.process_pdus=false
                        - cryptolib.sadb.mariadb.fqdn=asec-cmdenc-dev2.jpl.nasa.gov
                        - cryptolib.sadb.mariadb.username=testuser2
                        - cryptolib.sadb.mariadb.password=
                        - cryptolib.sadb.mariadb.tls.cacert=/etc/pki/tls/certs/ammos-ca-bundle.crt
                        - cryptolib.sadb.mariadb.tls.verifyserver=true
                        - cryptolib.sadb.mariadb.mtls.clientcert=/etc/pki/tls/certs/local-test-cert.pem
                        - cryptolib.sadb.mariadb.mtls.clientkey=/etc/pki/tls/certs/local-test-key.pem
                        - cryptolib.sadb.mariadb.require_secure_transport=true
                        - cryptolib.crypto.kmccryptoservice.protocol=https
                        - cryptolib.crypto.kmccryptoservice.fqdn=asec-cmdenc-srv1.jpl.nasa.gov
                        - cryptolib.crypto.kmccryptoservice.app=crypto-service
                        - cryptolib.crypto.kmccryptoservice.mtls.clientcert=/etc/pki/tls/certs/local-test-cert.pem
                        - cryptolib.crypto.kmccryptoservice.mtls.clientcertformat=PEM
                        - cryptolib.crypto.kmccryptoservice.mtls.clientkey=/etc/pki/tls/certs/local-test-key.pem
                        - cryptolib.crypto.kmccryptoservice.cacert=/etc/pki/tls/certs/ammos-ca-bundle.crt
                        - cryptolib.crypto.kmccryptoservice.verifyserver=true
                        - cryptolib.tc.vcid_bitmask=0x07
                        - cryptolib.apply_tc.create_ecf=true
                        - cryptolib.process_tc.check_fecf=false
                        - cryptolib.tc.44.0.0.has_segmentation_header=false
                        - cryptolib.tc.44.0.0.has_pus_header=false
                        - cryptolib.tc.44.0.0.has_ecf=true
                        - cryptolib.tc.44.0.0.max_frame_length=1024
                        - cryptolib.tc.44.1.0.has_segmentation_header=false
                        - cryptolib.tc.44.1.0.has_pus_header=false
                        - cryptolib.tc.44.1.0.has_ecf=true
                        - cryptolib.tc.44.1.0.max_frame_length=1024
                        - cryptolib.tc.44.2.0.has_segmentation_header=false
                        - cryptolib.tc.44.2.0.has_pus_header=false
                        - cryptolib.tc.44.2.0.has_ecf=true
                        - cryptolib.tc.44.2.0.max_frame_length=1024
                        - cryptolib.tc.44.3.0.has_segmentation_header=false
                        - cryptolib.tc.44.3.0.has_pus_header=false
                        - cryptolib.tc.44.3.0.has_ecf=true
                        - cryptolib.tc.44.3.0.max_frame_length=1024
                    kmc_property_file: None


The KMC-encrypter supports either the *kmc_properties* list or a single *kmc_property_file*, but not both.
If both are specified, and the value of the *kmc_property_file* points to a file that exists, the file will be used.
Else the properties will be used.

The format for the KMC properties file is a single property-pair (property.name=value) per line.
Comments can be included on their own lines and must start with the '#' character.

An abbreviated example of a KMC property file:

::

  # CMT: Properties for sample deployment
  cryptolib.sadb.type=mariadb
  cryptolib.crypto.type=kmccryptoservice
  cryptolib.process_tc.ignore_antireplay=true



KMC SDSL Client API Specifics
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

While the AIT Encyryption API handles input/output for encryption and decryption generically, the KMC SDSL Client has some specialization.

  * Encryption:

    - Input: an unencrypted telecommand (TC), as byte-array
    - Output: entire encrypted telecommand, as byte-array

  * Decryption:

    - Input: an encrypted telecommand, as byte-array
    - Output: only the decrypted telecommand's user-data/payload, as byte-array



	
EncrypterPlugin
---------------

The EncrypterPlugin provides a command processing pipeline the ability to encrypt TCTFs.
The plugin will read and use any configuration specified in the config.yaml.

First, configure the parameters in config.yaml as described above.

Then add the following block to the plugins section of config.yaml

::
            - plugin:
                name: ait.dsn.plugins.EncrypterPlugin.Encrypter
                inputs:
                    - TCTF_Manager

The EncrypterPlugin will now encrypt the TCTF whenever TCTF_Manager publishes on the PUB/SUB network.
Set the next pipeline element to receive *Encrypter* as its input in order to continue processing the encrypted TCTF.
