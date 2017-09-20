import binascii

def hexint(b):
    return int(binascii.hexlify(b), 16)
