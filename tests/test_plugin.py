import time

import pytest


class Namespace:
    class T:
        def get(self):
            return time.perf_counter()


def test_automock_sync(tmp_path_automock):

    a = []
    with tmp_path_automock((Namespace, "T"), unlocked=True) as memories:
        t = Namespace.T()
        a.append(t.get())
        a.append(t.get())
        memory, *_ = memories.values()
        assert len(memory) == 3

    b = []
    with tmp_path_automock((Namespace, "T"), unlocked=False) as memories:
        t = Namespace.T()
        b.append(t.get())
        b.append(t.get())
        memory, *_ = memories.values()
        assert len(memory) == 3

    assert a == b


def test_names_collision(tmp_path_automock):
    with pytest.raises(RuntimeError):
        with tmp_path_automock((Namespace, "T"), (Namespace, "T"), unlocked=True):
            pass
