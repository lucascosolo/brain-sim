"""P2-E5: item-specific recall on correlated inputs (structured-input diagnostic).

Contract: docs/plant2/P2-E5-structured-items.md, frozen at commit bc28cd9 before this file existed.
The P2-E3 system runs unchanged; only the item generator (`_pat`) is replaced by the contract's
family generator. Learning-time memory spikes are captured by a read-only wrapper on `net.step`
around the inherited `learn_one` (never copied or changed). P2-E3's run_phase, readout and score,
and P2-E4's online driver, are reused unchanged.

    python3 -m plant2.experiments.p2_e5_structured explore --seeds 44 45
    python3 -m plant2.experiments.p2_e5_structured predict
    python3 -m plant2.experiments.p2_e5_structured run --seeds 21 22 23 24 25 --gated
    python3 -m plant2.experiments.p2_e5_structured verdict
"""
import argparse
import copy
import hashlib
import io
import json
import subprocess
import sys
import time

import numpy as np

from plant2 import power, record
from plant2.btsp import BinarySynapses
from plant2.experiments import p2_e1_btsp as e1
from plant2.experiments import p2_e3_completion as e3
from plant2.experiments import p2_e4_online as e4
from plant2.readout import replay

PROTO, EXEMPLAR, BLOCK_CUES, POOLED, PI = 20, 21, 22, 23, 24  # stream ids (contract stream table)
GATED_SEEDS = (21, 22, 23, 24, 25)
EXPLORE_SEEDS = (44, 45)
P2E3_ARMS = ("s100", "s80", "s40", "pooled", "F40")
ARM_SPEC = dict(main=dict(s=60, F=10), s80=dict(s=80, F=10), s40=dict(s=40, F=10), pooled=dict(s=60, F=10, pooled=True),
                F40=dict(s=60, F=40), s100=None)  # s100: P2-E3's own generator
OWN_BLOCK = ("main", "s80", "s40", "F40")  # arms presented their own reported block; pooled and s100 get main's
REUSED_FILES = ("experiments/p2_e4_online.py", "experiments/p2_e3_completion.py", "experiments/p2_e2_accommodation.py",
                "experiments/p2_e1_btsp.py", "engine.py", "readout.py", "btsp.py")
P2E4_TREE = "9152f1e44821d199697b7c8ff80ff351c0134d88"

CONTRACT = dict(
    e3.CONTRACT, J_fb=2.80, s=60, F=10, gate_M=(500, 1000),
    grid_J=(1.5, 2.0, 2.4, 2.8, 3.2, 3.6, 4.0, 5.0, 6.0), grid_g=(0.0, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0),
    R_k=(2, 3, 4, 6), grid_k=3, n_newex=100, n_proto=50, auc_items=200, frac=0.90,
    material_frac=0.10, margin_frac=0.05, worsens_ratio=1.25, not_worse_ratio=1.10, min_seeds=4,
    overlap_lo=15.0, overlap_hi=19.0, auc_bar=0.95, specificity_ratio=0.5,
    win_mem=50, recall_bar=0.80, spurious_of_A=0.5, joint_missing=40, joint_intrusions=10,
)
DIGEST = record.digest(CONTRACT)
CONTRACT_FROZEN_AT = "bc28cd9"
CONTRACT_PATH = "docs/plant2/P2-E5-structured-items.md"
VECTOR_PARTS = ("C1", "C2", "C3", "C4_recall", "C4_spurious", "S2", "S3", "S4")


def stream(seed, *key):
    return e1.stream(seed, *key)


# ---------------------------------------------------------------- the family generator (contract: streams and draws)

class _GenState:
    """Stands in for numpy's bit_generator so P2-E4's state_digest can hash the generator's position."""

    def __init__(self, owner):
        self._o = owner

    @property
    def state(self):
        o = self._o
        return dict(generator="p2e5_family", seed=o.seed, s=o.s, F=o.F, pooled=o.pooled, k=o.k)


def prototypes(seed, m, a, F):
    r = stream(seed, PROTO, F)
    return [np.sort(r.choice(m, a, replace=False)) for _ in range(F)]


def exemplar_from(r, P, m, s, a):
    """One exemplar from generator r: a - s of P's lines and s lines outside P (nested across s for the same draws)."""
    pp = r.permutation(P)
    po = r.permutation(np.setdiff1d(np.arange(m), P))
    return np.sort(np.concatenate([pp[:a - s], po[:s]]))


class FamilyGen:
    """The injected `_pat`: exemplar k (1-based) of family k mod F, drawn from (seed, 21, F, k), or the pooled control's
    exemplar k from (seed, 23, k). Only `choice(m, a, replace=False)` is used by the learning code."""

    def __init__(self, seed, m, a, s, F, pooled=False):
        self.seed, self.m, self.a, self.s, self.F, self.pooled = seed, m, a, s, F, pooled
        self.protos = prototypes(seed, m, a, F)
        self.union = np.unique(np.concatenate(self.protos))
        self.k = 0
        self.fam = []
        self.bit_generator = _GenState(self)

    def family(self, k):
        return k % self.F

    def exemplar(self, k):
        if k < 1:
            raise ValueError("exemplar index k starts at 1 (k = 0 aliases the stream key)")
        f = self.family(k)
        if self.pooled:
            r = stream(self.seed, POOLED, k)
            d = r.choice(self.union, self.a - self.s, replace=False)
            pool = np.setdiff1d(np.arange(self.m), np.union1d(self.protos[f], d))
            return np.sort(np.concatenate([d, r.choice(pool, self.s, replace=False)]))
        return exemplar_from(stream(self.seed, EXEMPLAR, self.F, k), self.protos[f], self.m, self.s, self.a)

    def choice(self, m, a, replace=False):
        if m != self.m or a != self.a or replace:
            raise ValueError("the family generator only draws items of the configured size without replacement")
        self.k += 1
        self.fam.append(self.family(self.k))
        return self.exemplar(self.k)


def make_gen(arm, c, seed):
    spec = ARM_SPEC[arm]
    if spec is None:
        return None
    return FamilyGen(seed, c["m"], c["a"], spec["s"], spec["F"], spec.get("pooled", False))


