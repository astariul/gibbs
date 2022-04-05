import traceback
import uuid
from multiprocessing import Process
from typing import Any, Callable

import msgpack
import zmq
from loguru import logger


DEFAULT_PORT: int = 5019
DEFAULT_HEARTBEAT_INTERVAL: float = 1
DEFAULT_RESET_AFTER_N_MISS: int = 2
MS: int = 1000
CODE_SUCCESS: int = 0
CODE_FAILURE: int = 1
PING: bytes = b""
PONG: bytes = b""


class Worker(Process):
    """Define a worker process. This worker process indefinitely waits for
    requests on a socket. Upon receiving a request, it processes it with the
    worker class provided, and return the response.

    After creating the Worker object, you have 2 different ways to run it :
     * `worker.run()` : It will run in the current process directly (blocking,
        infinite loop).
     * `worker.start()` : It will start a different process and start the code
        there (non-blocking).

    Args:
        worker_cls (Callable): Worker class containing the code that will be used
            to process requests.
        gibbs_host (str): Host of the Hub. Defaults to "localhost".
        gibbs_port (int): Port of the Hub. Defaults to DEFAULT_PORT.
        gibbs_heartbeat_interval (float): Heartbeat interval between the
            worker and the Hub. Defaults to DEFAULT_HEARTBEAT_INTERVAL.
        gibbs_reset_after_n_miss (int): Number of missed heartbeats
            allowed before hard-resetting the socket and retrying. Defaults to
            DEFAULT_RESET_AFTER_N_MISS.
    """

    def __init__(
        self,
        worker_cls: Callable,
        *args: Any,
        gibbs_host: str = "localhost",
        gibbs_port: int = DEFAULT_PORT,
        gibbs_heartbeat_interval: float = DEFAULT_HEARTBEAT_INTERVAL,
        gibbs_reset_after_n_miss: int = DEFAULT_RESET_AFTER_N_MISS,
        **kwargs: Any,
    ):
        super().__init__()

        self.worker_cls = worker_cls
        self.worker_args = args
        self.worker_kwargs = kwargs

        self.identity = uuid.uuid4().hex
        self.host = gibbs_host
        self.port = gibbs_port
        self.heartbeat_t = gibbs_heartbeat_interval
        self.reset_n_miss = gibbs_reset_after_n_miss

        self.waiting_pong = 0

    def create_socket(self, context: zmq.Context) -> zmq.Socket:
        """Helper method to create a socket, setting its identity and connecting
        to the Hub.

        Args:
            context (zmq.Context): ZMQ context to use.

        Returns:
            zmq.Socket: Initialized and connected socket, ready to use.
        """
        # Create the socket, set its identity
        socket = context.socket(zmq.DEALER)
        socket.setsockopt_string(zmq.IDENTITY, self.identity)

        # Connect to the Hub
        socket.connect(f"tcp://{self.host}:{self.port}")

        return socket

    def ping(self, socket: zmq.Socket):
        """Helper method used for the heartbeat. Also takes care of keeping the
        counter of heartbeats up-to-date.

        Args:
            socket (zmq.Socket): Socket to use to send the heartbeat.
        """
        logger.debug("Sending ping...")
        socket.send(PING)
        self.waiting_pong += 1

    def run(self):
        """Main method. It will initialize the worker class, and enter an
        infinite loop, waiting for requests. Whenever a request is received, it
        processes it with the code provided in the constructor.
        """
        # Instanciate the worker
        worker = self.worker_cls(*self.worker_args, **self.worker_kwargs)

        # Create the socket
        context = zmq.Context()
        socket = self.create_socket(context)
        logger.info("Worker ready to roll")

        # Tell the Hub we are ready
        self.ping(socket)

        # Indefinitely wait for requests : when we are done with one request,
        # we wait for the next one
        while True:
            logger.debug("Waiting for request...")
            if socket.poll(self.heartbeat_t * MS, zmq.POLLIN):
                _, workload = socket.recv_multipart(zmq.NOBLOCK)
                logger.debug("Received something !")
                self.waiting_pong = 0
            else:
                logger.debug(f"Didn't receive anything for {self.heartbeat_t}s ({self.waiting_pong})")

                if self.waiting_pong >= self.reset_n_miss:
                    logger.warning(
                        f"The Hub is not answering, even after {self.waiting_pong} missed pings... "
                        f"Resetting the socket"
                    )
                    socket.close(linger=0)
                    socket = self.create_socket(context)
                    self.waiting_pong = 0

                # We didn't receive anything for some time, try to ping again
                self.ping(socket)
                continue

            if workload == PONG:
                # Just a Pong, ignore it
                logger.debug("It was just a pong...")
                continue

            # From here the Hub sent us an actual request
            req_id, req_args, req_kwargs = msgpack.unpackb(workload)
            logger.debug(f"Request #{req_id} received")

            # Call worker's code with the request arguments
            try:
                res = worker(*req_args, **req_kwargs)
            except Exception as e:
                logger.warning(f"Exception in user-defined __call__ method : {e.__class__.__name__}({str(e)})")
                socket.send_multipart([b"", msgpack.packb([req_id, CODE_FAILURE, traceback.format_exc()])])
            else:
                logger.debug("Sending back the response")
                socket.send_multipart([b"", msgpack.packb([req_id, CODE_SUCCESS, res])])
