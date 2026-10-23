"""P2-E8 driver tests, written from docs/plant2/P2-E8-graded-error-eligibility.md before the driver exists.

Outputs, if any, go through the run_dir fixture only. Every test learns at most 20 small
episodes, so none is marked slow.
"""
import json
import re

import numpy as np
import pytest

from analysis import offline_screens_20261022 as osx
from plant2 import record
from plant2.btsp import BinarySynapses
from plant2.engine import LIF, GlobalInhibition, Projection
from plant2.experiments import p2_e1_btsp as e1
from plant2.experiments import p2_e3_completion as e3
from plant2.experiments import p2_e5_structured as e5
from plant2.experiments import p2_e7_error_gated as e7
from plant2.experiments import p2_e8_graded_error as e8

SEED = 123
EMPTY = np.empty(0, np.int64)


def small():
    return dict(e8.CONTRACT, m=160, n=80, a=8, f_q=.05, n_novel=2)


def tiny():
    return dict(e8.CONTRACT, m=160, n=80, f_q=.05, n_novel=2)


def a64(*xs):
    return np.array(xs, np.int64)


def same_mem(a, b):
    pairs = [(a.mem.v, b.mem.v), (a.mem.vbar, b.mem.vbar), (a.mem.ring, b.mem.ring), (a.mem.t_last, b.mem.t_last)]
    return all(np.array_equal(x, y) for x, y in pairs)


# ---------------------------------------------------------------- module constants

def test_module_constants_follow_the_frozen_json():
    on_disk = json.loads((record.REPO / "docs/plant2/P2-E8-frozen.json").read_text())
    assert e8.FROZEN == on_disk and e8.FROZEN["experiment"] == "P2-E8"
    assert dict(e8.CONTRACT) == dict(e5.CONTRACT)
    assert tuple(e8.LOADS) == (500, 1000)
    assert e8.ARMS == on_disk["arms"]
    assert re.fullmatch(r"[0-9a-f]{7,40}", e8.FROZEN_JSON_COMMIT)
    assert str(e8.ACCEPTANCE_PATH).endswith("docs/plant2/P2-E8-acceptance.json")


# ---------------------------------------------------------------- graded weights and budget

def test_graded_weights_hand_values():
    E, G = a64(2, 5, 7, 9), a64(5, 9, 11)          # 11 is outside E and must not matter
    w = e8.graded_weights(E, G, np.array([5.0, 30.0, 20.0, 0.0]))
    assert np.asarray(w).tolist() == [0.75, 0.0, 0.0, 0.0]   # d over E; G -> 0; d >= 20 clips to 0
    w = e8.graded_weights(a64(1, 2), EMPTY, np.array([0.0, 10.0]))
    assert np.asarray(w).tolist() == [1.0, 0.5]


def test_graded_p_uncapped_case_sums_to_half_of_E():
    E, G = np.arange(6, dtype=np.int64), a64(0)
    d = np.array([0.0, 0.0, 0.0, 10.0, 10.0, 10.0])      # w = [0, 1, 1, .5, .5, .5], sum 3.5, budget 3
    p, lam, capped, n1 = e8.graded_p(E, G, d)
    assert p[0] == 0.0 and p[1] == p[2] == pytest.approx(3 / 3.5) and p[3:].tolist() == pytest.approx([1.5 / 3.5] * 3)
    assert float(np.sum(p)) == pytest.approx(3.0, abs=1e-12) and lam == pytest.approx(3 / 3.5)
    assert capped is False and n1 == 0


def test_graded_p_cap_flag_at_equality_below_and_above():
    E, G = np.arange(10, dtype=np.int64), EMPTY
    for n_pos, flag in ((4, True), (5, True), (6, False)):
        d = np.where(np.arange(10) < n_pos, 0.0, 20.0)    # n_pos lines with w = 1, the rest w = 0
        p, _, capped, n1 = e8.graded_p(E, G, d)
        assert capped is flag
        if flag:
            assert p.tolist() == [1.0] * n_pos + [0.0] * (10 - n_pos)
        else:
            assert p.max() < 1.0
        assert n1 == 0                                     # a capped episode logs no n_p_eq_1
    p, _, capped, _ = e8.graded_p(E, G, np.where(np.arange(10) < 6, 0.0, 20.0))
    assert p[:6].tolist() == pytest.approx([5 / 6] * 6)


def test_graded_p_counts_p_equal_one_lines_on_uncapped_episodes():
    E, G = np.arange(10, dtype=np.int64), EMPTY
    d = np.array([0.0] + [19.8] * 9)                       # w = [1, .01 x 9]; budget 5 saturates line 0 only
    p, lam, capped, n1 = e8.graded_p(E, G, d)
    assert capped is False and n1 == 1 and p[0] == 1.0
    assert p[1:].tolist() == pytest.approx([4 / 0.09 * 0.01] * 9)
    assert float(np.sum(p)) == pytest.approx(5.0, abs=1e-12)


def test_graded_p_degenerate_episodes():
    E = np.arange(8, dtype=np.int64)
    p, _, capped, n1 = e8.graded_p(E, E, np.zeros(8))      # every line predicted: nothing toggles
    assert not p.any() and capped is False and n1 == 0
    p, _, capped, n1 = e8.graded_p(E, EMPTY, np.full(8, 20.0))   # every w is 0 without a spike
    assert not p.any() and capped is False and n1 == 0
    p, _, capped, n1 = e8.graded_p(EMPTY, EMPTY, np.empty(0))
    assert p.size == 0 and capped is False and n1 == 0
    p, lam, capped, n1 = e8.graded_p(E, EMPTY, np.zeros(8))      # empty store: w = 1, p = .5, lambda = .5
    assert p.tolist() == [.5] * 8 and lam == .5 and capped is False and n1 == 0


CASES = [(s, hi) for s in range(5) for hi in (25.0, 20.5)]


