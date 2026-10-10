import copy
import json

import numpy as np
import pytest

from plant2.btsp import BinarySynapses
from plant2.engine import LIF, GlobalInhibition, Net, Poisson, Projection
from plant2.experiments import p2_e1_btsp as e1
from plant2.experiments import p2_e2_accommodation as e2
from plant2.experiments import p2_e3_completion as e3
from plant2.readout import replay

SMALL = dict(e3.CONTRACT, m=800, n=800, a=40, M=60, n_old=20, n_rand=20, n_novel=20, f_q=0.03, t_gap=100,
             acc_tau=300, settle=1500, converge_window=300)
# for the scoring checks: a=100 so the joint criterion's 40-of-50 bar means what it does in the contract
MID = dict(e3.CONTRACT, m=1500, n=1500, a=100, n_old=20, n_rand=20, n_novel=20, f_q=0.0133, t_gap=200,
           acc_tau=2000, settle=8000, converge_window=2000)
# seeds 90+ belong to no experiment (gated seeds so far: 1-20; exploration: 42-43, 97-99)


def test_contract_constants_are_the_predeclared_ones():
    assert e3.G == 0.3 and e3.WINDOW == 75 and e3.SHORT == 50 and e3.SPAN == 300
    assert (e3.JOINT_MISSING, e3.JOINT_INTRUSIONS, e3.NOVEL_LINES, e3.FRAC) == (40, 10, 10, 0.90)
    assert e3.J_GRID[0] == 1.0 and e3.J_GRID[-1] == 6.0 and len(e3.J_GRID) == 101
    assert e3.GATE_M == (250, 500, 1000) and e3.GATED_SEEDS == (11, 12, 13, 14, 15) and e3.CAL_SEED == 0
    assert e3.CONTRACT["t_cont"] == 50 and e3.CONTRACT["J"] == 1.525 and e3.CONTRACT["acc_tau"] == 10_000
    assert (e3.CONT, e3.SHUFFLED, e3.PERMUTED) == (9, 10, 11)
    # the memory criteria keep P2-E2's 50 ms window (a collision with the rec window was a bug, fixed before gating)
    assert e3.CONTRACT["window"] == e1.CONTRACT["window"] == 50 and e3.CONTRACT["rec_window"] == 75
    # the readout takes its window and span from the config; in the contract config they are WINDOW and SPAN
    assert e3.CONTRACT["rec_window"] == e3.WINDOW and e3.CONTRACT["t_cue"] + e3.CONTRACT["t_gap"] == e3.SPAN


def test_clipped_add_sets_without_toggling():
    s = BinarySynapses(10, 10)
    assert s.add([3, 7, 7, 15]) == 3 and s.add([7, 20]) == 1
    assert s.keys.tolist() == [3, 7, 15, 20]


