"""SPEC 8.23 ceiling diagnostic: can any weights on this wiring let a half cue recall the assembly?
Run: PYTHONPATH=<worktree> python tests/k823_ceiling.py [--seed N] [--json out.json] [--smoke]
Diagnostic only; the weights set in Part 2 are an oracle, not a rule. Exit 0 unless an assertion fails.
"""
import copy
import json
import os
import sys

import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import k03_pairing as k03
import k11_binding as k11
import k821_helpers as h
import k821_triplet as t6
from k816_hetero_write import A_TICKS, BASE_TICKS, K_W, PATTERN_A, PATTERN_B, step1000
from brainsim import encode

RECORDED = os.path.expanduser("~/.cache/scratch/brainsim-tri/t6_seed%d.json")
STIMS = ("none", "A", "half", "B")
TICKS = (50, 200)
ARMS = ("N", "Ah", "Aa", "Aall", "R", "AhR", "AaR")
FULL_STATES = (3000, 4000, 5000, 6000, 7000)     # offsets from T0 = 122,000: t = 125,000 .. 129,000
SMOKE_STATES = (3000, 4000)
DONE_MIN, QUIET_MAX, SELECT_MUL = 13, 3, 0.5


def frozen_copy(eng):
    """Deep copy with no weight or liveness able to change. The pair lineage has triplet off, so k822.frozen_copy
    (which asserts triplet on) cannot be used; here pair-rule changes need a_plus_n / a_minus_n > 0, both zeroed;
    hetero write off; the slow sweep is the only other writer and the probe is asserted not to cross one."""
    e = copy.deepcopy(eng)
    assert not e.triplet_stdp
    e.hetero_write = False
    e.net.a_plus_n[:] = 0.0
    e.net.a_minus_n[:] = 0.0
    return e


def probe(eng, stim, ticks, A_ids):
    """One frozen probe on its own copy, stimulus held for the whole probe; per-cell spike counts."""
    e = frozen_copy(eng)
    sw = e.p.SWEEP_TICKS
    assert (int(e.t) + ticks) // sw == int(e.t) // sw, ("probe crosses a slow sweep", int(e.t), ticks)
    w0, al0 = e.net.w.copy(), e.net.alive.copy()
    if stim == "half":
        e.inject(encode.cue_ids(A_ids), e.p.PATTERN_AMP_MV, ticks)
    elif stim in ("A", "B"):
        e.present(PATTERN_A if stim == "A" else PATTERN_B, ticks)
    c = k11._step_chunked_counting(e, ticks)
    assert np.array_equal(e.net.w, w0) and np.array_equal(e.net.alive, al0), ("weights changed in frozen probe", stim, ticks)
    return c.astype(np.int64)


def outputs(c, W, hpc, ctx, ticks):
    out_w = np.setdiff1d(hpc, W)
    return {"W_cells": int((c[W] > 0).sum()), "W_spikes": int(c[W].sum()),
            "hpc_out_cells": int((c[out_w] > 0).sum()),
            "hpc_hz": float(c[hpc].sum()) * 1000.0 / (len(hpc) * ticks),
            "ctx_hz": float(c[ctx].sum()) * 1000.0 / (len(ctx) * ticks)}


def pearson(a, b):
    a, b = a.astype(float), b.astype(float)
    if a.std() == 0 or b.std() == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def part1(eng, W, hpc, ctx, A_ids):
    net = eng.net
    cnt = {s: probe(eng, s, 50, A_ids) for s in STIMS}
    res = {}
    for name, ids in (("ctx", ctx), ("hpc", hpc)):
        r = {f"frac_{s}": float((cnt[s][ids] > 0).mean()) for s in STIMS}
        sa, sb = cnt["A"][ids] > 0, cnt["B"][ids] > 0
        r["frac_A_also_B"] = float((sa & sb).sum() / sa.sum()) if sa.any() else float("nan")
        top = lambda c: set(ids[np.argsort(-c[ids], kind="stable")[:100]].tolist())
        r["top100_overlap_A_B"] = len(top(cnt["A"]) & top(cnt["B"]))
        r["pearson_A_B"] = pearson(cnt["A"][ids], cnt["B"][ids])
        res[name] = r
    half_set = ctx[cnt["half"][ctx] > 0]
    A_set = ctx[cnt["A"][ctx] > 0]
    indeg = {}
    for name, pre_ids in (("from_W", W), ("from_half_active_ctx", half_set), ("from_A_active_ctx", A_set)):
        idx = h.exc_onto(net, W)
        idx = idx[np.isin(net.pre[idx], pre_ids)]
        indeg[name + "_per_W_cell"] = len(idx) / len(W)
        indeg[name + "_mean_w_frac"] = (float((net.w[idx] / net.w_max_n[net.post[idx]]).mean()) if idx.size else float("nan"))
    res["indegree"] = indeg
    return res, half_set, A_set


def arm_synapses(net, arm, W, ctx, half_set, A_set):
    if arm == "N":
        return np.empty(0, np.int64)
    idx = h.exc_onto(net, W)
    pre = net.pre[idx]
    pick = {"Ah": [half_set], "Aa": [A_set], "Aall": [ctx], "R": [W], "AhR": [half_set, W], "AaR": [A_set, W]}[arm]
    return idx[np.isin(pre, np.concatenate(pick))]


def part2(eng, W, hpc, ctx, A_ids, half_set, A_set, arms=ARMS):
    res = {}
    for arm in arms:
        e = copy.deepcopy(eng)
        net = e.net
        idx = arm_synapses(net, arm, W, ctx, half_set, A_set)
        wm = net.w_max_n[net.post[idx]]
        before = float((net.w[idx] / wm).mean()) if idx.size else float("nan")
        net.w[idx] = wm
        r = {"n_set": int(idx.size), "mean_w_frac_before": before}
        for ticks in TICKS:
            for s in STIMS:
                r[f"{s}_{ticks}"] = outputs(probe(e, s, ticks, A_ids), W, hpc, ctx, ticks)
        res[arm] = r
        del e
    return res


