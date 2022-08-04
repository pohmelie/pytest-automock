import gzip
import inspect
import itertools
import pickle
from enum import Enum
from functools import partial
from typing import Any, Callable, Dict, Optional

__all__ = (
    "automock",
    "AutoMockException",
    "default_decode",
    "default_encode",
    "Call",
)


class AutoMockException(Exception):
    pass


class _CallType(Enum):
    sync = "sync"
    async_ = "async"


def default_encode(v: Any) -> bytes:
    return gzip.compress(pickle.dumps(v))


def default_decode(b: bytes) -> Any:
    return pickle.loads(gzip.decompress(b))


class Call:
    def __init__(self,
                 instance_index: int,
                 call_index: int,
                 method: str,
                 request: bytes,
                 type: Optional[_CallType] = None,
                 response: Optional[bytes] = None,
                 is_exception: bool = False,
                 encode: Callable[[Any], bytes] = default_encode,
                 decode: Callable[[bytes], Any] = default_decode):
        self.instance_index = instance_index
        self.call_index = call_index
        self.method = method
        self.request = request
        self.type = type
        self.response = response
        self.is_exception = is_exception
        self.encode = encode
        self.decode = decode

    @property
    def key(self):
        return self.instance_index, self.call_index

    @property
    def args(self):
        args, _ = self.decode(self.request)
        return args

    @property
    def kwargs(self):
        _, kwargs = self.decode(self.request)
        return kwargs

    @property
    def result(self):
        return self.decode(self.response)

    def __repr__(self):
        return f"{self.__class__.__name__}(instance_index={self.instance_index}, call_index={self.call_index}, " \
               f"method={self.method})"


def automock(factory: Callable, *,
             memory: Dict,
             locked: bool = True,
             encode: Callable[[Any], bytes] = default_encode,
             decode: Callable[[bytes], Any] = default_decode,
             debug: Optional[Callable[[Dict, Call, Optional[Call]], None]] = None):
    counter = itertools.count()
    if inspect.isfunction(factory) or inspect.isbuiltin(factory):
        factory = partial(_FunctionAsClass, factory)
        return _Proxy(memory, counter, factory, locked, encode, decode, debug)
    return partial(_Proxy, memory, counter, factory, locked, encode, decode, debug)


class _FunctionAsClass:

    def __init__(self, f):
        self._f = f

    def __call__(self, *args, **kwargs):
        return self._f(*args, **kwargs)


class _Proxy:

    def __init__(self, memory, counter, factory, locked, encode, decode, debug, *args, **kwargs):
        self.__memory = memory
        self.__instance_index = next(counter)
        self.__counter = itertools.count()
        self.__instance = None
        self.__locked = locked
        self.__encode = encode
        self.__decode = decode
        if debug == "pdb":
            debug = self.__pdb_debug
        self.__debug = debug
        call = self.__build_call("__init__", args, kwargs)
        if call.key in self.__memory:
            self.__compare_request_with_saved(call)
        else:
            self.__check_if_can_call(call)
            self.__instance = factory(*args, **kwargs)
            call.type = _CallType.sync
            self.__memory[call.key] = call

    def __build_call(self, method, args, kwargs):
        request = self.__encode((args, kwargs))
        return Call(self.__instance_index, next(self.__counter), method, request,
                    encode=self.__encode, decode=self.__decode)

    @staticmethod
    def __pdb_debug(memory: Dict, call_wanted: Call, call_saved: Optional[Call] = None):
        import pdb
        pdb.set_trace()

    def __invoke_debug(self, call_wanted: Call, call_saved: Optional[Call] = None):
        if self.__debug is not None:
            self.__debug(self.__memory, call_wanted, call_saved)

    def __compare_request_with_saved(self, call_wanted: Call) -> Call:
        call_saved = self.__memory[call_wanted.key]
        if (call_wanted.method, call_wanted.request) == (call_saved.method, call_saved.request):
            return call_saved
        self.__invoke_debug(call_wanted, call_saved)
        raise AutoMockException(f"Requested broken call:\n"
                                f"Wanted: {call_wanted.method}, {call_wanted.args}, {call_wanted.kwargs}\n"
                                f"Saved:  {call_saved.method}, {call_saved.args}, {call_saved.kwargs}")

    def __check_if_can_call(self, call: Call):
        if self.__locked:
            self.__invoke_debug(call)
            raise AutoMockException(f"Mock is locked, but {call!r} wanted, there is no such "
                                    f"instance and call indexes pair in memory")

    def __resolve_method(self, name):
        def wrapper(*args, **kwargs):
            call_wanted = self.__build_call(name, args, kwargs)
            if call_wanted.key in self.__memory:
                call_saved = self.__compare_request_with_saved(call_wanted)
                if call_saved.type == _CallType.async_:
                    return self.__resolve_async(call_saved)
                elif call_saved.type == _CallType.sync:
                    return self.__resolve_sync(call_saved)
                else:
                    self.__invoke_debug(call_wanted, call_saved)
                    raise AutoMockException(f"Unknown call type {call_saved}")
            if self.__instance is None:
                self.__invoke_debug(call_wanted)
                calls = sorted(self.__memory.values(), key=lambda c: c.key)
                raise AutoMockException(f"Missed call {call_wanted} in mock sequence {calls}")
            self.__check_if_can_call(call_wanted)
            attr = getattr(self.__instance, call_wanted.method)
            if inspect.iscoroutinefunction(attr):
                return self.__resolve_async(call_wanted)
            elif inspect.ismethod(attr):
                return self.__resolve_sync(call_wanted)
            else:
                self.__invoke_debug(call_wanted)
                raise AutoMockException(f"Unsupported attribute {call_wanted.method} {attr}")
        return wrapper

    async def __resolve_async(self, call: Call, *, coroutine=None):
        call.type = _CallType.async_
        if call.key not in self.__memory:
            f = getattr(self.__instance, call.method)
            try:
                if coroutine is None:
                    value = await f(*call.args, **call.kwargs)
                else:
                    value = await coroutine
            except Exception as e:
                call.response = self.__encode(e)
                call.is_exception = True
            else:
                call.response = self.__encode(value)
            self.__memory[call.key] = call
        return self.__resolve_result(call)

    def __resolve_sync(self, call: Call):
        call.type = _CallType.sync
        if call.key not in self.__memory:
            f = getattr(self.__instance, call.method)
            try:
                value = f(*call.args, **call.kwargs)
                if inspect.iscoroutine(value):
                    return self.__resolve_async(call, coroutine=value)
            except Exception as e:
                call.response = self.__encode(e)
                call.is_exception = True
            else:
                call.response = self.__encode(value)
            self.__memory[call.key] = call
        return self.__resolve_result(call)

    def __resolve_result(self, call: Call):
        if call.is_exception:
            raise call.result
        return call.result

    def __getattr__(self, name):
        return self.__resolve_method(name)

    def __call__(self, *args, **kwargs):
        return self.__getattr__("__call__")(*args, **kwargs)
