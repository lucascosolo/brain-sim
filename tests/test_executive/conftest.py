import sys
from pathlib import Path

import pytest

try:
    import reflex  # noqa: F401
except ImportError:  # dev fallback: a sibling checkout of reflex-layer
    sibling = Path(__file__).resolve().parents[3] / "reflex-layer"
    if not (sibling / "reflex").is_dir():
        raise ImportError("reflex-layer is not installed: run `pip install -e ../reflex-layer`")
    sys.path.insert(0, str(sibling))


@pytest.fixture
def dirs(tmp_path):
    repo, state, memory = tmp_path / "repo", tmp_path / "state", tmp_path / "memory"
    repo.mkdir()
    return repo, state, memory
