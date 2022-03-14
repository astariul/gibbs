import multiprocessing as mp
import time

import requests
import uvicorn
from fastapi import FastAPI


PORT = 8000
COMPUT_TIME = 0.25
N_REQUESTS = 10


# Define a dummy model, simulating a non-negligible computation time
class MySimpleModel:
    def __init__(self, comput_time=COMPUT_TIME):
        self.comput_time = comput_time

    def __call__(self, x):
        time.sleep(self.comput_time)
        return x**2


# Instanciate the model, create the FastAPI app, declare a route
app = FastAPI()
model = MySimpleModel()


@app.get("/request")
async def simple_request(x: int):
    return {"result": model(x)}


# Define the sub-processes for this example
def app_process():
    uvicorn.run(app, host="0.0.0.0", port=PORT)


def req_process(i):
    r = requests.get(f"http://localhost:{PORT}/request?x={i}")
    assert r.status_code == 200
    return r.json()


def time_parallel_requests(n):
    with mp.Pool(n) as p:
        t0 = time.time()
        p.map(req_process, range(n))
        t1 = time.time()

    return t1 - t0


def main():
    # Start the app (in another process)
    ap = mp.Process(target=app_process)
    ap.start()

    # Make sure the server had time to start and it's working properly
    time.sleep(0.1)
    r = req_process(2)
    assert r == {"result": 4}

    # Sends parallel requests and see how long it takes
    t = time_parallel_requests(N_REQUESTS)

    ap.terminate()
    print(f"\nIt tooks {t:.3f}s to process {N_REQUESTS} requests\n")


if __name__ == "__main__":
    main()
