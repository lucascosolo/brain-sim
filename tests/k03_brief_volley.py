"""K0.3 brief-volley diagnostic: one imposed pre-before-post pairing per trial,
drive limited to a single synchronous A volley, alongside the unchanged K0.3
instrument and its protocol/threshold/result of record.

Operational definition (condensed from protocol.md; every number kept)
------------------------------------------------------------------------
Engine: master 83e44ad, unchanged. Diagnostic alongside K0.3; K0.3's protocol,
threshold (ratio >= 1.2) and result (0.927473 pairing / 0.869582 control) stand.
Test-side only: engine RNG never drawn from, nothing forced/reset/gated/frozen;
noise, spontaneous sense (5 Hz), STDP, scaling, structural turnover and the
phase schedule all run unchanged.

Warm state: ``k03.warm_engine(seed=1)`` -- 120,000 ticks, one sleep at 60-80 s.
Targets ctx_A via the unchanged ``select_ctx_a``. Presentation:
``Engine.present(0, ON_TICKS)`` at PATTERN_AMP_MV = 1.3 mV/tick (unchanged
amplitude, only duration differs).

Duration rule R1: ON_TICKS = tick of the 3-tick-moving-sum's first zero after
the first volley peak (peaks at 29, 59, 91 per K0.3's docstring) -> window
centred on tick 40 (ticks 39-41) -> ON_TICKS = 40, OFF_TICKS = 293. (Literal
single-tick rule would land at 35, inside the volley tail; recorded, not run.)
Consequence: drive covers the pulse tick (39) and ends one tick later.

Postsynaptic pulse: ``Engine.inject(ctx_A, 30 mV, 1 tick)`` at offset 39 ticks
after onset -- K0.3's first pulse unchanged (peak 29 + the same 10-tick lag;
exceeds every A->ctx_A delay of 1-4 ticks). One pulse per trial, no lag search.

Trial period 333 ticks, 60 trials = 19,980 ticks (t = 120,000 .. 139,980, all
wake), matching the reference's pulse count (60, 30 mV x 1 tick). At 333 ticks
the A cells' theta increment has decayed to 11% (tau 150 ms).

Expected sensory exposure per A cell: 60 volley spikes + spontaneous 5 Hz x
~17.6 s ~= 88 spikes = ~150 pre spikes (reference: ~160 presentation + ~70
spontaneous = ~230); measured value is reported.

Control arm: same presentations/targets/pulse count/amplitude/duration; one
pulse per trial at an offset drawn uniformly in [0, 333) from
``np.random.default_rng(20260911)`` (K0.3's control seed, never the engine
RNG) -- shuffled timing relative to the volley.

Predeclared intervention-validity criteria (pairing arm; a weak/absent volley,
i.e. any of V1-V4 failing, is an invalid intervention, not evidence about the
learning rule):
  V1  mean pulse spike fraction of ctx_A >= 0.7 (reference 0.80-0.91).
  V2a mean fraction of A cells spiking inside the drive window per trial >= 0.7.
  V2b A rate outside the drive windows <= 8 Hz (spontaneous level).
  V3a pulse-window causal lag median in [5, 25] ms.
  V3b pulse-window causal:anticausal for A > 1.5 (reference 1.25).
  V4a full-interval trace-weighted causal:anticausal, group A >= 2.0 (reference
      protocol 1.389 pairing / 1.045 control, i.e. at least +44% over reference).
  V4b brief-volley control's full-interval trace ratio (A) within [0.8, 1.25].
  V5  instrument: non-sweep residual 0, scaling prediction residual 0,
      pair-count cross-check ok, ring/spike disagreements only within D_MAX
      ticks after a sweep boundary.

Reference frame from the rule (approximation, not a verdict): at equal trace
values and mean weight w, net potentiation needs trace-weighted
causal:anticausal above A- w / (A+ (w_max - w)) -- 3.7 at 0.755 w_max, 1.2 at
the fixed point 0.45 w_max.

Budget: one seed (1), one protocol, one matched control; wall budget 10 min
(warm-up ~1 min, two instrumented arms of 19,980 ticks); no amplitude/duration/
lag variation, no repeat.
"""

import contextlib
import copy
import os
import sys
import time

import numpy as np

if __package__ in (None, ""):  # run directly as `python tests/k03_brief_volley.py`
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import k03_pairing as k03
from brainsim import params

