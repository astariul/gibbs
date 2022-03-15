import asyncio
import uuid

import msgpack
import zmq
import zmq.asyncio
from loguru import logger

from gibbs.worker import DEFAULT_PORT


RESPONSE_BUFFER_SIZE = 4096


class Hub:
    def __init__(self, port=DEFAULT_PORT):
        super().__init__()

        self.port = port

        self.socket = None

        self.ready_workers = asyncio.Queue()
        self.responses = {}
        self.req_states = {}

    async def receive_loop(self):
        """Infinite loop for receiving responses from the workers."""
        while True:
            # Receive stuff
            address, _, resp = await self.socket.recv_multipart()
            logger.debug(f"Received something from worker #{address}")

            # Since we received a response from this worker, it means it's ready for more !
            await self.ready_workers.put(address)

            # Check if the response is a prediction or just a ready message
            if resp != b"":
                req_id, res = msgpack.unpackb(resp)
                logger.debug(f"Received response from request #{req_id}")

                # Ensure we don't store too many requests
                if len(self.responses) > RESPONSE_BUFFER_SIZE:
                    logger.warning(f"Response buffer overflow (>{RESPONSE_BUFFER_SIZE}). Forgetting oldest response")
                    # Forget the oldest one
                    self.responses.pop(list(self.responses.keys())[0])
                    self.req_states.pop(list(self.req_states.keys())[0])

                # Store the response and set the Event
                self.responses[req_id] = res
                self.req_states[req_id].set()

    async def request(self, *args, **kwargs):
        # Before anything, if the receiving loop was not started, start it
        if self.socket is None:
            # Bind the socket for further communications
            context = zmq.asyncio.Context()
            self.socket = context.socket(zmq.ROUTER)
            self.socket.bind(f"tcp://*:{self.port}")

            # Fire and forget : infinite loop, taking care of receiving stuff from the socket
            logger.info("Starting receiving loop...")
            asyncio.create_task(self.receive_loop())

        # Assign a unique ID to the request, so we know which one to wait for
        req_id = uuid.uuid4().hex

        # Create an event for this request, so we know when we receive an answer
        self.req_states[req_id] = asyncio.Event()

        # Send the request
        address = await self.ready_workers.get()
        logger.debug(f"Sending request #{req_id} to worker #{address}")
        await self.socket.send_multipart([address, b"", msgpack.packb([req_id, args, kwargs])])

        # Wait for the receiving loop to receive the response
        await self.req_states[req_id].wait()
        logger.debug(f"Accessing result for request #{req_id}")

        # Once we get it, access the result and return it
        res = self.responses.pop(req_id)

        # Don't forget to remove the event
        self.req_states.pop(req_id)

        return res
