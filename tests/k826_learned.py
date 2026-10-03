"""SPEC 8.26 Part 2: learned half-cue recall on the gen2 plant, trained arm beside a never-trained twin.
Run: BRAINSIM_PLANT=gen2 PYTHONPATH=<worktree> python tests/k826_learned.py --seed N --path {P,PH,TH} [--json out.json] [--smoke]
Diagnostic only; K1.1 is unchanged and is not decided here. No hand-set weights. Exit 0, 2 if path P is INVALID against 8.25.
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
import k823_ceiling as c823
from k816_hetero_write import A_TICKS, B_TICKS, BASE_TICKS, K_W, PATTERN_A, PATTERN_B, step1000
from brainsim import encode, params

RECORDED = os.path.expanduser("~/.cache/scratch/brainsim-gen2/gen2_seed%d.json")
STIMS, TICKS, ARMS, WINDOWS = c823.STIMS, c823.TICKS, ("trained", "never"), ("early", "late")
FULL = {"early": (3000, 4000, 5000, 6000, 7000), "late": (58000, 59000, 60000, 61000, 62000), "B_at": 40000}
SMOKE = {"early": (3000, 4000), "late": (7000, 8000), "B_at": 5000}
SAT_FRAC = 0.999


def frozen_copy(eng):
    """Deep copy in which no weight or liveness can change, for the pair rule and the triplet rule alike."""
    e = copy.deepcopy(eng)
    e.hetero_write = False
    e.net.a_plus_n[:] = 0.0
    e.net.a_minus_n[:] = 0.0
    if e.triplet_stdp:
        if e._tri_k is None:
            e._tri_k = e._triplet_k_vec()
        e._tri_k = np.zeros_like(e._tri_k)
    return e


def probe(eng, stim, ticks, A_ids):
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


def readout(eng, W, hpc, ctx, A_ids):
    w0, al0 = eng.net.w.copy(), eng.net.alive.copy()
    out = {f"{s}_{n}": c823.outputs(probe(eng, s, n, A_ids), W, hpc, ctx, n) for n in TICKS for s in STIMS}
    assert np.array_equal(eng.net.w, w0) and np.array_equal(eng.net.alive, al0), "main engine touched by a readout"
    return out


def saturated(net, groups):
    r = {}
    for k in ("ctx", "hpc"):
        idx = h.exc_onto(net, groups[k])
        r[k + "_E"] = float(np.mean(net.w[idx] >= SAT_FRAC * net.w_max_n[net.post[idx]])) if idx.size else 0.0
    return r


def readings(m):
    r = {}
    for n in TICKS:
        t_, v_ = m["trained"][f"half_{n}"]["W_cells"], m["never"][f"half_{n}"]["W_cells"]
        r[f"half_{n}"] = {"trained": t_, "never": v_, "difference": t_ - v_}
    for a in ARMS:
        x = m[a]
        r[a] = {"K1.1 clause (half cue, 50 ticks, mean >= 13)": bool(x["half_50"]["W_cells"] >= c823.DONE_MIN),
                "K1.1-200 (diagnostic, NOT K1.1)": bool(x["half_200"]["W_cells"] >= c823.DONE_MIN),
                "idle <= 3 at 50": bool(x["none_50"]["W_cells"] <= c823.QUIET_MAX),
                "B <= 0.5 * half at 50": bool(x["B_50"]["W_cells"] <= c823.SELECT_MUL * x["half_50"]["W_cells"]),
                "B <= 0.5 * half at 200": bool(x["B_200"]["W_cells"] <= c823.SELECT_MUL * x["half_200"]["W_cells"]),
                "none ctx_hz (50, 200)": [x[f"none_{n}"]["ctx_hz"] for n in TICKS],
                "none hpc_hz (50, 200)": [x[f"none_{n}"]["hpc_hz"] for n in TICKS]}
    return r


def validate(rows, W, seed):
    rec = json.load(open(RECORDED % seed))
    if sorted(int(x) for x in W) != sorted(int(x) for x in rec["W"]):
        return "W differs from recorded 8.25 W"
    for i, r in enumerate(rows["trained"]["early"]):
        for k in (f"{s}_{n}" for n in TICKS for s in STIMS):
            mine, old = r["probes"][k]["W_cells"], rec["states"][i]["part2"]["N"][k]["W_cells"]
            if mine != old:
                return f"early state {i} {k} W_cells: mine {mine} recorded {old}"
    return None


def table(arm, win, rws, mean):
    print(f"\n[{arm} {win}] W cells of 16, stimulus at 50 ticks | at 200 ticks")
    print("%8s | %s | %s" % ("t", " ".join("%6s" % s for s in STIMS), " ".join("%6s" % s for s in STIMS)))
    for r in rws:
        print("%8d | %s | %s" % (r["t"], " ".join("%6d" % r["probes"][f"{s}_50"]["W_cells"] for s in STIMS),
                                 " ".join("%6d" % r["probes"][f"{s}_200"]["W_cells"] for s in STIMS)))
    print("%8s | %s | %s" % ("mean", " ".join("%6.2f" % mean[f"{s}_50"]["W_cells"] for s in STIMS),
                             " ".join("%6.2f" % mean[f"{s}_200"]["W_cells"] for s in STIMS)))


def main():
    arg = lambda k, d=None: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
    smoke = "--smoke" in sys.argv
    seed, path = int(arg("--seed", 1)), arg("--path")
    assert params.ACTIVE_PROFILE == "gen2", "k826 needs BRAINSIM_PLANT=gen2 in the environment"
    assert path in ("P", "PH", "TH"), "--path {P,PH,TH} is required"
    tl = SMOKE if smoke else FULL
    if smoke:
        k03.WARMUP_TICKS = 4000
    eng, _ = k03.warm_engine(seed)
    net = eng.net
    hpc, ctx = encode.hpc_e_ids(net), encode.ctx_e_ids(net)
    groups = {"hpc": hpc, "ctx": ctx}
    h.install_tracking(groups, net.n)
    h.own_params(eng, t6.OVERRIDES)
    assert not eng.triplet_stdp
    eng.triplet_stdp = path == "TH"
    k11._step_chunked_counting(eng, BASE_TICKS)
    assert eng.g_struct == 0.0
    T0 = int(eng.t)
    A_ids = np.asarray(eng.patterns[PATTERN_A], np.int64)
    print(f"seed {seed} path {path} T0={T0}" + ("  [SMOKE]" if smoke else ""))

    engs = {"trained": eng, "never": copy.deepcopy(eng)}
    for e in engs.values():
        e.hetero_write = path != "P"
    h.register(engs["trained"])
    h.TRACK["ctx"] = h.TRACK["hpc"] = 0.0

    end = tl["late"][-1]
    rows = {a: {w: [] for w in WINDOWS} for a in ARMS}
    health, W = {}, None
    for arm in ARMS:
        e = engs[arm]
        log = {"sweeps": [], "B": []}
        tot = np.zeros(e.net.n, np.int64)
        if arm == "trained":
            e.present(PATTERN_A, A_TICKS)
        off = 0
        while off < end:
            if off == tl["B_at"]:
                e.present(PATTERN_B, B_TICKS)
            c = step1000(e, log, False)
            h.check_phase(e)
            off += 1000
            if arm == "trained" and off <= A_TICKS:
                tot += c
            if arm == "trained" and off == A_TICKS:
                W = encode.select_winners(tot, hpc, K_W)
            for win in WINDOWS:
                if off in tl[win]:
                    rows[arm][win].append({"t": int(e.t), "probes": readout(e, W, hpc, ctx, A_ids)})
        health[arm] = {"saturated_frac_w_ge_0.999_wmax": saturated(e.net, groups), "hetero_sweeps": len(log["sweeps"])}
        if arm == "trained":
            health[arm]["max_one_tick_frac"] = {"ctx": h.TRACK["ctx"], "hpc": h.TRACK["hpc"]}
        h.unregister(e)
        print(f"arm {arm} done, t={e.t}", flush=True)

    means = {a: {w: c823.mean_dicts([r["probes"] for r in rows[a][w]]) for w in WINDOWS} for a in ARMS}
    reads = {w: readings({a: means[a][w] for a in ARMS}) for w in WINDOWS}

    validity = {"valid": None, "first_mismatch": None}
    if path == "P" and not smoke:
        mm = validate(rows, W, seed)
        validity = {"valid": mm is None, "first_mismatch": mm}
        print("validity:", "VALID" if mm is None else f"INVALID, first mismatch {mm}")
    else:
        print("validity: not applicable" + (" (smoke)" if smoke else f" (path {path})"))

    for win in WINDOWS:
        for arm in ARMS:
            table(arm, win, rows[arm][win], means[arm][win])
        r = reads[win]
        print(f"\n=== readings, {win} window ===")
        for n in TICKS:
            x = r[f"half_{n}"]
            print(f"half cue at {n}: trained {x['trained']:.2f} never {x['never']:.2f} difference {x['difference']:+.2f}")
        for a in ARMS:
            x = r[a]
            print(f"{a}: K1.1 clause as a diagnostic (half cue, 50 ticks, mean >= 13): {x['K1.1 clause (half cue, 50 ticks, mean >= 13)']}")
            print(f"{a}: K1.1-200 (diagnostic, NOT K1.1): {x['K1.1-200 (diagnostic, NOT K1.1)']}")
            print(f"{a}: idle <= 3 at 50: {x['idle <= 3 at 50']}; B <= 0.5*half at 50: {x['B <= 0.5 * half at 50']}, at 200: {x['B <= 0.5 * half at 200']}")
            print(f"{a}: no-stimulus probe ctx_hz {x['none ctx_hz (50, 200)']} hpc_hz {x['none hpc_hz (50, 200)']}")
    print("\nhealth:", json.dumps(health))

    rec = {"seed": seed, "path": path, "smoke": smoke, "T0": T0, "W": W.tolist(), "rows": rows, "means": means,
           "readings": reads, "health": health, "validity": validity}
    if arg("--json"):
        with open(arg("--json"), "w") as f:
            json.dump(rec, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    sys.exit(2 if validity["valid"] is False else 0)


if __name__ == "__main__":
    main()
