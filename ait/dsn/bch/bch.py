#!/usr/bin/env python
 
"""
bch.py provides a BCH (Bose, Chaudhuri, Hocquenghem) code class
 
Author: Kabir Marwah / ASU
 
"""

import ait.core.log
 
class BCH():
    """
    The BCH class is intended to provide methods and attributes to
    generate BCH code blocks and appends them to TC Transfer Frames, to produce
    a valid CLTU that can be interpreted by IRIS v2 Radio
    """
 
    def __init__(self):
        pass

    @staticmethod
    def generateBCH(input_byte_array):
        """
        Generates the BCH code blocks. Appends the error code handling
        bits to the TC Transfer Frame to enable construction of CLTUs
        :param input_byte_array: the TC Transfer Frame byte array that is
        used to generate the BCH code blocks, expected to be 7-bytes
        :return byte_array: returns full 8 byte byte-array with BCH code
        blocks appended to the end, or None if input data is invalid
        """

        if input_byte_array is None:
            ait.core.log.error("Input data for BCH is None")
            return None

        output_byte_array = '\x00\0\0\0\0\0\0\0'

        # Check that the input_byte_array is the right length (7 bytes)
        if len(input_byte_array) == 7:

            # Initialize the bch_parity_bits with seven 0s
            bch_parity_bits_past    = [0, 0, 0, 0, 0, 0, 0]
            bch_parity_bits_current = [0, 0, 0, 0, 0, 0, 0]
 
            # Convert the data bytes to bit
            #encoded_bits = BCH.toBits(input_byte_array)
            encoded_bits_str = BCH.byteArrayToBitStr(input_byte_array)

            # The full list of 64 bits to be returned once it is casted to byte array
            output_bits = []
            for i in range(64):
                output_bits.append(0)

            # Perform the logic to generate the BCH code block
            # Iterate through all 56 input bits
            for index, bit in enumerate(encoded_bits_str):
 
                # Cast the binary string value to an integer so bitwise xor can be performed
                bit_int = int(bit)
 
                # Copy the current bch parity bits into bch parity bits past list
                for i, b in enumerate(bch_parity_bits_current):
                    bch_parity_bits_past[i] = b
 
                # Perform BCH code block arithmetic
                bch_parity_bits_current[6] = (bch_parity_bits_past[6] ^ bit_int) ^ bch_parity_bits_past[5]
                bch_parity_bits_current[5] = bch_parity_bits_past[4]
                bch_parity_bits_current[4] = bch_parity_bits_past[3]
                bch_parity_bits_current[3] = bch_parity_bits_past[2]
                bch_parity_bits_current[2] = (bch_parity_bits_past[6] ^ bit_int) ^ bch_parity_bits_past[1]
                bch_parity_bits_current[1] = bch_parity_bits_past[0]
                bch_parity_bits_current[0] = bch_parity_bits_past[6] ^ bit_int
 
                # Copy the output bit integer to output_bits list that will be returned
                output_bits[index] = bit_int
 
            # Calculate the complement of bch_parity_bits_current and append to end the of output_bits
            for i in range(56, 63):
                output_bits[i] = 1 ^ bch_parity_bits_current[62 - i]
 
            # Add final bch filler bit (0)
            output_bits[63] = 0

            # Change from list of integer bits to output byte array
            output_bit_string = BCH.bitArrayToBitStr(output_bits)
            output_byte_array = BCH.bitStrToByteArray(output_bit_string)

        else:
            ait.core.log.error("Length of input data for BCH is not equal to 56 bits")
            ait.core.log.error("Length: "+  str(len(input_byte_array)*8) + " bits")
            return None

        return output_byte_array


    @staticmethod
    def bitStrToByteArray(bit_str):
        """
        Converts a bit-string to byte-array
        :param byte_array: the bit-string to be converted
        :return bit_array: the converted bit-array
        """

        intArray = [int(bit_str[x:x + 8], 2) for x in range(0, len(bit_str), 8)]
        bytearrayVal = bytearray(intArray)
        return bytearrayVal

    @staticmethod
    def bitArrayToBitStr(bit_array):
        """
        Converts a bit-array to bit-string
        :param bit_array: the bit-array to be converted
        :return bit_string: the converted bit-array as string
        """

        return ''.join(str(bit) for bit in bit_array)


    @staticmethod
    def byteArrayToBitStr(byte_array):
        """
        Converts a byte-array to bit-string
        :param byte_array: the byte-array to be converted
        :return bit_string: the converted bit-array as string
        """

        return ''.join(format(x, '08b') for x in byte_array)
