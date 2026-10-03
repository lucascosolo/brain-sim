"""PRD section 1: Engine stim bookkeeping (observation only)."""
import numpy as np

from brainsim import params
from brainsim.engine import Engine

STIMLOG_MAX = getattr(params, "STIMLOG_MAX", 64)


def test_inject_returns_stim_record():
    e = Engine(seed=1)
    rec = e.inject(np.array([0]), 5.0, 50)
    assert isinstance(rec, dict)
    for key in ("stim_id", "n_cells", "amp_mv", "t_accept", "t_end_planned",
                "t_first_applied", "t_last_applied", "delivered_ticks",
                "gated_ticks", "t_dropped", "done"):
        assert key in rec, key
    assert rec["stim_id"] == 1
    assert rec["n_cells"] == 1
    assert rec["amp_mv"] == 5.0
    assert rec["t_accept"] == 0
    assert rec["t_end_planned"] == 50
    assert rec["done"] is False


def test_present_returns_stim_record():
    e = Engine(seed=1)
    rec = e.present(0, 200)
    assert isinstance(rec, dict)
    assert rec["t_end_planned"] == e.t + 200


def test_gated_present_returns_none_and_appends_nothing():
    e = Engine(seed=1)
    e.set_sleep(True)
    n_before = len(e._inj)
    rec = e.present(0, 200)
    assert rec is None
    assert len(e._inj) == n_before


def test_inject_returns_none_when_ticks_non_positive():
    e = Engine(seed=1)
    rec = e.inject(np.array([0]), 5.0, 0)
    assert rec is None


def test_t_first_applied_after_one_step():
    e = Engine(seed=1)
    rec = e.inject(np.array([0]), 5.0, 50)
    e.step(1)
    active = e.stims_active()
    match = next(r for r in active if r["stim_id"] == rec["stim_id"])
    assert match["t_first_applied"] == rec["t_accept"]


def test_delivered_ticks_after_full_run():
    e = Engine(seed=1)
    rec = e.inject(np.array([0]), 5.0, 50)
    e.step(50)
    done = next(r for r in e.stimlog if r["stim_id"] == rec["stim_id"])
    assert done["delivered_ticks"] == 50


def test_t_last_applied_is_end_minus_one():
    e = Engine(seed=1)
    rec = e.inject(np.array([0]), 5.0, 50)
    e.step(50)
    done = next(r for r in e.stimlog if r["stim_id"] == rec["stim_id"])
    assert done["t_last_applied"] == rec["t_end_planned"] - 1


def test_done_and_in_stimlog_after_drop_with_t_dropped():
    e = Engine(seed=1)
    rec = e.inject(np.array([0]), 5.0, 50)
    e.step(50)
    ids_active = [r["stim_id"] for r in e.stims_active()]
    assert rec["stim_id"] not in ids_active
    done = next(r for r in e.stimlog if r["stim_id"] == rec["stim_id"])
    assert done["done"] is True
    assert done["t_dropped"] == rec["t_end_planned"]


def test_two_overlapping_injections_keep_separate_counts():
    e = Engine(seed=1)
    a = e.inject(np.array([0]), 5.0, 30)
    e.step(10)
    b = e.inject(np.array([1]), 7.0, 30)
    e.step(20)
    a_done = next(r for r in e.stimlog if r["stim_id"] == a["stim_id"])
    assert a_done["done"] is True
    b_active = next(r for r in e.stims_active() if r["stim_id"] == b["stim_id"])
    assert b_active["done"] is False
    assert a_done["stim_id"] != b_active["stim_id"]
    assert a_done["delivered_ticks"] == 30


def test_wake_stimulus_gated_when_sleep_starts_mid_run():
    e = Engine(seed=1)
    sense_slice = e.net.region_slice["sense"]
    ids = np.array([sense_slice.start])
    rec = e.inject(ids, 5.0, 100)
    e.step(40)
    e.set_sleep(True)
    e.step(60)
    ids_after = [r["stim_id"] for r in e.stims_active()] + [r["stim_id"] for r in e.stimlog]
    assert rec["stim_id"] in ids_after
    found = next((r for r in e.stims_active() if r["stim_id"] == rec["stim_id"]),
                 None) or next(r for r in e.stimlog if r["stim_id"] == rec["stim_id"])
    # entry ticks 0-39 deliver in wake; 40-99 are all-sense under the gate
    assert found["gated_ticks"] == 60
    assert found["delivered_ticks"] == 40


