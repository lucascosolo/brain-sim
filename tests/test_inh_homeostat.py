"""SPEC 8.17: inhibition as the hippocampal rate controller (Vogels-style inhibitory STDP on
hpc E cells, with excitatory scaling and rate-driven elimination exempt on those cells).

Covers: params, brainsim/inhib.py maths (weights stored negative), flag-off identity,
scope/bounds/no-RNG/no-structure of the rule on a real engine, the hpc E exemption in the
slow sweep, Engine.inh_view, rate-direction behaviour, and the pure helpers of the
driver tests/k817_inh_homeostat.py (delivered_exc_onto, verdict).

Ambiguity assumed in inh_view: frac_at_zero = share of the n_syn synapses with w == 0
(m <= 0), frac_at_max = share with m >= m_max (to float32 tolerance); both over n_syn.
"""
import copy
import sys

import numpy as np
import pytest

from brainsim import encode, params
from brainsim.engine import Engine

import tests.k03_pairing as k03
from tests.test_engine_determinism import REFERENCE_DIGEST, _digest, run_schedule


def _eng():
    return Engine(seed=1, params=k03._deepcopyable_params())


def _warm():
    e = _eng()
    e.step(300)  # t = 300; stay below the first slow sweep at t = 1000 in tick-level tests
    return e


def _inh_syn(net):
    al = np.flatnonzero(net.alive)
    return al[~net.is_exc[net.pre[al]]]


def _inh_onto_hpc_e(net):
    s = _inh_syn(net)
    return s[np.isin(net.post[s], encode.hpc_e_ids(net))]


def _hpc_cell_with_inh(net):
    s = _inh_onto_hpc_e(net)
    cnt = np.bincount(net.post[s], minlength=net.n)
    hpc = encode.hpc_e_ids(net)
    return int(hpc[np.argmax(cnt[hpc])])


# ---- E1 params -------------------------------------------------------------------------
def test_params_constants():
    assert params.INH_HOMEOSTAT is False
    assert params.INH_ETA == 0.004
    assert Engine(seed=1).inh_homeostat is False


# ---- E2 inhib maths --------------------------------------------------------------------
def test_inhib_eta_and_alpha():
    from brainsim import inhib
    assert inhib.ETA_DEFAULT == 0.004
    assert inhib.eta(params) == params.INH_ETA
    assert inhib.eta(object()) == 0.004

    class P:
        INH_ETA = 0.01
    assert inhib.eta(P()) == 0.01
    assert inhib.alpha(1.0, 20.0) == pytest.approx(0.04)
    assert np.allclose(inhib.alpha(np.array([0.0, 1.0, 2.5]), 20.0), [0.0, 0.04, 0.1])


def test_on_pre_direction_clamps_gain_and_purity():
    from brainsim import inhib
    w = np.array([-2.0, -2.0, -2.0, -0.001, -7.499], np.float32)
    mmax = np.full(5, 7.5, np.float32)
    w0 = w.copy()
    hi = inhib.on_pre(w, np.full(5, 1.04, np.float32), np.full(5, 0.04, np.float32), mmax, 0.004)
    lo = inhib.on_pre(w, np.zeros(5, np.float32), np.full(5, 0.04, np.float32), mmax, 0.004)
    assert np.array_equal(w, w0)
    assert hi[0] == pytest.approx(-2.0 - 0.004 * 7.5 * 1.0, rel=1e-5)  # stronger inhibition
    assert lo[0] == pytest.approx(-2.0 + 0.004 * 7.5 * 0.04, rel=1e-5)  # weaker inhibition
    assert lo[3] == 0.0                      # clamps at 0 (never turns excitatory)
    assert hi[4] == pytest.approx(-7.5)      # clamps at -m_max
    half = inhib.on_pre(w, np.full(5, 1.04, np.float32), np.full(5, 0.04, np.float32), mmax,
                        0.004, g=0.5)
    assert (half[0] - w[0]) == pytest.approx(0.5 * (hi[0] - w[0]), rel=1e-4)
    assert np.all(hi <= 0) and np.all(lo <= 0)


