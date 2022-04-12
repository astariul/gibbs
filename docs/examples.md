# Examples

All examples are located in the `examples/` folder.

All examples can be run directly without any arguments. You can experiment new settings by changing the constants inside the scripts.

!!! important
    Some examples require additional dependencies. You can install these dependencies with `pip install gibbs[ex]` (see [Installation](index.md#extra-dependencies))

## vanilla_fastapi.py

```bash
python examples/vanilla_fastapi.py
```

This example simply creates a FastAPI application with a dummy model.  
The dummy model simulate some computations time.

The script will measure the time needed to send and receive 10 requests.

## gibbs_fastapi.py

```bash
python examples/gibbs_fastapi.py
```

This example is the same as [`vanilla_fastapi.py`](#vanilla_fastapipy), but it uses `gibbs` to scale up the dummy model (with 2 workers).

The script will also measure the time needed to send and receive 10 requests, so you can compare the results with the vanilla approach.

## transformer.py

```bash
python examples/transformer.py
```

A more "real-life" application, where we use a BART model (from `transformers` library) along with `gibbs` for scaling up text-summarization.
