"""SPEC 8.48: persistence and a second pattern on the 8.46 setting (excitatory binding). No engine change.
Run: BRAINSIM_PLANT=gen2 PYTHONPATH=<worktree> python tests/k848_persist_dual.py [--seed N] [--reps 96] [--ref 8.46.json] [--json out.json]
"""
import copy
import json
import os
import sys
import time

import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import k03_pairing as k03
import k11_binding as k11
import k821_helpers as h
import k831_k11_official as k831
import k837_ei_frozen as k837
import k838_headroom as k838
from k816_hetero_write import K_W
from brainsim import encode, params

K, ETA, WIN = 1.25, 0.30, k11.WINDOW_TICKS
T_A_END, T_1S, T_10S, T_SLEEP, T_WAKE, T_37S, T_DUAL = 124_000, 125_000, 134_000, 140_000, 160_000, 161_000, 128_000


def advance(e, ticks, groups):
    """Step `ticks`; over the last 1000: rate (Hz) and the largest one-tick share of each group."""
    assert ticks >= 1000
    k11._step_chunked_counting(e, ticks - 1000)
    before = e.spike_counts().astype(np.int64)
    e.step(1000)
    mx = {g: max(float(m[s].sum()) for s in e._buf_spikes) / ids.size for g, (ids, m) in groups.items()}
    k03._drain_telemetry(e)
    c = e.spike_counts().astype(np.int64) - before
    return {g: (float(c[ids].sum()) / ids.size, mx[g]) for g, (ids, m) in groups.items()}


def probe(eng, stim, rep):
    e = copy.deepcopy(eng)
    e.rng = np.random.default_rng(10_000 + rep)
    if stim is not None:
        stim(e)
    first = np.full(e.net.n, -1, np.int64)
    for k in range(WIN):
        e.step(1)
        s = e._buf_spikes[-1]
        first[s[first[s] < 0]] = k
        k03._drain_telemetry(e)
    return first


def probes(eng, stims, sets, reps):
    return {a: [{n: int(np.count_nonzero(f[ids] >= 0)) for n, ids in sets.items()}
                for f in (probe(eng, fn, r) for r in range(reps))] for a, fn in stims.items()}


def diff(pT, pN, arm, key):
    d = np.array([t[key] - n[key] for t, n in zip(pT[arm], pN[arm])], float)
    return float(d.mean()), float(d.std(ddof=1) / np.sqrt(d.size))


def mean(p, arm, key):
    return float(np.mean([r[key] for r in p[arm]]))


def share(e, pre_ids, post_ids):
    n = e.net
    m = n.alive & k11._mask(pre_ids, n.n)[n.pre] & k11._mask(post_ids, n.n)[n.post]
    return float((n.w[m] / n.w_max_n[n.post[m]]).mean()) if m.any() else float("nan")


def checks(G, other, none, run, twin_none, G_min=None):
    ok = G >= 2.0 and other <= 0.5 * G and none <= 0.5 and not run and twin_none <= 3.0
    return bool(ok and (G_min is None or G >= G_min))


