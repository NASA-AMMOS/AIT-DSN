

import struct
import socket
import time

from ait.dsn.proc.deframe_packet_processor import ModuloList

def test_modulus_list():
    size = 10
    ml = ModuloList(size)
    print("alphaVal: "+str(ml._alpha_value))
    print("betaVal:  "+str(ml._beta_value))



    value_list = [ 0, 1, 2, 4, 5, 6, 7, 8, 9, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0, 1, 7, 9, 1, 5]
    for value in value_list:
        ml.add_value(value)
        print("ModList contents after adding "+str(value)+": ")
        print("alpha: "+str(ml._alpha_list))
        print("beta:  "+str(ml._beta_list))

        if value % 2:
            to_remove = ml.get_next_value()
            if to_remove is not None:
                ml.remove_value(to_remove)
                print("ModList contents after removing " + str(to_remove) + ": ")
                print("alpha: " + str(ml._alpha_list))
                print("beta:  " + str(ml._beta_list))

        #time.sleep(2)

if __name__ == '__main__':
    test_modulus_list()