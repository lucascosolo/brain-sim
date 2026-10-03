"""PRD section 5/6: runs the node:test suite covering ui/evidence.js."""
import glob
import os
import subprocess

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = "/home/lucas/.nvm/versions/node/v24.20.0/bin/node"


def test_evidence_js_suite_passes():
    if not os.path.exists(NODE):
        pytest.skip(f"node not found at {NODE}")
    # `node --test tests/js/` (a bare directory arg) errors as MODULE_NOT_FOUND on this
    # node install (v24.20.0) -- confirmed reproducible outside pytest too. Passing the
    # directory's *.test.mjs files explicitly runs the same suite under the same runner.
    files = sorted(glob.glob(os.path.join(REPO_ROOT, "tests", "js", "*.test.mjs")))
    assert files, "no tests/js/*.test.mjs files found"
    proc = subprocess.run(
        [NODE, "--test", *files],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, (
        f"node --test tests/js/ failed (exit {proc.returncode})\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
