# pytest-automock
[![Travis status for master branch](https://travis-ci.com/pohmelie/pytest-automock.svg?branch=master)](https://travis-ci.com/pohmelie/pytest-automock)
[![Codecov coverage for master branch](https://codecov.io/gh/pohmelie/pytest-automock/branch/master/graph/badge.svg)](https://codecov.io/gh/pohmelie/pytest-automock)
[![Pypi version](https://img.shields.io/pypi/v/pytest-automock.svg)](https://pypi.org/project/pytest-automock/)
[![Pypi downloads count](https://img.shields.io/pypi/dm/pytest-automock)](https://pypi.org/project/pytest-automock/)

# Reason
* No generic automock solution

# Features
* Pytest plugin
* Autogenerate/autouse mocks for functions and objects
* Sync and async support
* Locked mode to be sure mocked objects stay untouched
* Black and white lists for attributes
* Customizable serialization

# Limitaions
* No support for dunder methods (can be partly solved in future)
* No support for sync/async generators/contexts
* Races will break tests, since order counts

# License
`pytest-automock` is offered under MIT license.

# Requirements
* python 3.6+

# Usage
Lets say you have some module `mymod.py`:
``` python
import time

class Network:
    def get_data_from_network(self, x, y):
        time.sleep(1)
        return x + y

    def send_data_to_network(self, value):
        time.sleep(1)

def logic(x):
    n = Network()
    a, b = 0, 1
    while b < x:
        c = n.get_data_from_network(a, b)
        a, b = b, c
        n.send_data_to_network("ok")
    return b
```
And you want to create mocks for your `Network` class (since testing time and sane counts), but you are too lazy to write them... `conftest.py`:
``` python
import pytest
import mymod

@pytest.fixture(autouse=True)
def _mocks(automock):
    with automock((mymod, "Network")):
        yield
```
`test_logic.py`:
``` python
from mymod import logic

def test_logic():
    assert logic(7) == 8
    assert logic(10) == 13
```
If you run `pytest` on this setup, then you will see fail:
``` bash
$ pytest -x
...
E           RuntimeError: Mock is locked, but '__init__' wanted
```
`automock` can work in two modes: locked and unlocked. Locked mode is default, real methods calls of mocked objects are
not allowed in this mode. So, above error says that we can't call `__init__` of our `Network`.
In locked mode there is no mock-files update also.

To allow real calls and mocks generation `automock` provides extra cli argument to `pytest`: `--automock-unlocked`
``` bash
$ pytest -x --automock-unlocked
...
test_logic.py .
...
1 passed in 22.09s
```
After that you can see that `tests/mocks/test_logic/mymod/Network` file was created. This is mock for your test sequence.
Now you can rerun tests and see what happens (you can omit `--automock-unlocked` key for ensurance, that real object
will not be touched (actually even created)).
``` bash
$ pytest -x
...
test_logic.py .
...
1 passed in 0.04s
```
# API
## `automock` (fixture)
`automock` fixture is a **context manager**
```python
def automock(*pairs,
             storage: Union[str, Path] = "tests/mocks",
             override_name: Optional[str] = None,
             unlocked: Optional[bool] = None,
             allowed_methods: Optional[Sequence[str]] = None,
             forbidden_methods: Optional[Sequence[str]] = None,
             encode: Callable[[Any], bytes] = pickle.dumps,
             decode: Callable[[bytes], Any] = pickle.loads)
```
* `*pairs`: pair/tuple of object/module and attribute name (`str`)
* `storage`: root path for storing mocks
* `override_name`: forced mock-file name
* `unlocked`: mode selector (if omited, selected by `--automock-unlocked`)
* `allowed_methods`: sequence of **allowed to mock** attributes
* `forbidden_methods`: sequnce of **forbidden to mock** attributes
* `encode`: encode routine
* `decode`: decode routine

## `automock_unlocked` (fixture)
Fixture with default mode from cli parameter (`bool`).

## `automock` (function)
`automock` function is not supposed to be used by anyone but `automock` fixture
``` python
def automock(factory: Callable, *,
             memory: Dict,
             locked: bool = True,
             allowed_methods: Optional[Sequence[str]] = None,
             forbidden_methods: Optional[Sequence[str]] = None)
```
* `factory`: object/function to wrap
* `memory`: dicrionary to get/put mocks
* `locked`: mode selector
* `allowed_methods`: sequence of **allowed to mock** attributes
* `forbidden_methods`: sequnce of **forbidden to mock** attributes

# Development
## Run tests
Since coverage issue/feature, plugins coverage is broken by default. [Workaround](https://pytest-cov.readthedocs.io/en/latest/plugins.html):
``` bash
COV_CORE_SOURCE=pytest_automock COV_CORE_CONFIG=.coveragerc COV_CORE_DATAFILE=.coverage.eager pytest
```