SEED = 1
TRIALS = 60
ON_TICKS = 40
OFF_TICKS = 293
TRIAL_TICKS = 333
TOTAL_TICKS = TRIALS * TRIAL_TICKS
PULSE_OFFSET = 39
CONTROL_RNG_SEED = 20260911
REFERENCE = {
    "pairing": 0.927473, "control": 0.869582,
    "provenance": "SPEC section 7 K0.3 result of record at 3060f23; "
                   "reproduced on the 83e44ad engine 2026-09-12 by the round-11 instrument",
}
THRESHOLD = 1.2


def configure(trials=TRIALS):
    """Override k03's module globals so run_arm/_per_trial read the brief-volley
    schedule instead of K0.3's; PULSE_AMP_MV and PULSE_TICKS are left as-is."""
    k03.TRIALS = trials
    k03.ON_TICKS = ON_TICKS
    k03.OFF_TICKS = OFF_TICKS
    k03.TRIAL_TICKS = TRIAL_TICKS
    k03.TOTAL_TICKS = trials * TRIAL_TICKS


@contextlib.contextmanager
def _restore_k03_globals():
    """configure() overrides k03's module globals for the duration of one
    run_experiment call; restore the originals afterward so importers of
    k03_pairing see it unchanged once this diagnostic returns."""
    saved = (k03.TRIALS, k03.ON_TICKS, k03.OFF_TICKS, k03.TRIAL_TICKS, k03.TOTAL_TICKS)
    try:
        yield
    finally:
        k03.TRIALS, k03.ON_TICKS, k03.OFF_TICKS, k03.TRIAL_TICKS, k03.TOTAL_TICKS = saved


def brief_control_schedule(rng, trials):
    """One pulse per trial, uniform over the whole trial period."""
    return [(int(rng.integers(0, TRIAL_TICKS)),) for _ in range(trials)]


def _record_a_spikes(eng, a_mask, a_pos, n_a, out_counts, out_hits):
    """Wrap eng.step to record, per tick, the A-spike count AND which A cells
    spiked (for the per-trial drive-window cell fraction), delegating to the
    real bound step so the instrument's own tick logic runs unchanged. Reads
    _buf_spikes[-1] before the instrument drains the telemetry buffers itself,
    so it must not drain or otherwise touch them."""
    orig = eng.step

    def step(n):
        for _ in range(n):
            orig(1)
            s = eng._buf_spikes[-1]
            out_counts.append(int(a_mask[s].sum()))
            hit = np.zeros(n_a, bool)
            hit[a_pos[s[a_mask[s]]]] = True
            out_hits.append(hit)
    eng.step = step


def run_experiment(trials=TRIALS):
    with _restore_k03_globals():
        configure(trials)
        out = _run_experiment_inner(trials)
    return out


