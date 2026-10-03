"""SPEC 8.17 kill test T5: inhibition as the hpc E rate controller, with the heterosynaptic write.
Run: PYTHONPATH=<worktree> python tests/k817_inh_homeostat.py [--seed N] [--json out.json] [--smoke]
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
from k815_selective_write import contrast, hz, retention
from k816_hetero_write import (A_TICKS, B_TICKS, BASE_TICKS, K_W, PATTERN_A, PATTERN_B, READOUT_TICKS,
                               abort, build_marks, readout, step1000)
from brainsim import encode, params

CTX_E_HZ, HPC_E_HZ = (3.0, 5.0), (0.5, 1.5)
C1_MIN, C2_MIN, C2_KEEP, C3_GAP = 12, 0.20, 0.5, 4
MAX_HPC_FRAC, MAX_AT_BOUND = 0.20, 0.20
V1_REF = dict(c2=0.309, c3=1.221, readout=(10, 3, 0))
CONDITIONS = ("full_A", "half_cue", "none")

# offsets from T0 = 122,000 (full) / the post-baseline tick (smoke); "end" is 184,000, "end2" is 300,000
FULL = {"snaps": (2000, 3000, 8000, 18000, 38000, 42000, 62000), "B_at": 40000, "end": 62000,
        "end2": 178000, "phases": ((28000, "sleep"), (39000, "wake")),
        "phases2": ((108000, "sleep"), (119000, "wake"))}
SMOKE = {"snaps": (2000, 3000, 4000, 5000, 6000, 7000, 8000), "B_at": 5000, "end": 8000,
         "end2": 12000, "phases": (), "phases2": ()}

# per-tick hpc E spike fraction: read from the engine's spike buffer just before each drain
TRACK = {"eng": None, "max": 0.0}
_drain = k03._drain_telemetry


def _tracked_drain(eng):
    if eng is TRACK["eng"]:
        for s in eng._buf_spikes:
            TRACK["max"] = max(TRACK["max"], np.count_nonzero(eng._hpc_e[s]) / np.count_nonzero(eng._hpc_e))
    _drain(eng)


def delivered_exc_onto(eng, cells, ticks):
    """Summed weight of the excitatory synapses delivered onto `cells` over the next `ticks`; steps eng."""
    net, p = eng.net, eng.p
    onto = np.zeros(net.n, bool)
    onto[np.asarray(cells, np.int64)] = True
    total = 0.0
    for _ in range(ticks):
        bucket = eng.ring[eng.t % (p.D_MAX + 1)]
        if bucket:
            d = np.concatenate(bucket)
            d = d[net.alive[d] & net.is_exc[net.pre[d]] & onto[net.post[d]]]
            total += float(net.w[d].astype(np.float64).sum())
        eng.step(1)
    return total


def verdict(rec):
    """(passed, failed clause names in order V1 V2 V3 c1 c2 c3) for one seed's record."""
    failed = []
    if rec["seed"] == 1 and not (round(rec["ref_c2"], 3) == V1_REF["c2"] and round(rec["ref_c3"], 3) == V1_REF["c3"]
                                 and tuple(rec["ref_readout"]) == V1_REF["readout"]):
        failed.append("V1")
    in_band = all(HPC_E_HZ[0] <= h["hpc_E"] <= HPC_E_HZ[1] and CTX_E_HZ[0] <= h["ctx_E"] <= CTX_E_HZ[1]
                  for h in (rec["hz_184"], rec["hz_300"]))
    if not (in_band and rec["max_hpc_frac_tick"] <= MAX_HPC_FRAC):
        failed.append("V2")
    if any(v["frac_at_zero"] + v["frac_at_max"] > MAX_AT_BOUND + 1e-9 for v in (rec["inh_184"], rec["inh_300"])):
        failed.append("V3")
    if not (rec["n_trig_W"] >= C1_MIN and rec["c2_written"] >= C2_MIN):
        failed.append("c1")
    if not rec["surv_184"] >= C2_KEEP * rec["surv_124"]:
        failed.append("c2")
    a = rec["full_A"]
    if not (a["on"] >= a["never"] + C3_GAP and a["on"] >= a["off"] + C3_GAP):
        failed.append("c3")
    return not failed, failed


