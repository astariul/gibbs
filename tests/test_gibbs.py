import asyncio
import time
from collections import Counter

import pytest

from gibbs import Hub, UserCodeException, Worker


COMPUTATION_TIME = 0.1


class TWorker:
    def __init__(self, pos_1, pos_2, *, key_1, key_2, wait=False):
        super().__init__()

        self.pos_1 = pos_1
        self.pos_2 = pos_2
        self.key_1 = key_1
        self.key_2 = key_2
        self.wait = wait

    def __call__(self, pos_1, pos_2, *, key_1, key_2):
        if self.wait:
            time.sleep(COMPUTATION_TIME)

        return {
            "pos_1": self.pos_1 * pos_1,
            "pos_2": self.pos_2 * pos_2,
            "key_1": self.key_1 * key_1,
            "key_2": self.key_2 * key_2,
        }


async def test_hub_worker_communication(unused_tcp_port):
    # Just start 1 worker and 1 hub and ensure they can properly communicate
    w = Worker(TWorker, 1, 2, key_1=3, key_2=4, gibbs_port=unused_tcp_port)
    w.start()

    h = Hub(port=unused_tcp_port)

    res = await h.request(4, 3, key_1=2.5, key_2=5)

    assert res == {
        "pos_1": 4,
        "pos_2": 6,
        "key_1": 7.5,
        "key_2": 20,
    }

    w.terminate()


async def test_parallel_worker(unused_tcp_port):
    # Start 2 worker and ensure they compute in parallel
    workers = [Worker(TWorker, 1, 2, key_1=3, key_2=4, wait=True, gibbs_port=unused_tcp_port) for _ in range(2)]
    for w in workers:
        w.start()

    h = Hub(port=unused_tcp_port)

    # The first request is slower because we have to start the receiving loop
    res = await h.request(4, 3, key_1=2.5, key_2=5)

    # Time concurrent request
    t0 = time.time()
    res = await asyncio.gather(h.request(4, 3, key_1=2.5, key_2=5), h.request(3, 4, key_1=6, key_2=6))
    t1 = time.time()

    # Each task takes 0.1s, but they run concurrently, so they take less than their sequential sum
    assert t1 - t0 < 0.2
    assert res[0] == {
        "pos_1": 4,
        "pos_2": 6,
        "key_1": 7.5,
        "key_2": 20,
    }
    assert res[1] == {
        "pos_1": 3,
        "pos_2": 8,
        "key_1": 18,
        "key_2": 24,
    }

    for w in workers:
        w.terminate()


async def test_del_hub_with_recv_loop():
    h = Hub()
    t = asyncio.create_task(h.request(3))
    h.__del__()
    t.cancel()


def test_del_hub_without_starting_recv_loop():
    h = Hub()
    h.__del__()


class TWorkerSlow:
    def __call__(self, x):
        time.sleep(0.1)
        return x**2


async def test_overload_response_buffer_fast(unused_tcp_port):
    # Starts 3 workers
    workers = [Worker(TWorkerSlow, gibbs_port=unused_tcp_port) for _ in range(3)]
    for w in workers:
        w.start()

    # Set the buffer size to 2 so the third request will erase the first one
    h = Hub(port=unused_tcp_port, resp_buffer_size=2)

    # Fire 3 requests
    reqs = await asyncio.gather(*[asyncio.create_task(h.request(i)) for i in range(3)], return_exceptions=True)

    # The third request erases the first on in the Hub, before we can even send
    # it to the worker. So when we wait for the response, the request ID is unknown
    assert isinstance(reqs[0], KeyError)
    assert reqs[1] == 1
    assert reqs[2] == 4

    for w in workers:
        w.terminate()


async def test_overload_response_buffer_slow(unused_tcp_port):
    # Starts 3 workers
    workers = [Worker(TWorkerSlow, gibbs_port=unused_tcp_port) for _ in range(3)]
    for w in workers:
        w.start()

    # Set the buffer size to 2 so the third request will erase the first one
    h = Hub(port=unused_tcp_port, resp_buffer_size=2)

    # Send a request to make sure the worker is fine
    res = await h.request(3)
    assert res == 9

    # Fire 1 request, then 2 requests
    t = [asyncio.create_task(h.request(0))]
    await asyncio.sleep(0.01)
    t.append(asyncio.create_task(h.request(1)))
    t.append(asyncio.create_task(h.request(2)))

    # After sending the first request, the task is waiting for the result
    # But meanwhile, the response buffer was erased because of other incoming requests
    # So the first task is indefinitely waiting...
    done, pending = await asyncio.wait(t, timeout=0.3)
    assert t[0] in pending
    assert t[1] in done
    assert t[2] in done

    for w in workers:
        w.terminate()


class TWorkerCrash:
    def __init__(self, in_init=False, in_call=False):
        super().__init__()

        if in_init:
            raise ValueError("Simulated crash in __init__()")
        self.in_call = in_call

    def __call__(self, x):
        if self.in_call:
            raise ValueError("Simulated crash in __call__()")
        return x**2


def test_user_defined_code_crash_in_init():
    # If something crash in init, nothing to do, just let the worker crash
    w = Worker(TWorkerCrash, in_init=True)
    with pytest.raises(ValueError):
        w.run()


async def test_user_defined_code_crash_in_call(unused_tcp_port):
    w = Worker(TWorkerCrash, in_call=True, gibbs_port=unused_tcp_port)
    w.start()

    h = Hub(port=unused_tcp_port)

    with pytest.raises(UserCodeException):
        await h.request(4)

    w.terminate()


