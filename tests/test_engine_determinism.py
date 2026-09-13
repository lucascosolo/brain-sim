"""PRD section 6: determinism reference.

Reference digest computed by actually running `run_schedule` on brainsim.engine.Engine
at commit 3060f23 (K0.3 population protocol...), via:
    git -C /home/lucas/Workspaces/brain-sim worktree add ~/.cache/scratch/brainsim-ref 3060f23
    <worktree>/.venv-equivalent .venv/bin/python <script running run_schedule() below,
        hashing (t, spike_count bytes, w bytes, alive bytes, v bytes)>
    git -C /home/lucas/Workspaces/brain-sim worktree remove ~/.cache/scratch/brainsim-ref
"""
import hashlib

import numpy as np

from brainsim.engine import Engine

# Pinned at commit 3060f23 ("K0.3 population protocol: imposed pairing with exact
# per-tick attribution; result 0.93, fails"), schedule = run_schedule() below.
REFERENCE_DIGEST = "a839afcf22ea24b7b2f8fa022ff6791e153c91df55dfd463b282906870d95309"


def run_schedule():
    e = Engine(seed=1)
    e.step(300)
    e.present(0, 200)
    e.step(100)
    e.inject(list(range(400, 420)), 5.0, 50)
    e.step(500)
    e.set_sleep(True)
    e.present(1, 200)
    e.step(300)
    e.set_sleep(False)
    e.step(1200)  # crosses a sweep (SWEEP_TICKS = 1000)
    return e


def _digest(e):
    h = hashlib.sha256()
    h.update(int(e.t).to_bytes(8, "little"))
    h.update(e.net.spike_count.tobytes())
    h.update(e.net.w.tobytes())
    h.update(e.net.alive.tobytes())
    h.update(e.net.v.tobytes())
    return h.hexdigest()


def test_schedule_digest_matches_reference():
    e = run_schedule()
    assert _digest(e) == REFERENCE_DIGEST


def test_frame_and_stims_reads_consume_no_rng():
    e_read = Engine(seed=1)
    e_plain = Engine(seed=1)
    for _ in range(20):
        e_read.step(50)
        e_read.frame()
        e_read.stims_active()
        list(e_read.stimlog)
        e_plain.step(50)
    assert e_read.rng.bit_generator.state == e_plain.rng.bit_generator.state
    assert np.array_equal(e_read.net.v, e_plain.net.v)
