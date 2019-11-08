import time

import pytest


class DummyException(Exception):
    pass


def test_automock_sync(tmp_path_automock):
    class Namespace:
        class T:
            def get(self):
                return time.perf_counter()

            def exception(self):
                raise DummyException()

    with tmp_path_automock((Namespace, "T"), unlocked=False):
        with pytest.raises(RuntimeError):
            Namespace.T().get()

    with pytest.raises(RuntimeError):
        with tmp_path_automock((Namespace, "T"), (Namespace, "T"), unlocked=False):
            pass

    a = []
    with tmp_path_automock((Namespace, "T"), unlocked=True) as mocks:
        t = Namespace.T()
        a.append(t.get())
        a.append(t.get())
        with pytest.raises(DummyException):
            t.exception()
        mock, *_ = mocks.values()
        assert len(mock.mem) == 4

    b = []
    with tmp_path_automock((Namespace, "T"), unlocked=True) as mocks:
        t = Namespace.T()
        b.append(t.get())
        b.append(t.get())
        with pytest.raises(DummyException):
            t.exception()
        mock, *_ = mocks.values()
        assert len(mock.mem) == 4

    with tmp_path_automock((Namespace, "T"), unlocked=False) as mocks:
        t = Namespace.T()
        with pytest.raises(RuntimeError):
            t.unknown()

    assert a == b


@pytest.mark.asyncio
async def test_automock_async(tmp_path_automock):
    class Namespace:
        class T:
            async def get(self):
                return time.perf_counter()

            async def exception(self):
                raise DummyException()

    with tmp_path_automock((Namespace, "T"), unlocked=False):
        with pytest.raises(RuntimeError):
            await Namespace.T().get()

    a = []
    with tmp_path_automock((Namespace, "T"), unlocked=True) as mocks:
        t = Namespace.T()
        a.append(await t.get())
        a.append(await t.get())
        with pytest.raises(DummyException):
            await t.exception()
        mock, *_ = mocks.values()
        assert len(mock.mem) == 4

    b = []
    with tmp_path_automock((Namespace, "T"), unlocked=False) as mocks:
        t = Namespace.T()
        b.append(await t.get())
        b.append(await t.get())
        with pytest.raises(DummyException):
            await t.exception()
        mock, *_ = mocks.values()
        assert len(mock.mem) == 4

    assert a == b


@pytest.mark.asyncio
async def test_automock_coroutine(tmp_path_automock):
    class Namespace:
        class T:
            def get(self):
                async def foo():
                    return time.perf_counter()
                return foo()

    a = []
    with tmp_path_automock((Namespace, "T"), unlocked=True) as mocks:
        t = Namespace.T()
        a.append(await t.get())
        a.append(await t.get())
        mock, *_ = mocks.values()
        assert len(mock.mem) == 3

    b = []
    with tmp_path_automock((Namespace, "T"), unlocked=False) as mocks:
        t = Namespace.T()
        b.append(await t.get())
        b.append(await t.get())
        mock, *_ = mocks.values()
        assert len(mock.mem) == 3

    assert a == b


def test_plain_function(tmp_path_automock):
    def f():
        return time.perf_counter()

    class Namespace:
        method = f

    with tmp_path_automock((Namespace, "method"), unlocked=True) as mocks:
        mock, *_ = mocks.values()
        assert len(mock.mem) == 1
        a = Namespace.method()
        assert len(mock.mem) == 2

    with tmp_path_automock((Namespace, "method"), unlocked=False) as mocks:
        mock, *_ = mocks.values()
        assert len(mock.mem) == 2
        b = Namespace.method()
        assert len(mock.mem) == 2

    assert a == b