class TWorkerId:
    def __init__(self, i):
        super().__init__()

        self.i = i

    def __call__(self, x):
        time.sleep(0.1)
        return x * self.i


async def test_workers_roll(unused_tcp_port):
    workers = [Worker(TWorkerId, i=i + 1, gibbs_port=unused_tcp_port) for i in range(2)]
    for w in workers:
        w.start()

    h = Hub(port=unused_tcp_port)

    # 4 requests : 2 should go to worker #1, 2 should go to worker #2
    res = await asyncio.gather(h.request(1), h.request(1), h.request(1), h.request(1))

    c = Counter(res)
    assert c[1] == 2 and c[2] == 2

    for w in workers:
        w.terminate()


async def test_worker_crash_but_next_request_is_correctly_send_to_alive_worker(unused_tcp_port):
    workers = [Worker(TWorkerId, i=i + 1, gibbs_port=unused_tcp_port, gibbs_heartbeat_interval=0.1) for i in range(2)]
    for w in workers:
        w.start()

    h = Hub(port=unused_tcp_port, heartbeat_interval=0.1)

    # Send requests to make sure both workers are working fine
    res = await asyncio.gather(h.request(1), h.request(1))
    assert 1 in res and 2 in res

    # Simulate a crash in one of the worker
    workers[0].terminate()

    # Wait a bit : without heartbeat, the hub knows this worker is dead
    await asyncio.sleep(0.15)

    # Send requests again : both requests are processed by the left alive worker
    res = await asyncio.gather(h.request(1), h.request(1))
    assert res == [2, 2]

    workers[1].terminate()


class TWorkerFast:
    def __call__(self, x):
        return x**2


async def test_worker_crash_and_can_reconnect_without_problem(unused_tcp_port):
    w = Worker(TWorkerFast, gibbs_port=unused_tcp_port, gibbs_heartbeat_interval=0.1)
    w.start()

    h = Hub(port=unused_tcp_port, heartbeat_interval=0.1)

    # Send a request to make sure the worker is fine
    res = await h.request(4)
    assert res == 16

    # Simulate a worker crash
    w.kill()

    # Wait a bit : without heartbeat, the hub knows this worker is dead
    await asyncio.sleep(0.15)

    # Fire a request : no one will answer it because there is no worker
    req = asyncio.create_task(h.request(3))
    done, pending = await asyncio.wait([req], timeout=0.1)
    assert req in pending

    # Restart a worker
    w = Worker(TWorkerFast, gibbs_port=unused_tcp_port)
    w.start()

    # Since we have a worker, the request was processed
    done, pending = await asyncio.wait([req], timeout=0.15)
    assert req in done

    w.terminate()


async def test_hub_crash_but_worker_automatically_reconnect(unused_tcp_port):
    w = Worker(TWorkerFast, gibbs_port=unused_tcp_port, gibbs_heartbeat_interval=0.1, gibbs_reset_after_n_miss=1)
    w.start()

    h = Hub(port=unused_tcp_port, heartbeat_interval=0.1)

    # Send a request to make sure the worker is fine
    res = await h.request(3)
    assert res == 9

    # Simulate a hub crash
    h.__del__()

    # Wait a bit : without heartbeat response, the worker will know the hub is dead
    await asyncio.sleep(0.2)

    # Recreate a brand new hub, the worker will automatically try to reconnect
    h2 = Hub(port=unused_tcp_port, heartbeat_interval=0.1)

    # Send a request to make sure the worker is fine
    res = await h2.request(5)
    assert res == 25

    w.terminate()


async def test_request_timeout(unused_tcp_port):
    # Start a Hub without workers, so the request will timeout
    h = Hub(port=unused_tcp_port)

    # Sending a request with a timeout will lead to TimeoutError
    with pytest.raises(asyncio.TimeoutError):
        await h.request(2, gibbs_timeout=0.1)


async def test_worker_crash_but_request_is_automatically_retried(unused_tcp_port):
    workers = [Worker(TWorkerId, i=i + 1, gibbs_port=unused_tcp_port) for i in range(2)]
    for w in workers:
        w.start()

    h = Hub(port=unused_tcp_port)

    # Send requests to make sure both workers are working fine
    res = await asyncio.gather(h.request(1), h.request(1))
    assert 1 in res and 2 in res

    # Simulate a crash in one of the worker
    workers[0].kill()

    # Send another request directly after the crash
    # The Hub received a heartbeat recently so he thinks the worker is alive
    # But we set retries to 1, so the Hub will retry until a worker alive process it
    res = await asyncio.gather(*[h.request(1, gibbs_timeout=0.2, gibbs_retries=1) for _ in range(2)])

    # Both requests are processed by the left alive worker
    assert res == [2, 2]

    workers[1].terminate()


async def test_request_infinite_retry(unused_tcp_port):
    # Start a Hub without workers, so the request will timeout
    h = Hub(port=unused_tcp_port)

    # Fire a request with a short timeout
    # No one will answer but we keep retrying indefinitely
    req = asyncio.create_task(h.request(3, gibbs_timeout=0.05, gibbs_retries=-1))
    done, pending = await asyncio.wait([req], timeout=0.1)
    assert req in pending

    # Start a worker
    w = Worker(TWorkerFast, gibbs_port=unused_tcp_port)
    w.start()

    # Since we have a worker, the request was processed
    done, pending = await asyncio.wait([req], timeout=0.2)
    assert req in done

    w.terminate()