def test_replay_matches_the_engine_spike_for_spike():
    rng = np.random.default_rng(1)
    src = Poisson("inp", 60)
    src.set_rates(rng.uniform(5, 80, 60))
    mem = LIF("mem", 40, d_max=1)
    rec = LIF("rec", 30, d_max=2)
    J, g = 2.35, 0.3
    keys = np.unique(rng.integers(0, 40 * 30, 300))
    fb = Projection(mem, rec, keys // 30, keys % 30, J, 1)
    net = Net([src], [mem, rec], [Projection(src, mem, rng.integers(0, 60, 900), rng.integers(0, 40, 900), 3.0, 1),
                                  fb, GlobalInhibition(mem, rec, g * J, 2)])
    raster, engine_spikes = {}, []
    for t in range(3000):
        sp = net.step(rng)
        if sp["mem"].size:
            raster[t] = sp["mem"].copy()
        engine_spikes += [(t, 0, int(j)) for j in sp["rec"]]
    assert len(raster) > 200 and len(engine_spikes) > 50
    store = BinarySynapses(40, 30)
    store.keys = keys.astype(np.int64)
    indptr, post = store.csr()
    trace = []
    replay(raster, 3000, indptr, post, 30, np.array([J]), np.array([g]), [], trace=trace)
    assert trace == engine_spikes


def test_replay_arms_are_independent_of_each_other():
    rng = np.random.default_rng(2)
    raster = {t: rng.choice(40, 2, replace=False) for t in range(0, 2000, 3)}
    keys = np.unique(rng.integers(0, 40 * 30, 300))
    store = BinarySynapses(40, 30)
    store.keys = keys.astype(np.int64)
    indptr, post = store.csr()
    together, alone = [], []
    replay(raster, 2000, indptr, post, 30, np.array([1.5, 3.0]), np.array([0.3, 0.0]), [], trace=together)
    replay(raster, 2000, indptr, post, 30, np.array([3.0]), np.array([0.0]), [], trace=alone)
    assert [(t, j) for t, a, j in together if a == 1] == [(t, j) for t, a, j in alone]


def test_forward_store_is_p2e1s_and_feedback_reads_spikes_not_items():
    e = e3.E3(SMALL, 90)
    e.learn(30)
    plain = e1.E1(SMALL, 90)
    plain.learn(30)
    assert np.array_equal(e.store.keys, plain.store.keys)
    m = SMALL["m"]
    # the feedback store is exactly the union of responders x eligible lines; the plateau-set store uses A instead
    union = lambda cells: np.unique(np.concatenate([(cells[k][:, None] * m + e.E[k][None, :]).ravel() for k in range(30)]))
    assert np.array_equal(e.fb.keys, union(e.R)) and np.array_equal(e.fb_plateau.keys, union(e.A))
    assert sum(r.size for r in e.R) > 0 and not all(np.array_equal(r, a) for r, a in zip(e.R, e.A))


def test_a_silenced_item_line_receives_no_feedback():
    class Silenced(e3.E3):
        def _rates(self, active):
            super()._rates(active)
            if active is not None and len(self.items) == 1:
                self.inp.rate_hz[active[0]] = 0.0
                self.inp.set_rates(self.inp.rate_hz.copy())
    e = Silenced(dict(SMALL, f_q=0.08), 91)
    e.learn(1)
    line = e.items[0][0]
    assert line not in e.E[0]
    assert not np.isin(e.fb.keys % SMALL["m"], [line]).any()


def test_testing_a_copy_leaves_learning_untouched():
    a = e3.E3(SMALL, 92)
    a.learn(20)
    b = copy.deepcopy(a)
    e3.run_phase(copy.deepcopy(a), 20)
    a.learn(40)
    b.learn(40)
    assert np.array_equal(a.store.keys, b.store.keys) and np.array_equal(a.fb.keys, b.fb.keys)


def test_small_calibration_and_seed_write_complete_records(run_dir):
    out = run_dir / "r.jsonl"
    c = dict(SMALL, n_old=10, n_rand=10)
    J_star, J0, reread = e3.calibrate(c, seed=0, grid=(1.5, 2.5, 3.5), loads=(30, 60), results_path=out, log=lambda m: None)
    rec = e3.run_seed(c, 93, 2.5, 1.5, gated=True, results_path=out, log=lambda m: None, loads=(30, 60),
                      gate_loads=(30, 60), struct_M=60)
    rows = [json.loads(l) for l in out.read_text().splitlines()]
    kinds = [r["kind"] for r in rows]
    assert kinds.count("calibration_point") == 2 and "calibration_verdict" in kinds and "kill_test_seed" in kinds
    assert rec["validity"]["fwd_equals_p2e1"] and rec["validity"]["stores_unchanged_by_tests"]
    for k in ("main", "matched_g0", "g0_at_J_star", "shuffled", "label_permuted", "plateau_set", "memory"):
        assert k in rec["loads"]["60"]
    assert {"joint", "D1", "D2", "D3", "D4", "hd_ratio", "latency_ms_median"} <= set(rec["loads"]["60"]["main"])


@pytest.mark.slow
def test_p2e2_seed6_m250_point_reproduces(run_dir):
    rows = [json.loads(l) for l in open(e2.record.RESULTS)]
    ref = [r for r in rows if r.get("experiment") == "P2-E2" and r["kind"] == "kill_test_seed" and r["seed"] == 6][0]
    e = e2.E2(dict(e2.CONTRACT, J=1.525), 6)
    e.learn(250)
    e.settle(250, phase=1)
    out = e2.evaluate(e, 250, phase=1)
    assert out["criteria"] == ref["loads"]["250"]["main"]["criteria"]


def _live_and_replayed(cfg, seed, M, J, g, extra=0):
    """One learned network tested twice: rec simulated live inside the engine, and replayed from the raster.

    `extra` ticks of background follow the test phase in both, so spans longer than the cue spacing fit.
    """
    main = e3.E3(cfg, seed)
    main.learn(M)
    live, e = copy.deepcopy(main), copy.deepcopy(main)
    live.settle_drift(M, 1)
    rec = LIF("rec", cfg["m"], d_max=2)
    indptr, post = live.fb.csr()
    live.net.populations.append(rec)
    live.net.projections += [Projection(live.mem, rec, np.repeat(np.arange(cfg["n"]), np.diff(indptr)), post, J, 1),
                             GlobalInhibition(live.mem, rec, g * J, 2)]
    t0, spikes, step = live.net.t, [], live.net.step

    def logged(rng):
        sp = step(rng)
        spikes.extend((live.net.t - 1 - t0, int(j)) for j in sp["rec"])
        return sp
    live.net.step = logged
    live._raster, live._onsets, live._t0 = {}, [], live.net.t
    e2.evaluate(live, M, phase=1)
    out, raster, n_ticks, onsets, _ = e3.run_phase(e, M)
    for net_owner in (live, e):
        net_owner._rates(None)
        rng = np.random.default_rng(94)
        for _ in range(extra):
            net_owner._step(rng)
    assert live.net.t - live._t0 == e.net.t - e._t0 == n_ticks + extra and onsets == live._onsets
    assert raster.keys() == live._raster.keys() and all(np.array_equal(raster[t], live._raster[t]) for t in raster)
    return e, raster, n_ticks + extra, onsets, spikes


@pytest.mark.parametrize("t_gap, span", [(200, 300), (100, 300)])
def test_replay_scoring_matches_the_live_engine_and_brute_force(t_gap, span):
    cfg = dict(MID, t_gap=t_gap)
    J, g, M = 2.8, 0.3, 60
    e, raster, n_ticks, onsets, spikes = _live_and_replayed(cfg, 95, M, J, g, extra=span - cfg["t_cue"] - t_gap)
    cues = e3.build_cues(e, M, onsets)
    indptr, post = e.fb.csr()
    trace = []
    res, lat, _ = replay(raster, n_ticks, indptr, post, cfg["m"], np.array([J]), np.array([g]), cues,
                         window=cfg["rec_window"], short=e3.SHORT, span=span, trace=trace)
    assert [(t, j) for t, _, j in trace] == spikes
    by_t = {}
    for t, j in spikes:
        by_t.setdefault(t, []).append(j)

    def lines(on, w):
        first = {}
        for t in range(on, on + w):
            for j in by_t.get(t, []):
                first.setdefault(j, t - on)
        return first
    joint = []
    for i, c in enumerate(cues):
        f75, f50, fs = lines(c["onset"], cfg["rec_window"]), lines(c["onset"], e3.SHORT), lines(c["onset"], span)
        s75, s50, ss = set(f75), set(f50), set(fs)
        item, miss = set(c["item"].tolist()), set(c["missing"].tolist())
        want = dict(missing=len(s75 & miss), visible=len(s75 & set(c["cue"].tolist())), item=len(s75 & item),
                    total=len(s75), missing_short=len(s50 & miss), item_short=len(s50 & item), total_short=len(s50),
                    total_span=len(ss), item_span=len(ss & item), other_missing=len(s75 & set(c["other_missing"].tolist())))
        assert {k: int(res[k][i, 0]) for k in want} == want, (i, c["kind"])
        if s75 & miss:
            assert np.median([f75[j] for j in s75 & miss]) == lat[i, 0]
        if c["kind"] == "half":
            joint.append(want["missing"] >= e3.JOINT_MISSING and want["total"] - want["item"] < e3.JOINT_INTRUSIONS)
    arm = e3.score(res, lat, cues, cfg["n_old"], 1)[0]
    assert arm["joint"] == np.mean(joint) and arm["D4"] == np.mean(joint[:cfg["n_old"]])
    assert arm["joint"] > 0.5 and res["total_span"][:, 0].sum() > 0  # the check exercised real regeneration


def test_build_cues_match_what_was_presented():
    e = e3.E3(MID, 96)
    e.learn(40)
    shown, rates = [], e._rates
    e._rates = lambda active: (shown.append(np.sort(active)) if active is not None else None, rates(active))[1]
    _, _, n_ticks, onsets, _ = e3.run_phase(e, 40)
    cues = e3.build_cues(e, 40, onsets)
    assert len(shown) == len(cues) and all(np.array_equal(s, np.sort(c["cue"])) for s, c in zip(shown, cues))
    kinds = [c["kind"] for c in cues]
    n_cued = len(e1.test_sets(e.c, e.seed, 40)[0])
    assert kinds == ["half"] * n_cued + ["novel"] * MID["n_novel"] + ["full"] * n_cued
    assert min(np.diff(onsets)) == MID["t_cue"] + MID["t_gap"] and onsets[-1] + MID["t_cue"] + MID["t_gap"] == n_ticks


def test_replay_refuses_layouts_it_cannot_score():
    store = BinarySynapses(10, 10)
    store.keys = np.array([3, 14], np.int64)
    indptr, post = store.csr()
    cue = lambda on: dict(onset=on, item=np.arange(4), cue=np.arange(2), missing=np.arange(2, 4),
                          other_missing=np.empty(0, np.int64))
    one = np.array([2.0])
    replay({}, 600, indptr, post, 10, one, one, [cue(0), cue(200)], window=75, span=300)  # overlapping spans are fine
    with pytest.raises(ValueError):
        replay({}, 600, indptr, post, 10, one, one, [cue(0), cue(50)], window=75, span=300)  # overlapping windows
    with pytest.raises(ValueError):
        replay({}, 400, indptr, post, 10, one, one, [cue(0), cue(200)], window=75, span=300)  # span cut off


@pytest.mark.slow
def test_e3_without_continuation_reproduces_p2e2_seed6_m250():
    rows = [json.loads(l) for l in open(e2.record.RESULTS)]
    ref = [r for r in rows if r.get("experiment") == "P2-E2" and r["kind"] == "kill_test_seed" and r["seed"] == 6][0]
    e = e3.E3(dict(e3.CONTRACT, t_cont=0), 6)
    e.learn(250)
    out, _, _, _, drift = e3.run_phase(e, 250)
    assert out["criteria"] == ref["loads"]["250"]["main"]["criteria"]


@pytest.mark.slow
def test_p2e3_gated_seed11_m250_reproduces():
    rows = [json.loads(l) for l in open(e3.record.RESULTS)]
    ref = [r for r in rows if r.get("experiment") == "P2-E3" and r["kind"] == "kill_test_seed" and r["seed"] == 11
           and r["gated"] and r["contract_digest"] == e3.DIGEST][0]
    main = e3.E3(e3.CONTRACT, 11)
    main.learn(250)
    e = copy.deepcopy(main)
    out, raster, n_ticks, onsets, drift = e3.run_phase(e, 250)
    arms = e3.readout(e, 250, raster, n_ticks, onsets, np.array([ref["J_star"], ref["J0"], ref["J_star"]]),
                      np.array([e3.G, 0.0, 0.0]))
    load = ref["loads"]["250"]
    assert [arms[0], arms[1], arms[2]] == [load["main"], load["matched_g0"], load["g0_at_J_star"]]
    assert json.loads(json.dumps(e3.memory_summary(out))) == load["memory"]  # as recorded (tuples become lists)
    assert list(drift) == [load["converge_mv"], load["drift_signed_mv"]]
