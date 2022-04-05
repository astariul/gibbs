import asyncio
import time
import uuid
from collections import namedtuple
from typing import Any, Tuple

import msgpack
import zmq
import zmq.asyncio
from loguru import logger

from gibbs.worker import CODE_FAILURE, DEFAULT_HEARTBEAT_INTERVAL, DEFAULT_PORT, PONG


RESPONSE_BUFFER_SIZE: int = 4096


class UserCodeException(Exception):
    """Custom Exception for user-defined catched errors.

    Args:
        t (str): Traceback returned by the worker.
    """

    def __init__(self, t: str):
        super().__init__(f"Exception raised in user-defined code. Traceback :\n{t}")


class WorkerManager:
    """A helper class that takes care of managing workers.
    Workers' address can be registered as available, and this class will make
    sure to return address of workers that are available and alive.

    A worker is considered as dead if we didn't receive any heartbeat within a
    given interval.

    Args:
        heartbeat_interval (float): Interval of time (in seconds) after which we
            consider a worker to be dead.
    """

    def __init__(self, heartbeat_interval: float):
        super().__init__()

        self.heartbeat_t = heartbeat_interval

        self.w_ts = {}
        self.w_access = asyncio.Condition()

    async def reckon(self, address: str):
        """Register the given address as available.

        Args:
            address (str): Address of the worker to register as available.
        """
        async with self.w_access:
            self.w_ts[address] = time.time()
            self.w_access.notify()

    async def get_next_worker(self) -> str:
        """Retrieve the next available and alive worker's address.

        Returns:
            str: Address of the available and alive worker.
        """
        async with self.w_access:
            # Iterate workers until we find one that was alive recently
            w_alive = False
            while not w_alive:
                # If no workers are available, wait...
                if not self.w_ts:
                    await self.w_access.wait()

                address, ts = self.w_ts.popitem()
                w_alive = time.time() - ts < self.heartbeat_t

            return address


Response = namedtuple("Response", ["code", "content"])


class RequestManager:
    """A helper class that takes care of storing responses and waiting for the
    right response.

    Args:
        resp_buffer_size (int): Maximum size of the response buffer.
    """

    def __init__(self, resp_buffer_size: int):
        super().__init__()

        self.resp_buffer_size = resp_buffer_size

        self.responses = {}
        self.req_states = {}

    def pin(self, req_id: str):
        """Pin a request ID. This is a necessary step when sending a request,
        so that the request can be awaited until a response is received.
        This method should be called for each `req_id` before calling `wait_for`.

        Args:
            req_id (str): Request unique identifier.
        """
        self.req_states[req_id] = asyncio.Event()

        # Ensure we don't store too many requests
        if len(self.req_states) > self.resp_buffer_size:
            # If it's the case, forget the oldest one
            k = list(self.req_states.keys())[0]
            logger.warning(f"Response buffer overflow (>{self.resp_buffer_size}). Forgetting oldest request : {k}")
            self.req_states.pop(k)
            self.responses.pop(k, None)

    async def wait_for(self, req_id: str) -> Tuple[int, Any]:
        """Async method that waits until we received the response corresponding
        to the given request ID.

        The method `pin` should be called before waiting with this method.

        Args:
            req_id (str): Request unique identifier.

        Raises:
            KeyError: Exception raised if the request wasn't registered previously.

        Returns:
            Tuple[int, Any]: Code and content of the received response.
        """
        if req_id not in self.req_states:
            raise KeyError(f"Request #{req_id} was not pinned, or was removed because of buffer overflow")

        # Wait for the receiving loop to receive the response
        await self.req_states[req_id].wait()

        # Once we get it, access the result
        r = self.responses.pop(req_id)

        # Don't forget to remove the event
        self.req_states.pop(req_id)

        return r.code, r.content

    def store(self, req_id: str, code: int, response: Any):
        """Store a response, to be consumed later.

        Args:
            req_id (str): Request unique identifier.
            code (int): Code of the response.
            response (Any): Content of the response.
        """
        # Store the response if the req_id is recognized
        if req_id in self.req_states:
            self.responses[req_id] = Response(code, response)

            # Notify that we received the response
            self.req_states[req_id].set()
        else:
            logger.warning(
                f"Request #{req_id} was previously removed from response buffer. "
                f"Ignoring the response from this request..."
            )


