#!/usr/bin/python3

#
# client1
#

import sys
import zmq
import time

if __name__ == "__main__":
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.connect("ipc:///tmp/hearbeat")

    while True:
        time.sleep(1)
        print("client1 SEND")
        socket.send_string(u"./client1.py")
