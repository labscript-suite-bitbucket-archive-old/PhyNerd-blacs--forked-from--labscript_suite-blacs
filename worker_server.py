from zprocess import WriteQueue, ReadQueue, context, ZMQServer
import zmq
from threading import Thread, Event


def shutdown(signal, frame):
    # Terminate all aktive workers
    for device_name in workers:
        for name in workers[device_name]:
            terminate(device_name, name)

    print("\nExiting")
    sys.exit(0)


def forward(device_name, name, forward_from, forward_to):
    # Get current Kill Comand
    stop_event = kill_threads[device_name][name]

    # Forward messages untill Killed
    while not stop_event.wait(0):
        try:
            success, message, results = forward_from.get(timeout=1)
            forward_to.put((success, message, results))
            if not success and message == 'quit':
                break
        except Exception:
            pass


def initialize_forwarding(device_name, name, to_worker, from_worker, port, address):
    from_extern = context.socket(zmq.PULL)
    port_from_worker_back = from_extern.bind_to_random_port('tcp://*')
    from_extern = ReadQueue(from_extern, None)
    thread_from_worker_back = Thread(target=forward, args=(device_name, name, from_extern, from_worker))
    thread_from_worker_back.start()

    from_extern = context.socket(zmq.PULL)
    port_from_extern = from_extern.bind_to_random_port('tcp://*')
    from_extern = ReadQueue(from_extern, None)
    thread_to_worker = Thread(target=forward, args=(device_name, name, from_extern, to_worker))
    thread_to_worker.start()

    to_extern = context.socket(zmq.PUSH)
    to_extern.connect('tcp://{}:{}'.format(address, port))
    to_extern = WriteQueue(to_extern)
    thread_from_worker = Thread(target=forward, args=(device_name, name, from_worker, to_extern))
    thread_from_worker.start()

    return port_from_extern, port_from_worker_back


def terminate(device_name, name):
    print("Terminating (Device: {}, Worker: {})".format(device_name, name))
    # trigger Thread Kill Command
    if device_name in kill_threads and name in kill_threads[device_name]:
        kill_threads[device_name][name].set()

    # terminate Worker
    if device_name in workers and name in workers[device_name]:
        worker = workers[device_name].pop(name)
        return worker.terminate()


class WorkerServer(ZMQServer):
    def handler(self, message):
        action = message['action']
        name = message['name']
        device_name = message['device_name']

        if action == 'start':
            workerargs = message['workerargs']
            port_from_worker = message['port_from_worker']
            address_from_worker = message['address_from_worker']

            # initialize dict for workers and Thread-kill-commands
            if device_name not in workers:
                workers[device_name] = {}
                kill_threads[device_name] = {}

            # Terminate old Worker before creating an new one
            if name in workers[device_name]:
                terminate(device_name, name)

            # create Worker and Thread-kill-command
            print("Initializing (Device: {}, Worker: {})".format(device_name, name))
            workers[device_name][name] = message['WorkerClass']()
            to_worker, from_worker = workers[device_name][name].start(name, device_name, workerargs)
            kill_threads[device_name][name] = Event()

            # return forwarded ports
            return initialize_forwarding(device_name, name, to_worker, from_worker, port_from_worker, address_from_worker)

        elif action == 'terminate':
            return terminate(device_name, name)


if __name__ == '__main__':
    # Start experiment server
    import socket
    import sys
    import signal
    import time

    # helper Variables
    workers = {}
    kill_threads = {}

    # On Shutdown close all aktive workers
    signal.signal(signal.SIGINT, shutdown)

    # Start Worker Server
    print("Starting Worker Server on IP {} Port {} to exit press CTRL + C".format(socket.gethostbyname(socket.gethostname()), 5789))
    worker_server = WorkerServer(5789)

    while True:
        # reduce CPU usage by long sleep periods
        time.sleep(10)