@pytest.mark.parametrize("seed, hi", CASES)
def test_graded_p_equals_the_offline_reference_and_its_invariants(seed, hi):
    r = np.random.default_rng(seed)
    E = np.sort(r.choice(200, 30, replace=False)).astype(np.int64)
    G = np.sort(np.concatenate((r.choice(E, 6, replace=False), a64(300, 301))))
    d = r.uniform(0.0, hi, E.size)
    d[np.isin(E, G)] = 20.0 + r.uniform(0, 3, int(np.isin(E, G).sum()))   # spikers sit above threshold
    p, lam, capped, n1 = e8.graded_p(E, G, d)
    w = np.asarray(e8.graded_weights(E, G, d))
    assert np.array_equal(p, osx.counterfactual_p(E, G, d, "graded"))
    assert np.array_equal(p, osx.water_fill(w, .5 * E.size)[0])
    assert (p[np.isin(E, G)] == 0).all() and (p[w == 0] == 0).all() and p.max() <= 1.0
    n_pos = int((w > 0).sum())
    assert capped == (0 < n_pos <= .5 * E.size)
    if n_pos > .5 * E.size:
        assert float(p.sum()) == pytest.approx(.5 * E.size, abs=1e-9)
        assert n1 == int((p == 1.0).sum())
    elif n_pos:
        assert (p[w > 0] == 1.0).all() and n1 == 0


def test_binary_weights_reproduce_the_p2_e7_veto_probability_bit_exactly():
    r = np.random.default_rng(9)
    for n_keep in (30, 17, 12, 8, 3):                      # |E| = 30; the last three hit and pass the cap
        E = np.sort(r.choice(200, 30, replace=False)).astype(np.int64)
        G = np.sort(r.choice(E, 30 - n_keep, replace=False))
        p, _, capped, _ = e8.graded_p(E, G, np.zeros(E.size))      # d = 0 off G, so w in {0, 1}
        keep = ~np.isin(E, G)
        want = e7.veto_probability(E.size, n_keep)
        assert (p[keep] == want).all() and (p[~keep] == 0).all()
        assert capped == (want == 1.0)
        mask_ref = e7.gated_flip_mask(np.full((E.size, 1), .7), keep, want)
        assert np.array_equal(p[:, None] > .7, mask_ref)


# ---------------------------------------------------------------- control weight assignments

def test_shuffled_w_follows_the_stream_37_permutation_on_ascending_E_prime():
    E, G = np.arange(0, 20, dtype=np.int64), a64(3, 8, 9)
    w_all = np.random.default_rng(1).uniform(.05, 1.0, E.size)
    w_all[np.isin(E, G)] = 0.0
    for k in (1, 6):
        got = np.asarray(e8.shuffled_w(w_all, E, G, SEED, k))
        Ep = E[~np.isin(E, G)]
        pi = e1.stream(SEED, 37, k).permutation(Ep.size)
        want = np.zeros(E.size)
        for i, line in enumerate(Ep):
            want[line] = w_all[Ep[pi[i]]]
        assert np.array_equal(got, want)
        assert np.array_equal(got, np.asarray(e8.shuffled_w(w_all, E, G, SEED, k)))
        assert (got[np.isin(E, G)] == 0).all()
    assert not np.array_equal(e8.shuffled_w(w_all, E, G, SEED, 1), e8.shuffled_w(w_all, E, G, SEED, 2))


def test_shuffled_w_preserves_the_multiset_of_p_bit_exactly_and_handles_empty_E_prime():
    r = np.random.default_rng(2)
    E = np.sort(r.choice(200, 40, replace=False)).astype(np.int64)
    G = np.sort(r.choice(E, 9, replace=False))
    d = r.uniform(0, 19, E.size)
    w = np.asarray(e8.graded_weights(E, G, d))
    p0 = osx.water_fill(w, .5 * E.size)[0]
    p1 = osx.water_fill(np.asarray(e8.shuffled_w(w, E, G, SEED, 4)), .5 * E.size)[0]
    assert np.array_equal(np.sort(p0), np.sort(p1)) and not np.array_equal(p0, p1)
    assert not np.asarray(e8.shuffled_w(np.zeros(E.size), E, E, SEED, 1)).any()


def test_history_rank_w_hand_example_with_ties_going_to_the_lower_line_id():
    E, G = np.arange(6, dtype=np.int64), a64(1)
    w = np.array([.9, 0.0, .2, .5, .7, .1])
    H = np.array([3, 9, 3, 7, 0, 3], np.int64)             # E' order by H desc, id asc: 3, 0, 2, 5, 4
    got = np.asarray(e8.history_rank_w(w, E, G, H))
    assert got.tolist() == [.2, 0.0, .5, .1, .9, .7]       # ascending w {.1 .2 .5 .7 .9} in that order
    assert np.array_equal(got, np.asarray(e8.history_rank_w(w, E, G, H)))


def test_history_rank_w_preserves_the_multiset_of_p_bit_exactly_and_ignores_input_order_of_w():
    r = np.random.default_rng(5)
    E = np.sort(r.choice(200, 40, replace=False)).astype(np.int64)
    G = np.sort(r.choice(E, 9, replace=False))
    H = r.integers(0, 6, 200).astype(np.int64)            # many ties
    w = np.asarray(e8.graded_weights(E, G, r.uniform(0, 19, E.size)))
    out = np.asarray(e8.history_rank_w(w, E, G, H))
    p0 = osx.water_fill(w, .5 * E.size)[0]
    p1 = osx.water_fill(out, .5 * E.size)[0]
    assert np.array_equal(np.sort(p0), np.sort(p1))
    Ep = E[~np.isin(E, G)]
    order = sorted(range(Ep.size), key=lambda i: (-H[Ep[i]], Ep[i]))
    ranked = out[~np.isin(E, G)][order]
    assert (np.diff(ranked) >= 0).all()                    # the most-used line gets the smallest w
    assert (out[np.isin(E, G)] == 0).all()


# ---------------------------------------------------------------- lockstep

