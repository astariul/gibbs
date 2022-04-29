# Usage

Let's walk-through an example of how to scale a FastAPI application together !

!!! note
    Here we use FastAPI to show how easy it is to integrate `gibbs` in an asynchronous framework, but `gibbs` can be used like any asynchronous python code !

## Initial application

Let's take a simple example to see how we can scale with `gibbs`.

---

Say we have developed a great ML model. For the simplicity of this example, here is the code of a dummy model :

```python
import time


class MyAwesomeModel:
    def __init__(self, wait_time=0.25):
        super().__init__()
        self.w = wait_time

    def __call__(self, x):
        time.sleep(self.w)
        return x**2
```

This model simply return the squared input, after simulating a certain processing time.

---

Now, having a model is great, but we want to make it available to our users. To do that, we create an API using FastAPI, serving that model. Here is the code :

```python
import time

import uvicorn
from fastapi import FastAPI


class MyAwesomeModel:
    def __init__(self, wait_time=0.25):
        super().__init__()
        self.w = wait_time

    def __call__(self, x):
        time.sleep(self.w)
        return x**2


# Instanciate FastAPI app and instanciate our model
app = FastAPI()
model = MyAwesomeModel()


# Define a route that will call our model and return the result
@app.get("/request")
async def simple_request(x: int):
    return {"result": model(x)}


if __name__=="__main__":
    # Run the app
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

You can run this python script and access [http://localhost:8000/docs](http://localhost:8000/docs) to try the route by yourself.

Great ! We are serving our awesome model !

## The scaling issue

This code is great, but it does not scale.

Because our model takes `250ms` to deal with every request, you can imagine what happen when 10 clients send one request at the same time... One of the client will have to wait `2.5s` before receiving a response !

You can try this out by starting our simple app, and in another terminal, run the following script :

```python
import multiprocessing as mp
import time

import requests


def req_process(i):
    r = requests.get(f"http://localhost:8000/request?x={i}")
    assert r.status_code == 200
    return r.json()


def time_parallel_requests(n):
    with mp.Pool(n) as p:
        t0 = time.time()
        p.map(req_process, range(n))
        t1 = time.time()

    return t1 - t0


if __name__ == "__main__":
    t = time_parallel_requests(10)
    print(f"It tooks {t:.3f}s to process 10 requests")
```

This script simply run 10 requests in parallel and print the time necessary to complete all of them. And as expected :

> It tooks 2.532s to process 10 requests

## How `gibbs` works

What we want is simply to have pool of several models, and when one model is busy dealing with a request, instead of waiting for it to finish, we want to call another (idle) model.

So we can deal with several requests in parallel, and therefore serve several clients with a low latency !

---

To achieve this, `gibbs` introduces 2 classes :

* `Hub`
* `Worker`

The `Worker` class is just a process, dealing with requests sequentially by calling the awesome model you created.

The `Hub` is the class that orchestrate the requests, sending each request to the right worker (currently idle).

!!! hint
    You can see a more detailed description of how this work in [Architecture](architecture.md)

## Use `gibbs` to scale up

Let's see how to modify our simple app to scale up.

We simply have to create a `Hub` and use it to send requests, and start a few workers with our awesome model !

```python hl_lines="6 21 27 31 32 33 34"
import time

import uvicorn
from fastapi import FastAPI

from gibbs import Hub, Worker


class MyAwesomeModel:
    def __init__(self, wait_time=0.25):
        super().__init__()
        self.w = wait_time

    def __call__(self, x):
        time.sleep(self.w)
        return x**2


# Instanciate FastAPI app and instanciate the Hub
app = FastAPI()
hub = Hub()


# Define a route that will call our model and return the result
@app.get("/request")
async def simple_request(x: int):
    return {"result": await hub.request(x)}


if __name__=="__main__":
    # Start the workers (in another process)
    workers = [Worker(MyAwesomeModel) for _ in range(4)]
    for w in workers:
        w.start()

    # Run the app
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

Quite simple, right ?

---

Now, if we use the same script as before to run 10 requests in parallel in another terminal :

> It tooks 0.855s to process 10 requests

The time needed to deal with 10 requests is greatly reduced, by sharing the work between the 4 workers !