class Hub:
    """Class acting as a hub for all the requests to send. All requests sent
    through this class will be automatically dispatched to connected workers,
    will wait for the responses and return it.

    Args:
        port (int): Port number to use for the sockets. Defaults to
            DEFAULT_PORT.
        heartbeat_interval (float): Heartbeat interval used by the
            workers, in seconds. Defaults to DEFAULT_HEARTBEAT_INTERVAL.
        resp_buffer_size (int): Maximum response buffer size. Defaults
            to RESPONSE_BUFFER_SIZE.
    """

    def __init__(
        self,
        port: int = DEFAULT_PORT,
        heartbeat_interval: float = DEFAULT_HEARTBEAT_INTERVAL,
        resp_buffer_size: int = RESPONSE_BUFFER_SIZE,
    ):
        super().__init__()

        self.port = port
        self.heartbeat_t = heartbeat_interval
        self.socket = None
        self.w_manager = None
        self.req_manager = RequestManager(resp_buffer_size=resp_buffer_size)

    async def receive_loop(self):
        """Infinite loop for receiving responses from the workers."""
        while True:
            # Receive stuff
            logger.debug("Receiving...")
            address, *frames = await self.socket.recv_multipart()
            logger.debug(f"Received something from worker #{address}")

            # Since we received a response from this worker, it means it's ready for more !
            await self.w_manager.reckon(address)

            if len(frames) == 1:
                # Answer the Ping
                logger.debug("Answering the ping")
                await self.socket.send_multipart([address, b"", PONG])
                continue

            _, resp = frames
            req_id, code, res = msgpack.unpackb(resp)
            logger.debug(f"Received response from request #{req_id}")

            self.req_manager.store(req_id, code, res)

    def _start_if_not_started(self):
        """Helper method to ensure everything is properly started (socket is
        initialized, receiving loop is started, etc...).
        """
        if self.socket is None:
            # Create what we need here in this process/context
            context = zmq.asyncio.Context()
            self.socket = context.socket(zmq.ROUTER)
            self.socket.bind(f"tcp://*:{self.port}")
            self.w_manager = WorkerManager(heartbeat_interval=self.heartbeat_t)

            # Fire and forget : infinite loop, taking care of receiving stuff from the socket
            logger.info("Starting receiving loop...")
            asyncio.create_task(self.receive_loop())

    async def _request(self, *args: Any, **kwargs: Any) -> Any:
        """Raw method to send a request. This method will do the following :
         * Start the receiving loop if it was not started
         * Get the address of the next worker ready (blocking)
         * Send the request to the worker
         * Wait for the response (blocking)
         * Return the result

        Args:
            *args: Positional arguments for the request.
            **kwargs: Keywords arguments for the request.

        Raises:
            UserCodeException: Exception raised if an exception was raised inside
                user-defined code on the worker side.

        Returns:
            Any: The response for the request.
        """
        # Before anything, if the receiving loop was not started, start it
        self._start_if_not_started()

        # Assign a unique ID to the request
        req_id = uuid.uuid4().hex

        # Let the manager know that we are waiting for this request
        logger.debug(f"Pinning request #{req_id}")
        self.req_manager.pin(req_id)

        # Send the request
        address = await self.w_manager.get_next_worker()
        logger.debug(f"Sending request #{req_id} to worker #{address}")
        await self.socket.send_multipart([address, b"", msgpack.packb([req_id, args, kwargs])])

        # Wait until we receive the response
        code, res = await self.req_manager.wait_for(req_id)
        logger.debug(f"Received result for request #{req_id}")

        # Depending on what is the response, deal with it properly
        if code == CODE_FAILURE:
            raise UserCodeException(res)
        else:
            return res

    async def request(self, *args: Any, gibbs_timeout: float = None, gibbs_retries: int = 0, **kwargs: Any) -> Any:
        """Main method, used to send a request to workers and get the result.

        This method is a wrapper around `_request`, providing additional
        functionalities :
         * Timeout
         * Automatic retries

        Args:
            *args: Positional arguments for the request.
            gibbs_timeout (float): Timeout for the request, in seconds.
                If `None` is given, block until the request is complete.
                Defaults to None.
            gibbs_retries (int): Number of retries. This argument is
                used only if `gibbs_timeout` is not `None`. If `-1` is given,
                indefinitely retry. Defaults to 0.
            **kwargs: Keywords arguments for the request.

        Raises:
            asyncio.TimeoutError: Error raised if no response is received within
                the given timeout.

        Returns:
            Any: The response for the request.
        """
        try:
            return await asyncio.wait_for(self._request(*args, **kwargs), timeout=gibbs_timeout)
        except asyncio.TimeoutError:
            if gibbs_retries == 0:
                logger.error(f"Request failed : no response received within {gibbs_timeout}s")
                raise
            else:
                retries_left = max(gibbs_retries - 1, -1)
                logger.warning(
                    f"Request failed : no response received within {gibbs_timeout}s. Retrying {retries_left} times"
                )
                return await self.request(*args, gibbs_timeout=gibbs_timeout, gibbs_retries=retries_left, **kwargs)

    def __del__(self):
        if self.socket is not None:
            self.socket.close()
