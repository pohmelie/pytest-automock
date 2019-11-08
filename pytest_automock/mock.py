import itertools
import pickle
import inspect
from enum import Enum
from dataclasses import dataclass
from functools import partial
from typing import Any, Optional, Dict


class ObjectMock:

    def __init__(self, factory, *, mem: Optional[Dict] = None, locked: bool = True):
        self.factory = factory
        self.mem = mem or {}
        self.locked = locked
        self.counter = itertools.count()

    def as_bytes(self) -> bytes:
        return pickle.dumps(self.mem)

    @classmethod
    def from_bytes(cls, factory, *, binary: Optional[bytes] = None, locked: bool = True):
        mem = None
        if binary is not None:
            mem = pickle.loads(binary)
        return cls(factory, mem=mem, locked=locked)

    @property
    def proxy(self):
        if inspect.isfunction(self.factory):
            factory = partial(_FunctionAsClass, self.factory)
            return _Proxy(self.mem, self.counter, factory, self.locked)
        return partial(_Proxy, self.mem, self.counter, self.factory, self.locked)


class _FunctionAsClass:

    def __init__(self, f):
        self._f = f

    def __call__(self, *args, **kwargs):
        return self._f(*args, **kwargs)


class _ResultType(Enum):
    sync = "sync"
    async_ = "async"


@dataclass
class _Result:
    value: Any
    type: _ResultType
    is_exception: bool = False


class _Proxy:

    def __init__(self, mem, counter, factory, locked, *args, **kwargs):
        self.__mem = mem
        self.__counter = counter
        self.__instance = None
        self.__locked = locked
        key = pickle.dumps([next(self.__counter), "__init__", args, kwargs])
        if key not in self.__mem:
            self.__check_if_locked("__init__")
            self.__instance = factory(*args, **kwargs)
            self.__mem[key] = True

    def __check_if_locked(self, method):
        if self.__locked:
            raise RuntimeError(f"Mock is locked, but {method!r} wanted")

    def __resolve_method(self, index, name):
        def wrapper(*args, **kwargs):
            key = pickle.dumps([index, name, args, kwargs])
            if key in self.__mem:
                result = self.__mem[key]
                if result.type == _ResultType.async_:
                    return self.__resolve_async(key)
                elif result.type == _ResultType.sync:
                    return self.__resolve_sync(key)
                else:
                    raise ValueError(f"Unknown result type {result}")
            if self.__instance is None:
                info = pickle.loads(key)
                raise RuntimeError(f"Missed key {info!r} in "
                                   f"recorded mock sequence {self.__mem}")
            self.__check_if_locked(name)
            attr = getattr(self.__instance, name)
            if inspect.iscoroutinefunction(attr):
                return self.__resolve_async(key)
            elif inspect.ismethod(attr):
                return self.__resolve_sync(key)
            else:
                raise ValueError(f"Unsupported attribute {name} {attr}")
        return wrapper

    async def __resolve_async(self, key, *, coroutine=None):
        if key not in self.__mem:
            _, name, args, kwargs = pickle.loads(key)
            self.__check_if_locked(name)
            f = getattr(self.__instance, name)
            try:
                if coroutine is None:
                    value = await f(*args, **kwargs)
                else:
                    value = await coroutine
            except Exception as e:
                result = _Result(e, _ResultType.async_, is_exception=True)
            else:
                result = _Result(value, _ResultType.async_)
            self.__mem[key] = result
        return self.__resolve_result(key)

    def __resolve_sync(self, key):
        if key not in self.__mem:
            *_, name, args, kwargs = pickle.loads(key)
            f = getattr(self.__instance, name)
            try:
                value = f(*args, **kwargs)
                if inspect.iscoroutine(value):
                    return self.__resolve_async(key, coroutine=value)
            except Exception as e:
                result = _Result(e, _ResultType.sync, is_exception=True)
            else:
                result = _Result(value, _ResultType.sync)
            self.__mem[key] = result
        return self.__resolve_result(key)

    def __resolve_result(self, key):
        result = self.__mem[key]
        if result.is_exception:
            raise result.value
        return result.value

    def __getattr__(self, name):
        index = next(self.__counter)
        return self.__resolve_method(index, name)

    def __call__(self, *args, **kwargs):
        return self.__getattr__("__call__")(*args, **kwargs)
