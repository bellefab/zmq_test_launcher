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
from threading import Thread
import zmq

pgm_list = (u"./client1.py", u"./client2.py")
processes = []
pgm_last_heart_beat = [0.0, 0.0]  # time of last heartbeat
pgm_no_heart_beat = [0.0, 0.0]    # number of second without heartbeat
LOST = 4  # Number of seconds before we consider pgm as lost
REQUEST_TIMEOUT = 2500  # 2500 milli-second, i.e. 2.5 seconds
MAX_TIME = 8

usage = "Usage :: \
   help/h : this help message.\
   list/l : list all processes planned to be launched.\
   quit/q : quit the program after killing all launched processes.\
   killall : kill all launched processes.\
   kill : kill one particular process.\
   "
shell_url = "inproc://shell"


class Shell(Thread):
    """Kind of shell for user commands."""

    def __init__(self):
        """Initialize comm with main thread."""
        Thread.__init__(self)
        self.socket_shell_cmd = context.socket(zmq.REQ)
        self.socket_shell_cmd.connect(shell_url)
        self.to_stop = False

    def stop(self):
        """Set variable to stop the shell loop."""
        self.to_stop = True

    def run(self):
        """Activate the shell loop."""
        while True:
            if self.to_stop:
                break
            cmd = input("> ")
            if cmd == "h" or cmd == "help":
                print(usage)
            elif cmd == "l" or cmd == "list":
                # send msg to get list
                # wait for answer and print
                self.socket_shell_cmd.send_string(u"list")
                msg_list = self.socket_shell_cmd.recv()
                print("list : ", msg_list)
            elif cmd == "killall":
                self.socket_shell_cmd.send_string(u"killall")
                msg_list = self.socket_shell_cmd.recv()
                print("list : ", msg_list)
            elif cmd.startwith("k ") or cmd.startwith("kill "):
                self.socket_shell_cmd.send_string(u"list")
                msg_list = self.socket_shell_cmd.recv()
                ans = input(">Choose a process to kill : ", msg_list)
                # TODO check ans is a number in the right range
                self.socket_shell_cmd.send_string("kill "+ans)
            elif cmd == "s" or cmd == "stop":
                self.socket_shell_cmd.send_string(u"stop")
            elif cmd == "q" or cmd == "quit":
                self.socket_shell_cmd.send_string(u"quit")
                print("quit")
                self.stop()
                break
            else:
                print("unknown")


def treat_shell_cmd(msg_from_shell):
    """Get msg from shell and treat it.

    Args:
        msg_from_shell : String from shell thread.

    Returns:
        a,b : a is string representing the answer to the command,
            b is a string "cont" or "stop"

    """
    if msg_from_shell == "list":
        msg_shell_list = " -- ".join(pgm_list)
        return msg_shell_list, "cont"
    elif msg_from_shell.startwith("kill "):
        num = msg_from_shell[5:]
        kill_process(int(num))
        return "OK", "cont"
    elif msg_from_shell == "killall":
        killall_process()
        return "OK", "cont"
    elif msg_from_shell == "stats":
        return "TODO", "cont"
    elif msg_from_shell == "quit":
        killall_process()
        return "OK", "stop"
    return "OK", "cont"


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


def kill_process(num):
    """Kill process number num.

    Args:
        num : .

    """
    processes[num].kill()


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

    # socket for shell_loop
    socket_shell = context.socket(zmq.REP)
    socket_shell.bind(shell_url)

    # start command loop
    shell_thread = Shell()
    shell_thread.start()

    # loop to launch processes
    for pgm_name in pgm_list:
        proc = subprocess.Popen(['/usr/bin/python3', pgm_name],
                                start_new_session=True)
        processes.append(proc)

    pgm_last_heart_beat = [time.time() for i in range(2)]

    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)
    poller.register(socket_shell, zmq.POLLIN)

    t_start = time.time()

    while True:
        # wait for heartbeat signals / stop after MAX_TIME seconds
        if time.time() > (t_start + MAX_TIME):
            break

        socks = dict(poller.poll(REQUEST_TIMEOUT))
        if socks.get(socket) == zmq.POLLIN:
            msg = socket.recv_string()
            update_last_heart_beat(msg)
        elif socks.get(socket_shell) == zmq.POLLIN:
            msg_shell = socket_shell.recv_string()
            print("Received from shell ", msg_shell)
            msg_shell_answer, cont_stop = treat_shell_cmd(msg_shell)
            socket_shell.send_string(msg_shell_answer)
            if cont_stop == "stop":
                break
        else:
            print("\n\n\n --------TIMEOUT----------\n\n\n")
        check_and_restart()

    print("END !!!")
    killall_process()
    socket_shell.close()
    socket.close()
    shell_thread.stop()
