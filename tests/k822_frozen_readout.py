"""SPEC 8.22 Part A: the T6 early readouts re-read with learning frozen (arms on and never only).
Run: PYTHONPATH=<worktree> python tests/k822_frozen_readout.py [--seed N] [--json out.json] [--smoke]
Exit 0 if the unfrozen rows reproduce the recorded T6 early rows, 2 if not.
"""
import copy
import json
import math
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
from k816_hetero_write import A_TICKS, B_TICKS, BASE_TICKS, K_W, PATTERN_A, PATTERN_B, step1000
from brainsim import encode

ARMS = ("on", "never")
TICKS = (50, 200)
RECORDED = os.path.expanduser("~/.cache/scratch/brainsim-tri/t6_seed%d.json")


def frozen_copy(eng):
    """Deep copy in which no synaptic weight or liveness can change (engine.py _tick lines 354-373, 410-415, 462, 499).
    Pair-rule weight changes need a_plus_n / a_minus_n > 0; the triplet branch is taken only where a_plus_n > 0 and
    is also zeroed through _tri_k; hetero write is off; the slow sweep is the only other writer and is asserted away."""
    e = copy.deepcopy(eng)
    e.hetero_write = False
    assert e.triplet_stdp and e._tri_k is not None
    e._tri_k = np.zeros_like(e._tri_k)
    e.net.a_plus_n[:] = 0.0
    e.net.a_minus_n[:] = 0.0
    return e


def frozen_probe(eng, kind, ticks, W, A_ids):
    """One frozen probe on its own copy; asserts weights and alive are bit-identical and no sweep is crossed."""
    e = frozen_copy(eng)
    sw = e.p.SWEEP_TICKS
    assert (int(e.t) + ticks) // sw == int(e.t) // sw, ("probe crosses a slow sweep", int(e.t), ticks)
    w0, al0 = e.net.w.copy(), e.net.alive.copy()
    deliv = None
    if kind == "half":
        e.inject(encode.cue_ids(A_ids), e.p.PATTERN_AMP_MV, ticks)
    else:
        e.present(PATTERN_A if kind == "A" else PATTERN_B, ticks)
    if kind == "A":
        before = e.spike_counts().astype(np.int64)
        deliv = h.delivered_exc(e, W, ticks)
        c = e.spike_counts().astype(np.int64) - before
    else:
        c = k11._step_chunked_counting(e, ticks)
    assert np.array_equal(e.net.w, w0) and np.array_equal(e.net.alive, al0), ("weights changed in frozen probe", kind, ticks)
    return c, deliv


def frozen_row(eng, W, P, A_ids, ticks):
    cA, dv = frozen_probe(eng, "A", ticks, W, A_ids)
    ch, _ = frozen_probe(eng, "half", ticks, W, A_ids)
    cb, _ = frozen_probe(eng, "B", ticks, W, A_ids)
    a, hf, b = h.on_W(cA, W), h.on_W(ch, W), h.on_W(cb, W)
    return {"deliv_A": dv, "W_spikes_A": a["spikes"], "W_cells_A": a["cells"], "P_spikes_A": int(cA[P].sum()),
            "W_spikes_half": hf["spikes"], "W_cells_half": hf["cells"], "W_spikes_B": b["spikes"], "W_cells_B": b["cells"]}


def mean_over(rows):
    return {k: float(np.mean([r[k] for r in rows])) for k in rows[0]}


def ratio(a, b):
    return a / b if b else float("inf") if a else float("nan")


def compare(mine, rec):
    """First mismatch between two row lists, or None. Ints exact, floats to 1e-9 relative."""
    for i, (m, r) in enumerate(zip(mine, rec)):
        for k, v in r.items():
            x = m.get(k)
            ok = x == v if isinstance(v, int) and not isinstance(v, bool) else math.isclose(x, v, rel_tol=1e-9, abs_tol=0.0)
            if not ok:
                return f"time index {i} key {k}: mine {x!r} recorded {v!r}"
    return None if len(mine) == len(rec) else f"row count {len(mine)} vs {len(rec)}"


