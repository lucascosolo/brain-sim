"""P2-E7 driver tests, written from docs/plant2/P2-E7-error-gated-eligibility.md before the driver exists.

Outputs, if any, go through the run_dir fixture only. Every test learns at most 20 small
episodes, so none is marked slow.
"""
import numpy as np
import pytest

from plant2 import record
from plant2.btsp import BinarySynapses, btsp_update
from plant2.engine import LIF, GlobalInhibition, Projection
from plant2.experiments import p2_e1_btsp as e1
from plant2.experiments import p2_e3_completion as e3
from plant2.experiments import p2_e5_structured as e5
from plant2.experiments import p2_e7_error_gated as e7

SEED = 121
EMPTY = np.empty(0, np.int64)


def small():
    """Small independent-stream configuration (E6's uniform_integrity pattern, a = 8)."""
    return dict(e7.CONTRACT, m=160, n=80, a=8, f_q=.05, n_novel=2)


def tiny():
    """Small F10-capable configuration: a = 100, s = 60 fits in m = 160 (E6's tiny())."""
    return dict(e7.CONTRACT, m=160, n=80, f_q=.05, n_novel=2)


def mem_state(e):
    return [e.mem.v.copy(), e.mem.vbar.copy(), e.mem.ring.copy(), e.mem.t_last.copy()]


def same_mem(a, b):
    return all(np.array_equal(x, y) for x, y in zip(mem_state(a), mem_state(b)))


def test_module_constants_follow_the_contract():
    assert e7.FROZEN["experiment"] == "P2-E7"
    assert dict(e7.CONTRACT) == dict(e5.CONTRACT)
    assert tuple(e7.LOADS) == (500, 1000)


# ---------------------------------------------------------------- mixed generator

