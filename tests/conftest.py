from functools import partial

import pytest


@pytest.fixture
def tmp_path_automock(automock, tmp_path):
    return partial(automock, storage=tmp_path)
