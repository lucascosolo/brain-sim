"""SPEC 8.21 kill test T6: triplet potentiation beside the heterosynaptic write, on the slowed homeostat.
Run: PYTHONPATH=<worktree> python tests/k821_triplet.py [--seed N] [--json out.json] [--smoke]
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
from k815_selective_write import contrast, hz
from k816_hetero_write import A_TICKS, B_TICKS, BASE_TICKS, K_W, PATTERN_A, PATTERN_B, READOUT_TICKS, build_marks, step1000
from brainsim import encode

N_P = 100
V1_REF = {1: (8, 0.258), 2: (12, 0.239), 3: (13, 0.293)}
HPC_BAND, CTX_BAND = (0.5, 1.5), (3.0, 5.0)
MAX_FRAC, MAX_SAT, MAX_DIED = 0.20, 0.20, 0.20
C1_MIN, C2_SLACK, C2_B_MUL, C2_B_ADD, C3_MIN = 1.20, 0.05, 1.20, 1.0, 1.10
OVERRIDES = {"STRUCT_BASE": 0.0, "ETA_SCALING": 0.01, "SCALING_CLIP": 0.01}   # 8.19's C3, absolute values
ARMS = ("on", "nowrite", "never", "pair_on")
SPEC = {"on": ("tri", True, True), "nowrite": ("tri", False, True), "never": ("tri", True, False),
        "pair_on": ("pair", True, True)}                 # arm: (lineage, hetero_write, A presented)
# offsets from T0 = 122,000: early 180,000..184,000, late 434,000..438,000, end 440,000
FULL = {"early": (58000, 59000, 60000, 61000, 62000), "late": (312000, 313000, 314000, 315000, 316000),
        "B_at": 40000, "end": 318000, "hz": {"184": 62000, "300": 178000, "440": 318000}}
SMOKE = {"early": (3000, 4000, 5000, 6000, 7000), "late": (11000, 12000, 13000, 14000, 15000),
         "B_at": 4000, "end": 17000, "hz": {"184": 7000, "300": 12000, "440": 17000}}


def _s(x):
    return x[0] / (x[0] + x[1]) if (x[0] + x[1]) else 0.0


def verdict(rec):
    """(all clauses hold, failed clause names in order) for one seed's record."""
    failed = []
    n, c = V1_REF[rec["seed"]]
    p = rec["pair_on"]
    if not (p["W_cells_full_A_184"] == n and round(p["surv_contrast_184"], 3) == c):
        failed.append("V1")
    inband = lambda v, b: b[0] <= v <= b[1]
    if not (all(inband(rec["hz"][t]["hpc_E"], HPC_BAND) and inband(rec["hz"][t]["ctx_E"], CTX_BAND) for t in ("184", "300", "440"))
            and max(rec["max_tick_frac"].values()) <= MAX_FRAC):
        failed.append("V2")
    if not all(rec[k][t][g] <= lim for k, lim in (("sat", MAX_SAT), ("died", MAX_DIED))
               for t in ("184", "440") for g in ("ctx_E", "hpc_E")):
        failed.append("V3")
    on, nv = rec["early"]["on"], rec["early"]["never"]
    if not (on["deliv_A"] >= C1_MIN * nv["deliv_A"] and on["W_spikes_A"] >= C1_MIN * nv["W_spikes_A"]):
        failed.append("c1")
    if not (_s((on["W_spikes_A"], on["W_spikes_B"])) >= _s((nv["W_spikes_A"], nv["W_spikes_B"])) - C2_SLACK
            and on["W_spikes_B"] <= C2_B_MUL * nv["W_spikes_B"] + C2_B_ADD):
        failed.append("c2")
    if not rec["late"]["on"]["deliv_A"] >= C3_MIN * rec["late"]["never"]["deliv_A"]:
        failed.append("c3")
    return not failed, failed


def mean_over(rows):
    return {k: float(np.mean([r[k] for r in rows])) for k in rows[0]}


