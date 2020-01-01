#!/usr/bin/python3
"""Launch processes contained in list_processes.

Programs send messages every second, main program
receives them and print them on stdout.
After 10 seconds, main program kill everybody.


After MAX_TIME second, send msg to processes to stop
Monitor Hear Beat messages from processes
  if no Heart Beat after LOST second, restart process
"""
import subprocess
import time
import zmq

pgm_list = (u"./client1.py", u"./client2.py")
processes = []
pgm_last_heart_beat = [0.0, 0.0]  # time of last heartbeat
pgm_no_heart_beat = [0.0, 0.0]    # number of second without heartbeat
LOST = 4  # Number of seconds before we consider pgm as lost
REQUEST_TIMEOUT = 2500  # 2500 milli-second, i.e. 2.5 seconds
MAX_TIME = 50


def restart(idx):
    """Restart pgm of index idx in pgm_list.

    Args:
        idx : Index in pgm_list.

    """
    pgm_no_heart_beat[idx] = 0
    pgm_last_heart_beat[idx] = time.time()
    proc_restart = subprocess.Popen(['/usr/bin/python3', pgm_list[idx]],
                                    start_new_session=True)
    processes.append(proc_restart)


def check_and_restart():
    """Check every pgm and restart them if needed."""
    for idx, pgm in enumerate(pgm_list):
        print("pgm_no_heart_beat[%d]=%f time=%f pgm_last_heart_beat[%f]" %
              (idx, pgm_no_heart_beat[idx], time.time(),
               pgm_last_heart_beat[idx]))
        if (time.time() - pgm_last_heart_beat[idx]) > LOST:
            print("\n\n\nINFO %s IS DEAD ...\n\n\n" % pgm)
            restart(idx)


def update_last_heart_beat(msg_rcv):
    """Update pgm_last_heart_beat.

    Args:
        msg_rcv : Name of pgm which sent the heartBeat.

    """
    print("Msg received :" + msg_rcv)
    for idx, pgm in enumerate(pgm_list):
        print(" --str=%s -- p=%s-" % (msg_rcv, pgm))
        if msg_rcv == pgm:
            pgm_last_heart_beat[idx] = time.time()
            print("--pgm_no_heart_beat[%d]=%f -- pgm_last_heart_beat[%d]=%f --"
                  % (idx, pgm_no_heart_beat[idx], idx,
                     pgm_last_heart_beat[idx]))
            break


def killall_process():
    """Kill processes."""
    for proc_tokill in processes:
        proc_tokill.kill()


if __name__ == '__main__':

    # zmq init
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.bind("ipc:///tmp/hearbeat")
    socket.setsockopt_string(zmq.SUBSCRIBE, u'')

    # loop to launch processes
    for pgm_name in pgm_list:
        proc = subprocess.Popen(['/usr/bin/python3', pgm_name],
                                start_new_session=True)
        processes.append(proc)

    pgm_last_heart_beat = [time.time() for i in range(2)]

    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)

    t_start = time.time()

    while True:
        # wait for heartbeat signals / stop after MAX_TIME seconds
        if time.time() > (t_start + MAX_TIME):
            break

        socks = dict(poller.poll(REQUEST_TIMEOUT))
        if socks.get(socket) == zmq.POLLIN:
            msg = socket.recv_string()
            update_last_heart_beat(msg)
        else:
            print("\n\n\n --------TIMEOUT----------\n\n\n")
        check_and_restart()

    print("END !!!")
    killall_process()
