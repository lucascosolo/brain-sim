"""Triplet potentiation beside the heterosynaptic write (SPEC.md section 8.21), branch `triplet`.

Covers: brainsim/triplet.py pure maths, params and the flag, the engine rule on hand-built
networks (traces, LTD/LTP order, scope, K per region, gate, bounds, no RNG), the off-path
digest, Engine.triplet_view, and the verdict() helper of tests/k821_triplet.py.
"""
import importlib
import importlib.util
import pathlib
import types

import numpy as np
import pytest

from brainsim import params
from brainsim.engine import Engine
from brainsim.net import Network

from tests.test_engine_determinism import REFERENCE_DIGEST, _digest, run_schedule

A2P, A3P, A2M = 5.3e-3, 8e-3, 3.5e-3
TAU_R, TAU_O1, TAU_O2 = 16.8, 33.7, 40.0
K_CTX, K_HPC = 3.3, 16.5
F32 = np.float32


def _tri():
    return importlib.import_module("brainsim.triplet")


# ---- 1. pure maths ---------------------------------------------------------------
def test_triplet_constants():
    t = _tri()
    assert (t.A2_PLUS, t.A3_PLUS, t.A2_MINUS) == (A2P, A3P, A2M)
    assert (t.TAU_PLUS_MS, t.TAU_MINUS_MS, t.TAU_Y_MS) == (TAU_R, TAU_O1, TAU_O2)
    assert t.K_DEFAULT == {"hpc": 16.5, "ctx": 3.3}


def test_k_of_reads_params_else_default():
    t = _tri()
    assert t.k_of(types.SimpleNamespace(TRIPLET_K={"hpc": 1.0, "ctx": 2.0})) == {"hpc": 1.0, "ctx": 2.0}
    assert t.k_of(types.SimpleNamespace()) == {"hpc": 16.5, "ctx": 3.3}
    assert t.k_of(params) == {"hpc": 16.5, "ctx": 3.3}


def test_on_pre_hand_value():
    t = _tri()
    # 1.0 - 3.3 * 3.5e-3 * 0.5 * 2.0
    assert t.on_pre(1.0, 0.5, 2.0, 3.3) == pytest.approx(1.0 - 3.3 * 3.5e-3 * 0.5 * 2.0)
    assert t.on_pre(1.0, 0.5, 2.0, 3.3) == pytest.approx(0.98845)


def test_on_post_hand_value():
    t = _tri()
    # 1.0 + 3.3 * 0.4 * (5.3e-3 + 8e-3 * 0.6) * 2.0
    assert t.on_post(1.0, 0.4, 0.6, 2.0, 3.3) == pytest.approx(1.026664)
    # o2 = 0 is the pure pair term
    assert t.on_post(1.0, 0.4, 0.0, 2.0, 3.3) == pytest.approx(1.0 + 3.3 * 0.4 * 5.3e-3 * 2.0)


def test_pure_gate_scaling_and_vectorised():
    t = _tri()
    w = np.array([0.5, 1.0, 1.5])
    o1 = np.array([0.0, 0.5, 1.0])
    r1 = np.array([1.0, 0.5, 0.0])
    o2 = np.array([0.0, 0.5, 1.0])
    d_pre = w - t.on_pre(w, o1, 2.0, 3.3)
    np.testing.assert_allclose(d_pre, 3.3 * A2M * o1 * 2.0, rtol=1e-12, atol=1e-15)
    d_post = t.on_post(w, r1, o2, 2.0, 3.3) - w
    np.testing.assert_allclose(d_post, 3.3 * r1 * (A2P + A3P * o2) * 2.0, rtol=1e-12, atol=1e-15)
    np.testing.assert_allclose(w - t.on_pre(w, o1, 2.0, 3.3, g=0.3), 0.3 * d_pre, rtol=1e-12, atol=1e-15)
    np.testing.assert_allclose(t.on_post(w, r1, o2, 2.0, 3.3, g=0.3) - w, 0.3 * d_post, rtol=1e-12, atol=1e-15)
    # per-element w_max
    wm = np.array([2.0, 3.0, 2.0])
    np.testing.assert_allclose(w - t.on_pre(w, o1, wm, 3.3), 3.3 * A2M * o1 * wm, rtol=1e-12, atol=1e-15)


