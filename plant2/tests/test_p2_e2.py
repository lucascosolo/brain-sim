import json

import numpy as np

from plant2.engine import LIF
from plant2.experiments import p2_e1_btsp as e1
from plant2.experiments import p2_e2_accommodation as e2

SMALL = dict(e2.CONTRACT, m=800, n=800, a=40, M=60, n_old=20, n_rand=20, n_novel=20, f_q=0.03, t_persist=300,
             t_gap=100, acc_tau=300, settle=1500, converge_window=300, persist_at=60)


def test_contract_constants_are_the_predeclared_ones():
    assert e2.ACC_TAU_MS == 10_000 and e2.SETTLE_MS == 50_000 and e2.CONVERGE_WINDOW_MS == 10_000
    assert e2.CONVERGE_BAR_MV == 0.2 and e2.J_GRID == (1.4, 1.45, 1.5, 1.55, 1.6, 1.65, 1.7, 1.75, 1.8, 1.85, 1.9)
    assert e2.GATE_M == (250, 500, 1000) and e2.GATED_SEEDS == (6, 7, 8, 9, 10) and e2.CAL_SEED == 0
    c = e2.CONTRACT
    assert {k: c[k] for k in e1.CONTRACT if k != "J"} == {k: v for k, v in e1.CONTRACT.items() if k != "J"}


def drive(cell, inputs):
    spikes = []
    for t, x in enumerate(inputs):
        cell.ring[t % (cell.d_max + 1)] += x
        if cell.step(t).size:
            spikes.append(t)
    return spikes


def test_accommodation_matches_a_reference_loop():
    rng = np.random.default_rng(0)
    inputs = rng.poisson(0.8, 3000) * 1.4
    cell = LIF("c", 1, d_max=1, acc_tau=500.0)
    got = drive(cell, inputs)
    v, vbar, last, ref = -70.0, -70.0, -10_000, []
    decay = np.float32(np.exp(-1 / 20.0))
    for t, x in enumerate(inputs):
        v = np.float32(np.float32(v) * decay + np.float32(-70.0 * (1 - decay))) + np.float32(x)
        vbar += (float(v) - vbar) / 500.0
        if v >= vbar + 20.0 and t - last > 2:
            ref.append(t)
            v, last = np.float32(-65.0), t
    assert got == ref and len(got) > 5


def test_threshold_tracks_a_steady_drive_and_quiet_keeps_it():
    cell = LIF("c", 1, d_max=1, acc_tau=200.0)
    drive(cell, np.full(4000, 0.6))  # steady 12 mV above rest, never reaches a fixed threshold
    assert abs((cell.threshold()[0] - cell.v_th) - (cell.vbar[0] + 70.0)) < 1e-9
    assert 11.0 < cell.vbar[0] + 70.0 < 12.5
    vbar = cell.vbar.copy()
    cell.quiet()
    assert np.array_equal(cell.vbar, vbar) and cell.v[0] == -70.0


def test_written_cells_keep_half_of_their_items_eligible_inputs():
    # P2-E1 review F1: toggling leaves a written cell's own eligible inputs strong with p 0.5,
    # whatever later plateaus do, so cue synapses do not grow with the cell's plateau count.
    e = e2.E2(dict(SMALL, f_q=0.05), 4)
    e.learn(150)
    n = e.c["n"]
    fr = []
    for item, A in zip(e.items, e.A):
        if A.size:
            hits = np.isin((item[:, None] * n + A[None, :]).ravel(), e.store.keys)
            fr.append(hits.mean())
    assert abs(np.mean(fr) - 0.5 * 0.986) < 0.03


def test_random_store_keeps_each_cells_count_and_moves_inputs():
    e = e2.E2(SMALL, 5)
    e.learn(40)
    counts, keys = e.store.per_post_count().copy(), e.store.keys.copy()
    e.randomise_store()
    assert np.array_equal(counts, e.store.per_post_count())
    assert np.isin(e.store.keys, keys).mean() < 0.2 and np.all(np.diff(e.store.keys) > 0)


def test_small_calibration_and_seed_run_write_complete_records(run_dir):
    out = run_dir / "r.jsonl"
    J_star, ok = e2.calibrate(SMALL, seed=0, grid=(1.4, 2.4), loads=(30, 60), results_path=out, log=lambda m: None)
    rec = e2.run_seed(SMALL, 7, 1.6, gated=True, results_path=out, log=lambda m: None, loads=(30, 60), gate_loads=(30, 60))
    rows = [json.loads(l) for l in out.read_text().splitlines()]
    kinds = [r["kind"] for r in rows]
    assert kinds.count("calibration_point") == 4 and "calibration_verdict" in kinds and "kill_test_seed" in kinds
    v = rec["validity"]
    assert v["weights_unchanged"] and v["store_equals_p2e1"]
    for k in ("main", "fixed_threshold", "random_store", "after_60s", "repeated_cue", "cue_synapses", "offsets"):
        assert k in rec["loads"]["60"]
    assert len(rec["loads"]["60"]["repeated_cue"]) == e2.REPEATS