def random_case(seed, m=64, n=32):
    r = np.random.default_rng(seed)
    fb = BinarySynapses(n, m)
    cells, lines = np.nonzero(r.random((n, m)) < .3)
    fb.add(cells * m + lines)
    raster = {t: np.flatnonzero(r.random(n) < (.15 if t < 50 else .02)).astype(np.int64) for t in range(75)}
    return raster, fb, m


@pytest.mark.parametrize("seed", [11, 12, 13])
def test_lockstep_predict_equals_predict_set_and_the_offline_lockstep(seed):
    raster, fb, m = random_case(seed)
    keys = fb.keys.copy()
    spikes, dmax = e8.lockstep_predict(raster, fb, m)
    assert 0 < len(spikes) < m
    assert np.array_equal(np.sort(np.asarray(spikes)), e7.predict_set(raster, fb, m))
    indptr, post = fb.csr()
    ref_spikes, ref_dmax = osx.lockstep_rec(raster, indptr, post, m)
    assert np.array_equal(np.sort(np.asarray(spikes)), np.sort(ref_spikes))
    assert np.asarray(dmax).shape == (m,) and np.array_equal(np.asarray(dmax), ref_dmax)
    fired = np.isin(np.arange(m), spikes)
    assert (np.asarray(dmax)[fired] >= 20.0).all() and (np.asarray(dmax)[~fired] < 20.0).all()
    assert np.array_equal(fb.keys, keys)


def test_lockstep_predict_reads_the_drive_before_reset_and_is_zero_on_an_empty_store():
    n, m = 8, 4
    store = BinarySynapses(n, m)
    store.add(np.arange(n, dtype=np.int64) * m)            # eight cells all wired to line 0: 22.4 mV at tick 1
    raster = {0: np.arange(n, dtype=np.int64)}
    spikes, dmax = e8.lockstep_predict(raster, store, m)
    assert list(np.asarray(spikes)) == [0] and 22.0 <= dmax[0] <= 22.5
    spikes, dmax = e8.lockstep_predict(raster, BinarySynapses(n, m), m)
    assert len(spikes) == 0 and not np.asarray(dmax).any()
    spikes, dmax = e8.lockstep_predict({}, store, m)
    assert len(spikes) == 0 and not np.asarray(dmax).any()


# ---------------------------------------------------------------- learners

def test_make_learner_returns_the_contract_classes():
    cfg = tiny()
    binary = e8.make_learner(cfg, SEED, "binary", "F10")
    assert type(binary) is e7.E7 and binary.arm == "candidate" and binary.condition == "F10"
    oracle = e8.make_learner(cfg, SEED, "label_oracle", "F10")
    assert type(oracle) is e7.E7 and oracle.arm == "label_oracle"
    assert type(e8.make_learner(cfg, SEED, "baseline", "mixed")) is e7.Baseline
    for arm in ("graded", "gate_off", "graded_shuffled", "history_rank", "surplus_only"):
        e = e8.make_learner(cfg, SEED, arm, "F10")
        assert type(e) is e8.E8 and e.arm == arm and isinstance(e, e3.E3)
    assert type(e8.make_learner(cfg, SEED, "graded", "independent")) is e8.E8


@pytest.mark.parametrize("arm", ["baseline", "binary", "label_oracle", "candidate", "random_drop", "nope"])
def test_e8_refuses_arms_that_belong_to_other_classes(arm):
    with pytest.raises(ValueError):
        e8.E8(tiny(), SEED, arm, "F10")


def test_gate_off_reproduces_the_baseline_trajectory_and_state():
    cfg = small()
    base, off = e7.Baseline(cfg, SEED, "independent"), e8.E8(cfg, SEED, "gate_off", "independent")
    base.learn(8)
    off.learn(8)
    assert base.store.size > 0
    assert np.array_equal(off.store.keys, base.store.keys)
    assert np.array_equal(off.fb.keys, base.fb.keys)
    assert all(np.array_equal(x, y) for x, y in zip(off.R, base.R))
    assert same_mem(off, base)
    for stream in ("_learn_in", "_plat", "_coin"):
        assert getattr(off, stream).random() == getattr(base, stream).random()
    assert len(off.gate_log) == len(off.dmax_log) == 8 and off.episodes == 8
    for g in off.gate_log:
        assert g["tv_mean_abs_dev_from_half"] == 0.0 and g["p_capped"] is False


def test_graded_with_an_empty_feedback_store_flips_the_baseline_keys():
    for condition, cfg in (("F10", tiny()), ("independent", small())):
        base, gr = e7.Baseline(cfg, SEED, condition), e8.E8(cfg, SEED, "graded", condition)
        base.learn(1)
        gr.learn(1)
        assert base.store.size > 0
        assert np.array_equal(gr.store.keys, base.store.keys)
        assert same_mem(gr, base)                          # no rec -> mem path
        g = gr.gate_log[0]
        assert (g["G_size"], g["V_size"], g["lambda"], g["p_capped"], g["Eprime_empty"], g["n_p_eq_1"]) == (0, 0, .5, False, False, 0)
        assert g["tv_mean_abs_dev_from_half"] == 0.0 and g["E_size"] == len(gr.E[0])
        assert not np.asarray(gr.dmax_log[0]).any() and len(gr.dmax_log[0]) == len(gr.E[0])


ARMS8 = ["graded", "gate_off", "graded_shuffled", "history_rank", "surplus_only"]


@pytest.mark.parametrize("arm", ARMS8)
def test_exactly_E_times_A_coins_are_drawn_per_episode(arm):
    e = e8.E8(tiny(), SEED, arm, "F10")
    e.learn(6)
    ref = e1.stream(SEED, e1.COIN)
    ref.random(sum(len(E) * len(A) for E, A in zip(e.E, e.A)))
    assert e._coin.random() == ref.random()


def fb_before(e, k):
    store = BinarySynapses(e.c["n"], e.c["m"])
    for j in range(k):
        store.add((e.R[j][:, None] * e.c["m"] + e.E[j][None, :]).ravel())
    return store


