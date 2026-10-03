"""K0.13 baseline: autonomous onset learning, protocol (predeclared 2026-09-12, before the run)

Engine unchanged (master 311d3c4 == 83e44ad). Test-side only: engine RNG never drawn from;
nothing forced/reset/gated/frozen; noise, spontaneous sense (5 Hz), STDP, scaling, turnover
and the phase schedule all run. No postsynaptic injection anywhere: every stimulus is
``Engine.present(pattern, 40)`` at unchanged ``PATTERN_AMP_MV`` (1.3 mV) -- sense cells only.
K0.1/K0.3/K0.4 stay unresolved; K0.13 replaces none of them; the imposed-timing
investigation stays closed.

Constants: SEED 1; warm-up 120,000 ticks (``k03_pairing.warm_engine``, one sleep at
60-80 s); A = patterns[0], B = patterns[1] (40 sense cells each); TRIALS 60; ON_TICKS 40
(first volley only: peak 29 ticks after onset, 3-tick-sum trough at 40); TRIAL_TICKS 300;
training 18,000 ticks = 18 s, t = 120,000..138,000, all wake (sleep starts at 140,000).

Deviation, stated: the section-8 proposal used period 333 (19,980 ticks); the owner's
probe correction needs an after-training probe run in wake from each arm's end state, and
at 333 only 20 wake ticks remain. Rest is shortened 10% to 300 so a 1,500-tick probe fits
(ends 139,500). Trial count and presentation duration (the exposure) are unchanged; no
other schedule tried.

Targets, frozen before training: ctx_A = select_ctx_a(net, A) (ctx cells, E+I, >half of
alive incoming sense synapses from A) on the warmed state before any arm runs; ctx_B = same
with B, secondary/alternative-exposure control. Reported: |A ∩ B|, |ctx_A ∩ ctx_B|, and for
A->ctx_A, B->ctx_A, A->ctx_B, B->ctx_B the alive synapse count and mean w/w_max.

Training, three deepcopies of the warmed state: arm_A 60 x present(0,40) at trial start,
period 300, no injection; arm_B 60 x present(1,40) same schedule; arm_none 18,000 ticks,
nothing presented. Each runs through the K0.3 instrument (run_arm, generalised to zero
pulses / chosen pattern / no presentation), tracked endpoint unchanged (alive A->ctx_A vs
non-A->ctx_A). A step wrapper records per tick the presented pattern's spikes (drive-window
cell fraction) and ctx_A/ctx_B spikes (first-five vs last-five descriptive response);
removed before any further copy, so a probe copy never steps the original.

Probes, on separate discarded copies (training trajectories are never probed in place).
probe(X, state): deepcopy, then 5 x present(X,40) at onsets = probe-start + 20 + k*300,
k=0..4 (1,520 ticks total). States: before (t=120,000), after_A/after_B/after_none (each
arm's t=138,000 end state); both X=A and X=B probed on every state -- 8 copies. Onset is
the commanded (not measured) tick. Response window [onset+25,onset+45), baseline
[onset-20,onset). Volley: fraction of the probed pattern's 40 cells spiking in
[onset,onset+40); <0.7 is "no volley" (reported, not gated). Per pop in {ctx_A (main),
ctx_B (secondary)} (E-only also for ctx_A): evoked(X,state,pop) = mean over 5 presentations
of [spikes(pop,resp) - spikes(pop,basel)]/|pop| (first presentation also reported).
Selectivity S(state,pop) = (evoked_A-evoked_B)/(evoked_A+evoked_B), defined only when
evoked_A>=0, evoked_B>=0 and their sum >= 0.05 (SEL_MIN_SUM); else "undefined", no epsilon.

Success criteria: weight endpoint (K0.3's): ratio_final(arm_A) >= 1.2 AND
ratio_final(arm_A)-ratio_final(arm_B) >= 0.1 AND ratio_final(arm_A)-ratio_final(arm_none)
>= 0.1. Functional F1, on ctx_A: evoked_A(after_A)-evoked_A(after_none) >= 0.15 AND
evoked_A(after_A)-evoked_A(after_B) >= 0.15. Ratios evoked_A(after_A)/evoked_A(after_ctrl)
reported only when the denominator >= 0.05, else "undefined". dS(arm) = S(after_arm) -
S(before), and dS(A)-dS(B), dS(A)-dS(none), reported not gated. Weight and behaviour
reported separately; a disagreement is stated as such.

Input validity (fail = invalid run) vs performance (fail = a result): (a) training volley:
mean drive-window cell fraction >= 0.7 in arm_A (A cells) and arm_B (B cells), min
reported; (b) probe volley: every probe presentation >= 0.7; (c) instrument: non-sweep
residual 0, scaling-prediction residual 0, pair-count cross-check ok in all three arms;
(d) every inject call in the whole experiment targets sense cells only. Performance:
evoked_A(before,ctx_A) >= 0.05 (natural_response_ok); if not met, reported as the headline.

Reference frame from the rule (reading only): at equal trace values and mean weight w, net
potentiation needs trace-weighted causal:anticausal above A- w/(A+ (w_max-w)): 3.6 at
0.75 w_max, 2.1 at 0.64, 1.35 at 0.53, ~1.0 at 0.45.

Budget: one seed, one run, no parameter search, no retention run, no new mechanism, no UI.
"""

