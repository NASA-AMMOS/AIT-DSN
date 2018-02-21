import os

def calc_file_size(filepath):
    statinfo = os.stat(filepath)
    return statinfo.st_size