def test_stimlog_bounded_at_max_and_oldest_evicted():
    e = Engine(seed=1)
    first_id = None
    for i in range(STIMLOG_MAX + 5):
        rec = e.inject(np.array([0]), 5.0, 1)
        if i == 0:
            first_id = rec["stim_id"]
        e.step(1)
    assert len(e.stimlog) == STIMLOG_MAX
    logged_ids = [r["stim_id"] for r in e.stimlog]
    assert first_id not in logged_ids


def test_stim_events_started_and_ended_in_frame():
    e = Engine(seed=1)
    rec = e.inject(np.array([0]), 5.0, 10)
    e.step(10)
    f = e.frame()
    events = f["stim_events"]
    started = [ev for ev in events if ev["stim_id"] == rec["stim_id"] and ev["event"] == "started"]
    ended = [ev for ev in events if ev["stim_id"] == rec["stim_id"] and ev["event"] == "ended"]
    assert len(started) == 1
    assert started[0]["t"] == rec["t_accept"]
    assert len(ended) == 1
    assert ended[0]["t"] == rec["t_end_planned"] - 1
    assert ended[0]["t_dropped"] == rec["t_end_planned"]


def test_ended_event_carries_delivered_and_gated_ticks_full_delivery():
    e = Engine(seed=1)
    rec = e.inject(np.array([0]), 5.0, 30)
    e.step(30)
    done = next(r for r in e.stimlog if r["stim_id"] == rec["stim_id"])
    f = e.frame()
    ended = next(ev for ev in f["stim_events"]
                 if ev["stim_id"] == rec["stim_id"] and ev["event"] == "ended")
    assert ended["delivered_ticks"] == done["delivered_ticks"] == 30
    assert ended["gated_ticks"] == done["gated_ticks"] == 0
    assert ended["partially_gated_ticks"] == done["partially_gated_ticks"] == 0


def test_ended_event_carries_delivered_and_gated_ticks_when_gated():
    e = Engine(seed=1)
    sense_slice = e.net.region_slice["sense"]
    rec = e.inject(np.array([sense_slice.start]), 5.0, 20)
    e.set_sleep(True)
    e.step(20)
    done = next(r for r in e.stimlog if r["stim_id"] == rec["stim_id"])
    f = e.frame()
    ended = next(ev for ev in f["stim_events"]
                 if ev["stim_id"] == rec["stim_id"] and ev["event"] == "ended")
    assert ended["delivered_ticks"] == done["delivered_ticks"]
    assert ended["gated_ticks"] == done["gated_ticks"] == 20
    assert ended["partially_gated_ticks"] == done["partially_gated_ticks"] == 0


def test_frame_seq_increments():
    e = Engine(seed=1)
    e.step(1)
    f1 = e.frame()
    e.step(1)
    f2 = e.frame()
    assert f2["seq"] == f1["seq"] + 1


def test_mixed_sense_and_ctx_injection_gated_partially_when_sleep_starts():
    e = Engine(seed=1)
    sense_id = e.net.region_slice["sense"].start
    ctx_id = e.net.region_slice["ctx"].start
    rec = e.inject(np.array([sense_id, ctx_id]), 5.0, 20)
    assert rec["n_sense_cells"] == 1
    e.set_sleep(True)
    e.step(20)
    done = next(r for r in e.stimlog if r["stim_id"] == rec["stim_id"])
    assert done["delivered_ticks"] == 20
    assert done["partially_gated_ticks"] == 20
    assert done["gated_ticks"] == 0


def test_all_sense_injection_under_gate_is_fully_gated_not_partial():
    e = Engine(seed=1)
    sense_slice = e.net.region_slice["sense"]
    rec = e.inject(np.array([sense_slice.start, sense_slice.start + 1]), 5.0, 20)
    e.set_sleep(True)
    e.step(20)
    done = next(r for r in e.stimlog if r["stim_id"] == rec["stim_id"])
    assert done["gated_ticks"] == 20
    assert done["partially_gated_ticks"] == 0


def test_stims_active_snapshot_matches_inj_length():
    e = Engine(seed=1)
    e.inject(np.array([0]), 5.0, 100)
    e.inject(np.array([1]), 5.0, 100)
    assert len(e.stims_active()) == len(e._inj)