import contextlib
import copy
import os
import sys
import time

import numpy as np

if __package__ in (None, ""):  # run directly as `python tests/k013_onset.py`
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import k03_pairing as k03
from brainsim import params

SEED = 1
TRIALS = 60
ON_TICKS = 40
OFF_TICKS = 260
TRIAL_TICKS = 300
PROBE_N = 5
PROBE_LEAD = 20
PROBE_PERIOD = 300
RESP_WIN = (25, 45)
BASE_WIN = (-20, 0)
VOLLEY_MIN_FRAC = 0.7
F1_MIN = 0.15
SEL_MIN_SUM = 0.05
NATURAL_MIN = 0.05
RATIO_DEN_MIN = 0.05
RATIO_THRESHOLD = 1.2
RATIO_GAP = 0.1
PATTERN_A = 0
PATTERN_B = 1
PROBE_TOTAL_TICKS = PROBE_N * PROBE_PERIOD + PROBE_LEAD

A_PLUS = params.REGIONS["ctx"]["a_plus"]
A_MINUS = params.REGIONS["ctx"]["a_minus"]
W_MAX = params.REGIONS["ctx"]["w_max"]


def configure(trials=TRIALS):
    """Override k03's module globals so run_arm/_per_trial read the K0.13 schedule."""
    k03.TRIALS = trials
    k03.ON_TICKS = ON_TICKS
    k03.OFF_TICKS = OFF_TICKS
    k03.TRIAL_TICKS = TRIAL_TICKS
    k03.TOTAL_TICKS = trials * TRIAL_TICKS


@contextlib.contextmanager
def _restore_k03_globals():
    """configure() overrides k03's module globals for the duration of one
    run_experiment call; restore the originals afterward so importers of k03_pairing
    see it unchanged once this script returns."""
    saved = (k03.TRIALS, k03.ON_TICKS, k03.OFF_TICKS, k03.TRIAL_TICKS, k03.TOTAL_TICKS)
    try:
        yield
    finally:
        k03.TRIALS, k03.ON_TICKS, k03.OFF_TICKS, k03.TRIAL_TICKS, k03.TOTAL_TICKS = saved


def _mask(ids, n):
    m = np.zeros(n, bool)
    m[ids] = True
    return m


def _install_inject_log(eng, log):
    """Wrap eng.inject on THIS instance (installed only after it was deepcopy'd) to
    append (t, ids copy, amp, ticks, all_sense) to the shared log and delegate."""
    sense = eng.net.region_slice["sense"]
    orig = eng.inject

    def inject(ids, amp_mv, ticks):
        arr = np.asarray(ids, np.int32).copy()
        all_sense = bool(arr.size == 0 or bool(((arr >= sense.start) & (arr < sense.stop)).all()))
        log.append((int(eng.t), arr, float(amp_mv), int(ticks), all_sense))
        return orig(ids, amp_mv, ticks)
    eng.inject = inject


def _fresh_copy(src_eng, log):
    e = copy.deepcopy(src_eng)
    _install_inject_log(e, log)
    return e


