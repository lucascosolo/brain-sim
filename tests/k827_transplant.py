"""SPEC 8.27: synapse-class transplant between the trained arm and its never-trained twin on gen2, path P of 8.26.
Run: BRAINSIM_PLANT=gen2 PYTHONPATH=<worktree> python tests/k827_transplant.py --seed N [--smoke] [--json out.json]
Diagnostic only; K1.1 is unchanged. Exit 0; 2 if the trained W differs from the recorded 8.26 W; 3 if the slot layouts differ.
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
from k816_hetero_write import A_TICKS, BASE_TICKS, K_W, PATTERN_A, PATTERN_B, step1000
from k826_learned import frozen_copy
from brainsim import encode, params

RECORD = os.path.expanduser("~/.cache/scratch/brainsim-gen2/k826_P_seed%d.json")
STIMS, TICKS, REPS = ("none", "half", "A", "B"), 50, 8
FULL, SMOKE = (3000, 4000, 5000, 6000, 7000), (3000, 4000)
CLASSES = ("C1", "C2", "C3", "C4", "C5", "C0_other", "ALL")


def class_masks(net, W):
    """Partition of slots by (post cell group, pre cell type). C0_other collects anything C1..C5 do not name."""
    rs, n = net.region_slice, net.n
    hpc_all, ctx_all = np.zeros(n, bool), np.zeros(n, bool)
    hpc_all[rs["hpc"]] = True
    ctx_all[rs["ctx"]] = True
    inW = np.zeros(n, bool)
    inW[W] = True
    pre_ctx_e = ctx_all & net.is_exc
    pre_hpc_e = hpc_all & net.is_exc
    pre, post = net.pre, net.post
    m = {"C1": pre_ctx_e[pre] & inW[post], "C2": pre_hpc_e[pre] & inW[post],
         "C3": ~net.is_exc[pre] & inW[post], "C4": hpc_all[post] & ~inW[post], "C5": ctx_all[post]}
    return m


def classes_for(netT, netN, W):
    """Class masks over slots alive in either arm; asserts disjointness and coverage on both arms."""
    union = netT.alive | netN.alive
    m = {k: v & union for k, v in class_masks(netT, W).items()}
    tot = sum(v.astype(int) for v in m.values())
    assert tot.max() <= 1, "classes C1..C5 overlap"
    m["C0_other"] = union & (tot == 0)
    m["ALL"] = union.copy()
    for net in (netT, netN):
        cover = sum(m[k].astype(int) for k in CLASSES[:-1])
        assert (cover[net.alive] == 1).all() and cover.max() <= 1, "classes do not partition the alive synapses"
    return m


def layout_report(netT, netN):
    u = netT.alive | netN.alive
    r = {"slots_alive_either": int(u.sum()), "alive_differs": int((netT.alive != netN.alive).sum()),
         "pre_differs": int((netT.pre[u] != netN.pre[u]).sum()), "post_differs": int((netT.post[u] != netN.post[u]).sum()),
         "delay_differs": int((netT.delay[u] != netN.delay[u]).sum()),
         "w_differs": int((netT.w[u] != netN.w[u]).sum())}
    r["identical_layout"] = r["pre_differs"] == 0 and r["post_differs"] == 0 and r["delay_differs"] == 0
    return r


def hybrid(host, donor, mask):
    """Frozen copy of host with every per-synapse array (length s_max) copied from donor at the slots of mask.
    Slot layouts are asserted identical beforehand, so ids stay stable. In-flight spikes in host.ring are left alone:
    they belong to the host's cell state, and the engine drops any whose slot is no longer alive at delivery."""
    e = frozen_copy(host)
    for k, v in vars(e.net).items():
        if isinstance(v, np.ndarray) and v.shape == (e.net.s_max,):
            v[mask] = getattr(donor.net, k)[mask]
    e.net.rebuild_index(int(e.t))
    return e


def probe(e0, stim, A_ids, rep):
    e = copy.deepcopy(e0)  # e0 is already frozen
    e.rng = np.random.default_rng(10_000 + rep)
    sw = e.p.SWEEP_TICKS
    assert (int(e.t) + TICKS) // sw == int(e.t) // sw, "probe crosses a slow sweep"
    w0, al0 = e.net.w.copy(), e.net.alive.copy()
    if stim == "half":
        e.inject(encode.cue_ids(A_ids), e.p.PATTERN_AMP_MV, TICKS)
    elif stim in ("A", "B"):
        e.present(PATTERN_A if stim == "A" else PATTERN_B, TICKS)
    c = k11._step_chunked_counting(e, TICKS).astype(np.int64)
    assert np.array_equal(e.net.w, w0) and np.array_equal(e.net.alive, al0), ("weights changed in probe", stim)
    return c


