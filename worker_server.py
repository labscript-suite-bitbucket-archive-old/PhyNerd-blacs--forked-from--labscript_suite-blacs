from zprocess import WriteQueue, ReadQueue, context, ZMQServer
import zmq
from threading import Thread, Event
import os


def to_local(path, prefix_remote):
    global prefix_local
    if path.startswith(prefix_remote):
        path = path.split(prefix_remote, 1)[1]
        path = prefix_local + path
        path = path.replace(os.path.sep, '\\')
    return path


def forward(device_name, name, forward_from, forward_to, stop_event, shared_drive=""):
    # Forward messages untill Killed
    while not stop_event.wait(0):
        try:
            success, message, results = forward_from.get(timeout=1)
            if shared_drive != "" and type(message) is tuple and len(message) > 2:
                message = list(message)
                message[1] = to_local(message[1], shared_drive)
                message = tuple(message)
            # for i, mess in enumerate(message):
            #   print(i, mess)
            forward_to.put((success, message, results))
            if not success and message == 'quit':
                break
        except Exception:
            pass


class WorkerServer(ZMQServer):
    def __init__(self, port, prefix_local='Z:\\', **kwargs):
        ZMQServer.__init__(self, port, **kwargs)
        self.workers = {}
        self.kill_threads = {}
        self.prefix_local = prefix_local

    def handler(self, message):
        action = message['action']
        name = message['name']
        device_name = message['device_name']

        if action == 'start':
            workerargs = message['workerargs']
            port_from_worker = message['port_from_worker']
            address_from_worker = message['address_from_worker']
            shared_drive_remote = message['shared_drive']

            # initialize dict for workers and Thread-kill-commands
            if device_name not in self.workers:
                self.workers[device_name] = {}
                self.kill_threads[device_name] = {}

            # Terminate old Worker before creating an new one
            if name in self.workers[device_name]:
                self.terminate_worker(device_name, name)

            # create Worker and Thread-kill-command
            print("Initializing (Device: {}, Worker: {})".format(device_name, name))
            self.workers[device_name][name] = message['WorkerClass']()
            to_worker, from_worker = self.workers[device_name][name].start(name, device_name, workerargs)
            self.kill_threads[device_name][name] = Event()

            # return forwarded ports
            return self.initialize_forwarding(device_name, name, to_worker, from_worker, port_from_worker, address_from_worker, shared_drive_remote)

        elif action == 'terminate':
            return self.terminate_worker(device_name, name)

    def initialize_forwarding(self, device_name, name, to_worker, from_worker, port, address, shared_drive_remote):
        from_extern = context.socket(zmq.PULL)
        port_from_worker_back = from_extern.bind_to_random_port('tcp://*')
        from_extern = ReadQueue(from_extern, None)
        thread_from_worker_back = Thread(target=forward, args=(device_name, name, from_extern, from_worker, self.kill_threads[device_name][name]))
        thread_from_worker_back.start()

        from_extern = context.socket(zmq.PULL)
        port_from_extern = from_extern.bind_to_random_port('tcp://*')
        from_extern = ReadQueue(from_extern, None)
        thread_to_worker = Thread(target=forward, args=(device_name, name, from_extern, to_worker, self.kill_threads[device_name][name], shared_drive_remote))
        thread_to_worker.start()

        to_extern = context.socket(zmq.PUSH)
        to_extern.connect('tcp://{}:{}'.format(address, port))
        to_extern = WriteQueue(to_extern)
        thread_from_worker = Thread(target=forward, args=(device_name, name, from_worker, to_extern, self.kill_threads[device_name][name]))
        thread_from_worker.start()

        return port_from_extern, port_from_worker_back

    def terminate_worker(self, device_name, name):
        print("Terminating (Device: {}, Worker: {})".format(device_name, name))
        # trigger Thread Kill Command
        if device_name in self.kill_threads and name in self.kill_threads[device_name]:
            self.kill_threads[device_name][name].set()

        # terminate Worker
        if device_name in self.workers and name in self.workers[device_name]:
            worker = self.workers[device_name].pop(name)
            return worker.terminate()
        return True

    def shutdown(self, signal, frame):
        # Terminate all aktive workers
        for device_name in self.workers.keys():
            for name in self.workers[device_name].keys():
                self.terminate_worker(device_name, name)

        print("\nExiting")
        sys.exit(0)


if __name__ == '__main__':
    # Start experiment server
    import socket
    import sys
    import signal
    import time
    from labscript_utils.labconfig import LabConfig

    # config
    port = 5789

    # Get Path to Shareddrive
    _config = LabConfig(required_params={'paths': ['shared_drive']})
    prefix_local = _config.get('paths', 'shared_drive')

    # Start Worker Server
    print("Starting Worker Server on IP {} Port {} to exit press CTRL + C".format(socket.gethostbyname(socket.gethostname()), port))
    worker_server = WorkerServer(port, prefix_local=prefix_local)

    # On Shutdown close all aktive workers
    signal.signal(signal.SIGINT, worker_server.shutdown)

    while True:
        # reduce CPU usage by long sleep periods
        time.sleep(10)
