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
* Customizable serialization

# Limitaions
* No support for dunder methods (can be partly solved in future)
* No support for sync/async generators/contexts
* Races can break tests, since order counts
* Non-determenistic representation will break tests, since representation is a part of call snapshot key

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
You can also use module path notation:
``` python
import pytest

@pytest.fixture(autouse=True)
def _mocks(automock):
    with automock("mymod.Network"):
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
def automock(*targets,
             storage: Union[str, Path] = "tests/mocks",
             override_name: Optional[str] = None,
             unlocked: Optional[bool] = None,
             remove: Optional[bool] = None,
             encode: Callable[[Any], bytes] = pickle.dumps,
             decode: Callable[[bytes], Any] = pickle.loads)
```
* `*targets`: pair/tuple of object/module and attribute name (`str`) or module path to object/function with dot delimiter (`(mymod, "Network")` or `"mymod.Network"`)
* `storage`: root path for storing mocks
* `override_name`: forced mock-file name
* `unlocked`: mode selector (if omited, selected by `--automock-unlocked`)
* `remove`: remove test mock before test run (if omited, selected by `--automock-remove`)
* `encode`: encode routine
* `decode`: decode routine

## `automock_unlocked` (fixture)
Fixture with default mode from cli parameter (`bool`).

## `automock_remove` (fixture)
Fixture with default mode from cli parameter (`bool`).

## `automock` (function)
`automock` function is not supposed to be used by anyone but `automock` fixture
``` python
def automock(factory: Callable, *,
             memory: Dict,
             locked: bool = True,
             encode: Callable[[Any], bytes] = pickle.dumps,
             decode: Callable[[bytes], Any] = pickle.loads):
```
* `factory`: object/function to wrap
* `memory`: dicrionary to get/put mocks
* `locked`: mode selector
* `encode`: encode routine
* `decode`: decode routine

# Caveats
## Order
As feature paragraph described: «order counts». What does it mean?

### Functions
Mocked functions/coroutines call order counts. If you mock sequence
``` python
func(1, 2)
func(2, 3)
```
and trying to use mocked data with sequence
``` python
func(2, 3)
func(1, 2)
```
You will get an error, since calling order is part of idea of deterministic tests

### Objects
Mocked objects have same behavior, but methods call are individual, so if you mock sequence
``` python
t1 = T(1)
t2 = T(2)
t1.func(1, 2)
t2.func(2, 3)
```
then calling order are individual for method calls, so this is ok:
``` python
t1 = T(1)
t2 = T(2)
t2.func(2, 3)
t1.func(1, 2)
```
But not for `__init__` method, since mocks are internaly attached to instance
``` python
t2 = T(2)
t1 = T(1)
t1.func(1, 2)
t2.func(2, 3)
```
will fail

## Function arguments
Internally, key for mocks consists of instance number, call number, method name, positional arguments representation and keyword arguments representation. This leads to some «unobvious» behavior:
``` python
import time
from pytest_automock import automock

def nop(x):
    return x

m = {}
mocked = automock(nop, memory=m, locked=False)
mocked(time.time())

mocked = automock(nop, memory=m, locked=True)
mocked(time.time())
```
Will fail because of argument in mock creation time differs from argument in mock use time.

Same thing will break mocks if representation is not determenistic:
``` python
...
mocked(object())
...
mocked(object())
```
Since basic objects are represented as `<object object at 0x7ffa21c1cb90>`.

# Development
## Run tests
Since coverage issue/feature, plugins coverage is broken by default. [Workaround](https://pytest-cov.readthedocs.io/en/latest/plugins.html):
``` bash
COV_CORE_SOURCE=pytest_automock COV_CORE_CONFIG=.coveragerc COV_CORE_DATAFILE=.coverage.eager pytest
```