def reference(e, arm):
    """Rebuild the forward store and the per-episode p from the learner's persisted episodes and the public helpers."""
    c = e.c
    store = BinarySynapses(c["m"], c["n"])
    coin = e1.stream(SEED, e1.COIN)
    H = np.zeros(c["m"], np.int64)
    rows = []
    for k in range(len(e.E)):
        E, A = e.E[k], e.A[k]
        spikes, dmax = e8.lockstep_predict(e.encoding_rasters[k], fb_before(e, k), c["m"])
        G, d = np.asarray(spikes, np.int64), np.asarray(dmax)[E]
        w = np.asarray(e8.graded_weights(E, G, d))
        if arm == "gate_off":
            p = np.full(E.size, .5)
        elif arm == "surplus_only":
            p = osx.counterfactual_p(E, G, d, "surplus_only")
        else:
            if arm == "graded_shuffled":
                w = np.asarray(e8.shuffled_w(w, E, G, SEED, k + 1))
            elif arm == "history_rank":
                w = np.asarray(e8.history_rank_w(w, E, G, H))
            p = osx.water_fill(w, .5 * E.size)[0]
        coins = coin.random(E.size * A.size).reshape(E.size, A.size) if E.size and A.size else np.empty((E.size, A.size))
        mask = coins < p[:, None]
        store.toggle((E[:, None] * c["n"] + A[None, :])[mask])
        H[E] += 1
        rows.append((E, G, d, p))
    return store, H, rows


@pytest.mark.parametrize("arm", ARMS8)
def test_each_arm_applies_its_rule_to_the_btsp_coins(arm):
    e = e8.E8(tiny(), SEED, arm, "F10")
    e.learn(8)
    assert e.episodes == 8 and len(e.gate_log) == 8 and len(e.dmax_log) == 8
    store, H, rows = reference(e, arm)
    assert store.size > 0 and np.array_equal(e.store.keys, store.keys)
    assert e.H.dtype == np.int64 and np.array_equal(e.H, H)          # H updated after the write
    for k, (E, G, d, p) in enumerate(rows):
        assert np.array_equal(np.asarray(e.dmax_log[k]), d)
        assert e.gate_log[k]["G_size"] == G.size and e.gate_log[k]["V_size"] == np.isin(E, G).sum()
        assert (p[np.isin(E, G)] == 0).all() or arm == "gate_off"


def test_graded_gate_log_fields_match_the_reference_definitions():
    cfg = tiny()
    e = e8.E8(cfg, SEED, "graded", "F10")
    e.learn(8)
    gen = e5.FamilyGen(SEED, cfg["m"], cfg["a"], 60, 10)
    _, _, rows = reference(e, "graded")
    seen_proto = False
    for k, (E, G, d, p) in enumerate(rows):
        g = e.gate_log[k]
        P = gen.protos[(k + 1) % 10]
        in_P = np.isin(E, P)
        _, lam, capped, n1 = e8.graded_p(E, G, d)
        pb = osx.counterfactual_p(E, G, d, "binary")
        assert g["expected_proto_flips"] == pytest.approx(float(p[in_P].sum()))
        assert g["expected_nonproto_flips"] == pytest.approx(float(p[~in_P].sum()))
        assert g["expected_proto_flips_binary_cf"] == pytest.approx(float(pb[in_P].sum()))
        assert g["tv_mean_abs_dev_from_half"] == pytest.approx(float(np.abs(p - .5).mean()) if E.size else 0.0)
        assert (g["p_capped"], g["n_p_eq_1"]) == (capped, n1)
        assert g["Eprime_empty"] == bool(E.size and np.isin(E, G).all())
        if capped is False and E.size and not g["Eprime_empty"]:
            assert g["lambda"] == pytest.approx(lam)
        unpred = in_P & ~np.isin(E, G)
        if unpred.any():
            seen_proto = True
            assert g["w_mean_proto_unpredicted"] == pytest.approx(float(np.asarray(e8.graded_weights(E, G, d))[unpred].mean()))
    assert seen_proto


def test_mixed_graded_logs_the_subset_of_every_episode():
    e = e8.E8(tiny(), SEED, "graded", "mixed")
    e.learn(4)
    assert [g["subset"] for g in e.gate_log] == ["F10", "independent", "F10", "independent"]


def test_persisted_per_episode_evidence_is_consistent_with_learning():
    cfg = tiny()
    e = e8.E8(cfg, SEED, "graded", "F10")
    e.learn(5)
    assert len(e.encoding_rasters) == len(e.cont_counts) == len(e.dmax_log) == 5
    for k in range(5):
        assert set(e.encoding_rasters[k]) <= set(range(75))
        assert np.array_equal(np.flatnonzero(e.cont_counts[k]), e.R[k])
    for g in e.gate_log:
        assert {"E_size", "G_size", "V_size", "p_capped", "Eprime_empty", "veto_proto_fraction", "proto_predicted",
                "nonproto_predicted", "subset", "expected_proto_flips", "expected_nonproto_flips",
                "expected_proto_flips_binary_cf", "w_mean_proto_unpredicted", "w_mean_nonproto_unpredicted",
                "tv_mean_abs_dev_from_half", "lambda", "n_p_eq_1"} <= set(g)


# ---------------------------------------------------------------- structural fields and kills

def entry(V=0, E=100, capped=False, empty=False, vpf=None, pp=None, npp=None, subset="F10",
          ep=1.0, cf=2.0, tv=.1, lam=.5, n1=0):
    return dict(E_size=E, G_size=V, V_size=V, p=.5, p_capped=capped, Eprime_empty=empty, veto_proto_fraction=vpf,
                proto_predicted=pp, nonproto_predicted=npp, subset=subset, expected_proto_flips=ep,
                expected_proto_flips_binary_cf=cf, tv_mean_abs_dev_from_half=tv, **{"lambda": lam}, n_p_eq_1=n1)


class Log:
    def __init__(self, log):
        self.gate_log, self.episodes = log, len(log)