def test_on_post_only_strengthens_clamps_and_scales():
    from brainsim import inhib
    w = np.array([-2.0, -7.49, 0.0], np.float32)
    mmax = np.full(3, 7.5, np.float32)
    w0 = w.copy()
    out = inhib.on_post(w, np.array([1.0, 1.0, 0.0], np.float32), mmax, 0.004)
    assert np.array_equal(w, w0)
    assert out[0] == pytest.approx(-2.0 - 0.004 * 7.5, rel=1e-5)
    assert out[1] == pytest.approx(-7.5)
    assert out[2] == 0.0
    assert np.all(out <= w0 + 1e-7)
    half = inhib.on_post(w, np.ones(3, np.float32), mmax, 0.004, g=0.3)
    assert (half[0] - w[0]) == pytest.approx(0.3 * (out[0] - w[0]) / 1.0, rel=1e-4)


# ---- E3 flag off -----------------------------------------------------------------------
def test_flag_off_digest_equals_reference():
    assert _digest(run_schedule()) == REFERENCE_DIGEST


def test_flag_off_no_inhibitory_weight_changes():
    e = _warm()
    s = _inh_syn(e.net)
    w0 = e.net.w[s].copy()
    inj = encode.hpc_e_ids(e.net)[:20]
    e.inject(inj, 8.0, 300)
    e.step(600)
    assert np.array_equal(e.net.w[s], w0)


# ---- E4 rule on a real engine ----------------------------------------------------------
def _run_on(ticks=600, with_inject=True):
    e = _warm()
    e.inh_homeostat = True
    twin = copy.deepcopy(e)
    twin.inh_homeostat = False
    cells = encode.hpc_e_ids(e.net)[:40]
    for x in (e, twin):
        if with_inject:
            x.inject(cells, 8.0, 300)
    return e, twin, ticks


def test_rule_scope_only_inhibitory_onto_hpc_e():
    e, twin, ticks = _run_on()
    net = e.net
    s = _inh_syn(net)
    w0 = net.w[s].copy()
    e.step(ticks)
    changed = s[net.w[s] != w0]
    assert changed.size > 0
    assert np.isin(net.post[changed], encode.hpc_e_ids(net)).all()
    assert not net.is_exc[net.pre[changed]].any()
    keep = ~np.isin(net.post[s], encode.hpc_e_ids(net))
    assert np.array_equal(net.w[s][keep], w0[keep])   # ctx and hpc I targets bit-unchanged
    twin.step(ticks)
    assert np.array_equal(twin.net.w[s], w0)          # the flag-off twin changes none


def test_rule_weights_stay_in_bounds():
    e, _, ticks = _run_on()
    net = e.net
    s = _inh_onto_hpc_e(net)
    w0 = net.w[s].copy()
    e.step(ticks)
    assert (net.w[s] != w0).any()  # the rule acted, so the bounds below are not vacuous
    lim = net.w_max_n[net.post[s]] * params.I_GAIN
    assert (net.w[s] <= 0).all()
    assert (net.w[s] >= -lim - 1e-5).all()


def test_rule_draws_no_rng_and_creates_no_structure():
    e, twin, _ = _run_on()
    e.step(100)
    twin.step(100)
    s = _inh_onto_hpc_e(e.net)
    assert (e.net.w[s] != twin.net.w[s]).any()  # the rule acted
    assert e.rng.bit_generator.state == twin.rng.bit_generator.state
    assert np.array_equal(e.net.alive, twin.net.alive)
    assert e.net.s_used == twin.net.s_used


# ---- E5 exemption in the slow sweep ----------------------------------------------------
def _sweep_case(flag):
    e = _eng()
    e.step(300)
    e.inh_homeostat = flag
    net = e.net
    hpc = encode.hpc_e_ids(net)
    e.inject(hpc, 8.0, 300)   # push hpc E far above target so scaling and elimination act
    e.step(300)
    al = np.flatnonzero(net.alive)
    exc = al[net.is_exc[net.pre[al]]]
    onto_h = exc[np.isin(net.post[exc], hpc)]
    onto_c = exc[np.isin(net.post[exc], encode.ctx_e_ids(net))]
    w0h, w0c = net.w[onto_h].copy(), net.w[onto_c].copy()
    ident0 = [(int(a), int(b), int(c)) for a, b, c in
              zip(net.pre[onto_h], net.post[onto_h], net.born[onto_h])]
    weak0 = w0h < params.W_PRUNE_FRAC * net.w_max_n[net.post[onto_h]]
    e._slow_sweep()
    e._ident0, e._weak0, e._w0h = ident0, weak0, w0h
    return net, onto_h, onto_c, w0h, w0c, e


