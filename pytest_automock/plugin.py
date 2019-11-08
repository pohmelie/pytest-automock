import contextlib
from pathlib import Path

import pytest

from .mock import ObjectMock


def pytest_addoption(parser):
    parser.addoption("--automock-unlocked", action="store_true", default=False,
                     help="Unlock automock plugin storage and actual calls")


@pytest.fixture(scope="session")
def automock_unlocked(request):
    return request.config.getoption("--automock-unlocked")


@pytest.fixture
def automock(request, monkeypatch, automock_unlocked):
    @contextlib.contextmanager
    def automocker(*pairs, storage="tests/mocks", unlocked=None):
        if unlocked is None:
            unlocked = automock_unlocked
        with monkeypatch.context() as m:
            mocks = {}
            for obj, name in pairs:
                p = Path(storage).joinpath(request.node.name, obj.__name__, name)
                binary = None
                if p.exists():
                    binary = p.read_bytes()
                original = getattr(obj, name)
                mock = ObjectMock.from_bytes(original, binary=binary, locked=not unlocked)
                m.setattr(obj, name, mock.proxy)
                if p in mocks:
                    raise RuntimeError(f"Mock with path {p} already exist")
                mocks[p] = mock
            yield mocks
            if unlocked:
                for p, mock in mocks.items():
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_bytes(mock.as_bytes())

    return automocker
