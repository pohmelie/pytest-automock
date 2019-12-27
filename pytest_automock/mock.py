import itertools
import inspect
import pickle
import reprlib
from enum import Enum
from functools import partial
from typing import Any, Dict, Callable


__all__ = (
    "automock",
)


def automock(factory: Callable, *,
             memory: Dict,
             locked: bool = True,
             encode: Callable[[Any], bytes] = pickle.dumps,
             decode: Callable[[bytes], Any] = pickle.loads):
    counter = itertools.count()
    if inspect.isfunction(factory) or inspect.isbuiltin(factory):
        factory = partial(_FunctionAsClass, factory)
        return _Proxy(memory, counter, factory, locked, encode, decode)
    return partial(_Proxy, memory, counter, factory, locked, encode, decode)


class _FunctionAsClass:

    def __init__(self, f):
        self._f = f

    def __call__(self, *args, **kwargs):
        return self._f(*args, **kwargs)


class _ResultType(Enum):
    sync = "sync"
    async_ = "async"


class _Result:

    def __init__(self, value: Any, type: _ResultType, is_exception: bool = False):
        self.value = value
        self.type = type
        self.is_exception = is_exception

    def __repr__(self):
        return f"{self.__class__.__name__}(value={self.value!r}, type={self.type!r}, " \
               f"is_exception={self.is_exception!r})"


class _Proxy:

    def __init__(self, memory, counter, factory, locked, encode, decode, *args, **kwargs):
        self.__memory = memory
        self.__instance_index = next(counter)
        self.__counter = itertools.count()
        self.__instance = None
        self.__locked = locked
        self.__encode = encode
        self.__decode = decode
        key = self.__build_key("__init__", args, kwargs)
        if key not in self.__memory:
            self.__check_if_can_call("__init__")
            self.__instance = factory(*args, **kwargs)
            self.__memory[key] = True

    def __build_key(self, method, args, kwargs):
        return self.__instance_index, next(self.__counter), method, repr((args, kwargs))

    def __check_if_can_call(self, method):
        if self.__locked:
            raise RuntimeError(f"Mock is locked, but {method!r} wanted")

    def __resolve_method(self, name):
        def wrapper(*args, **kwargs):
            key = self.__build_key(name, args, kwargs)
            if key in self.__memory:
                result = self.__decode(self.__memory[key])
                if result.type == _ResultType.async_:
                    return self.__resolve_async(key, name, args, kwargs)
                elif result.type == _ResultType.sync:
                    return self.__resolve_sync(key, name, args, kwargs)
                else:
                    raise ValueError(f"Unknown result type {result}")
            if self.__instance is None:
                keys_representation = ", ".join(reprlib.repr(k) for k in self.__memory.keys())
                raise RuntimeError(f"Missed key {key!r} in mock sequence {keys_representation}")
            self.__check_if_can_call(name)
            attr = getattr(self.__instance, name)
            if inspect.iscoroutinefunction(attr):
                return self.__resolve_async(key, name, args, kwargs)
            elif inspect.ismethod(attr):
                return self.__resolve_sync(key, name, args, kwargs)
            else:
                raise ValueError(f"Unsupported attribute {name} {attr}")
        return wrapper

    async def __resolve_async(self, key, name, args, kwargs, *, coroutine=None):
        if key not in self.__memory:
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
            try:
                self.__memory[key] = self.__encode(result)
            except Exception as e:
                raise ValueError(f"Can't encode {result!r}") from e
        return self.__resolve_result(key)

    def __resolve_sync(self, key, name, args, kwargs):
        if key not in self.__memory:
            f = getattr(self.__instance, name)
            try:
                value = f(*args, **kwargs)
                if inspect.iscoroutine(value):
                    return self.__resolve_async(key, name, args, kwargs, coroutine=value)
            except Exception as e:
                result = _Result(e, _ResultType.sync, is_exception=True)
            else:
                result = _Result(value, _ResultType.sync)
            self.__memory[key] = self.__encode(result)
        return self.__resolve_result(key)

    def __resolve_result(self, key):
        result = self.__decode(self.__memory[key])
        if result.is_exception:
            raise result.value
        return result.value

    def __getattr__(self, name):
        return self.__resolve_method(name)

    def __call__(self, *args, **kwargs):
        return self.__getattr__("__call__")(*args, **kwargs)
