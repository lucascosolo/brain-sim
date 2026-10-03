"""SPEC 8.22 Part B: offline screen of R1 (triplet as built), R3 (triplet with sliding depression threshold, converged
state emulated) and R4 (Graupner-Brunel 2012 calcium rule, no noise) on the pair-rule plant's own spike trains.
A shadow observer rides an engine it never writes to. Engine untouched.
Run: PYTHONPATH=<worktree> python tests/k822_rule_screen.py [--seed N] [--json out.json] [--smoke]
Exit 0 if the R0 validity check holds, 2 if not.
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
import k822_rules as rules
from k816_hetero_write import A_TICKS, B_TICKS, K_W, PATTERN_A, PATTERN_B, READOUT_TICKS
from k821_triplet import N_P, OVERRIDES
from brainsim import encode, triplet
from brainsim.engine import _gather

CLASSES = ("W<-P", "W<-otherctxE", "W<-hpcE", "otherhpcE<-P", "otherhpcE<-ctxE", "P<-Asense", "P<-othersense",
           "P<-ctxE", "otherctxE<-ctxE")
NC = len(CLASSES)
CI = {c: i for i, c in enumerate(CLASSES)}
DRIFT_CLASSES = ("otherhpcE<-ctxE", "otherctxE<-ctxE")
RULE_IDS = ("R1", "R3", "R4")
VALID_TOL = 1e-4
SPEC_MIN, DRIFT_MAX, KEPT_MIN = 0.10, 0.05, 0.5
RHO_HI, RHO_LO = 0.98, 0.02
# ticks: warm = engine warm-up end (rate filter and nothing else start here), shadow = traces start, ovr = C3 overrides
# applied (as T6's pair_on arm, right after the warm-up), base = baseline stretch start, T0 = classes / A / accumulation.
# offs = snapshots after T0; windows A, wake, sleep, B-and-after.
FULL = {"warm": 92000, "shadow": 111000, "ovr": 120000, "base": 112000, "T0": 122000,
        "offs": (2000, 18000, 38000, 62000), "B_off": 40000}
SMOKE = {"warm": 8000, "shadow": 8000, "ovr": 8000, "base": 9000, "T0": 10000,
         "offs": (2000, 4000, 6000, 8000), "B_off": 5000}
WINDOWS = ("A", "wake", "sleep", "B+after")
T6_DIR = os.path.expanduser("~/.cache/scratch/brainsim-tri")


class Shadow:
    def __init__(self, eng):
        net = eng.net
        n, s = net.n, net.s_max
        self.exc = net.is_exc
        self.tr = {k: np.zeros(n) for k in ("r1", "o1", "o2")}
        self.dec = {"r1": np.exp(-1.0 / triplet.TAU_PLUS_MS), "o1": np.exp(-1.0 / triplet.TAU_MINUS_MS),
                    "o2": np.exp(-1.0 / triplet.TAU_Y_MS)}
        kd = triplet.k_of(eng.p)
        self.kvec = np.zeros(n)
        for i, name in enumerate(net.region_names):
            self.kvec[net.region == i] = kd.get(name, 0.0)
        self.kvec *= net.a_plus_n > 0                       # the engine applies the rule only to cells with a_plus > 0
        self.acc = {r: np.zeros(s) for r in ("R0", "R1", "R3")}
        self.ok = np.ones(s, bool)
        self.w0 = np.empty(s, net.w.dtype)
        self.al0 = np.empty(s, bool)
        self.rate = np.zeros(n)                              # running rate, spikes per tick, tau 10,000 ticks
        self.traces = False                                  # shadow traces run
        self.base = False                                    # baseline stretch: per-cell R1 LTP / LTD
        self.on = False                                      # per-synapse accumulation (R1, R3, R4)
        self.r0 = False                                      # R0 accumulation (validity only)
        self.cell_ltp = np.zeros(n)
        self.cell_ltd = np.zeros(n)
        self.cj = np.ones(n)
        self.base_j = np.ones(n)
        self.ca = rules.gb_ca_decay()
        self.pre_tr = np.zeros(n)
        self.post_tr = np.zeros(n)
        self.delay = [np.zeros(0, np.int64) for _ in range(rules.GB["delay_ticks"])]
        self.ident = None
        self.rho = None
        self.t_r4 = 0.0

    def _add(self, rule, ids, vals):
        m = self.ok[ids]
        self.acc[rule][ids[m]] += vals[m]

    def set_members(self, ids, pre0, post0, rho0):
        self.ids, self.mpre, self.mpost, self.rho = ids, pre0, post0, rho0.copy()

    def _after(self, s, spiked_mask_shape):
        mask = np.zeros(spiked_mask_shape, bool)
        mask[s] = True
        self.rate = rules.rate_step(self.rate, mask)

    def tick(self, eng):
        net, p, tr = eng.net, eng.p, self.tr
        if not self.traces:
            eng.step(1)
            s = eng._buf_spikes[-1]
            k03._drain_telemetry(eng)
            self._after(s, net.n)
            return
        g = eng.g
        sweep = (eng.t + 1) % p.SWEEP_TICKS == 0
        pre, post = (net.pre.copy(), net.post.copy()) if sweep else (net.pre, net.post)
        np.copyto(self.w0, net.w)
        np.copyto(self.al0, net.alive)
        w0, al0 = self.w0, self.al0
        x0, y0 = net.x_pre.copy(), net.y_post.copy()
        ip, ii = net.in_ptr, net.in_ids
        acc = self.on or self.base
        bucket = eng.ring[eng.t % (p.D_MAX + 1)]
        if bucket:
            d = bucket[0] if len(bucket) == 1 else np.concatenate(bucket)
            d = d[al0[d]]
            de = d[self.exc[pre[d]]]
            if de.size:
                pd = post[de]
                wd = w0[de]
                w1 = np.maximum(wd * (1.0 - g * net.a_minus_n[pd] * y0[pd]), 0.0)
                if self.r0:
                    self._add("R0", de, (w1 - wd) / net.w_max_n[pd])
                if acc:
                    k = self.kvec[pd] > 0
                    dek, pdk = de[k], pd[k]
                    v1 = -g * self.kvec[pdk] * triplet.A2_MINUS * tr["o1"][pdk]
                    if self.base:
                        self.cell_ltd += np.bincount(pdk, weights=v1, minlength=net.n)
                    if self.on:
                        self._add("R1", dek, v1)
                        mult = rules.r3_multiplier(self.cj[pdk], self.rate[pdk], self.base_j[pdk])
                        self._add("R3", dek, v1 * mult)
                w0[de] = w1
        for k, dk in self.dec.items():
            tr[k] *= dk
        eng.step(1)
        s = eng._buf_spikes[-1]
        k03._drain_telemetry(eng)
        if s.size:
            inc = _gather(ip, ii, s)
            inc = inc[al0[inc]]
            inc = inc[self.exc[pre[inc]]]
            if inc.size:
                pp, qq = post[inc], pre[inc]
                if self.r0:
                    xd = x0[qq] * eng._tr_decay
                    self._add("R0", inc, g * net.a_plus_n[pp] * xd * (net.w_max_n[pp] - w0[inc]) / net.w_max_n[pp])
                if acc:
                    k = self.kvec[pp] > 0
                    ik, ppk, qqk = inc[k], pp[k], qq[k]
                    v = g * self.kvec[ppk] * tr["r1"][qqk] * (triplet.A2_PLUS + triplet.A3_PLUS * tr["o2"][ppk])
                    if self.base:
                        self.cell_ltp += np.bincount(ppk, weights=v, minlength=net.n)
                    if self.on:
                        self._add("R1", ik, v)
                        self._add("R3", ik, v)
            for k in tr:
                tr[k][s] += 1.0
        # calcium traces: presynaptic +1 arrives GB delay_ticks after the cell's spike, postsynaptic at the spike
        self.pre_tr *= self.ca
        self.post_tr *= self.ca
        late = self.delay.pop(0)
        self.delay.append(s.astype(np.int64))
        self.pre_tr[late] += 1.0
        self.post_tr[s] += 1.0
        if self.on:
            t1 = time.time()
            c = rules.gb_calcium(self.pre_tr[self.mpre], self.post_tr[self.mpost])
            self.rho = rules.gb_step(self.rho, c, g=g)
            self.t_r4 += time.time() - t1
        self._after(s, net.n)

    def update_ok(self, net):
        pre0, post0, born0, ids = self.ident
        still = net.alive[ids] & (net.pre[ids] == pre0) & (net.post[ids] == post0) & (net.born[ids] == born0)
        self.ok[ids[~still]] = False


def build_classes(net, P, W, A_ids, sh):
    """Labels fixed at the engine's current tick, by synapse id and identity (pre, post, born). Precedence = CLASSES
    order, first match wins: otherhpcE<-P is before otherhpcE<-ctxE and P-pre is excluded from both drift classes."""
    ctx = encode.ctx_e_ids(net)
    sense = np.arange(net.region_slice["sense"].start, net.region_slice["sense"].stop)
    hpc = encode.hpc_e_ids(net)
    mk = lambda ids: np.isin(np.arange(net.n), ids)
    isP, isW, isCtx, isHpc, isA, isSense = mk(P), mk(W), mk(ctx), mk(hpc), mk(A_ids), mk(sense)
    ids = np.flatnonzero(net.alive & net.is_exc[net.pre]).astype(np.int64)
    pre, post = net.pre[ids], net.post[ids]
    cls = np.full(ids.size, -1, np.int8)
    masks = {"W<-P": isW[post] & isP[pre],
             "W<-otherctxE": isW[post] & isCtx[pre] & ~isP[pre],
             "W<-hpcE": isW[post] & isHpc[pre],
             "otherhpcE<-P": isHpc[post] & ~isW[post] & isP[pre],
             "otherhpcE<-ctxE": isHpc[post] & ~isW[post] & isCtx[pre] & ~isP[pre],
             "P<-Asense": isP[post] & isA[pre],
             "P<-othersense": isP[post] & isSense[pre] & ~isA[pre],
             "P<-ctxE": isP[post] & isCtx[pre],
             "otherctxE<-ctxE": isCtx[post] & ~isP[post] & isCtx[pre] & ~isP[pre]}
    for c, name in enumerate(CLASSES):
        cls[masks[name] & (cls < 0)] = c
    keep = cls >= 0
    ids, cls = ids[keep], cls[keep]
    sh.ident = (net.pre[ids].copy(), net.post[ids].copy(), net.born[ids].copy(), ids)
    return ids, cls


def stats(vals):
    if vals.size == 0:
        return {"n": 0, "mean": None, "p10": None, "p50": None, "p90": None}
    q = np.percentile(vals, (10, 50, 90))
    return {"n": int(vals.size), "mean": float(vals.mean()), "p10": float(q[0]), "p50": float(q[1]), "p90": float(q[2])}


def build_W(base, hpc):
    """W from a separate copy (hetero write on, A presented), as 8.20; the observed engine is not touched."""
    e = copy.deepcopy(base)
    e.hetero_write = True
    e.present(PATTERN_A, A_TICKS)
    c = k11._step_chunked_counting(e, A_TICKS)
    return encode.select_winners(c, hpc, K_W)


def compare_t6(seed, P, W):
    path = os.path.join(T6_DIR, f"t6_seed{seed}.json")
    if not os.path.exists(path):
        print(f"T6 CHECK: {path} not found")
        return {}
    rec = json.load(open(path))
    out = {}
    for name, mine, key in (("P", P, "P"), ("W", W, "own_W")):
        same = sorted(int(x) for x in mine) == sorted(int(x) for x in rec[key])
        out[name] = "MATCH" if same else "DIFFERENT"
        print(f"T6 CHECK {name} vs t6_seed{seed}.json[{key}]: {out[name]}"
              + ("" if same else f"  (mine {len(mine)} ids, recorded {len(rec[key])}, overlap "
                                 f"{len(set(map(int, mine)) & set(map(int, rec[key])))})"))
    return out


def main():
    smoke = "--smoke" in sys.argv
    seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 1
    tl = SMOKE if smoke else FULL
    tag = "  [SMOKE: shortened schedule, not a result]" if smoke else ""
    k03.WARMUP_TICKS = tl["warm"]
    t_start = time.time()
    e, _ = k03.warm_engine(seed)
    net = e.net
    hpc, ctx = encode.hpc_e_ids(net), encode.ctx_e_ids(net)
    e.hetero_write = False
    assert not e.triplet_stdp
    sh = Shadow(e)
    T0 = tl["T0"]
    print(f"seed {seed}{tag}\nclasses (first match wins): {list(CLASSES)}\ndrift classes: {list(DRIFT_CLASSES)} "
          f"(P-pre excluded from both, so P->otherctxE synapses are unlabelled)")
    t_shadow = None
    while e.t < T0:
        if e.t == tl["ovr"]:
            h.own_params(e, OVERRIDES)
            e.hetero_write = False
        if e.t == tl["shadow"]:
            sh.traces = True
            t_shadow = time.time()
            t_shadow_tick = e.t
        if e.t == tl["base"]:
            sh.base = True
        sh.tick(e)
        if not smoke and e.t % 1000 == 0 and e.t > 1000:
            h.check_phase(e)
    assert e.p.STRUCT_BASE == 0.0 and e.g_struct == 0.0, "C3 structural gain not zero"
    sh.base = False
    sh.base_j = np.maximum(sh.rate, 1.0 / 10000.0)   # SPEC 8.22 amendment: floor at one spike per filter time constant
    print(f"R3 base floor applied to {int((sh.rate < 1e-4).sum())} cells")
    sh.cj = rules.r3_cj(sh.cell_ltp, sh.cell_ltd)
    print(f"T0={e.t}  overrides applied at {tl['ovr']}: {OVERRIDES}  rate filter started at {tl['warm']}, "
          f"shadow traces at {tl['shadow']}, baseline stretch {tl['base']}..{T0}")

    p0 = copy.deepcopy(e)
    p0.present(PATTERN_A, READOUT_TICKS)
    c = k11._step_chunked_counting(p0, READOUT_TICKS)
    P = ctx[np.argsort(-c[ctx], kind="stable")[:N_P]]
    del p0
    W = build_W(e, hpc)
    t6 = {} if smoke else compare_t6(seed, P, W)
    A_ids = np.asarray(e.patterns[PATTERN_A], np.int64)
    ids, cls = build_classes(net, P, W, A_ids, sh)
    pre0, post0 = net.pre[ids].astype(np.int64), net.post[ids].astype(np.int64)
    w0frac = net.w[ids].astype(np.float64) / net.w_max_n[post0]
    sh.set_members(ids, pre0, post0, np.clip(w0frac, 0.0, 1.0))
    rho0 = sh.rho.copy()
    members = [np.flatnonzero(cls == c) for c in range(NC)]
    print(f"P first 10 {P[:10].tolist()}  W {W.tolist()}\nclass sizes {dict(zip(CLASSES, np.bincount(cls, minlength=NC).tolist()))}")

    snaps = {T0: {"R1": np.zeros(ids.size), "R3": np.zeros(ids.size), "R4": np.zeros(ids.size),
                  "ok": np.ones(ids.size, bool), "counts": e.spike_counts().astype(np.int64)}}
    snap_ticks = [T0 + o for o in tl["offs"]]

    def snapshot():
        snaps[int(e.t)] = {"R1": sh.acc["R1"][ids].copy(), "R3": sh.acc["R3"][ids].copy(), "R4": sh.rho - rho0,
                           "ok": sh.ok[ids].copy(), "counts": e.spike_counts().astype(np.int64)}

    # ---- A presented, R0 validity on the first sweep-free stretch --------------------------------------------- #
    e.present(PATTERN_A, A_TICKS)
    sh.on = sh.r0 = True
    n_val = e.p.SWEEP_TICKS - 1 - T0 % e.p.SWEEP_TICKS
    w_before = net.w.copy()
    for _ in range(n_val):
        sh.tick(e)
    w_after = net.w.copy()
    alive = net.alive & net.is_exc[net.pre]
    onto = alive & np.isin(net.region[net.post], [net.region_names.index("ctx"), net.region_names.index("hpc")])
    sidx = np.flatnonzero(onto)
    err = np.abs((w_after[sidx] - w_before[sidx]) / net.w_max_n[net.post[sidx]] - sh.acc["R0"][sidx])
    max_err = float(err.max()) if err.size else 0.0
    valid = bool(max_err <= VALID_TOL)
    print(f"VALIDITY seed {seed}: ticks {T0 + 1}..{T0 + n_val}  synapses {sidx.size}  max abs err {max_err:.3e} w_max  "
          + ("VALID" if valid else "INVALID"))
    sh.r0 = False
    sh.ok = np.zeros_like(sh.ok)
    sh.ok[ids] = True

    t_run = time.time()
    tick0 = e.t
    while snap_ticks:
        if e.t == T0 + tl["B_off"]:
            e.present(PATTERN_B, B_TICKS)
        sh.tick(e)
        if e.t % e.p.SWEEP_TICKS == 0:
            sh.update_ok(net)
            if not smoke:
                h.check_phase(e)
        if e.t == snap_ticks[0]:
            snapshot()
            snap_ticks.pop(0)
            print(f"snapshot t={e.t}  wall {time.time() - t_start:.0f}s")
    wall_run = time.time() - t_run
    sec_per_1000 = wall_run / (e.t - tick0) * 1000.0
    print(f"wall: {sec_per_1000:.2f} s per 1000 ticks (full shadow incl. R4; R4 step alone {sh.t_r4 / (e.t - tick0) * 1000:.2f} s/1000)"
          f"; total {time.time() - t_start:.0f}s")
    if not smoke:
        print(f"estimate: ~{sec_per_1000 * 62:.0f}s accumulation + warm/baseline/W; full run shown above for this seed")

    # ---- tables ----------------------------------------------------------------------------------------------- #
    times = sorted(snaps)
    tables = {r: {cn: {} for cn in CLASSES} for r in RULE_IDS}
    means = {r: {cn: {} for cn in CLASSES} for r in RULE_IDS}
    for r in RULE_IDS:
        for ci, cn in enumerate(CLASSES):
            for t in times[1:]:
                m = members[ci][snaps[t]["ok"][members[ci]]]
                st = stats(snaps[t][r][m])
                tables[r][cn][t] = st
                means[r][cn][t] = st["mean"]
    last, first = times[-1], times[1]
    dec, spec, windows, bounds = {}, {}, {}, {}
    for r in RULE_IDS:
        sp = {t: (None if means[r]["W<-P"][t] is None or means[r]["W<-otherctxE"][t] is None
                  else means[r]["W<-P"][t] - means[r]["W<-otherctxE"][t]) for t in times[1:]}
        drift = max(abs(means[r][cn][last] or 0.0) for cn in DRIFT_CLASSES)
        kept = sp[last] / sp[first] if sp[first] is not None and sp[first] > 0 and sp[last] is not None else None
        q = [sp[last] is not None and sp[last] >= SPEC_MIN, drift <= DRIFT_MAX, kept is not None and kept >= KEPT_MIN]
        dec[r] = {"spec_ok": bool(q[0]), "drift_ok": bool(q[1]), "kept_ok": bool(q[2]), "QUALIFIES": bool(all(q)),
                  "spec_last": sp[last], "drift": drift, "kept": kept}
        spec[r] = sp
        windows[r] = {}
        for cn in ("W<-P", "W<-otherctxE"):
            windows[r][cn] = {}
            for wi, (a, b) in enumerate(zip(times[:-1], times[1:])):
                m = members[CI[cn]][snaps[b]["ok"][members[CI[cn]]]]
                windows[r][cn][WINDOWS[wi]] = float((snaps[b][r][m] - snaps[a][r][m]).mean()) if m.size else None
        bounds[r] = {}
        for ci, cn in enumerate(CLASSES):
            m = members[ci][snaps[last]["ok"][members[ci]]]
            if m.size == 0:
                bounds[r][cn] = None
            elif r == "R4":
                x = rho0[m] + snaps[last][r][m]
                bounds[r][cn] = float(((x >= RHO_HI) | (x <= RHO_LO)).mean())
            else:
                x = w0frac[m] + snaps[last][r][m]
                bounds[r][cn] = float(((x >= 1.0) | (x <= 0.0)).mean())

    def cj_stats(cells):
        v = sh.cj[cells]
        d = stats(v)
        d["kept_at_1"] = int((v == 1.0).sum())
        return d
    cjd = {"ctxE": cj_stats(ctx), "hpcE": cj_stats(hpc), "W": cj_stats(W)}
    notP = np.setdiff1d(ctx, P)
    notW = np.setdiff1d(hpc, W)
    groups = {"P": P, "W": W, "otherctxE": notP, "otherhpcE": notW}
    rates = {}
    for wi, (a, b) in enumerate(zip(times[:-1], times[1:])):
        d = snaps[b]["counts"] - snaps[a]["counts"]
        rates[WINDOWS[wi]] = {gn: float(d[g_].mean() * 1000.0 / (b - a)) for gn, g_ in groups.items()}

    fmt = lambda s: "n/a" if s["mean"] is None else "%+.3f %+.3f %+.3f %+.3f" % (s["mean"], s["p10"], s["p50"], s["p90"])
    for r in RULE_IDS:
        print(f"\n=== {r}: cumulative change since {T0} in w_max (n, mean p10 p50 p90) ===")
        for cn in CLASSES:
            print("%-16s " % cn + " | ".join("%d: n=%d %s" % (t, tables[r][cn][t]["n"], fmt(tables[r][cn][t]))
                                            for t in times[1:]))
        print("spec per snapshot:", {t: (None if v is None else round(v, 4)) for t, v in spec[r].items()})
        print("window increments (mean):", {cn: {w: (None if v is None else round(v, 4)) for w, v in d.items()}
                                              for cn, d in windows[r].items()})
        print("fraction at a bound at the last snapshot:", {cn: (None if v is None else round(v, 3)) for cn, v in bounds[r].items()})
    print("\nR3 c_j:", {k: {a: (None if v is None else round(v, 3)) for a, v in d.items()} for k, d in cjd.items()})
    print("rates Hz:", {w: {g_: round(v, 3) for g_, v in d.items()} for w, d in rates.items()})
    print(f"\n=== decision, seed {seed}{tag}: spec({last}) >= {SPEC_MIN}, drift <= {DRIFT_MAX}, kept >= {KEPT_MIN} ===")
    for r, d in dec.items():
        print(r, "spec", d["spec_ok"], "drift", d["drift_ok"], "kept", d["kept_ok"], "-> QUALIFIES" if d["QUALIFIES"] else "-> no",
              {k: (None if v is None or isinstance(v, bool) else round(v, 4)) for k, v in d.items() if not isinstance(v, bool)})
    if "--json" in sys.argv:
        with open(sys.argv[sys.argv.index("--json") + 1], "w") as f:
            json.dump(dict(smoke=smoke, seed=seed, T0=T0, timeline=tl, valid=valid, validity_max_err=max_err,
                           P=P.tolist(), W=W.tolist(), t6_check=t6, classes=list(CLASSES),
                           drift_classes=list(DRIFT_CLASSES), class_sizes=np.bincount(cls, minlength=NC).tolist(),
                           tables=tables, spec=spec, windows=windows, bounds=bounds, cj=cjd, rates=rates, decision=dec,
                           sec_per_1000_ticks=sec_per_1000, overrides=OVERRIDES),
                      f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(f"EXIT {'SMOKE ' if smoke else ''}{'VALID' if valid else 'INVALID'}")
    sys.exit(0 if valid else 2)


if __name__ == "__main__":
    main()
