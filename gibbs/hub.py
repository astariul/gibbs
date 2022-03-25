import asyncio
import time
import uuid

import msgpack
import zmq
import zmq.asyncio
from loguru import logger

from gibbs.worker import CODE_FAILURE, DEFAULT_PORT, HEARTBEAT_INTERVAL


RESPONSE_BUFFER_SIZE = 4096


class UserCodeException(Exception):
    def __init__(self, t):
        super().__init__(f"Exception raised in user-defined code. Traceback :\n{t}")


class Hub:
    def __init__(self, port=DEFAULT_PORT, resp_buffer_size=RESPONSE_BUFFER_SIZE):
        super().__init__()

        self.port = port
        self.resp_buffer_size = resp_buffer_size
        self.socket = None
        self.workers_c = None
        self.ready_workers = {}
        self.responses = {}
        self.req_states = {}

    async def receive_loop(self):
        """Infinite loop for receiving responses from the workers."""
        while True:
            # Receive stuff
            logger.debug("Receiving...")
            address, *frames = await self.socket.recv_multipart()
            logger.debug(f"Received something from worker #{address}")

            # Since we received a response from this worker, it means it's ready for more !
            async with self.workers_c:
                self.ready_workers[address] = time.time()
                self.workers_c.notify()

            if len(frames) == 1:
                # Answer the Ping
                logger.debug("Answering the ping")
                await self.socket.send_multipart([address, b"", b""])
                continue

            _, resp = frames
            req_id, code, res = msgpack.unpackb(resp)
            logger.debug(f"Received response from request #{req_id}")

            # Ensure we don't store too many requests
            if len(self.req_states) > self.resp_buffer_size:
                # If it's the case, forget the oldest one
                k = list(self.req_states.keys())[0]
                logger.warning(f"Response buffer overflow (>{self.resp_buffer_size}). Forgetting oldest request : {k}")
                self.req_states.pop(k)
                self.responses.pop(k, None)

            # Store the response and set the Event
            if req_id in self.req_states:
                self.responses[req_id] = (code, res)
                self.req_states[req_id].set()
            else:
                logger.warning(
                    f"Request #{req_id} was previously removed from response buffer. "
                    f"Ignoring the response from this request..."
                )

    async def request(self, *args, **kwargs):
        # Before anything, if the receiving loop was not started, start it
        if self.socket is None:
            # Create what we need here in this process/context
            context = zmq.asyncio.Context()
            self.socket = context.socket(zmq.ROUTER)
            self.socket.bind(f"tcp://*:{self.port}")
            self.workers_c = asyncio.Condition()

            # Fire and forget : infinite loop, taking care of receiving stuff from the socket
            logger.info("Starting receiving loop...")
            asyncio.create_task(self.receive_loop())

        # Assign a unique ID to the request, so we know which one to wait for
        req_id = uuid.uuid4().hex

        # Create an event for this request, so we know when we receive an answer
        self.req_states[req_id] = asyncio.Event()

        # Send the request
        address = await self._get_ready_worker()
        logger.debug(f"Sending request #{req_id} to worker #{address}")
        await self.socket.send_multipart([address, b"", msgpack.packb([req_id, args, kwargs])])

        # Wait for the receiving loop to receive the response
        await self.req_states[req_id].wait()
        logger.debug(f"Accessing result for request #{req_id}")

        # Once we get it, access the result
        code, res = self.responses.pop(req_id)

        # Don't forget to remove the event
        self.req_states.pop(req_id)

        # Depending on what is the response, deal with it properly
        if code == CODE_FAILURE:
            raise UserCodeException(res)
        else:
            return res

    async def _get_ready_worker(self):
        async with self.workers_c:
            # Iterate workers until we find one that was alive recently
            w_alive = False
            while not w_alive:
                # If no workers are available, wait...
                if not self.ready_workers:
                    await self.workers_c.wait()

                address, ts = self.ready_workers.popitem()
                w_alive = time.time() - ts < HEARTBEAT_INTERVAL

            return address

    def __del__(self):
        if self.socket is not None:
            self.socket.close()