def f10_log():
    log = []
    for k in range(1000):
        if k < 300:
            log.append(entry(V=4, vpf=.9, pp=.1, npp=.5, ep=4.0, cf=5.0, tv=.16, lam=.4))
        elif k < 500:
            log.append(entry(V=4, vpf=.9, pp=.1, npp=.5, ep=9.0, cf=9.0, tv=.5, lam=.4))
        else:
            log.append(entry(V=20, vpf=.9, pp=.6, npp=.05, ep=1.0, cf=4.0, tv=.03, lam=.6))
    for k in (10, 20, 30, 700):
        log[k]["p_capped"] = True
    for k in (40, 800):
        log[k]["n_p_eq_1"] = 1
    return log


def test_graded_structural_fields_window_means_and_counts():
    f = e8.graded_structural_fields(Log(f10_log()), "F10")
    assert f["expected_proto_flips_1_300"] == pytest.approx(4.0)
    assert f["expected_proto_flips_binary_cf_1_300"] == pytest.approx(5.0)
    assert f["expected_proto_flips_501_1000"] == pytest.approx(1.0)
    assert f["expected_proto_flips_binary_cf_501_1000"] == pytest.approx(4.0)
    assert f["tv_mean_1_300"] == pytest.approx(.16) and f["tv_mean_501_1000"] == pytest.approx(.03)
    assert f["lambda_mean"] == pytest.approx((300 * .4 + 200 * .4 + 500 * .6) / 1000)
    assert f["p_capped_episodes"] == 4 and f["n_p_eq_1_episodes"] == 2
    assert f["mean_V_501_1000"] == pytest.approx(20.0) and f["veto_precision_501_1000"] == pytest.approx(.9)
    assert f["proto_predicted_501_1000"] == pytest.approx(.6) and f["max_V"] == 20      # P2-E7's fields are kept


def good_fields(**kw):
    base = dict(mean_V_1_500=1.0, mean_V_501_1000=25.0, veto_precision_501_1000=.9, proto_predicted_501_1000=.6,
                nonproto_predicted_501_1000=.05, veto_episode_fraction=.5, veto_episode_fraction_501_1000=.5,
                veto_episode_fraction_independent_subset=None, veto_episode_fraction_independent_subset_501_1000=None,
                max_V=40, empty_Eprime_episodes=[], p_capped_episodes=0, first_engagement_by_family={},
                expected_proto_flips_1_300=4.0, expected_proto_flips_binary_cf_1_300=5.0,
                expected_proto_flips_501_1000=1.0, expected_proto_flips_binary_cf_501_1000=4.0,
                tv_mean_1_300=.16, tv_mean_501_1000=.03, lambda_mean=.5, n_p_eq_1_episodes=0)
    return dict(base, **kw)


def kills(fields, condition="F10", ref=None):
    return e8.graded_structural_kills(fields, condition, reference_tv_1_300=ref)


@pytest.mark.parametrize("override, rule", [
    (dict(mean_V_501_1000=4.9), "no engagement"),
    (dict(veto_precision_501_1000=.69), "contamination-driven veto"),
    (dict(nonproto_predicted_501_1000=.26), "saturated teacher"),
    (dict(proto_predicted_501_1000=.24), "no structure"),
    (dict(expected_proto_flips_501_1000=2.5, expected_proto_flips_binary_cf_501_1000=4.0), "no graded reduction"),
    (dict(expected_proto_flips_501_1000=0.0, expected_proto_flips_binary_cf_501_1000=0.0), "no graded reduction"),
])
def test_each_f10_structural_rule_fires_alone(override, rule):
    assert kills(good_fields(**override)) == [rule]


def test_graded_reduction_ratio_at_exactly_the_threshold_does_not_fire():
    assert kills(good_fields(expected_proto_flips_501_1000=2.4, expected_proto_flips_binary_cf_501_1000=4.0)) == []
    assert kills(good_fields()) == []
    assert kills(good_fields(mean_V_501_1000=5.0, veto_precision_501_1000=.7, nonproto_predicted_501_1000=.25,
                             proto_predicted_501_1000=.25)) == []


def test_independent_perturbation_compares_with_the_supplied_f10_reference():
    assert kills(good_fields(tv_mean_501_1000=.17), "independent", ref=.16) == ["independent perturbation"]
    assert kills(good_fields(tv_mean_501_1000=.16), "independent", ref=.16) == []
    assert kills(good_fields(tv_mean_501_1000=.029), "independent", ref=.161) == []
    # the F10-only rules are scoped to F10
    bad = good_fields(expected_proto_flips_501_1000=4.0, mean_V_501_1000=0.0)
    assert kills(bad, "independent", ref=.16) == []


def test_false_engagement_rules_apply_to_their_own_condition_only():
    both = dict(veto_episode_fraction=.06, veto_episode_fraction_501_1000=.06)
    assert kills(good_fields(**both), "independent", ref=.16) == ["false engagement"]
    ok = dict(veto_episode_fraction=.05, veto_episode_fraction_501_1000=.05)
    assert kills(good_fields(**ok), "independent", ref=.16) == []
    mixed = dict(veto_episode_fraction_independent_subset=.06, veto_episode_fraction_independent_subset_501_1000=.06)
    assert kills(good_fields(**mixed), "mixed", ref=.16) == ["false engagement, mixed"]
    assert kills(good_fields(**mixed), "independent", ref=.16) == []
    assert kills(good_fields(), "mixed", ref=.16) == []


# ---------------------------------------------------------------- seed guard

D = "d1" * 32
MANIFEST = dict(code_sha256=D)
ACC = dict(question="f", accepted=True, by="owner", date="2026-10-23", source="DECISIONS.md 2026-10-23")


def passing(seed, digest=D):
    return dict(kind="seed_screen", seed=seed, full_size=True, attempt=f"a{seed}", source=dict(code_sha256=digest),
                screen=dict(verdict="FEASIBILITY PASS", failed=[], missing=[]))


