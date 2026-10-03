"""SPEC 8.28: plateau override, a labelled test-side PROXY, measured as trained minus never-trained on gen2.
Run: BRAINSIM_PLANT=gen2 PYTHONPATH=<worktree> python tests/k828_override.py --seed N --arm {PH,PO,POC} [--smoke] [--json out.json]
Arms: PH (no override, reference), PO (hpc E cells exempt), POC (hpc E and ctx E cells exempt). Pair rule, hetero_write on both engines.
Each 1000-tick chunk is stepped as 999 + 1 so the override acts just before the engine's own sweep, on the engine's own counts
(spike_count - _sweep_base), except that the sweep's final tick is not yet in them (counted and recorded as late_cells).
Exit 0; 2 if arm PH's W differs from the recorded 8.26 PH W (full runs).
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
import k821_triplet as t6
import k823_ceiling as c823
from k816_hetero_write import A_TICKS, B_TICKS, BASE_TICKS, K_W, PATTERN_A, PATTERN_B
from k826_learned import FULL, SMOKE, WINDOWS, frozen_copy
from k827_transplant import STIMS, probe_all, wc
from brainsim import encode, hetero, params

RECORD = os.path.expanduser("~/.cache/scratch/brainsim-gen2/k826_PH_seed%d.json")


def sweep_phase(e):
    """Phase the engine will be in when the sweep fires at the end of its next tick (set_sleep runs before the sweep)."""
    ph = e.phase
    limit = e.p.WAKE_TICKS if ph == "wake" else e.p.SLEEP_TICKS
    if e._phase_ticks + 1 >= limit:
        ph = "sleep" if ph == "wake" else "wake"
    return ph


def override(e, snap, groups):
    """Restore, for every exempt cell, its alive excitatory inputs that are unchanged slots since the snapshot."""
    net = e.net
    trigger = hetero.constants(e.p)[0]
    counts = net.spike_count - e._sweep_base
    exempt = np.zeros(net.n, bool)
    for g in groups:
        exempt[g] = True
    exempt &= net.is_exc & (counts >= trigger)
    same = net.alive & snap["alive"] & (net.pre == snap["pre"]) & (net.post == snap["post"])
    slots = np.flatnonzero(same & net.is_exc[net.pre] & exempt[net.post])
    w_before, alive_b, pre_b, post_b = net.w.copy(), net.alive.copy(), net.pre.copy(), net.post.copy()
    net.w[slots] = snap["w"][slots]
    other = np.ones(net.s_max, bool)
    other[slots] = False
    assert np.array_equal(net.w[other], w_before[other]), "override changed a weight outside the restored slots"
    assert np.array_equal(net.alive, alive_b) and np.array_equal(net.pre, pre_b) and np.array_equal(net.post, post_b)
    assert exempt[net.post[slots]].all() and net.is_exc[net.pre[slots]].all()
    wm = net.w_max_n[net.post[slots]]
    return {"n_hpc": int(exempt[groups[0]].sum()), "n_ctx": int(exempt[groups[1]].sum()) if len(groups) > 1 else 0,
            "slots_restored": int(slots.size),
            "mean_dw_over_wmax": float(np.mean((net.w[slots] - w_before[slots]) / wm)) if slots.size else None}, exempt


def take_snap(net):
    return {"w": net.w.copy(), "alive": net.alive.copy(), "pre": net.pre.copy(), "post": net.post.copy()}


def step_chunk(e, snap, groups, tag_t_off, log):
    """One 1000 ticks as 999 + 1. Returns the summed per-cell spike counts; updates snap in place (after the engine's sweep)."""
    c = k11._step_chunked_counting(e, 999).astype(np.int64)
    ph = sweep_phase(e)
    rec = {"off": tag_t_off, "phase": ph, "applied": False}
    trig = hetero.constants(e.p)[0]
    base = e._sweep_base.copy()
    n0 = e.stats["hetero_sweeps"]
    if groups is not None and ph != "sleep":
        o, exempt = override(e, snap, groups)
        rec.update(o, applied=True)
        pre_cnt = e.net.spike_count - base
        grp = np.zeros(e.net.n, bool)
        for g in groups:
            grp[g] = True
        near = grp & e.net.is_exc & (pre_cnt == trig - 1)
    c += k11._step_chunked_counting(e, 1).astype(np.int64)
    assert e.t % e.p.SWEEP_TICKS == 0 and e.phase == ph, ("phase prediction wrong", int(e.t), e.phase, ph)
    assert e.stats["hetero_sweeps"] - n0 == (1 if ph != "sleep" else 0), "engine sweep/hetero count unexpected"
    if rec["applied"]:
        final = e.net.spike_count - base
        rec["late_cells"] = int((near & (final >= trig)).sum())
    log.append(rec)
    snap.update(take_snap(e.net))
    return c


def class_weights(net, W, hpc, ctx):
    inW = np.zeros(net.n, bool)
    inW[W] = True
    out = {}
    for name, ids in (("C1_ctx_to_W", ctx), ("hpc_to_W", hpc)):
        pre_ok = np.zeros(net.n, bool)
        pre_ok[ids] = True
        s = np.flatnonzero(net.alive & pre_ok[net.pre] & inW[net.post])
        out[name] = {"n": int(s.size), "mean_w_over_wmax": float(np.mean(net.w[s] / net.w_max_n[net.post[s]])) if s.size else None}
    return out


def main():
    arg = lambda k, d=None: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
    smoke, seed, arm = "--smoke" in sys.argv, int(arg("--seed", 1)), arg("--arm")
    assert params.ACTIVE_PROFILE == "gen2", "k828 needs BRAINSIM_PLANT=gen2 in the environment"
    assert arm in ("PH", "PO", "POC"), "--arm {PH,PO,POC} is required"
    tl = SMOKE if smoke else FULL
    if smoke:
        k03.WARMUP_TICKS = 4000
    t_start = time.time()
    eng, _ = k03.warm_engine(seed)
    net = eng.net
    hpc, ctx = encode.hpc_e_ids(net), encode.ctx_e_ids(net)
    h.install_tracking({"hpc": hpc, "ctx": ctx}, net.n)
    h.own_params(eng, t6.OVERRIDES)
    assert not eng.triplet_stdp
    k11._step_chunked_counting(eng, BASE_TICKS)
    assert eng.g_struct == 0.0
    T0 = int(eng.t)
    assert T0 % eng.p.SWEEP_TICKS == 0
    A_ids = np.asarray(eng.patterns[PATTERN_A], np.int64)
    print(f"seed {seed} arm {arm} T0={T0}" + ("  [SMOKE]" if smoke else ""))
    groups = {"PH": None, "PO": (hpc,), "POC": (hpc, ctx)}[arm]

    E = {"T": eng, "N": copy.deepcopy(eng)}
    for e in E.values():
        e.hetero_write = True
    h.register(E["T"])
    h.TRACK["ctx"] = h.TRACK["hpc"] = 0.0
    E["T"].present(PATTERN_A, A_TICKS)
    snaps = {a: take_snap(E[a].net) for a in E}
    sweeps = {"T": [], "N": []}

    end = tl["late"][-1]
    W, tot, off = None, np.zeros(net.n, np.int64), 0
    res = {w: [] for w in WINDOWS}
    wts = {w: [] for w in WINDOWS}
    while off < end:
        if off == tl["B_at"]:
            for e in E.values():
                e.present(PATTERN_B, B_TICKS)
        for a in ("T", "N"):
            c = step_chunk(E[a], snaps[a], groups, off + 1000, sweeps[a])
            h.check_phase(E[a])
            if a == "T" and off + 1000 <= A_TICKS:
                tot += c
        off += 1000
        if off == A_TICKS:
            W = encode.select_winners(tot, hpc, K_W)
        for win in WINDOWS:
            if off in tl[win]:
                assert E["T"].t == E["N"].t
                st = {"t": int(E["T"].t)}
                st["T"], _ = probe_all(frozen_copy(E["T"]), W, hpc, ctx, A_ids)
                st["N"], _ = probe_all(frozen_copy(E["N"]), W, hpc, ctx, A_ids)
                res[win].append(st)
                wts[win].append({"t": int(E["T"].t), "T": class_weights(E["T"].net, W, hpc, ctx),
                                 "N": class_weights(E["N"].net, W, hpc, ctx)})
                print(f"  {win} state +{off} done, elapsed {time.time() - t_start:.0f}s", flush=True)
    max_tick = {"ctx": h.TRACK["ctx"], "hpc": h.TRACK["hpc"]}
    h.unregister(E["T"])
    runtime = time.time() - t_start

    means, diffs, readings = {}, {}, {}
    for win in WINDOWS:
        r = res[win]
        means[win] = {c: {s: float(wc(r, c, s).mean()) for s in STIMS} for c in ("T", "N")}
        print(f"\n[{arm} {win}] mean W cells of 16 (50 ticks), {len(r)} states x 8 reps")
        print("%-8s" % "" + " ".join("%7s" % s for s in STIMS))
        for c, nm in (("T", "trained"), ("N", "never")):
            print("%-8s" % nm + " ".join("%7.2f" % means[win][c][s] for s in STIMS))
        diffs[win] = {}
        for s in ("half", "A", "B", "none"):
            d = (wc(r, "T", s) - wc(r, "N", s)).ravel()
            se = float(d.std(ddof=1) / np.sqrt(d.size)) if d.size > 1 else float("nan")
            diffs[win][s] = {"D": float(d.mean()), "se": se, "n": int(d.size)}
            print(f"  D_{s:<4} = trained - never = {d.mean():+.3f}  (paired SE {se:.3f}, {d.size} pairs)")
        for tag in ("T", "N"):
            for k in ("C1_ctx_to_W", "hpc_to_W"):
                v = [x[tag][k]["mean_w_over_wmax"] for x in wts[win]]
                print(f"  {'trained' if tag == 'T' else 'never':<8}{k} mean w/w_max over states: {np.mean([x for x in v if x is not None] or [np.nan]):.4f}")
        for c, nm in (("T", "trained"), ("N", "never")):
            hz = {k: float(np.mean([[p[k] for p in st[c]["none"]] for st in r])) for k in ("ctx_hz", "hpc_hz")}
            print(f"  {nm:<8}no-stimulus probe ctx_hz {hz['ctx_hz']:.3f} hpc_hz {hz['hpc_hz']:.3f}")
            means[win][c]["none_hz"] = hz
    d = diffs["early"]
    readings = {"D_half>=2.0": bool(d["half"]["D"] >= 2.0), "D_B<=0.5*D_half": bool(d["B"]["D"] <= 0.5 * d["half"]["D"]),
                "D_none<=0.5": bool(d["none"]["D"] <= 0.5)}
    readings["meets_all"] = all(readings.values())
    print("\n=== readings, early window (kill test line 2, this seed only) ===")
    for k, v in readings.items():
        print(f"  {k}: {v}")

    ex = {}
    for a in ("T", "N"):
        ap = [s for s in sweeps[a] if s["applied"]]
        isA = lambda s: 1000 < s["off"] <= A_TICKS
        for k in ("n_hpc", "n_ctx", "slots_restored", "late_cells"):
            ex[(a, k)] = {"A_sweeps": float(np.mean([s[k] for s in ap if isA(s)] or [np.nan])),
                          "other": float(np.mean([s[k] for s in ap if not isA(s)] or [np.nan]))}
    if groups is not None:
        print("\nexempt cells per sweep (applied sweeps; A sweeps of the trained arm vs all others):")
        for a, nm in (("T", "trained"), ("N", "never")):
            print(f"  {nm}: " + "; ".join(f"{k}: A {ex[(a, k)]['A_sweeps']:.1f} other {ex[(a, k)]['other']:.1f}" for k in ("n_hpc", "n_ctx", "slots_restored", "late_cells")))
        skipped = sum(1 for s in sweeps["T"] if not s["applied"])
        print(f"  sweeps skipped for sleep (trained): {skipped} of {len(sweeps['T'])}")
    print(f"max one-tick fraction (trained arm): ctx {max_tick['ctx']:.4f} hpc {max_tick['hpc']:.4f}")

    match = None
    if arm == "PH" and not smoke:
        match = sorted(int(x) for x in W) == sorted(int(x) for x in json.load(open(RECORD % seed))["W"])
        print("W vs recorded k826 PH W:", "MATCH" if match else "DIFFERENT")
    else:
        print("W vs recorded k826 PH W: not checked" + (" (smoke)" if smoke else f" (arm {arm})"))
    print(f"runtime {runtime:.0f}s")
    if arg("--json"):
        out = {"seed": seed, "arm": arm, "smoke": smoke, "T0": T0, "W": W.tolist(), "raw": res, "weights": wts, "means": means,
               "diffs": diffs, "readings": readings, "sweeps": sweeps, "max_one_tick_frac": max_tick,
               "W_match_recorded": match, "runtime_s": runtime}
        with open(arg("--json"), "w") as fh:
            json.dump(out, fh, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    sys.exit(2 if match is False else 0)


if __name__ == "__main__":
    main()
