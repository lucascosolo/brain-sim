"""Stage 1 contract (SPEC 8.1): gated plasticity (three-factor) candidate, unit tests
+ S1.0 wrapper.

Written before the implementation (brainsim/params.py PLASTICITY_MODE,
brainsim/engine.py Engine.gate / gated _tick / gated _slow_sweep, tests/k03_pairing.py
gate-aware instrument, tests/k013_onset.py warm_end_syn_stats, tests/s10_gated.py
driver). Every test here must fail today for the right reason (missing
attribute/symbol, ValueError not raised, or a numeric assertion) -- never a syntax
error, never a skip. See ~/.cache/scratch/brainsim-gated/API.md for the exact API
these tests pin, and SPEC.md section 8.1 for the contract.
"""
import types

import numpy as np
import pytest

from brainsim import params
from brainsim.net import Network
from brainsim.engine import Engine


def _ns(**overrides):
    """A params namespace built the way tests/k03_pairing.py._deepcopyable_params does,
    with the given attributes overridden afterwards."""
    ns = types.SimpleNamespace(**{k: getattr(params, k) for k in dir(params) if k.isupper()})
    for k, v in overrides.items():
        setattr(ns, k, v)
    return ns


# --------------------------------------------------------------------------- #
# 1. params pins
# --------------------------------------------------------------------------- #

def test_params_pins():
    assert params.PLASTICITY_MODE == "always"


# --------------------------------------------------------------------------- #
# 2. always mode reproduces the determinism reference digest, and gate exists
# --------------------------------------------------------------------------- #

def test_always_mode_reproduces_reference_digest():
    from tests.test_engine_determinism import _digest, REFERENCE_DIGEST

    ns = _ns(PLASTICITY_MODE="always")
    e = Engine(seed=1, params=ns)
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

    assert _digest(e) == REFERENCE_DIGEST
    # Engine.gate exists and is recomputed every tick in BOTH modes (API.md); at the
    # end of this schedule nothing is live, so gate must read 0.
    assert hasattr(e, "gate")
    assert e.gate == 0


# --------------------------------------------------------------------------- #
# 3. unknown mode raises
# --------------------------------------------------------------------------- #

def test_unknown_plasticity_mode_raises():
    ns = _ns(PLASTICITY_MODE="foo")
    with pytest.raises(ValueError):
        Engine(seed=1, params=ns)


# --------------------------------------------------------------------------- #
# 4. gate semantics on the full network
# --------------------------------------------------------------------------- #

def test_gate_semantics_on_full_network():
    ns = _ns(PLASTICITY_MODE="gated")
    eng = Engine(seed=1, params=ns)
    sense = eng.net.region_slice["sense"]

    for _ in range(5):
        eng.step(1)
        assert eng.gate == 0

    eng.present(0, 4)
    for _ in range(4):
        eng.step(1)
        assert eng.gate == 1
    eng.step(1)
    assert eng.gate == 0  # entry expired

    # a non-sense injection (ctx ids) never sets the gate
    eng.inject(list(range(400, 420)), 5.0, 4)
    for _ in range(4):
        eng.step(1)
        assert eng.gate == 0

    # a mixed injection (some sense ids + some ctx ids) is not all-sense either
    mixed = list(range(sense.start, sense.start + 5)) + list(range(400, 405))
    eng.inject(mixed, 5.0, 4)
    for _ in range(4):
        eng.step(1)
        assert eng.gate == 0

    # sleep: present() filters the sense ids out entirely -> nothing queued
    eng.set_sleep(True)
    rec = eng.present(1, 4)
    assert rec is None
    for _ in range(4):
        eng.step(1)
        assert eng.gate == 0


# --------------------------------------------------------------------------- #
# 5/6. gate 0 freezes the sense->ctx nerve but not ctx->ctx scaling; always mode
#      touches both
# --------------------------------------------------------------------------- #

def _alive_pathway(net, pre_slice, post_slice, exc_pre=False):
    pre, post = net.pre, net.post
    m = (net.alive
         & (pre >= pre_slice.start) & (pre < pre_slice.stop)
         & (post >= post_slice.start) & (post < post_slice.stop))
    if exc_pre:
        m &= net.is_exc[pre]
    return np.flatnonzero(m)


