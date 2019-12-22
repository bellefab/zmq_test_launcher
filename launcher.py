#!/usr/bin/python3
"""
 Launch process contained in list_processes
 Programs send messages every second, main program
 receives them and print them on stdout.
 After 10 seconds, main program kill everybody.
"""
import subprocess
import zmq
import sys
import os
import time

pgm_list = (u"./client1.py", u"./client2.py")
processes = []


def killAll_process():
    for idx in range(len(processes)):
        processes[idx].kill()


if __name__ == '__main__':

    # zmq init
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.bind("ipc:///tmp/hearbeat")
    socket.setsockopt_string(zmq.SUBSCRIBE, u'')

    # loop to launch processes
    for p in pgm_list:
        p = subprocess.Popen(['/usr/bin/python3', p], start_new_session=True)
        processes.append(p)

    # wait for heartbeat signals / stop after 10 seconds
    t_start = time.time()
    while True:
        str = socket.recv_string()
        print("Msg received : ", str)
        if time.time() > (t_start + 10):
            break

    print("END !!!")
    killAll_process()
