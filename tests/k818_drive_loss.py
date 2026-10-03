"""SPEC 8.18 diagnostic: where the drive onto W goes in the 8.17 readout loss. Measures only; engine untouched.
Run: PYTHONPATH=<worktree> python tests/k818_drive_loss.py [--seed N] [--json out.json] [--smoke]
"""
import copy
import json
import os
import re
import sys

import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import k03_pairing as k03
import k11_binding as k11
from k815_selective_write import hz
from k816_hetero_write import A_TICKS, B_TICKS, BASE_TICKS, K_W, PATTERN_A, PATTERN_B, READOUT_TICKS, abort, step1000
from brainsim import encode

N_P = 100
T5_LOG = "/home/lucas/.cache/scratch/brainsim-inh/t5_seed%d.log"
# probe offsets from T0 = 122,000: 122,000 124,000 125,000 140,000 160,000 164,000 184,000
FULL = {"probes": (0, 2000, 3000, 18000, 38000, 42000, 62000), "B_at": 40000, "end": 62000,
        "phases": ((28000, "sleep"), (39000, "wake"))}
SMOKE = {"probes": (0, 2000, 3000, 7000, 8000), "B_at": 5000, "end": 8000, "phases": ()}
# arm: (lineage, hetero_write, A presented)
SPEC = {"off": ("inh", False, True), "never": ("inh", True, False), "neveroff": ("inh", False, False),
        "refoff": ("ref", False, True), "refneveroff": ("ref", False, False)}
ARMS = tuple(SPEC)


def deliveries(eng, W, ticks):
    """Steps eng `ticks` ticks, reading each tick's ring bucket before the step (as k817.delivered_exc_onto)."""
    net, p = eng.net, eng.p
    ctx_id, hpc_id = net.region_names.index("ctx"), net.region_names.index("hpc")
    onto = np.zeros(net.n, bool)
    onto[np.asarray(W, np.int64)] = True
    acc = {k: [0, 0.0] for k in ("exc_total", "ctx_E", "hpc_E", "inh")}
    for _ in range(ticks):
        bucket = eng.ring[eng.t % (p.D_MAX + 1)]
        if bucket:
            d = np.concatenate(bucket)
            d = d[net.alive[d] & onto[net.post[d]]]
            w = net.w[d].astype(np.float64)
            exc = net.is_exc[net.pre[d]]
            reg = net.region[net.pre[d]]
            for key, sel in (("exc_total", exc), ("ctx_E", exc & (reg == ctx_id)), ("hpc_E", exc & (reg == hpc_id))):
                acc[key][0] += int(sel.sum())
                acc[key][1] += float(w[sel].sum())
            acc["inh"][0] += int((~exc).sum())
            acc["inh"][1] += float(np.abs(w[~exc]).sum())
        eng.step(1)
    out = {}
    for key, (n, s) in acc.items():
        out[key] = {"count": n, "sum": s, "mean": s / n if n else None}
    return out


def probe(eng, W, P, sense_A, groups):
    """One 50-tick full-A probe with the write off on a deep copy: spikes and deliveries from the same run."""
    e = copy.deepcopy(eng)
    e.hetero_write = False
    e.present(PATTERN_A, READOUT_TICKS)
    before = e.spike_counts().astype(np.int64)
    dl = deliveries(e, W, READOUT_TICKS)
    c = e.spike_counts().astype(np.int64) - before
    spikes = {"sense_A": int(c[sense_A].sum()), "ctx_E": int(c[groups["ctx"]].sum()), "P": int(c[P].sum()),
              "ctx_I": int(c[groups["ctx_I"]].sum()), "hpc_E": int(c[groups["hpc"]].sum()),
              "W_spiking": int((c[W] > 0).sum())}
    return spikes, dl


def _stats(vals):
    return float(np.mean(vals)) if len(vals) else None


def state(net, W, P, ctx):
    """Read-only structural state; no probe."""
    s = np.flatnonzero(net.alive)
    pre, post, w = net.pre[s], net.post[s], net.w[s].astype(np.float64)
    exc = net.is_exc[pre]
    reg = net.region[pre]
    names = net.region_names
    onto_P, onto_W = np.isin(post, P), np.isin(post, W)
    out = {"onto_P": {}, "onto_W_inh": {}, "P_to_W": {}, "ctxE_to_W": {}}
    for r in ("sense", "ctx", "hpc"):
        sel = onto_P & exc & (reg == names.index(r))
        out["onto_P"][r + "_exc"] = {"in_degree": float(sel.sum() / len(P)), "mean_w": _stats(w[sel])}
    sel = onto_P & ~exc
    out["onto_P"]["inh"] = {"in_degree": float(sel.sum() / len(P)), "mean_abs_w": _stats(np.abs(w[sel]))}
    out["onto_P"]["theta"] = float(net.theta[P].mean())
    out["onto_P"]["rate"] = float(net.rate[P].mean())
    sel = onto_W & ~exc
    out["onto_W_inh"] = {"in_degree": float(sel.sum() / len(W)), "mean_abs_w": _stats(np.abs(w[sel]))}
    for key, src in (("P_to_W", P), ("ctxE_to_W", ctx)):
        sel = onto_W & exc & np.isin(pre, src)
        out[key] = {"count": int(sel.sum()), "mean_w": _stats(w[sel])}
    return out


def flatten(d, prefix=""):
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flatten(v, key + "."))
        else:
            out[key] = v
    return out


def t5_reference(seed):
    """{arm: (W cells spiking, summed excitatory weight)} for off and never, parsed from the recorded T5 log."""
    path = T5_LOG % seed
    if not os.path.exists(path):
        return None
    ref = {}
    pat = re.compile(r"^  (off|never)\s+\{'full_A': (\d+)[^}]*\} \{'full_A': ([\d.]+)")
    in_block = False
    for line in open(path):
        in_block = in_block or line.startswith("readout at 184,000")
        m = pat.match(line) if in_block else None
        if m:
            ref[m.group(1)] = (int(m.group(2)), float(m.group(3)))
    return ref if set(ref) == {"off", "never"} else None


