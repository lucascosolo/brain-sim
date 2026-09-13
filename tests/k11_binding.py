"""K1.1 hpc binding / pattern completion (SPEC.md section 8.2).

Question: does the binder form a sparse hpc assembly for a presented pattern and
complete it from a half cue? Engine, server and UI are untouched; every stimulus
in this module is an ordinary sense-only ``present()``/``inject()`` call, nothing
else is imposed (no forced state, no reset, no frozen turnover, no test-side RNG
draws from the engine).
"""

import contextlib
import copy
import os
import sys
import time

import numpy as np

if __package__ in (None, ""):  # run directly as `python tests/k11_binding.py`
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import k03_pairing as k03
import k013_onset as k013
from brainsim import params

SEED = 1
BASE_TICKS = 2000
A_TICKS = 2000
DELAY_TICKS = 1000
CUE_TICKS = 200
WINDOW_TICKS = 50
REPORT_WINDOWS = (50, 100, 200)
EXCESS_HZ = 4.0
ASSEMBLY_MAX = 20
RECALL_MIN = 0.80
SPURIOUS_FRAC = 0.5
VOLLEY_MIN_FRAC = 0.7
PATTERN_A = 0
PATTERN_B = 1
SLEEP_ONSET_TICK = 140_000


# --------------------------------------------------------------------------- #
# pure helpers
# --------------------------------------------------------------------------- #

@contextlib.contextmanager
def hpc_struct_prune_exc(flag):
    """Temporarily set params.REGIONS['hpc']['struct_prune_exc'], restoring the
    previous value on exit (exception or not)."""
    prev = params.REGIONS["hpc"]["struct_prune_exc"]
    params.REGIONS["hpc"]["struct_prune_exc"] = flag
    try:
        yield
    finally:
        params.REGIONS["hpc"]["struct_prune_exc"] = prev


def cue_ids(pattern_ids):
    """The 20 cells at even positions of the sorted pattern (a fixed half)."""
    return np.sort(np.asarray(pattern_ids, np.int64))[0::2]


def assembly_from_counts(base_counts, stim_counts, ids, ticks):
    """ids (subset) whose excess rate during stim over base is >= EXCESS_HZ."""
    ids = np.asarray(ids, np.int64)
    base = np.asarray(base_counts)[ids].astype(np.float64)
    stim = np.asarray(stim_counts)[ids].astype(np.float64)
    excess_hz = (stim - base) * 1000.0 / ticks
    return np.sort(ids[excess_hz >= EXCESS_HZ])


def expected_spiking(rates_hz, window_ticks):
    r = np.asarray(rates_hz, np.float64)
    return float(np.sum(1.0 - np.exp(-r * window_ticks / 1000.0)))


# --------------------------------------------------------------------------- #
# snapshot / synapse stats
# --------------------------------------------------------------------------- #

def _snapshot(net):
    return {
        "alive": net.alive.copy(), "pre": net.pre.copy(), "post": net.post.copy(),
        "born": net.born.copy(), "w": net.w.copy(),
        "w_max_post": net.w_max_n[net.post].copy(),
    }


def _syn_group_stats(snap, src_mask, dst_mask):
    m = snap["alive"] & src_mask[snap["pre"]] & dst_mask[snap["post"]]
    idx = np.flatnonzero(m)
    if idx.size == 0:
        return {"n": 0, "mean_w_over_wmax": float("nan")}
    w = snap["w"][idx].astype(np.float64)
    wmax = snap["w_max_post"][idx].astype(np.float64)
    return {"n": int(idx.size), "mean_w_over_wmax": float((w / wmax).mean())}


def _before_after(before, after, src_mask, dst_mask):
    b = _syn_group_stats(before, src_mask, dst_mask)
    a = _syn_group_stats(after, src_mask, dst_mask)
    return {"n_before": b["n"], "mean_before": b["mean_w_over_wmax"],
            "n_after": a["n"], "mean_after": a["mean_w_over_wmax"]}


def _mask(ids, n):
    m = np.zeros(n, bool)
    m[np.asarray(ids, np.int64)] = True
    return m