def block_cues(c, seed, M, F, s):
    """The reported cue block at load M (stream (seed, 22, M), one generator used in order); returns (cues, generator)."""
    protos = prototypes(seed, c["m"], c["a"], F)
    r = stream(seed, BLOCK_CUES, M)
    a = c["a"]
    cues = []
    for j in range(c["n_newex"]):
        f = j % F
        ex = exemplar_from(r, protos[f], c["m"], s, a)
        mk = np.sort(r.choice(a, a // 2, replace=False))
        cues.append(dict(kind="newex", family=f, item=ex, cue=ex[mk]))
    for j in range(c["n_proto"]):
        f = j % F
        mk = np.sort(r.choice(a, a // 2, replace=False))
        cues.append(dict(kind="proto", family=f, item=protos[f], cue=protos[f][mk]))
    return cues, r


# ---------------------------------------------------------------- read-only capture of learning-time memory spikes

class CaptureMixin:
    """Wraps net.step for one learning episode, around the inherited learn_one (neither copied nor changed); the
    wrapper makes no draws, changes no state, and is removed in a finally clause so deep copies never carry it."""

    def _init_capture(self):
        self.cont_cells, self.cont_counts, self.cont_first, self.learn_raster = [], [], [], []

    def learn_one(self):
        cap = []
        orig = self.net.step

        def step(rng):
            sp = orig(rng)
            cap.append(sp["mem"].copy())
            return sp
        self.net.step = step
        try:
            super().learn_one()
        finally:
            del self.net.step
        c, n = self.c, self.c["n"]
        if len(cap) != c["t_item"] + c["t_cont"]:
            raise RuntimeError(f"episode had {len(cap)} steps, expected {c['t_item'] + c['t_cont']}")
        counts = np.zeros(n, np.int64)
        first = np.full(n, -1, np.int64)
        for t, s in enumerate(cap[-c["t_cont"]:]):  # the continuation: the last t_cont steps, loop index t = 0..49
            if s.size:
                counts[s] += 1
                new = s[first[s] < 0]
                first[new] = t
        cells = np.flatnonzero(counts)
        self.cont_cells.append(cells)
        self.cont_counts.append(counts[cells])
        self.cont_first.append(first[cells])
        parts = [t * n + s.astype(np.int64) for t, s in enumerate(cap) if s.size]
        self.learn_raster.append(np.concatenate(parts) if parts else np.empty(0, np.int64))


class E5(CaptureMixin, e3.E3):
    def __init__(self, cfg, seed, gen=None):
        super().__init__(cfg, seed)
        if gen is not None:
            self._pat = gen
        self._init_capture()


class OnlineE5(CaptureMixin, e4.Online):
    def __init__(self, cfg, seed, gen=None):
        super().__init__(cfg, seed)
        if gen is not None:
            self._pat = gen
        self._init_capture()


def capture_ok(e, M):
    """Validity 7a: R(x) equals the cells with at least 1 captured continuation spike, for every x <= M."""
    return bool(len(e.R) >= M and all(np.array_equal(e.R[i], e.cont_cells[i]) for i in range(M)))


def store_from(e, M, k=None, cells=None):
    """Feedback store written from R_k(x) (cells with >= k continuation spikes) x E(x), items 1..M."""
    m = e.c["m"]
    s = BinarySynapses(e.c["n"], m)
    parts = []
    for i in range(M):
        R = e.cont_cells[i][e.cont_counts[i] >= k] if cells is None else cells[i]
        if R.size and e.E[i].size:
            parts.append((R[:, None] * m + e.E[i][None, :]).ravel())
    if parts:
        s.add(np.concatenate(parts))
    return s


def permuted_store(e, M, fam):
    """x's responders write onto pi(x)'s eligible lines, pi a within-family derangement (stream (seed, 24, M))."""
    r = stream(e.seed, PI, M)
    pi = np.arange(M)
    F = max(fam[:M]) + 1 if M else 0
    for f in range(F):
        idx = np.array([i for i in range(M) if fam[i] == f], np.int64)
        if idx.size < 2:
            continue
        while True:
            p = r.permutation(idx)
            if not np.any(p == idx):
                break
        pi[idx] = p
    m = e.c["m"]
    s = BinarySynapses(e.c["n"], m)
    s.add(np.concatenate([(e.R[i][:, None] * m + e.E[pi[i]][None, :]).ravel() for i in range(M)
                          if e.R[i].size and e.E[pi[i]].size]))
    return s, pi


# ---------------------------------------------------------------- readout helpers (P2-E3's arithmetic, extended outputs)

class FirstLines:
    """A replay `trace` sink keeping, per scored cue, each rec line's first spike tick inside the cue's scoring window
    (arm 0 only)."""

    def __init__(self, onsets, window, n_ticks):
        self.cue_of = np.full(n_ticks, -1, np.int64)
        for i, on in enumerate(onsets):
            self.cue_of[on:on + window] = i
        self.onsets = list(onsets)
        self.first = [dict() for _ in onsets]

    def extend(self, it):
        cue_of, first, onsets = self.cue_of, self.first, self.onsets
        for t, a, j in it:
            if a:
                continue
            i = cue_of[t]
            if i >= 0:
                d = first[i]
                if j not in d:
                    d[j] = t - onsets[i]

    def lines(self, i):
        d = self.first[i]
        return np.array(sorted(d), np.int64), np.array([d[j] for j in sorted(d)], np.int64)


def readout_full(e, M, raster, n_ticks, onsets, J, g, store=None, pi=None, trace=None):
    """e3.readout with the same arguments, also returning the replay counts and the cue list (one replay)."""
    c = e.c
    store = e.fb if store is None else store
    cues = e3.build_cues(e, M, onsets, pi=pi)
    indptr, post = store.csr()
    J, g = np.asarray(J, float), np.asarray(g, float)
    res, lat, oow = replay(raster, n_ticks, indptr, post, c["m"], J, g, cues, window=c["rec_window"], short=e3.SHORT,
                           span=c["t_cue"] + c["t_gap"], trace=trace)
    arms = e3.score(res, lat, cues, c["n_old"], len(J))
    for a, d in enumerate(arms):
        d.update(J=float(J[a]), g=float(g[a]), out_of_window_spikes_per_cue=float(oow[a] / len(cues)))
    return arms, res, cues


def cues_count(frac_value, n):
    return int(round(frac_value * n))


def per_cue_joint(res, cues, c):
    h = np.array([q["kind"] == "half" for q in cues])
    miss = res["missing"][h][:, 0]
    intr = res["total"][h][:, 0] - res["item"][h][:, 0]
    return (miss >= c["joint_missing"]) & (intr < c["joint_intrusions"])


def per_cue_index(out, e, c):
    """Index pass per half cue (recall >= 0.8 at 50 ms and spurious < 0.5|A|), in cued order."""
    rec = np.array(out["recall"][50])
    sp = np.array(out["spurious"])
    A = np.array(out["A_size"])
    return (rec >= c["recall_bar"]) & (sp < c["spurious_of_A"] * A)


def bits(x):
    return "".join("1" if v else "0" for v in np.asarray(x, bool))


def grid_arrays(c):
    Js = np.array([J for J in c["grid_J"] for _ in c["grid_g"]], float)
    gs = np.array([g for _ in c["grid_J"] for g in c["grid_g"]], float)
    return Js, gs


def grid_summary(arms, c, n_half, n_old, n_novel):
    """Frozen point, grid best (maximum joint, first maximum in grid order) and passing points, in cues."""
    joints = [cues_count(a["joint"], n_half) for a in arms]
    i_best = int(np.argmax(joints))
    fro = [a for a in arms if abs(a["J"] - c["J_fb"]) < 1e-9 and abs(a["g"] - c["g"]) < 1e-9][0]
    bar = lambda n: power.bar_count(n, c["frac"])
    passing = sum(cues_count(a["joint"], n_half) >= bar(n_half) and cues_count(a["D3"], n_novel) >= bar(n_novel)
                  and cues_count(a["D4"], n_old) >= bar(n_old) for a in arms)
    keep = ("joint", "D1", "D2", "D3", "D4", "J", "g", "intrusions_median")
    return dict(frozen={k: fro[k] for k in keep}, frozen_cues=cues_count(fro["joint"], n_half),
                best={k: arms[i_best][k] for k in keep}, best_cues=joints[i_best], passing_points=int(passing))


# ---------------------------------------------------------------- one P2-E3-protocol timeline

def test_copy(main, M, block):
    """P2-E3's test on a deep copy, then (optionally) the reported block as a separate present() call."""
    e = copy.deepcopy(main)
    fwd, fb = e.store.keys.copy(), e.fb.keys.copy()
    out, raster, n_ticks, onsets, drift = e3.run_phase(e, M)
    gated_raster = {t: s for t, s in raster.items() if t < n_ticks}
    n_gated = len(onsets)
    blk = None
    if block is not None:
        cues, r = block
        resp = e.present([q["cue"] for q in cues], r)
        blk = dict(cues=cues, resp=resp, raster=dict(e._raster), n_ticks=e.net.t - e._t0, onsets=list(e._onsets[n_gated:]))
    unchanged = bool(np.array_equal(fwd, e.store.keys) and np.array_equal(fb, e.fb.keys))
    return dict(e=e, out=out, raster=gated_raster, n_ticks=n_ticks, onsets=list(onsets), drift=drift, block=blk,
                unchanged=unchanged)


def criteria_vector(mem_out, main_arm, n_half, n_novel, n_old, c):
    cr = mem_out["criteria"]
    bar = lambda n: power.bar_count(n, c["frac"])
    counts = dict(C1=cues_count(cr["C1_frac"], n_half), C2=cues_count(cr["C2_frac"], n_half),
                  C3=cues_count(cr["C3_frac"], n_novel), C4_recall=cues_count(cr["C4_recall_frac"], n_old),
                  C4_spurious=cues_count(cr["C4_spurious_frac"], n_old), S2=cues_count(main_arm["joint"], n_half),
                  S3=cues_count(main_arm["D3"], n_novel), S4=cues_count(main_arm["D4"], n_old))
    n_of = dict(C1=n_half, C2=n_half, C3=n_novel, C4_recall=n_old, C4_spurious=n_old, S2=n_half, S3=n_novel, S4=n_old)
    return {k: bool(counts[k] >= bar(n_of[k])) for k in VECTOR_PARTS}, counts


def run_timeline(arm, c, seed, log, keep=False):
    """Learn to each gated load on the P2-E3 protocol and test a copy. Returns (per-load results, main line, gen)."""
    gen = make_gen(arm, c, seed)
    main = E5(c, seed, gen)
    plain = e1.E1(dict(c, J=e1.CONTRACT["J"]), seed)
    if gen is not None:
        plain._pat = make_gen(arm, c, seed)
    loads = {}
    t0 = time.time()
    for M in c["gate_M"]:
        main.learn(M)
        before = (main.store.keys.copy(), main.fb.keys.copy(), main.mem.vbar.copy())
        if arm in OWN_BLOCK:
            spec = ARM_SPEC[arm]
            block = block_cues(c, seed, M, spec["F"], spec["s"])
        else:
            block = block_cues(c, seed, M, ARM_SPEC["main"]["F"], ARM_SPEC["main"]["s"])
        T = test_copy(main, M, block)
        main_untouched = bool(np.array_equal(before[0], main.store.keys) and np.array_equal(before[1], main.fb.keys)
                              and np.array_equal(before[2], main.mem.vbar))
        plain.learn(M)
        T.update(M=M, main_untouched=main_untouched, fwd_equals_p2e1=e3.digest(plain.store.keys) == e3.digest(main.store.keys),
                 fb_store=BinarySynapses(c["n"], c["m"]))
        T["fb_store"].keys = main.fb.keys.copy()
        T["fb_plateau"] = BinarySynapses(c["n"], c["m"])
        T["fb_plateau"].keys = main.fb_plateau.keys.copy()
        T["capture_ok"] = capture_ok(main, M)
        T["fb_union_ok"] = e4.fb_union_ok(main)
        T["r1_equals_main"] = e3.digest(store_from(main, M, k=1).keys) == e3.digest(main.fb.keys)
        T["learning"] = e3.learning_summary(main, M)
        T["fwd_digest"], T["fb_digest"] = e3.digest(main.store.keys), e3.digest(main.fb.keys)
        T["A_digest"] = hashlib.sha256(b"".join(a.astype(np.int64).tobytes() for a in main.A[:M])).hexdigest()[:16]
        loads[M] = T
        log(f"seed {seed} {arm} M={M}: learned and tested ({time.time() - t0:.0f} s)")
    return loads, main, gen


def arm_validity(c, loads, main):
    v = {}
    for M, T in loads.items():
        v[str(M)] = dict(fwd_equals_p2e1=bool(T["fwd_equals_p2e1"]), stores_unchanged_by_tests=bool(T["unchanged"]),
                         main_untouched=bool(T["main_untouched"]), converged=bool(T["drift"][0] <= e3.e2.CONVERGE_BAR_MV),
                         capture_ok=bool(T["capture_ok"]), fb_union_ok=bool(T["fb_union_ok"]),
                         r1_equals_main=bool(T["r1_equals_main"]))
    g1 = max(loads)
    v["mean_elig_frac"] = float(np.mean(main.learn_log["elig_frac"][:g1]))
    v["mean_A"] = float(np.mean([a.size for a in main.A[:g1]]))
    v["elig_ok"] = v["mean_elig_frac"] >= e1.BARS["elig_valid"]
    v["mean_A_ok"] = c.get("mean_A_lo", e1.BARS["mean_A_lo"]) <= v["mean_A"] <= c.get("mean_A_hi", e1.BARS["mean_A_hi"])
    return v


def load_valid(v, M):
    L = v[str(M)]
    return bool(all(L.values()) and v["elig_ok"] and v["mean_A_ok"])


# ---------------------------------------------------------------- the gated arm

def sibling_overlap(items, fam, M):
    """Validity 6: mean |x ∩ y| over all within-family pairs among items 1..M."""
    tot, n = 0.0, 0
    for f in sorted(set(fam[:M])):
        idx = [i for i in range(M) if fam[i] == f]
        if len(idx) < 2:
            continue
        m = max(int(items[i].max()) for i in idx) + 1
        X = np.zeros((len(idx), m), np.int32)
        for r, i in enumerate(idx):
            X[r, items[i]] = 1
        O = X @ X.T
        iu = np.triu_indices(len(idx), 1)
        tot += float(O[iu].sum())
        n += iu[0].size
    return tot / n if n else float("nan")


def persist(seed, gated, main, loads, c):
    """Learning raster, E, A, R, continuation counts and first ticks, test rasters (gated arm), by path and sha256."""
    kind = "gated" if gated else "explore"
    path = record.cache_dir("p2_e5") / f"seed{seed}_{kind}_{record.now().replace(':', '')}.npz"
    g1 = max(loads)
    arrs = {}

    def pack(name, lst):
        arrs[name] = np.concatenate(lst) if lst else np.empty(0, np.int64)
        arrs[name + "_offsets"] = np.cumsum([0] + [x.size for x in lst]).astype(np.int64)
    pack("learn_raster", main.learn_raster[:g1])
    pack("E", main.E[:g1])
    pack("A", main.A[:g1])
    pack("R", main.R[:g1])
    pack("cont_cells", main.cont_cells[:g1])
    pack("cont_counts", main.cont_counts[:g1])
    pack("cont_first", main.cont_first[:g1])
    for M, T in loads.items():
        ticks = sorted(T["block"]["raster"]) if T["block"] else sorted(T["raster"])
        R = T["block"]["raster"] if T["block"] else T["raster"]
        pack(f"test_raster_{M}", [t * c["n"] + R[t].astype(np.int64) for t in ticks])
        arrs[f"test_n_ticks_gated_{M}"] = np.array([T["n_ticks"]])
        arrs[f"test_onsets_{M}"] = np.array(T["onsets"] + (T["block"]["onsets"] if T["block"] else []), np.int64)
    buf = io.BytesIO()
    np.savez_compressed(buf, **arrs)
    data = buf.getvalue()
    path.write_bytes(data)
    return dict(path=str(path), sha256_file=hashlib.sha256(data).hexdigest())


def run_gated_arm(c, seed, gated, results_path, log):
    t0 = time.time()
    loads, main, gen = run_timeline("main", c, seed, log)
    rec_loads, vec, counts = {}, {}, {}
    n_half = c["n_old"] + c["n_rand"]
    for M, T in loads.items():
        e = T["e"]
        J, g = np.array([c["J_fb"]]), np.array([c["g"]])
        arms, res, cues = readout_full(e, M, T["raster"], T["n_ticks"], T["onsets"], J, g)
        T["main_res"], T["cues"], T["main_arm"] = res, cues, arms[0]
        vec[str(M)], counts[str(M)] = criteria_vector(T["out"], arms[0], n_half, c["n_novel"], min(c["n_old"], M), c)
        rec_loads[str(M)] = dict(memory=e3.memory_summary(T["out"]), main=arms[0], converge_mv=T["drift"][0],
                                 drift_signed_mv=T["drift"][1], learning=T["learning"], fwd_digest=T["fwd_digest"],
                                 fb_digest=T["fb_digest"], A_digest=T["A_digest"], vector=vec[str(M)], counts=counts[str(M)],
                                 per_cue=dict(joint=bits(per_cue_joint(res, cues, c)), index=bits(per_cue_index(T["out"], e, c))))
        log(f"seed {seed} main M={M}: C1 {T['out']['criteria']['C1_frac']:.3f} C2 {T['out']['criteria']['C2_frac']:.3f} "
            f"C3 {T['out']['criteria']['C3_frac']:.3f} C4 {T['out']['criteria']['C4_recall_frac']:.3f}/"
            f"{T['out']['criteria']['C4_spurious_frac']:.3f} | joint {arms[0]['joint']:.3f} D3 {arms[0]['D3']:.3f} "
            f"D4 {arms[0]['D4']:.3f} | conv {T['drift'][0]:.3f} ({T['drift'][1]:+.3f}) mV")
    g1 = max(loads)
    v = arm_validity(c, loads, main)
    T1 = loads[g1]
    sh = readout_full(T1["e"], g1, T1["raster"], T1["n_ticks"], T1["onsets"], np.array([c["J_fb"]]), np.array([c["g"]]),
                      store=e3.shuffled_store(T1["e"], g1))[0][0]
    v["shuffled_joint_M"] = sh["joint"]
    v["shuffled_ok"] = bool(sh["joint"] < c["frac"])
    v["sibling_overlap_mean"] = sibling_overlap(main.items, gen.fam, g1)
    v["overlap_ok"] = bool(c["overlap_lo"] <= v["sibling_overlap_mean"] <= c["overlap_hi"])
    valid = bool(all(load_valid(v, M) for M in loads) and v["shuffled_ok"] and v["overlap_ok"])
    passed = bool(valid and all(all(x.values()) for x in vec.values()))
    files = persist(seed, gated, main, loads, c)
    rec = dict(experiment="P2-E5", kind="kill_test_seed" if gated else "exploration_seed", seed=seed, gated=gated,
               contract_digest=record.digest(c), loads=rec_loads, validity=v, valid=valid, vector=vec, passed=passed,
               persistence=files, timestamp=record.now(), git=record.git_state(), runtime=record.runtime(),
               wall_s=round(time.time() - t0, 1))
    record.append(rec, results_path)
    log(f"seed {seed} ({'gated' if gated else 'exploration'}): valid={valid} passed={passed} wall {rec['wall_s']} s")
    return rec, loads, main, gen


# ---------------------------------------------------------------- same-raster diagnostics on the gated arm (A, C, F, G)

def auc(pos, neg, higher=True):
    """P(pos > neg) + 0.5 P(pos = neg) over all pairs (pos < neg when higher is False)."""
    pos, neg = np.asarray(pos), np.asarray(neg)
    if not pos.size or not neg.size:
        return None
    if not higher:
        pos, neg = -pos, -neg
    vals = np.union1d(pos, neg)
    pc = np.array([(pos == x).sum() for x in vals], float)
    nc = np.array([(neg == x).sum() for x in vals], float)
    below = np.concatenate([[0.0], np.cumsum(nc)[:-1]])
    return float((pc * (below + 0.5 * nc)).sum() / (pos.size * neg.size))


def activity_identity(e, M, c):
    lo = max(0, M - c["auc_items"])
    pc, nc, pf, nf = [], [], [], []
    for i in range(lo, M):
        inA = np.isin(e.cont_cells[i], e.A[i])
        pc.append(e.cont_counts[i][inA])
        nc.append(e.cont_counts[i][~inA])
        pf.append(e.cont_first[i][inA])
        nf.append(e.cont_first[i][~inA])
    pc, nc, pf, nf = (np.concatenate(x) if x else np.empty(0, np.int64) for x in (pc, nc, pf, nf))
    hist = lambda x: np.bincount(x, minlength=c["t_cont"] + 1).tolist()
    return dict(items=[lo + 1, M], n_pos=int(pc.size), n_neg=int(nc.size), count_auc=auc(pc, nc),
                first_spike_auc=auc(pf, nf, higher=False), count_hist_pos=hist(pc), count_hist_neg=hist(nc),
                mean_count_pos=float(pc.mean()) if pc.size else None, mean_count_neg=float(nc.mean()) if nc.size else None)


def mem_first(raster, onset, window, n):
    first = np.full(n, -1, np.int64)
    for k in range(window):
        s = raster.get(onset + k)
        if s is not None and s.size:
            s = s[first[s] < 0]
            first[s] = k
    return first


def line_classes(gen, items, i, M):
    """Exclusive classes of non-item lines for cued item i (0-based) at load M."""
    m = gen.m
    f = gen.fam[i]
    item = items[i]
    P = gen.protos[f]
    sib = [y for y in range(M) if gen.fam[y] == f and y != i]
    U_e = np.unique(np.concatenate([items[y] for y in sib if y < i])) if any(y < i for y in sib) else np.empty(0, np.int64)
    U_l = np.unique(np.concatenate([items[y] for y in sib if y > i])) if any(y > i for y in sib) else np.empty(0, np.int64)
    rest = np.setdiff1d(np.setdiff1d(np.arange(m), item), P)
    cls = dict(proto_not_x=np.setdiff1d(P, item),
               later_only=np.intersect1d(np.setdiff1d(U_l, U_e), rest),
               earlier_only=np.intersect1d(np.setdiff1d(U_e, U_l), rest),
               both=np.intersect1d(np.intersect1d(U_e, U_l), rest),
               other=np.setdiff1d(rest, np.union1d(U_e, U_l)))
    return cls, P, sib


def contamination(T, gen, M, c, fl_main, fl_plat, fl_perm, store_main):
    """Part F: intrusion classes (main and plateau-set), own-cell share, spurious memory cells, label-permuted fractions."""
    e, cues = T["e"], T["cues"]
    items = e.items
    half = [(k, q) for k, q in enumerate(cues) if q["kind"] == "half"]
    names = ("proto_not_x", "later_only", "earlier_only", "both", "other")
    stats = {s: {nm: [] for nm in names} for s in ("main", "plateau")}
    rates = {s: {nm: [] for nm in names} for s in ("main", "plateau")}
    own_share, spur_n, spur_sib, spur_proto, spur_spec = [], [], [], [], []
    perm = dict(main_proto=[], main_spec=[], perm_proto=[], perm_spec=[])
    indptr, post = store_main.csr()
    n = c["n"]
    half_resp = T["out"]["_half"]
    for h, (k, q) in enumerate(half):
        i = q["index"]
        cls, P, sib = line_classes(gen, items, i, M)
        for s, fl in (("main", fl_main), ("plateau", fl_plat)):
            G, _ = fl.lines(k)
            intr = np.setdiff1d(G, q["item"])
            for nm in names:
                cnt = int(np.isin(intr, cls[nm]).sum())
                stats[s][nm].append(cnt)
                rates[s][nm].append(cnt / cls[nm].size if cls[nm].size else 0.0)
        # own-cell share of candidate inputs to the main store's intrusion lines
        G, Gt = fl_main.lines(k)
        is_intr = ~np.isin(G, q["item"])
        if is_intr.any():
            fm = mem_first(T["raster"], q["onset"], c["rec_window"], n)
            cells = np.flatnonzero(fm >= 0)
            line_t = dict(zip(G[is_intr].tolist(), Gt[is_intr].tolist()))
            tot = own = 0
            A = e.A[i]
            for cell in cells:
                tgt = post[indptr[cell]:indptr[cell + 1]]
                hit = [j for j in tgt[np.isin(tgt, G[is_intr])].tolist() if fm[cell] <= line_t[j] - 1]
                tot += len(hit)
                if np.isin(cell, A):
                    own += len(hit)
            if tot:
                own_share.append(own / tot)
        # spurious memory cells under the half cue (forward store)
        hc, ht = half_resp[h]
        A = e.A[i]
        sp = np.setdiff1d(hc[ht < c["win_mem"]], A)
        spur_n.append(int(sp.size))
        if sp.size:
            sibA = np.unique(np.concatenate([e.A[y] for y in sib])) if sib else np.empty(0, np.int64)
            spur_sib.append(float(np.isin(sp, sibA).mean()))
            cue = q["cue"]
            cue_p, cue_s = np.intersect1d(cue, P), np.setdiff1d(cue, P)
            keys = e.store.keys
            spur_proto.append(float(np.mean([np.isin(cue_p * n + x, keys).sum() for x in sp])))
            spur_spec.append(float(np.mean([np.isin(cue_s * n + x, keys).sum() for x in sp])))
        # label-permuted against main: regenerated fractions of the missing prototype and item-specific lines
        miss = q["missing"]
        mp, ms = np.intersect1d(miss, P), np.setdiff1d(miss, P)
        Gp, _ = fl_perm.lines(k)
        for tag, GG in (("main", G), ("perm", Gp)):
            perm[f"{tag}_proto"].append(float(np.isin(mp, GG).mean()) if mp.size else None)
            perm[f"{tag}_spec"].append(float(np.isin(ms, GG).mean()) if ms.size else None)
    summ = lambda x: dict(mean=float(np.mean(x)), median=float(np.median(x))) if len(x) else None
    out = dict(intrusions={s: {nm: summ(stats[s][nm]) for nm in names} for s in stats},
               per_line_rate={s: {nm: float(np.mean(rates[s][nm])) for nm in names} for s in rates})
    for s in rates:
        other = out["per_line_rate"][s]["other"]
        out.setdefault("contamination_ratio", {})[s] = {nm: (out["per_line_rate"][s][nm] / other if other > 0 else None)
                                                         for nm in names if nm != "other"}
    tot_main = np.array([sum(stats["main"][nm][h] for nm in names) for h in range(len(half))], float)
    tot_plat = np.array([sum(stats["plateau"][nm][h] for nm in names) for h in range(len(half))], float)
    out["intrusion_ratio_main_to_plateau"] = float((np.median(tot_main) + 1) / (np.median(tot_plat) + 1))
    out["own_cell_share"] = dict(median=float(np.median(own_share)) if own_share else None,
                                 mean=float(np.mean(own_share)) if own_share else None, n_cues=len(own_share))
    out["spurious"] = dict(per_cue_mean=float(np.mean(spur_n)), sibling_plateau_share=summ(spur_sib),
                           strong_from_cue_prototype=summ(spur_proto), strong_from_cue_specific=summ(spur_spec))
    out["label_permuted"] = {k: (float(np.mean([x for x in v if x is not None])) if any(x is not None for x in v) else None)
                             for k, v in perm.items()}
    return out


def block_stats(T, gen_items, gen_fam, protos, M, c, store):
    """Part G per cue kind, read through `store` on the copy's full raster."""
    blk = T["block"]
    e = T["e"]
    cues = []
    for q, on in zip(blk["cues"], blk["onsets"]):
        cues.append(dict(kind=q["kind"], item=q["item"], cue=q["cue"], missing=np.setdiff1d(q["item"], q["cue"]),
                         other_missing=np.empty(0, np.int64), onset=on, family=q["family"]))
    indptr, post = store.csr()
    fl = FirstLines([q["onset"] for q in cues], c["rec_window"], blk["n_ticks"])
    replay(blk["raster"], blk["n_ticks"], indptr, post, c["m"], np.array([c["J_fb"]]), np.array([c["g"]]), cues,
           window=c["rec_window"], short=e3.SHORT, span=c["t_cue"] + c["t_gap"], trace=fl)
    out = {"newex": [], "proto": []}
    for k, q in enumerate(cues):
        G, _ = fl.lines(k)
        hc, ht = blk["resp"][k]
        resp = int((ht < c["win_mem"]).sum())
        f = q["family"]
        P = protos[f] if protos is not None else np.empty(0, np.int64)
        sib = [y for y in range(M) if gen_fam is not None and gen_fam[y] == f]
        U = np.unique(np.concatenate([gen_items[y] for y in sib])) if sib else np.empty(0, np.int64)
        sib_only = np.setdiff1d(np.setdiff1d(U, P), q["item"])
        if q["kind"] == "newex":
            miss = q["missing"]
            mp, ms = np.intersect1d(miss, P), np.setdiff1d(miss, P)
            lacks = np.setdiff1d(P, q["item"])
            out["newex"].append(dict(responders=resp, lines=int(G.size),
                                     missing_proto_frac=float(np.isin(mp, G).mean()) if mp.size else None,
                                     lacking_proto_frac=float(np.isin(lacks, G).mean()) if lacks.size else None,
                                     sibling_only_lines=int(np.isin(G, sib_only).sum()),
                                     missing_specific_frac=float(np.isin(ms, G).mean()) if ms.size else None,
                                     quiet=bool(G.size < e3.NOVEL_LINES)))
        else:
            intr = np.setdiff1d(G, P)
            out["proto"].append(dict(responders=resp, lines=int(G.size),
                                     missing_proto_frac=float(np.isin(q["missing"], G).mean()) if q["missing"].size else None,
                                     intr_sibling_specific=int(np.isin(intr, sib_only).sum()),
                                     intr_other=int((~np.isin(intr, sib_only)).sum())))

    def agg(rows):
        if not rows:
            return None
        keys = [k for k in rows[0] if k != "quiet"]
        d = {}
        for k in keys:
            xs = [r[k] for r in rows if r[k] is not None]
            d[k] = dict(mean=float(np.mean(xs)), median=float(np.median(xs))) if xs else None
        if "quiet" in rows[0]:
            d["p_fewer_than_10_lines"] = float(np.mean([r["quiet"] for r in rows]))
        return d
    return {k: agg(v) for k, v in out.items()}


def gated_diagnostics(c, seed, gated, loads, main, gen, results_path, log):
    t0 = time.time()
    out = dict(experiment="P2-E5", kind="reported_arm", arm="gated_diagnostics", seed=seed, gated=gated,
               contract_digest=record.digest(c), loads={})
    Js, gs = grid_arrays(c)
    n_half, n_novel = c["n_old"] + c["n_rand"], c["n_novel"]
    J1, g1 = np.array([c["J_fb"]]), np.array([c["g"]])
    for M, T in loads.items():
        e = T["e"]
        n_old = min(c["n_old"], M)
        r3 = store_from(main, M, k=c["grid_k"])
        grids = {}
        for name, st in (("main", T["fb_store"]), ("plateau", T["fb_plateau"]), ("R3", r3)):
            arms = readout_full(e, M, T["raster"], T["n_ticks"], T["onsets"], Js, gs, store=st)[0]
            grids[name] = grid_summary(arms, c, n_half, n_old, n_novel)
        rk = {}
        for k in c["R_k"]:
            a = readout_full(e, M, T["raster"], T["n_ticks"], T["onsets"], J1, g1, store=store_from(main, M, k=k))[0][0]
            rk[str(k)] = dict(joint=a["joint"], D1=a["D1"], D2=a["D2"], D4=a["D4"], cues=cues_count(a["joint"], n_half))
        fls = {}
        for name, st, pi in (("main", T["fb_store"], None), ("plateau", T["fb_plateau"], None)):
            fl = FirstLines(T["onsets"], c["rec_window"], T["n_ticks"])
            readout_full(e, M, T["raster"], T["n_ticks"], T["onsets"], J1, g1, store=st, trace=fl)
            fls[name] = fl
        ps, pi = permuted_store(e, M, gen.fam)
        fl = FirstLines(T["onsets"], c["rec_window"], T["n_ticks"])
        perm_arm = readout_full(e, M, T["raster"], T["n_ticks"], T["onsets"], J1, g1, store=ps, pi=pi, trace=fl)[0][0]
        fls["perm"] = fl
        F_ = contamination(T, gen, M, c, fls["main"], fls["plateau"], fls["perm"], T["fb_store"])
        F_["label_permuted_arm"] = dict(joint=perm_arm["joint"], D1=perm_arm["D1"], D2=perm_arm["D2"])
        G_ = block_stats(T, main.items, gen.fam, gen.protos, M, c, T["fb_store"])
        out["loads"][str(M)] = dict(grid=grids, R_k=rk, activity=activity_identity(main, M, c), contamination=F_,
                                    block=G_, n_half=n_half)
        log(f"seed {seed} diagnostics M={M}: plateau best {grids['plateau']['best']['joint']:.3f} main best "
            f"{grids['main']['best']['joint']:.3f} R3 best {grids['R3']['best']['joint']:.3f} | count AUC "
            f"{out['loads'][str(M)]['activity']['count_auc']} ({time.time() - t0:.0f} s)")
    out.update(timestamp=record.now(), git=record.git_state(), runtime=record.runtime(), wall_s=round(time.time() - t0, 1))
    record.append(out, results_path)
    return out


# ---------------------------------------------------------------- other P2-E3-protocol arms (Part E)

def p2e3_gate(mem_out, main_arm, n_half, n_novel, n_old, c):
    vec, _ = criteria_vector(mem_out, main_arm, n_half, n_novel, n_old, c)
    return bool(all(vec.values()))


def run_p2e3_arm(arm, c, seed, gated, results_path, log, main_gen=None):
    t0 = time.time()
    loads, main, gen = run_timeline(arm, c, seed, log)
    v = arm_validity(c, loads, main)
    n_half, n_novel = c["n_old"] + c["n_rand"], c["n_novel"]
    J1, g1 = np.array([c["J_fb"]]), np.array([c["g"]])
    out = dict(experiment="P2-E5", kind="reported_arm", arm=arm, seed=seed, gated=gated, contract_digest=record.digest(c),
               validity=v, loads={})
    for M, T in loads.items():
        e = T["e"]
        n_old = min(c["n_old"], M)
        arms, res, cues = readout_full(e, M, T["raster"], T["n_ticks"], T["onsets"], J1, g1)
        pl = readout_full(e, M, T["raster"], T["n_ticks"], T["onsets"], J1, g1, store=T["fb_plateau"])[0][0]
        vec, counts = criteria_vector(T["out"], arms[0], n_half, n_novel, n_old, c)
        L = dict(memory=e3.memory_summary(T["out"]), main=arms[0], plateau=pl, vector=vec, counts=counts,
                 plateau_cues=cues_count(pl["joint"], n_half), converge_mv=T["drift"][0], drift_signed_mv=T["drift"][1],
                 learning=T["learning"], A_digest=T["A_digest"], valid=load_valid(v, M),
                 per_cue=dict(joint=bits(per_cue_joint(res, cues, c)), index=bits(per_cue_index(T["out"], e, c))))
        if arm == "s100":
            L["p2e3_gate"] = p2e3_gate(T["out"], arms[0], n_half, n_novel, n_old, c)
        if T["block"] is not None:
            if arm in OWN_BLOCK:
                L["block"] = block_stats(T, main.items, gen.fam, gen.protos, M, c, T["fb_store"])
            else:  # pooled and s100: main's block; memory responders and total lines only
                blk = block_stats(T, main.items, None, None, M, c, T["fb_store"])
                L["block"] = {k: ({kk: vv for kk, vv in d.items() if kk in ("responders", "lines")} if d else None)
                              for k, d in blk.items()}
        out["loads"][str(M)] = L
        log(f"seed {seed} {arm} M={M}: joint {arms[0]['joint']:.3f} D4 {arms[0]['D4']:.3f} plateau {pl['joint']:.3f} | "
            f"C2 {T['out']['criteria']['C2_frac']:.3f} | valid {L['valid']}")
    out.update(timestamp=record.now(), git=record.git_state(), runtime=record.runtime(), wall_s=round(time.time() - t0, 1))
    record.append(out, results_path)
    return out


# ---------------------------------------------------------------- the online arm (Part D, and L_o for Part B)

def blob_check():
    """The reused files' blobs in the working tree equal their blobs in P2-E4's frozen tree."""
    def git(*a):
        return subprocess.run(["git", "-C", str(record.REPO), *a], capture_output=True, text=True).stdout.strip()
    out = {}
    for f in REUSED_FILES:
        frozen = git("rev-parse", f"{P2E4_TREE}:{f}")
        now = git("hash-object", f"plant2/{f}")
        out[f] = dict(frozen=frozen, now=now, same=bool(frozen) and frozen == now)
    return out


def run_online_arm(seed, gated, gated_fb, results_path, log, c4=None, c=CONTRACT):
    t0 = time.time()
    c4 = e4.CONTRACT if c4 is None else c4
    spec = ARM_SPEC["main"]
    gen = FamilyGen(seed, c4["m"], c4["a"], spec["s"], spec["F"])
    o = OnlineE5(c4, seed, gen)
    plain = e1.E1(dict(c4, J=e1.CONTRACT["J"]), seed)
    plain._pat = FamilyGen(seed, c4["m"], c4["a"], spec["s"], spec["F"])
    blobs = blob_check()
    out = dict(experiment="P2-E5", kind="reported_arm", arm="online", seed=seed, gated=gated, contract_digest=record.digest(c),
               online_contract_digest=record.digest(c4), blobs=blobs, loads={})
    for M in c4["gate_M"]:
        o.run_to(M)
        S = copy.deepcopy(o)
        d0 = e4.state_digest(S)
        crit = e4.block_criteria(o, M)
        A1, B = e4.twin_A(S, M, ref_store=gated_fb.get(M))
        tb = e4.twin_B(B, S, M)
        r3 = store_from(o, M, k=c["grid_k"])
        A2, _ = e4.twin_A(S, M, ref_store=r3)
        untouched = e4.state_digest(S) == d0
        plain.learn(M)
        n = tb["all"]["n"]
        mc_m, mc_c = tb["all"]["mcnemar_memory"], tb["all"]["mcnemar_content"]
        net_m, net_c = mc_m[1] - mc_m[0], mc_c[1] - mc_c[0]
        on_med = A1["main"]["intrusions_median"]
        ref = A1.get("swap_reference")
        v = dict(fwd_equals_p2e1=e3.digest(plain.store.keys) == e3.digest(S.store.keys),
                 elig_ok=float(np.mean(o.learn_log["elig_frac"][:M])) >= c4["elig_valid"],
                 mean_A_ok=c4["mean_A_lo"] <= float(np.mean([a.size for a in o.A[:M]])) <= c4["mean_A_hi"],
                 fb_union_ok=e4.fb_union_ok(S), capture_ok=capture_ok(o, M),
                 slot_checks_ok=bool(all(crit["slot_checks"].values()) and all(d["writes_ok"] for d in o.log if d["step"] <= M)),
                 audit_ok=not list(e4.realised_audit(o, M)), leak_ok=bool(crit["leak"]["ok"]), twins_untouched=bool(untouched),
                 blobs_ok=bool(all(b["same"] for b in blobs.values())), reference_present=ref is not None)
        valid = bool(all(v.values()))
        L = dict(validity=v, valid=valid, block=dict(rates=crit["rates"], per_kind=crit["per_kind"], offset_mv=crit["offset_mv"]),
                 twin_A=dict(online=A1["main"], reference=ref, plateau=A1["swap_plateau"], R3=A2.get("swap_reference"),
                             offset_settled=A1["offset_settled"], drift=A1["drift"], memory=A1["memory"]),
                 twin_B=tb, L_o=dict(net_memory=int(net_m), net_content=int(net_c), n=int(n), loss=int(max(0, net_m, net_c))),
                 ratio=(on_med + 1) / (ref["intrusions_median"] + 1) if ref is not None else None,
                 activity=activity_identity(o, M, c), responders=e4.responder_stats(o))
        out["loads"][str(M)] = L
        log(f"seed {seed} online M={M}: block C1 {crit['rates']['C1']:.3f} C2 {crit['rates']['C2']:.3f} joint "
            f"{crit['rates']['joint']:.3f} | twin A online {A1['main']['joint']:.3f} ref "
            f"{ref['joint'] if ref else None} | R {L['ratio']} | L_o {L['L_o']} | valid {valid} ({time.time() - t0:.0f} s)")
    out.update(timestamp=record.now(), git=record.git_state(), runtime=record.runtime(), wall_s=round(time.time() - t0, 1))
    record.append(out, results_path)
    return out


# ---------------------------------------------------------------- one seed

def run_seed(c, seed, gated, results_path=record.RESULTS, log=print, reported=True, arms=None, c4=None):
    if str(results_path) == str(record.RESULTS) and record.digest(c) != DIGEST:
        raise SystemExit("only the contract configuration may write to the results file")
    rec, loads, main, gen = run_gated_arm(c, seed, gated, results_path, log)
    if not reported:
        return rec
    gated_diagnostics(c, seed, gated, loads, main, gen, results_path, log)
    gated_fb = {M: T["fb_store"] for M, T in loads.items()}
    del loads
    for arm in (arms or P2E3_ARMS + ("online",)):
        try:
            if arm == "online":
                run_online_arm(seed, gated, gated_fb, results_path, log, c4=c4, c=c)
            else:
                run_p2e3_arm(arm, c, seed, gated, results_path, log)
        except Exception as ex:  # a crashed reported arm voids only that arm (contract: Voids)
            record.append(dict(experiment="P2-E5", kind="reported_arm", arm=arm, seed=seed, gated=gated,
                               contract_digest=record.digest(c), crashed=repr(ex), timestamp=record.now(),
                               git=record.git_state()), results_path)
            log(f"seed {seed} {arm}: CRASHED {ex!r} (the arm is void)")
    log(f"seed {seed}: reported arms done")
    return rec


# ---------------------------------------------------------------- verdict and readings

LABEL_ORDER = ["STRUCTURED INDEX FAIL", "STRUCTURED CONTENT FAIL"]


def labels(recs):
    lab = set()
    for r in recs:
        for M, v in r["vector"].items():
            if not all(v[k] for k in ("C1", "C2", "C3", "C4_recall", "C4_spurious")):
                lab.add("STRUCTURED INDEX FAIL")
            if not all(v[k] for k in ("S2", "S3", "S4")):
                lab.add("STRUCTURED CONTENT FAIL")
    return [x for x in LABEL_ORDER if x in lab]


def first_records(recs, kind, gated=True, arm=None, digest=DIGEST):
    first = {}
    for r in recs:
        if (r.get("experiment") == "P2-E5" and r.get("kind") == kind and r.get("gated") is gated
                and r.get("contract_digest") == digest and (arm is None or r.get("arm") == arm) and r["seed"] not in first):
            first[r["seed"]] = r
    return first


def readings(c, gated, diag, arms, loads):
    """Parts B-E from the records (contract: 'Reported arms and readings')."""
    seeds = sorted(gated)
    out = {}
    online, s100, pooled = arms.get("online", {}), arms.get("s100", {}), arms.get("pooled", {})
    for M in loads:
        rows = {}
        n = None
        for s in seeds:
            d = diag.get(s)
            if d is None or "loads" not in d:
                rows[s] = None
                continue
            D = d["loads"][M]
            n = D["n_half"]
            bar, mat, mar = power.bar_count(n, c["frac"]), cues_count(c["material_frac"], n), cues_count(c["margin_frac"], n)
            ub, own = D["grid"]["plateau"]["best_cues"], D["grid"]["main"]["best_cues"]
            Lc = max(0, min(ub, bar) - min(own, bar))
            Lc_frozen = max(0, min(D["grid"]["plateau"]["frozen_cues"], bar) - min(D["grid"]["main"]["frozen_cues"], bar))
            Li = max(0, bar - ub)
            o = online.get(s)
            oL = o["loads"].get(M) if o and "loads" in o else None
            Lo = oL["L_o"]["loss"] if oL and oL["valid"] else None
            a = s100.get(s)
            aL = a["loads"].get(M) if a and "loads" in a else None
            attributable = bool(aL is not None and aL["valid"] and aL.get("p2e3_gate") and Lo is not None)
            dom = None
            if attributable:
                L = dict(CONTAMINATION=Lc, INDEX=Li, OPERATING_POINT=Lo)
                for x, val in L.items():
                    others = max(v for k, v in L.items() if k != x)
                    if val >= mat and val - others >= mar:
                        dom = x
            rows[s] = dict(L_c=Lc, L_c_frozen=Lc_frozen, L_i=Li, L_o=Lo, attributable=attributable, dominant=dom,
                           all_below_material=bool(attributable and max(Lc, Li, Lo) < mat))
        att = [r for r in rows.values() if r and r["attributable"]]
        need = c["min_seeds"]
        if len(att) < need:
            reading = "NOT ATTRIBUTABLE"
        else:
            reading = None
            for x in ("CONTAMINATION", "INDEX", "OPERATING_POINT"):
                if sum(r["dominant"] == x for r in att) >= need:
                    reading = f"{x.replace('_', '-')}-DOMINANT"
            if reading is None:
                reading = "NO MATERIAL LOSS" if sum(r["all_below_material"] for r in att) >= need else "SPLIT"
        mat_ = cues_count(c["material_frac"], n) if n else None
        material = {k: bool(len(att) >= need and sum(r[k] is not None and r[k] >= mat_ for r in att) >= need)
                    for k in ("L_c", "L_i", "L_o")}
        B = dict(per_seed={str(s): r for s, r in rows.items()}, reading=reading, material=material)
        # Part C
        okC = []
        for s in seeds:
            d = diag.get(s)
            if d is None or "loads" not in d:
                okC.append(False)
                continue
            D = d["loads"][M]
            nn = D["n_half"]
            tol = cues_count(c["margin_frac"], nn)
            au = D["activity"]["count_auc"]
            g = D["grid"]
            okC.append(bool(au is not None and au >= c["auc_bar"] and g["R3"]["frozen_cues"] >= g["plateau"]["frozen_cues"] - tol
                            and g["R3"]["best_cues"] >= g["plateau"]["best_cues"] - tol))
        C = dict(per_seed=okC, ok=bool(okC and all(okC)))
        # Part D
        ratios = [online[s]["loads"][M]["ratio"] for s in seeds if s in online and "loads" in online[s]
                  and online[s]["loads"][M]["valid"] and online[s]["loads"][M]["ratio"] is not None]
        if len(ratios) < need:
            Dr = "NOT ESTIMABLE"
        elif sum(x >= c["worsens_ratio"] for x in ratios) >= need:
            Dr = "WORSENS"
        elif sum(x < c["not_worse_ratio"] for x in ratios) >= need:
            Dr = "NOT WORSE"
        else:
            Dr = "MIXED"
        Dd = dict(ratios=ratios, reading=Dr)
        # Part E: pooled
        prow = []
        for s in seeds:
            p = pooled.get(s)
            g_ = gated[s]["loads"][M]
            if not (p and "loads" in p and p["loads"][M]["valid"]) or g_["vector"]["S2"]:
                continue
            P_ = p["loads"][M]
            nn = c["n_old"] + c["n_rand"]
            d = diag.get(s)
            main_plat = d["loads"][M]["grid"]["plateau"]["frozen_cues"] if d and "loads" in d else None
            mc2, pc2 = g_["counts"]["C2"], P_["counts"]["C2"]
            prow.append(dict(seed=s, pooled_passes_S2=bool(P_["vector"]["S2"]),
                             plateau_gain=None if main_plat is None else P_["plateau_cues"] - main_plat, C2_gain=pc2 - mc2))
        mat_e, tol_e = cues_count(c["material_frac"], c["n_old"] + c["n_rand"]), cues_count(c["margin_frac"], c["n_old"] + c["n_rand"])
        if len(prow) < need:
            Er = "NOT ESTIMABLE"
        elif sum(r["pooled_passes_S2"] for r in prow) >= need:
            Er = "CORRELATION-ATTRIBUTABLE"
        elif sum((not r["pooled_passes_S2"]) and ((r["plateau_gain"] or 0) >= mat_e or r["C2_gain"] >= mat_e) for r in prow) >= need:
            Er = "LINE LOAD SUFFICIENT, CORRELATION WORSENS"
        elif sum((not r["pooled_passes_S2"]) and r["plateau_gain"] is not None and abs(r["plateau_gain"]) <= tol_e
                 and abs(r["C2_gain"]) <= tol_e for r in prow) >= need:
            Er = "LINE-LOAD-LIMITED"
        else:
            Er = "MIXED"
        dose = {}
        for a_, b_ in (("s80", "main"), ("main", "s40")):
            mc = []
            for s in seeds:
                ja = (arms.get(a_, {}).get(s) or {}).get("loads", {}).get(M) if a_ != "main" else gated[s]["loads"][M]
                jb = (arms.get(b_, {}).get(s) or {}).get("loads", {}).get(M) if b_ != "main" else gated[s]["loads"][M]
                if ja and jb and ja.get("per_cue") and jb.get("per_cue"):
                    xa = np.array([ch == "1" for ch in ja["per_cue"]["joint"]])
                    xb = np.array([ch == "1" for ch in jb["per_cue"]["joint"]])
                    mc.append([int((xa & ~xb).sum()), int((~xa & xb).sum())])
            dose[f"{a_}_vs_{b_}"] = mc
        out[M] = dict(part_B=B, part_C=C, part_D=Dd, pooled=dict(rows=prow, reading=Er), dose_response=dose)
    # s100, ordered rule over (seed, load)
    fails, nonvoid = False, 0
    for s in seeds:
        a = s100.get(s)
        ok_loads = a is not None and "loads" in a and all(a["loads"][M]["valid"] for M in loads)
        if a is not None and "loads" in a:
            for M in loads:
                if a["loads"][M]["valid"] and not a["loads"][M].get("p2e3_gate"):
                    fails = True
        nonvoid += bool(ok_loads)
    out["s100"] = "REPLICATION FAIL" if fails else ("NOT ESTIMABLE" if nonvoid < c["min_seeds"] else "REPLICATES")
    out["part_C"] = "AVAILABLE FROM ACTIVITY" if all(out[M]["part_C"]["ok"] for M in loads) else "NOT SHOWN"
    out["loads_disagree"] = len({out[M]["part_B"]["reading"] for M in loads}) > 1
    return out


def verdict(recs, results_path=record.RESULTS, log=print, c=CONTRACT, seeds=GATED_SEEDS):
    gated = first_records(recs, "kill_test_seed")
    if sorted(gated) != sorted(seeds):
        raise SystemExit(f"verdict needs exactly the gated seeds {seeds}; have {sorted(gated)}")
    invalid = [s for s, r in gated.items() if not r["valid"]]
    labs = ["INVALID"] if invalid else labels(list(gated.values()))
    label = "INVALID" if invalid else ("PASS" if not labs else " + ".join(labs))
    loads = list(next(iter(gated.values()))["vector"])
    vector = {M: {k: all(r["vector"][M][k] for r in gated.values()) for k in VECTOR_PARTS} for M in loads}
    diag = first_records(recs, "reported_arm", arm="gated_diagnostics")
    arms = {a: first_records(recs, "reported_arm", arm=a) for a in P2E3_ARMS + ("online",)}
    rd = readings(c, gated, diag, arms, loads)
    spec_flag = None
    if label == "PASS":
        spec_flag = any(d["loads"][M]["contamination"]["label_permuted"]["perm_spec"] >
                        c["specificity_ratio"] * d["loads"][M]["contamination"]["label_permuted"]["main_spec"]
                        for d in diag.values() for M in loads)
    rec = dict(experiment="P2-E5", kind="kill_test_verdict", seeds=sorted(gated), verdict=label, labels=labs,
               invalid_seeds=invalid, vector=vector, readings=rd, pass_specificity_check_failed=spec_flag,
               per_seed={str(s): {M: r["counts"] for M, r in r_["loads"].items()} for s, r_ in gated.items()},
               contract_digest=DIGEST, timestamp=record.now(), git=record.git_state(), runtime=record.runtime())
    record.append(rec, results_path)
    log(f"P2-E5 verdict: {label} | Part B {[rd[M]['part_B']['reading'] for M in loads]} | Part C {rd['part_C']} | "
        f"Part D {[rd[M]['part_D']['reading'] for M in loads]} | s100 {rd['s100']} | pooled "
        f"{[rd[M]['pooled']['reading'] for M in loads]}")
    return rec


# ---------------------------------------------------------------- predictions from the exploration seeds

def predictions(recs, draws=400, rng_seed=5, results_path=record.RESULTS, log=print, c=CONTRACT):
    """P(PASS), per-criterion five-seed pass probabilities and label probabilities from the exploration seeds'
    pooled per-cue counts (Beta posteriors, logit seed SD as P2-E4), plus the exploration seeds' reading inputs."""
    g = record.git_state()
    if g["plant2_dirty"]:
        raise SystemExit("predictions: plant2/ has uncommitted changes")
    first, skipped = {}, []
    for r in recs:
        if not (r.get("experiment") == "P2-E5" and r.get("kind") == "exploration_seed"):
            continue
        ok = (r.get("contract_digest") == DIGEST and r["seed"] in EXPLORE_SEEDS and r["git"]["plant2_tree"] == g["plant2_tree"]
              and not r["git"]["plant2_dirty"])
        if not ok or r["seed"] in first:
            skipped.append(dict(seed=r["seed"], reason="duplicate" if ok else "other tree, dirty tree, digest or seed"))
            continue
        first[r["seed"]] = r
    if sorted(first) != sorted(EXPLORE_SEEDS):
        raise SystemExit(f"predictions need exploration seeds {EXPLORE_SEEDS} on this clean plant2 tree; have {sorted(first)}")
    ex = [first[s] for s in sorted(first)]
    n_half, n_novel, n_old = c["n_old"] + c["n_rand"], c["n_novel"], c["n_old"]
    n_of = dict(C1=n_half, C2=n_half, C3=n_novel, C4_recall=n_old, C4_spurious=n_old, S2=n_half, S3=n_novel, S4=n_old)
    loads = list(ex[0]["loads"])
    rng = np.random.default_rng(rng_seed)
    obs = {M: {k: (sum(r["loads"][M]["counts"][k] for r in ex), n_of[k] * len(ex)) for k in VECTOR_PARTS} for M in loads}
    p_pass, p_index, p_content, per = [], [], [], {f"{M}:{k}": [] for M in loads for k in VECTOR_PARTS}
    for _ in range(draws):
        pi_ = pc_ = 1.0
        for M in loads:
            for k in VECTOR_PARTS:
                x, nn = obs[M][k]
                p = float(np.clip(rng.beta(1 + x, 1 + nn - x), 0.001, 0.999))
                v = power.p_rule([(n_of[k], p)], seeds=5, seed_sd=power.P2E4_SEED_SD)
                per[f"{M}:{k}"].append(v)
                if k.startswith("S"):
                    pc_ *= v
                else:
                    pi_ *= v
        p_index.append(pi_)
        p_content.append(pc_)
        p_pass.append(pi_ * pc_)
    q = lambda x: [float(np.percentile(x, 5)), float(np.percentile(x, 95))]
    diag = first_records(recs, "reported_arm", gated=False, arm="gated_diagnostics")
    arms = {a: first_records(recs, "reported_arm", gated=False, arm=a) for a in P2E3_ARMS + ("online",)}
    expl = {str(s): first[s] for s in first}
    inputs = readings(dict(c, min_seeds=1), {s: first[s] for s in first}, diag, arms, loads)
    rec = dict(experiment="P2-E5", kind="power_predictions", contract_digest=DIGEST, plant2_tree=g["plant2_tree"],
               exploration_seeds=sorted(first), skipped_records=skipped, observed={M: {k: list(v) for k, v in o.items()} for M, o in obs.items()},
               p_pass_median=float(np.median(p_pass)), p_pass_interval_5_95=q(p_pass),
               p_label=dict(STRUCTURED_INDEX_FAIL=float(1 - np.mean(p_index)), STRUCTURED_CONTENT_FAIL=float(1 - np.mean(p_content))),
               p_criterion_5seeds={k: float(np.median(v)) for k, v in per.items()},
               exploration_reading_inputs=inputs, draws=draws, timestamp=record.now(), git=g, runtime=record.runtime())
    del expl
    record.append(rec, results_path)
    log(f"P2-E5 predictions: P(PASS) median {rec['p_pass_median']:.3g} {rec['p_pass_interval_5_95']}; labels {rec['p_label']}")
    return rec


# ---------------------------------------------------------------- guard and CLI

def _git(*args):
    return subprocess.run(["git", "-C", str(record.REPO), *args], capture_output=True, text=True)


def guard(recs):
    """--gated refuses unless: plant2/ is committed; the contract is unmodified in the working tree and has only had lines
    added since its frozen commit; and HEAD's results file holds a P2-E5 power_predictions record made under this contract
    digest and this plant2 tree."""
    g = record.git_state()
    if g["plant2_dirty"]:
        raise SystemExit("guard: plant2/ has uncommitted changes")
    if _git("diff", "--quiet", "HEAD", "--", CONTRACT_PATH).returncode != 0:
        raise SystemExit("guard: the contract differs from HEAD")
    if _git("merge-base", "--is-ancestor", CONTRACT_FROZEN_AT, "HEAD").returncode != 0:
        raise SystemExit(f"guard: the frozen contract commit {CONTRACT_FROZEN_AT} is not an ancestor of HEAD")
    r_num = _git("diff", "--numstat", CONTRACT_FROZEN_AT, "HEAD", "--", CONTRACT_PATH)
    if r_num.returncode != 0:
        raise SystemExit(f"guard: cannot compare the contract with its frozen commit {CONTRACT_FROZEN_AT}")
    num = r_num.stdout.split()
    if num and int(num[1]) != 0:
        raise SystemExit("guard: the frozen contract text was changed (only additions are allowed)")
    head = _git("show", "HEAD:bench/results/plant2.jsonl").stdout.splitlines()
    pred = [json.loads(l) for l in head if '"power_predictions"' in l and '"P2-E5"' in l]
    pred = [p for p in pred if p.get("experiment") == "P2-E5"]
    if not pred:
        raise SystemExit("guard: no committed P2-E5 power_predictions record")
    p = pred[-1]
    if p["contract_digest"] != DIGEST or p["plant2_tree"] != g["plant2_tree"]:
        raise SystemExit("guard: predictions were made under a different contract digest or plant2 tree")
    return set(first_records(recs, "kill_test_seed"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("explore", "run"):
        p = sub.add_parser(name)
        p.add_argument("--seeds", type=int, nargs="+", required=True)
        p.add_argument("--gated", action="store_true")
        p.add_argument("--no-reported", action="store_true")
        p.add_argument("--owner-ruled-rerun", action="store_true", help="only with the owner's written ruling")
    sub.add_parser("predict")
    sub.add_parser("verdict")
    a = ap.parse_args(argv)

    def log(msg):
        print(f"[{record.now()}] {msg}", flush=True)
    if a.cmd == "explore":
        if record.git_state()["plant2_dirty"]:
            raise SystemExit("explore: plant2/ has uncommitted changes")
        for s in dict.fromkeys(a.seeds):
            if s not in EXPLORE_SEEDS:
                raise SystemExit(f"exploration uses seeds {EXPLORE_SEEDS} only")
            run_seed(CONTRACT, s, gated=False, log=log, reported=not a.no_reported)
    elif a.cmd == "run":
        if not a.gated:
            raise SystemExit("use 'explore' for non-gated seeds")
        for s in dict.fromkeys(a.seeds):
            if s not in GATED_SEEDS:
                raise SystemExit(f"{s} is not a gated seed")
            done = guard(e4.load_records())
            marker = record.cache_dir("p2_e5") / f"gated_seed{s}.started"
            if s in done or (marker.exists() and not a.owner_ruled_rerun):
                raise SystemExit(f"seed {s} was already started or recorded (each gated seed runs once)")
            marker.write_text(record.now())
            run_seed(CONTRACT, s, gated=True, log=log)
    elif a.cmd == "predict":
        predictions(e4.load_records(), log=log)
    elif a.cmd == "verdict":
        verdict(e4.load_records(), log=log)


if __name__ == "__main__":
    sys.exit(main())
