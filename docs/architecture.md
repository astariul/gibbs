# Architecture

!!! warning
    This page contains advanced technical details about `gibbs`. You can probably skip it if you just want to use the library.

## Tooling

`gibbs` relies on the `zmq` library for communication between the hub and the workers.

`zmq` is a low-level networking library, providing us with TCP sockets. This gives us performances, and the ability to have workers on different machines.

## Pattern

`gibbs` implement a modified version of the ***Paranoid Pirate Pattern***.

You can read more about the Paranoid Pirate Pattern in the [zmq guide](https://zguide.zeromq.org/docs/chapter4/#Robust-Reliable-Queuing-Paranoid-Pirate-Pattern). But basically :

* It is a **reliable** pattern (it can handle failures)
* It relies on the *REQUEST - REPLY* sockets (and their asynchronous equivalent : *ROUTER - DEALER*)
* It automatically balance requests across workers as they come

---

Here is a schema for the Paranoid Pirate Pattern implemented in `gibbs` :

![](img/gibbs_base.png)

!!! tip
    As you can see the the original Paranoid Pirate Pattern is slightly modified : the clients and the queue are merged into a single component, called "Hub".

---

Let's see how these components interact with each other to deal with parallel requests :

![](img/gibbs_parallel.png)

The Hub simply keeps a list of workers that are ready, and send incoming requests to one of the ready worker.

Each worker deal with the request it receives. So with two workers, we can deal with two requests in parallel, as shown in the figure above.

When receiving the response from the worker, the Hub marks it as ready again.


## Heartbeat

In the [zmq guide](https://zguide.zeromq.org/docs/chapter4/#Heartbeating-for-Paranoid-Pirate), the Paranoid Pirate Pattern implements a _One-way heartbeat_.

In `gibbs` though, the heartbeat is implemented as a _Ping-pong heartbeat_.

!!! question
    Heartbeat is necessary to have _robustness_, in case of workers or Hub crash.

---

Here is how heartbeat works :

![](img/gibbs_heartbeat.png)

The workers always initiate the heartbeat (_ping_), and the hub answer it (_pong_).

If the worker keeps sending pings but does not receive pongs, we know the Hub is dead. In this case the worker will try to reconnect his socket. So when the Hub is restarted, the worker will automatically reconnect.

If the Hub didn't receive a heartbeat from some time, we know this worker is dead. In this case the worker is removed from the list of workers ready, so no requests are sent to this worker.

!!! warning
    There is a small time interval where a worker can die and the Hub still thinks it's alive. If a request is sent in this interval, the request will fail. To solve this, you can check the [section about automatic retrials](advanced.md#retrials-timeouts).
