import itertools
import inspect
from enum import Enum
from dataclasses import dataclass
from functools import partial
from typing import Any, Dict, Callable, Optional, Sequence


__all__ = (
    "automock",
)


def automock(factory: Callable, *,
             memory: Dict,
             locked: bool = True,
             allowed_methods: Optional[Sequence[str]] = None,
             forbidden_methods: Optional[Sequence[str]] = None):
    if allowed_methods and forbidden_methods:
        intersection = set(allowed_methods) & set(forbidden_methods)
        if intersection:
            raise ValueError(f"{intersection} methods presents in both lists")
    counter = itertools.count()
    if inspect.isfunction(factory):
        factory = partial(_FunctionAsClass, factory)
        return _Proxy(memory, counter, factory, locked, allowed_methods, forbidden_methods)
    return partial(_Proxy, memory, counter, factory, locked, allowed_methods, forbidden_methods)


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

    def __init__(self, memory, counter, factory, locked, allowed, forbidden, *args, **kwargs):
        self.__memory = memory
        self.__counter = counter
        self.__instance = None
        self.__locked = locked
        self.__allowed = allowed
        self.__forbidden = forbidden
        key = self.__build_key("__init__", args, kwargs)
        force_create = allowed is not None or forbidden is not None
        if key not in self.__memory or force_create:
            if not force_create:
                self.__check_if_can_call("__init__")
            self.__instance = factory(*args, **kwargs)
            self.__memory[key] = True

    def __build_key(self, method, args, kwargs):
        return next(self.__counter), method, repr((args, kwargs))

    def __check_if_can_call(self, method):
        if self.__locked:
            raise RuntimeError(f"Mock is locked, but {method!r} wanted")

    def __should_mock(self, method):
        if self.__allowed is not None and method not in self.__allowed:
            return False
        if self.__forbidden is not None and method in self.__forbidden:
            return False
        return True

    def __resolve_method(self, name):
        def wrapper(*args, **kwargs):
            key = self.__build_key(name, args, kwargs)
            if key in self.__memory:
                result = self.__memory[key]
                if result.type == _ResultType.async_:
                    return self.__resolve_async(key, name, args, kwargs)
                elif result.type == _ResultType.sync:
                    return self.__resolve_sync(key, name, args, kwargs)
                else:
                    raise ValueError(f"Unknown result type {result}")
            if self.__instance is None:
                raise RuntimeError(f"Missed key {key!r} in mock sequence {self.__memory}")
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
            self.__memory[key] = result
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
            self.__memory[key] = result
        return self.__resolve_result(key)

    def __resolve_result(self, key):
        result = self.__memory[key]
        if result.is_exception:
            raise result.value
        return result.value

    def __getattr__(self, name):
        if not self.__should_mock(name):
            return getattr(self.__instance, name)
        return self.__resolve_method(name)

    def __call__(self, *args, **kwargs):
        return self.__getattr__("__call__")(*args, **kwargs)