def print_tables(rec, times, T0):
    keys = sorted({k for a in ARMS for t in times for k in rec[a][t]})
    for key in keys:
        print(f"\n{key}")
        print("%8s " % "t" + " ".join("%12s" % a for a in ARMS))
        for t in times:
            cells = []
            for a in ARMS:
                v = rec[a][t].get(key)
                cells.append("%12s" % ("-" if v is None else ("%12.4f" % v if isinstance(v, float) else v)))
            print("%8d " % (T0 + t) + " ".join(cells))


def main():
    smoke = "--smoke" in sys.argv
    seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 1
    tl = SMOKE if smoke else FULL
    if smoke:
        k03.WARMUP_TICKS = 4000
    eng, _ = k03.warm_engine(seed)
    net = eng.net
    hpc, ctx = encode.hpc_e_ids(net), encode.ctx_e_ids(net)
    groups = {"hpc": hpc, "ctx": ctx, "ctx_I": np.flatnonzero((net.region == net.region_names.index("ctx")) & ~net.is_exc)}
    lineage = {"ref": eng, "inh": copy.deepcopy(eng)}
    lineage["inh"].inh_homeostat = True
    for e in lineage.values():
        k11._step_chunked_counting(e, BASE_TICKS)
    T0 = int(eng.t)
    print(f"seed {seed} T0={T0}" + ("  [SMOKE]" if smoke else ""))

    # W: the T5 `on` arm (inh lineage, write on, A presented) through the A epoch, as T5 computes it
    on = copy.deepcopy(lineage["inh"])
    on.hetero_write = True
    A_ids = np.asarray(on.patterns[PATTERN_A], np.int64)
    # P: fixed before any arm, from a full-A probe on a copy of the inh lineage at T0
    p0 = copy.deepcopy(lineage["inh"])
    p0.hetero_write = False
    p0.present(PATTERN_A, READOUT_TICKS)
    c0 = k11._step_chunked_counting(p0, READOUT_TICKS)
    P = ctx[np.argsort(-c0[ctx], kind="stable")[:N_P]]
    del p0
    on.present(PATTERN_A, A_TICKS)
    tot = np.zeros(net.n, np.int64)
    log = {"sweeps": [], "B": []}
    for _ in range(A_TICKS // 1000):
        tot += step1000(on, log, False)
    W = encode.select_winners(tot, hpc, K_W)
    del on
    print(f"W={W.tolist()}  P (first 10 of {len(P)})={P[:10].tolist()}")

    engs = {}
    for arm, (lin, flag, _) in SPEC.items():
        engs[arm] = copy.deepcopy(lineage[lin])
        engs[arm].hetero_write = flag
    del eng, lineage

    probes = {a: {} for a in ARMS}
    spikes_rec = {a: {} for a in ARMS}
    deliv_rec = {a: {} for a in ARMS}
    state_rec = {a: {} for a in ARMS}
    phases = dict(tl["phases"])

    def measure(arm, off):
        e = engs[arm]
        sp, dl = probe(e, W, P, A_ids, groups)
        spikes_rec[arm][off], deliv_rec[arm][off] = sp, dl
        st = state(e.net, W, P, ctx)
        state_rec[arm][off] = st
        probes[arm][off] = {**{"spikes." + k: v for k, v in sp.items()},
                            **{"deliv." + k: v for k, v in flatten(dl).items()},
                            **{"state." + k: v for k, v in flatten(st).items()}}

    for arm in ARMS:
        e, (_, _, give_A) = engs[arm], SPEC[arm]
        log = {"sweeps": [], "B": []}
        measure(arm, 0)
        if give_A:
            e.present(PATTERN_A, A_TICKS)
        off = 0
        while off < tl["end"]:
            if off == tl["B_at"]:
                e.present(PATTERN_B, B_TICKS)
            step1000(e, log, False)
            off += 1000
            if off in tl["probes"]:
                measure(arm, off)
            if off in phases and e.phase != phases[off]:
                abort(e, phases[off])
        print(f"arm {arm} done, t={e.t}")

    times = tl["probes"]
    print_tables(probes, times, T0)

    valid = None
    if not smoke:
        ref = t5_reference(seed)
        end = tl["end"]
        if ref is None:
            print(f"\nVALIDITY seed {seed}: INVALID (no T5 reference parsed from {T5_LOG % seed})")
            valid = False
        else:
            res = {}
            for a in ("off", "never"):
                got = (spikes_rec[a][end]["W_spiking"], deliv_rec[a][end]["exc_total"]["sum"])
                res[a] = (got, ref[a], got[0] == ref[a][0] and abs(got[1] - ref[a][1]) < 0.01)
            valid = all(r[2] for r in res.values())
            print(f"\nVALIDITY seed {seed}: " + ("VALID" if valid else "INVALID"), {a: r for a, r in res.items()})
    else:
        print("\nVALIDITY: skipped in smoke (T5 values are for the full timeline)")

    if "--json" in sys.argv:
        with open(sys.argv[sys.argv.index("--json") + 1], "w") as f:
            json.dump(dict(smoke=smoke, seed=seed, T0=T0, W=W.tolist(), P=P.tolist(), valid=valid, times=list(times),
                           spikes=spikes_rec, deliveries=deliv_rec, state=state_rec, flat=probes), f, indent=1,
                      default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(f"EXIT {'SMOKE' if smoke else ('VALID' if valid else 'INVALID')}")


if __name__ == "__main__":
    main()
