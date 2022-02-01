import time

import pytest

from pytest_automock import AutoMockException


class Namespace:
    class T:
        def get(self):
            return time.perf_counter()


def test_automock_sync(tmp_path_automock):
    a = []
    with tmp_path_automock((Namespace, "T"), unlocked=True, remove=False) as memories:
        t = Namespace.T()
        a.append(t.get())
        a.append(t.get())
        memory, *_ = memories.values()
        assert len(memory) == 3

    b = []
    with tmp_path_automock((Namespace, "T"), unlocked=False, remove=False) as memories:
        t = Namespace.T()
        b.append(t.get())
        b.append(t.get())
        memory, *_ = memories.values()
        assert len(memory) == 3

    assert a == b


def test_names_collision(tmp_path_automock):
    with pytest.raises(RuntimeError):
        with tmp_path_automock((Namespace, "T"), (Namespace, "T"), unlocked=True, remove=False):
            pass


def test_remove(tmp_path_automock):
    with tmp_path_automock((Namespace, "T"), unlocked=True, remove=False):
        a = Namespace.T().get()
    with tmp_path_automock((Namespace, "T"), unlocked=True, remove=False):
        b = Namespace.T().get()
    with tmp_path_automock((Namespace, "T"), unlocked=True, remove=True):
        c = Namespace.T().get()
    assert a == b
    assert a != c


def test_target_variants(tmp_path_automock):
    with tmp_path_automock("time.perf_counter", unlocked=True, remove=False):
        a = time.perf_counter()
    with tmp_path_automock("time.perf_counter", unlocked=False, remove=False):
        b = time.perf_counter()
    assert a == b
    with pytest.raises(TypeError):
        with tmp_path_automock(Namespace.T, unlocked=True, remove=False):
            pass


def test_defaults(tmp_path_automock, automock_unlocked, automock_remove):
    assert automock_unlocked is False
    assert automock_remove is False
    with pytest.raises(AutoMockException):
        with tmp_path_automock("time.perf_counter"):
            time.perf_counter()
    with tmp_path_automock("time.perf_counter", unlocked=True):
        a = time.perf_counter()
    with tmp_path_automock("time.perf_counter"):
        b = time.perf_counter()
    assert a == b
