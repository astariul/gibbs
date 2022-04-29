# Advanced

## Changing the port used by `gibbs`

By default, `gibbs` uses the port `5019` for the sockets the communicate.

You can change this port by using the argument `gibbs_port` in the Worker constructor, and the argument `port` in the Hub constructor :

```python
hub = Hub(port=6222)

w = Worker(MyModel, gibbs_port=6222)
```

## Passing arguments to model's constructor

If your model requires arguments for the constructor (like in the example given in the [Usage section](usage.md)) :

```python
class MyAwesomeModel:
    def __init__(self, wait_time=0.25):
        super().__init__()
        self.w = wait_time
```

You can just pass the arguments to the Worker (positional arguments or keyword arguments, both work) :

```python
# With positional argument
w1 = Worker(MyAwesomeModel, 0.3)

# With keyword argument
w2 = Worker(MyAwesomeModel, wait_time=0.3)
```

---

Only a small list of keywords arguments are reserved for `gibbs`. Here is the exhaustive list :

* `gibbs_host`
* `gibbs_port`
* `gibbs_heartbeat_interval`
* `gibbs_reset_after_n_miss`

## Starting workers in another machine

By default, `gibbs` workers try to connect to a Hub on the local machine (`localhost`).

But you can change this behavior, to have workers running in another machine !

To do this, simply start your worker with the appropriate host using the `gibbs_host` argument :

```python
w = Worker(MyModel, gibbs_host="192.178.0.3")
```

## Retrials & timeouts

By default, the `request()` method of the Hub will indefinitely waits for a response from the worker.

---

If instead you want to have a timeout, you can specify the timeout (in _seconds_) with the `gibbs_timeout` argument :

```python
h = Hub()
await h.request(x, gibbs_timeout=0.4)
```

If the Hub doesn't receive any response from the worker within the specified timeout, a `asyncio.TimeoutError` exception is raised.

---

You can also specify a number of retries with the argument `gibbs_retries` :

```python
h = Hub()
await h.request(x, gibbs_timeout=2, gibbs_retries=3)
```

With this code, the Hub will try to send a request. If the Hub didn't receive an answer within 2 seconds, it will retry the request again, up to 3 times.

!!! note
    You need to specify `gibbs_timeout` when using `gibbs_retries`, because there is no timeout by default !

---

You can also specify `gibbs_retries=-1` for infinite retries !

## Logging

Inside `gibbs`, the library [`loguru`](https://github.com/Delgan/loguru) is used for logging.

By default, the logger is **disabled** ([so logging functions become no-op](https://github.com/Delgan/loguru#suitable-for-scripts-and-libraries)). If you want to see what's going on inside `gibbs` (for contributing or debugging for example), you can activate it :

```python
from loguru import logger

logger.enable("gibbs")
# From here, logs will be displayed
```

---

You can also change the level of logs you want, the format, etc...

```python
from loguru import logger
import sys

logger.enable("gibbs")
logger.remove()
logger.add(sys.stderr, format="{time} {level} {message}", level="INFO")
```

!!! tip
    For more details, check out the [`loguru` library](https://github.com/Delgan/loguru) !

## Changing the heartbeat interval

By default, the heartbeat interval is set to **one second**.

You can change this value by using the argument `gibbs_heartbeat_interval` in the Worker constructor, and the argument `heartbeat_interval` in the Hub constructor :

```python
hub = Hub(heartbeat_interval=10)

w = Worker(MyModel, gibbs_heartbeat_interval=10)
```

!!! warning
    Make sure that both the Hub and the workers have the same value for the heartbeat interval, otherwise they might have synchronisation issues !