def _install_step_recorder(eng, pat_ids, ctx_a_mask, ctx_b_mask, rec):
    """Wrap eng.step (installed after the copy) recording per tick: count of
    presented-pattern cells spiking, their hit vector, and ctx_A/ctx_B counts."""
    n = eng.net.n
    n_pat = int(pat_ids.size)
    pat_mask = _mask(pat_ids, n) if n_pat else np.zeros(n, bool)
    pat_pos = np.full(n, -1, np.int64)
    if n_pat:
        pat_pos[pat_ids] = np.arange(n_pat)
    orig = eng.step

    def step(k):
        for _ in range(k):
            orig(1)
            s = eng._buf_spikes[-1]
            rec["pat_count"].append(int(pat_mask[s].sum()))
            hit = np.zeros(n_pat, bool)
            if n_pat:
                sel = s[pat_mask[s]]
                if sel.size:
                    hit[pat_pos[sel]] = True
            rec["pat_hits"].append(hit)
            rec["ctx_a_count"].append(int(ctx_a_mask[s].sum()))
            rec["ctx_b_count"].append(int(ctx_b_mask[s].sum()))
    eng.step = step


def probe(e, X, ctx_a, ctx_a_e, ctx_b, A, B):
    """5 presentations of pattern X on a discarded copy; return evoked/volley stats."""
    n = e.net.n
    ctx_a_mask, ctx_ae_mask, ctx_b_mask = _mask(ctx_a, n), _mask(ctx_a_e, n), _mask(ctx_b, n)
    pat_ids = A if X == PATTERN_A else B
    n_pat = pat_ids.size
    pat_mask = _mask(pat_ids, n)
    pat_pos = np.full(n, -1, np.int64)
    pat_pos[pat_ids] = np.arange(n_pat)

    ca = np.zeros(PROBE_TOTAL_TICKS, np.int32)
    cae = np.zeros(PROBE_TOTAL_TICKS, np.int32)
    cb = np.zeros(PROBE_TOTAL_TICKS, np.int32)
    hits = np.zeros((PROBE_TOTAL_TICKS, n_pat), bool)

    onsets = [k * PROBE_PERIOD + PROBE_LEAD for k in range(PROBE_N)]
    onset_set = set(onsets)
    for k_local in range(PROBE_TOTAL_TICKS):
        if k_local in onset_set:
            e.present(X, ON_TICKS)
        e.step(1)
        s = e._buf_spikes[-1]
        k03._drain_telemetry(e)
        ca[k_local] = int(ctx_a_mask[s].sum())
        cae[k_local] = int(ctx_ae_mask[s].sum())
        cb[k_local] = int(ctx_b_mask[s].sum())
        sel = s[pat_mask[s]]
        if sel.size:
            hits[k_local, pat_pos[sel]] = True

    def ev(counts, pop_size):
        vals = []
        for onset in onsets:
            resp = float(counts[onset + RESP_WIN[0]:onset + RESP_WIN[1]].sum())
            basel = float(counts[onset + BASE_WIN[0]:onset + BASE_WIN[1]].sum())
            vals.append((resp - basel) / pop_size)
        return {"evoked": vals, "mean": float(np.mean(vals)), "first": float(vals[0])}

    volley = [float(hits[o:o + 40].any(axis=0).mean()) for o in onsets]
    return {
        "ctx_A": ev(ca, ctx_a.size), "ctx_A_E": ev(cae, ctx_a_e.size), "ctx_B": ev(cb, ctx_b.size),
        "volley_fracs": volley, "volley_min": float(min(volley)),
    }


def _trial_evoked(counts, trial, pop_size):
    """Response-minus-baseline for one training presentation, same windows as probe().
    Trial 0's baseline reaches before training start; ticks before t=0 are treated as
    zero-count (no recording exists there), so trial 0's baseline is an underestimate."""
    onset = trial * TRIAL_TICKS

    def wsum(lo, hi):
        lo2, hi2 = max(0, onset + lo), max(0, onset + hi)
        return float(counts[lo2:hi2].sum()) if hi2 > lo2 else 0.0
    return (wsum(*RESP_WIN) - wsum(*BASE_WIN)) / pop_size


