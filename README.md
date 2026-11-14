<h1 align="center">pintel</h1>
<p align="center">
Scale your ML workers asynchronously across processes and machines
</p>

<p align="center">
    <a href="https://github.com/astariul/pintel/releases"><img src="https://img.shields.io/github/release/astariul/pintel.svg" alt="GitHub release" /></a>
    <a href="https://github.com/astariul/pintel/actions/workflows/pytest.yaml"><img src="https://github.com/astariul/pintel/actions/workflows/pytest.yaml/badge.svg" alt="Test status" /></a>
    <a href="https://github.com/astariul/pintel/actions/workflows/lint.yaml"><img src="https://github.com/astariul/pintel/actions/workflows/lint.yaml/badge.svg" alt="Lint status" /></a>
    <img src=".github/badges/coverage.svg" alt="Coverage status" />
    <a href="https://astariul.github.io/pintel"><img src="https://img.shields.io/website?down_message=failing&label=docs&up_color=green&up_message=passing&url=https%3A%2F%2Fastariul.github.io%2Fpintel" alt="Docs" /></a>
    <a href="https://github.com/astariul/pintel/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="licence" /></a>
</p>

<p align="center">
  <a href="#description">Description</a> •
  <a href="#install">Install</a> •
  <a href="#usage">Usage</a> •
  <a href="#faq">FAQ</a> •
  <a href="#contribute">Contribute</a>
  <br>
  <a href="https://astariul.github.io/pintel/" target="_blank">Documentation</a>
</p>


<h2 align="center">Description</h2>

**`pintel`** is a python package that helps you scale your ML workers (or any python code) across processes and machines, asynchronously.

`pintel` is :

* ⚡️ Highly performant
* 🔀 Asynchronous
* 🐥 Easy-to-use


<h2 align="center">Install</h2>

Install `pintel` by running :


```
pip install pintel
```


<h2 align="center">Usage</h2>

After defining your awesome model :

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

You can simply start a few workers serving the model :

```python
from pintel import Worker

for _ in range(4):
    Worker(MyAwesomeModel).start()
```

And send requests through the Hub :

```python
from pintel import Hub

hub = Hub()

# In an async function
await hub.request(34)
```

And that's it !

---

Make sure to check the [documentation](https://astariul.github.io/pintel/usage/) for a more detailed explanation.

Or you can run some examples from the `examples/` folder.


<h2 align="center">FAQ</h2>

#### ❓ **How `pintel` works ?**

`pintel` simply run your model code in separate processes, and send requests to the right process to ensure requests are treated in parallel.

`pintel` uses a modified form of [the Paranoid Pirate Pattern from the zmq guide](https://zguide.zeromq.org/docs/chapter4/#Robust-Reliable-Queuing-Paranoid-Pirate-Pattern).

#### ❓ **Why the name "pintel" ?**

Pintel is one of the pirates of Captain Barbossa's crew on the Black Pearl.  
Since we are using the Paranoid Pirate Pattern, we needed a pirate name !

<h2 align="center">Contribute</h2>

To contribute, install the package locally, create your own branch, add your code (and tests, and documentation), and open a PR !

### Pre-commit hooks

Pre-commit hooks are set to check the code added whenever you commit something.

If you never ran the hooks before, install it with :

```bash
pre-commit install
```

---

Then you can just try to commit your code. If you code does not meet the quality required by linters, it will not be committed. You can just fix your code and try to commit again !

---

You can manually run the pre-commit hooks with :

```bash
pre-commit run --all-files
```

### Tests

When you contribute, you need to make sure all the unit-tests pass. You should also add tests if necessary !

You can run the tests with :

```bash
pytest
```

---

Pre-commit hooks will not run the tests, but it will automatically update the coverage badge !

### Documentation

The documentation should be kept up-to-date. You can visualize the documentation locally by running :

```bash
mkdocs serve
```
