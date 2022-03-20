import asyncio
import time

from gibbs import Hub, Worker


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


def test_del_hub_without_starting_recv_loop():
    h = Hub()
    h.__del__()