def readout_row(eng, W, A_ids, own_W=None):
    """One readout: three probes on deep copies. Own-W counts are for pair_on's V1 (same full-A run)."""
    c, dv = h.probe_full_A(eng, W)
    half = h.on_W(h.probe_counts(eng, "half", A_ids), W)
    b = h.on_W(h.probe_counts(eng, "B", A_ids), W)
    a = h.on_W(c, W)
    row = {"deliv_A": dv, "W_spikes_A": a["spikes"], "W_cells_A": a["cells"], "W_spikes_half": half["spikes"],
           "W_cells_half": half["cells"], "W_spikes_B": b["spikes"], "W_cells_B": b["cells"]}
    return row, c


def main():
    smoke = "--smoke" in sys.argv
    seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 1
    tl = SMOKE if smoke else FULL
    if smoke:
        k03.WARMUP_TICKS = 4000
    eng, _ = k03.warm_engine(seed)
    net = eng.net
    hpc, ctx = encode.hpc_e_ids(net), encode.ctx_e_ids(net)
    groups = {"hpc": hpc, "ctx": ctx}
    h.install_tracking(groups, net.n)

    # ---- two lineages from the warmed plant, each with its own parameter object ---------------------------- #
    base = {"pair": eng, "tri": copy.deepcopy(eng)}
    for name, e in base.items():
        h.own_params(e, OVERRIDES)
        e.triplet_stdp = name == "tri"
        h.register(e)
    h.TRACK["ctx"] = h.TRACK["hpc"] = 0.0
    for e in base.values():
        k11._step_chunked_counting(e, BASE_TICKS)
        assert e.g_struct == 0.0
    assert base["tri"].triplet_view()["on"] and not base["pair"].triplet_stdp
    T0 = int(eng.t)
    print(f"seed {seed} T0={T0}" + ("  [SMOKE]" if smoke else ""))
    print("overrides:", OVERRIDES, " triplet:", base["tri"].triplet_view())
    ident0 = h.identities(base["tri"].net, groups)

    p0 = copy.deepcopy(base["tri"])
    p0.hetero_write = False
    p0.present(PATTERN_A, READOUT_TICKS)
    c = k11._step_chunked_counting(p0, READOUT_TICKS)
    P = ctx[np.argsort(-c[ctx], kind="stable")[:N_P]]
    del p0
    A_ids = np.asarray(base["tri"].patterns[PATTERN_A], np.int64)

    engs = {"on": base["tri"], "nowrite": copy.deepcopy(base["tri"]), "never": copy.deepcopy(base["tri"]),
            "pair_on": base["pair"]}
    for arm, (_, flag, _) in SPEC.items():
        engs[arm].hetero_write = flag
        h.register(engs[arm])
    del base, eng

    early_end = tl["early"][-1]
    rows = {"early": {a: [] for a in ARMS}, "late": {a: [] for a in ARMS}}
    extra = {a: {} for a in ARMS}           # per-readout-time reports
    state = {"W": None, "marks": None, "own_W": None, "own_marks": None}
    hz_rec, sat_rec, died_rec = {}, {}, {}
    series = []

    for arm in ARMS:
        e = engs[arm]
        end = tl["end"] if arm in ("on", "never") else early_end
        log = {"sweeps": [], "B": []}
        a_log = {"writes": {}, "cells": set()}
        tot = np.zeros(e.net.n, np.int64)
        win = []
        if SPEC[arm][2]:
            e.present(PATTERN_A, A_TICKS)
        off = 0
        while off < end:
            if off == tl["B_at"]:
                e.present(PATTERN_B, B_TICKS)
            c = step1000(e, log, False)
            win.append(c)
            win = win[-2:]
            h.check_phase(e)
            off += 1000
            if arm in ("on", "pair_on") and off <= A_TICKS:
                tot += c
                h.a_epoch_log(e, a_log)
            if off == A_TICKS and arm in ("on", "pair_on"):
                Wa = encode.select_winners(tot, hpc, K_W)
                marks = build_marks(a_log["writes"], Wa)
                key = ("W", "marks") if arm == "on" else ("own_W", "own_marks")
                state[key[0]], state[key[1]] = Wa, marks
            if arm == "on":
                series.append({"t": int(e.t), **{k: v for k, v in h.hz_pair(c, groups, 1000).items()},
                               "mean_o2": e.triplet_view()["mean_o2"]})
            for tag, t in tl["hz"].items():
                if off == t and arm == "on":
                    hz_rec[tag] = h.hz_pair(sum(win), groups, 2000)
                if off == t and arm == "on" and tag != "300":
                    sat_rec[tag], died_rec[tag] = h.sat_and_died(e.net, groups, ident0)
            for set_name in ("early", "late"):
                if off in tl[set_name] and (set_name == "early" or arm in ("on", "never")):
                    W = state["W"]
                    row, cA = readout_row(e, W, A_ids)
                    row["P_spikes_A"] = int(cA[P].sum())
                    ex = {}
                    if arm == "pair_on":
                        own = h.on_W(cA, state["own_W"])
                        ex["own_W_cells_A"], ex["own_W_spikes_A"] = own["cells"], own["spikes"]
                    mk = state["own_marks"] if arm == "pair_on" else state["marks"]
                    if arm in ("on", "pair_on"):
                        con = contrast(k11._snapshot(e.net), mk)
                        ex["con_C"], ex["con_C_survivors"] = con["C"], con["C_survivors"]
                    extra[arm][off] = ex
                    rows[set_name][arm].append(row)
            if off in (tl["early"][-1], tl["hz"]["300"], tl["end"]):
                extra[arm].setdefault("proj", {})[off] = h.projections(e.net)
        h.unregister(e)
        print(f"arm {arm} done, t={e.t}")

    mf = {"ctx_E": h.TRACK["ctx"], "hpc_E": h.TRACK["hpc"]}
    early = {a: mean_over(rows["early"][a]) for a in ARMS}
    late = {a: mean_over(rows["late"][a]) for a in ("on", "never")}
    last = extra["pair_on"][early_end]
    rec = {"seed": seed, "smoke": smoke, "T0": T0,
           "pair_on": {"W_cells_full_A_184": last["own_W_cells_A"], "surv_contrast_184": last["con_C_survivors"],
                       "own_W_spikes_A_184": last["own_W_spikes_A"], "C_184": last["con_C"]},
           "hz": hz_rec, "max_tick_frac": mf, "sat": sat_rec, "died": died_rec,
           "early": early, "late": late, "rows": rows, "extra": extra, "series": series,
           "W": state["W"].tolist(), "own_W": state["own_W"].tolist(), "P": P.tolist(),
           "overrides": OVERRIDES, "triplet_k": engs["on"].triplet_view()["k"]}

    for set_name, tab in (("early", early), ("late", late)):
        print(f"\n[{set_name}] mean over five readouts (W read on the on arm's W)")
        keys = list(next(iter(tab.values())))
        print("%10s " % "" + " ".join("%14s" % k for k in keys))
        for a, r in tab.items():
            print("%10s " % a + " ".join("%14.3f" % r[k] for k in keys))
    print("\nhz (on, 2 idle sweeps):", {t: {k: round(v, 3) for k, v in d.items()} for t, d in hz_rec.items()})
    print("max tick fraction:", mf, " sat:", sat_rec, " died:", died_rec)
    print("pair_on own W:", rec["pair_on"])

    ok, failed = verdict(rec)
    rec["verdict"] = {"ok": ok, "failed": failed}
    print(f"\n=== T6 clauses, seed {seed} ===")
    for cl in ("V1", "V2", "V3", "c1", "c2", "c3"):
        print(f"{cl}: {'FAIL' if cl in failed else 'PASS'}")
    if "--json" in sys.argv:
        with open(sys.argv[sys.argv.index("--json") + 1], "w") as f:
            json.dump(rec, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print("EXIT SMOKE" if smoke else ("EXIT PASS" if ok else "EXIT REJECTED"))


if __name__ == "__main__":
    main()
