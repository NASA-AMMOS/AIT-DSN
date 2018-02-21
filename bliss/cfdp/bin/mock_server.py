#!/usr/bin/env python
# Mock incoming PDUs

import gevent
import gevent.server
import socket

def handle(sock, address):
    count = 0
    while True:
        sock.send('Hello {}'.format(count))
        count += 1
        gevent.sleep(2)

if __name__ == '__main__':
    server = gevent.server.StreamServer(('127.0.0.1', 8000), handle)
    server.serve_forever()