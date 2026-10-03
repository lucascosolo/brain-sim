"""SPEC 8.15 selective-write contrast fixture (a diagnostic, not a mechanism). Seed 1, default plant.
Three twins at t_w (after A): selective (U up, D down, cell sum kept), uniform (U and D up), sham.
Run: PYTHONPATH=<worktree> python tests/k815_selective_write.py [--json out.json] [--smoke]
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
from brainsim import encode, params

SEED = 1
PATTERN_A, PATTERN_B = 0, 1
A_TICKS = B_TICKS = 2000
BASE_TICKS = 2000
K_W = 16
READOUT_TICKS = 50
VALID_MIN = 0.20
R_C_MIN = 0.80
R_M_MAX = 0.80
HPC_E_HZ = (0.5, 1.5)
CTX_E_HZ = (3.0, 5.0)
ARMS = ("selective", "uniform", "sham")


# --------------------------------------------------------------------------- #
# pure functions
# --------------------------------------------------------------------------- #

def split_marks(net, W, donor_counts, src_ids):
    W = np.asarray(W, np.int64)
    in_w = np.zeros(net.n, bool)
    in_w[W] = True
    in_src = np.zeros(net.n, bool)
    in_src[np.asarray(src_ids, np.int64)] = True
    slots = np.flatnonzero(net.alive & in_w[net.post] & in_src[net.pre])
    counts = np.asarray(donor_counts).astype(np.int64)
    U, D = [], []
    for c in np.unique(net.post[slots]):
        s = slots[net.post[slots] == c]
        s = s[np.lexsort((s, -counts[net.pre[s]]))]
        h = math.ceil(len(s) / 2)
        U.extend(s[:h])
        D.extend(s[h:])
    return np.sort(np.asarray(U, np.int64)), np.sort(np.asarray(D, np.int64))


def selective_write(net, U, D, delta_frac=0.15, floor_frac=0.10):
    U, D = np.asarray(U, np.int64), np.asarray(D, np.int64)
    marks = np.concatenate([U, D])
    before = net.w[marks].astype(np.float64)
    wmax = net.w_max_n[net.post].astype(np.float64)
    w_old_U = net.w[U].astype(np.float64)
    w_new_U = np.minimum(w_old_U + delta_frac * wmax[U], wmax[U])
    n_clamped_up = int((w_old_U + delta_frac * wmax[U] > wmax[U]).sum())
    net.w[U] = w_new_U
    up_by_cell = {}
    for s, inc in zip(U, w_new_U - w_old_U):
        up_by_cell[int(net.post[s])] = up_by_cell.get(int(net.post[s]), 0.0) + float(inc)
    n_clamped_down = 0
    for c, total_up in up_by_cell.items():
        d = D[net.post[D] == c]
        if d.size == 0:
            continue
        floor = floor_frac * float(net.w_max_n[c])
        w = net.w[d].astype(np.float64)
        lowered = w - total_up / d.size
        new = np.where(w < floor, w, np.maximum(lowered, floor))
        n_clamped_down += int(((w >= floor) & (lowered < floor)).sum())
        net.w[d] = new
    after = net.w[marks].astype(np.float64)
    resid = {}
    for s, b, a in zip(marks, before, after):
        c = int(net.post[s])
        resid[c] = resid.get(c, 0.0) + float(a - b)
    return {"n_U": int(U.size), "n_D": int(D.size), "n_clamped_up": n_clamped_up,
            "n_clamped_down": n_clamped_down, "residual_per_cell": resid,
            "max_abs_residual": max((abs(v) for v in resid.values()), default=0.0)}


def uniform_write(net, U, D, delta_frac=0.15):
    marks = np.concatenate([np.asarray(U, np.int64), np.asarray(D, np.int64)])
    wmax = net.w_max_n[net.post[marks]].astype(np.float64)
    raw = net.w[marks].astype(np.float64) + delta_frac * wmax
    net.w[marks] = np.minimum(raw, wmax)
    return {"n": int(marks.size), "n_clamped": int((raw > wmax).sum())}


def marks_from(snap, U, D):
    out = []
    for ids, up in ((U, True), (D, False)):
        for s in np.asarray(ids, np.int64):
            out.append((int(snap["pre"][s]), int(snap["post"][s]), int(snap["born"][s]), up))
    return out


def _alive_lookup(snap, marks):
    posts = np.unique([m[1] for m in marks]) if marks else np.empty(0, np.int64)
    in_p = np.zeros(len(snap["pre"]) and int(max(snap["post"].max(), posts.max() if posts.size else 0)) + 1, bool)
    in_p[posts] = True
    idx = np.flatnonzero(snap["alive"] & in_p[snap["post"]])
    return {(int(snap["pre"][i]), int(snap["post"][i]), int(snap["born"][i])):
            float(snap["w"][i]) / float(snap["w_max_post"][i]) for i in idx}


def _mark_values(snap, marks):
    look = _alive_lookup(snap, marks)
    return [(m[1], m[3], look.get(m[:3])) for m in marks]  # (post, is_up, frac or None)


def contrast(snap, marks):
    vals = _mark_values(snap, marks)
    cells = sorted({v[0] for v in vals})

    def cell_c(c, dead_as_zero):
        g = {True: [], False: []}
        for p, up, f in vals:
            if p != c:
                continue
            if f is None and not dead_as_zero:
                continue
            g[up].append(0.0 if f is None else f)
        if not g[True] or not g[False]:
            return None
        return float(np.mean(g[True]) - np.mean(g[False]))

    def cmean(dead_as_zero):
        x = [r for r in (cell_c(c, dead_as_zero) for c in cells) if r is not None]
        return float(np.mean(x)) if x else float("nan")

    def allmean(sel):
        x = [0.0 if f is None else f for p, up, f in vals if sel(up)]
        return float(np.mean(x)) if x else float("nan")

    return {"C": cmean(True), "C_survivors": cmean(False), "M": allmean(lambda u: True),
            "U_mean": allmean(lambda u: u), "D_mean": allmean(lambda u: not u),
            "dead_U": sum(1 for p, up, f in vals if up and f is None),
            "dead_D": sum(1 for p, up, f in vals if not up and f is None),
            "n_U": sum(1 for v in vals if v[1]), "n_D": sum(1 for v in vals if not v[1])}


def retention(x_arm_t, x_sham_t, x_arm_0, x_sham_0):
    den = x_arm_0 - x_sham_0
    return float("nan") if den == 0 else float((x_arm_t - x_sham_t) / den)


def cell_sums(snap, marks):
    """Mean over cells of the summed weight (w, dead as 0) of that cell's marks."""
    look = _alive_lookup(snap, marks)
    tot = {}
    for pre, post, born, _ in marks:
        f = look.get((pre, post, born))
        tot[post] = tot.get(post, 0.0) + (0.0 if f is None else f * float(snap["w_max_post"][
            np.flatnonzero(snap["post"] == post)[0]]))
    return float(np.mean(list(tot.values()))) if tot else float("nan")