def _descriptive(counts, pop_size, trials):
    """Trial 0 is excluded from the early window: its baseline precedes the recorded
    ticks (see _trial_evoked), so early uses trials 2-6 (indices 1..5) when available."""
    n_edge = min(5, trials)
    early_idx = list(range(1, min(1 + n_edge, trials))) if trials > 1 else []
    late_idx = list(range(max(0, trials - n_edge), trials))
    early = [_trial_evoked(counts, k, pop_size) for k in early_idx] or [float("nan")]
    late = [_trial_evoked(counts, k, pop_size) for k in late_idx]
    return {"early_mean": float(np.mean(early)), "late_mean": float(np.mean(late)),
            "early_idx": early_idx, "late_idx": late_idx}


def _exposure_stats(rec, n_pat, trials):
    counts = np.asarray(rec["pat_count"], np.float64).reshape(trials, TRIAL_TICKS)
    hits = np.asarray(rec["pat_hits"], bool).reshape(trials, TRIAL_TICKS, n_pat)
    drive = counts[:, :ON_TICKS].sum(axis=1) / n_pat
    off_total = counts[:, ON_TICKS:].sum() / n_pat
    off_rate_hz = float(off_total * 1000.0 / (trials * OFF_TICKS))
    drive_frac = hits[:, :ON_TICKS, :].any(axis=1).mean(axis=1)
    return {
        "drive_spikes_per_cell_mean": float(drive.mean()), "drive_spikes_per_cell_min": float(drive.min()),
        "drive_cell_frac_mean": float(drive_frac.mean()), "drive_cell_frac_min": float(drive_frac.min()),
        "off_rate_hz": off_rate_hz,
    }


def _syn_stats(net, src_ids, ctx_ids):
    m = net.alive & _mask(src_ids, net.n)[net.pre] & _mask(ctx_ids, net.n)[net.post]
    idx = np.flatnonzero(m)
    if idx.size == 0:
        return {"n": 0, "mean_w_over_wmax": float("nan")}
    w = net.w[idx].astype(np.float64)
    wmax = net.w_max_n[net.post[idx]].astype(np.float64)
    return {"n": int(idx.size), "mean_w_over_wmax": float((w / wmax).mean())}


def selectivity(ev_a, ev_b):
    if ev_a >= 0 and ev_b >= 0 and (ev_a + ev_b) >= SEL_MIN_SUM:
        return (ev_a - ev_b) / (ev_a + ev_b)
    return "undefined"


def _delta_s(s_after, s_before):
    if s_after == "undefined" or s_before == "undefined":
        return "undefined"
    return s_after - s_before


def _diff(a, b):
    if a == "undefined" or b == "undefined":
        return "undefined"
    return a - b


def ratio_or_undef(num, den):
    return float(num / den) if den >= RATIO_DEN_MIN else "undefined"


def rule_needed(w):
    return float(A_MINUS * w / (A_PLUS * (W_MAX - w)))


# --------------------------------------------------------------------------- #
# experiment
# --------------------------------------------------------------------------- #

def run_experiment(trials=TRIALS):
    with _restore_k03_globals():
        configure(trials)
        out = _run_experiment_inner(trials)
    return out