# --------------------------------------------------------------------------- #
# step-at-a-time helpers
# --------------------------------------------------------------------------- #

def _step_counting(eng, ticks):
    """Step ticks one at a time, draining telemetry, return per-cell counts diff."""
    before = eng.spike_counts().astype(np.int64)
    for _ in range(ticks):
        eng.step(1)
        k03._drain_telemetry(eng)
    after = eng.spike_counts().astype(np.int64)
    return after - before


def _step_chunked_counting(eng, ticks):
    before = eng.spike_counts().astype(np.int64)
    remaining = ticks
    while remaining:
        chunk = min(1000, remaining)
        eng.step(chunk)
        k03._drain_telemetry(eng)
        remaining -= chunk
    after = eng.spike_counts().astype(np.int64)
    return after - before


def _present_recording_volley(eng, pattern_id, ticks, pattern_ids):
    """present(pattern_id, ticks) stepped one tick at a time, recording which
    pattern cells spiked (volley) and returning the per-cell count diff."""
    n = eng.net.n
    pat_mask = _mask(pattern_ids, n)
    hit = np.zeros(n, bool)
    before = eng.spike_counts().astype(np.int64)
    eng.present(pattern_id, ticks)
    for _ in range(ticks):
        eng.step(1)
        s = eng._buf_spikes[-1]
        hit[s[pat_mask[s]]] = True
        k03._drain_telemetry(eng)
    after = eng.spike_counts().astype(np.int64)
    return after - before, hit


def _run_arm(eng, ticks, inject_fn, watch_ids):
    """Step ticks one at a time (inject_fn called first to start the stimulus,
    or None for the 'none' arm). Returns per-cell counts over WINDOW_TICKS and
    over `ticks`, first-spike tick (relative to onset) per watch_ids cell, and
    stim volley fraction (fraction of injected cells spiking at all)."""
    n = eng.net.n
    if inject_fn is not None:
        inj_ids = inject_fn(eng)
    else:
        inj_ids = np.empty(0, np.int64)
    inj_mask = _mask(inj_ids, n)
    inj_hit = np.zeros(n, bool)
    watch_mask = _mask(watch_ids, n)
    first_spike = np.full(n, -1, np.int64)
    before = eng.spike_counts().astype(np.int64)
    win_after = None
    for k in range(ticks):
        eng.step(1)
        s = eng._buf_spikes[-1]
        if inj_mask.any():
            inj_hit[s[inj_mask[s]]] = True
        wm = watch_mask[s]
        newly = s[wm & (first_spike[s] < 0)]
        first_spike[newly] = k
        k03._drain_telemetry(eng)
        if k == WINDOW_TICKS - 1:
            win_after = eng.spike_counts().astype(np.int64)
    after = eng.spike_counts().astype(np.int64)
    counts_window = (win_after - before) if win_after is not None else (after - before)
    stim_volley_frac = (float(inj_hit.sum()) / inj_ids.size) if inj_ids.size else float("nan")
    return {
        "counts_window": counts_window, "counts_full": after - before,
        "first_spike": first_spike, "stim_volley_frac": stim_volley_frac,
    }


# --------------------------------------------------------------------------- #
# experiment
# --------------------------------------------------------------------------- #

def run_experiment(seed=SEED, hpc_prune_exc=True):
    with hpc_struct_prune_exc(hpc_prune_exc):
        return _run_experiment(seed, hpc_prune_exc)