def ready(digest=D, predictions=None):
    return dict(kind="gate_ready", source=dict(code_sha256=digest),
                predictions=e8.FROZEN["predictions"] if predictions is None else predictions)


def started(seed, full=True):
    return dict(kind="seed_started", seed=seed, full_size=full, attempt=f"s{seed}")


def guard(seed, committed, existing, acceptance=ACC):
    return e8.seed_guard(seed, MANIFEST, committed, existing, acceptance=acceptance)


def refused(seed, committed, existing, acceptance=ACC):
    with pytest.raises(ValueError) as info:
        guard(seed, committed, existing, acceptance)
    assert str(info.value)


def test_seed_guard_refuses_every_seed_outside_the_registry():
    for seed in (0, 101, 121, 122, 131, 150, 156, 999):
        refused(seed, [passing(123), passing(124), ready()], [])


def test_seed_guard_opens_development_and_refuses_a_repeat_full_size_attempt():
    assert "stage" in guard(123, [], [])
    assert "stage" in guard(123, [], [started(123, full=False)])
    refused(123, [], [started(123)])
    refused(124, [passing(123)], [started(124)])
    refused(151, [passing(123), passing(124), ready()], [started(151)])


@pytest.mark.parametrize("seed, committed", [
    (123, []), (124, [passing(123)]), (151, [passing(123), passing(124), ready()])])
def test_every_full_size_seed_needs_the_owners_acceptance(seed, committed):
    assert "stage" in guard(seed, committed, [])
    refused(seed, committed, [], acceptance=None)
    refused(seed, committed, [], acceptance={})
    refused(seed, committed, [], acceptance=dict(ACC, accepted=False))
    refused(seed, committed, [], acceptance=dict(ACC, by="agent"))
    refused(seed, committed, [], acceptance=dict(ACC, question="e"))
    partial = {k: v for k, v in ACC.items() if k != "accepted"}
    refused(seed, committed, [], acceptance=partial)


def test_held_out_seed_needs_a_committed_pass_on_123_with_the_same_source_digest():
    refused(124, [], [])
    refused(124, [passing(123, digest="ee" * 32)], [])
    fail = passing(123)
    fail["screen"] = dict(verdict="FEASIBILITY FAIL", failed=["x"], missing=[])
    refused(124, [fail], [])
    opened = guard(124, [passing(123)], [started(123)])
    assert opened["stage"] != guard(123, [], [])["stage"]


def test_gated_seeds_need_both_passes_and_a_gate_ready_with_the_frozen_predictions():
    committed = [passing(123), passing(124), ready()]
    stages = {s: guard(s, committed, []) for s in (151, 152, 153, 154, 155)}
    assert all("stage" in v for v in stages.values())
    assert stages[151]["stage"] != guard(124, committed, [])["stage"]
    refused(151, [passing(123), ready()], [])
    refused(151, [passing(124), ready()], [])
    refused(151, [passing(123), passing(124)], [])
    refused(151, [passing(123), passing(124), ready(digest="ee" * 32)], [])
    altered = dict(e8.FROZEN["predictions"], independent_delta_max=1)
    refused(151, [passing(123), passing(124), ready(predictions=altered)], [])
    refused(151, [passing(123, digest="ee" * 32), passing(124), ready()], [])


def test_an_invalid_screen_on_any_registry_seed_locks_every_remaining_seed():
    invalid = dict(kind="seed_screen", seed=151, full_size=True, attempt="a151", source=dict(code_sha256=D),
                   screen=dict(verdict="INVALID", failed=[], missing=[]))
    committed = [passing(123), passing(124), ready(), invalid]
    refused(152, committed, [invalid])
    refused(153, committed, [invalid])
    invalid_dev = dict(invalid, seed=123, attempt="a123x")
    refused(124, [invalid_dev, passing(123)], [invalid_dev])


# ---------------------------------------------------------------- screen

GOOD = dict(C1=.98, C2=.96, C3=.99, C4_recall=.95, C4_spurious=.95, joint_index=.95)
SUBSET = dict(C1_count=98, C2_count=97, joint_index_count=96, C4_recall_count=49, C4_spurious_count=49,
              n_cues=100, n_oldest_cues=50)


def make_load(condition, arm, M, **kw):
    load = dict(condition=condition, arm=arm, M=M, index=dict(GOOD), integrity=True,
                content=dict(inherited=dict(joint=.92, D3=.99, D4=.91), assigned_A=dict(joint=.5, D3=.9, D4=.5)),
                protocol=dict(eligibility=True, mean_A_1000=True if M == 1000 else None, settled=True),
                forward_sha256="s" + arm + str(M), feedback_sha256="f" + arm + str(M))
    if arm in ("baseline", "gate_off"):
        load["forward_sha256"] = f"shared{condition}{M}"
    if condition == "mixed":
        load["index_by_subset"] = dict(F10=dict(SUBSET), independent=dict(SUBSET))
        load["content_by_subset"] = dict(independent=dict(joint=.9, joint_count=60))
    load.update(kw)
    return load


F10_1000 = {"baseline": (.65, .75), "binary": (.85, .88), "graded_shuffled": (.85, .88), "history_rank": (.85, .88)}


def good_loads():
    loads = []
    for condition, arms in e8.FROZEN["arms"].items():
        for arm in arms:
            for M in e8.LOADS:
                load = make_load(condition, arm, M)
                if condition == "F10" and M == 1000 and arm in F10_1000:
                    load["index"].update(C2=F10_1000[arm][0], joint_index=F10_1000[arm][1])
                loads.append(load)
    return loads


SANITY = dict(wrong_label=dict(C1=.02), empty_store=dict(responders=0))
STRUCT = dict(F10=[], independent=[], mixed=[])


def run_screen(loads, sanity=None, structural=None, uniform=True, invalid=False):
    return e8.screen(loads, SANITY if sanity is None else sanity, STRUCT if structural is None else structural,
                     uniform, invalid=invalid)