def mean_dicts(rows):
    if isinstance(rows[0], dict):
        return {k: mean_dicts([r[k] for r in rows]) for k in rows[0]}
    v = np.asarray(rows, float)
    return float(np.nanmean(v)) if not np.isnan(v).all() else float("nan")


def reading(m, ticks):
    half, none, b = m[f"half_{ticks}"]["W_cells"], m[f"none_{ticks}"]["W_cells"], m[f"B_{ticks}"]["W_cells"]
    r = {"completes": half >= DONE_MIN, "quiet": none <= QUIET_MAX, "selective": b <= SELECT_MUL * half}
    r["all_three"] = all(r.values())
    return r


def run(seed, smoke, arms=ARMS, warm=None, compare_recorded=True):
    """The 8.23 body. `warm(seed)` returns the warmed engine (default k03.warm_engine); returns the record."""
    states = SMOKE_STATES if smoke else FULL_STATES
    if smoke:
        k03.WARMUP_TICKS = 4000
    eng = warm(seed) if warm else k03.warm_engine(seed)[0]
    net = eng.net
    hpc, ctx = encode.hpc_e_ids(net), encode.ctx_e_ids(net)
    h.own_params(eng, t6.OVERRIDES)
    eng.hetero_write = False
    assert not eng.triplet_stdp
    k11._step_chunked_counting(eng, BASE_TICKS)
    assert eng.g_struct == 0.0
    T0 = int(eng.t)
    print(f"seed {seed} T0={T0}" + ("  [SMOKE: short warm-up, two states only]" if smoke else ""))
    A_ids = np.asarray(eng.patterns[PATTERN_A], np.int64)

    tot = np.zeros(net.n, np.int64)
    log = {"sweeps": [], "B": []}
    eng.present(PATTERN_A, A_TICKS)
    off = 0
    while off < A_TICKS:
        tot += step1000(eng, log, False)
        h.check_phase(eng)
        off += 1000
    W = encode.select_winners(tot, hpc, K_W)
    own = json.load(open(RECORDED % seed))["own_W"] if not smoke and compare_recorded else None
    match = None if own is None else (sorted(int(x) for x in W) == sorted(own))
    if compare_recorded:
        print("W vs recorded T6 own_W:", "N/A (smoke)" if smoke else ("MATCH" if match else "DIFFERENT"))

    rows = []
    for s_off in states:
        while off < s_off:
            step1000(eng, log, False)
            h.check_phase(eng)
            off += 1000
        assert not eng.hetero_write
        w0, al0 = eng.net.w.copy(), eng.net.alive.copy()
        p1, half_set, A_set = part1(eng, W, hpc, ctx, A_ids)
        p2 = part2(eng, W, hpc, ctx, A_ids, half_set, A_set, arms)
        assert np.array_equal(eng.net.w, w0) and np.array_equal(eng.net.alive, al0), "main engine touched by probing"
        rows.append({"t": int(eng.t), "n_half_active_ctx": int(half_set.size), "n_A_active_ctx": int(A_set.size),
                     "part1": p1, "part2": p2})
        print(f"state t={eng.t} done (half-active ctx {half_set.size}, A-active ctx {A_set.size})", flush=True)

    mean1 = mean_dicts([r["part1"] for r in rows])
    mean2 = mean_dicts([r["part2"] for r in rows])
    read = {a: {str(t): reading(mean2[a], t) for t in TICKS} for a in arms}

    print("\nPart 1, five-state means" if not smoke else "\nPart 1, means over the two smoke states")
    for g in ("ctx", "hpc"):
        print(g, {k: round(v, 3) for k, v in mean1[g].items()})
    print("indegree", {k: round(v, 3) for k, v in mean1["indegree"].items()})

    print("\nPart 2: W cells (of 16), means over states.  columns: stimulus at 50 ticks | at 200 ticks")
    print("%6s %6s %7s | %s | %s" % ("arm", "n_set", "w/wmax", " ".join("%6s" % s for s in STIMS), " ".join("%6s" % s for s in STIMS)))
    for a in arms:
        m = mean2[a]
        print("%6s %6.0f %7.3f | %s | %s" % (a, m["n_set"], m["mean_w_frac_before"],
              " ".join("%6.2f" % m[f"{s}_50"]["W_cells"] for s in STIMS),
              " ".join("%6.2f" % m[f"{s}_200"]["W_cells"] for s in STIMS)))
    print("\nreading (50 ticks, the rule) and 200 ticks (report-only):")
    for a in arms:
        r50, r200 = read[a]["50"], read[a]["200"]
        print(f"{a:>5}: completes={r50['completes']} quiet={r50['quiet']} selective={r50['selective']} "
              f"ALL-THREE={'yes' if r50['all_three'] else 'no'} | report-only 200: completes={r200['completes']} "
              f"quiet={r200['quiet']} selective={r200['selective']} all-three={'yes' if r200['all_three'] else 'no'}")
    rec = {"seed": seed, "smoke": smoke, "T0": T0, "W": W.tolist(), "own_W_match": match, "states": rows,
           "mean_part1": mean1, "mean_part2": mean2, "reading": read}
    return rec


def main():
    smoke = "--smoke" in sys.argv
    seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 1
    rec = run(seed, smoke)
    if "--json" in sys.argv:
        with open(sys.argv[sys.argv.index("--json") + 1], "w") as f:
            json.dump(rec, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print("EXIT SMOKE" if smoke else "EXIT OK")


if __name__ == "__main__":
    main()
