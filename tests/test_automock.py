import time

import pytest

from pytest_automock import automock


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
    m1 = {}
    t = automock(T, memory=m1)
    t()
    t()


def test_out_of_sequence():
    m = {}
    t = automock(T, memory=m, locked=False)(1)
    assert t.some_sync(1) == 2
    assert t.some_sync(2) == 3
    assert len(m) == 3

    with pytest.raises(RuntimeError):
        t = automock(None, memory=m, locked=True)(2)

    t = automock(None, memory=m, locked=True)(1)
    with pytest.raises(RuntimeError):
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
    with pytest.raises(RuntimeError):
        automock(T, memory=m, locked=True)(1)