def _run_experiment_inner(trials):
    eng, spk = k03.warm_engine(SEED)
    net = eng.net
    sense = net.region_slice["sense"]
    A = eng.patterns[0]
    ctx_a = k03.select_ctx_a(net, A)
    assert ctx_a.size > 0, "no ctx_a cells selected"

    ctx_a_mask = np.zeros(net.n, bool)
    ctx_a_mask[ctx_a] = True
    T0 = k03._tracked(net, ctx_a_mask, sense)
    a_mask = np.zeros(net.n, bool)
    a_mask[A] = True
    base = {
        "slots": T0, "pre": net.pre[T0].copy(), "post": net.post[T0].copy(),
        "born": net.born[T0].copy(), "w": net.w[T0].copy(),
        "group": a_mask[net.pre[T0]],
    }
    assert base["group"].any(), "group A empty"
    assert (~base["group"]).any(), "group nonA empty"

    ctrl = copy.deepcopy(eng)
    ctrl_spk = spk.copy()
    ctrl_offsets = brief_control_schedule(np.random.default_rng(CONTROL_RNG_SEED), trials)

    n_a = len(A)
    a_pos = np.full(net.n, -1, np.int64)
    a_pos[A] = np.arange(n_a)
    p_a_counts, c_a_counts = [], []
    p_a_hits, c_a_hits = [], []
    _record_a_spikes(eng, a_mask, a_pos, n_a, p_a_counts, p_a_hits)
    _record_a_spikes(ctrl, a_mask, a_pos, n_a, c_a_counts, c_a_hits)

    pairing = k03.run_arm(eng, spk, ctx_a, A, [(PULSE_OFFSET,)] * trials, base)
    control = k03.run_arm(ctrl, ctrl_spk, ctx_a, A, ctrl_offsets, base)

    A_PLUS = params.REGIONS["ctx"]["a_plus"]
    A_MINUS = params.REGIONS["ctx"]["a_minus"]
    W_MAX = params.REGIONS["ctx"]["w_max"]

    def rule_needed(w):
        return float(A_MINUS * w / (A_PLUS * (W_MAX - w)))

    for arm, counts, hits in ((pairing, p_a_counts, p_a_hits), (control, c_a_counts, c_a_hits)):
        assert len(counts) == trials * TRIAL_TICKS, len(counts)
        psth = np.asarray(counts, np.float64).reshape(trials, TRIAL_TICKS)
        hit_mat = np.asarray(hits, bool).reshape(trials, TRIAL_TICKS, n_a)
        drive = psth[:, :ON_TICKS].sum(axis=1) / n_a
        off_total = psth[:, ON_TICKS:].sum() / n_a
        off_rate_hz = float(off_total * 1000.0 / (trials * OFF_TICKS))
        drive_cell_frac = hit_mat[:, :ON_TICKS, :].any(axis=1).mean(axis=1)
        exposure = {
            "per_trial_drive_spikes_per_cell": drive.tolist(),
            "drive_spikes_per_cell_mean": float(drive.mean()),
            "drive_spikes_per_cell_min": float(drive.min()),
            "drive_spikes_per_cell_max": float(drive.max()),
            "per_trial_drive_cell_frac": drive_cell_frac.tolist(),
            "drive_cell_frac_mean": float(drive_cell_frac.mean()),
            "drive_cell_frac_min": float(drive_cell_frac.min()),
            "drive_cell_frac_max": float(drive_cell_frac.max()),
            "off_spikes_per_cell_total": float(off_total),
            "off_rate_hz": off_rate_hz,
            "total_spikes_per_cell": float(psth.sum() / n_a),
            "mean_psth_0_79": psth[:, :80].mean(axis=0).tolist(),
        }
        # cross-check: the wrapper's independent per-tick A-spike count must
        # agree with the instrument's own a_off rate over the same window.
        assert abs(off_rate_hz - arm["rates_hz"]["a_off"]) < 1e-6, \
            (off_rate_hz, arm["rates_hz"]["a_off"])
        arm["exposure"] = exposure

        trace_ratio_full = {}
        trace_ratio_pulse = {}
        for grp in ("A", "nonA"):
            g = arm["groups"][grp]
            cs, ac = g["causal_trace_sum"], g["anticausal_trace_sum"]
            trace_ratio_full[grp] = float(cs / ac) if ac else float("inf")
            pcs, pac = g["pulse_causal_trace_sum"], g["pulse_anticausal_trace_sum"]
            trace_ratio_pulse[grp] = float(pcs / pac) if pac else float("inf")
        arm["trace_ratio_full"] = trace_ratio_full
        arm["trace_ratio_pulse"] = trace_ratio_pulse

        gA = arm["groups"]["A"]
        arm["rule_needed_ratio"] = {
            "at_baseline_w": rule_needed(gA["mean_w_baseline"]),
            "at_final_w": rule_needed(gA["mean_w_final"]),
        }

    gA_p, gA_c = pairing["groups"]["A"], control["groups"]["A"]
    ep, ec = pairing["exposure"], control["exposure"]
    v = {
        "V1_pulse_frac_mean": pairing["pulse_spike_frac_mean"] >= 0.7,
        "V2a_drive_cell_frac_mean": ep["drive_cell_frac_mean"] >= 0.7,
        "V2b_off_rate_hz": ep["off_rate_hz"] <= 8.0,
        "V3a_pulse_causal_lag_median": 5 <= gA_p["pulse_causal_lag_median"] <= 25,
        "V3b_pulse_causal_over_anticausal": gA_p["pulse_causal_over_anticausal"] > 1.5,
        "V4a_trace_ratio_full_A": pairing["trace_ratio_full"]["A"] >= 2.0,
        "V4b_control_trace_ratio_full_A": 0.8 <= control["trace_ratio_full"]["A"] <= 1.25,
    }
    for arm_name, arm in (("pairing", pairing), ("control", control)):
        ok = (arm["instrument_max_residual_nonsweep"] == 0
              and arm["scaling_pred_vs_resid_max_abs"] == 0
              and arm["pair_count_crosscheck_ok"]
              and all(e[2] for e in arm["ring_vs_spk_events"]))
        v[f"V5_instrument_{arm_name}"] = ok
    v["valid_all"] = all(v.values())

    return {"ctx_a": ctx_a.tolist(), "pairing": pairing, "control": control,
            "control_offsets": ctrl_offsets, "validity": v, "trials": trials}


