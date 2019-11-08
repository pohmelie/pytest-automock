import time

import pytest


class DummyException(Exception):
    pass


def test_automock_sync(automock, tmp_path):
    class Namespace:
        class T:
            def get(self):
                return time.perf_counter()

            def exception(self):
                raise DummyException()

    with automock((Namespace, "T"), storage=tmp_path, unlocked=False):
        with pytest.raises(RuntimeError):
            Namespace.T().get()

    with pytest.raises(RuntimeError):
        with automock((Namespace, "T"), (Namespace, "T"), storage=tmp_path, unlocked=False):
            pass

    a = []
    with automock((Namespace, "T"), storage=tmp_path, unlocked=True) as mocks:
        t = Namespace.T()
        a.append(t.get())
        a.append(t.get())
        with pytest.raises(DummyException):
            t.exception()
        mock, *_ = mocks.values()
        assert len(mock.mem) == 4

    b = []
    with automock((Namespace, "T"), storage=tmp_path, unlocked=True) as mocks:
        t = Namespace.T()
        b.append(t.get())
        b.append(t.get())
        with pytest.raises(DummyException):
            t.exception()
        mock, *_ = mocks.values()
        assert len(mock.mem) == 4

    with automock((Namespace, "T"), storage=tmp_path, unlocked=False) as mocks:
        t = Namespace.T()
        with pytest.raises(RuntimeError):
            t.unknown()

    assert a == b


@pytest.mark.asyncio
async def test_automock_async(automock, tmp_path):
    class Namespace:
        class T:
            async def get(self):
                return time.perf_counter()

            async def exception(self):
                raise DummyException()

    with automock((Namespace, "T"), storage=tmp_path, unlocked=False):
        with pytest.raises(RuntimeError):
            await Namespace.T().get()

    a = []
    with automock((Namespace, "T"), storage=tmp_path, unlocked=True) as mocks:
        t = Namespace.T()
        a.append(await t.get())
        a.append(await t.get())
        with pytest.raises(DummyException):
            await t.exception()
        mock, *_ = mocks.values()
        assert len(mock.mem) == 4

    b = []
    with automock((Namespace, "T"), storage=tmp_path, unlocked=True) as mocks:
        t = Namespace.T()
        b.append(await t.get())
        b.append(await t.get())
        with pytest.raises(DummyException):
            await t.exception()
        mock, *_ = mocks.values()
        assert len(mock.mem) == 4

    assert a == b


@pytest.mark.asyncio
async def test_automock_coroutine(automock, tmp_path):
    class Namespace:
        class T:
            def get(self):
                async def foo():
                    return time.perf_counter()
                return foo()

    a = []
    with automock((Namespace, "T"), storage=tmp_path, unlocked=True) as mocks:
        t = Namespace.T()
        a.append(await t.get())
        a.append(await t.get())
        mock, *_ = mocks.values()
        assert len(mock.mem) == 3

    b = []
    with automock((Namespace, "T"), storage=tmp_path, unlocked=True) as mocks:
        t = Namespace.T()
        b.append(await t.get())
        b.append(await t.get())
        mock, *_ = mocks.values()
        assert len(mock.mem) == 3

    assert a == b
