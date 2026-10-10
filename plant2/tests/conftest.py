import os

import pytest

from plant2 import record


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: full kill-test runs (minutes); deselect with -m 'not slow'")


@pytest.fixture
def run_dir(request, monkeypatch):
    """A fresh directory for one test's outputs, under ~/.cache/brain-sim/plant2/test-runs.

    AGENTS.md invariants 1 and 5: test outputs never go to /tmp and no code cleans them up
    (pytest's own temporary directories are pruned automatically, so they are not used).
    BRAINSIM_CACHE is pointed inside it so drivers write there too.
    """
    name = f"{record.now().replace(':', '')}-{os.getpid()}-{request.node.name}"
    d = record.cache_dir("test-runs", name)
    monkeypatch.setenv("BRAINSIM_CACHE", str(d))
    return d
