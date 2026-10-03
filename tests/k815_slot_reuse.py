"""SPEC 8.15 diagnostic (3): how often can a queued delay-ring event be delivered through a
reused synapse slot? MEASUREMENT ONLY; the engine is not changed and master is not fixed.

The defect (found by an outside read, confirmed in Engine._tick): the ring holds synapse SLOT
ids; delivery checks only net.alive[slot]. A slot killed by the weak-synapse prune in a slow
sweep is back on the free list before structural growth runs in the same sweep, so growth can
reuse it. Events the old synapse queued in the last D_MAX ticks are then delivered with the
NEW synapse's weight to the NEW synapse's target, although the new synapse is not yet
conducting (net.conduct = t + CONDUCT_DELAY_TICKS). Slots killed by the rate-driven prune are
held back until after growth and cannot be reused in the same sweep.

This driver wraps Engine._slow_sweep (observation only: copies before, compares after, reads
the ring) on the standard run: seed 1, 0 -> 120,000 warm-up, idle to 122,000, A presented
122,000 -> 124,000 on the default plant, on to 135,000.
Run: PYTHONPATH=<worktree> python tests/k815_slot_reuse.py [--json out.json] [--smoke]
"""
import json
import os
import sys
import time

import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import k03_pairing as k03
from brainsim.engine import Engine

SEED = 1
T_WARM, T_A0, T_A1, T_END = 120_000, 122_000, 124_000, 135_000


def instrument(eng, log):
    net = eng.net
    inner = eng._slow_sweep

    def wrapped():
        alive0, pre0, post0, born0 = net.alive.copy(), net.pre.copy(), net.post.copy(), net.born.copy()
        inner()
        reused = np.flatnonzero(alive0 & net.alive
                                & ((pre0 != net.pre) | (post0 != net.post) | (born0 != net.born)))
        rec = dict(t=int(eng.t), killed=int((alive0 & ~net.alive).sum()) + int(reused.size),
                   reused=int(reused.size), stale_events=0, stale_by_region={}, queued=0)
        queued = [a for bucket in eng.ring for a in bucket]
        if queued:
            q = np.concatenate(queued)
            rec["queued"] = int(q.size)
            if reused.size:
                stale = q[np.isin(q, reused)]
                rec["stale_events"] = int(stale.size)
                for name, sl in net.region_slice.items():
                    n = int(((net.post[stale] >= sl.start) & (net.post[stale] < sl.stop)).sum())
                    if n:
                        rec["stale_by_region"][name] = n
                rec["stale_w_over_wmax_mean"] = float(
                    (np.abs(net.w[stale]) / net.w_max_n[net.post[stale]]).mean()) if stale.size else 0.0
                rec["stale_exc"] = int(net.is_exc[net.pre[stale]].sum())
        log.append(rec)

    eng._slow_sweep = wrapped


def _run_to(eng, t_end):
    while eng.t < t_end:
        eng.step(min(1000, t_end - eng.t))
        k03._drain_telemetry(eng)


def _summary(log, t0, t1, touched):
    rows = [r for r in log if t0 < r["t"] <= t1]
    by = {}
    for r in rows:
        for k, v in r["stale_by_region"].items():
            by[k] = by.get(k, 0) + v
    stale = sum(r["stale_events"] for r in rows)
    return dict(t0=t0, t1=t1, sweeps=len(rows), killed=sum(r["killed"] for r in rows),
                reused_slots=sum(r["reused"] for r in rows),
                sweeps_with_reuse=sum(1 for r in rows if r["reused"]),
                stale_events=stale, sweeps_with_stale=sum(1 for r in rows if r["stale_events"]),
                max_stale_in_one_sweep=max([r["stale_events"] for r in rows], default=0),
                stale_exc=sum(r.get("stale_exc", 0) for r in rows),
                stale_by_region=by, delivered_events=int(touched),
                stale_per_million_delivered=(1e6 * stale / touched) if touched else float("nan"))


def main():
    smoke = "--smoke" in sys.argv
    scale = 0.05 if smoke else 1.0
    tw, a0, a1, te = (int(x * scale) for x in (T_WARM, T_A0, T_A1, T_END))
    t_wall = time.time()
    eng = Engine(seed=SEED, params=k03._deepcopyable_params())
    log = []
    instrument(eng, log)
    _run_to(eng, tw)
    touched_warm = eng.stats["syn_touched_sum"]
    _run_to(eng, a0)
    eng.present(0, a1 - a0)
    _run_to(eng, te)
    touched_all = eng.stats["syn_touched_sum"]
    out = dict(seed=SEED, wall_s=time.time() - t_wall,
               warm=_summary(log, 0, tw, touched_warm),
               encode_epoch=_summary(log, tw, te, touched_all - touched_warm),
               per_sweep_encode_epoch=[r for r in log if r["t"] > tw])
    print("=" * 76)
    print("SPEC 8.15 diagnostic: delay-ring events delivered through a reused slot (seed 1)")
    print("MEASUREMENT ONLY: engine unchanged, master not fixed")
    print("=" * 76)
    for name in ("warm", "encode_epoch"):
        s = out[name]
        print(f"{name:13s} t {s['t0']:>7d}-{s['t1']:<7d} sweeps {s['sweeps']:4d}  killed {s['killed']:7d}  "
              f"reused slots {s['reused_slots']:6d} (in {s['sweeps_with_reuse']} sweeps)  "
              f"stale events {s['stale_events']:6d} (in {s['sweeps_with_stale']} sweeps, max {s['max_stale_in_one_sweep']})  "
              f"exc {s['stale_exc']}  by region {s['stale_by_region']}  "
              f"delivered {s['delivered_events']:d}  stale per 1e6 delivered {s['stale_per_million_delivered']:.3f}")
    print("encode epoch per sweep (t, reused, stale):",
          [(r["t"], r["reused"], r["stale_events"]) for r in out["per_sweep_encode_epoch"]])
    if "--json" in sys.argv:
        with open(sys.argv[sys.argv.index("--json") + 1], "w") as f:
            json.dump(out, f, indent=1)
    print("EXIT 0")


if __name__ == "__main__":
    main()
