import time

import pytest
from pytest_automock import AutoMockException, automock


class TException(Exception):
    def __init__(self):
        self.time = time.perf_counter()


class T:

    def __init__(self, x):
        self.x = x

    def some_sync(self, y):
        return self.x + y

    def some_sync2(self, y):
        return self.x + y

    async def some_async(self, y):
        return self.x + y

    def some_coro(self, y):
        async def some():
            return self.x + y
        return some()

    @staticmethod
    def some_static_sync(x, y):
        return x + y

    @staticmethod
    async def some_static_async(x, y):
        return x + y

    def some_exception_sync(self):
        raise TException

    async def some_exception_async(self):
        raise TException

    def side_sync(self):
        return time.perf_counter()

    @property
    def some_property(self):
        return


@pytest.mark.asyncio
async def test_simple():
    m = {}
    t = automock(T, memory=m, locked=False)(1)
    assert t.some_sync(1) == 2
    assert await t.some_async(2) == 3
    assert await t.some_coro(3) == 4
    assert t.some_sync(1) == 2
    assert t.some_sync(4) == 5
    assert len(m) == 6

    t = automock(None, memory=m, locked=True)(1)
    assert t.some_sync(1) == 2
    assert await t.some_async(2) == 3
    assert await t.some_coro(3) == 4
    assert t.some_sync(1) == 2
    assert t.some_sync(4) == 5
    assert len(m) == 6


def test_multiple_instance():
    m = {}
    t = automock(T, memory=m, locked=False)
    t11 = t(1)
    t12 = t(2)
    r11 = t11.side_sync()
    r12 = t12.side_sync()
    assert r11 != r12

    t = automock(T, memory=m, locked=True)
    t21 = t(1)
    t22 = t(2)
    r22 = t22.side_sync()
    r21 = t21.side_sync()
    assert r21 != r22

    assert r11 == r21
    assert r12 == r22


def test_out_of_sequence():
    m = {}
    t = automock(T, memory=m, locked=False)(1)
    assert t.some_sync(1) == 2
    assert t.some_sync(2) == 3
    assert len(m) == 3

    with pytest.raises(AutoMockException):
        t = automock(None, memory=m, locked=True)(2)

    t = automock(None, memory=m, locked=True)(1)
    with pytest.raises(AutoMockException):
        t.some_sync(2)


@pytest.mark.asyncio
async def test_function_mock():
    m = {}
    f = automock(T.some_static_sync, memory=m, locked=False)
    assert f(1, 2) == 3
    assert f(1, 2) == 3
    assert f(1, 3) == 4
    assert len(m) == 4

    f = automock(T.some_static_sync, memory=m, locked=True)
    assert f(1, 2) == 3
    assert f(1, 2) == 3
    assert f(1, 3) == 4
    assert len(m) == 4

    m = {}
    f = automock(T.some_static_async, memory=m, locked=False)
    assert await f(1, 2) == 3
    assert await f(1, 2) == 3
    assert await f(1, 3) == 4
    assert len(m) == 4


@pytest.mark.asyncio
async def test_exception():
    m = {}
    t = automock(T, memory=m, locked=False)(1)
    a = None
    try:
        t.some_exception_sync()
    except TException as e:
        a = e

    t = automock(T, memory=m, locked=True)(1)
    b = None
    try:
        t.some_exception_sync()
    except TException as e:
        b = e

    assert a.time == b.time

    m = {}
    t = automock(T, memory=m, locked=False)(1)
    a = None
    try:
        await t.some_exception_async()
    except TException as e:
        a = e

    t = automock(T, memory=m, locked=True)(1)
    b = None
    try:
        await t.some_exception_async()
    except TException as e:
        b = e

    assert a.time == b.time


def test_lock():
    m = {}
    with pytest.raises(AutoMockException):
        automock(T, memory=m, locked=True)(1)


def test_missed_key():
    m = {}
    t = automock(T, memory=m, locked=False)(1)
    t.some_sync(1)

    t = automock(T, memory=m, locked=True)(1)
    t.some_sync(1)
    with pytest.raises(AutoMockException):
        t.some_sync(1)


def test_broken_memory():
    m = {}
    t = automock(T, memory=m, locked=False)(1)
    t.some_sync(1)

    m[0, 1].type = "foo"

    t = automock(T, memory=m, locked=True)(1)
    with pytest.raises(AutoMockException):
        t.some_sync(1)


def test_bad_attribute():
    m = {}
    t = automock(T, memory=m, locked=False)(1)
    with pytest.raises(AutoMockException):
        t.some_property()


def test_debug():
    called = False

    def debug(m, c1, c2):
        nonlocal called
        called = True
        assert isinstance(m, dict)
        assert len(m) == 2
        assert c1.args == (2,)
        assert c2.args == (1,)

    m = {}
    t = automock(T, memory=m, locked=False)(1)
    t.some_sync(1)

    t = automock(T, memory=m, locked=True, debug=debug)(1)
    with pytest.raises(AutoMockException):
        t.some_sync(2)
    assert called
