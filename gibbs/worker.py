import uuid
from multiprocessing import Process

import msgpack
import zmq
from loguru import logger

from gibbs import DEFAULT_PORT


class Worker(Process):
    def __init__(self, host="localhost", port=DEFAULT_PORT):
        super().__init__(daemon=True)

        self.identity = uuid.uuid4().hex
        self.host = host
        self.port = port

        context = zmq.Context()
        self.socket = context.socket(zmq.REQ)
        self.socket.setsockopt_string(zmq.IDENTITY, self.identity)

    def __call__(self, *args, **kwargs):
        raise NotImplementedError("Missing implementation for `__call__` method, please overwrite it")

    def run(self):
        # Connect to the Hub
        self.socket.connect(f"tcp://{self.host}:{self.port}")

        # Tell the Hub we are ready
        self.socket.send(b"")
        logger.info("Worker ready to roll")

        # Indefinitely wait for requests : when we are done with one request,
        # we wait for the next one
        while True:
            logger.debug("Waiting for request...")
            workload = self.socket.recv()
            req_id, req_args, req_kwargs = msgpack.unpackb(workload)
            logger.debug(f"Request #{req_id} received")

            # Call user's code with the request arguments
            res = self(*req_args, **req_kwargs)

            logger.debug("Sending back the response")
            self.socket.send(msgpack.packb([req_id, res]))
