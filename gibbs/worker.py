import uuid
from multiprocessing import Process

import msgpack
import zmq
from loguru import logger


DEFAULT_PORT = 5019


class Worker(Process):
    def __init__(self, worker_cls, *args, gibbs_host="localhost", gibbs_port=DEFAULT_PORT, **kwargs):
        super().__init__()

        self.worker_cls = worker_cls
        self.worker_args = args
        self.worker_kwargs = kwargs

        self.identity = uuid.uuid4().hex
        self.host = gibbs_host
        self.port = gibbs_port

    def run(self):
        # Instanciate the worker
        worker = self.worker_cls(*self.worker_args, **self.worker_kwargs)

        # Create the context for the socket
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt_string(zmq.IDENTITY, self.identity)

        # Connect to the Hub
        socket.connect(f"tcp://{self.host}:{self.port}")

        # Tell the Hub we are ready
        socket.send(b"")
        logger.info("Worker ready to roll")

        # Indefinitely wait for requests : when we are done with one request,
        # we wait for the next one
        while True:
            logger.debug("Waiting for request...")
            workload = socket.recv()
            req_id, req_args, req_kwargs = msgpack.unpackb(workload)
            logger.debug(f"Request #{req_id} received")

            # Call worker's code with the request arguments
            res = worker(*req_args, **req_kwargs)

            logger.debug("Sending back the response")
            socket.send(msgpack.packb([req_id, res]))
