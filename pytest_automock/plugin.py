import contextlib
import importlib
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union

import pytest

from .mock import default_decode, default_encode, Call
from .mock import automock as automock_implementation


def pytest_addoption(parser):
    parser.addoption("--automock-unlocked", action="store_true", default=False,
                     help="Unlock automock plugin storage and actual calls")
    parser.addoption("--automock-remove", action="store_true", default=False,
                     help="Remove appropriate existing mock before each test")


@pytest.fixture(scope="session")
def automock_unlocked(request):
    return request.config.getoption("--automock-unlocked")


@pytest.fixture(scope="session")
def automock_remove(request):
    return request.config.getoption("--automock-remove")


@pytest.fixture
def automock(request, monkeypatch, automock_unlocked, automock_remove):
    @contextlib.contextmanager
    def automocker(*targets,
                   storage: Union[str, Path] = "tests/mocks",
                   override_name: Optional[str] = None,
                   unlocked: Optional[bool] = None,
                   remove: Optional[bool] = None,
                   encode: Callable[[Any], bytes] = default_encode,
                   decode: Callable[[bytes], Any] = default_decode,
                   debug: Optional[Callable[[Dict, Call, Optional[Call]], None]] = None):
        if unlocked is None:
            unlocked = automock_unlocked
        if remove is None:
            remove = automock_remove
        with monkeypatch.context() as m:
            memories = {}
            for target in targets:
                if isinstance(target, tuple):
                    obj, name = target
                elif isinstance(target, str):
                    module_name, name = target.rsplit(".", maxsplit=1)
                    obj = importlib.import_module(module_name)
                else:
                    raise TypeError(f"Expect tuple of (obj, name) or string-path, got {target!r}")
                filename = override_name or name
                p = Path(storage).joinpath(request.node.name, obj.__name__, filename)
                if p in memories:
                    raise RuntimeError(f"Mock with path {p} already exist")
                if remove and p.exists():
                    p.unlink()
                memory = {}
                if p.exists():
                    memory = decode(p.read_bytes())
                original = getattr(obj, name)
                mocked = automock_implementation(
                    original,
                    memory=memory,
                    locked=not unlocked,
                    encode=encode,
                    decode=decode,
                    debug=debug,
                )
                m.setattr(obj, name, mocked)
                memories[p] = memory
            yield memories
            if unlocked:
                for p, memory in memories.items():
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_bytes(encode(memory))

    return automocker
