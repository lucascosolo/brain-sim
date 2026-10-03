"""SPEC 8.19 diagnostic: which half of the homeostat (scaling or structural) suppresses a seen stimulus.
Per-engine parameter overrides applied at 120,000 on deep copies of the warmed default engine; engine untouched.
Run: PYTHONPATH=<worktree> python tests/k819_homeostat_ablation.py [--seed N] [--json out.json] [--smoke]
"""
import copy
import json
import os
import sys
import types

import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import k03_pairing as k03
import k11_binding as k11
from k815_selective_write import contrast, hz
from k816_hetero_write import A_TICKS, B_TICKS, BASE_TICKS, K_W, PATTERN_A, PATTERN_B, READOUT_TICKS, abort, build_marks, step1000
from k817_inh_homeostat import a_epoch_log
from k818_drive_loss import deliveries, flatten, state
from brainsim import encode, params

N_P = 100
CTX_E_HZ, HPC_E_HZ = (3.0, 5.0), (0.5, 1.5)
MAX_FRAC = 0.20
RATIO_MEAN_MIN, RATIO_END_MIN = 0.7, 0.85
D_REF = "/home/lucas/.cache/scratch/brainsim-diag/d_seed%d.json"
ARMS = ("on", "off", "neveroff")
SPEC = {"on": (True, True), "off": (False, True), "neveroff": (False, False)}   # arm: (hetero_write, A presented)
# offsets from T0 = 122,000: 125,000 126,000 127,000 140,000 160,000 164,000 184,000; "end2" = 300,000
FULL = {"probes": (3000, 4000, 5000, 18000, 38000, 42000, 62000), "B_at": 40000, "end": 62000, "end2": 178000,
        "phases": ((28000, "sleep"), (39000, "wake")), "phases2": ((108000, "sleep"), (119000, "wake")),
        "mean": (3000, 4000, 5000)}
SMOKE = {"probes": (3000, 4000, 5000, 7000, 8000), "B_at": 5000, "end": 8000, "end2": 12000,
         "phases": (), "phases2": (), "mean": (3000, 4000, 5000)}


def make_conditions(p):
    return {"C0": {},
            "C1": {"STRUCT_BASE": 0.0},
            "C2": {"ETA_SCALING": p.ETA_SCALING / 10.0, "SCALING_CLIP": p.SCALING_CLIP / 10.0},
            "C3": {"STRUCT_BASE": 0.0, "ETA_SCALING": p.ETA_SCALING / 10.0, "SCALING_CLIP": p.SCALING_CLIP / 10.0}}


# largest fraction of ctx E / hpc E spiking in one tick, over the registered arm engines (not probe copies)
TRACK = {"ids": set(), "ctx": 0.0, "hpc": 0.0, "ctx_mask": None, "hpc_mask": None}
_drain = k03._drain_telemetry


def _tracked_drain(eng):
    if id(eng) in TRACK["ids"]:
        for s in eng._buf_spikes:
            TRACK["ctx"] = max(TRACK["ctx"], np.count_nonzero(TRACK["ctx_mask"][s]) / np.count_nonzero(TRACK["ctx_mask"]))
            TRACK["hpc"] = max(TRACK["hpc"], np.count_nonzero(TRACK["hpc_mask"][s]) / np.count_nonzero(TRACK["hpc_mask"]))
    _drain(eng)


def full_probe(eng, W, P, sense_A, groups):
    """50-tick full-A probe, write off, on a deep copy: spikes and deliveries onto W from the same run."""
    e = copy.deepcopy(eng)
    e.hetero_write = False
    e.present(PATTERN_A, READOUT_TICKS)
    before = e.spike_counts().astype(np.int64)
    dl = deliveries(e, W, READOUT_TICKS)
    c = e.spike_counts().astype(np.int64) - before
    sp = {"P": int(c[P].sum()), "ctx_E": int(c[groups["ctx"]].sum()), "W_cells": int((c[W] > 0).sum()),
          "W": int(c[W].sum()), "hpc_E": int(c[groups["hpc"]].sum())}
    return sp, dl


