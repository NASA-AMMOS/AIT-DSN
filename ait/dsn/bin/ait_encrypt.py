#!/usr/bin/env python

import argparse
from collections import OrderedDict

from pathlib import Path
import sys
import ait.core
from ait.dsn.encrypt.encrypter import EncryptMode, EncryptResult, EncrypterFactory, BaseEncrypter
import traceback

'''

usage: ait_encrypt.py [-h] --mode {encrypt,decrypt} --type TYPE --input INPUT 
                      [--output OUTPUT] [--verbose]

Performs encryption or decryption on bytes from a file.

optional arguments:
  -h, --help            show this help message and exit
  --mode {encrypt,decrypt}
                        Mode: 'encrypt', 'decrypt' (default: encrypt)
  --type TYPE           Type of encrypter to use: 'null', 'kmc'; or full class name
                        (default: null)
  --input INPUT         Input filename, required. (default: None)
  --output OUTPUT       Output filename, optional. (default: None)
  --verbose             Print debug messages. (default: False)
  
Examples:

  $ ait_encrypt --mode encrypt --type null --input input.bin  --output output.bin
  $ ait_encrypt --mode decrypt --type null --input output.bin --output restored.bin
  
'''

this = sys.modules[__name__]

# Dict from short-name to full classname for known Encrypters
this.encrypter_class_map = {'null'  : 'ait.dsn.encrypt.encrypter.NullEncrypter',
                       'kmc'   : 'ait.dsn.encrypt.kmc_encrypter.KmcSdlsEncrypter'}

this.debug_enabled = False


def main():

    descr = "Performs encryption or decryption on bytes from a file."

    parser = argparse.ArgumentParser(

        description=descr,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    encrypt_mode_list = list(map(lambda x: x.name.lower(), EncryptMode))
    encrypt_mode_list_str = str(encrypt_mode_list)[1:-1]

    encrypt_type_list = list(this.encrypter_class_map.keys())
    encrypt_type_list_str = str(encrypt_type_list)[1:-1]

    arg_defns = OrderedDict({
        '--mode': {
            'type': str,
            'default': EncryptMode.ENCRYPT.name.lower(),
            'choices' : encrypt_mode_list,
            'help': f"Mode: {encrypt_mode_list_str}",
            'required': True
        },
        '--type': {
            'type': str,
            'default': 'null',
            'help': f"Type of encrypter to use: {encrypt_type_list_str}; or full class name",
            'required': True
        },
        '--input': {
            'type': str,
            'default': None,
            'help': 'Input filename, required.',
            'required': True
        },
        '--output': {
            'type': str,
            'default': None,
            'help': 'Output filename, optional.'
        },
        '--verbose': {
            'action': 'store_true',
            'default': False,
            'help': 'Print debug messages.'
        },

    })


    ## Push argument defs to the parser
    for name, params in arg_defns.items():
        parser.add_argument(name, **params)

    ## Get arg results of the parser
    args = parser.parse_args()

    type = args.type
    mode = args.mode
    in_filename = args.input
    out_filename  = args.output
    this.debug_enabled = args.verbose



    if mode not in encrypt_mode_list:
        ait.core.log.error(f"Unrecognized encryption mode option: {mode}")
        ait.core.log.error(f"Legal values are: {encrypt_mode_list_str}")
        sys.exit()

    encrypt_mode = EncryptMode[mode.upper()]

    in_filepath = Path(in_filename)
    if not in_filepath.is_file():
        ait.core.log.error(f"File '{in_filename}' does not exist")
        sys.exit()

    in_file = open(in_filename, "rb")
    in_data = in_file.read()
    in_file.close()

    if this.debug_enabled:
        ait.core.log.info(f"Input:\n{in_data.hex()}")

    # Convert bytes to bytearray
    in_byte_arr  = bytearray(in_data)

    # Captures the processing output (as bytearray)
    out_byte_arr = None
    try:
        out_byte_arr = process_data(in_byte_arr, encrypt_mode, type)
    except Exception as ex:
        ait.core.log.error(f"Error occurred during processing: {ex}")
        traceback.print_exc()
        sys.exit()

    if out_byte_arr is not None:
        out_data = bytes(out_byte_arr)


        if out_filename:
            # Write to file
            if this.debug_enabled:
                ait.core.log.info(f"Saving result to {out_filename}")
            out_file = open(out_filename, "wb")
            out_file.write(out_data)
            out_file.close()
        else:
            # Write to screen
            out_data_str = out_data.hex()
            if this.debug_enabled:
                ait.core.log.info(f"Result:\n{out_data_str}")
            else:
                print(f"{out_data_str}")
    else:
        ait.core.log.error(f"No output from processing.")
        sys.exit()

def get_encrypter(type=None):
    '''
    Returns a newly instantiated, configured and connected Encrypter instance
    If type is shortname per encrypter class dict, then associated class is used.
    If type contains a period, it is assumed to be the full encrypter class name
    If type is None, then a default encrypter will be returned
    :param type: Short name based on supported map, or full encrypter class name, or None
    :return: New Encrypter instance
    '''
    encrypter_clazz = None
    encrypter_inst = None

    # If type contains a period, assume its the full classname
    if type is not None:
        if '.' in type:
            encrypter_clazz = type
        elif type in this.encrypter_class_map.keys():
            encrypter_clazz = this.encrypter_class_map.get(type)

    encrypter_inst = EncrypterFactory().get(encrypter_clazz)

    if encrypter_inst:
        encrypter_inst.configure(debug_enabled=this.debug_enabled)
        encrypter_inst.connect()

    return encrypter_inst

def process_data(in_data, mode, encr_type=None):
    '''
    Process the input data, based on the mode and encrypter type
    :param mode: EncryptMode enum
    :param in_data: Input data
    :param encr_type: Type of the Encrypter to use
    :return: Processed (encrypted or decrypted) output as bytearray, no None
    '''

    out_data = None

    encr = get_encrypter(encr_type)

    if not encr:
        ait.core.log.error(f"Unable to create encrypter with id '{encr_type}'")
        return None
    elif not encr.is_configured():
        ait.core.log.error(f"Encrypter was created but is not configured.")
        return None
    elif not encr.is_connected():
        ait.core.log.error(f"Encrypter was created but is not connected.")
        return None

    if this.debug_enabled:
        encr_cgf = encr.show_config()
        ait.core.log.info(f"Encrypter information: {encr_cgf}")

    if mode == EncryptMode.ENCRYPT:
        if this.debug_enabled:
            ait.core.log.info(f"Performing encryption...")
        ait_result = encr.encrypt(in_data)
    elif mode == EncryptMode.DECRYPT:
        if this.debug_enabled:
            ait.core.log.info(f"Performing decryption...")
        ait_result = encr.decrypt(in_data)
    else:
        ait.core.log.error(f"Unrecognized mode: {mode}")
        return None

    if ait_result is not None:
        if ait_result.has_result:
            out_data = ait_result.result
        elif ait_result.errors is not None:
            for e in ait_result.errors:
                ait.core.log.error(f"Error occurred during processing: {e}")

    encr.close()

    return out_data




if __name__ == '__main__':
  main()