def test_pure_bounds_at_zero_and_w_max():
    t = _tri()
    assert t.on_pre(0.001, 1.0, 2.0, 100.0) == 0.0
    assert t.on_post(1.999, 1.0, 1.0, 2.0, 100.0) == 2.0
    out = t.on_post(np.array([0.0, 2.0]), np.array([0.0, 0.0]), np.array([0.0, 0.0]), 2.0, 3.3)
    np.testing.assert_array_equal(out, [0.0, 2.0])
    out = t.on_pre(np.array([0.0, 2.0]), np.array([0.0, 0.0]), 2.0, 3.3)
    np.testing.assert_array_equal(out, [0.0, 2.0])


def test_pure_float32_preserved():
    t = _tri()
    w = np.array([0.5, 1.0], F32)
    tr = np.array([0.3, 0.7], F32)
    assert t.on_pre(w, tr, F32(2.0), 3.3).dtype == F32
    assert t.on_post(w, tr, tr, F32(2.0), 3.3).dtype == F32
    assert t.on_pre(w, tr, np.array([2.0, 3.0], F32), 3.3).dtype == F32


# ---- 2. params, flag, off path ------------------------------------------------
def test_params_and_flag_default():
    assert params.TRIPLET_STDP is False
    assert params.TRIPLET_K == {"hpc": 16.5, "ctx": 3.3}
    e = Engine(seed=1)
    assert e.triplet_stdp is False
    for name in ("r1", "o1", "o2"):
        a = getattr(e.net, name)
        assert a.dtype == F32 and a.shape == (e.net.n,) and not a.any()


def test_flag_off_digest_equals_reference():
    e = run_schedule()
    assert e.triplet_stdp is False
    assert _digest(e) == REFERENCE_DIGEST


# ---- helpers for hand-built engines -------------------------------------------
def _tiny(n, is_exc, syns, region="ctx", a_plus=None):
    net = Network.tiny(n, is_exc, syns)
    net.region_names = [region]
    net.region_slice = {region: slice(0, n)}
    if a_plus is not None:
        net.a_plus_n[:] = a_plus
    return net


def _eng(net, on=True, noise=0.0):
    e = Engine(seed=1, net=net, noise_sigma=noise)
    assert e.triplet_stdp is False
    e.triplet_stdp = on
    return e


def _fire(e, ids):
    e.inject(np.array(ids), 30.0, 1)


def _deliver(e, syn=0):
    e.ring[e.t % (params.D_MAX + 1)].append(np.array([syn]))


def _ltd_setup(w=1.0, **kw):
    net = _tiny(2, [True, True], [(0, 1, w, 1)], **kw)
    return net, _eng(net)


# ---- 3a. traces ------------------------------------------------------------------
def test_traces_increment_at_spike_and_decay_with_own_tau():
    net = _tiny(3, [True] * 3, [])
    e = _eng(net)
    assert net.r1.dtype == F32 and not net.r1.any()
    _fire(e, [0])
    e.step(1)
    for tr in (net.r1, net.o1, net.o2):
        assert tr[0] == pytest.approx(1.0)
        assert tr[1] == 0.0 and tr[2] == 0.0
    e.step(10)
    assert net.r1[0] == pytest.approx(np.exp(-10 / TAU_R), rel=1e-4)
    assert net.o1[0] == pytest.approx(np.exp(-10 / TAU_O1), rel=1e-4)
    assert net.o2[0] == pytest.approx(np.exp(-10 / TAU_O2), rel=1e-4)


def test_traces_stay_zero_without_spikes():
    net = _tiny(3, [True] * 3, [])
    e = _eng(net)
    e.step(20)
    assert not (net.r1.any() or net.o1.any() or net.o2.any())