def other_probe(eng, kind, W, P, A_ids):
    e = copy.deepcopy(eng)
    e.hetero_write = False
    if kind == "half":
        e.inject(encode.cue_ids(A_ids), e.p.PATTERN_AMP_MV, READOUT_TICKS)
    elif kind == "B":
        e.present(PATTERN_B, READOUT_TICKS)
    c = k11._step_chunked_counting(e, READOUT_TICKS)
    out = {"W_cells": int((c[W] > 0).sum())}
    if kind != "none":
        out["W"] = int(c[W].sum())
    if kind == "B":
        out["P"] = int(c[P].sum())
    return out


def idle_hz(counts, groups):
    return {"hpc_E": hz(counts, groups["hpc"], 2000), "ctx_E": hz(counts, groups["ctx"], 2000)}


def in_band(h):
    return bool(HPC_E_HZ[0] <= h["hpc_E"] <= HPC_E_HZ[1] and CTX_E_HZ[0] <= h["ctx_E"] <= CTX_E_HZ[1])


def run_condition(cid, base, tl, P, groups, ref, smoke):
    """base: this condition's engine at T0 (override applied, idled). Returns the condition record."""
    net = base.net
    ctx = groups["ctx"]
    engs = {}
    for arm, (flag, _) in SPEC.items():
        engs[arm] = copy.deepcopy(base)
        engs[arm].hetero_write = flag
        assert engs[arm].p.STRUCT_BASE == base.p.STRUCT_BASE and engs[arm].p.ETA_SCALING == base.p.ETA_SCALING
        TRACK["ids"].add(id(engs[arm]))
    A_ids = np.asarray(base.patterns[PATTERN_A], np.int64)
    ctxv = {"W": None, "marks": None, "marks_set": None, "n_trig": None}
    probes = {a: {} for a in ARMS}
    spikes_rec = {a: {} for a in ARMS}
    idle = {a: {} for a in ARMS}
    series = []
    validity = {}
    a_log = {"writes": {}, "cells": set()}
    last2 = {}
    end, end2 = tl["end"], tl["end2"]
    phases, phases2 = dict(tl["phases"]), dict(tl["phases2"])

    def measure(arm, off, e):
        W = ctxv["W"]
        sp, dl = full_probe(e, W, P, A_ids, groups)
        row = {"spikes." + k: v for k, v in sp.items()}
        row.update({"deliv." + k: v for k, v in flatten(dl).items()})
        h = other_probe(e, "half", W, P, A_ids)
        row.update({"half." + k: v for k, v in h.items()})
        b = other_probe(e, "B", W, P, A_ids)
        row.update({"B." + k: v for k, v in b.items()})
        row["none.W_cells"] = other_probe(e, "none", W, P, A_ids)["W_cells"]
        st = state(e.net, W, P, ctx)
        row.update({"state." + k: v for k, v in flatten(st).items()})
        row["state.alive"] = int(e.net.alive.sum())
        row["state.latched"] = "+".join(k for k, v in e.growth_halted.items() if v) or "-"
        if arm == "on":
            con = contrast(k11._snapshot(e.net), ctxv["marks"])
            row["con.C"], row["con.C_survivors"] = con["C"], con["C_survivors"]
        probes[arm][off] = row
        spikes_rec[arm][off] = sp
        if cid == "C0" and arm in ("off", "neveroff") and ref is not None and off in (tl["probes"][0], end):
            lab = "refoff" if arm == "off" else "refneveroff"
            key = str({tl["probes"][0]: 3000, end: 62000}[off]) if not smoke else None
            rsp, rdl = full_probe(e, np.asarray(ref["W"]), np.asarray(ref["P"]), A_ids, groups)
            want = ref["flat"][lab][key]
            got = (rsp["P"], rdl["exc_total"]["sum"])
            exp = (want["spikes.P"], want["deliv.exc_total.sum"])
            validity[f"{arm}@{off}"] = {"got": got, "want": exp, "ok": bool(got[0] == exp[0] and abs(got[1] - exp[1]) < 0.01)}

    for arm in ARMS:
        e = engs[arm]
        log = {"sweeps": [], "B": []}
        tot = np.zeros(net.n, np.int64)
        if SPEC[arm][1]:
            e.present(PATTERN_A, A_TICKS)
        off = 0
        counts = []
        while off < end:
            if off == tl["B_at"]:
                e.present(PATTERN_B, B_TICKS)
            c = step1000(e, log, False)
            counts.append(c)
            if arm == "on":
                series.append((int(e.t), hz(c, groups["hpc"], 1000), hz(c, ctx, 1000)))
                if off < A_TICKS:
                    tot += c
                    a_epoch_log(e, a_log)
            off += 1000
            if arm == "on" and off == A_TICKS:
                ctxv["W"] = encode.select_winners(tot, groups["hpc"], K_W)
                ctxv["marks"] = build_marks(a_log["writes"], ctxv["W"])
                ctxv["n_trig"] = len(set(ctxv["W"].tolist()) & a_log["cells"])
                con = contrast(k11._snapshot(e.net), ctxv["marks"])
                ctxv["con_A"] = {"C": con["C"], "C_survivors": con["C_survivors"]}
            if off in tl["probes"]:
                measure(arm, off, e)
            if off in phases and e.phase != phases[off]:
                abort(e, phases[off])
        idle[arm][end] = idle_hz(sum(counts[-2:]), groups)
        print(f"{cid} arm {arm} done, t={e.t}")
        if arm == "on":
            cnts = []
            while off < end2:
                c = step1000(e, log, False)
                cnts.append(c)
                series.append((int(e.t), hz(c, groups["hpc"], 1000), hz(c, ctx, 1000)))
                off += 1000
                if off in phases2 and e.phase != phases2[off]:
                    abort(e, phases2[off])
            idle[arm][end2] = idle_hz(sum(cnts[-2:]), groups)
            measure(arm, end2, e)
            print(f"{cid} arm on to t={e.t}")
    for e in engs.values():
        TRACK["ids"].discard(id(e))
    return dict(probes=probes, spikes=spikes_rec, idle=idle, series=series, validity=validity, W=ctxv["W"].tolist(),
                n_marks=len(ctxv["marks"]), n_trig_W=ctxv["n_trig"], con_A=ctxv["con_A"])