def _run_experiment(seed, hpc_prune_exc):
    inject_log = []
    eng, _ = k03.warm_engine(seed)
    net = eng.net
    t_warm_end = eng.t
    assert t_warm_end == 120_000
    rate_warm_end = net.rate.copy()   # EMA at t = 120,000, before any stimulus
    del_wrapper = "inject" in eng.__dict__
    if del_wrapper:
        del eng.inject
    k013._install_inject_log(eng, inject_log)

    hpc = net.region_slice["hpc"]
    n_hpc_exc = params.REGIONS["hpc"]["n_exc"]
    hpc_e_ids = np.arange(hpc.start, hpc.start + n_hpc_exc, dtype=np.int64)
    hpc_i_ids = np.arange(hpc.start + n_hpc_exc, hpc.stop, dtype=np.int64)
    ctx = net.region_slice["ctx"]
    n_ctx_exc = params.REGIONS["ctx"]["n_exc"]
    ctx_e_ids = np.arange(ctx.start, ctx.start + n_ctx_exc, dtype=np.int64)

    A_ids = np.sort(np.asarray(eng.patterns[PATTERN_A], np.int64))
    B_ids = np.sort(np.asarray(eng.patterns[PATTERN_B], np.int64))
    cue = cue_ids(A_ids)

    # --- baseline: t 120,000 -> 122,000 --------------------------------- #
    base_counts = _step_chunked_counting(eng, BASE_TICKS)
    assert eng.t == 122_000

    snap_before = _snapshot(net)

    if "inject" in eng.__dict__:
        del eng.inject
    eng_B = copy.deepcopy(eng)
    k013._install_inject_log(eng, inject_log)
    k013._install_inject_log(eng_B, inject_log)

    # --- present A: t 122,000 -> 124,000 --------------------------------- #
    a_counts, a_hit = _present_recording_volley(eng, PATTERN_A, A_TICKS, A_ids)
    assert eng.t == 124_000
    snap_after = _snapshot(net)

    assembly = assembly_from_counts(base_counts, a_counts, hpc_e_ids, A_TICKS)
    i_responders = assembly_from_counts(base_counts, a_counts, hpc_i_ids, A_TICKS)
    a_volley_frac = float(a_hit[A_ids].sum()) / A_ids.size

    other_e = np.setdiff1d(hpc_e_ids, assembly)

    def hz(counts, ids, ticks):
        if len(ids) == 0:
            return float("nan")
        return float(np.asarray(counts)[ids].sum()) * 1000.0 / (len(ids) * ticks)

    assembly_info = {
        "ids": assembly.tolist(), "size": int(assembly.size),
        "i_responders": int(i_responders.size),
        "rate_a_hz": hz(a_counts, assembly, A_TICKS),
        "rate_base_hz": hz(base_counts, assembly, BASE_TICKS),
        "other_e_rate_a_hz": hz(a_counts, other_e, A_TICKS),
        "other_e_rate_base_hz": hz(base_counts, other_e, BASE_TICKS),
        "hpc_i_rate_a_hz": hz(a_counts, hpc_i_ids, A_TICKS),
        "hpc_i_rate_base_hz": hz(base_counts, hpc_i_ids, BASE_TICKS),
        "ctx_e_rate_a_hz": hz(a_counts, ctx_e_ids, A_TICKS),
        "ctx_e_rate_base_hz": hz(base_counts, ctx_e_ids, BASE_TICKS),
        "a_volley_frac": a_volley_frac,
    }

    # --- delay: t 124,000 -> 125,000 ------------------------------------- #
    _step_chunked_counting(eng, DELAY_TICKS)
    assert eng.t == 125_000

    # --- three copies at t = 125,000 ------------------------------------- #
    if "inject" in eng.__dict__:
        del eng.inject
    eng_cue = copy.deepcopy(eng)
    eng_full = copy.deepcopy(eng)
    eng_none = copy.deepcopy(eng)
    k013._install_inject_log(eng, inject_log)
    for e in (eng_cue, eng_full, eng_none):
        k013._install_inject_log(e, inject_log)

    watch_ids = assembly if assembly.size else np.empty(0, np.int64)

    def _cue_inject(e):
        e.inject(cue, params.PATTERN_AMP_MV, CUE_TICKS)
        return cue

    def _full_inject(e):
        e.present(PATTERN_A, CUE_TICKS)
        return A_ids

    arm_raw = {
        "cue": _run_arm(eng_cue, CUE_TICKS, _cue_inject, watch_ids),
        "full": _run_arm(eng_full, CUE_TICKS, _full_inject, watch_ids),
        "none": _run_arm(eng_none, CUE_TICKS, None, watch_ids),
    }

    other_e_base_rates = (base_counts[other_e].astype(np.float64) * 1000.0 / BASE_TICKS) \
        if other_e.size else np.zeros(0)
    nonassembly_expected_50 = expected_spiking(other_e_base_rates, WINDOW_TICKS)

    stim_ids_by_arm = {"cue": cue, "full": A_ids, "none": np.empty(0, np.int64)}
    arms = {}
    for name, raw in arm_raw.items():
        cw = raw["counts_window"]
        sid = np.asarray(stim_ids_by_arm[name], np.int64)
        stim_spikes_50 = int(cw[sid].sum()) if sid.size else None
        ctx_e_rate_window_hz = hz(cw, ctx_e_ids, WINDOW_TICKS)
        assembly_spiking_50 = int((cw[assembly] > 0).sum()) if assembly.size else 0
        nonassembly_spiking_50 = int((cw[other_e] > 0).sum()) if other_e.size else 0
        spurious_excess_50 = nonassembly_spiking_50 - nonassembly_expected_50
        recall = {}
        cf = raw["counts_full"]
        for w in REPORT_WINDOWS:
            if assembly.size == 0:
                recall[w] = float("nan")
            elif w == WINDOW_TICKS:
                recall[w] = float((cw[assembly] > 0).sum()) / assembly.size
            else:
                fs = raw["first_spike"][assembly]
                recall[w] = float(np.count_nonzero((fs >= 0) & (fs < w))) / assembly.size
        hpc_e_rate_window_hz = hz(cw, hpc_e_ids, WINDOW_TICKS)
        hpc_i_rate_window_hz = hz(cw, hpc_i_ids, WINDOW_TICKS)
        if assembly.size:
            fs_assembly = raw["first_spike"][assembly]
            fs_assembly = fs_assembly[fs_assembly >= 0]
            first_assembly_spike_tick = int(fs_assembly.min()) if fs_assembly.size else None
        else:
            first_assembly_spike_tick = None
        arms[name] = {
            "recall": recall,
            "assembly_spiking_50": assembly_spiking_50,
            "nonassembly_spiking_50": nonassembly_spiking_50,
            "nonassembly_expected_50": nonassembly_expected_50,
            "spurious_excess_50": spurious_excess_50,
            "hpc_e_rate_window_hz": hpc_e_rate_window_hz,
            "hpc_i_rate_window_hz": hpc_i_rate_window_hz,
            "ctx_e_rate_window_hz": ctx_e_rate_window_hz,
            "stim_spikes_50": stim_spikes_50,
            "first_assembly_spike_tick": first_assembly_spike_tick,
            "stim_volley_frac": raw["stim_volley_frac"],
        }

    cue_volley_frac = arm_raw["cue"]["stim_volley_frac"]

    # --- B arm: present(1, 2000) from the t=122,000 copy ------------------ #
    if "inject" in eng_B.__dict__:
        del eng_B.inject
    k013._install_inject_log(eng_B, inject_log)
    b_counts, _ = _present_recording_volley(eng_B, PATTERN_B, A_TICKS, B_ids)
    assembly_B = assembly_from_counts(base_counts, b_counts, hpc_e_ids, A_TICKS)
    overlap_with_A = int(np.intersect1d(assembly, assembly_B).size)
    overlap_frac_of_A = (float(overlap_with_A) / assembly.size) if assembly.size else float("nan")
    assembly_B_info = {"ids": assembly_B.tolist(), "size": int(assembly_B.size),
                        "overlap_with_A": overlap_with_A,
                        "overlap_frac_of_A": overlap_frac_of_A}

    t_end = max(eng.t, eng_cue.t, eng_full.t, eng_none.t, eng_B.t)
    phase_end = eng.phase

    # --- synapse stats ----------------------------------------------------- #
    sense = net.region_slice["sense"]
    sense_mask = np.zeros(net.n, bool)
    sense_mask[sense.start:sense.stop] = True
    hpc_mask = np.zeros(net.n, bool)
    hpc_mask[hpc.start:hpc.stop] = True
    ctx_mask = _mask(ctx_e_ids, net.n)   # excitatory ctx sources only (ctx I also projects to hpc)
    assembly_mask = _mask(assembly, net.n)
    other_e_mask = _mask(other_e, net.n)

    synapses = {
        "sense_to_hpc": _syn_group_stats(snap_after, sense_mask, hpc_mask),
        "ctx_to_hpc_onto_assembly": _before_after(snap_before, snap_after, ctx_mask, assembly_mask),
        "ctx_to_hpc_onto_other_e": _before_after(snap_before, snap_after, ctx_mask, other_e_mask),
        "hpc_hpc_within_assembly": _before_after(snap_before, snap_after, assembly_mask, assembly_mask),
        "hpc_hpc_assembly_to_other_e": _before_after(snap_before, snap_after, assembly_mask, other_e_mask),
        "hpc_hpc_other_e_to_assembly": _before_after(snap_before, snap_after, other_e_mask, assembly_mask),
        "indegree_assembly_e_mean": float(net.in_degree(assembly).mean()) if assembly.size else float("nan"),
        "indegree_other_e_mean": float(net.in_degree(other_e).mean()) if other_e.size else float("nan"),
    }

    rates_ema = {}
    for region in ("sense", "ctx", "hpc"):
        sl = net.region_slice[region]
        n_exc = params.REGIONS[region]["n_exc"]
        e_ids = np.arange(sl.start, sl.start + n_exc, dtype=np.int64)
        i_ids = np.arange(sl.start + n_exc, sl.stop, dtype=np.int64)
        rates_ema[region] = {
            "E": float(rate_warm_end[e_ids].mean()) if e_ids.size else float("nan"),
            "I": float(rate_warm_end[i_ids].mean()) if i_ids.size else None,
        }

    any_sense_to_hpc_proj = any(p[0] == "sense" and p[1] == "hpc" for p in params.PROJECTIONS)
    engine_pins = {
        "has_plasticity_mode": hasattr(params, "PLASTICITY_MODE"),
        "has_stdp_rule": hasattr(params, "STDP_RULE"),
        "a_plus_hpc": params.REGIONS["hpc"]["a_plus"],
        "a_minus_hpc": params.REGIONS["hpc"]["a_minus"],
        "w_max_hpc": params.REGIONS["hpc"]["w_max"],
        "r_target_hpc_e": params.REGIONS["hpc"]["r_target_exc"],
        "r_target_hpc_i": params.REGIONS["hpc"]["r_target_inh"],
        "pattern_amp_mv": params.PATTERN_AMP_MV,
        "pattern_size": int(A_ids.size),
        "sense_to_hpc_projection": bool(any_sense_to_hpc_proj),
        # read from the mask the engine built at construction, not from the global the
        # context manager set (eng.p.REGIONS is params.REGIONS by reference)
        "struct_prune_exc": {name: bool(eng._prune_exc_ok[net.region_slice[name]].all())
                             for name in ("sense", "ctx", "hpc")},
    }

    wake_throughout = (
        eng.phase == "wake" and eng_cue.phase == "wake" and eng_full.phase == "wake"
        and eng_none.phase == "wake" and eng_B.phase == "wake"
        and t_warm_end <= SLEEP_ONSET_TICK and 122_000 <= SLEEP_ONSET_TICK
        and 124_000 <= SLEEP_ONSET_TICK and 125_000 <= SLEEP_ONSET_TICK
        and t_end <= SLEEP_ONSET_TICK
    )
    engine_pins_ok = (
        not engine_pins["has_plasticity_mode"] and not engine_pins["has_stdp_rule"]
        and engine_pins["a_plus_hpc"] == 0.05 and engine_pins["a_minus_hpc"] == 0.06
        and engine_pins["w_max_hpc"] == 3.0 and engine_pins["r_target_hpc_e"] == 1.0
        and engine_pins["r_target_hpc_i"] == 6.0 and engine_pins["pattern_amp_mv"] == 1.3
        and engine_pins["pattern_size"] == 40
    )
    validity = {
        "wake_throughout": bool(wake_throughout),
        "a_volley": bool(a_volley_frac >= VOLLEY_MIN_FRAC),
        "cue_volley": bool(cue_volley_frac >= VOLLEY_MIN_FRAC),
        "inject_sense_only": bool(inject_log) and all(e[4] for e in inject_log),
        "engine_pins_ok": bool(engine_pins_ok),
    }
    validity["valid_all"] = all(validity.values())

    size = assembly_info["size"]
    c1 = 1 <= size <= 20
    c2 = arms["cue"]["recall"][50] >= RECALL_MIN
    c3 = arms["cue"]["spurious_excess_50"] < SPURIOUS_FRAC * size
    criteria = {"c1_forms_sparse": c1, "c2_recall_50": c2, "c3_no_other_assembly": c3,
                "pass": bool(c1 and c2 and c3)}

    return {
        "seed": seed, "hpc_prune_exc": bool(hpc_prune_exc),
        "t_warm_end": int(t_warm_end), "t_end": int(t_end), "phase_end": phase_end,
        "engine_pins": engine_pins,
        "rates_ema_hz_at_warm_end": rates_ema,
        "A_ids": A_ids.tolist(), "cue_ids": cue.tolist(), "B_ids": B_ids.tolist(),
        "assembly": assembly_info, "assembly_B": assembly_B_info,
        "arms": arms,
        "synapses": synapses,
        "validity": validity,
        "criteria": criteria,
        "inject_log": inject_log,
    }