def main():
    smoke = "--smoke" in sys.argv
    seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 1
    tl = t6.SMOKE if smoke else t6.FULL
    if smoke:
        k03.WARMUP_TICKS = 4000
    eng, _ = k03.warm_engine(seed)
    net = eng.net
    hpc, ctx = encode.hpc_e_ids(net), encode.ctx_e_ids(net)
    groups = {"hpc": hpc, "ctx": ctx}
    h.install_tracking(groups, net.n)

    tri = copy.deepcopy(eng)
    h.own_params(tri, t6.OVERRIDES)
    tri.triplet_stdp = True
    h.register(tri)
    h.TRACK["ctx"] = h.TRACK["hpc"] = 0.0
    k11._step_chunked_counting(tri, BASE_TICKS)
    assert tri.g_struct == 0.0 and tri.triplet_view()["on"]
    T0 = int(tri.t)
    print(f"seed {seed} T0={T0}" + ("  [SMOKE]" if smoke else ""))

    p0 = copy.deepcopy(tri)
    p0.hetero_write = False
    p0.present(PATTERN_A, t6.READOUT_TICKS)
    c = k11._step_chunked_counting(p0, t6.READOUT_TICKS)
    P = ctx[np.argsort(-c[ctx], kind="stable")[:t6.N_P]]
    del p0
    A_ids = np.asarray(tri.patterns[PATTERN_A], np.int64)

    engs = {"on": tri, "never": copy.deepcopy(tri)}
    for arm in ARMS:
        engs[arm].hetero_write = True
        h.register(engs[arm])
    del eng

    end = tl["early"][-1]
    rows = {a: {"t6": [], "frozen50": [], "frozen200": []} for a in ARMS}
    W = None
    for arm in ARMS:
        e = engs[arm]
        log = {"sweeps": [], "B": []}
        tot = np.zeros(e.net.n, np.int64)
        if arm == "on":
            e.present(PATTERN_A, A_TICKS)
        off = 0
        while off < end:
            if off == tl["B_at"]:
                e.present(PATTERN_B, B_TICKS)
            c = step1000(e, log, False)
            h.check_phase(e)
            off += 1000
            if arm == "on" and off <= A_TICKS:
                tot += c
            if arm == "on" and off == A_TICKS:
                W = encode.select_winners(tot, hpc, K_W)
            if off in tl["early"]:
                row, cA = t6.readout_row(e, W, A_ids)
                row["P_spikes_A"] = int(cA[P].sum())
                rows[arm]["t6"].append(row)
                for n in TICKS:
                    rows[arm][f"frozen{n}"].append(frozen_row(e, W, P, A_ids, n))
        h.unregister(e)
        print(f"arm {arm} done, t={e.t}")

    means = {a: {k: mean_over(v) for k, v in rows[a].items()} for a in ARMS}

    if smoke:
        valid, first = True, "skipped in smoke (no recorded smoke rows for this table)"
        print("validity: SKIPPED (smoke)")
    else:
        rec = json.load(open(RECORDED % seed))["rows"]["early"]
        first = next((m for m in (f"{a}: {compare(rows[a]['t6'], rec[a])}" for a in ARMS if compare(rows[a]["t6"], rec[a])) if m), None)
        valid = first is None
        print("validity:", "VALID" if valid else f"INVALID, first mismatch {first}")

    keys = list(rows["on"]["t6"][0])
    for arm in ARMS:
        for kind in ("t6", "frozen50", "frozen200"):
            print(f"\n[{arm} {kind}] " + " ".join(f"{k:>14}" for k in keys))
            for i, r in enumerate(rows[arm][kind]):
                print(f"  t{i} {'':>{len(arm) + len(kind)}} " + " ".join(f"{r.get(k, float('nan')):14.3f}" for k in keys))
            print("  mean " + " ".join(f"{means[arm][kind].get(k, float('nan')):14.3f}" for k in keys))

    def rt(kind, key):
        return ratio(means["on"][kind][key], means["never"][kind][key])

    reading = {f"{k}_{n}_on_over_never": rt(f"frozen{n}", k) for n in TICKS for k in ("W_spikes_A", "deliv_A")}
    for n in TICKS:
        reading[f"W_cells_half_{n}_on_vs_never"] = [means["on"][f"frozen{n}"]["W_cells_half"], means["never"][f"frozen{n}"]["W_cells_half"]]
    reading["frozen50_W_spikes_A_ratio"] = rt("frozen50", "W_spikes_A")
    reading["verdict"] = "STANDS" if reading["frozen50_W_spikes_A_ratio"] >= 1.20 else "CORRECTED"
    print("\n=== reading, seed", seed, "===")
    for n in TICKS:
        print(f"frozen-{n} W spikes under A, on/never: {reading[f'W_spikes_A_{n}_on_over_never']:.3f}")
        print(f"frozen-{n} delivered weight, on/never: {reading[f'deliv_A_{n}_on_over_never']:.3f}")
        print(f"frozen-{n} half-cue W cells, on vs never: {reading[f'W_cells_half_{n}_on_vs_never']}")
    print(f"frozen-50 ratio {reading['frozen50_W_spikes_A_ratio']:.3f} (bar 1.20): {reading['verdict']}")

    rec_out = {"seed": seed, "smoke": smoke, "W": W.tolist(), "P": P.tolist(), "rows": rows, "means": means,
               "validity": {"valid": valid, "first_mismatch": first}, "reading": reading}
    if "--json" in sys.argv:
        with open(sys.argv[sys.argv.index("--json") + 1], "w") as f:
            json.dump(rec_out, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    sys.exit(0 if valid else 2)


if __name__ == "__main__":
    main()
