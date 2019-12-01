import contextlib
import pickle
from pathlib import Path
from typing import Union, Optional, Callable, Any

import pytest

from .mock import automock as automock_implementation


def pytest_addoption(parser):
    parser.addoption("--automock-unlocked", action="store_true", default=False,
                     help="Unlock automock plugin storage and actual calls")


@pytest.fixture(scope="session")
def automock_unlocked(request):
    return request.config.getoption("--automock-unlocked")


@pytest.fixture
def automock(request, monkeypatch, automock_unlocked):
    @contextlib.contextmanager
    def automocker(*pairs,
                   storage: Union[str, Path] = "tests/mocks",
                   override_name: Optional[str] = None,
                   unlocked: Optional[bool] = None,
                   encode: Callable[[Any], bytes] = pickle.dumps,
                   decode: Callable[[bytes], Any] = pickle.loads):
        if unlocked is None:
            unlocked = automock_unlocked
        with monkeypatch.context() as m:
            memories = {}
            for obj, name in pairs:
                filename = override_name or name
                p = Path(storage).joinpath(request.node.name, obj.__name__, filename)
                if p in memories:
                    raise RuntimeError(f"Mock with path {p} already exist")
                memory = {}
                if p.exists():
                    memory = decode(p.read_bytes())
                original = getattr(obj, name)
                mocked = automock_implementation(
                    original,
                    memory=memory,
                    locked=not unlocked,
                )
                m.setattr(obj, name, mocked)
                memories[p] = memory
            yield memories
            if unlocked:
                for p, memory in memories.items():
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_bytes(encode(memory))

    return automocker
