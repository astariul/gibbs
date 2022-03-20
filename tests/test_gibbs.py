import pytest

from gibbs import Hub, Worker


class TWorker:
    def __init__(self, pos_1, pos_2, *, key_1, key_2):
        super().__init__()

        self.pos_1 = pos_1
        self.pos_2 = pos_2
        self.key_1 = key_1
        self.key_2 = key_2

    def __call__(self, pos_1, pos_2, *, key_1, key_2):
        return {
            "pos_1": self.pos_1 * pos_1,
            "pos_2": self.pos_2 * pos_2,
            "key_1": self.key_1 * key_1,
            "key_2": self.key_2 * key_2,
        }


@pytest.mark.asyncio
async def test_hub_worker_communication():
    # Just start 1 worker and 1 hub and ensure they can properly communicate.
    w = Worker(TWorker, 1, 2, key_1=3, key_2=4)
    w.start()

    h = Hub()

    res = await h.request(4, 3, key_1=2.5, key_2=5)

    assert res == {
        "pos_1": 4,
        "pos_2": 6,
        "key_1": 7.5,
        "key_2": 20,
    }

    w.terminate()
