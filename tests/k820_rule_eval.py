"""SPEC 8.20 diagnostic: what the published triplet rule (Pfister and Gerstner 2006) would do on this plant's own
spike trains. A shadow observer rides the C3 engine (8.19) and never writes to it; weights are frozen for the
triplet sets. Engine untouched.
Run: PYTHONPATH=<worktree> python tests/k820_rule_eval.py [--seed N] [--json out.json] [--smoke]
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
from k816_hetero_write import A_TICKS, BASE_TICKS, K_W, PATTERN_A, READOUT_TICKS
from k819_homeostat_ablation import N_P, make_conditions
from brainsim import encode
from brainsim.engine import _gather

TAU_PLUS, TAU_MINUS = 16.8, 33.7
# rule: (A2+, A3+, A2-, tau_y), amplitudes as published, fractions of w_max
RULES = {"R1": (5.3e-3, 8e-3, 3.5e-3, 40.0), "R2": (0.0, 6.5e-3, 7.1e-3, 114.0)}
RULE_IDS = ("R0", "R1", "R2")
CLASSES = ("W<-P", "W<-otherctxE", "W<-hpcE", "otherhpcE<-ctxE", "P<-Asense", "P<-othersense", "P<-ctxE",
           "otherctxE<-ctxE")
NC = len(CLASSES)
GAIN_PW, GAIN_SP, OTHER_PW, OTHER_SP = 0, 4, 1, 5   # class indices
VALID_TOL = 1e-4
GAIN_TARGET, DRIFT_MAX, SEL_MIN = 0.10, 0.003, 2.0
FULL = {"A": A_TICKS, "bg": 15000, "warm": 1000}
SMOKE = {"A": A_TICKS, "bg": 3000, "warm": 1000}


class Shadow:
    """Accumulates, per synapse id and in units of w_max, what R0 (engine's rule), R1 and R2 would change."""

    def __init__(self, eng):
        net = eng.net
        n, s = net.n, net.s_max
        self.exc = net.is_exc
        self.tr = {k: np.zeros(n) for k in ("r1", "o1", "o2_R1", "o2_R2")}
        self.dec = {"r1": np.exp(-1.0 / TAU_PLUS), "o1": np.exp(-1.0 / TAU_MINUS),
                    "o2_R1": np.exp(-1.0 / RULES["R1"][3]), "o2_R2": np.exp(-1.0 / RULES["R2"][3])}
        self.acc = {r: np.zeros(s) for r in RULE_IDS}
        self.ok = np.ones(s, bool)           # synapse ids still accumulating (all during validity, then class members)
        self.label = np.full(s, -1, np.int8)
        self.w0 = np.empty(s, net.w.dtype)
        self.al0 = np.empty(s, bool)
        self.on = False                      # accumulate (False: only the shadow traces run)
        self.win = 0                         # window index for the o2 statistics
        self.o2sum = {r: np.zeros((2, NC)) for r in RULES}
        self.o2cnt = np.zeros((2, NC))

    def _add(self, rule, ids, vals):
        m = self.ok[ids]
        self.acc[rule][ids[m]] += vals[m]

    def tick(self, eng):
        net, p, tr = eng.net, eng.p, self.tr
        g = eng.g
        sweep = (eng.t + 1) % p.SWEEP_TICKS == 0
        pre, post = (net.pre.copy(), net.post.copy()) if sweep else (net.pre, net.post)
        np.copyto(self.w0, net.w)
        np.copyto(self.al0, net.alive)
        w0, al0 = self.w0, self.al0
        x0, y0 = net.x_pre.copy(), net.y_post.copy()
        ip, ii = net.in_ptr, net.in_ids
        bucket = eng.ring[eng.t % (p.D_MAX + 1)]
        if bucket:
            d = bucket[0] if len(bucket) == 1 else np.concatenate(bucket)
            d = d[al0[d]]
            de = d[self.exc[pre[d]]]
            if de.size:
                pd = post[de]
                wd = w0[de]
                w1 = np.maximum(wd * (1.0 - g * net.a_minus_n[pd] * y0[pd]), 0.0)
                if self.on:
                    self._add("R0", de, (w1 - wd) / net.w_max_n[pd])
                    for r, (_, _, a2m, _) in RULES.items():
                        self._add(r, de, -g * tr["o1"][pd] * a2m)
                w0[de] = w1                  # LTP of the same tick reads the post-LTD weight
        for k, dk in self.dec.items():
            tr[k] *= dk
        eng.step(1)
        s = eng._buf_spikes[-1]
        k03._drain_telemetry(eng)
        if s.size:
            inc = _gather(ip, ii, s)
            inc = inc[al0[inc]]
            inc = inc[self.exc[pre[inc]]]
            if inc.size and self.on:
                pp, qq = post[inc], pre[inc]
                xd = x0[qq] * eng._tr_decay
                self._add("R0", inc, g * net.a_plus_n[pp] * xd * (net.w_max_n[pp] - w0[inc]) / net.w_max_n[pp])
                lab = self.label[inc]
                m = (lab >= 0) & self.ok[inc]
                for r, (a2p, a3p, _, _) in RULES.items():
                    o2 = tr["o2_" + r][pp]
                    self._add(r, inc, g * tr["r1"][qq] * (a2p + a3p * o2))
                    self.o2sum[r][self.win] += np.bincount(lab[m], weights=o2[m], minlength=NC)
                self.o2cnt[self.win] += np.bincount(lab[m], minlength=NC)
            for k in tr:
                tr[k][s] += 1.0

    def run(self, eng, ticks):
        for _ in range(ticks):
            self.tick(eng)
            if eng.t % eng.p.SWEEP_TICKS == 0 and self.on and self.ident is not None:
                self.update_ok(eng.net)

    ident = None

    def update_ok(self, net):
        pre0, post0, born0, ids = self.ident
        still = net.alive[ids] & (net.pre[ids] == pre0) & (net.post[ids] == post0) & (net.born[ids] == born0)
        self.ok[ids[~still]] = False


def build_classes(net, P, W, A_ids, sh):
    """Labels fixed at the engine's current tick, by synapse id and identity (pre, post, born)."""
    ctx, sense = encode.ctx_e_ids(net), np.arange(net.region_slice["sense"].start, net.region_slice["sense"].stop)
    hpc = encode.hpc_e_ids(net)
    mk = lambda ids: np.isin(np.arange(net.n), ids)
    isP, isW, isCtx, isHpc, isA, isSense = mk(P), mk(W), mk(ctx), mk(hpc), mk(A_ids), mk(sense)
    ids = np.flatnonzero(net.alive & net.is_exc[net.pre]).astype(np.int64)
    pre, post = net.pre[ids], net.post[ids]
    cls = np.full(ids.size, -1, np.int8)
    for c, m in enumerate((isW[post] & isP[pre], isW[post] & isCtx[pre] & ~isP[pre], isW[post] & isHpc[pre],
                           isHpc[post] & ~isW[post] & isCtx[pre], isP[post] & isA[pre],
                           isP[post] & isSense[pre] & ~isA[pre], isP[post] & isCtx[pre],
                           isCtx[post] & ~isP[post] & isCtx[pre])):
        cls[m & (cls < 0)] = c
    keep = cls >= 0
    ids, cls = ids[keep], cls[keep]
    sh.label[ids] = cls
    sh.ident = (net.pre[ids].copy(), net.post[ids].copy(), net.born[ids].copy(), ids)
    return ids, cls


def stats(vals):
    if vals.size == 0:
        return {"n": 0, "mean": None, "p10": None, "p50": None, "p90": None}
    q = np.percentile(vals, (10, 50, 90))
    return {"n": int(vals.size), "mean": float(vals.mean()), "p10": float(q[0]), "p50": float(q[1]), "p90": float(q[2])}


def build_W(base, hpc):
    """W from a separate on-style copy (hetero write on, A presented), not the observed engine."""
    e = copy.deepcopy(base)
    e.hetero_write = True
    e.present(PATTERN_A, A_TICKS)
    c = k11._step_chunked_counting(e, A_TICKS)
    return encode.select_winners(c, hpc, K_W)


def decision(per_rule, nwin):
    """Per-seed decision-rule quantities at scale 1 and the per-seed k that gives +GAIN_TARGET on the smaller gain."""
    out = {}
    for r, tab in per_rule.items():
        mean = lambda c, w: tab[CLASSES[c]][w]["mean"]
        gpw, gsp = mean(GAIN_PW, "A"), mean(GAIN_SP, "A")
        opw, osp = mean(OTHER_PW, "A"), mean(OTHER_SP, "A")
        gmin = min(gpw, gsp)
        drift = max(abs(tab[c]["bg"]["mean"] or 0.0) for c in CLASSES)
        k = GAIN_TARGET / gmin if gmin > 0 else None
        sel = lambda g, o: (g / o if o not in (0, None) and o > 0 else None)
        out[r] = {"gain_PW": gpw, "gain_SP": gsp, "gain_min": gmin, "k_seed": k,
                  "other_PW": opw, "other_SP": osp, "sel_PW": sel(gpw, opw), "sel_SP": sel(gsp, osp),
                  "drift_scale1": drift, "drift_at_k": (drift * k if k else None)}
    return out


def main():
    smoke = "--smoke" in sys.argv
    seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 1
    tl = SMOKE if smoke else FULL
    if smoke:
        k03.WARMUP_TICKS = 4000
    eng, _ = k03.warm_engine(seed)
    net = eng.net
    hpc, ctx = encode.hpc_e_ids(net), encode.ctx_e_ids(net)

    # C3: no rate-driven rewiring, scaling / 10, own parameter object, override at the warmed tick (as 8.19)
    over = make_conditions(eng.p)["C3"]
    e = copy.deepcopy(eng)
    e.p = types.SimpleNamespace(**{k: v for k, v in vars(eng.p).items() if k.isupper()})
    for k, v in over.items():
        setattr(e.p, k, v)
    del eng
    e.hetero_write = False
    sh = Shadow(e)
    k11._step_chunked_counting(e, BASE_TICKS - tl["warm"])
    sh.run(e, tl["warm"])                    # shadow traces warm up, nothing accumulated
    assert e.p.STRUCT_BASE == 0.0 and e.g_struct == 0.0, "C3 structural gain not zero"
    T0 = int(e.t)
    print(f"seed {seed} T0={T0}" + ("  [SMOKE]" if smoke else "") + "  overrides:", over)

    p0 = copy.deepcopy(e)
    p0.present(PATTERN_A, READOUT_TICKS)
    c = k11._step_chunked_counting(p0, READOUT_TICKS)
    P = ctx[np.argsort(-c[ctx], kind="stable")[:N_P]]
    del p0
    W = build_W(e, hpc)
    A_ids = np.asarray(e.patterns[PATTERN_A], np.int64)
    ids, cls = build_classes(e.net, P, W, A_ids, sh)
    print(f"P first 10 {P[:10].tolist()}  W {W.tolist()}  class sizes {np.bincount(cls, minlength=NC).tolist()}")
    pre0, post0 = e.net.pre[ids].astype(np.int64), e.net.post[ids].astype(np.int64)
    members = [np.flatnonzero(cls == c) for c in range(NC)]

    # ---- window A (A presented exactly as the 8.19 `off` arm), validity on the first sweep-free stretch ------- #
    e.present(PATTERN_A, tl["A"])
    sh.on = True
    n_val = e.p.SWEEP_TICKS - 1 - T0 % e.p.SWEEP_TICKS
    count0 = e.spike_counts().astype(np.int64)
    w_before = e.net.w.copy()
    sh.run(e, n_val)
    w_after = e.net.w.copy()
    snap_val = sh.acc["R0"].copy()
    alive = e.net.alive & e.net.is_exc[e.net.pre]
    reg = e.net.region[e.net.post]
    onto = alive & np.isin(reg, [e.net.region_names.index("ctx"), e.net.region_names.index("hpc")])
    sidx = np.flatnonzero(onto)
    err = np.abs((w_after[sidx] - w_before[sidx]) / e.net.w_max_n[e.net.post[sidx]] - snap_val[sidx])
    max_err = float(err.max()) if err.size else 0.0
    valid = bool(max_err <= VALID_TOL)
    print(f"VALIDITY seed {seed}: ticks {T0 + 1}..{T0 + n_val}  synapses {sidx.size}  max abs err {max_err:.3e} w_max  "
          + ("VALID" if valid else "INVALID"))
    sh.ok = np.zeros_like(sh.ok)
    sh.ok[ids] = True                        # from here only class members accumulate (sweeps drop dead ids)

    # the accumulators hold ticks T0..T0+n_val already; they start at zero at T0
    snaps, counts = {"0": {r: np.zeros_like(sh.acc[r]) for r in RULE_IDS}}, {"0": count0}
    sh.run(e, tl["A"] - n_val)
    snaps["A"] = {r: sh.acc[r].copy() for r in RULE_IDS}
    counts["A"] = e.spike_counts().astype(np.int64)
    sh.win = 1
    sh.run(e, tl["bg"])
    snaps["bg"] = {r: sh.acc[r].copy() for r in RULE_IDS}
    counts["bg"] = e.spike_counts().astype(np.int64)
    print(f"windows done, t={e.t}")

    # ---- tables ---------------------------------------------------------------------------------------------- #
    span = {"A": ("0", "A", tl["A"], 1.0), "bg": ("A", "bg", tl["bg"], 1000.0 / tl["bg"])}   # scale: per presentation / per s
    tables, rates = {}, {}
    for r in RULE_IDS:
        tables[r] = {}
        for ci, cname in enumerate(CLASSES):
            tables[r][cname] = {}
            for w, (a, b, _, f) in span.items():
                v = (snaps[b][r] - snaps[a][r])[ids[members[ci]]] * f
                tables[r][cname][w] = stats(v)
    for ci, cname in enumerate(CLASSES):
        rates[cname] = {}
        up, uq = np.unique(pre0[members[ci]]), np.unique(post0[members[ci]])
        for w, (a, b, nt, _) in span.items():
            d = counts[b] - counts[a]
            rates[cname][w] = {"pre_hz": float(d[up].mean() * 1000.0 / nt) if up.size else None,
                               "post_hz": float(d[uq].mean() * 1000.0 / nt) if uq.size else None}
    o2 = {r: {cname: {w: (float(sh.o2sum[r][wi, ci] / sh.o2cnt[wi, ci]) if sh.o2cnt[wi, ci] else None)
                      for wi, w in enumerate(("A", "bg"))} for ci, cname in enumerate(CLASSES)} for r in RULES}
    dec = decision(tables, tl)

    for r in RULE_IDS:
        print(f"\n=== {r}: accumulated change in w_max (A: per presentation, bg: per second) ===")
        print("%-16s %6s | %-34s | %-34s | pre/post Hz A | pre/post Hz bg%s" % (
            "class", "n", "A mean p10 p50 p90", "bg mean p10 p50 p90", " | o2@post A bg" if r in RULES else ""))
        for cname in CLASSES:
            row = tables[r][cname]
            fmt = lambda s: "n/a" if s["mean"] is None else "%+.2e %+.2e %+.2e %+.2e" % (s["mean"], s["p10"], s["p50"], s["p90"])
            rt = rates[cname]
            fr = lambda x: "-" if x is None else "%.2f" % x
            extra = ""
            if r in RULES:
                extra = " | " + " ".join(fr(o2[r][cname][w]) for w in ("A", "bg"))
            print("%-16s %6d | %-34s | %-34s | %s/%s | %s/%s%s" % (
                cname, row["A"]["n"], fmt(row["A"]), fmt(row["bg"]), fr(rt["A"]["pre_hz"]), fr(rt["A"]["post_hz"]),
                fr(rt["bg"]["pre_hz"]), fr(rt["bg"]["post_hz"]), extra))
    print(f"\n=== decision-rule quantities, seed {seed} (scale 1; k_seed gives +{GAIN_TARGET} on the smaller gain) ===")
    for r, d in dec.items():
        print(r, {k: (None if v is None else float("%.4g" % v)) for k, v in d.items()})
    if "--json" in sys.argv:
        with open(sys.argv[sys.argv.index("--json") + 1], "w") as f:
            json.dump(dict(smoke=smoke, seed=seed, T0=T0, P=P.tolist(), W=W.tolist(), valid=valid, validity_max_err=max_err,
                           class_sizes=np.bincount(cls, minlength=NC).tolist(), classes=list(CLASSES), tables=tables,
                           rates=rates, o2_at_post_spikes=o2, decision=dec,
                           constants=dict(RULES=RULES, TAU_PLUS=TAU_PLUS, TAU_MINUS=TAU_MINUS, GAIN_TARGET=GAIN_TARGET,
                                          DRIFT_MAX=DRIFT_MAX, SEL_MIN=SEL_MIN, windows=tl)),
                      f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(f"EXIT {'SMOKE' if smoke else ''} {'VALID' if valid else 'INVALID'}")


if __name__ == "__main__":
    main()