def _snapshot(net, idx):
    return {"idx": idx, "pre": net.pre[idx].copy(), "post": net.post[idx].copy(),
            "born": net.born[idx].copy(), "w": net.w[idx].copy()}


def _identity_kept(net, snap):
    idx = snap["idx"]
    return (net.alive[idx] & (net.pre[idx] == snap["pre"])
            & (net.post[idx] == snap["post"]) & (net.born[idx] == snap["born"]))


def test_gate_zero_means_no_stdp_and_frozen_nerve():
    ns = _ns(PLASTICITY_MODE="gated")
    eng = Engine(seed=1, params=ns)
    assert hasattr(eng, "gate")
    net = eng.net
    sense, ctx = net.region_slice["sense"], net.region_slice["ctx"]

    s2c = _snapshot(net, _alive_pathway(net, sense, ctx))
    ee = _snapshot(net, _alive_pathway(net, ctx, ctx, exc_pre=True))

    eng.step(3000)  # three sweeps, no stimulus ever

    keep_s2c = _identity_kept(net, s2c)
    assert keep_s2c.any()
    assert np.array_equal(net.w[s2c["idx"][keep_s2c]], s2c["w"][keep_s2c])

    keep_ee = _identity_kept(net, ee)
    assert keep_ee.any()
    assert not np.array_equal(net.w[ee["idx"][keep_ee]], ee["w"][keep_ee])


def test_always_mode_scaling_touches_the_nerve():
    ns = _ns(PLASTICITY_MODE="always")
    eng = Engine(seed=1, params=ns)
    assert hasattr(eng, "gate")
    net = eng.net
    sense, ctx = net.region_slice["sense"], net.region_slice["ctx"]

    s2c = _snapshot(net, _alive_pathway(net, sense, ctx))
    eng.step(3000)
    keep = _identity_kept(net, s2c)
    assert keep.any()
    assert not np.array_equal(net.w[s2c["idx"][keep]], s2c["w"][keep])


# --------------------------------------------------------------------------- #
# 7. two-neuron pairing rig: gate 1 reproduces today's pair update, gate 0 blocks it
# --------------------------------------------------------------------------- #

def _tiny_sense_ctx_net():
    net = Network.tiny(2, [True, True], [(0, 1, 1.0, 1)])
    net.region_names = ["sense", "ctx"]  # _init_windup iterates region_names
    net.region_slice = {"sense": slice(0, 1), "ctx": slice(1, 2)}
    return net


def _expected_w_after_pairing(eng, net, w0):
    """LTD before injection (zero here, y_post[1]==0), trace decay before the spike
    check, LTP uses the decayed x_pre and the current (post-LTD) w:
        w += g * a_plus[post] * x_pre[pre] * (w_max[post] - w)
    with x_pre = exp(-1/TAU_TRACE_MS) (one decay of the pre spike's unit increment).
    Computed with the same float32 arrays/order engine.py uses so the result matches
    bit-for-bit."""
    x_pre = np.float32(1.0) * eng._tr_decay
    w_arr = np.array([w0], np.float32)
    w_arr += eng.g * net.a_plus_n[1:2] * x_pre * (net.w_max_n[1:2] - w_arr)
    return float(w_arr[0])


def test_gate_one_reproduces_pair_update_on_two_neuron_rig():
    results = {}
    eng = net = w0 = None
    for mode in ("always", "gated"):
        net = _tiny_sense_ctx_net()
        ns = _ns(PLASTICITY_MODE=mode)
        eng = Engine(seed=1, net=net, noise_sigma=0.0, params=ns)
        assert eng._sense is not None  # without a sense region the gate is 0 forever
        eng.set_sense_spont(0.0)
        w0 = float(net.w[0])

        eng.inject(np.array([0]), 60.0, 2)  # pre spike; stim stays live one more tick
        eng.step(1)
        assert eng.gate == 1
        eng.inject(np.array([1]), 60.0, 1)  # post spike
        eng.step(1)
        assert eng.gate == 1

        results[mode] = float(net.w[0])

    expected = _expected_w_after_pairing(eng, net, w0)
    assert results["always"] == expected
    assert results["gated"] == expected