# --------------------------------------------------------------------------- #
# driver
# --------------------------------------------------------------------------- #

def hz(counts, ids, ticks):
    return float(np.asarray(counts)[ids].sum()) * 1000.0 / (len(ids) * ticks)


FULL = {"pts": (0, 1000, 6000, 16000, 36000, 40000, 60000), "B_at": 38000, "end": 60000,
        "idle": 2000, "phases": ((26000, "sleep"), (37000, "wake")), "early": 2000}
SMOKE = {"pts": (0, 500, 1000, 1500, 2500, 3000, 4000), "B_at": 1500, "end": 4000,
         "idle": 1000, "phases": (), "early": 1000}


def run_arm(eng, t_w, tl, marks, W, n_cells):
    net = eng.net
    hpc, ctx = encode.hpc_e_ids(net), encode.ctx_e_ids(net)
    hpc_i = np.arange(net.region_slice["hpc"].start + params.REGIONS["hpc"]["n_exc"],
                      net.region_slice["hpc"].stop)
    snaps = {0: k11._snapshot(net)}
    seg = {}
    stops = set(tl["pts"]) | {tl["B_at"], tl["B_at"] + B_TICKS, tl["end"] - tl["idle"],
                              tl["early"], tl["end"]} | {p[0] for p in tl["phases"]}
    stops = sorted(s for s in stops if 0 < s <= tl["end"])
    phases = dict(tl["phases"])
    prev = 0
    for s in stops:
        if prev == tl["B_at"]:
            eng.present(PATTERN_B, B_TICKS)
        seg[(prev, s)] = k11._step_chunked_counting(eng, s - prev)
        prev = s
        if s in tl["pts"]:
            snaps[s] = k11._snapshot(net)
        if s in phases and eng.phase != phases[s]:
            print(f"ABORT: phase at t={eng.t} is {eng.phase}, expected {phases[s]}")
            print("EXIT ABORT")
            sys.exit(2)
    def window(a, b):
        return sum(c for (x, y), c in seg.items() if a <= x and y <= b)
    idle = window(tl["end"] - tl["idle"], tl["end"])
    early = window(0, tl["early"])
    rates = {"hpc_E": hz(idle, hpc, tl["idle"]), "hpc_I": hz(idle, hpc_i, tl["idle"]),
             "ctx_E": hz(idle, ctx, tl["idle"]),
             "W_idle_end": hz(idle, W, tl["idle"]), "W_early": hz(early, W, tl["early"])}
    con = {t: contrast(snaps[t], marks) for t in tl["pts"]}
    sums = {"write": cell_sums(snaps[0], marks), "end": cell_sums(snaps[tl["end"]], marks)}
    return eng, {"contrast": con, "rates": rates, "cell_sum": sums}


