"""S1.0: the Stage 1 contract driver for the gated-plasticity candidate (SPEC 8.1).

Runs the K0.13 onset-learning protocol with ``params.PLASTICITY_MODE`` switched to
"gated" (the pair rule of record gated by an all-sense-stimulus modulator, STDP off
at rest, sense->ctx frozen for scaling) instead of the always-on Stage 0 path, then
evaluates the predeclared reject criteria R1 (warm-up ceilings the nerve) and R2
(the on-window nets LTD at the measured rest weight) and the unchanged S1.0 weight
endpoint and validity checks. See SPEC.md section 8.1 for the contract.
"""
import contextlib
import math
import os
import sys
import time

if __package__ in (None, ""):  # run directly as `python tests/s10_gated.py`
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import k013_onset as k013
from brainsim import params

SEED = 1
TRIALS = 60
RATIO_THRESHOLD = 1.2
RATIO_GAP = 0.1
BURST_MAX_FRAC = 0.20
MODE = "gated"
R1_MEAN_MAX = 0.85
R1_CEILING_MAX = 0.05


@contextlib.contextmanager
def plasticity_mode(mode):
    prev = params.PLASTICITY_MODE
    params.PLASTICITY_MODE = mode
    try:
        yield
    finally:
        params.PLASTICITY_MODE = prev


def run_k02_guard():
    t0 = time.time()
    with plasticity_mode(MODE):
        from tests.test_kill_stage0 import test_k0_2_stability_over_60s_wake
        try:
            test_k0_2_stability_over_60s_wake()
        except Exception as e:  # any failure, not only an assertion, must not discard the k013 result
            return {"pass": False, "message": f"{type(e).__name__}: {e}", "wall_s": time.time() - t0}
    return {"pass": True, "message": "", "wall_s": time.time() - t0}


def run_experiment(trials=TRIALS, k02_guard=True):
    prev = params.PLASTICITY_MODE
    with plasticity_mode(MODE):
        k013_res = k013.run_experiment(trials)
        mode_during_run = params.PLASTICITY_MODE
        k02 = run_k02_guard() if k02_guard else {"pass": None, "message": "not run", "wall_s": 0.0}
    assert params.PLASTICITY_MODE == prev

    arms = k013_res["arms"]
    nerve = k013_res["warm_end_syn_stats"]["sense_to_ctx"]
    r1 = {
        "mean_w_over_wmax": nerve["mean_w_over_wmax"],
        "frac_ceiling": nerve["frac_ceiling"],
        "reject": bool(nerve["mean_w_over_wmax"] > R1_MEAN_MAX
                       or nerve["frac_ceiling"] > R1_CEILING_MAX),
    }
    gA = arms["A"]["groups"]["A"]
    net_a = gA["ltp_mean"] + gA["ltd_mean"]
    r2 = {
        "ltp_mean": gA["ltp_mean"],
        "ltd_mean": gA["ltd_mean"],
        "net": net_a,
        "rule_needed_at_rest": k013.rule_needed(gA["mean_w_baseline"]),
        "trace_ratio_full": k013_res["trace_ratio_full"],
        "reject": bool(net_a < 0),
    }
    gate = {}
    for name, arm in arms.items():
        gate[name] = {
            "ticks": arm["gate_ticks"],
            "expected_ticks": trials * k013.ON_TICKS if name in ("A", "B") else 0,
            "mirror_disagreements": arm["gate_mirror_disagreements"],
            "frac_a_spikes": arm["gate_frac_a_spikes"],
            "frac_ctxa_spikes": arm["gate_frac_ctxa_spikes"],
        }
    return {
        "k013": k013_res,
        "k02": k02,
        "plasticity_mode_during_run": mode_during_run,
        "rates_ema_hz_at_warm_end": k013_res["warm_end_rates_ema_hz"],
        "warm_end_syn_stats": k013_res["warm_end_syn_stats"],
        "r1": r1,
        "r2": r2,
        "gate": gate,
        "burst_max_frac": {name: arm["ctx_burst_max_frac"] for name, arm in arms.items()},
        "trials": trials,
    }


def _fmt(v):
    if isinstance(v, float):
        return "nan" if math.isnan(v) else f"{v:.6g}"
    return str(v)