def test_sweep_exempts_hpc_e_but_not_ctx_when_flag_on():
    net, onto_h, onto_c, w0h, w0c, e = _sweep_case(True)
    # compare by synapse identity (pre, post, born): slots can be reused within a sweep
    survivors = 0
    for i, (ident, weak, w0) in enumerate(zip(e._ident0, e._weak0, e._w0h)):
        j = onto_h[i]
        same = (net.alive[j] and (int(net.pre[j]), int(net.post[j]), int(net.born[j])) == ident)
        if same:
            survivors += 1
            assert net.w[j] == w0                       # no scaling
        else:
            assert weak                                 # died only by the weak-weight prune
    assert survivors > 0
    changed_c = (~net.alive[onto_c]) | (net.w[onto_c] != w0c)
    assert changed_c.any()                              # ctx still scaled/pruned


def test_sweep_acts_on_hpc_e_when_flag_off_control():
    net, onto_h, _, w0h, _, _ = _sweep_case(False)
    assert ((~net.alive[onto_h]) | (net.w[onto_h] != w0h)).any()


# ---- E6 inh_view -----------------------------------------------------------------------
def test_inh_view_keys_values_and_read_only():
    e = _warm()
    net = e.net
    s = _inh_onto_hpc_e(net)
    mm = (net.w_max_n[net.post[s]] * params.I_GAIN).astype(np.float32)
    w = -0.5 * mm
    w[: s.size // 4] = 0.0
    w[s.size // 4: s.size // 2] = -mm[s.size // 4: s.size // 2]
    net.w[s] = w
    state = e.rng.bit_generator.state
    w_snap = net.w.copy()
    v = e.inh_view()
    assert set(v) == {"on", "n_syn", "mean_frac", "frac_at_zero", "frac_at_max"}
    assert v["on"] is False and v == e.inh_view()
    assert v["n_syn"] == s.size
    assert v["mean_frac"] == pytest.approx(float(np.mean(-net.w[s] / mm)), rel=1e-4)
    assert v["frac_at_zero"] == pytest.approx(float(np.mean(net.w[s] == 0)), abs=1e-3)
    assert v["frac_at_max"] == pytest.approx(float(np.mean(-net.w[s] >= mm * (1 - 1e-5))), abs=1e-3)
    assert e.rng.bit_generator.state == state and np.array_equal(net.w, w_snap)
    e.inh_homeostat = True
    assert e.inh_view()["on"] is True


# ---- E7 direction ----------------------------------------------------------------------
def _mag(e, c):
    net = e.net
    s = _inh_onto_hpc_e(net)
    s = s[net.post[s] == c]
    return float(np.mean(-net.w[s]))


def test_overdriven_hpc_cell_gains_inhibition_vs_twin():
    e = _warm()
    c = _hpc_cell_with_inh(e.net)
    twin = copy.deepcopy(e)
    e.inh_homeostat, twin.inh_homeostat = True, False
    m0 = _mag(e, c)
    for x in (e, twin):
        x.inject([c], 8.0, 650)
        x.step(650)
    assert x.net.spike_count[c] > 50              # it really fired far above target
    assert _mag(twin, c) == pytest.approx(m0)
    assert _mag(e, c) > m0 * 1.01


def test_silent_hpc_cell_loses_inhibition():
    e = _warm()
    c = _hpc_cell_with_inh(e.net)
    twin = copy.deepcopy(e)
    e.inh_homeostat, twin.inh_homeostat = True, False
    m0 = _mag(e, c)
    n0 = e.net.spike_count[c]
    for x in (e, twin):
        x.inject([c], -8.0, 650)
        x.step(650)
    assert e.net.spike_count[c] == n0             # held silent
    assert _mag(twin, c) == pytest.approx(m0)
    assert _mag(e, c) < m0


# ---- driver helpers --------------------------------------------------------------------
def _k817():
    sys.path.insert(0, "tests")
    import tests.k817_inh_homeostat as k817
    return k817


def test_delivered_exc_onto_matches_independent_sum_and_keeps_trajectory():
    k817 = _k817()
    a, b = _warm(), _warm()
    cells = encode.hpc_e_ids(a.net)
    for x in (a, b):
        x.inject(cells[:30], 8.0, 100)
    ticks = 100
    ref = 0.0
    net, p = b.net, b.p
    for _ in range(ticks):
        bucket = b.ring[b.t % (p.D_MAX + 1)]
        if bucket:
            d = np.concatenate(bucket)
            d = d[net.alive[d] & net.is_exc[net.pre[d]] & np.isin(net.post[d], cells)]
            ref += float(net.w[d].astype(np.float64).sum())
        b.step(1)
    got = k817.delivered_exc_onto(a, cells, ticks)
    assert ref > 0
    assert got == pytest.approx(ref, rel=1e-9)
    twin = _warm()
    twin.inject(cells[:30], 8.0, 100)
    twin.step(ticks)
    assert a.t == twin.t
    assert np.array_equal(a.net.v, twin.net.v) and np.array_equal(a.net.w, twin.net.w)


def _good():
    return dict(seed=1, ref_c2=0.309, ref_c3=1.221, ref_readout=(10, 3, 0),
                hz_184={"hpc_E": 1.0, "ctx_E": 4.0}, hz_300={"hpc_E": 1.0, "ctx_E": 4.0},
                max_hpc_frac_tick=0.10,
                inh_184={"on": True, "n_syn": 100, "mean_frac": 0.4, "frac_at_zero": 0.05,
                         "frac_at_max": 0.05},
                inh_300={"on": True, "n_syn": 100, "mean_frac": 0.4, "frac_at_zero": 0.05,
                         "frac_at_max": 0.05},
                n_trig_W=14, c2_written=0.25, surv_124=0.15, surv_184=0.10,
                full_A={"on": 10, "off": 4, "never": 5})


def test_verdict_passing_record():
    assert _k817().verdict(_good()) == (True, [])


@pytest.mark.parametrize("edit,clause", [
    (dict(ref_c2=0.310), "V1"),
    (dict(ref_c3=1.222), "V1"),
    (dict(ref_readout=(9, 3, 0)), "V1"),
    (dict(hz_184={"hpc_E": 1.6, "ctx_E": 4.0}), "V2"),
    (dict(hz_300={"hpc_E": 1.0, "ctx_E": 2.9}), "V2"),
    (dict(hz_184={"hpc_E": 0.4, "ctx_E": 4.0}), "V2"),
    (dict(hz_300={"hpc_E": 1.0, "ctx_E": 5.1}), "V2"),
    (dict(max_hpc_frac_tick=0.21), "V2"),
    (dict(inh_184={"on": True, "n_syn": 100, "mean_frac": 0.4, "frac_at_zero": 0.15,
                   "frac_at_max": 0.06}), "V3"),
    (dict(inh_300={"on": True, "n_syn": 100, "mean_frac": 0.4, "frac_at_zero": 0.0,
                   "frac_at_max": 0.25}), "V3"),
    (dict(n_trig_W=11), "c1"),
    (dict(c2_written=0.19), "c1"),
    (dict(surv_184=0.07), "c2"),
    (dict(full_A={"on": 7, "off": 3, "never": 4}), "c3"),
    (dict(full_A={"on": 7, "off": 4, "never": 2}), "c3"),
])
def test_verdict_each_clause_fails_alone(edit, clause):
    rec = _good()
    rec.update(edit)
    ok, failed = _k817().verdict(rec)
    assert ok is False and failed == [clause]


def test_verdict_boundaries_pass_and_v1_only_on_seed_1():
    k817 = _k817()
    rec = _good()
    rec.update(hz_184={"hpc_E": 0.5, "ctx_E": 3.0}, hz_300={"hpc_E": 1.5, "ctx_E": 5.0},
               max_hpc_frac_tick=0.20, n_trig_W=12, c2_written=0.20, surv_184=0.075,
               full_A={"on": 9, "off": 5, "never": 5})
    rec["inh_184"] = dict(rec["inh_184"], frac_at_zero=0.10, frac_at_max=0.10)
    assert k817.verdict(rec) == (True, [])
    rec = _good()
    rec.update(seed=2, ref_c2=0.0, ref_c3=0.0, ref_readout=(0, 0, 0))
    assert k817.verdict(rec) == (True, [])
    rec.update(seed=1)
    assert k817.verdict(rec) == (False, ["V1"])


def test_verdict_lists_several_failures_in_clause_order():
    rec = _good()
    rec.update(max_hpc_frac_tick=0.5, n_trig_W=3, full_A={"on": 1, "off": 1, "never": 1})
    assert _k817().verdict(rec) == (False, ["V2", "c1", "c3"])
