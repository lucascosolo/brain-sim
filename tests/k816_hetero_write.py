"""SPEC 8.16 kill test T4: the engine's own sweep-level heterosynaptic write on hpc afferents.
Run: PYTHONPATH=<worktree> python tests/k816_hetero_write.py [--seed N] [--json out.json] [--smoke]
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
from k815_selective_write import contrast, hz, retention
from brainsim import encode, params

PATTERN_A, PATTERN_B = 0, 1
A_TICKS = B_TICKS = 2000
BASE_TICKS = 2000
K_W = 16
READOUT_TICKS = 50
C1_MIN, C2_MIN, C3_MIN, C5_MAX = 12, 0.20, 0.80, 2.0
HPC_E_HZ, CTX_E_HZ = (0.5, 1.5), (3.0, 5.0)
ARMS = ("on", "off", "never")

# offsets from T0 = 122,000 (full) / the post-baseline tick (smoke)
FULL = {"snaps": (2000, 3000, 8000, 18000, 38000, 42000, 62000), "B_at": 40000, "end": 62000,
        "phases": ((28000, "sleep"), (39000, "wake")), "c5": ((4000, 18000), (44000, 62000))}
SMOKE = {"snaps": (2000, 3000, 4000, 5000, 6000, 7000, 8000), "B_at": 5000, "end": 8000,
         "phases": (), "c5": ((3000, 4000), (7000, 8000))}


def abort(eng, expected):
    print(f"ABORT: phase at t={eng.t} is {eng.phase}, expected {expected}")
    print("EXIT ABORT")
    sys.exit(2)


def step1000(eng, log, is_on, marks_set=None, W=None, B_window=None):
    """One 1000-tick chunk; record a hetero sweep if one fired in it."""
    n0 = eng.stats["hetero_sweeps"]
    c = k11._step_chunked_counting(eng, 1000)
    if eng.stats["hetero_sweeps"] - n0 > 1:
        raise RuntimeError("more than one hetero sweep in one chunk; hetero_last holds only the last")
    if eng.stats["hetero_sweeps"] != n0:
        log["sweeps"].append((int(eng.t), int(eng.stats["hetero_cells_last"])))
        h = eng.hetero_last
        if is_on and B_window and B_window[0] < eng.t <= B_window[1]:
            cells = set(h["cells"].tolist()) if h else set()
            ids = set(zip(h["pre"].tolist(), h["post"].tolist(), h["born"].tolist())) if h else set()
            log["B"].append({"t": int(eng.t), "W_cells": len(cells & set(W.tolist())),
                             "marks_rewritten": len(ids & marks_set)})
    return c


def build_marks(a_writes, W):
    Wset = set(W.tolist())
    marks = []
    for (pre, post, born), dw in a_writes.items():
        if post in Wset and dw != 0:
            marks.append((pre, post, born, bool(dw > 0)))
    return marks


def readout(eng, W, A_ids):
    cue = encode.cue_ids(A_ids)
    hpc = encode.hpc_e_ids(eng.net)
    out = {}
    for name in ("full_A", "half_cue", "none"):
        e = copy.deepcopy(eng)
        e.hetero_write = False
        if name == "full_A":
            e.present(PATTERN_A, READOUT_TICKS)
        elif name == "half_cue":
            e.inject(cue, params.PATTERN_AMP_MV, READOUT_TICKS)
        c = k11._step_chunked_counting(e, READOUT_TICKS)
        out[name] = {"W_spiking": int((c[W] > 0).sum()), "of": int(len(W)),
                     "hpc_E_spikes": int(c[hpc].sum())}
    return out


def main():
    smoke = "--smoke" in sys.argv
    seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 1
    tl = SMOKE if smoke else FULL
    if smoke:
        k03.WARMUP_TICKS = 4000
    eng, _ = k03.warm_engine(seed)
    net = eng.net
    hpc, ctx = encode.hpc_e_ids(net), encode.ctx_e_ids(net)
    hpc_i = np.arange(net.region_slice["hpc"].start + params.REGIONS["hpc"]["n_exc"],
                      net.region_slice["hpc"].stop)
    base = k11._step_chunked_counting(eng, BASE_TICKS)
    baseline = {"hpc_E": hz(base, hpc, BASE_TICKS), "ctx_E": hz(base, ctx, BASE_TICKS)}
    T0 = int(eng.t)
    print(f"seed {seed} T0={T0} baseline idle Hz {baseline}" + ("  [SMOKE]" if smoke else ""))
    if smoke:
        print("smoke: warm-up 4,000, timeline compressed, phase assertions skipped")
    copies = {"on": (True, True), "off": (False, True), "never": (True, False)}
    engs, logs = {}, {}
    for arm, (flag, _) in copies.items():
        engs[arm] = copy.deepcopy(eng)
        engs[arm].hetero_write = flag
        logs[arm] = {"sweeps": [], "B": []}
    del eng

    # ---- A epoch --------------------------------------------------------- #
    a_writes, a_cells = {}, set()
    a_counts = None
    for arm in ARMS:
        if copies[arm][1]:
            engs[arm].present(PATTERN_A, A_TICKS)
    for arm in ARMS:
        e = engs[arm]
        tot = np.zeros(net.n, np.int64)
        for _ in range(A_TICKS // 1000):
            tot += step1000(e, logs[arm], arm == "on")
            if arm == "on" and e.hetero_last is not None and e.hetero_last["t"] == e.t:
                h = e.hetero_last
                a_cells |= set(h["cells"].tolist())
                for pre, post, born, dw, wm in zip(h["pre"].tolist(), h["post"].tolist(),
                                                   h["born"].tolist(), h["dw"].tolist(), h["w_max"].tolist()):
                    a_writes[(pre, post, born)] = a_writes.get((pre, post, born), 0.0) + dw / wm
        if arm == "on":
            a_counts = tot
    W = encode.select_winners(a_counts, hpc, K_W)
    marks = build_marks(a_writes, W)
    marks_set = {m[:3] for m in marks}
    n_trig_W = len(set(W.tolist()) & a_cells)
    print(f"W={W.tolist()} W cells triggered {n_trig_W}/{len(W)}; marks {len(marks)} "
          f"(U {sum(m[3] for m in marks)}, D {sum(not m[3] for m in marks)})")
    A_ids = np.asarray(engs["on"].patterns[PATTERN_A], np.int64)

    # ---- untouched epoch ------------------------------------------------- #
    snaps = {a: {} for a in ("on", "off")}
    rate_counts = {a: [] for a in ARMS}
    phases = dict(tl["phases"])
    for arm in ARMS:
        e = engs[arm]
        if arm in snaps:
            snaps[arm][A_TICKS] = k11._snapshot(e.net)
        off = A_TICKS
        while off < tl["end"]:
            if off == tl["B_at"]:
                e.present(PATTERN_B, B_TICKS)
            c = step1000(e, logs[arm], arm == "on", marks_set, W,
                         (T0 + tl["B_at"], T0 + tl["B_at"] + B_TICKS))
            off += 1000
            rate_counts[arm].append(c)
            if arm in snaps and off in tl["snaps"]:
                snaps[arm][off] = k11._snapshot(e.net)
            if off in phases and e.phase != phases[off]:
                abort(e, phases[off])
        print(f"arm {arm} done, t={e.t}")

    # ---- metrics --------------------------------------------------------- #
    res = {"smoke": smoke, "seed": seed, "T0": T0, "W": W.tolist(), "baseline": baseline,
           "n_marks": len(marks), "W_triggered": n_trig_W, "arms": {}}
    rates = {}
    for arm in ARMS:
        idle = sum(rate_counts[arm][-2:])
        rates[arm] = {"hpc_E": hz(idle, hpc, 2000), "hpc_I": hz(idle, hpc_i, 2000),
                      "ctx_E": hz(idle, ctx, 2000), "W": hz(idle, W, 2000),
                      "alive": int(engs[arm].net.alive.sum())}
    con = {a: {t: contrast(snaps[a][t], marks) for t in tl["snaps"]} for a in snaps}
    ret = {}
    for t in tl["snaps"]:
        o, f = con["on"], con["off"]
        ret[t] = {"R_C": retention(o[t]["C"], f[t]["C"], o[A_TICKS]["C"], f[A_TICKS]["C"]),
                  "R_U": retention(o[t]["U_mean"], f[t]["U_mean"], o[A_TICKS]["U_mean"], f[A_TICKS]["U_mean"])}
    cols = ("C", "C_survivors", "M", "U_mean", "D_mean", "dead_U", "dead_D")
    print("\n%-6s %7s " % ("arm", "t") + " ".join("%11s" % c for c in cols))
    for arm in ("on", "off"):
        for t in tl["snaps"]:
            print("%-6s %7d " % (arm, T0 + t) + " ".join("%11.4f" % con[arm][t][k] for k in cols))
    print("\nretention vs off (denominator: 124,000 values): R_C, R_U")
    for t in tl["snaps"]:
        print("%7d  R_C %8.3f  R_U %8.3f" % (T0 + t, ret[t]["R_C"], ret[t]["R_U"]))
    print("\nrates at end window (Hz) and alive synapses:")
    for arm in ARMS:
        print(" ", arm, {k: round(v, 3) for k, v in rates[arm].items()})
    sw = logs["on"]["sweeps"]
    print("on-arm hetero_cells_last per sweep:", sw)
    print("never-arm hetero_cells_last per sweep:", logs["never"]["sweeps"])
    print("on-arm B sweeps (W cells triggered, mark identities rewritten):", logs["on"]["B"])

    bg = [c for t, c in sw if any(a <= t - T0 <= b for a, b in tl["c5"])]
    bg_mean = float(np.mean(bg)) if bg else float("nan")
    end = tl["snaps"][-1]
    written = con["on"][A_TICKS]["C"] - con["off"][A_TICKS]["C"]
    r_c = ret[end]["R_C"]
    r = rates["on"]
    crit = {"c1_selfselect": (n_trig_W >= C1_MIN, n_trig_W),
            "c2_written_contrast": (bool(written >= C2_MIN), written),
            "c3_retention": (bool(r_c >= C3_MIN), r_c),
            "c4_rates": (bool(HPC_E_HZ[0] <= r["hpc_E"] <= HPC_E_HZ[1]
                              and CTX_E_HZ[0] <= r["ctx_E"] <= CTX_E_HZ[1]), (r["hpc_E"], r["ctx_E"])),
            "c5_background": (bool(bg_mean <= C5_MAX), bg_mean)}
    verdict = "PASS" if all(v[0] for v in crit.values()) else "FAIL"
    v = {"seed": seed, "verdict": verdict, "criteria": {k: bool(x[0]) for k, x in crit.items()},
         "numbers": {k: x[1] for k, x in crit.items()}}
    print("\nT4 verdict:", v)
    for k, (ok, num) in crit.items():
        print(f"  {k}: {ok}  ({num})")
    print(f"information (no bar): survivors-only C at end on/off "
          f"{con['on'][end]['C_survivors']:.4f}/{con['off'][end]['C_survivors']:.4f}; "
          f"R_U {ret[end]['R_U']:.3f}; dead_U/dead_D on at end "
          f"{con['on'][end]['dead_U']}/{con['on'][end]['dead_D']}; alive on/off "
          f"{rates['on']['alive']}/{rates['off']['alive']}")
    ro = {a: readout(engs[a], W, A_ids) for a in ARMS}
    print("\nReadout at end: DIAGNOSTIC ONLY (not a pass bar; K1.1 not run)")
    for a in ARMS:
        print(f"  {a:6s}", ro[a])
    res.update(contrast=con, retention=ret, rates=rates, sweeps={a: logs[a]["sweeps"] for a in ARMS},
               B_sweeps=logs["on"]["B"], readout=ro, verdict=v)
    if "--json" in sys.argv:
        with open(sys.argv[sys.argv.index("--json") + 1], "w") as f:
            json.dump(res, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(f"EXIT {verdict}")


if __name__ == "__main__":
    main()
