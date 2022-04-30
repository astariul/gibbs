# Gibbs

## Introduction

Welcome to the documentation of the `gibbs` package.

`gibbs` is a package that help you scale your ML workers (or any python code) across processes and machines, asynchronously.

---

`gibbs` is :

* ⚡️ Highly performant
* 🔀 Asynchronous
* 🐥 Easy-to-use

## Installation

### Latest version

You can install the latest stable version of the package directly from PyPi with :

```bash
pip install gibbs
```

### Bleeding-edge version

To install the bleeding-edge version (`main`, not released), you can do :

```bash
pip install git+https://github.com/astariul/gibbs.git
```

### Local version

For development purposes, you can clone the repository locally and install it manually :

```bash
git clone https://github.com/astariul/gibbs.git
cd gibbs
pip install -e .
```

### Extra dependencies

You can also install extras dependencies, for example :

```bash
pip install gibbs[docs]
```

Will install necessary dependencies for building the docs.

---

List of extra dependencies :

* **`test`** : Dependencies for running unit-tests.
* **`hook`** : Dependencies for running pre-commit hooks.
* **`lint`** : Dependencies for running linters and formatters.
* **`docs`** : Dependencies for building the documentation.
* **`ex`** : Dependencies for running the examples.
* **`dev`** : `test` + `hook` + `lint` + `docs`.
* **`all`** : All extra dependencies.

## Contribute

To contribute, install the package locally (see [Installation](#local-version)), create your own branch, add your code (and tests, and documentation), and open a PR !

### Pre-commit hooks

Pre-commit hooks are set to check the code added whenever you commit something.

When you try to commit your code, hooks are automatically run, and if you code does not meet the quality required by linters, it will not be committed. You then have to fix your code and try to commit again !

!!! important
    If you never ran the hooks before, install it with :
    ```bash
    pre-commit install
    ```

!!! info
    You can manually run the pre-commit hooks with :
    ```bash
    pre-commit run --all-files
    ```

### Unit-tests

When you contribute, you need to make sure all the unit-tests pass. You should also add tests if necessary !

You can run the tests with :

```bash
pytest
```

!!! info
    Pre-commit hooks will not run the tests, but it will automatically update the coverage badge !

### Documentation

When you contribute, make sure to keep the documentation up-to-date.

You can visualize the documentation locally by running :

```bash
mkdocs serve
```