def find(loads, condition, arm, M):
    return next(x for x in loads if (x["condition"], x["arm"], x["M"]) == (condition, arm, M))


def mutated(fn):
    loads = good_loads()
    fn(loads)
    return run_screen(loads)


def idx(arm, **kw):
    return lambda L: find(L, "F10", arm, 1000)["index"].update(**kw)


def test_screen_passes_a_complete_set_and_reports_the_decisive_delta():
    out = run_screen(good_loads())
    assert out["verdict"] == "FEASIBILITY PASS" and out["failed"] == [] and out["missing"] == []
    assert out["delta_C2_vs_binary"] == pytest.approx(.11) and not out.get("informative")
    assert isinstance(out["band"], str) and out["band"]


@pytest.mark.parametrize("name, fn, words", [
    ("C2 vs binary", idx("binary", C2=.93), ("C2", "binary")),
    ("C2 vs shuffled", idx("graded_shuffled", C2=.93), ("C2", "shuffled")),
    ("C2 vs history_rank", idx("history_rank", C2=.93), ("C2", "history_rank")),
    ("C2 vs baseline", idx("baseline", C2=.80), ("C2", "baseline")),
    ("joint vs binary", idx("binary", joint_index=.94), ("joint", "binary")),
    ("joint vs baseline", idx("baseline", joint_index=.90), ("joint", "baseline")),
    ("C1 non-regression F10", lambda L: find(L, "F10", "graded", 500)["index"].update(C1=.90), ("C1",)),
    ("C1 non-regression independent", lambda L: find(L, "independent", "graded", 1000)["index"].update(C1=.90), ("C1",)),
    ("C4_recall non-regression", idx("graded", C4_recall=.90), ("C4",)),
    ("independent C2 non-regression", lambda L: (find(L, "independent", "baseline", 500)["index"].update(C2=.99),
                                                 find(L, "independent", "graded", 500)["index"].update(C2=.94)), ("C2",)),
    ("independent content joint", lambda L: find(L, "independent", "graded", 1000)["content"]["inherited"].update(joint=.80), ("joint",)),
    ("independent content D4", lambda L: find(L, "independent", "graded", 500)["content"]["inherited"].update(D4=.80), ("D4",)),
    ("C3 at F10", lambda L: find(L, "F10", "graded", 500)["index"].update(C3=.89), ("C3",)),
    ("C3 at independent", lambda L: find(L, "independent", "graded", 1000)["index"].update(C3=.89), ("C3",)),
    ("absolute joint bar", lambda L: [find(L, "independent", a, 500)["index"].update(joint_index=.84) for a in ("graded", "baseline")], ("joint",)),
    ("protocol check on mixed", lambda L: find(L, "mixed", "baseline", 500)["protocol"].update(eligibility=False), ()),
    ("protocol check on a control arm", lambda L: find(L, "F10", "graded_shuffled", 1000)["protocol"].update(settled=False), ()),
])
def test_each_kill_rule_gives_feasibility_fail(name, fn, words):
    out = mutated(fn)
    assert out["verdict"] == "FEASIBILITY FAIL", name
    assert out["failed"] and all(any(w in str(f) for f in out["failed"]) for w in words), name


def test_mixed_independent_subset_margins_are_counted_in_cues():
    def set_counts(key, base, graded, where="index_by_subset"):
        def fn(L):
            find(L, "mixed", "baseline", 1000)[where]["independent"][key] = base
            find(L, "mixed", "graded", 1000)[where]["independent"][key] = graded
        return fn
    assert mutated(set_counts("C1_count", 100, 97))["verdict"] == "FEASIBILITY PASS"
    assert mutated(set_counts("C1_count", 100, 96))["verdict"] == "FEASIBILITY FAIL"
    assert mutated(set_counts("C2_count", 100, 97))["verdict"] == "FEASIBILITY PASS"
    assert mutated(set_counts("C2_count", 100, 96))["verdict"] == "FEASIBILITY FAIL"
    assert mutated(set_counts("joint_count", 60, 56, "content_by_subset"))["verdict"] == "FEASIBILITY PASS"
    assert mutated(set_counts("joint_count", 60, 55, "content_by_subset"))["verdict"] == "FEASIBILITY FAIL"


def test_f40_and_the_surplus_only_arm_cannot_fail_the_screen():
    def fn(L):
        for M in e8.LOADS:
            find(L, "F40", "graded", M)["index"].update(C1=.1, C2=.1, C3=.1, joint_index=.1)
        find(L, "F10", "surplus_only", 1000)["index"].update(C2=.1, joint_index=.1)
    assert mutated(fn)["verdict"] == "FEASIBILITY PASS"


def test_sanity_and_structural_failures_fail_the_screen():
    assert run_screen(good_loads(), sanity=dict(wrong_label=dict(C1=.10), empty_store=dict(responders=0)))["verdict"] == "FEASIBILITY FAIL"
    assert run_screen(good_loads(), sanity=dict(wrong_label=dict(C1=.09), empty_store=dict(responders=0)))["verdict"] == "FEASIBILITY PASS"
    assert run_screen(good_loads(), sanity=dict(wrong_label=dict(C1=.02), empty_store=dict(responders=1)))["verdict"] == "FEASIBILITY FAIL"
    out = run_screen(good_loads(), structural=dict(F10=["no graded reduction"], independent=[], mixed=[]))
    assert out["verdict"] == "FEASIBILITY FAIL"


def test_the_boundary_delta_of_exactly_five_points_is_not_a_kill():
    out = mutated(idx("binary", C2=.91))                  # .96 - .91 is .0499999... in floating point
    assert out["verdict"] == "FEASIBILITY PASS" and out["delta_C2_vs_binary"] == pytest.approx(.05)


def band_of(fn=None, structural=None):
    loads = good_loads()
    if fn:
        fn(loads)
    return run_screen(loads, structural=structural)