def _run_experiment_inner(trials):
    inject_log = []
    eng, spk = k03.warm_engine(SEED)
    net = eng.net
    A, B = eng.patterns[PATTERN_A], eng.patterns[PATTERN_B]
    ctx_a = k03.select_ctx_a(net, A)
    ctx_b = k03.select_ctx_a(net, B)
    assert ctx_a.size > 0 and ctx_b.size > 0
    ctx_a_e = ctx_a[net.is_exc[ctx_a]]

    ctx_a_mask = _mask(ctx_a, net.n)
    ctx_b_mask = _mask(ctx_b, net.n)
    a_mask = _mask(A, net.n)
    T0 = k03._tracked(net, ctx_a_mask, net.region_slice["sense"])
    base = {"slots": T0, "pre": net.pre[T0].copy(), "post": net.post[T0].copy(),
            "born": net.born[T0].copy(), "w": net.w[T0].copy(), "group": a_mask[net.pre[T0]]}
    assert base["group"].any() and (~base["group"]).any()

    overlap = {
        "A_and_B": int(np.intersect1d(A, B).size),
        "ctxA_and_ctxB": int(np.intersect1d(ctx_a, ctx_b).size),
        "A_to_ctxA": _syn_stats(net, A, ctx_a), "B_to_ctxA": _syn_stats(net, B, ctx_a),
        "A_to_ctxB": _syn_stats(net, A, ctx_b), "B_to_ctxB": _syn_stats(net, B, ctx_b),
    }

    probes_before = {
        "A": probe(_fresh_copy(eng, inject_log), PATTERN_A, ctx_a, ctx_a_e, ctx_b, A, B),
        "B": probe(_fresh_copy(eng, inject_log), PATTERN_B, ctx_a, ctx_a_e, ctx_b, A, B),
    }

    arms, exposures, descriptive = {}, {}, {}
    for name, pattern, present_ in (("A", PATTERN_A, True), ("B", PATTERN_B, True),
                                     ("none", PATTERN_A, False)):
        arm_eng = _fresh_copy(eng, inject_log)
        rec = {"pat_count": [], "pat_hits": [], "ctx_a_count": [], "ctx_b_count": []}
        pat_ids = {"A": A, "B": B, "none": np.empty(0, np.int64)}[name]
        _install_step_recorder(arm_eng, pat_ids, ctx_a_mask, ctx_b_mask, rec)
        res = k03.run_arm(arm_eng, spk.copy(), ctx_a, A, [()] * trials, base,
                           pattern=pattern, present=present_)
        del arm_eng.step
        del arm_eng.inject
        assert "step" not in arm_eng.__dict__ and "inject" not in arm_eng.__dict__
        arms[name] = {"res": res, "eng": arm_eng}
        if pat_ids.size:
            exposures[name] = _exposure_stats(rec, pat_ids.size, trials)
        if name == "A":
            assert abs(exposures["A"]["off_rate_hz"] - res["rates_hz"]["a_off"]) < 1e-6, \
                (exposures["A"]["off_rate_hz"], res["rates_hz"]["a_off"])
            descriptive["A_ctxA"] = _descriptive(
                np.asarray(rec["ctx_a_count"], np.float64), ctx_a.size, trials)
        if name == "B":
            descriptive["B_ctxB"] = _descriptive(
                np.asarray(rec["ctx_b_count"], np.float64), ctx_b.size, trials)

    probes_after = {}
    for name in ("A", "B", "none"):
        e = arms[name]["eng"]
        probes_after[name] = {
            "A": probe(_fresh_copy(e, inject_log), PATTERN_A, ctx_a, ctx_a_e, ctx_b, A, B),
            "B": probe(_fresh_copy(e, inject_log), PATTERN_B, ctx_a, ctx_a_e, ctx_b, A, B),
        }

    states = {"before": probes_before, "after_A": probes_after["A"],
              "after_B": probes_after["B"], "after_none": probes_after["none"]}
    probe_table = {}
    for state, pr in states.items():
        row = {}
        for pop in ("ctx_A", "ctx_A_E", "ctx_B"):
            ev_a, ev_b = pr["A"][pop]["mean"], pr["B"][pop]["mean"]
            row[pop] = {"evoked_A": ev_a, "evoked_B": ev_b,
                        "first_A": pr["A"][pop]["first"], "first_B": pr["B"][pop]["first"],
                        "S": selectivity(ev_a, ev_b),
                        "volley_min_A": pr["A"]["volley_min"], "volley_min_B": pr["B"]["volley_min"]}
        probe_table[state] = row

    res_a, res_b, res_n = arms["A"]["res"], arms["B"]["res"], arms["none"]["res"]
    ratio_a, ratio_b, ratio_n = res_a["ratio_final"], res_b["ratio_final"], res_n["ratio_final"]
    weight_pass = (ratio_a >= RATIO_THRESHOLD and ratio_a - ratio_b >= RATIO_GAP
                   and ratio_a - ratio_n >= RATIO_GAP)

    evA_after_A = probe_table["after_A"]["ctx_A"]["evoked_A"]
    evA_after_B = probe_table["after_B"]["ctx_A"]["evoked_A"]
    evA_after_none = probe_table["after_none"]["ctx_A"]["evoked_A"]
    evA_before = probe_table["before"]["ctx_A"]["evoked_A"]
    f1_vs_none = evA_after_A - evA_after_none >= F1_MIN
    f1_vs_b = evA_after_A - evA_after_B >= F1_MIN
    f1_pass = f1_vs_none and f1_vs_b

    ratios = {"after_A_over_after_B": ratio_or_undef(evA_after_A, evA_after_B),
              "after_A_over_after_none": ratio_or_undef(evA_after_A, evA_after_none)}

    delta_s = {}
    for name in ("A", "B", "none"):
        delta_s[name] = _delta_s(probe_table["after_" + name]["ctx_A"]["S"],
                                  probe_table["before"]["ctx_A"]["S"])
    delta_s_diff = {"A_minus_B": _diff(delta_s["A"], delta_s["B"]),
                    "A_minus_none": _diff(delta_s["A"], delta_s["none"])}

    gA = res_a["groups"]["A"]
    trace_ratio_full = float(gA["causal_trace_sum"] / gA["anticausal_trace_sum"]) \
        if gA["anticausal_trace_sum"] else float("inf")
    rule_needed_ratio = {"at_baseline_w": rule_needed(gA["mean_w_baseline"]),
                          "at_final_w": rule_needed(gA["mean_w_final"])}

    validity = {
        "a_training_volley": min(exposures["A"]["drive_cell_frac_mean"],
                                  exposures["B"]["drive_cell_frac_mean"]) >= VOLLEY_MIN_FRAC,
        "b_probe_volley": min(v["volley_min"] for v in
                               (probes_before["A"], probes_before["B"],
                                probes_after["A"]["A"], probes_after["A"]["B"],
                                probes_after["B"]["A"], probes_after["B"]["B"],
                                probes_after["none"]["A"], probes_after["none"]["B"])
                               ) >= VOLLEY_MIN_FRAC,
        "c_instrument": all(
            r["instrument_max_residual_nonsweep"] == 0 and r["scaling_pred_vs_resid_max_abs"] == 0
            and r["pair_count_crosscheck_ok"] for r in (res_a, res_b, res_n)),
        "d_inject_sense_only": bool(inject_log) and all(e[4] for e in inject_log),
    }
    validity["valid_all"] = all(validity.values())
    natural_response_ok = evA_before >= NATURAL_MIN
    expected_inject_calls = trials * 2 + 8 * PROBE_N
    assert len(inject_log) == expected_inject_calls, (len(inject_log), expected_inject_calls)

    return {
        "expected_inject_calls": expected_inject_calls,
        "trials": trials, "ctx_a": ctx_a, "ctx_b": ctx_b, "overlap": overlap,
        "arms": {k: v["res"] for k, v in arms.items()}, "exposures": exposures,
        "descriptive": descriptive, "probe_table": probe_table, "probes_by_state": states,
        "weight_pass": weight_pass, "f1_pass": f1_pass, "f1_vs_none": f1_vs_none,
        "f1_vs_b": f1_vs_b, "ratios": ratios, "delta_s": delta_s, "delta_s_diff": delta_s_diff,
        "trace_ratio_full": trace_ratio_full, "rule_needed_ratio": rule_needed_ratio,
        "validity": validity, "natural_response_ok": natural_response_ok,
        "inject_log": inject_log,
    }