def test_gate_zero_blocks_pair_update_on_two_neuron_rig():
    net_g = _tiny_sense_ctx_net()
    eng_g = Engine(seed=1, net=net_g, noise_sigma=0.0, params=_ns(PLASTICITY_MODE="gated"))
    assert eng_g._sense is not None  # without a sense region the gate is 0 forever
    eng_g.set_sense_spont(0.0)
    w0 = float(net_g.w[0])

    eng_g.inject(np.array([0]), 60.0, 1)  # 1-tick stim: gone by the next tick
    eng_g.step(1)
    assert eng_g.gate == 1
    eng_g.inject(np.array([1]), 60.0, 1)
    eng_g.step(1)
    assert eng_g.gate == 0
    w_gated = float(net_g.w[0])
    assert w_gated == w0  # bit-for-bit unchanged: no LTD, no LTP touched the slot

    net_a = _tiny_sense_ctx_net()
    eng_a = Engine(seed=1, net=net_a, noise_sigma=0.0, params=_ns(PLASTICITY_MODE="always"))
    eng_a.set_sense_spont(0.0)
    eng_a.inject(np.array([0]), 60.0, 1)
    eng_a.step(1)
    eng_a.inject(np.array([1]), 60.0, 1)
    eng_a.step(1)
    w_always = float(net_a.w[0])

    expected = _expected_w_after_pairing(eng_a, net_a, w0)
    assert w_always == expected
    assert w_always != w_gated


# --------------------------------------------------------------------------- #
# 8. sleep gates the sense; nothing all-sense can exist there
# --------------------------------------------------------------------------- #

def test_sleep_gate_zero_even_with_stimulus():
    ns = _ns(PLASTICITY_MODE="gated")
    eng = Engine(seed=1, params=ns)
    ctx = eng.net.region_slice["ctx"]
    eng.set_sleep(True)
    eng.inject(list(range(ctx.start, ctx.start + 20)), 5.0, 3)
    for _ in range(3):
        eng.step(1)
        assert eng.gate == 0


# --------------------------------------------------------------------------- #
# 9/10. k03 instrument, gate-aware, in gated / always mode
# --------------------------------------------------------------------------- #

def _rig_arm(monkeypatch, mode):
    from tests import k03_pairing as k03
    monkeypatch.setattr(k03, "TRIALS", 2)
    monkeypatch.setattr(k03, "TOTAL_TICKS", 2 * k03.TRIAL_TICKS)
    monkeypatch.setattr(params, "PLASTICITY_MODE", mode)  # BEFORE Engine: k03 snapshots it

    eng = k03.Engine(seed=1, params=k03._deepcopyable_params())
    spk = np.zeros((k03.D_MAX + 1, eng.net.n), bool)
    for _ in range(k03.D_MAX):
        t = eng.t
        eng.step(1)
        s = eng._buf_spikes[-1]
        k03._drain_telemetry(eng)
        spk[t % (k03.D_MAX + 1)] = False
        spk[t % (k03.D_MAX + 1), s] = True

    ctx_a = k03.select_ctx_a(eng.net, eng.patterns[0])
    if ctx_a.size == 0:
        pytest.skip("no ctx_a cells selected on this seed/warmup")

    A = eng.patterns[0]
    ctx_a_mask = np.zeros(eng.net.n, bool)
    ctx_a_mask[ctx_a] = True
    sense = eng.net.region_slice["sense"]
    T0 = k03._tracked(eng.net, ctx_a_mask, sense)
    a_mask = np.zeros(eng.net.n, bool)
    a_mask[A] = True
    base = {
        "slots": T0, "pre": eng.net.pre[T0].copy(), "post": eng.net.post[T0].copy(),
        "born": eng.net.born[T0].copy(), "w": eng.net.w[T0].copy(),
        "group": a_mask[eng.net.pre[T0]],
    }
    return k03, eng, spk, ctx_a, A, base


