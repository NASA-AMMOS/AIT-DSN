AIT Encryption
================

This guide covers AIT's encryption support as provided by the AIT-DSN repository.

AIT offers an encryption API with some supported implementations, and to which extensions can be added.
The default implementation, NullEncrypter, supports the API but performs no encryption/decryption.

For projects which utilize the MGSS KMC SDLS Encryption service, AIT offers a wrapper for that service, KmcSdlsEncrypter.

Encryption is currently limited to support command uplink (TC Frames), though may be expanded for downlink at some future date.



Configuration
^^^^^^^^^^^^^

The necessary configuration parameters can be added to the **config.yaml**; under 'dsn:encryption'.
Optionally, many of the same parameters can also be passed in at runtime as keyword arguments for greater flexibility.
Below is an example configuration which can be used as a reference, in addition to the default configuration available in the repository.


::

    dsn:
        encryption:
            vcid_filter: [list of vcids for which encryption applies]  #None means all VCIDs included, empty list means No VCID's allowed)
            client:
                name: ait.dsn.encrypt.module.class
                config:
                    <client-specific-config, parsed by implementation>



An *example* of the configuration that uses the KMC SDLS encrypter (configured to use Cryptolib) is:

::

    dsn:
        encryption:
            vcid_filter: None
            client:
                name: ait.dsn.encrypt.kmc_encrypter.KmcSdlsEncrypter
                config:
                    kmc_properties:
                      - cryptolib.sadb.type=inmemory
                      - cryptolib.crypto.type=libgcrypt
                      - cryptolib.process_tc.ignore_antireplay=true
                      - cryptolib.process_tc.ignore_sa_state=true
                      - cryptolib.process_tc.process_pdus=false
                      - cryptolib.tc.vcid_bitmask=0x3F
                      - cryptolib.tc.3.0.has_segmentation_header=true
                      - cryptolib.tc.3.0.has_pus_header=true
                      - cryptolib.tc.3.0.has_ecf=true
                      - cryptolib.tc.3.0.max_frame_length=1024
                    kmc_property_file: None


Note: The KMC-encrypter supports either the *kmc_properties* list or a single *kmc_property_file*, but not both.
If both are specified, and the value of the *kmc_property_file* points to a file that exists, the file will be used.
Else the properties will be used.

Note: For the *proper* set of kmc_properties to include for your particular environment, please contact your GDS or KMC-deployment representative.


Using the Encryption API
^^^^^^^^^^^^^^^^^^^^^^^^

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

    # Configure, rely solely on AIT config
    encrypter.configure()

    # ...or configure passing in keyword arguments, will override AIT config
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
        for e in ait_result.errors:
            ait.core.log.error(f"Error occurred during processing {e}")
    elseif crypt_result.has_result:
        out_bytearray = ait_result.result
        out_bytes = bytes(out_bytearray)


When processing is complete, you can close the encrypter instance:

::

    # Close the encrypter, releasing any resources
    encrypter.close()


Setting up your environment for MGSS KMC SDSL Client
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

MGSS provides the KMC SDLS client for which AIT offers a wrapper.

The KMC client should already have been installed in your environment.
Otherwise, you may install it locally via an expanded tar-ball distribution.
In either situation, the client contains shared libraries and Python wrappers.

Notes
-----

- Configuration of the KMC client falls outside the scope of this document.  Please refer to your GDS rep.

- While AIT typically recommends Python 3.7, MGSS is currently supporting only Python 3.6, 3.8 and 3.9.  As such, we recommend users switch to Python 3.8 for combined AIT tools and KMC Client. No compatibility issues have been found using this version, thus far.

Environment Variables Setup
---------------------------

AIT continues to recommend the usage of virtual environments when using its tools.
However, further manual steps are required to ensure that AIT can find and load the KMC client.
Below are setup steps used to integrate this client with your AIT repository.

We recommend that these steps be captured in a environment setup script.

::

    # Set some environment variables pointing to your expanded KMC tarball
    setenv KMC_CLIENT_HOME /path/to/installed/kmc/client/
    setenv KMC_PYTHON_VERSION python3.8

    setenv LD_LIBRARY_PATH ${KMC_CLIENT_HOME}/lib/:${LD_LIBRARY_PATH}
    setenv PYTHONPATH ${KMC_CLIENT_HOME}/lib/${KMC_PYTHON_VERSION}/site-packages/

From this point, the AIT KMC wrapper should be able to load all libraries and Python modules.


Check Installation
------------------

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