def report(out, wall):
    k013.report(out["k013"], out["trials"], wall)

    k013_res = out["k013"]
    arms = k013_res["arms"]

    print()
    print("=" * 76)
    print("S1.0 gated contrast (SPEC 8.1)")
    print("=" * 76)
    print(f"  plasticity_mode={out['plasticity_mode_during_run']}  trials={out['trials']}")

    print()
    print("  warm-end synapse stats (t=120,000)")
    for k in ("sense_to_ctx", "ctx_to_ctx_EE"):
        s = out["warm_end_syn_stats"][k]
        print(f"    {k:<14} n={s['n']:<7} mean_w/w_max={s['mean_w_over_wmax']:.4f}  "
              f"frac_ceiling={s['frac_ceiling']:.4f}")
    r1 = out["r1"]
    print(f"  R1 warm-up ceilings the nerve: mean_w/w_max={r1['mean_w_over_wmax']:.4f} "
          f"(limit {R1_MEAN_MAX})  frac_ceiling={r1['frac_ceiling']:.4f} (limit {R1_CEILING_MAX})"
          f"  -> {'REJECT' if r1['reject'] else 'ok'}")
    r2 = out["r2"]
    print(f"  R2 on-window nets LTD: ltp_mean={_fmt(r2['ltp_mean'])}  ltd_mean={_fmt(r2['ltd_mean'])}"
          f"  net={_fmt(r2['net'])}  -> {'REJECT' if r2['reject'] else 'ok'}")
    print(f"     rule needs causal:anticausal >= {r2['rule_needed_at_rest']:.4f} at the rest weight; "
          f"measured trace_ratio_full={_fmt(r2['trace_ratio_full'])}")

    print()
    print("  gate per arm")
    for name, gt in out["gate"].items():
        print(f"    {name:<6} ticks={gt['ticks']} (expected {gt['expected_ticks']})  "
              f"mirror_disagreements={gt['mirror_disagreements']}  "
              f"frac_a_spikes={_fmt(gt['frac_a_spikes'])}  frac_ctxa_spikes={_fmt(gt['frac_ctxa_spikes'])}")

    ra = arms["A"].get("ratio_final")
    rb = arms["B"].get("ratio_final")
    rn = arms["none"].get("ratio_final")
    print()
    print(f"  ratio_final: A {ra}  B {rb}  none {rn}")
    gap_b = None if ra is None or rb is None else ra - rb
    gap_n = None if ra is None or rn is None else ra - rn
    print(f"  A-B gap: {gap_b}  A-none gap: {gap_n}")
    print(f"  weight_pass: {k013_res['weight_pass']}")

    print()
    print("  validity")
    for name, valid in k013_res["validity"].items():
        print(f"    {name:<28}{valid}")
    print(f"    natural_response_ok        {k013_res['natural_response_ok']}")
    print("  burst_max_frac (limit {:.2f})".format(BURST_MAX_FRAC))
    for name, frac in out["burst_max_frac"].items():
        print(f"    {name:<12}{frac:.4f}  {'ok' if frac <= BURST_MAX_FRAC else 'OVER'}")
    k02 = out["k02"]
    print(f"  k02: pass={k02['pass']}  message={k02['message']!r}  wall_s={k02['wall_s']:.1f}")

    print()
    print("  rates_ema_hz_at_warm_end")
    for region, rates in out["rates_ema_hz_at_warm_end"].items():
        print(f"    {region:<8}{rates}")

    print()
    print("  arm A groups (A / nonA)")
    for group in ("A", "nonA"):
        g = arms["A"]["groups"][group]
        print(f"    group {group}")
        print(f"      mean_w_over_wmax baseline/final  {g['mean_w_over_wmax_baseline']:.4f} / "
              f"{g['mean_w_over_wmax_final']:.4f}")
        print(f"      frac_ceiling baseline/final      {g['frac_ceiling_baseline']:.4f} / "
              f"{g['frac_ceiling_final']:.4f}")
        print(f"      ltp_mean                         {g['ltp_mean']:.6g}")
        print(f"      ltd_mean                         {g['ltd_mean']:.6g}")
        print(f"      scaling_mean                     {g['scaling_mean']:.6g}"
              "  (0 by construction in gated mode: the nerve is frozen for scaling)")
        print(f"      causal/anticausal pairs          {g['causal_pairs']} / {g['anticausal_pairs']}")
        print(f"      causal/anticausal trace_sum      {g['causal_trace_sum']:.6g} / "
              f"{g['anticausal_trace_sum']:.6g}")

    print()
    print(f"  arm A rates_hz: {arms['A'].get('rates_hz')}")

    print()
    print("  F1 (ctx_A) and S per state")
    pt = k013_res["probe_table"]
    for state in ("before", "after_A", "after_B", "after_none"):
        row = pt[state]["ctx_A"]
        print(f"    {state:<12}evoked_A={row['evoked_A']:.4f}  S={row.get('S')}")

    validity_ok = all(k013_res["validity"].values())
    burst_ok = all(frac <= BURST_MAX_FRAC for frac in out["burst_max_frac"].values())
    k02_ok = out["k02"]["pass"] is True
    gate_ok = all(gt["mirror_disagreements"] == 0 and gt["ticks"] == gt["expected_ticks"]
                  for gt in out["gate"].values())
    natural_ok = k013_res["natural_response_ok"]

    print()
    if not (validity_ok and burst_ok and k02_ok and gate_ok):
        reasons = []
        if not validity_ok:
            reasons.append("k013 validity")
        if not burst_ok:
            reasons.append("burst_max_frac")
        if not k02_ok:
            reasons.append("k02")
        if not gate_ok:
            reasons.append("gate mirror/ticks")
        print(f"S1.0 VERDICT: INVALID ({', '.join(reasons)})")
    elif out["r1"]["reject"]:
        print("S1.0 VERDICT: REJECT (R1 warm-up ceilings the nerve)")
    elif not natural_ok:
        print("S1.0 VERDICT: REJECT (no natural response at the rest weight)")
    elif out["r2"]["reject"]:
        print("S1.0 VERDICT: REJECT (R2 on-window nets LTD at the rest weight)")
    elif k013_res["weight_pass"]:
        print("S1.0 VERDICT: PASS")
    else:
        print("S1.0 VERDICT: REJECT (weight endpoint)")


def main():
    trials = int(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else TRIALS
    k02_guard = "--no-k02" not in sys.argv
    t0 = time.time()
    out = run_experiment(trials, k02_guard=k02_guard)
    wall = time.time() - t0
    report(out, wall)
    return out


if __name__ == "__main__":
    main()