def main():
    arg = lambda k, d=None: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
    seed, jpath, reps, ref = int(arg("--seed", 1)), arg("--json"), int(arg("--reps", 96)), arg("--ref")
    assert params.ACTIVE_PROFILE == "gen2", "k848 needs BRAINSIM_PLANT=gen2 in the environment"
    t_start = time.time()
    k838.raise_bound(K)
    stash = []
    _, warm = k831.configured_warm(stash)
    warm(seed)
    b = stash[0]
    h.own_params(b, {"HETERO_ETA": ETA})
    b.hetero_additive, b.hetero_recurrent = False, True
    inh = ~b.net.is_exc
    b.net.a_plus_n[inh] = 0.0
    b.net.a_minus_n[inh] = 0.0
    flags = lambda e: bool(e.hetero_write and not e.hetero_additive and e.hetero_recurrent and e.pending_stdp and e.pending_express
                           and e.p.HETERO_ETA == ETA and e.p.STRUCT_BASE == 0.0
                           and not e.net.a_plus_n[~e.net.is_exc].any() and not e.net.a_minus_n[~e.net.is_exc].any())
    assert flags(b) and b.t == 120_000 and b.phase == "wake"
    hpc_e, ctx_e = encode.hpc_e_ids(b.net), encode.ctx_e_ids(b.net)
    groups = {"hpc_e": (hpc_e, k11._mask(hpc_e, b.net.n)), "ctx_e": (ctx_e, k11._mask(ctx_e, b.net.n))}
    A_ids = np.sort(np.asarray(b.patterns[k11.PATTERN_A], np.int64))
    B_ids = np.sort(np.asarray(b.patterns[k11.PATTERN_B], np.int64))
    cueA, cueB = k11.cue_ids(A_ids), k11.cue_ids(B_ids)
    rest = k837.rest(b, {"ctx_e": ctx_e, "hpc_e": hpc_e})
    health = bool(1.5 <= rest["ctx_e"][0] <= 2.5 and 0.75 <= rest["hpc_e"][0] <= 1.25 and max(rest["ctx_e"][1], rest["hpc_e"][1]) <= 0.20)
    print(f"seed {seed} reps {reps}; rest ctx E {rest['ctx_e'][0]:.2f} Hz, hpc E {rest['hpc_e'][0]:.2f} Hz; in band {health}")

    def to_1s(present):
        e = copy.deepcopy(b)
        base = k11._step_chunked_counting(e, k11.BASE_TICKS)
        cnt = k11._present_recording_volley(e, k11.PATTERN_A, k11.A_TICKS, A_ids)[0] if present else k11._step_chunked_counting(e, k11.A_TICKS)
        assert e.t == T_A_END
        return e, base, cnt, advance(e, k11.DELAY_TICKS, groups)

    T, base_T, a_T, rT = to_1s(True)
    N, _, _, rN = to_1s(False)
    WA = encode.select_winners(a_T, hpc_e, K_W)
    asm = k11.assembly_from_counts(base_T, a_T, hpc_e, k11.A_TICKS)
    ctxA = k11.assembly_from_counts(base_T, a_T, ctx_e, k11.A_TICKS)
    res = {"seed": seed, "reps": reps, "rest": rest, "health": health, "assembly": int(asm.size), "WA": WA.tolist(), "part1": {}, "valid": {}}

    # ---- Part 1: persistence ----
    stims1 = {"half": lambda e: e.inject(cueA, params.PATTERN_AMP_MV, WIN), "B": lambda e: e.present(k11.PATTERN_B, WIN), "none": None}
    sets1 = {"W": WA}
    phases = {}

    def later(e0, ticks, keep_awake):
        e = copy.deepcopy(e0)
        if keep_awake:
            k11._step_chunked_counting(e, 139_000 - e.t)
            e.set_sleep(False)
            ticks -= 139_000 - e0.t
        if not keep_awake and e.t < T_SLEEP < e.t + ticks:
            k11._step_chunked_counting(e, 150_000 - e.t)
            mid = e.phase
            ticks -= 150_000 - e0.t
        elif keep_awake:
            k11._step_chunked_counting(e, 150_000 - e.t)
            mid = e.phase
            ticks -= 150_000 - 139_000
        else:
            mid = e.phase
        r = advance(e, ticks, groups)
        return e, r, mid

    T10, rT10, _ = later(T, T_10S - T_1S, False)
    N10, rN10, _ = later(N, T_10S - T_1S, False)
    TS, rTS, midTS = later(T10, T_37S - T_10S, False)
    NS, rNS, midNS = later(N10, T_37S - T_10S, False)
    TW, rTW, midTW = later(T10, T_37S - T_10S, True)
    NW, rNW, midNW = later(N10, T_37S - T_10S, True)
    assert T10.t == N10.t == T_10S and TS.t == NS.t == TW.t == NW.t == T_37S
    phases = {"sleep_mid": (midTS, midNS), "awake_mid": (midTW, midNW), "end": (TS.phase, NS.phase, TW.phase, NW.phase)}
    sched_ok = bool(midTS == midNS == "sleep" and midTW == midNW == "wake" and all(p == "wake" for p in phases["end"])
                    and T10.phase == "wake")
    pts = {"1s": (T, N, rT, rN), "10s": (T10, N10, rT10, rN10), "37s_sleep": (TS, NS, rTS, rNS), "37s_awake": (TW, NW, rTW, rNW)}
    G1 = None
    print(f"assembly {asm.size}; schedule as declared {sched_ok} {phases}")
    print(f"\nPart 1. W(A) of 16 at 50 ticks, trained | twin, difference +/- paired SE (n={reps})")
    print(f"  {'point':<10}{'half':>24}{'B':>24}{'none':>24}{'>=13':>6}{'none>=6':>8}{'hpcE Hz':>9}{'1-tick':>7}{'WW':>12}{'ctxA>W':>12}  verdict")
    for name, (eT, eN, rt, rn) in pts.items():
        assert flags(eT) and flags(eN)
        pT, pN = probes(eT, stims1, sets1, reps), probes(eN, stims1, sets1, reps)
        d = {a: diff(pT, pN, a, "W") for a in stims1}
        if name == "1s":
            G1 = d["half"][0]
        run = bool(rt["hpc_e"][0] > 1.4 or max(rt["hpc_e"][1], rt["ctx_e"][1]) > 0.20)
        tw0 = mean(pN, "none", "W")
        ok = checks(d["half"][0], d["B"][0], d["none"][0], run, tw0, None if name == "1s" else 0.5 * G1)
        n13 = sum(r["W"] >= 13 for r in pT["half"])
        c6 = (sum(r["W"] >= 6 for r in pT["none"]), sum(r["W"] >= 6 for r in pN["none"]))
        ww, ca = (share(eT, WA, WA), share(eN, WA, WA)), (share(eT, ctxA, WA), share(eN, ctxA, WA))
        res["part1"][name] = {"T": pT, "N": pN, "diff": d, "rate_T": rt, "rate_N": rn, "runaway": run, "twin_none": tw0, "ok": ok,
                              "n13": n13, "none_ge6": c6, "WW": ww, "ctxA_W": ca}
        cell = lambda a: f"{mean(pT, a, 'W'):5.2f}|{mean(pN, a, 'W'):5.2f} {d[a][0]:+5.2f}+/-{d[a][1]:.2f}"
        print(f"  {name:<10}{cell('half'):>24}{cell('B'):>24}{cell('none'):>24}{n13:>6}{c6[0]:>5}|{c6[1]:<2}{rt['hpc_e'][0]:>9.2f}{max(rt['hpc_e'][1], rt['ctx_e'][1]):>7.3f}"
              f"{ww[0]:>7.2f}|{ww[1]:.2f}{ca[0]:>7.2f}|{ca[1]:.2f}  {'met' if ok else 'NOT met'}" + (" RUNAWAY" if run else ""))
    if ref:
        r46 = json.load(open(ref))["res"]["probes"]
        same = all([x["W"] for x in res["part1"]["1s"][who][a]] == [x["W"] for x in r46[who][a]][:reps]
                   for who in ("T", "N") for a in ("half", "B", "none"))
        res["valid"]["reproduces_8_46"] = bool(same)
        print(f"  1 s point reproduces 8.46's repeats exactly: {same}")
    res["valid"]["schedule"] = sched_ok
    res["phases"] = phases

    # ---- Part 2: A then B ----
    def second(e0, present):
        e = copy.deepcopy(e0)
        cnt = k11._present_recording_volley(e, k11.PATTERN_B, k11.A_TICKS, B_ids)[0] if present else k11._step_chunked_counting(e, k11.A_TICKS)
        r = advance(e, k11.DELAY_TICKS, groups)
        assert e.t == T_DUAL and e.phase == "wake" and flags(e)
        return e, cnt, r

    AB, b_AB, rAB = second(T, True)
    Ao, _, rAo = second(T, False)
    Bo, b_Bo, rBo = second(N, True)
    NN, _, rNN = second(N, False)
    WB = encode.select_winners(b_AB, hpc_e, K_W)
    WB_alone = encode.select_winners(b_Bo, hpc_e, K_W)
    sets2 = {"WA": WA, "WB": WB, "WBo": WB_alone}
    stims2 = {"halfA": lambda e: e.inject(cueA, params.PATTERN_AMP_MV, WIN), "halfB": lambda e: e.inject(cueB, params.PATTERN_AMP_MV, WIN),
              "fullA": lambda e: e.present(k11.PATTERN_A, WIN), "fullB": lambda e: e.present(k11.PATTERN_B, WIN), "none": None}
    P = {n: probes(e, stims2, sets2, reps) for n, e in (("AB", AB), ("Ao", Ao), ("Bo", Bo), ("NN", NN))}
    run2 = bool(rAB["hpc_e"][0] > 1.4 or max(rAB["hpc_e"][1], rAB["ctx_e"][1]) > 0.20)
    D = lambda who, arm, key: diff(P[who], P["NN"], arm, key)
    gA, oA, nA = D("AB", "halfA", "WA"), D("AB", "fullB", "WA"), D("AB", "none", "WA")
    gB, oB, nB = D("AB", "halfB", "WB"), D("AB", "fullA", "WB"), D("AB", "none", "WB")
    gA_alone, gB_alone = D("Ao", "halfA", "WA"), D("Bo", "halfB", "WBo")
    okA = checks(gA[0], oA[0], nA[0], run2, mean(P["NN"], "none", "WA"), 0.5 * gA_alone[0])
    okB = checks(gB[0], oB[0], nB[0], run2, mean(P["NN"], "none", "WB"))
    f = lambda x: f"{x[0]:+.2f}+/-{x[1]:.2f}"
    n13 = lambda who, arm, key: sum(r[key] >= 13 for r in P[who][arm])
    print(f"\nPart 2 at {T_DUAL}. W(A) and W(B) share {np.intersect1d(WA, WB).size} cells; W(B) here vs in the B-only brain share {np.intersect1d(WB, WB_alone).size}")
    print(f"  rates over the last second, hpc E Hz (largest one-tick share): A then B {rAB['hpc_e'][0]:.2f} ({max(rAB['hpc_e'][1], rAB['ctx_e'][1]):.3f}), "
          f"A only {rAo['hpc_e'][0]:.2f}, B only {rBo['hpc_e'][0]:.2f}, twin {rNN['hpc_e'][0]:.2f}; runaway {run2}")
    print(f"  means of 16 at 50 ticks (A then B | A only | B only | twin)")
    for key in ("WA", "WB"):
        for arm in stims2:
            print(f"    {key} {arm:<6}" + " | ".join(f"{mean(P[w], arm, key):5.2f}" for w in ("AB", "Ao", "Bo", "NN")))
    print(f"  A in the A-then-B brain: G {f(gA)} (A-only brain {f(gA_alone)}; needs half of it), full B {f(oA)}, none {f(nA)}; "
          f">=13 on {n13('AB', 'halfA', 'WA')}/{reps}; none >=6 on {sum(r['WA'] >= 6 for r in P['AB']['none'])}: {'met' if okA else 'NOT met'}")
    print(f"  B in the A-then-B brain: G {f(gB)} (B-only brain, its own W, {f(gB_alone)}), full A {f(oB)}, none {f(nB)}; "
          f">=13 on {n13('AB', 'halfB', 'WB')}/{reps}; none >=6 on {sum(r['WB'] >= 6 for r in P['AB']['none'])}: {'met' if okB else 'NOT met'}")
    ww = {n: (share(e, WA, WA), share(e, WB, WB), share(e, WA, WB), share(e, WB, WA)) for n, e in (("AB", AB), ("Ao", Ao), ("Bo", Bo), ("NN", NN))}
    print("  W-to-W share of bound (A>A, B>B, A>B, B>A): " + "; ".join(f"{n} " + "/".join(f"{x:.2f}" for x in v) for n, v in ww.items()))
    res["part2"] = {"P": P, "WB": WB.tolist(), "WB_alone": WB_alone.tolist(), "overlap": int(np.intersect1d(WA, WB).size),
                    "rates": {"AB": rAB, "Ao": rAo, "Bo": rBo, "NN": rNN}, "runaway": run2, "gA": gA, "oA": oA, "nA": nA, "gB": gB, "oB": oB,
                    "nB": nB, "gA_alone": gA_alone, "gB_alone": gB_alone, "okA": okA, "okB": okB, "WW": ww,
                    "twin_none": (mean(P["NN"], "none", "WA"), mean(P["NN"], "none", "WB"))}
    res["runtime_s"] = time.time() - t_start
    print(f"runtime {res['runtime_s']:.0f}s")
    if jpath:
        os.makedirs(os.path.dirname(os.path.abspath(jpath)), exist_ok=True)
        with open(jpath, "w") as fh:
            json.dump(res, fh, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))


if __name__ == "__main__":
    main()