def test_instrument_closes_in_gated_mode(monkeypatch):
    k03, eng, spk, ctx_a, A, base = _rig_arm(monkeypatch, "gated")

    res = k03.run_arm(eng, spk, ctx_a, A, [()] * 2, base, pattern=0, present=True)

    assert res["instrument_max_residual_nonsweep"] == 0.0
    assert res["scaling_pred_vs_resid_max_abs"] == 0.0
    assert res["pair_count_crosscheck_ok"] is True
    assert res["gate_mirror_disagreements"] == 0
    assert res["plasticity_mode"] == "gated"
    assert res["gate_ticks"] == 2 * k03.ON_TICKS
    for name in ("A", "nonA"):
        g = res["groups"][name]
        assert abs(g["closure_residual"]) < 1e-6
        assert g["scaling_mean"] == 0.0
        assert g["scaling_pred_mean"] == 0.0
    gA = res["groups"]["A"]
    assert gA["ltp_mean"] != 0 or gA["ltd_mean"] != 0
    assert 0 <= res["gate_frac_a_spikes"] <= 1


def test_instrument_always_mode_keys_present(monkeypatch):
    k03, eng, spk, ctx_a, A, base = _rig_arm(monkeypatch, "always")

    res = k03.run_arm(eng, spk, ctx_a, A, [()] * 2, base, pattern=0, present=True)

    assert res["gate_mirror_disagreements"] == 0
    assert res["plasticity_mode"] == "always"
    assert res["gate_ticks"] == 2 * k03.ON_TICKS
    assert res["instrument_max_residual_nonsweep"] == 0.0
    assert res["scaling_pred_vs_resid_max_abs"] == 0.0
    for name in ("A", "nonA"):
        assert abs(res["groups"][name]["closure_residual"]) < 1e-6


# --------------------------------------------------------------------------- #
# 11. plasticity_mode context manager restores PLASTICITY_MODE, including on
#     exception
# --------------------------------------------------------------------------- #

def test_plasticity_mode_context_manager_restores():
    from tests import s10_gated as s10

    assert params.PLASTICITY_MODE == "always"
    with s10.plasticity_mode("gated"):
        assert params.PLASTICITY_MODE == "gated"
    assert params.PLASTICITY_MODE == "always"

    with pytest.raises(RuntimeError):
        with s10.plasticity_mode("gated"):
            assert params.PLASTICITY_MODE == "gated"
            raise RuntimeError("boom")
    assert params.PLASTICITY_MODE == "always"

    assert s10.MODE == "gated"
    assert s10.R1_MEAN_MAX == 0.85
    assert s10.R1_CEILING_MAX == 0.05


# --------------------------------------------------------------------------- #
# 12. k013_onset.warm_end_syn_stats
# --------------------------------------------------------------------------- #

def test_k013_warm_end_syn_stats_shape():
    from tests import k013_onset

    eng = Engine(seed=1)  # t == 0; init weights are 0.2-0.6 w_max, no ceiling yet
    stats = k013_onset.warm_end_syn_stats(eng.net)

    for key in ("sense_to_ctx", "ctx_to_ctx_EE"):
        s = stats[key]
        assert s["n"] > 0
        assert 0 <= s["mean_w_over_wmax"] <= 1
        assert 0 <= s["frac_ceiling"] <= 1
    assert stats["sense_to_ctx"]["frac_ceiling"] == 0
    assert stats["ctx_to_ctx_EE"]["frac_ceiling"] == 0


# --------------------------------------------------------------------------- #
# 13. S1.0 wrapper
# --------------------------------------------------------------------------- #

_S10_CACHE = {}


def _s10_result():
    if "result" not in _S10_CACHE:
        from tests import s10_gated as s10
        _S10_CACHE["module"] = s10
        _S10_CACHE["result"] = s10.run_experiment()
    return _S10_CACHE["module"], _S10_CACHE["result"]


