import asyncio
import time
import uuid

import msgpack
import zmq
import zmq.asyncio
from loguru import logger

from gibbs.worker import CODE_FAILURE, DEFAULT_HEARTBEAT_INTERVAL, DEFAULT_PORT, PONG


RESPONSE_BUFFER_SIZE = 4096


class UserCodeException(Exception):
    def __init__(self, t):
        super().__init__(f"Exception raised in user-defined code. Traceback :\n{t}")


class WorkerManager:
    def __init__(self, heartbeat_interval):
        super().__init__()

        self.heartbeat_t = heartbeat_interval

        self.w_ts = {}
        self.w_access = asyncio.Condition()

    async def reckon(self, address):
        async with self.w_access:
            self.w_ts[address] = time.time()
            self.w_access.notify()

    async def get_next_worker(self):
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


class RequestManager:
    def __init__(self, resp_buffer_size):
        super().__init__()

        self.resp_buffer_size = resp_buffer_size

        self.responses = {}
        self.req_states = {}

    def pin(self, req_id):
        self.req_states[req_id] = asyncio.Event()

        # Ensure we don't store too many requests
        if len(self.req_states) > self.resp_buffer_size:
            # If it's the case, forget the oldest one
            k = list(self.req_states.keys())[0]
            logger.warning(f"Response buffer overflow (>{self.resp_buffer_size}). Forgetting oldest request : {k}")
            self.req_states.pop(k)
            self.responses.pop(k, None)

    async def wait_for(self, req_id):
        if req_id not in self.req_states:
            raise KeyError(f"Request #{req_id} was not pinned, or was removed because of buffer overflow")

        # Wait for the receiving loop to receive the response
        await self.req_states[req_id].wait()

        # Once we get it, access the result
        code, res = self.responses.pop(req_id)

        # Don't forget to remove the event
        self.req_states.pop(req_id)

        return code, res

    def store(self, req_id, code, response):
        # Store the response if the req_id is recognized
        if req_id in self.req_states:
            self.responses[req_id] = (code, response)

            # Notify that we received the response
            self.req_states[req_id].set()
        else:
            logger.warning(
                f"Request #{req_id} was previously removed from response buffer. "
                f"Ignoring the response from this request..."
            )


class Hub:
    def __init__(
        self, port=DEFAULT_PORT, heartbeat_interval=DEFAULT_HEARTBEAT_INTERVAL, resp_buffer_size=RESPONSE_BUFFER_SIZE
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
        if self.socket is None:
            # Create what we need here in this process/context
            context = zmq.asyncio.Context()
            self.socket = context.socket(zmq.ROUTER)
            self.socket.bind(f"tcp://*:{self.port}")
            self.w_manager = WorkerManager(heartbeat_interval=self.heartbeat_t)

            # Fire and forget : infinite loop, taking care of receiving stuff from the socket
            logger.info("Starting receiving loop...")
            asyncio.create_task(self.receive_loop())

    async def request(self, *args, **kwargs):
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

    def __del__(self):
        if self.socket is not None:
            self.socket.close()