def readout(eng, W, A_ids):
    cue = encode.cue_ids(A_ids)
    out = {}
    for name in ("full_A", "half_cue", "none"):
        e = copy.deepcopy(eng)
        if name == "full_A":
            e.present(PATTERN_A, READOUT_TICKS)
        elif name == "half_cue":
            e.inject(cue, params.PATTERN_AMP_MV, READOUT_TICKS)
        c = k11._step_chunked_counting(e, READOUT_TICKS)
        out[name] = {"W_spiking": int((c[W] > 0).sum()), "of": int(len(W)),
                     "hpc_E_spikes": int(c[encode.hpc_e_ids(e.net)].sum())}
    return out


def main():
    smoke = "--smoke" in sys.argv
    tl = SMOKE if smoke else FULL
    if smoke:
        k03.WARMUP_TICKS = 4000
    eng, _ = k03.warm_engine(SEED)
    net = eng.net
    hpc, ctx = encode.hpc_e_ids(net), encode.ctx_e_ids(net)
    base_counts = k11._step_chunked_counting(eng, BASE_TICKS)
    baseline = {"hpc_E": hz(base_counts, hpc, BASE_TICKS), "ctx_E": hz(base_counts, ctx, BASE_TICKS)}
    print(f"baseline idle Hz {baseline}")
    eng.present(PATTERN_A, A_TICKS)
    counts = k11._step_chunked_counting(eng, A_TICKS)
    W = encode.select_winners(counts, hpc, K_W)
    U, D = split_marks(net, W, counts, ctx)
    print(f"t={eng.t} W={W.tolist()} marks U={U.size} D={D.size}" + ("  [SMOKE]" if smoke else ""))
    if smoke:
        print("smoke: timeline compressed, phase assertions skipped")
    t_w = eng.t
    A_ids = np.asarray(eng.patterns[PATTERN_A], np.int64)
    marks = marks_from(k11._snapshot(net), U, D)
    res = {"smoke": smoke, "t_w": t_w, "W": W.tolist(), "baseline": baseline, "arms": {}, "writes": {}}
    finals = {}
    for arm in ARMS:
        e = copy.deepcopy(eng)
        if arm == "selective":
            rec = selective_write(e.net, U, D)
            rec["residual_per_cell"] = {str(k): v for k, v in rec["residual_per_cell"].items()}
            res["writes"][arm] = rec
        elif arm == "uniform":
            res["writes"][arm] = uniform_write(e.net, U, D)
        e, res["arms"][arm] = run_arm(e, t_w, tl, marks, W, len(W))
        res["arms"][arm]["readout"] = readout(e, W, A_ids)
        print(f"arm {arm} done, t={e.t}")
    print("writes:", {k: {a: b for a, b in v.items() if a != "residual_per_cell"}
                      for k, v in res["writes"].items()})
    cols = ("C", "C_survivors", "M", "U_mean", "D_mean", "dead_U", "dead_D")
    print("\n%-10s %7s " % ("arm", "t") + " ".join("%11s" % c for c in cols))
    for arm in ARMS:
        for t in tl["pts"]:
            c = res["arms"][arm]["contrast"][t]
            print("%-10s %7d " % (arm, t_w + t) + " ".join("%11.4f" % c[k] for k in cols))
    ret = {}
    print("\nretention vs sham: R_C, R_U, R_M")
    for arm in ("selective", "uniform"):
        ret[arm] = {}
        a, s = res["arms"][arm]["contrast"], res["arms"]["sham"]["contrast"]
        for t in tl["pts"]:
            ret[arm][t] = {"R_C": retention(a[t]["C"], s[t]["C"], a[0]["C"], s[0]["C"]),
                           "R_U": retention(a[t]["U_mean"], s[t]["U_mean"], a[0]["U_mean"], s[0]["U_mean"]),
                           "R_M": retention(a[t]["M"], s[t]["M"], a[0]["M"], s[0]["M"])}
            r = ret[arm][t]
            print("%-10s %7d  R_C %8.3f  R_U %8.3f  R_M %8.3f" % (arm, t_w + t, r["R_C"], r["R_U"], r["R_M"]))
    res["retention"] = ret
    sham_w = res["arms"]["sham"]["cell_sum"]["write"]
    print("\nper-cell summed mark weight (mean over cells), end as fraction of sham write-time sum:")
    for arm in ARMS:
        cs = res["arms"][arm]["cell_sum"]
        cs["end_frac_of_sham_write"] = cs["end"] / sham_w
        print(f"  {arm:10s} write {cs['write']:.4f} end {cs['end']:.4f} frac {cs['end_frac_of_sham_write']:.3f}")
    print("rates (Hz):", {a: res["arms"][a]["rates"] for a in ARMS})
    end = tl["pts"][-1]
    sel = res["arms"]["selective"]
    sc, sh = sel["contrast"], res["arms"]["sham"]["contrast"]
    written = sc[0]["C"] - sh[0]["C"]
    r_c, r_u_sel = ret["selective"][end]["R_C"], ret["selective"][end]["R_U"]
    r_m_uni = ret["uniform"][end]["R_M"]
    rt = sel["rates"]
    crit = {
        "selective_R_C_ge_0.80": bool(r_c >= R_C_MIN),
        "uniform_R_M_lt_0.80": bool(r_m_uni < R_M_MAX),
        "hpc_E_in_0.5_1.5": bool(HPC_E_HZ[0] <= rt["hpc_E"] <= HPC_E_HZ[1]),
        "ctx_E_in_3_5": bool(CTX_E_HZ[0] <= rt["ctx_E"] <= CTX_E_HZ[1]),
    }
    valid = bool(written >= VALID_MIN)
    verdict = "INVALID" if not valid else ("PASS" if all(crit.values()) else "FAIL")
    v = {"valid": valid, "written_contrast": written, "criteria": crit,
         "numbers": {"selective_R_C": r_c, "uniform_R_M": r_m_uni,
                     "hpc_E_hz": rt["hpc_E"], "ctx_E_hz": rt["ctx_E"]},
         "verdict": verdict}
    res["verdict"] = v
    print("T3 verdict:", v)
    print(f"information (no bar): selective R_U >= 0.80 is {bool(r_u_sel >= 0.80)} (R_U = {r_u_sel:.3f}); "
          f"selective dead_U/dead_D at end {sc[end]['dead_U']}/{sc[end]['dead_D']}")
    print("\nReadout at end: DIAGNOSTIC ONLY (not a pass bar; K1.1 not run)")
    for arm in ARMS:
        print(f"  {arm:10s}", res["arms"][arm]["readout"])
    if "--json" in sys.argv:
        with open(sys.argv[sys.argv.index("--json") + 1], "w") as f:
            json.dump(res, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(f"EXIT {verdict}")


if __name__ == "__main__":
    main()