# ---- 3b. LTD at delivery -----------------------------------------------------------
def test_ltd_uses_o1_before_this_ticks_decay():
    net, e = _ltd_setup(1.0)
    net.o1[1] = 0.5
    _deliver(e)
    e.step(1)
    expect = 1.0 - 3.3 * A2M * 0.5 * 2.0
    assert float(net.w[0]) == pytest.approx(expect, abs=2e-6)


def test_ltd_ignores_y_post_pair_term_and_zero_o1_is_noop():
    net, e = _ltd_setup(1.0)
    net.y_post[1] = 0.5
    _deliver(e)
    e.step(1)
    assert float(net.w[0]) == 1.0


# ---- 3c. LTP at post spike ----------------------------------------------------
def test_ltp_uses_r1_and_o2_after_decay_before_increment():
    net, e = _ltd_setup(1.0)
    net.r1[0], net.o2[1] = 0.4, 0.6
    _fire(e, [1])
    e.step(1)
    r1 = 0.4 * np.exp(-1 / TAU_R)
    o2 = 0.6 * np.exp(-1 / TAU_O2)
    expect = 1.0 + 3.3 * r1 * (A2P + A3P * o2) * 2.0
    assert float(net.w[0]) == pytest.approx(expect, abs=2e-6)


def test_first_ever_spike_sees_o2_zero_pure_pair_term():
    net, e = _ltd_setup(1.0)
    net.r1[0] = 0.4
    assert net.o2[1] == 0.0
    _fire(e, [1])
    e.step(1)
    r1 = 0.4 * np.exp(-1 / TAU_R)
    assert float(net.w[0]) == pytest.approx(1.0 + 3.3 * r1 * A2P * 2.0, abs=2e-6)
    assert net.o2[1] == pytest.approx(1.0)


def test_pair_rule_updates_do_not_apply():
    # x_pre set, r1 zero: the pair rule would potentiate, the triplet rule must not
    net, e = _ltd_setup(1.0)
    net.x_pre[0] = 0.5
    _fire(e, [1])
    e.step(1)
    assert float(net.w[0]) == 1.0
    # and the pair-rule engine does move it
    net2 = _tiny(2, [True, True], [(0, 1, 1.0, 1)])
    e2 = _eng(net2, on=False)
    net2.x_pre[0] = 0.5
    _fire(e2, [1])
    e2.step(1)
    assert float(net2.w[0]) > 1.0


def test_flag_toggles_at_runtime_between_rules():
    net, e = _ltd_setup(1.0)
    e.triplet_stdp = False
    net.y_post[1] = 0.5
    _deliver(e)
    e.step(1)
    assert float(net.w[0]) < 1.0 and float(net.w[0]) != pytest.approx(1.0 - 3.3 * A2M * 0.0)
    pair_w = float(net.w[0])
    e.triplet_stdp = True
    net.y_post[1] = 0.0
    _deliver(e)
    e.step(1)
    assert float(net.w[0]) == pair_w


# ---- 3d. scope -----------------------------------------------------------------
def test_inhibitory_synapse_untouched():
    net = _tiny(2, [False, True], [(0, 1, -1.0, 1)])
    e = _eng(net)
    net.o1[1], net.r1[0] = 0.5, 0.5
    _deliver(e)
    _fire(e, [1])
    e.step(1)
    assert float(net.w[0]) == -1.0


def test_synapse_onto_sense_like_cell_untouched():
    net = _tiny(2, [True, True], [(0, 1, 1.0, 1)], a_plus=0.0)
    net.a_minus_n[:] = 0.0
    e = _eng(net)
    net.o1[1], net.r1[0], net.o2[1] = 0.5, 0.5, 0.5
    _deliver(e)
    _fire(e, [1])
    e.step(1)
    assert float(net.w[0]) == 1.0