# --------------------------------------------------------------------------- #
# report
# --------------------------------------------------------------------------- #

def main():
    trials = int(sys.argv[1]) if len(sys.argv) > 1 else TRIALS
    t0 = time.time()
    out = run_experiment(trials)
    wall = time.time() - t0

    print("=" * 76)
    print("K0.13 baseline: autonomous onset learning (no postsynaptic injection; "
          "engine unchanged)")
    print("=" * 76)
    print(f"SEED {SEED}  TRIALS {trials}  ON_TICKS {ON_TICKS}  OFF_TICKS {OFF_TICKS}  "
          f"TRIAL_TICKS {TRIAL_TICKS}")
    print("deviation: rest interval shortened from the proposed 333-tick period to 300 "
          "(10% shorter) so the after-training probe (1,500 ticks) fits inside wake; "
          "trial count and presentation duration are unchanged.")
    print(f"run_experiment wall time: {wall:.1f} s")
    print(f"simulated training time per arm: {trials * TRIAL_TICKS / 1000:.3f} s "
          f"(x3 arms); probes: {PROBE_TOTAL_TICKS / 1000:.3f} s each x 8 copies")

    ov = out["overlap"]
    print()
    print("  overlap (warmed state)")
    print(f"    |A ∩ B| (sense cells)          {ov['A_and_B']}")
    print(f"    |ctx_A ∩ ctx_B|                {ov['ctxA_and_ctxB']}")
    for k in ("A_to_ctxA", "B_to_ctxA", "A_to_ctxB", "B_to_ctxB"):
        s = ov[k]
        print(f"    {k:<20} n={s['n']:<6} mean_w/w_max={s['mean_w_over_wmax']:.4f}")

    key_list = ("t_start", "t_end", "phase_start", "phase_end", "sense_gated_end", "g_end",
                "n_sweeps", "pulse_ticks_total", "instrument_max_residual_nonsweep",
                "scaling_pred_vs_resid_max_abs", "pair_count_crosscheck_ok",
                "ring_vs_spk_disagreements", "ratio_baseline", "ratio_final",
                "ratio_final_survivors", "old_measure_ratio_final",
                "ctx_burst_max_frac", "ctx_burst_max_t", "ctx_burst_max_at_pulse")
    group_keys = ("n_baseline", "n_final_alive", "n_survivors", "n_deaths", "n_births",
                  "mean_w_baseline", "mean_w_final", "mean_w_over_wmax_baseline",
                  "mean_w_over_wmax_final", "frac_ceiling_baseline", "frac_ceiling_final",
                  "mean_w_survivors_baseline", "mean_w_survivors_final", "mean_dw_survivors",
                  "mean_w_births_final", "ltp_mean", "ltd_mean", "scaling_mean",
                  "scaling_pred_mean", "closure_residual", "causal_pairs", "anticausal_pairs",
                  "simultaneous_pairs", "causal_trace_sum", "anticausal_trace_sum")
    for name in ("A", "B", "none"):
        r = out["arms"][name]
        print()
        print(f"  arm_{name}  (pattern_presented={r['pattern_presented']})")
        for k in key_list:
            print(f"    {k:<34}{r[k]}")
        print("    rates_hz: " + ", ".join(f"{k}={v:.3f}" for k, v in r["rates_hz"].items()))
        for grp in ("A", "nonA"):
            print(f"    group {grp}")
            g = r["groups"][grp]
            for k in group_keys:
                print(f"      {k:<32}{g[k]}")
        if name in out["exposures"]:
            e = out["exposures"][name]
            print(f"    drive-window: cell_frac mean/min "
                  f"{e['drive_cell_frac_mean']:.4f}/{e['drive_cell_frac_min']:.4f}  "
                  f"spikes/cell mean/min {e['drive_spikes_per_cell_mean']:.4f}/"
                  f"{e['drive_spikes_per_cell_min']:.4f}  off_rate_hz {e['off_rate_hz']:.3f}")
    for k, d in out["descriptive"].items():
        e_lbl = f"{d['early_idx'][0] + 1}-{d['early_idx'][-1] + 1}" if d["early_idx"] else "none"
        l_lbl = f"{d['late_idx'][0] + 1}-{d['late_idx'][-1] + 1}" if d["late_idx"] else "none"
        print(f"  descriptive training response {k}: early(trials {e_lbl}) {d['early_mean']:.4f}  "
              f"late(trials {l_lbl}) {d['late_mean']:.4f}")

    print()
    print("  per-presentation probe volley fractions")
    for state in ("before", "after_A", "after_B", "after_none"):
        pr = out["probes_by_state"][state]
        for pattern in ("A", "B"):
            fr = " ".join(f"{x:.3f}" for x in pr[pattern]["volley_fracs"])
            print(f"    {state:<12}{pattern:<4}{fr}")

    print()
    print("  probe table")
    print(f"    {'state':<12}{'pop':<10}{'evoked_A':>10}{'first_A':>10}{'evoked_B':>10}"
          f"{'first_B':>10}{'S':>12}{'volley_A':>10}{'volley_B':>10}")
    for state in ("before", "after_A", "after_B", "after_none"):
        for pop in ("ctx_A", "ctx_A_E", "ctx_B"):
            row = out["probe_table"][state][pop]
            s_str = row["S"] if isinstance(row["S"], str) else f"{row['S']:.4f}"
            print(f"    {state:<12}{pop:<10}{row['evoked_A']:>10.4f}{row['first_A']:>10.4f}"
                  f"{row['evoked_B']:>10.4f}{row['first_B']:>10.4f}{s_str:>12}"
                  f"{row['volley_min_A']:>10.4f}{row['volley_min_B']:>10.4f}")

    print()
    print("  F1 (ctx_A, spikes/cell/presentation)")
    print(f"    evoked_A(after_A)={probe_table_val(out, 'after_A'):.4f}  "
          f"evoked_A(after_B)={probe_table_val(out, 'after_B'):.4f}  "
          f"evoked_A(after_none)={probe_table_val(out, 'after_none'):.4f}  "
          f"evoked_A(before)={probe_table_val(out, 'before'):.4f}")
    print(f"    after_A - after_none = "
          f"{probe_table_val(out, 'after_A') - probe_table_val(out, 'after_none'):.4f} "
          f">= {F1_MIN}: {out['f1_vs_none']}")
    print(f"    after_A - after_B = "
          f"{probe_table_val(out, 'after_A') - probe_table_val(out, 'after_B'):.4f} "
          f">= {F1_MIN}: {out['f1_vs_b']}")
    for k, v in out["ratios"].items():
        print(f"    ratio {k}: {v}")

    print()
    print("  weight endpoint")
    ra = out["arms"]["A"]["ratio_final"]
    rb = out["arms"]["B"]["ratio_final"]
    rn = out["arms"]["none"]["ratio_final"]
    print(f"    ratio_final: A {ra:.6f}  B {rb:.6f}  none {rn:.6f}")
    print(f"    A >= {RATIO_THRESHOLD}: {ra >= RATIO_THRESHOLD}   "
          f"A-B >= {RATIO_GAP}: {ra - rb >= RATIO_GAP}   "
          f"A-none >= {RATIO_GAP}: {ra - rn >= RATIO_GAP}")

    print()
    print("  selectivity change (ctx_A)")
    for name in ("A", "B", "none"):
        v = out["delta_s"][name]
        print(f"    dS({name}): {v if isinstance(v, str) else round(v, 4)}")
    for k, v in out["delta_s_diff"].items():
        print(f"    {k}: {v if isinstance(v, str) else round(v, 4)}")

    print()
    rn_ = out["rule_needed_ratio"]
    print(f"  trace_ratio_full (A->ctx_A, arm_A) {out['trace_ratio_full']:.4f}  "
          f"vs rule_needed at_baseline_w {rn_['at_baseline_w']:.4f}  "
          f"at_final_w {rn_['at_final_w']:.4f}")

    print()
    print("  validity")
    v = out["validity"]
    for k in ("a_training_volley", "b_probe_volley", "c_instrument", "d_inject_sense_only"):
        print(f"    {k:<28}{v[k]}   {'PASS' if v[k] else 'FAIL'}")
    print(f"    {'valid_all':<28}{v['valid_all']}   {'PASS' if v['valid_all'] else 'FAIL'}")
    print(f"    natural_response_ok        {out['natural_response_ok']}")

    log = out["inject_log"]
    n_bad = sum(0 if e[4] else 1 for e in log)
    print()
    print(f"  injection audit: {len(log)} inject call(s) (expected "
          f"{out['expected_inject_calls']} = trials*2 + 8*{PROBE_N}), {n_bad} non-sense "
          f"call(s) (must be 0)")

    print()
    print(f"VERDICT input valid: {v['valid_all']}")
    print(f"VERDICT natural response present: {out['natural_response_ok']}")
    print(f"VERDICT weight endpoint (ratio >= {RATIO_THRESHOLD} and gaps >= {RATIO_GAP}): "
          f"{out['weight_pass']}")
    print(f"VERDICT functional F1: {out['f1_pass']}")
    agree = "agree" if out["weight_pass"] == out["f1_pass"] else "disagree"
    print(f"VERDICT weight vs behaviour: {agree}")
    return out


def probe_table_val(out, state):
    return out["probe_table"][state]["ctx_A"]["evoked_A"]


if __name__ == "__main__":
    main()