@pytest.mark.s1
def test_s1_0_gated_contrast():
    s10, result = _s10_result()
    k013 = s10.k013  # the module object the driver actually ran

    assert s10.SEED == 1
    assert s10.TRIALS == 60
    assert s10.RATIO_THRESHOLD == 1.2
    assert s10.RATIO_GAP == 0.1
    assert s10.BURST_MAX_FRAC == 0.20
    assert s10.MODE == "gated"
    assert s10.R1_MEAN_MAX == 0.85
    assert s10.R1_CEILING_MAX == 0.05

    assert result["plasticity_mode_during_run"] == "gated"
    assert params.PLASTICITY_MODE == "always"  # restored after the run

    assert k013.TRIALS == 60
    assert k013.ON_TICKS == 40
    assert k013.TRIAL_TICKS == 300

    k013_res = result["k013"]
    arms = k013_res["arms"]

    def g(arm, group, key):
        return arms[arm]["groups"][group][key]

    rows = []
    for arm in ("A", "B", "none"):
        rows.append(f"ratio_final[{arm}]={arms[arm].get('ratio_final')}")
    rows.append(f"warm_end_syn_stats={result['warm_end_syn_stats']}")
    rows.append(f"r1={result['r1']}")
    rows.append(f"r2={result['r2']}")
    rows.append(f"gate={result['gate']}")
    for group in ("A", "nonA"):
        for key in ("mean_w_over_wmax_baseline", "mean_w_over_wmax_final", "frac_ceiling_final",
                    "ltp_mean", "ltd_mean", "scaling_mean",
                    "causal_pairs", "anticausal_pairs", "causal_trace_sum", "anticausal_trace_sum"):
            rows.append(f"A/{group}/{key}={g('A', group, key)}")
    rows.append(f"rates_hz[A]={arms['A'].get('rates_hz')}")
    rows.append(f"rates_ema_hz_at_warm_end={result['rates_ema_hz_at_warm_end']}")
    rows.append(f"burst_max_frac={result['burst_max_frac']}")
    rows.append(f"k02={result['k02']}")
    pt = k013_res["probe_table"]
    for state in ("before", "after_A", "after_B", "after_none"):
        rows.append(f"probe[{state}].ctx_A.evoked_A={pt[state]['ctx_A']['evoked_A']}")
        rows.append(f"probe[{state}].S={pt[state]['ctx_A'].get('S')}")
    outcome_report = "\n".join(rows)

    for name, valid in k013_res["validity"].items():
        assert valid, f"INVALID experiment: k013 validity[{name}] failed\n{outcome_report}"
    for arm, frac in result["burst_max_frac"].items():
        assert frac <= 0.20, f"INVALID experiment: burst_max_frac[{arm}]={frac} > 0.20\n{outcome_report}"
    assert result["k02"]["pass"] is True, f"INVALID experiment: k02 failed\n{outcome_report}"
    for arm, gt in result["gate"].items():
        assert gt["mirror_disagreements"] == 0, \
            f"INVALID experiment: gate mirror_disagreements[{arm}]={gt['mirror_disagreements']}\n{outcome_report}"
        assert gt["ticks"] == gt["expected_ticks"], \
            f"INVALID experiment: gate ticks[{arm}]={gt['ticks']} != {gt['expected_ticks']}\n{outcome_report}"

    assert result["r1"]["reject"] == (
        result["r1"]["mean_w_over_wmax"] > 0.85 or result["r1"]["frac_ceiling"] > 0.05
    ), "r1 reject booleans do not match the R1 contract\n" + outcome_report
    assert not result["r1"]["reject"], \
        f"S1.0 REJECT (R1 warm-up ceilings the nerve): {outcome_report}"

    assert k013_res["natural_response_ok"], \
        f"S1.0 REJECT (no natural response at the rest weight): {outcome_report}"

    assert result["r2"]["reject"] == (result["r2"]["net"] < 0), \
        "r2 reject boolean does not match the R2 contract\n" + outcome_report
    assert not result["r2"]["reject"], \
        f"S1.0 REJECT (R2 on-window nets LTD at the rest weight): {outcome_report}"

    assert k013_res["weight_pass"] is True, f"S1.0 REJECT (weight endpoint): {outcome_report}"