# ---- 3e. K by region and the gate ----------------------------------------------
def _default_ltp_change(post_region, g=1.0, seed=1):
    e = Engine(seed=seed)
    assert e.triplet_stdp is False
    e.triplet_stdp = True
    e.g = g
    net = e.net
    names = np.array(net.region_names)[net.region]
    alive = np.flatnonzero(net.alive & net.is_exc[net.pre])
    syn = int(alive[names[net.post[alive]] == post_region][0])
    pre, post = int(net.pre[syn]), int(net.post[syn])
    wmax = float(net.w_max_n[post])
    net.w[syn] = 0.5 * wmax
    net.r1[pre], net.o2[post] = 0.5, 0.2
    e.inject(np.array([post]), 100.0, 1)
    w0 = float(net.w[syn])
    e.step(1)
    return (float(net.w[syn]) - w0) / wmax, wmax


def test_k_ratio_by_post_region_on_default_network():
    d_ctx, wm_ctx = _default_ltp_change("ctx")
    d_hpc, wm_hpc = _default_ltp_change("hpc")
    r1, o2 = 0.5 * np.exp(-1 / TAU_R), 0.2 * np.exp(-1 / TAU_O2)
    base = r1 * (A2P + A3P * o2)
    assert d_ctx == pytest.approx(K_CTX * base, rel=1e-3)
    assert d_hpc == pytest.approx(K_HPC * base, rel=1e-3)
    assert d_hpc / d_ctx == pytest.approx(K_HPC / K_CTX, rel=1e-3)


def test_gate_scales_ltp_and_ltd():
    def run(g, ltd):
        net, e = _ltd_setup(1.0)
        e.g = g
        if ltd:
            net.o1[1] = 0.5
            _deliver(e)
        else:
            net.r1[0] = 0.4
            _fire(e, [1])
        e.step(1)
        return float(net.w[0]) - 1.0
    for ltd in (True, False):
        assert run(0.3, ltd) == pytest.approx(0.3 * run(1.0, ltd), rel=1e-3)
        assert run(1.0, ltd) != 0.0


# ---- 3f. RNG, bounds, alive, old traces ------------------------------------------
def test_same_seed_default_engines_identical_with_flag_on():
    def run():
        e = Engine(seed=2)
        assert e.triplet_stdp is False
        e.triplet_stdp = True
        e.step(300)
        return e
    a, b = run(), run()
    assert np.array_equal(a.net.w, b.net.w) and np.array_equal(a.net.spike_count, b.net.spike_count)
    assert np.array_equal(a.net.o2, b.net.o2) and a.net.o2.any()


def test_rule_consumes_no_rng():
    def run(on):
        net = _tiny(3, [True] * 3, [(0, 1, 1.0, 1), (1, 2, 1.0, 2)])
        e = _eng(net, on=on, noise=0.5)
        for k in range(150):
            if k % 10 == 0:
                _fire(e, [0, 1])
            e.step(1)
        return e.rng.bit_generator.state
    assert run(True) == run(False)


def test_weights_hard_bounded_and_alive_unchanged():
    # synapse 0 starts near w_max and is potentiated; synapse 1 starts near 0 and is depressed
    net = _tiny(2, [True, True], [(0, 1, 1.999, 1), (1, 0, 0.002, 1)])
    e = _eng(net)
    alive0 = net.alive.copy()
    net.r1[0], net.o2[1] = 50.0, 50.0       # LTP onto cell 1 via synapse 0
    net.o1[0] = 1e3                          # LTD onto cell 0 via synapse 1
    _deliver(e, 1)
    _fire(e, [1])
    e.step(1)
    assert float(net.w[0]) == 2.0
    assert float(net.w[1]) == 0.0
    assert np.array_equal(net.alive, alive0)


def test_default_engine_weights_in_bounds_and_alive_kept_flag_on():
    e = Engine(seed=1)
    assert e.triplet_stdp is False
    e.triplet_stdp = True
    alive0 = e.net.alive.copy()
    w0 = e.net.w.copy()
    e.step(400)
    net = e.net
    idx = np.flatnonzero(net.alive)
    exc = idx[net.is_exc[net.pre[idx]]]
    inh = idx[~net.is_exc[net.pre[idx]]]
    assert np.all(net.w[exc] >= 0.0)
    assert np.all(net.w[exc] <= net.w_max_n[net.post[exc]])
    assert np.array_equal(net.w[inh], w0[inh])
    assert np.array_equal(net.alive, alive0)  # no sweep in 400 ticks: the rule alone kills nothing