def main():
    trials = int(sys.argv[1]) if len(sys.argv) > 1 else TRIALS
    t0 = time.time()
    out = run_experiment(trials)
    wall = time.time() - t0
    p, c, v = out["pairing"], out["control"], out["validity"]

    print("=" * 76)
    print("K0.3 brief-volley diagnostic (alongside K0.3; protocol, threshold and "
          "result of record unchanged)")
    print("=" * 76)
    print(f"amp {params.PATTERN_AMP_MV} mV/tick, ON_TICKS {ON_TICKS}, OFF_TICKS {OFF_TICKS}, "
          f"trials {trials}, pulse offset {PULSE_OFFSET}, pulse amp {k03.PULSE_AMP_MV} mV "
          f"x {k03.PULSE_TICKS} tick")
    print(f"run_experiment wall time: {wall:.1f} s")
    print(f"simulated training time: {trials * TRIAL_TICKS / 1000:.3f} s")
    print(f"control offsets: {out['control_offsets']}")
    print()
    print(f"  {'':<34}{'PAIRING':>20}{'CONTROL':>20}")
    for k in ("t_start", "t_end", "phase_start", "phase_end", "sense_gated_end", "g_end",
              "n_sweeps", "pulse_ticks_total", "pulse_spike_frac_mean", "pulse_spike_frac_min",
              "ctx_burst_max_frac", "ctx_burst_max_t", "ctx_burst_max_at_pulse",
              "instrument_max_residual_nonsweep", "scaling_pred_vs_resid_max_abs",
              "pair_count_crosscheck_ok", "pair_count_crosscheck_n",
              "ring_vs_spk_disagreements", "ring_vs_spk_disagreement_slots",
              "ratio_baseline", "ratio_final", "ratio_final_survivors",
              "old_measure_ratio_final"):
        print(k03._row(k, p[k], c[k]))
    print(k03._row("phases_seen", str(p["phases_seen"]), str(c["phases_seen"])))
    print(k03._row("g_seen", str(p["g_seen"]), str(c["g_seen"])))
    print()
    print("  rates (Hz)")
    for k in p["rates_hz"]:
        print(k03._row("  " + k, p["rates_hz"][k], c["rates_hz"][k]))

    for grp in ("A", "nonA"):
        print()
        print(f"  group {grp}")
        gp, gc = p["groups"][grp], c["groups"][grp]
        for k in ("n_baseline", "n_final_alive", "n_survivors", "n_deaths", "n_births",
                  "mean_w_baseline", "mean_w_final",
                  "mean_w_over_wmax_baseline", "mean_w_over_wmax_final",
                  "frac_ceiling_baseline", "frac_ceiling_final",
                  "mean_w_survivors_baseline", "mean_w_survivors_final", "mean_dw_survivors",
                  "mean_w_births_final", "ltp_mean", "ltd_mean", "scaling_mean",
                  "scaling_pred_mean", "closure_residual",
                  "causal_pairs", "anticausal_pairs", "simultaneous_pairs",
                  "causal_trace_sum", "anticausal_trace_sum",
                  "pulse_causal_pairs", "pulse_anticausal_pairs", "pulse_simultaneous_pairs",
                  "pulse_causal_trace_sum", "pulse_anticausal_trace_sum",
                  "pulse_causal_lag_median", "pulse_causal_over_anticausal",
                  "pulse_lag_peak", "pulse_lag_peak_over_median"):
            print(k03._row("  " + k, gp[k], gc[k]))
        print(f"    lag_hist (d=-50..50)       {[int(x) for x in gp['lag_hist']]}")
        print(f"    pulse_lag_hist (d=-50..50) {[int(x) for x in gp['pulse_lag_hist']]}")

    for arm, r in (("PAIRING", p), ("CONTROL", c)):
        print()
        print(f"  per-trial pulse-window pairs, group A ({arm})")
        print(f"    {'trial':>5}{'causal':>12}{'anticausal':>13}{'ratio':>9}"
              f"{'lag_median':>12}{'pulse_frac':>12}{'burst_frac':>12}{'drive_spk/cell':>15}")
        drv = r["exposure"]["per_trial_drive_spikes_per_cell"]
        for k in range(trials):
            ca = r["per_trial_pulse_causal"][k]
            an = r["per_trial_pulse_anticausal"][k]
            rt = ca / an if an else float("inf")
            print(f"    {k:>5}{ca:>12.0f}{an:>13.0f}{rt:>9.3f}"
                  f"{r['per_trial_pulse_lag_median'][k]:>12.1f}"
                  f"{r['per_trial_pulse_spike_frac'][k]:>12.4f}"
                  f"{r['per_trial_ctx_burst_max_frac'][k]:>12.4f}"
                  f"{drv[k]:>15.4f}")
        rr = [ca / an if an else float("inf") for ca, an
              in zip(r["per_trial_pulse_causal"], r["per_trial_pulse_anticausal"])]
        print(f"    per-trial causal:anticausal min {min(rr):.3f}  max {max(rr):.3f}")

    for arm, r in (("PAIRING", p), ("CONTROL", c)):
        print()
        print(f"  exposure ({arm})")
        e = r["exposure"]
        for k in ("drive_spikes_per_cell_mean", "drive_spikes_per_cell_min",
                  "drive_spikes_per_cell_max", "drive_cell_frac_mean",
                  "drive_cell_frac_min", "drive_cell_frac_max",
                  "off_spikes_per_cell_total", "off_rate_hz", "total_spikes_per_cell"):
            print(f"    {k:<34}{e[k]: .6g}")
        print(f"    mean_psth_0_79: {['%.2f' % x for x in e['mean_psth_0_79']]}")

    print()
    print("  trace-weighted causal:anticausal")
    for arm, r in (("PAIRING", p), ("CONTROL", c)):
        print(f"    {arm}: full A {r['trace_ratio_full']['A']:.4f}  "
              f"full nonA {r['trace_ratio_full']['nonA']:.4f}  "
              f"pulse A {r['trace_ratio_pulse']['A']:.4f}  "
              f"pulse nonA {r['trace_ratio_pulse']['nonA']:.4f}")
        rn = r["rule_needed_ratio"]
        print(f"      rule_needed_ratio (approx, equal-trace): "
              f"at_baseline_w {rn['at_baseline_w']:.4f}  at_final_w {rn['at_final_w']:.4f}")

    print()
    print("  validity")
    for k, ok in v.items():
        if k == "valid_all":
            continue
        print(f"    {k:<34}{'PASS' if ok else 'FAIL'}")
    print(f"    {'valid_all':<34}{'PASS' if v['valid_all'] else 'FAIL'}")

    print()
    print(f"REFERENCE full-presentation K0.3 of record: pairing {REFERENCE['pairing']}, "
          f"control {REFERENCE['control']} ({REFERENCE['provenance']})")
    print(f"VERDICT intervention valid: {v['valid_all']}")
    gA_p, gA_c = p["groups"]["A"], c["groups"]["A"]
    ok_pair = gA_p["pulse_causal_pairs"] > gA_p["pulse_anticausal_pairs"]
    print(f"VERDICT pairing established (pulse causal > anticausal, group A): {ok_pair}")
    print(f"VERDICT ratio_final >= {THRESHOLD}: {p['ratio_final'] >= THRESHOLD} "
          f"(ratio_final = {p['ratio_final']:.4f})"
          f" (conditional on intervention valid_all = {v['valid_all']})")
    r_p, r_c = gA_p["pulse_causal_over_anticausal"], gA_c["pulse_causal_over_anticausal"]
    m_p, m_c = gA_p["pulse_lag_peak_over_median"], gA_c["pulse_lag_peak_over_median"]
    l_p, l_c = gA_p["pulse_lag_peak"], gA_c["pulse_lag_peak"]
    print(f"VERDICT control timing: A pulse-window causal:anticausal {r_c:.4f} "
          f"(pairing {r_p:.4f}); histogram peak at {l_c} ms, peak/median {m_c:.4f} "
          f"(pairing: peak at {l_p}, {m_p:.4f}); control disrupted pairing: "
          f"{abs(r_c - 1) < abs(r_p - 1) and m_c < m_p}")

    for arm_name, arm in (("PAIRING", p), ("CONTROL", c)):
        b_frac, b_t, b_pulse = arm["ctx_burst_max_frac"], arm["ctx_burst_max_t"], \
            arm["ctx_burst_max_at_pulse"]
        print(f"K0.2 guard ({arm_name}): largest single-tick ctx fraction {b_frac:.4f} "
              f"at t={b_t}, is a pulse tick: {b_pulse}")

    return out


if __name__ == "__main__":
    main()
