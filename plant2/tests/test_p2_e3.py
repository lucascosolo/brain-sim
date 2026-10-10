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


def test_contract_constants_are_the_predeclared_ones():
    assert e3.G == 0.3 and e3.WINDOW == 75 and e3.SHORT == 50 and e3.SPAN == 300
    assert (e3.JOINT_MISSING, e3.JOINT_INTRUSIONS, e3.NOVEL_LINES, e3.FRAC) == (40, 10, 10, 0.90)
    assert e3.J_GRID[0] == 1.0 and e3.J_GRID[-1] == 6.0 and len(e3.J_GRID) == 101
    assert e3.GATE_M == (250, 500, 1000) and e3.GATED_SEEDS == (11, 12, 13, 14, 15) and e3.CAL_SEED == 0
    assert e3.CONTRACT["t_cont"] == 50 and e3.CONTRACT["J"] == 1.525 and e3.CONTRACT["acc_tau"] == 10_000
    assert (e3.CONT, e3.SHUFFLED, e3.PERMUTED) == (9, 10, 11)
    # the memory criteria keep P2-E2's 50 ms window (a collision with the rec window was a bug, fixed before gating)
    assert e3.CONTRACT["window"] == e1.CONTRACT["window"] == 50 and e3.CONTRACT["rec_window"] == 75


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
    e = e3.E3(SMALL, 4)
    e.learn(30)
    plain = e1.E1(SMALL, 4)
    plain.learn(30)
    assert np.array_equal(e.store.keys, plain.store.keys)
    m = SMALL["m"]
    pre, post = e.fb.keys // m, e.fb.keys % m
    for k in range(30):  # every feedback synapse of item k's responders points at an eligible line, never elsewhere
        assert set(e.E[k].tolist()) <= set(post[np.isin(pre, e.R[k])].tolist()) or e.R[k].size == 0


def test_a_silenced_item_line_receives_no_feedback():
    class Silenced(e3.E3):
        def _rates(self, active):
            super()._rates(active)
            if active is not None and len(self.items) == 1:
                self.inp.rate_hz[active[0]] = 0.0
                self.inp.set_rates(self.inp.rate_hz.copy())
    e = Silenced(dict(SMALL, f_q=0.08), 6)
    e.learn(1)
    line = e.items[0][0]
    assert line not in e.E[0]
    assert not np.isin(e.fb.keys % SMALL["m"], [line]).any()


def test_testing_a_copy_leaves_learning_untouched():
    a = e3.E3(SMALL, 7)
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
    rec = e3.run_seed(c, 13, 2.5, 1.5, gated=True, results_path=out, log=lambda m: None, loads=(30, 60),
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