def clauses(rec, tl):
    """The decision-rule clauses of SPEC 8.19 for one condition on one seed."""
    pr = rec["spikes"]
    m = [pr["off"][o]["P"] / pr["neveroff"][o]["P"] if pr["neveroff"][o]["P"] else float("nan") for o in tl["mean"]]
    mean_of = lambda arm: float(np.mean([pr[arm][o]["P"] for o in tl["mean"]]))
    r_mean = mean_of("off") / mean_of("neveroff") if mean_of("neveroff") else float("nan")
    r_end = pr["off"][tl["end"]]["P"] / pr["neveroff"][tl["end"]]["P"] if pr["neveroff"][tl["end"]]["P"] else float("nan")
    h184, h300 = rec["idle"]["on"][tl["end"]], rec["idle"]["on"][tl["end2"]]
    out = {"rates_184": h184, "rates_300": h300, "rates_in_band": in_band(h184) and in_band(h300),
           "rates_in_band_all_arms_184": all(in_band(rec["idle"][a][tl["end"]]) for a in ARMS),
           "max_frac_ctx": rec["max_frac"]["ctx"], "max_frac_hpc": rec["max_frac"]["hpc"],
           "frac_ok": bool(max(rec["max_frac"].values()) <= MAX_FRAC),
           "P_ratio_each": m, "P_ratio_mean": r_mean, "P_ratio_mean_ok": bool(r_mean >= RATIO_MEAN_MIN),
           "P_ratio_end": r_end, "P_ratio_end_ok": bool(r_end >= RATIO_END_MIN),
           "surv_184": rec["probes"]["on"][tl["end"]]["con.C_survivors"]}
    out["eligible"] = bool(out["rates_in_band"] and out["frac_ok"] and out["P_ratio_mean_ok"] and out["P_ratio_end_ok"])
    return out