def test_outcome_bands_distinguish_the_contract_rows():
    passed = band_of()
    informative = band_of(lambda L: (find(L, "F10", "graded", 1000)["index"].update(C2=.88),
                                     find(L, "F10", "binary", 1000)["index"].update(C2=.80),
                                     find(L, "F10", "graded_shuffled", 1000)["index"].update(C2=.80),
                                     find(L, "F10", "history_rank", 1000)["index"].update(C2=.80),
                                     find(L, "F10", "baseline", 1000)["index"].update(C2=.60)))
    control = band_of(idx("graded_shuffled", C2=.93))
    other_kill = band_of(lambda L: find(L, "F10", "graded", 500)["index"].update(C3=.89))
    weakened = band_of(idx("binary", C2=.93))
    refuted = band_of(idx("binary", C2=.95))
    structural = band_of(structural=dict(F10=["no graded reduction"], independent=[], mixed=[]))
    assert informative["verdict"] == "FEASIBILITY FAIL" and informative["informative"] is True
    assert informative["delta_C2_vs_binary"] == pytest.approx(.08)
    assert weakened["delta_C2_vs_binary"] == pytest.approx(.03) and refuted["delta_C2_vs_binary"] == pytest.approx(.01)
    for out in (control, other_kill, weakened, refuted, structural):
        assert out["verdict"] == "FEASIBILITY FAIL" and not out.get("informative")
    assert control["delta_C2_vs_binary"] == pytest.approx(.11)
    bands = [o["band"] for o in (passed, informative, control, weakened, refuted, structural)]
    assert all(isinstance(b, str) and b for b in bands) and len(set(bands)) == 6
    assert other_kill["band"] == control["band"]          # one contract row: delta held, another KILL rule fired


def test_a_missing_arm_is_partial_and_named():
    loads = [x for x in good_loads() if (x["condition"], x["arm"], x["M"]) != ("F10", "graded_shuffled", 1000)]
    out = run_screen(loads)
    assert out["verdict"] == "PARTIAL" and out["failed"] == []
    assert len(out["missing"]) == 1 and "graded_shuffled" in str(out["missing"][0]) and "1000" in str(out["missing"][0])
    no_binary = [x for x in good_loads() if (x["condition"], x["arm"], x["M"]) != ("F10", "binary", 1000)]
    out = run_screen(no_binary)
    assert out["verdict"] == "PARTIAL" and out["delta_C2_vs_binary"] is None
    gone = [x for x in good_loads() if (x["condition"], x["arm"], x["M"]) != ("mixed", "baseline", 500)]
    assert run_screen(gone)["verdict"] == "PARTIAL"


def test_integrity_failures_make_the_screen_invalid():
    assert run_screen(good_loads(), invalid=True)["verdict"] == "INVALID"
    assert run_screen(good_loads(), uniform=False)["verdict"] == "INVALID"
    for M in e8.LOADS:
        loads = good_loads()
        find(loads, "F10", "gate_off", M)["forward_sha256"] = "different"
        assert run_screen(loads)["verdict"] == "INVALID"
    loads = good_loads()
    find(loads, "F10", "graded", 1000)["index"]["C3"] = .5       # a kill, but invalid takes precedence
    assert run_screen(loads, invalid=True)["verdict"] == "INVALID"


# ---------------------------------------------------------------- source manifest

PINNED_E3_ERA = ["plant2/engine.py", "plant2/btsp.py", "plant2/readout.py", "plant2/record.py",
                 "plant2/experiments/p2_e1_btsp.py", "plant2/experiments/p2_e2_accommodation.py",
                 "plant2/experiments/p2_e3_completion.py", "plant2/experiments/p2_e4_online.py",
                 "plant2/experiments/p2_e5_structured.py"]
GROUPS = {"e3_era", "contract_group", "p2_e7_driver_and_riders", "p2_e7_contract_append_only", "p2_e7_frozen_json",
          "offline_screens", "p2_e8_frozen_json", "self"}


def test_source_manifest_carries_every_pin_group_with_its_full_sha():
    m = e8.source_manifest()
    assert isinstance(m["code_sha256"], str) and len(m["code_sha256"]) == 64
    files = m["files"]
    assert GROUPS <= {f["pin"] for f in files.values()}
    for entry_ in files.values():
        assert len(entry_["sha256"]) == 64 and isinstance(entry_["passed"], bool)
    for path in PINNED_E3_ERA:
        assert files[path]["pin"] == "e3_era" and files[path]["rev"] == e8.FROZEN["pins"]["e3_era"]
    for path in ("plant2/experiments/p2_e6.py", "plant2/evidence.py", "analysis/p2r1_replay.py"):
        assert files[path]["pin"] == "contract_group" and files[path]["rev"] == e8.FROZEN["pins"]["contract_group"]
    for path in ("plant2/experiments/p2_e7_error_gated.py", "analysis/p2e7_riders.py"):
        assert files[path]["pin"] == "p2_e7_driver_and_riders" and files[path]["rev"] == e8.FROZEN["pins"]["p2_e7_driver_and_riders"]
    assert files["docs/plant2/P2-E7-frozen.json"]["pin"] == "p2_e7_frozen_json"
    assert files["docs/plant2/P2-E7-frozen.json"]["rev"] == e8.FROZEN["pins"]["p2_e7_frozen_json"]
    assert files["docs/plant2/P2-E7-error-gated-eligibility.md"]["pin"] == "p2_e7_contract_append_only"
    assert files["analysis/offline_screens_20261022.py"]["pin"] == "offline_screens"
    assert files["analysis/offline_screens_20261022.py"]["rev"] == e8.FROZEN["pins"]["offline_screens"]
    assert files["docs/plant2/P2-E8-frozen.json"]["pin"] == "p2_e8_frozen_json"
    assert files["docs/plant2/P2-E8-frozen.json"]["rev"] == e8.FROZEN_JSON_COMMIT
    for path in ("plant2/experiments/p2_e8_graded_error.py", "plant2/tests/test_p2_e8.py", "analysis/p2e8_riders.py"):
        assert files[path]["pin"] == "self"