def probe_all(e0, W, hpc, ctx, A_ids):
    out, counts0 = {}, None
    for s in STIMS:
        out[s] = []
        for rep in range(REPS):
            c = probe(e0, s, A_ids, rep)
            if s == "half" and rep == 0:
                counts0 = c
            out[s].append(c823.outputs(c, W, hpc, ctx, TICKS))
    return out, counts0


def wc(res, cond, stim):
    return np.array([[r["W_cells"] for r in st[cond][stim]] for st in res], float)  # states x reps


def main():
    arg = lambda k, d=None: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
    smoke, seed = "--smoke" in sys.argv, int(arg("--seed", 1))
    assert params.ACTIVE_PROFILE == "gen2", "k827 needs BRAINSIM_PLANT=gen2 in the environment"
    offsets = SMOKE if smoke else FULL
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
    A_ids = np.asarray(eng.patterns[PATTERN_A], np.int64)
    print(f"seed {seed} T0={T0}" + ("  [SMOKE]" if smoke else ""))
    E = {"T": eng, "N": copy.deepcopy(eng)}
    for e in E.values():
        e.hetero_write = False
    h.register(E["T"])
    h.TRACK["ctx"] = h.TRACK["hpc"] = 0.0
    E["T"].present(PATTERN_A, A_TICKS)

    log = {"T": {"sweeps": [], "B": []}, "N": {"sweeps": [], "B": []}}
    tot, W, off = np.zeros(net.n, np.int64), None, 0
    hpc_cells = np.arange(net.region_slice["hpc"].start, net.region_slice["hpc"].stop)
    res, states, layouts, ident, class_info = [], [], [], [], []
    W_all = np.concatenate([hpc_cells])
    while off < offsets[-1]:
        for a in ("T", "N"):
            c = step1000(E[a], log[a], False)
            h.check_phase(E[a])
            if a == "T" and off + 1000 <= A_TICKS:
                tot += c
        off += 1000
        if off == A_TICKS:
            W = encode.select_winners(tot, hpc, K_W)
        if off not in offsets:
            continue
        T, N = E["T"], E["N"]
        assert T.t == N.t
        lay = layout_report(T.net, N.net)
        layouts.append(lay)
        print(f"state +{off}: slot layout {lay}", flush=True)
        if not lay["identical_layout"]:
            print("STOP: slot layouts differ (pre/post/delay) between the arms; no hybrid built.")
            sys.exit(3)
        m = classes_for(T.net, N.net, W)
        cinfo = {}
        for k in CLASSES:
            for tag, nn in (("T", T.net), ("N", N.net)):
                sel = m[k] & nn.alive
                ex = sel & nn.is_exc[nn.pre]
                cinfo.setdefault(k, {})[tag] = {
                    "n": int(sel.sum()), "n_exc_pre": int(ex.sum()),
                    "mean_w_over_wmax_exc_pre": float(np.mean(nn.w[ex] / nn.w_max_n[nn.post[ex]])) if ex.any() else None,
                    "mean_abs_w_inh_pre": float(np.mean(np.abs(nn.w[sel & ~nn.is_exc[nn.pre]]))) if (sel & ~nn.is_exc[nn.pre]).any() else None}
        class_info.append(cinfo)
        print("  class sizes (T alive / N alive): " + " ".join(f"{k}={cinfo[k]['T']['n']}/{cinfo[k]['N']['n']}" for k in CLASSES), flush=True)
        st = {}
        st["T"], cT = probe_all(frozen_copy(T), W, hpc, ctx, A_ids)
        st["N"], cN = probe_all(frozen_copy(N), W, hpc, ctx, A_ids)
        allm = m["ALL"]
        for host, donor, tag, cref in ((T, T, "T", cT), (N, N, "N", cN)):
            hy = hybrid(host, donor, allm)
            c = probe(hy, "half", A_ids, 0)
            assert np.array_equal(c, cref), ("identity transplant changed the counts", tag)
        ident.append(True)
        print("  identity: OK", flush=True)
        for k in CLASSES:
            if k == "C0_other" and not m[k].any():
                continue
            st[f"T<-N:{k}"], _ = probe_all(hybrid(T, N, m[k]), W, hpc, ctx, A_ids)
            st[f"N<-T:{k}"], _ = probe_all(hybrid(N, T, m[k]), W, hpc, ctx, A_ids)
        res.append(st)
        states.append(off)
        print(f"  state done, elapsed {time.time() - t_start:.0f}s", flush=True)
    runtime = time.time() - t_start

    conds = list(res[0].keys())
    mean = {c: {s: float(wc(res, c, s).mean()) for s in STIMS} for c in conds}
    print("\n=== mean W cells of 16 (50 ticks), over states x reps ===")
    print("%-12s" % "condition" + " ".join("%7s" % s for s in STIMS))
    for c in conds:
        print("%-12s" % c + " ".join("%7.2f" % mean[c][s] for s in STIMS))
    d_pairs = (wc(res, "T", "half") - wc(res, "N", "half")).ravel()
    D = float(d_pairs.mean())
    se = float(d_pairs.std(ddof=1) / np.sqrt(d_pairs.size)) if d_pairs.size > 1 else float("nan")
    print(f"\nHalf cue D = T - N = {D:+.3f}  (SE {se:.3f}, {d_pairs.size} paired state-rep draws)")
    for s in ("A", "B", "none"):
        print(f"  {s}: T - N = {mean['T'][s] - mean['N'][s]:+.3f}")
    gap = mean["N"]["half"] - mean["T"]["half"]
    rec, ind, rows = {}, {}, {}
    print("\nclass table (half cue). w columns: mean w/w_max over excitatory-pre synapses; C3 shows mean |w| (inhibitory)")
    print("%-9s %8s %8s %9s %9s %10s %10s" % ("class", "nT", "nN", "wT", "wN", "recovered", "induced"))
    for k in CLASSES:
        if f"T<-N:{k}" not in mean:
            continue
        rec[k] = (mean[f"T<-N:{k}"]["half"] - mean["T"]["half"]) / gap if gap else float("nan")
        ind[k] = (mean["N"]["half"] - mean[f"N<-T:{k}"]["half"]) / gap if gap else float("nan")
        f = "mean_abs_w_inh_pre" if k == "C3" else "mean_w_over_wmax_exc_pre"
        v = {a: np.mean([ci[k][a][f] for ci in class_info if ci[k][a][f] is not None] or [np.nan]) for a in "TN"}
        n_ = {a: np.mean([ci[k][a]["n"] for ci in class_info]) for a in "TN"}
        rows[k] = {"nT": n_["T"], "nN": n_["N"], "wT": float(v["T"]), "wN": float(v["N"]), "w_kind": f}
        print("%-9s %8.0f %8.0f %9.4f %9.4f %10.3f %10.3f" % (k, n_["T"], n_["N"], v["T"], v["N"], rec[k], ind[k]))
    print("\nhybrid minus host, other stimuli (T<-N minus T | N<-T minus N)")
    print("%-9s " % "class" + " ".join("%8s|%-8s" % (s, s) for s in ("A", "B", "none")))
    for k in rec:
        print("%-9s " % k + " ".join("%+8.2f|%+-8.2f" % (mean[f"T<-N:{k}"][s] - mean["T"][s], mean[f"N<-T:{k}"][s] - mean["N"][s]) for s in ("A", "B", "none")))

    id_ok = bool(ident) and all(ident)
    valid = bool(D <= -1.5 and id_ok and rec["ALL"] >= 0.8)
    pass_classes = [k for k in rec if k != "ALL" and rec[k] >= 0.6 and ind[k] >= 0.6]
    print("\n=== readings (seed %d) ===" % seed)
    print(f"D (half, 50 ticks) = {D:+.3f} (<= -1.5: {D <= -1.5}); identity OK: {id_ok}; recovered(ALL) = {rec['ALL']:.3f} (>= 0.8: {rec['ALL'] >= 0.8})")
    print(f"valid = {valid}")
    print(f"pass_classes (recovered >= 0.6 and induced >= 0.6, excl. ALL) = {pass_classes}")

    match = None
    if not smoke:
        recorded = sorted(int(x) for x in json.load(open(RECORD % seed))["W"])
        match = sorted(int(x) for x in W) == recorded
        print("W vs recorded k826 P W:", "MATCH" if match else "DIFFERENT")
    else:
        print("W vs recorded k826 P W: not checked (smoke)")
    print(f"runtime {runtime:.0f}s for {len(states)} states")
    if arg("--json"):
        rec_out = {"seed": seed, "smoke": smoke, "T0": T0, "W": W.tolist(), "states": states, "layouts": layouts,
                   "class_info": class_info, "raw": res, "mean": mean, "D": D, "D_se": se,
                   "recovered": rec, "induced": ind, "class_rows": rows, "identity_ok": id_ok, "valid": valid,
                   "pass_classes": pass_classes, "W_match_recorded": match, "runtime_s": runtime}
        with open(arg("--json"), "w") as fh:
            json.dump(rec_out, fh, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    sys.exit(2 if match is False else 0)


if __name__ == "__main__":
    main()