def print_tables(rec, times, T0, cid):
    keys = sorted({k for a in ARMS for t in times if t in rec["probes"][a] for k in rec["probes"][a][t]})
    for key in keys:
        print(f"\n[{cid}] {key}")
        print("%8s " % "t" + " ".join("%12s" % a for a in ARMS))
        for t in times:
            cells = []
            for a in ARMS:
                v = rec["probes"][a].get(t, {}).get(key)
                cells.append("%12s" % ("-" if v is None else ("%12.4f" % v if isinstance(v, float) else v)))
            print("%8d " % (T0 + t) + " ".join(cells))


def main():
    smoke = "--smoke" in sys.argv
    seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 1
    tl = SMOKE if smoke else FULL
    if smoke:
        k03.WARMUP_TICKS = 4000
    k03._drain_telemetry = _tracked_drain
    eng, _ = k03.warm_engine(seed)
    net = eng.net
    hpc, ctx = encode.hpc_e_ids(net), encode.ctx_e_ids(net)
    groups = {"hpc": hpc, "ctx": ctx}
    TRACK["ctx_mask"] = np.zeros(net.n, bool)
    TRACK["ctx_mask"][ctx] = True
    TRACK["hpc_mask"] = np.zeros(net.n, bool)
    TRACK["hpc_mask"][hpc] = True

    # ---- per-condition engines: own parameter object, override at the warmed tick, common idle ---------- #
    cond = make_conditions(eng.p)
    plain = copy.deepcopy(eng) if smoke else None
    bases, max_frac = {}, {}
    for cid, over in cond.items():
        e = copy.deepcopy(eng)
        e.p = types.SimpleNamespace(**{k: v for k, v in vars(eng.p).items() if k.isupper()})
        for k, v in over.items():
            setattr(e.p, k, v)
        assert e.p is not eng.p
        for k, v in over.items():
            assert getattr(e.p, k) == v and getattr(eng.p, k) != v, (cid, k)
            assert getattr(copy.deepcopy(e).p, k) == v, (cid, k, "deepcopy lost the override")
        TRACK["ids"].add(id(e))
        TRACK["ctx"] = TRACK["hpc"] = 0.0
        k11._step_chunked_counting(e, BASE_TICKS)
        TRACK["ids"].discard(id(e))
        max_frac[cid] = {"ctx": TRACK["ctx"], "hpc": TRACK["hpc"]}
        if over.get("STRUCT_BASE") == 0.0:
            assert e.g_struct == 0.0, (cid, "structural gain not zero after a sweep")
        bases[cid] = e
    T0 = int(bases["C0"].t)
    print(f"seed {seed} T0={T0}" + ("  [SMOKE]" if smoke else ""))
    print("overrides:", {c: o for c, o in cond.items()})

    if smoke:   # C0 stays bit-identical to the default plant
        k11._step_chunked_counting(plain, BASE_TICKS)
        c0 = bases["C0"]
        same = (np.array_equal(c0.net.w, plain.net.w) and np.array_equal(c0.net.alive, plain.net.alive)
                and np.array_equal(c0.spike_counts(), plain.spike_counts()))
        assert same, "C0 differs from the untouched default plant"
        print("C0 bit-identical to the untouched default plant after", BASE_TICKS, "ticks: OK")
        del plain
    del eng

    # P: top 100 ctx E in a 50-tick full-A probe at T0 on the C0 engine, the same cell set in every condition
    p0 = copy.deepcopy(bases["C0"])
    p0.hetero_write = False
    p0.present(PATTERN_A, READOUT_TICKS)
    c = k11._step_chunked_counting(p0, READOUT_TICKS)
    P = ctx[np.argsort(-c[ctx], kind="stable")[:N_P]]
    del p0
    print(f"P (first 10 of {len(P)})={P[:10].tolist()}")

    ref = None
    if not smoke and os.path.exists(D_REF % seed):
        ref = json.load(open(D_REF % seed))

    recs, summ = {}, {}
    for cid in cond:
        TRACK["ctx"] = TRACK["hpc"] = 0.0
        rec = run_condition(cid, bases.pop(cid), tl, P, groups, ref, smoke)
        # rates, per-sweep series, tick fractions after 120,000 (idle phase tracked above, arms below)
        rec["max_frac"] = {k: max(max_frac[cid][k], TRACK[k]) for k in ("ctx", "hpc")}
        recs[cid] = rec
        summ[cid] = clauses(rec, tl)
        print_tables(rec, tl["probes"] + (tl["end2"],), T0, cid)
        print(f"\n[{cid}] idle Hz:", {a: {t: {k: round(v, 3) for k, v in h.items()} for t, h in d.items()}
                                      for a, d in rec["idle"].items()})
        print(f"[{cid}] on-arm per-sweep (t, hpc E Hz, ctx E Hz):", [(t, round(h, 2), round(x, 2)) for t, h, x in rec["series"]])
        print(f"[{cid}] W={rec['W']} triggered {rec['n_trig_W']}/{len(rec['W'])}, marks {rec['n_marks']}, contrast at A {rec['con_A']}")

    valid = None
    if smoke:
        print("\nVALIDITY: skipped in smoke (8.18 values are for the full timeline)")
    elif ref is None:
        print(f"\nVALIDITY seed {seed}: INVALID (no 8.18 reference at {D_REF % seed})")
        valid = False
    else:
        v = recs["C0"]["validity"]
        valid = bool(len(v) == 4 and all(x["ok"] for x in v.values()))
        print(f"\nVALIDITY seed {seed}: " + ("VALID" if valid else "INVALID"), v)

    print(f"\n=== decision-rule clauses, seed {seed} ===")
    for cid, s in summ.items():
        print(f"{cid}: eligible={s['eligible']}")
        print(f"   rates in band at both windows (on arm): {s['rates_in_band']}  184k {s['rates_184']}  300k {s['rates_300']}"
              f"  (all arms at 184k: {s['rates_in_band_all_arms_184']})")
        print(f"   max tick fraction <= {MAX_FRAC}: {s['frac_ok']}  ctx E {s['max_frac_ctx']:.3f}  hpc E {s['max_frac_hpc']:.3f}")
        print(f"   P off/neveroff 125-127k mean >= {RATIO_MEAN_MIN}: {s['P_ratio_mean_ok']}  {s['P_ratio_mean']:.3f}  each {[round(x, 3) for x in s['P_ratio_each']]}")
        print(f"   P off/neveroff at 184k >= {RATIO_END_MIN}: {s['P_ratio_end_ok']}  {s['P_ratio_end']:.3f}")
        print(f"   survivors-only contrast at 184k (on): {s['surv_184']:.4f}")

    if "--json" in sys.argv:
        with open(sys.argv[sys.argv.index("--json") + 1], "w") as f:
            json.dump(dict(smoke=smoke, seed=seed, T0=T0, P=P.tolist(), valid=valid, times=list(tl["probes"]) + [tl["end2"]],
                           overrides=cond, clauses=summ, conditions=recs), f, indent=1,
                      default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(f"EXIT {'SMOKE' if smoke else ('VALID' if valid else 'INVALID')}")


if __name__ == "__main__":
    main()