def test_x_pre_y_post_unchanged_by_flag():
    def run(on):
        net = _tiny(3, [True] * 3, [(0, 1, 1.0, 1), (1, 2, 1.0, 1)])
        e = _eng(net, on=on)
        for k in range(60):
            if k % 7 == 0:
                _fire(e, [0])
            if k % 11 == 0:
                _fire(e, [1, 2])
            e.step(1)
        return net.x_pre.copy(), net.y_post.copy(), net.spike_count.copy(), net
    xa, ya, ca, na = run(True)
    xb, yb, cb, nb = run(False)
    assert na.o2.any() and np.array_equal(ca, cb)
    np.testing.assert_array_equal(xa, xb)
    np.testing.assert_array_equal(ya, yb)
    assert not np.array_equal(na.w, nb.w)


# ---- 3g. triplet_view ---------------------------------------------------------
def test_triplet_view_keys_values_and_read_only():
    e = Engine(seed=1)
    v = e.triplet_view()
    assert set(v) == {"on", "k", "mean_o2"}
    assert v["on"] is False and v["k"] == {"hpc": 16.5, "ctx": 3.3}
    assert isinstance(v["mean_o2"], float) and v["mean_o2"] == 0.0
    e.triplet_stdp = True
    e.net.o2[:] = 0.25
    w0, rs = e.net.w.copy(), e.rng.bit_generator.state
    v = e.triplet_view()
    assert v["on"] is True and v["mean_o2"] == pytest.approx(0.25)
    assert np.array_equal(w0, e.net.w) and rs == e.rng.bit_generator.state
    assert float(e.net.o2[0]) == pytest.approx(0.25)


# ---- 4. driver verdict ---------------------------------------------------------
V1_REF_EXPECTED = {1: (8, 0.258), 2: (12, 0.239), 3: (13, 0.293)}