def _condition(e, name, A_ids):
    e.hetero_write = False
    if name == "full_A":
        e.present(PATTERN_A, READOUT_TICKS)
    elif name == "half_cue":
        e.inject(encode.cue_ids(A_ids), params.PATTERN_AMP_MV, READOUT_TICKS)


def delivered_by_condition(eng, W, A_ids):
    out = {}
    for name in CONDITIONS:
        e = copy.deepcopy(eng)
        _condition(e, name, A_ids)
        out[name] = delivered_exc_onto(e, W, READOUT_TICKS)
    return out


def inh_state(net):
    return types.SimpleNamespace(alive=net.alive.copy(), pre=net.pre.copy(), post=net.post.copy(),
                                 w=net.w.copy(), is_exc=net.is_exc, w_max_n=net.w_max_n)


def inh_onto(st, W, hpc):
    """Inhibitory mean magnitude (fraction of m_max) and in-degree onto W and onto the other hpc E cells."""
    s = np.flatnonzero(st.alive)
    s = s[~st.is_exc[st.pre[s]]]
    frac = -st.w[s] / (st.w_max_n[st.post[s]] * params.I_GAIN)
    out = {}
    for name, ids in (("W", W), ("rest", np.setdiff1d(hpc, W))):
        sel = np.isin(st.post[s], ids)
        out[name] = {"mean_frac": float(frac[sel].mean()), "in_degree": float(sel.sum() / len(ids))}
    return out