# --------------------------------------------------------------------------- #
# report
# --------------------------------------------------------------------------- #

def report(out, wall):
    print("=" * 76)
    print("K1.1 hpc binding / pattern completion report")
    print("=" * 76)
    print(f"run_experiment wall time: {wall:.1f} s")
    print(f"seed {out['seed']}  t_warm_end {out['t_warm_end']}  t_end {out['t_end']}  "
          f"phase_end {out['phase_end']}  hpc struct_prune_exc={out['hpc_prune_exc']}")

    print()
    print("  rates at warm end (EMA Hz) vs targets (hpc E 1, I 6)")
    for region, d in out["rates_ema_hz_at_warm_end"].items():
        print(f"    {region:<8} E={d['E']:.4f}  I={d.get('I')}")

    a = out["assembly"]
    print()
    print(f"  assembly: size={a['size']} i_responders={a['i_responders']} "
          f"a_volley_frac={a['a_volley_frac']:.4f}")
    print(f"    rate_base={a['rate_base_hz']:.4f} rate_a={a['rate_a_hz']:.4f} (assembly)")
    print(f"    other_e   rate_base={a['other_e_rate_base_hz']:.4f} rate_a={a['other_e_rate_a_hz']:.4f}")
    print(f"    hpc_i     rate_base={a['hpc_i_rate_base_hz']:.4f} rate_a={a['hpc_i_rate_a_hz']:.4f}")
    print(f"    ctx_e     rate_base={a['ctx_e_rate_base_hz']:.4f} rate_a={a['ctx_e_rate_a_hz']:.4f}")

    print()
    print("  arms")
    print(f"    {'arm':<8}{'recall50':>10}{'recall100':>11}{'recall200':>11}"
          f"{'asm_sp50':>10}{'nonasm_sp50':>12}{'expect50':>10}{'spur50':>10}"
          f"{'first_tick':>11}{'volley':>9}")
    for name, arm in out["arms"].items():
        r = arm["recall"]
        print(f"    {name:<8}{r.get(50, float('nan')):>10.4f}{r.get(100, float('nan')):>11.4f}"
              f"{r.get(200, float('nan')):>11.4f}{arm['assembly_spiking_50']:>10}"
              f"{arm['nonassembly_spiking_50']:>12}{arm['nonassembly_expected_50']:>10.4f}"
              f"{arm['spurious_excess_50']:>10.4f}{str(arm['first_assembly_spike_tick']):>11}"
              f"{arm['stim_volley_frac']:>9.4f}")
    print(f"    {'arm':<8}{'hpcE_50Hz':>10}{'hpcI_50Hz':>11}{'ctxE_50Hz':>11}{'stim_sp50':>10}")
    for name, arm in out["arms"].items():
        print(f"    {name:<8}{arm.get('hpc_e_rate_window_hz', float('nan')):>10.3f}"
              f"{arm.get('hpc_i_rate_window_hz', float('nan')):>11.3f}"
              f"{arm.get('ctx_e_rate_window_hz', float('nan')):>11.3f}"
              f"{str(arm.get('stim_spikes_50')):>10}")

    b = out["assembly_B"]
    print()
    print(f"  B: size={b['size']} overlap_with_A={b['overlap_with_A']} "
          f"overlap_frac_of_A={b['overlap_frac_of_A']}")

    print()
    print("  synapses")
    syn = out["synapses"]
    for k in ("sense_to_hpc",):
        s = syn[k]
        print(f"    {k:<30} n={s['n']:<6} mean_w/w_max={s['mean_w_over_wmax']}")
    for k in ("ctx_to_hpc_onto_assembly", "ctx_to_hpc_onto_other_e",
              "hpc_hpc_within_assembly", "hpc_hpc_assembly_to_other_e",
              "hpc_hpc_other_e_to_assembly"):
        s = syn[k]
        print(f"    {k:<30} n_before={s['n_before']:<6} mean_before={s['mean_before']} "
              f"n_after={s['n_after']:<6} mean_after={s['mean_after']}")
    print(f"    indegree_assembly_e_mean={syn['indegree_assembly_e_mean']}  "
          f"indegree_other_e_mean={syn['indegree_other_e_mean']}")

    print()
    print("  validity")
    v = out["validity"]
    for k in ("wake_throughout", "a_volley", "cue_volley", "inject_sense_only", "engine_pins_ok"):
        print(f"    {k:<20}{v[k]}   {'PASS' if v[k] else 'FAIL'}")
    print(f"    {'valid_all':<20}{v['valid_all']}   {'PASS' if v['valid_all'] else 'FAIL'}")

    print()
    print("  criteria")
    c = out["criteria"]
    print(f"    c1_forms_sparse       {c['c1_forms_sparse']}")
    print(f"    c2_recall_50          {c['c2_recall_50']}")
    print(f"    c3_no_other_assembly  {c['c3_no_other_assembly']}")
    print(f"    pass                  {c['pass']}")

    reasons = []
    if not v["valid_all"]:
        for name in ("wake_throughout", "a_volley", "cue_volley", "inject_sense_only",
                     "engine_pins_ok"):
            if not v[name]:
                reasons.append(name)
        print()
        print(f"K1.1 VERDICT: INVALID ({', '.join(reasons)})")
        return

    if not c["pass"]:
        size = a["size"]
        if not c["c1_forms_sparse"]:
            reasons.append("c1 no assembly" if size == 0
                            else f"c1 assembly too large (size {size} > 20)")
        if not c["c2_recall_50"]:
            reasons.append(
                f"c2 recall at 50 ticks {out['arms']['cue']['recall'][50]:.4f} < {RECALL_MIN} "
                f"(full-arm reference {out['arms']['full']['recall'][50]:.4f})")
        if not c["c3_no_other_assembly"]:
            reasons.append(
                f"c3 spurious excess {out['arms']['cue']['spurious_excess_50']} >= 0.5*size")
        print()
        print(f"K1.1 VERDICT: FAIL ({', '.join(reasons)})")
        return

    print()
    print("K1.1 VERDICT: PASS")


def main():
    args = sys.argv[1:]
    hpc_prune_exc = "--hpc-prune-off" not in args
    positional = [a for a in args if a != "--hpc-prune-off"]
    seed = int(positional[0]) if positional else SEED
    t0 = time.time()
    out = run_experiment(seed, hpc_prune_exc=hpc_prune_exc)
    wall = time.time() - t0
    report(out, wall)
    return out


if __name__ == "__main__":
    main()