def test_mixed_generator_alternates_odd_family_even_independent_with_one_based_keys():
    seed, m, a, s, F = 7, 4000, 100, 60, 10
    gen, fam = e7.MixedGen(seed, m, a, s, F), e5.FamilyGen(seed, m, a, s, F)
    drawn = [gen.choice(m, a, replace=False) for _ in range(6)]
    for k in (1, 3, 5):
        assert np.array_equal(drawn[k - 1], fam.exemplar((k + 1) // 2))
    for k in (2, 4, 6):
        assert np.array_equal(drawn[k - 1], np.sort(e1.stream(seed, 36, k).choice(m, a, replace=False)))
    assert gen.labels == ["F10", "independent"] * 3
    assert [gen.subset(k) for k in range(1, 7)] == gen.labels
    assert all(np.array_equal(x, np.sort(x)) for x in drawn)


def test_mixed_generator_labels_list_only_episodes_issued_so_far():
    gen = e7.MixedGen(7, 160, 100, 60, 10)
    assert gen.labels == []
    gen.choice(160, 100, replace=False)
    assert gen.labels == ["F10"]


# ---------------------------------------------------------------- prediction

def lockstep_lines(raster, fb, m):
    """Independent lockstep: engine.LIF rec population, Projection from the feedback CSR (J 2.8, delay 1),
    GlobalInhibition at g * J = 0.84 mV (delay 2). Memory spikes of tick t are delivered after rec steps."""
    src = LIF("mem", fb.n_pre, d_max=1)
    rec = LIF("rec", m, d_max=2)
    proj = Projection(src, rec, [], [], 2.8, 1)
    indptr, post = fb.csr()
    proj.set_csr(indptr, post, 2.8, 1)
    inh = GlobalInhibition(src, rec, float(np.float64(.3) * np.float64(2.8)), 2)
    lines = set()
    for t in range(75):
        lines.update(int(x) for x in rec.step(t))
        mem = np.asarray(raster.get(t, EMPTY), np.int64)
        proj.deliver(mem, t)
        inh.deliver(mem, t)
    return np.array(sorted(lines), np.int64)


def random_case(seed, m=64, n=32):
    r = np.random.default_rng(seed)
    fb = BinarySynapses(n, m)
    cells, lines = np.nonzero(r.random((n, m)) < .3)
    fb.add(cells * m + lines)
    raster = {t: np.flatnonzero(r.random(n) < (.15 if t < 50 else .02)).astype(np.int64) for t in range(75)}
    return raster, fb, m


@pytest.mark.parametrize("seed", [11, 12, 13])
def test_predict_set_equals_independent_lockstep_implementation(seed):
    raster, fb, m = random_case(seed)
    expected = lockstep_lines(raster, fb, m)
    assert 0 < expected.size < m  # the case exercises both spiking and silent lines
    keys_before = fb.keys.copy()
    got = e7.predict_set(raster, fb, m)
    assert got.dtype == np.int64 and np.array_equal(got, expected)
    assert np.array_equal(fb.keys, keys_before)  # the store is only read


def test_predict_set_handles_empty_store_empty_raster_and_missing_ticks():
    m, n = 64, 32
    raster, fb, _ = random_case(11)
    assert e7.predict_set(raster, BinarySynapses(n, m), m).size == 0
    assert e7.predict_set({}, fb, m).size == 0
    sparse = {t: s for t, s in raster.items() if t % 3 == 0}
    assert np.array_equal(e7.predict_set(sparse, fb, m), lockstep_lines(sparse, fb, m))


# ---------------------------------------------------------------- veto probability and flip mask

def test_veto_probability_budget_cap_and_empty_case():
    assert e7.veto_probability(10, 10) == .5
    assert e7.veto_probability(10, 20) == .25
    assert e7.veto_probability(10, 5) == 1.0          # exactly at the cap
    assert e7.veto_probability(10, 4) == 1.0          # capped, not 1.25
    assert e7.veto_probability(10, 6) == pytest.approx(5 / 6)
    assert e7.veto_probability(10, 0) == 0.0
    assert e7.veto_probability(0, 0) == 0.0
    assert isinstance(e7.veto_probability(10, 6), float)


def test_gated_flip_mask_equals_btsp_update_when_nothing_is_vetoed():
    m, n = 160, 80
    r = np.random.default_rng(3)
    E = np.sort(r.choice(m, 30, replace=False))
    A = np.sort(r.choice(n, 5, replace=False))
    ref, new = BinarySynapses(m, n), BinarySynapses(m, n)
    rng_a, rng_b = e1.stream(SEED, e1.COIN), e1.stream(SEED, e1.COIN)
    for _ in range(2):  # the second round toggles stored synapses off again
        btsp_update(ref, A, E, rng_a, .5)
        coins = rng_b.random(E.size * A.size).reshape(E.size, A.size)
        mask = e7.gated_flip_mask(coins, np.ones(E.size, bool), .5)
        assert mask.shape == (E.size, A.size) and mask.dtype == bool
        new.toggle((E[:, None] * n + A[None, :])[mask])
        assert np.array_equal(ref.keys, new.keys)
    assert ref.size > 0


def test_gated_flip_mask_selects_only_unvetoed_rows_below_p():
    coins = np.array([[.1, .6], [.1, .6], [.4, .9], [.0, .2]])
    keep = np.array([True, False, True, False])
    mask = e7.gated_flip_mask(coins, keep, .5)
    assert mask.tolist() == [[True, False], [False, False], [True, False], [False, False]]
    assert not e7.gated_flip_mask(coins, keep, 0.0).any()
    assert np.array_equal(e7.gated_flip_mask(coins, keep, 1.0), np.repeat(keep[:, None], 2, 1))


# ---------------------------------------------------------------- drop controls

def test_drop_random_counts_streams_and_one_based_keys():
    E = np.sort(np.random.default_rng(1).choice(400, 60, replace=False))
    for k, count in ((1, 7), (2, 0), (9, 25)):
        got = e7.drop_random(E, count, SEED, k)
        assert len(got) == count and len(np.unique(got)) == count and np.isin(got, E).all()
        assert np.array_equal(got, E[e1.stream(SEED, 33, k).choice(len(E), count, replace=False)])
        assert np.array_equal(got, e7.drop_random(E, count, SEED, k))
    assert not np.array_equal(e7.drop_random(E, 25, SEED, 9), e7.drop_random(E, 25, SEED, 10))


def test_drop_history_uses_history_plus_one_weights_on_stream_34():
    E = np.sort(np.random.default_rng(2).choice(400, 60, replace=False))
    H = np.random.default_rng(4).integers(0, 30, 400).astype(np.int64)
    for k, count in ((1, 7), (5, 0), (11, 25)):
        w = H[E] + 1
        want = E[e1.stream(SEED, 34, k).choice(len(E), count, replace=False, p=w / w.sum())]
        got = e7.drop_history(E, count, H, SEED, k)
        assert len(got) == count and len(np.unique(got)) == count
        assert np.array_equal(got, want)


def test_drop_history_prefers_a_hot_line_and_drop_random_does_not():
    E, H = np.arange(50), np.zeros(100, np.int64)
    H[7] = 10_000                                       # weight 10001 against 49 lines of weight 1
    hot = sum(int(7 in e7.drop_history(E, 1, H, SEED, k)) for k in range(1, 201))
    uniform = sum(int(7 in e7.drop_random(E, 1, SEED, k)) for k in range(1, 201))
    assert hot >= 190        # expected 199 of 200
    assert uniform <= 20     # expected 4 of 200


# ---------------------------------------------------------------- baseline and wrapper

def test_baseline_independent_gives_the_literal_e3_forward_store():
    cfg = small()
    base, literal = e7.Baseline(cfg, SEED, "independent"), e3.E3(cfg, SEED)
    base.learn(8)
    literal.learn(8)
    assert literal.store.size > 0
    assert np.array_equal(base.store.keys, literal.store.keys)
    assert np.array_equal(base.fb.keys, literal.fb.keys)
    assert all(np.array_equal(x, y) for x, y in zip(base.items, literal.items))
    assert not hasattr(base, "gate_log")


def test_baseline_swaps_only_the_pattern_generator():
    cfg = tiny()
    assert "learn_one" not in vars(e7.Baseline) and e7.Baseline.learn_one is e3.E3.learn_one
    base, literal = e7.Baseline(cfg, SEED, "F10"), e3.E3(cfg, SEED)
    literal._pat = e5.FamilyGen(SEED, cfg["m"], cfg["a"], 60, 10)
    base.learn(6)
    literal.learn(6)
    assert np.array_equal(base.store.keys, literal.store.keys)
    mixed = e7.Baseline(cfg, SEED, "mixed")
    mixed.learn(4)
    fam = e5.FamilyGen(SEED, cfg["m"], cfg["a"], 60, 10)
    assert np.array_equal(mixed.items[0], fam.exemplar(1)) and np.array_equal(mixed.items[2], fam.exemplar(2))
    assert mixed._pat.labels == ["F10", "independent", "F10", "independent"]
    f40 = e7.Baseline(dict(cfg, m=400, n=80), SEED, "F40")
    assert isinstance(f40._pat, e5.FamilyGen) and f40._pat.F == 40


def test_wrap_for_test_leaves_learning_and_the_store_unchanged():
    cfg = small()
    base, literal = e7.Baseline(cfg, SEED, "independent"), e3.E3(cfg, SEED)
    base.learn(4)
    keys = base.store.keys.copy()
    wrapped = e7.wrap_for_test(base)
    assert np.array_equal(wrapped.store.keys, keys)
    assert wrapped._probe_A is None and wrapped.onset_offsets == [] and wrapped.p_history == []
    assert np.array_equal(wrapped.H, np.bincount(np.concatenate(base.E), minlength=cfg["m"]))
    assert wrapped.H.dtype == np.int64 and len(wrapped.H) == cfg["m"]
    wrapped.learn(8)
    literal.learn(8)
    assert np.array_equal(wrapped.store.keys, literal.store.keys)


# ---------------------------------------------------------------- E7 arms

def test_gate_off_reproduces_the_baseline_trajectory_and_state():
    cfg = small()
    base, off = e7.Baseline(cfg, SEED, "independent"), e7.E7(cfg, SEED, "gate_off", "independent")
    base.learn(8)
    off.learn(8)
    assert base.store.size > 0
    assert np.array_equal(off.store.keys, base.store.keys)
    assert np.array_equal(off.fb.keys, base.fb.keys)
    assert np.array_equal(off.fb_plateau.keys, base.fb_plateau.keys)
    assert all(np.array_equal(x, y) for x, y in zip(off.R, base.R))
    assert same_mem(off, base)
    for stream in ("_learn_in", "_plat", "_coin"):
        assert getattr(off, stream).random() == getattr(base, stream).random()
    assert np.array_equal(off.H, e7.wrap_for_test(base).H)


def test_candidate_with_an_empty_feedback_store_flips_the_baseline_keys():
    cfg = small()
    base, cand = e7.Baseline(cfg, SEED, "independent"), e7.E7(cfg, SEED, "candidate", "independent")
    base.learn(1)
    cand.learn(1)
    assert base.store.size > 0
    assert np.array_equal(cand.store.keys, base.store.keys)
    assert same_mem(cand, base)  # computing the gate changes no memory-cell state
    g = cand.gate_log[0]
    assert (g["G_size"], g["V_size"], g["p"], g["p_capped"], g["Eprime_empty"]) == (0, 0, .5, False, False)
    assert g["E_size"] == len(cand.E[0])


def counts_total(e):
    return sum(len(E) * len(A) for E, A in zip(e.E, e.A))


@pytest.mark.parametrize("arm", ["baseline", "gate_off", "candidate"])
def test_exactly_E_times_A_coins_are_drawn_per_episode(arm):
    cfg = tiny()
    e = e7.Baseline(cfg, SEED, "F10") if arm == "baseline" else e7.E7(cfg, SEED, arm, "F10")
    e.learn(6)
    ref = e1.stream(SEED, e1.COIN)
    ref.random(counts_total(e))
    assert e._coin.random() == ref.random()


def fb_before(e, k, source):
    """The feedback store as it stood before episode k's write, rebuilt from the persisted R, A and E."""
    store = BinarySynapses(e.c["n"], e.c["m"])
    for j in range(k):
        rows = e.R[j] if source == "fb" else e.A[j]
        store.add((rows[:, None] * e.c["m"] + e.E[j][None, :]).ravel())
    return store


def reference_forward(e, arm, counts=None):
    """Rebuild the forward store of arm from its own persisted episodes, using only the public helpers."""
    c = e.c
    store = BinarySynapses(c["m"], c["n"])
    coin = e1.stream(SEED, e1.COIN)
    gen = e5.FamilyGen(SEED, c["m"], c["a"], 60, 10)
    H = np.zeros(c["m"], np.int64)
    seen = []
    for k in range(len(e.E)):
        E, A = e.E[k], e.A[k]
        G = e7.predict_set(e.encoding_rasters[k], fb_before(e, k, "plateau" if arm == "assigned_A_teacher" else "fb"), c["m"])
        V = np.intersect1d(E, G)
        if arm == "label_oracle":
            V = np.intersect1d(E, gen.protos[(k + 1) % 10])
        elif arm == "random_drop":
            V = e7.drop_random(E, counts[k], SEED, k + 1)
        elif arm == "history_drop":
            V = e7.drop_history(E, counts[k], H, SEED, k + 1)
        elif arm == "gate_off":
            V = EMPTY
        Eprime = ~np.isin(E, V)
        p = .5 if arm in ("gate_off", "no_conservation") else e7.veto_probability(E.size, int(Eprime.sum()))
        coins = coin.random(E.size * A.size).reshape(E.size, A.size) if E.size and A.size else np.empty((E.size, A.size))
        mask = e7.gated_flip_mask(coins, Eprime, p)
        store.toggle((E[:, None] * c["n"] + A[None, :])[mask])
        H[E] += 1
        seen.append((E.size, G.size, np.intersect1d(E, G).size))
    return store, H, seen


ARMS = ["candidate", "gate_off", "no_conservation", "label_oracle", "assigned_A_teacher", "random_drop", "history_drop"]


@pytest.mark.parametrize("arm", ARMS)
def test_each_arm_applies_its_rule_to_the_btsp_coins(arm):
    cfg, episodes = tiny(), 8
    counts = [3, 0, 5, 2, 7, 1, 4, 6]
    e = e7.E7(cfg, SEED, arm, "F10", veto_counts=counts if arm.endswith("_drop") else None)
    e.learn(episodes)
    assert e.episodes == episodes and len(e.gate_log) == episodes
    store, H, seen = reference_forward(e, arm, counts)
    assert np.array_equal(e.store.keys, store.keys)
    assert e.H.dtype == np.int64 and np.array_equal(e.H, H)
    assert np.array_equal(e.H, np.bincount(np.concatenate(e.E), minlength=cfg["m"]))
    for g, (n_e, n_g, n_v) in zip(e.gate_log, seen):  # every arm logs its own gate statistics
        assert (g["E_size"], g["G_size"]) == (n_e, n_g)
        assert 0 <= g["V_size"] <= g["E_size"]
        if arm in ("candidate", "gate_off", "no_conservation", "assigned_A_teacher"):
            assert g["V_size"] == n_v
        if arm == "candidate" and g["E_size"] > 0:
            assert g["Eprime_empty"] == (g["V_size"] == g["E_size"])
            if g["V_size"] < g["E_size"]:
                assert g["p"] == pytest.approx(e7.veto_probability(g["E_size"], g["E_size"] - g["V_size"]))
            assert g["p_capped"] == (g["p"] == 1.0)
        if arm in ("gate_off", "no_conservation"):
            assert g["p"] == .5 and not g["p_capped"]
        assert g["subset"] in (None, "F10")


def test_persisted_per_episode_evidence_is_consistent_with_learning():
    cfg = tiny()
    e = e7.E7(cfg, SEED, "candidate", "F10")
    e.learn(5)
    assert len(e.encoding_rasters) == len(e.cont_counts) == 5
    for k in range(5):
        raster, counts = e.encoding_rasters[k], e.cont_counts[k]
        assert set(raster) <= set(range(75))
        assert sum(len(v) for v in raster.values()) <= e.learn_log["mem_spikes"][k]
        assert counts.shape == (cfg["n"],) and np.issubdtype(counts.dtype, np.integer)
        assert np.array_equal(np.flatnonzero(counts), e.R[k])
    for g in e.gate_log:
        assert {"E_size", "G_size", "V_size", "p", "p_capped", "Eprime_empty", "veto_proto_fraction",
                "proto_predicted", "nonproto_predicted", "subset"} <= set(g)


def test_candidate_gate_never_changes_memory_state_beyond_the_forward_store():
    cfg = small()
    off, cand = e7.E7(cfg, SEED, "gate_off", "independent"), e7.E7(cfg, SEED, "candidate", "independent")
    off.learn(4)
    cand.learn(4)
    if np.array_equal(cand.store.keys, off.store.keys):  # same forward store implies the same dynamics
        assert same_mem(cand, off)
        assert all(np.array_equal(x, y) for x, y in zip(cand.R, off.R))


def test_mixed_candidate_logs_the_subset_of_every_episode():
    e = e7.E7(tiny(), SEED, "candidate", "mixed")
    e.learn(4)
    assert [g["subset"] for g in e.gate_log] == ["F10", "independent", "F10", "independent"]
    assert [g["subset"] for g in e7.E7(tiny(), SEED, "candidate", "F10").gate_log] == []


# ---------------------------------------------------------------- structural fields and kills

def entry(V=0, E=100, p=.5, capped=False, empty=False, vpf=None, pp=None, npp=None, subset="F10"):
    return dict(E_size=E, G_size=V, V_size=V, p=p, p_capped=capped, Eprime_empty=empty,
                veto_proto_fraction=vpf, proto_predicted=pp, nonproto_predicted=npp, subset=subset)


def f10_log():
    log = []
    for k in range(1000):
        if k < 500:
            log.append(entry(V=4 if k % 2 else 0, vpf=.9 if k % 2 else None, pp=.1, npp=.5))
        else:
            V = 0 if k == 600 else 40 if k == 700 else 20
            log.append(entry(V=V, vpf=.9 if V else None, pp=.6, npp=.05))
    for k in (123, 456, 789):
        log[k]["Eprime_empty"] = True
    for k in (10, 20, 30):
        log[k]["p_capped"] = True
    return log


def first_by_family(fields, f):
    fe = fields["first_engagement_by_family"]
    return fe[f] if isinstance(fe, (list, tuple)) else fe.get(f, fe.get(str(f)))


def test_structural_fields_on_a_synthetic_f10_log():
    fields = e7.structural_fields(SimpleNamespaceLog(f10_log()), "F10")
    assert fields["mean_V_1_500"] == pytest.approx(2.0)
    assert fields["mean_V_501_1000"] == pytest.approx(20.0)      # 498 x 20, one 0, one 40
    assert fields["max_V"] == 40
    assert fields["veto_precision_501_1000"] == pytest.approx(.9)
    assert fields["proto_predicted_501_1000"] == pytest.approx(.6)      # window only; earlier values are .1
    assert fields["nonproto_predicted_501_1000"] == pytest.approx(.05)
    assert fields["veto_episode_fraction"] == pytest.approx(749 / 1000)  # 250 early + 499 in the window
    assert list(fields["empty_Eprime_episodes"]) == [123, 456, 789]      # 0-based episode indices
    assert fields["p_capped_episodes"] == 3
    assert first_by_family(fields, 2) == 1 and first_by_family(fields, 0) == 9    # family of 0-based k is (k + 1) % 10
    assert first_by_family(fields, 1) == 500                                       # even steps carry V = 0 until 500
    assert fields.get("veto_episode_fraction_independent_subset") is None


class SimpleNamespaceLog:
    def __init__(self, log):
        self.gate_log, self.episodes = log, len(log)


def test_structural_window_for_a_short_log_is_the_second_half_of_what_exists():
    log = [entry(V=0) for _ in range(200)] + [entry(V=10, vpf=1.0, pp=.7, npp=.0) for _ in range(200)]
    fields = e7.structural_fields(SimpleNamespaceLog(log), "F10")
    assert fields["mean_V_501_1000"] == pytest.approx(10.0)     # episodes 201-400 of 400
    assert fields["proto_predicted_501_1000"] == pytest.approx(.7)
    assert fields["veto_precision_501_1000"] == pytest.approx(1.0)


def test_structural_precision_is_none_without_vetoes():
    fields = e7.structural_fields(SimpleNamespaceLog([entry() for _ in range(1000)]), "F10")
    assert fields["veto_precision_501_1000"] is None and fields["mean_V_501_1000"] == 0.0
    assert fields["veto_episode_fraction"] == 0.0 and fields["max_V"] == 0


def test_structural_fields_for_independent_and_mixed_streams():
    log = [entry(V=1 if k % 50 == 7 else 0, subset="independent") for k in range(1000)]
    fields = e7.structural_fields(SimpleNamespaceLog(log), "independent")
    assert fields["veto_episode_fraction"] == pytest.approx(.02) and fields["max_V"] == 1
    assert fields["proto_predicted_501_1000"] is None and fields["nonproto_predicted_501_1000"] is None
    mixed = []
    for k in range(1000):
        if k % 2 == 0:
            mixed.append(entry(V=20, vpf=.9, pp=.6, npp=.05, subset="F10"))
        else:
            mixed.append(entry(V=1 if k % 100 == 1 else 0, pp=0.0, npp=0.0, subset="independent"))
    fields = e7.structural_fields(SimpleNamespaceLog(mixed), "mixed")
    assert fields["veto_episode_fraction_independent_subset"] == pytest.approx(.02)   # 10 of 500
    assert fields["proto_predicted_501_1000"] == pytest.approx(.6)   # F10 subset only
    assert fields["nonproto_predicted_501_1000"] == pytest.approx(.05)


def good_fields(**kw):
    base = dict(mean_V_1_500=1.0, mean_V_501_1000=25.0, veto_precision_501_1000=.9,
                proto_predicted_501_1000=.6, nonproto_predicted_501_1000=.05, veto_episode_fraction=.5,
                veto_episode_fraction_independent_subset=None, max_V=40, empty_Eprime_episodes=[],
                p_capped_episodes=0, first_engagement_by_family=[None] * 10)
    return dict(base, **kw)


@pytest.mark.parametrize("override, rule", [
    (dict(mean_V_501_1000=4.9), "no engagement"),
    (dict(veto_precision_501_1000=.69), "contamination-driven veto"),
    (dict(nonproto_predicted_501_1000=.26), "saturated teacher"),
    (dict(proto_predicted_501_1000=.24), "no structure"),
])
def test_each_f10_structural_rule_fires_alone(override, rule):
    assert e7.structural_kills(good_fields(**override), "F10") == [rule]


def test_structural_rules_at_their_exact_thresholds_do_not_fire():
    edge = good_fields(mean_V_501_1000=5.0, veto_precision_501_1000=.7,
                       nonproto_predicted_501_1000=.25, proto_predicted_501_1000=.25)
    assert e7.structural_kills(edge, "F10") == []
    assert e7.structural_kills(good_fields(), "F10") == []


def test_structural_kills_list_every_fired_f10_rule_once_and_cope_with_no_vetoes():
    bad = good_fields(mean_V_501_1000=1.0, veto_precision_501_1000=.1,
                      nonproto_predicted_501_1000=.9, proto_predicted_501_1000=.0)
    assert sorted(e7.structural_kills(bad, "F10")) == sorted(
        ["no engagement", "contamination-driven veto", "saturated teacher", "no structure"])
    silent = good_fields(mean_V_501_1000=0.0, veto_precision_501_1000=None)
    assert e7.structural_kills(silent, "F10") == ["no engagement"]


def test_false_engagement_rules_apply_to_their_own_condition_only():
    assert e7.structural_kills(good_fields(veto_episode_fraction=.06), "independent") == ["false engagement"]
    assert e7.structural_kills(good_fields(veto_episode_fraction=.05), "independent") == []
    mixed = good_fields(veto_episode_fraction_independent_subset=.06)
    assert e7.structural_kills(mixed, "mixed") == ["false engagement, mixed"]
    assert e7.structural_kills(good_fields(veto_episode_fraction_independent_subset=.05), "mixed") == []
    # scoping: the mixed-only field is ignored for an independent stream whose own fraction is within bound
    assert e7.structural_kills(good_fields(veto_episode_fraction=.04, veto_episode_fraction_independent_subset=.06), "independent") == []
    assert e7.structural_kills(good_fields(veto_episode_fraction=.04), "mixed") == []


# ---------------------------------------------------------------- criteria recompute

def row(i, own, spur, oldest, kind="half", A=20):
    return dict(kind=kind, index_0based=i, own50=own, recall50=own / A, spurious50=spur, A_size=A, oldest=oldest)


ROWS = [row(0, 18, 3, True), row(1, 14, 2, True), row(2, 17, 10, True), row(3, 20, 9, True),
        row(4, 16, 0, False), row(5, 15, 0, False), row(6, 19, 12, False), row(7, 18, 5, False),
        dict(kind="novel", index_0based=8, total50=3), dict(kind="full", index_0based=9, own50=20, recall50=1.0,
                                                           spurious50=0, A_size=20, oldest=False)]
LABELS = ["F10", "independent"] * 5


def test_recompute_criteria_counts_half_cues_only_and_has_no_c3():
    out = e7.recompute_criteria(ROWS, tiny())
    assert (out["n_cues"], out["n_oldest_cues"]) == (8, 4)
    assert (out["C1_count"], out["C2_count"], out["joint_index_count"]) == (6, 6, 4)
    assert (out["C4_recall_count"], out["C4_spurious_count"]) == (3, 3)
    assert out["C1"] == .75 and out["C2"] == .75 and out["joint_index"] == .5
    assert out["C4_recall"] == .75 and out["C4_spurious"] == .75
    assert "C3" not in out and "C3_count" not in out


def test_c1_threshold_is_inclusive_and_c2_threshold_is_strict():
    rows = [row(0, 16, 9, True), row(1, 16, 10, True)]       # recall exactly .8; spurious 9 and 10 against < 10
    out = e7.recompute_criteria(rows, tiny())
    assert (out["C1_count"], out["C2_count"], out["joint_index_count"]) == (2, 1, 1)


def test_subset_scores_partition_the_half_cues():
    scores = e7.subset_scores(ROWS, LABELS)
    a, b = scores["F10"], scores["independent"]
    assert (a["n_cues"], a["n_oldest_cues"], b["n_cues"], b["n_oldest_cues"]) == (4, 2, 4, 2)
    assert (a["C1_count"], a["C2_count"], a["joint_index_count"]) == (4, 2, 2)
    assert (a["C4_recall_count"], a["C4_spurious_count"]) == (2, 1)
    assert (b["C1_count"], b["C2_count"], b["joint_index_count"]) == (2, 4, 2)
    assert (b["C4_recall_count"], b["C4_spurious_count"]) == (1, 2)
    total = e7.recompute_criteria(ROWS, tiny())
    for key in ("n_cues", "n_oldest_cues", "C1_count", "C2_count", "joint_index_count",
                "C4_recall_count", "C4_spurious_count"):
        assert a[key] + b[key] == total[key]
    assert a["C2"] == .5 and b["C2"] == 1.0 and a["C4_spurious"] == .5
    assert "C3" not in a


# ---------------------------------------------------------------- source manifest

PINNED_BASELINE = ["plant2/engine.py", "plant2/btsp.py", "plant2/readout.py", "plant2/record.py",
                   "plant2/experiments/p2_e1_btsp.py", "plant2/experiments/p2_e2_accommodation.py",
                   "plant2/experiments/p2_e3_completion.py", "plant2/experiments/p2_e4_online.py",
                   "plant2/experiments/p2_e5_structured.py"]
PINNED_CONTRACT = ["plant2/experiments/p2_e6.py", "plant2/evidence.py", "analysis/p2r1_replay.py"]


def test_source_manifest_lists_every_pinned_path_with_its_pin():
    m = e7.source_manifest()
    assert isinstance(m["code_sha256"], str) and len(m["code_sha256"]) == 64
    for path in PINNED_BASELINE:
        assert m["files"][path]["pin"] == "55e16eb"
    for path in PINNED_CONTRACT:
        assert m["files"][path]["pin"] == "contract"
    for entry_ in m["files"].values():
        assert len(entry_["sha256"]) == 64 and isinstance(entry_["passed"], bool)
    assert (record.REPO / "plant2/engine.py").exists()


# ---------------------------------------------------------------- seed guard

D = "d1" * 32
MANIFEST = dict(code_sha256=D)


def passing(seed, digest=D):
    return dict(kind="seed_screen", seed=seed, full_size=True, attempt=f"a{seed}", source=dict(code_sha256=digest),
                screen=dict(verdict="FEASIBILITY PASS", failed=[], missing=[]))


def ready(digest=D, predictions=None):
    return dict(kind="gate_ready", source=dict(code_sha256=digest),
                predictions=e7.FROZEN["predictions"] if predictions is None else predictions)


def started(seed, full=True):
    return dict(kind="seed_started", seed=seed, full_size=full, attempt=f"s{seed}")


def refused(seed, committed, existing):
    with pytest.raises(ValueError) as info:
        e7.seed_guard(seed, MANIFEST, committed, existing)
    assert str(info.value)


def test_seed_guard_refuses_every_seed_outside_the_registry():
    for seed in (0, 101, 102, 111, 120, 123, 130, 136, 999):
        refused(seed, [passing(121), passing(122), ready()], [])


def test_seed_guard_opens_development_and_refuses_a_repeat_full_size_attempt():
    assert "stage" in e7.seed_guard(121, MANIFEST, [], [])
    assert "stage" in e7.seed_guard(121, MANIFEST, [], [started(121, full=False)])
    refused(121, [], [started(121)])
    refused(122, [passing(121)], [started(122)])
    refused(133, [passing(121), passing(122), ready()], [started(133)])


def test_held_out_seed_needs_a_committed_pass_on_121_with_the_same_source_digest():
    refused(122, [], [])
    refused(122, [passing(121, digest="ee" * 32)], [])
    fail = passing(121)
    fail["screen"] = dict(verdict="FEASIBILITY FAIL", failed=["x"], missing=[])
    refused(122, [fail], [])
    opened = e7.seed_guard(122, MANIFEST, [passing(121)], [started(121)])
    assert "stage" in opened
    assert opened["stage"] != e7.seed_guard(121, MANIFEST, [], [])["stage"]


def test_gated_seeds_need_both_passes_and_a_gate_ready_with_the_frozen_predictions():
    committed = [passing(121), passing(122), ready()]
    stages = {s: e7.seed_guard(s, MANIFEST, committed, []) for s in (131, 132, 133, 134, 135)}
    assert all("stage" in v for v in stages.values())
    assert stages[131]["stage"] != e7.seed_guard(122, MANIFEST, committed, [])["stage"]
    refused(131, [passing(121), ready()], [])
    refused(131, [passing(122), ready()], [])
    refused(131, [passing(121), passing(122)], [])
    refused(131, [passing(121), passing(122), ready(digest="ee" * 32)], [])
    altered = dict(e7.FROZEN["predictions"], mean_V_501_1000_min=1)
    refused(131, [passing(121), passing(122), ready(predictions=altered)], [])
    refused(131, [passing(121, digest="ee" * 32), passing(122), ready()], [])


def test_an_invalid_screen_on_any_registry_seed_locks_every_remaining_seed():
    invalid = dict(kind="seed_screen", seed=131, full_size=True, attempt="a131", source=dict(code_sha256=D),
                   screen=dict(verdict="INVALID", failed=[], missing=[]))
    committed = [passing(121), passing(122), ready(), invalid]
    refused(132, committed, [invalid])
    refused(133, committed, [invalid])
    invalid_dev = dict(invalid, seed=121, attempt="a121x")
    refused(122, [invalid_dev, passing(121)], [invalid_dev])


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


def good_loads():
    loads = []
    for condition, arms in e7.FROZEN["arms"].items():
        for arm in arms:
            for M in e7.LOADS:
                load = make_load(condition, arm, M)
                if condition == "F10" and M == 1000 and arm in ("baseline", "random_drop", "history_drop"):
                    c2, joint = dict(baseline=(.65, .75), random_drop=(.80, .80), history_drop=(.84, .84))[arm]
                    load["index"].update(C2=c2, joint_index=joint)
                loads.append(load)
    return loads


SANITY = dict(wrong_label=dict(C1=.02), empty_store=dict(responders=0))
STRUCT = dict(F10=[], independent=[], mixed=[])


def run_screen(loads, sanity=None, structural=None, uniform=True, invalid=False):
    return e7.screen(loads, SANITY if sanity is None else sanity, STRUCT if structural is None else structural,
                     uniform, invalid=invalid)


def find(loads, condition, arm, M):
    return next(x for x in loads if (x["condition"], x["arm"], x["M"]) == (condition, arm, M))


def test_screen_passes_a_complete_set_that_meets_every_bar_and_margin():
    out = run_screen(good_loads())
    assert out["verdict"] == "FEASIBILITY PASS" and out["failed"] == [] and out["missing"] == []


def mutated(fn):
    loads = good_loads()
    fn(loads)
    return run_screen(loads)


@pytest.mark.parametrize("name, fn, word", [
    ("C2 vs random", lambda L: (find(L, "F10", "candidate", 1000)["index"].update(C2=.92),
                                find(L, "F10", "random_drop", 1000)["index"].update(C2=.85)), "C2"),
    ("C2 vs history", lambda L: (find(L, "F10", "candidate", 1000)["index"].update(C2=.92),
                                 find(L, "F10", "history_drop", 1000)["index"].update(C2=.90)), "C2"),
    ("C2 vs baseline", lambda L: (find(L, "F10", "candidate", 1000)["index"].update(C2=.92),
                                  find(L, "F10", "baseline", 1000)["index"].update(C2=.80)), "C2"),
    ("joint vs random", lambda L: find(L, "F10", "random_drop", 1000)["index"].update(joint_index=.90), "joint"),
    ("joint vs baseline", lambda L: find(L, "F10", "baseline", 1000)["index"].update(joint_index=.90), "joint"),
    ("C1 non-regression F10", lambda L: find(L, "F10", "candidate", 500)["index"].update(C1=.90), "C1"),
    ("C1 non-regression independent", lambda L: find(L, "independent", "candidate", 1000)["index"].update(C1=.90), "C1"),
    ("C4_recall non-regression", lambda L: find(L, "F10", "candidate", 1000)["index"].update(C4_recall=.90), "C4"),
    ("independent C2 non-regression", lambda L: (find(L, "independent", "baseline", 500)["index"].update(C2=.99),
                                                 find(L, "independent", "candidate", 500)["index"].update(C2=.94)), "C2"),
    ("independent content joint", lambda L: find(L, "independent", "candidate", 1000)["content"]["inherited"].update(joint=.80), "joint"),
    ("independent content D4", lambda L: find(L, "independent", "candidate", 500)["content"]["inherited"].update(D4=.80), "D4"),
    ("C3 at F10", lambda L: find(L, "F10", "candidate", 500)["index"].update(C3=.89), "C3"),
    ("C3 at independent", lambda L: find(L, "independent", "candidate", 1000)["index"].update(C3=.89), "C3"),
    ("absolute joint bar", lambda L: [find(L, "independent", a, 500)["index"].update(joint_index=.84) for a in ("candidate", "baseline")], "joint"),
    ("protocol check on mixed", lambda L: find(L, "mixed", "baseline", 500)["protocol"].update(eligibility=False), ""),
    ("protocol check on a control arm", lambda L: find(L, "F10", "label_oracle", 1000)["protocol"].update(settled=False), ""),
])
def test_each_kill_rule_gives_feasibility_fail(name, fn, word):
    out = mutated(fn)
    assert out["verdict"] == "FEASIBILITY FAIL", name
    assert out["failed"] and any(word in str(f) for f in out["failed"]), name


def test_mixed_independent_subset_margins_are_counted_in_cues():
    def set_counts(key, base, cand, where="index_by_subset"):
        def fn(L):
            find(L, "mixed", "baseline", 1000)[where]["independent"][key] = base
            find(L, "mixed", "candidate", 1000)[where]["independent"][key] = cand
        return fn
    assert mutated(set_counts("C1_count", 100, 97))["verdict"] == "FEASIBILITY PASS"      # three below: allowed
    assert mutated(set_counts("C1_count", 100, 96))["verdict"] == "FEASIBILITY FAIL"      # four below: kill
    assert mutated(set_counts("C2_count", 100, 97))["verdict"] == "FEASIBILITY PASS"
    assert mutated(set_counts("C2_count", 100, 96))["verdict"] == "FEASIBILITY FAIL"
    assert mutated(set_counts("joint_count", 60, 56, "content_by_subset"))["verdict"] == "FEASIBILITY PASS"
    assert mutated(set_counts("joint_count", 60, 55, "content_by_subset"))["verdict"] == "FEASIBILITY FAIL"


def test_f40_is_reported_only_and_cannot_fail_the_screen():
    def fn(L):
        for M in e7.LOADS:
            find(L, "F40", "candidate", M)["index"].update(C1=.1, C2=.1, C3=.1, joint_index=.1)
    assert mutated(fn)["verdict"] == "FEASIBILITY PASS"


def test_a_failed_sanity_check_or_a_fired_structural_rule_fails_the_screen():
    assert run_screen(good_loads(), sanity=dict(wrong_label=dict(C1=.10), empty_store=dict(responders=0)))["verdict"] == "FEASIBILITY FAIL"
    assert run_screen(good_loads(), sanity=dict(wrong_label=dict(C1=.09), empty_store=dict(responders=0)))["verdict"] == "FEASIBILITY PASS"
    assert run_screen(good_loads(), sanity=dict(wrong_label=dict(C1=.02), empty_store=dict(responders=1)))["verdict"] == "FEASIBILITY FAIL"
    assert run_screen(good_loads(), structural=dict(F10=["no structure"], independent=[], mixed=[]))["verdict"] == "FEASIBILITY FAIL"


def test_a_missing_arm_is_partial_and_named():
    loads = [x for x in good_loads() if (x["condition"], x["arm"], x["M"]) != ("F10", "history_drop", 1000)]
    out = run_screen(loads)
    assert out["verdict"] == "PARTIAL" and out["failed"] == []
    assert len(out["missing"]) == 1 and "history_drop" in str(out["missing"][0]) and "1000" in str(out["missing"][0])
    gone = [x for x in good_loads() if (x["condition"], x["arm"], x["M"]) != ("mixed", "baseline", 500)]
    assert run_screen(gone)["verdict"] == "PARTIAL"


def test_integrity_failures_make_the_screen_invalid():
    assert run_screen(good_loads(), invalid=True)["verdict"] == "INVALID"
    assert run_screen(good_loads(), uniform=False)["verdict"] == "INVALID"
    for M in e7.LOADS:  # the gate_off store must equal the baseline's at both checkpoints
        loads = good_loads()
        find(loads, "F10", "gate_off", M)["forward_sha256"] = "different"
        assert run_screen(loads)["verdict"] == "INVALID"
    loads = good_loads()
    find(loads, "F10", "candidate", 1000)["index"]["C3"] = .5   # a kill, but invalid takes precedence
    assert run_screen(loads, invalid=True)["verdict"] == "INVALID"