def _drv():
    path = pathlib.Path(__file__).with_name("k821_triplet.py")
    spec = importlib.util.spec_from_file_location("k821_triplet", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _rec(seed=1):
    n, c = V1_REF_EXPECTED[seed]
    return {
        "seed": seed,
        "pair_on": {"W_cells_full_A_184": n, "surv_contrast_184": c},
        "hz": {k: {"hpc_E": 1.0, "ctx_E": 4.0} for k in ("184", "300", "440")},
        "max_tick_frac": {"ctx_E": 0.05, "hpc_E": 0.05},
        "sat": {k: {"ctx_E": 0.05, "hpc_E": 0.05} for k in ("184", "440")},
        "died": {k: {"ctx_E": 0.05, "hpc_E": 0.05} for k in ("184", "440")},
        "early": {"on": {"deliv_A": 1.5, "W_spikes_A": 15.0, "W_spikes_B": 2.0},
                  "never": {"deliv_A": 1.0, "W_spikes_A": 10.0, "W_spikes_B": 2.0}},
        "late": {"on": {"deliv_A": 1.3}, "never": {"deliv_A": 1.0}},
    }


def _ver(rec):
    return _drv().verdict(rec)


def test_driver_v1_ref_constants():
    assert _drv().V1_REF == V1_REF_EXPECTED


def test_driver_all_pass_each_seed():
    for s in (1, 2, 3):
        assert _ver(_rec(s)) == (True, [])


def test_driver_v1_count_and_rounded_contrast():
    r = _rec(2)
    r["pair_on"]["W_cells_full_A_184"] = 11
    assert _ver(r) == (False, ["V1"])
    r = _rec(2)
    r["pair_on"]["surv_contrast_184"] = 0.2394      # rounds to 0.239
    assert _ver(r) == (True, [])
    r["pair_on"]["surv_contrast_184"] = 0.2406      # rounds to 0.241
    assert _ver(r) == (False, ["V1"])


@pytest.mark.parametrize("t", ["184", "300", "440"])
@pytest.mark.parametrize("cell,lo,hi", [("hpc_E", 0.5, 1.5), ("ctx_E", 3.0, 5.0)])
def test_driver_v2_bands_inclusive(t, cell, lo, hi):
    for ok_val in (lo, hi):
        r = _rec()
        r["hz"][t][cell] = ok_val
        assert _ver(r) == (True, [])
    for bad in (lo - 0.01, hi + 0.01):
        r = _rec()
        r["hz"][t][cell] = bad
        assert _ver(r) == (False, ["V2"])


@pytest.mark.parametrize("cell", ["ctx_E", "hpc_E"])
def test_driver_v2_max_tick_fraction(cell):
    r = _rec()
    r["max_tick_frac"][cell] = 0.20
    assert _ver(r) == (True, [])
    r["max_tick_frac"][cell] = 0.21
    assert _ver(r) == (False, ["V2"])


@pytest.mark.parametrize("key", ["sat", "died"])
@pytest.mark.parametrize("t", ["184", "440"])
@pytest.mark.parametrize("cell", ["ctx_E", "hpc_E"])
def test_driver_v3_bounds_inclusive(key, t, cell):
    r = _rec()
    r[key][t][cell] = 0.20
    assert _ver(r) == (True, [])
    r[key][t][cell] = 0.21
    assert _ver(r) == (False, ["V3"])


def test_driver_c1_delivered_weight_and_spikes_bars():
    r = _rec()
    r["early"]["on"]["deliv_A"] = 1.2
    assert _ver(r) == (True, [])
    r["early"]["on"]["deliv_A"] = 1.19
    assert _ver(r) == (False, ["c1"])
    r = _rec()
    r["early"]["never"]["W_spikes_A"] = 10.0
    r["early"]["on"]["W_spikes_A"] = 12.0
    assert _ver(r) == (True, [])
    r["early"]["on"]["W_spikes_A"] = 11.9
    ok, failed = _ver(r)
    assert not ok and "c1" in failed


def _c2_rec(on_a, on_b, nv_a=10.0, nv_b=2.0):
    r = _rec()
    r["early"]["on"].update(W_spikes_A=on_a, W_spikes_B=on_b)
    r["early"]["never"].update(W_spikes_A=nv_a, W_spikes_B=nv_b)
    return r


def test_driver_c2_selectivity_ratio():
    # S(never) = 10/12 = 0.8333; bar 0.7833
    assert _ver(_c2_rec(12.0, 3.2)) == (True, [])          # S = 0.789
    assert _ver(_c2_rec(12.0, 3.39)) == (False, ["c2"])    # S = 0.780
    # S(on) above S(never) is fine
    assert _ver(_c2_rec(30.0, 1.0)) == (True, [])


def test_driver_c2_b_bar_inclusive():
    # never B = 10: bar is 13.0; S stays high because A is large
    assert _ver(_c2_rec(30.0, 13.0, nv_b=10.0)) == (True, [])
    assert _ver(_c2_rec(30.0, 13.5, nv_b=10.0)) == (False, ["c2"])


def test_driver_c3_late_bar_inclusive():
    r = _rec()
    r["late"]["on"]["deliv_A"] = 1.1
    assert _ver(r) == (True, [])
    r["late"]["on"]["deliv_A"] = 1.09
    assert _ver(r) == (False, ["c3"])


def test_driver_failed_lists_every_failing_clause_in_order():
    r = _rec(3)
    r["pair_on"]["W_cells_full_A_184"] = 1                      # V1
    r["died"]["440"]["hpc_E"] = 0.9                             # V3
    r["hz"]["300"]["ctx_E"] = 9.0                               # V2
    r["late"]["on"]["deliv_A"] = 0.5                            # c3
    r["early"]["on"]["deliv_A"] = 1.0                           # c1
    assert _ver(r) == (False, ["V1", "V2", "V3", "c1", "c3"])