def a_epoch_log(e, a_log):
    h = e.hetero_last
    if h is not None and h["t"] == e.t:
        a_log["cells"] |= set(h["cells"].tolist())
        for pre, post, born, dw, wm in zip(h["pre"].tolist(), h["post"].tolist(), h["born"].tolist(),
                                           h["dw"].tolist(), h["w_max"].tolist()):
            a_log["writes"][(pre, post, born)] = a_log["writes"].get((pre, post, born), 0.0) + dw / wm


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
    lineage = {"ref": eng, "inh": copy.deepcopy(eng)}
    lineage["inh"].inh_homeostat = True
    TRACK["eng"] = lineage["inh"]
    baseline = {}
    for name, e in lineage.items():
        c = k11._step_chunked_counting(e, BASE_TICKS)
        baseline[name] = {"hpc_E": hz(c, hpc, BASE_TICKS), "ctx_E": hz(c, ctx, BASE_TICKS)}
    T0 = int(eng.t)
    print(f"seed {seed} T0={T0} baseline idle Hz {baseline}" + ("  [SMOKE]" if smoke else ""))
    if smoke:
        print("smoke: warm-up 4,000, timeline compressed, phase assertions skipped")

    ARMS = ("on", "off", "never", "ref", "refoff")   # refoff: the default plant's write-off twin, for the V1 values
    spec = {"on": ("inh", True, True), "off": ("inh", False, True), "never": ("inh", True, False),
            "ref": ("ref", True, True), "refoff": ("ref", False, True)}
    engs, logs = {}, {}
    for arm, (lin, flag, _) in spec.items():
        engs[arm] = copy.deepcopy(lineage[lin])
        engs[arm].hetero_write = flag
        logs[arm] = {"sweeps": [], "B": []}
    del eng, lineage
    TRACK["eng"] = engs["on"]
    states = {0: inh_state(engs["on"].net)}
    series = []   # on arm: hpc E Hz per 1000-tick sweep

    # ---- A epoch --------------------------------------------------------- #
    a_log = {a: {"writes": {}, "cells": set(), "counts": None} for a in ("on", "ref")}
    for arm in ARMS:
        if spec[arm][2]:
            engs[arm].present(PATTERN_A, A_TICKS)
    for arm in ARMS:
        e = engs[arm]
        tot = np.zeros(net.n, np.int64)
        for _ in range(A_TICKS // 1000):
            c = step1000(e, logs[arm], False)
            tot += c
            if arm == "on":
                series.append((int(e.t), hz(c, hpc, 1000)))
            if arm in a_log:
                a_epoch_log(e, a_log[arm])
        if arm in a_log:
            a_log[arm]["counts"] = tot
    W, marks, marks_set, n_trig = {}, {}, {}, {}
    for arm in a_log:
        W[arm] = encode.select_winners(a_log[arm]["counts"], hpc, K_W)
        marks[arm] = build_marks(a_log[arm]["writes"], W[arm])
        marks_set[arm] = {m[:3] for m in marks[arm]}
        n_trig[arm] = len(set(W[arm].tolist()) & a_log[arm]["cells"])
        print(f"{arm}: W={W[arm].tolist()} W cells triggered {n_trig[arm]}/{len(W[arm])}; marks {len(marks[arm])} "
              f"(U {sum(m[3] for m in marks[arm])}, D {sum(not m[3] for m in marks[arm])})")
    A_ids = np.asarray(engs["on"].patterns[PATTERN_A], np.int64)
    lin_of = {"on": "on", "off": "on", "never": "on", "ref": "ref", "refoff": "ref"}

    # ---- untouched epoch ------------------------------------------------- #
    snaps = {a: {} for a in ("on", "off", "ref", "refoff")}
    rate_counts = {a: [] for a in ARMS}
    phases = dict(tl["phases"])
    for arm in ARMS:
        e, L = engs[arm], lin_of[arm]
        if arm in snaps:
            snaps[arm][A_TICKS] = k11._snapshot(e.net)
        if arm == "on":
            states[A_TICKS] = inh_state(e.net)
        off = A_TICKS
        while off < tl["end"]:
            if off == tl["B_at"]:
                e.present(PATTERN_B, B_TICKS)
            c = step1000(e, logs[arm], arm in a_log, marks_set[L], W[L], (T0 + tl["B_at"], T0 + tl["B_at"] + B_TICKS))
            off += 1000
            rate_counts[arm].append(c)
            if arm == "on":
                series.append((int(e.t), hz(c, hpc, 1000)))
            if arm in snaps and off in tl["snaps"]:
                snaps[arm][off] = k11._snapshot(e.net)
            if off in phases and e.phase != phases[off]:
                abort(e, phases[off])
        print(f"arm {arm} done, t={e.t}")
    states[tl["end"]] = inh_state(engs["on"].net)

    # ---- metrics at 184,000 ---------------------------------------------- #
    end = tl["end"]
    con = {a: {t: contrast(snaps[a][t], marks[lin_of[a]]) for t in tl["snaps"]} for a in snaps}

    def r_c(o, f, t):
        return retention(con[o][t]["C"], con[f][t]["C"], con[o][A_TICKS]["C"], con[f][A_TICKS]["C"])
    ret = {"on": {t: r_c("on", "off", t) for t in tl["snaps"]}, "ref": {t: r_c("ref", "refoff", t) for t in tl["snaps"]}}
    rates = {}
    for arm in ARMS:
        idle = sum(rate_counts[arm][-2:])
        rates[arm] = {"hpc_E": hz(idle, hpc, 2000), "ctx_E": hz(idle, ctx, 2000)}
    written = con["on"][A_TICKS]["C"] - con["off"][A_TICKS]["C"]
    inh_184 = engs["on"].inh_view()
    ro, delivered = {}, {}
    for arm in ("on", "off", "never", "ref"):
        Wa = W["ref" if arm == "ref" else "on"]
        ro[arm] = readout(engs[arm], Wa, A_ids)
        delivered[arm] = delivered_by_condition(engs[arm], Wa, A_ids)
    cols = ("C", "C_survivors", "M", "U_mean", "D_mean", "dead_U", "dead_D")
    print("\n%-6s %7s " % ("arm", "t") + " ".join("%11s" % c for c in cols))
    for arm in snaps:
        for t in tl["snaps"]:
            print("%-6s %7d " % (arm, T0 + t) + " ".join("%11.4f" % con[arm][t][k] for k in cols))
    print("\nR_C vs the write-off twin (denominator: 124,000 values), on / ref")
    for t in tl["snaps"]:
        print("%7d  on %8.3f  ref %8.3f" % (T0 + t, ret["on"][t], ret["ref"][t]))
    print("\nidle Hz 182,000 to 184,000:", {a: {k: round(v, 3) for k, v in r.items()} for a, r in rates.items()})
    print("inh_view at 184,000:", inh_184)
    print("readout at 184,000 (W cells spiking in 50 ticks) and excitatory weight delivered onto W:")
    for a in ro:
        print(f"  {a:6s}", {k: v["W_spiking"] for k, v in ro[a].items()}, {k: round(v, 2) for k, v in delivered[a].items()})

    # ---- the on arm alone, untouched, to 300,000 -------------------------- #
    e, off = engs["on"], end
    phases2 = dict(tl["phases2"])
    cnts = []
    while off < tl["end2"]:
        c = step1000(e, logs["on"], True, marks_set["on"], W["on"], (0, 0))
        off += 1000
        cnts.append(c)
        series.append((int(e.t), hz(c, hpc, 1000)))
        if off in phases2 and e.phase != phases2[off]:
            abort(e, phases2[off])
    snap_300 = k11._snapshot(e.net)
    con_300 = contrast(snap_300, marks["on"])
    idle = sum(cnts[-2:])
    hz_300 = {"hpc_E": hz(idle, hpc, 2000), "ctx_E": hz(idle, ctx, 2000)}
    inh_300 = e.inh_view()
    states[tl["end2"]] = inh_state(e.net)
    print(f"\non arm at t={e.t}: idle Hz {hz_300}, inh_view {inh_300}, C {con_300['C']:.4f}, "
          f"C_survivors {con_300['C_survivors']:.4f}")

    rec = dict(seed=seed, ref_c2=con["ref"][A_TICKS]["C"] - con["refoff"][A_TICKS]["C"], ref_c3=ret["ref"][end],
               ref_readout=tuple(ro["ref"][k]["W_spiking"] for k in CONDITIONS),
               hz_184=rates["on"], hz_300=hz_300, max_hpc_frac_tick=TRACK["max"], inh_184=inh_184, inh_300=inh_300,
               n_trig_W=n_trig["on"], c2_written=written, surv_124=con["on"][A_TICKS]["C_survivors"],
               surv_184=con["on"][end]["C_survivors"], full_A={a: ro[a]["full_A"]["W_spiking"] for a in ("on", "off", "never")})
    ok, failed = verdict(rec)
    inh_groups = {T0 + t: inh_onto(st, W["on"], hpc) for t, st in states.items()}
    info = dict(baseline=baseline, W=W["on"].tolist(), W_ref=W["ref"].tolist(), n_marks={a: len(m) for a, m in marks.items()},
                half_cue={a: ro[a]["half_cue"]["W_spiking"] for a in ro}, none={a: ro[a]["none"]["W_spiking"] for a in ro},
                readout=ro, delivered_exc_onto_W=delivered, inh_onto_groups=inh_groups, hpc_E_hz_per_sweep=series,
                contrast=con, contrast_300=con_300, retention=ret, rates=rates, sweeps={a: logs[a]["sweeps"] for a in ARMS},
                B_sweeps=logs["on"]["B"], alive={a: int(engs[a].net.alive.sum()) for a in ARMS})
    print(f"\nreported without a bar: half cue {info['half_cue']}, none {info['none']}")
    print("inhibitory mean fraction / in-degree onto W and the rest of hpc E:")
    for t, g in inh_groups.items():
        print(f"  {t}: " + ", ".join(f"{k} {v['mean_frac']:.3f} / {v['in_degree']:.1f}" for k, v in g.items()))
    print("on-arm hpc E Hz per sweep:", [(t, round(h, 2)) for t, h in series])
    print(f"max fraction of hpc E spiking in one tick (on arm, from {T0 - BASE_TICKS}): {TRACK['max']:.3f}")
    verdict_word = "PASS" if ok else "REJECTED"
    print("\nT5 record:", {k: v for k, v in rec.items()})
    for clause in failed:
        print(f"  FAILED {clause} (seed {seed})")
    if "--json" in sys.argv:
        with open(sys.argv[sys.argv.index("--json") + 1], "w") as f:
            json.dump(dict(smoke=smoke, T0=T0, record=rec, failed=failed, verdict=verdict_word, **info), f, indent=1,
                      default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(f"EXIT {verdict_word}")


if __name__ == "__main__":
    main()
