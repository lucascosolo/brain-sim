"""P2-E3: content completion, regenerating the missing half of an input from a half cue.

Contract: docs/plant2/P2-E3-content-completion.md (predeclared). P2-E2's memory network is reused
unchanged (p2_e1_btsp and p2_e2_accommodation are not edited). Each learning episode adds a 50 ms
continuation and a one-shot clipped Hebbian feedback write. The reconstruction-layer arms are
replayed from each test phase's memory raster (plant2.readout).

    python3 -m plant2.experiments.p2_e3_completion calibrate
    python3 -m plant2.experiments.p2_e3_completion run --J 2.6 --J0 1.45 --seeds 11 12 13 14 15 --gated --verdict
"""
import argparse
import copy
import hashlib
import sys
import time

import numpy as np

from plant2 import record
from plant2.btsp import BinarySynapses, btsp_update
from plant2.experiments import p2_e1_btsp as e1
from plant2.experiments import p2_e2_accommodation as e2
from plant2.readout import replay

J_STAR_MEM = 1.525          # P2-E2's calibrated memory J
G = 0.3                     # fixed inhibition ratio of the main arm
WINDOW, SHORT, SPAN = 75, 50, 300
JOINT_MISSING, JOINT_INTRUSIONS, NOVEL_LINES, FRAC = 40, 10, 10, 0.90
J_GRID = tuple(round(1.0 + 0.05 * i, 2) for i in range(101))
GATE_M = (250, 500, 1000)
REPORT_M = (1500, 2000)
STRUCT_M = 1000
CAL_SEED = 0
GATED_SEEDS = (11, 12, 13, 14, 15)
CONT, SHUFFLED, PERMUTED = 9, 10, 11  # stream ids (P2-E1 uses 0-6, P2-E2 uses 8)
# "window" stays P2-E1/E2's 50 ms memory window (C1-C4); the rec scoring window is its own key
CONTRACT = dict(e2.CONTRACT, J=J_STAR_MEM, t_cont=50, g=G, rec_window=WINDOW)
DIGEST = record.digest(dict(CONTRACT, J_fb=None))


class E3(e2.E2):
    """P2-E2's network plus a continuation and a one-shot feedback write per episode."""

    def __init__(self, cfg, seed):
        super().__init__(cfg, seed)
        self.fb = BinarySynapses(cfg["n"], cfg["m"])
        self.fb_plateau = BinarySynapses(cfg["n"], cfg["m"])
        self.R, self.E, self.cont_offset = [], [], []

    def learn_one(self):
        # encoding: P2-E1's learn_one, statement for statement (the store must stay bit-identical)
        c = self.c
        item = np.sort(self._pat.choice(c["m"], c["a"], replace=False))
        self.items.append(item)
        self.net.quiet()
        self._rates(item)
        plateau = np.flatnonzero(self._plat.random(c["n"]) < c["f_q"])
        counts = np.zeros(c["m"], np.int64)
        mem_spk = 0
        for _ in range(c["t_item"]):
            sp = self.net.step(self._learn_in)
            counts[sp["inp"]] += 1
            mem_spk += sp["mem"].size
        eligible = np.flatnonzero(counts >= c["elig_min"])
        pot, dep = btsp_update(self.store, plateau, eligible, self._coin, c["p_flip"])
        self._load()
        self.A.append(plateau)
        self.plateaus_per_cell[plateau] += 1
        lg = self.learn_log
        lg["elig_frac"].append(float((counts[item] >= c["elig_min"]).mean()))
        lg["bg_eligible"].append(int(eligible.size - (counts[item] >= c["elig_min"]).sum()))
        lg["potentiated"].append(pot)
        lg["depressed"].append(dep)
        lg["mem_spikes"].append(mem_spk)
        # continuation: same item, own stream, no quiet(); responders write the feedback
        rng = e1.stream(self.seed, CONT, len(self.items) - 1)
        responded = np.zeros(c["n"], bool)
        for _ in range(c["t_cont"]):
            responded[self.net.step(rng)["mem"]] = True
        R = np.flatnonzero(responded)
        m = c["m"]
        self.fb.add((R[:, None] * m + eligible[None, :]).ravel())
        self.fb_plateau.add((plateau[:, None] * m + eligible[None, :]).ravel())
        self.R.append(R)
        self.E.append(eligible)
        self.cont_offset.append(float(self.mem.vbar.mean() - float(self.mem.v_rest)))

    def settle_drift(self, M, phase):
        """P2-E2's settle (same stream), returning (mean |dvbar|, signed mean dvbar) over the last 10 s."""
        rng = e1.stream(self.seed, e1.TEST_IN, M, e2.SETTLE_PHASE + phase)
        self._rates(None)
        for _ in range(self.c["settle"] - self.c["converge_window"]):
            self.net.step(rng)
        before = self.mem.vbar.copy()
        for _ in range(self.c["converge_window"]):
            self.net.step(rng)
        d = self.mem.vbar - before
        return float(np.abs(d).mean()), float(d.mean())

    def present(self, cues, rng):
        """P2-E2's presentation, also recording the memory raster and cue onsets for the readout."""
        c = self.c
        self._rates(None)
        for _ in range(c["t_gap"]):
            self._step(rng)
        out = []
        first = np.full(c["n"], -1, np.int64)
        for cue in cues:
            first[:] = -1
            self._rates(cue)
            self._onsets.append(self.net.t - self._t0)
            for k in range(c["t_cue"]):
                s = self._step(rng)
                if s.size:
                    s = s[first[s] < 0]
                    first[s] = k
            hit = np.flatnonzero(first >= 0)
            out.append((hit, first[hit].copy()))
            self._rates(None)
            for _ in range(c["t_gap"]):
                self._step(rng)
        return out

    def _step(self, rng):
        t = self.net.t - self._t0
        s = self.net.step(rng)["mem"]
        if s.size:
            self._raster[t] = s.copy()
        return s


def feedback_csr(store):
    indptr, post = store.csr()
    return indptr, post


def shuffled_store(e, M):
    rng = e1.stream(e.seed, SHUFFLED, M)
    counts = np.bincount(e.fb.keys // e.c["m"], minlength=e.c["n"])
    s = BinarySynapses(e.c["n"], e.c["m"])
    keys = [i * e.c["m"] + np.sort(rng.choice(e.c["m"], k, replace=False)) for i, k in enumerate(counts) if k]
    s.keys = np.sort(np.concatenate(keys)) if keys else np.empty(0, np.int64)
    return s


def permuted_store(e, M):
    pi = e1.stream(e.seed, PERMUTED, M).permutation(M)
    s = BinarySynapses(e.c["n"], e.c["m"])
    m = e.c["m"]
    s.add(np.concatenate([(e.R[k][:, None] * m + e.E[pi[k]][None, :]).ravel() for k in range(M)]))
    return s, pi


def build_cues(e, M, onsets, pi=None):
    c = e.c
    cued, masks, nmasks = e1.test_sets(c, e.seed, M)
    half, novel, full = [], [], []
    for idx, (i, mk) in enumerate(zip(cued, masks)):
        item = e.items[i]
        cue = item[mk]
        nxt = cued[(idx + 1) % len(cued)]
        other_item = e.items[nxt] if pi is None else e.items[pi[i]]
        other_mask = masks[(idx + 1) % len(cued)] if pi is None else None
        other_missing = (np.setdiff1d(other_item, other_item[other_mask]) if other_mask is not None
                         else np.setdiff1d(other_item, cue))
        half.append(dict(kind="half", item=item, cue=cue, missing=np.setdiff1d(item, cue), other_missing=other_missing,
                         index=int(i)))
    for j, mk in enumerate(nmasks):
        item = e.novel[j]
        novel.append(dict(kind="novel", item=item, cue=item[mk], missing=np.setdiff1d(item, item[mk]),
                          other_missing=np.empty(0, np.int64), index=j))
    for i in cued:
        full.append(dict(kind="full", item=e.items[i], cue=e.items[i], missing=np.empty(0, np.int64),
                         other_missing=np.empty(0, np.int64), index=int(i)))
    cues = half + novel + full
    assert len(cues) == len(onsets)
    for cdict, on in zip(cues, onsets):
        cdict["onset"] = on
    return cues


def run_phase(e, M, phase=1):
    """Settle, then P2-E2's evaluation with the raster recorded. Returns (memory out, raster, n_ticks, onsets, drift)."""
    drift = e.settle_drift(M, phase)
    e._raster, e._onsets, e._t0 = {}, [], e.net.t
    out = e2.evaluate(e, M, phase=phase)
    n_ticks = e.net.t - e._t0
    return out, e._raster, n_ticks, list(e._onsets), drift


def score(res, latency, cues, n_cued_old, A):
    """Per-arm criteria from replay output. Item, cue and missing sizes come from the cue arrays."""
    kinds = np.array([c["kind"] for c in cues])
    h, nv, fu = kinds == "half", kinds == "novel", kinds == "full"
    size = lambda kind, key: np.array([c[key].size for c in cues if c["kind"] == kind], float)[:, None]
    n_item, n_cue, n_miss = size("half", "item"), size("half", "cue"), size("half", "missing")
    miss = res["missing"][h]
    intr = res["total"][h] - res["item"][h]
    joint = (miss >= JOINT_MISSING) & (intr < JOINT_INTRUSIONS)
    old = np.zeros(h.sum(), bool)
    old[:n_cued_old] = True
    miss_s = res["missing_short"][h]
    intr_s = res["total_short"][h] - res["item_short"][h]
    joint_s = (miss_s >= JOINT_MISSING) & (intr_s < JOINT_INTRUSIONS)
    hd = ((res["total"][h] - res["item"][h]) + (n_item - res["item"][h])) / n_miss
    other_size = np.array([max(1, c["other_missing"].size) for c in cues if c["kind"] == "half"], float)
    arms = []
    for a in range(A):
        d = dict(
            joint=float(joint[:, a].mean()), D3=float((res["total"][nv][:, a] < NOVEL_LINES).mean()),
            D4=float(joint[old, a].mean()), D1=float((miss[:, a] >= JOINT_MISSING).mean()),
            D2=float((intr[:, a] < JOINT_INTRUSIONS).mean()),
            joint_50ms=float(joint_s[:, a].mean()), D1_50ms=float((miss_s[:, a] >= JOINT_MISSING).mean()),
            D2_50ms=float((intr_s[:, a] < JOINT_INTRUSIONS).mean()),
            missing_frac_median=float(np.median(miss[:, a] / n_miss[:, 0])),
            missing_frac_pct=[float(x) for x in np.percentile(miss[:, a] / n_miss[:, 0], [10, 25, 50, 75, 90])],
            intrusions_median=float(np.median(intr[:, a])), intrusions_p90=float(np.percentile(intr[:, a], 90)),
            intrusions_span_median=float(np.median(res["total_span"][h][:, a] - res["item_span"][h][:, a])),
            visible_frac_median=float(np.median(res["visible"][h][:, a] / n_cue[:, 0])),
            hd_ratio=[float(x) for x in np.percentile(hd[:, a], [10, 50, 90])],
            chance_other_missing=float(np.mean(res["other_missing"][h][:, a] / other_size)),
            novel_lines_median=float(np.median(res["total"][nv][:, a])),
            novel_lines_max=int(res["total"][nv][:, a].max()),
            full_item_frac_median=float(np.median(res["item"][fu][:, a] / size("full", "item")[:, 0])),
            latency_ms_median=float(np.nanmedian(latency[h][:, a])) if np.isfinite(latency[h][:, a]).any() else None,
        )
        d["passes"] = bool(d["joint"] >= FRAC and d["D3"] >= FRAC and d["D4"] >= FRAC)
        arms.append(d)
    return arms


def readout(e, M, raster, n_ticks, onsets, J, g, store=None, pi=None):
    store = e.fb if store is None else store
    cues = build_cues(e, M, onsets, pi=pi)
    indptr, post = feedback_csr(store)
    # the window is the contract's rec_window; the span is the whole cue plus its gap (SPAN in the contract config)
    res, lat, oow = replay(raster, n_ticks, indptr, post, e.c["m"], J, g, cues, window=e.c["rec_window"], short=SHORT,
                           span=e.c["t_cue"] + e.c["t_gap"])
    arms = score(res, lat, cues, e.c["n_old"], len(J))
    for a, d in enumerate(arms):
        d.update(J=float(J[a]), g=float(g[a]), out_of_window_spikes_per_cue=float(oow[a] / len(cues)))
    return arms


def memory_summary(out):
    s = e2.summary(out)
    cr = s["criteria"]
    return dict(C1=cr["C1_frac"], C2=cr["C2_frac"], C3=cr["C3_frac"], C4=(cr["C4_recall_frac"], cr["C4_spurious_frac"]),
                gate_ok=s["gate_ok"], recall_median=s["recall_median"], latency_half_ms=s["latency_half_median_ms"])


def learning_summary(e, M):
    sizes = np.array([len(r) for r in e.R[:M]])
    asz = np.array([len(a) for a in e.A[:M]])
    jac = [len(np.intersect1d(r, a)) / max(1, len(np.union1d(r, a))) for r, a in zip(e.R[:M], e.A[:M])]
    per_cell = np.bincount(e.fb.keys // e.c["m"], minlength=e.c["n"])
    return dict(R_size_mean=float(sizes.mean()), A_size_mean=float(asz.mean()), jaccard_R_A_mean=float(np.mean(jac)),
                R_minus_A_mean=float((sizes - asz).mean()), cont_offset_mv_last50=float(np.mean(e.cont_offset[max(0, M - 50):M])),
                fb_store_size=e.fb.size, fb_per_cell_mean=float(per_cell.mean()),
                fb_per_cell_pct=[int(x) for x in np.percentile(per_cell, [5, 50, 95, 100])],
                fb_line_density=float(per_cell[per_cell > 0].mean() / e.c["m"]) if (per_cell > 0).any() else 0.0)


def digest(keys):
    return hashlib.sha256(keys.tobytes()).hexdigest()[:16]


def choose(grid, passing):
    runs, cur = [], []
    for J in grid:
        if passing[J]:
            cur.append(J)
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    best = max(runs, key=len) if runs else None  # max() keeps the first (lower) run on ties
    J_star = round((best[0] + best[-1]) / 2, 4) if best else None
    censored = bool(best) and (best[0] == grid[0] or best[-1] == grid[-1])
    return J_star, runs, censored


def calibrate(c=CONTRACT, seed=CAL_SEED, grid=J_GRID, loads=GATE_M, results_path=record.RESULTS, log=print):
    main = E3(c, seed)
    Js = np.array(list(grid) * 2)
    gs = np.array([G] * len(grid) + [0.0] * len(grid))
    per_load, rasters = {}, {}
    for M in loads:
        t0 = time.time()
        main.learn(M)
        e = copy.deepcopy(main)
        out, raster, n_ticks, onsets, drift = run_phase(e, M)
        arms = readout(e, M, raster, n_ticks, onsets, Js, gs)
        per_load[M] = arms
        rasters[M] = (e, raster, n_ticks, onsets)
        mem = memory_summary(out)
        record.append(dict(experiment="P2-E3", kind="calibration_point", timestamp=record.now(), git=record.git_state(),
                           runtime=record.runtime(), contract_digest=DIGEST, seed=seed, M=M,
                           converge_mv=drift[0], drift_signed_mv=drift[1], memory=mem, learning=learning_summary(main, M),
                           arms=[[a["J"], a["g"], a["joint"], a["D3"], a["D4"], a["D1"], a["D2"]] for a in arms],
                           wall_s=round(time.time() - t0, 1)), results_path)
        best = max(arms[:len(grid)], key=lambda a: min(a["joint"], a["D3"], a["D4"]))
        best0 = max(arms[len(grid):], key=lambda a: min(a["joint"], a["D3"], a["D4"]))
        log(f"cal M={M}: memory C1 {mem['C1']:.3f} C2 {mem['C2']:.3f} C3 {mem['C3']:.3f} | conv {drift[0]:.3f} mV "
            f"(signed {drift[1]:+.3f}) | g=0.3 passing {sum(a['passes'] for a in arms[:len(grid)])} best J {best['J']} "
            f"joint {best['joint']:.3f} | g=0 passing {sum(a['passes'] for a in arms[len(grid):])} best J {best0['J']} "
            f"joint {best0['joint']:.3f} | {time.time() - t0:.0f} s")
    nJ = len(grid)
    passing = {J: all(per_load[M][i]["passes"] for M in loads) for i, J in enumerate(grid)}
    passing0 = {J: all(per_load[M][nJ + i]["passes"] for M in loads) for i, J in enumerate(grid)}
    J_star, runs, cens = choose(grid, passing)
    J0_star, runs0, cens0 = choose(grid, passing0)
    fallback0 = None
    if J0_star is None:
        score0 = [min(min(per_load[M][nJ + i][k] for k in ("joint", "D3", "D4")) for M in loads) for i in range(nJ)]
        fallback0 = grid[int(np.argmax(score0))]  # argmax takes the first (lower) J on ties
    J0_used = J0_star if J0_star is not None else fallback0
    reread = {}
    if J_star is not None:
        for M in loads:
            e, raster, n_ticks, onsets = rasters[M]
            arms = readout(e, M, raster, n_ticks, onsets, np.array([J_star, J0_used, J_star]), np.array([G, 0.0, 0.0]))
            reread[str(M)] = dict(main=arms[0], matched_g0=arms[1], g0_at_J_star=arms[2])
    record.append(dict(experiment="P2-E3", kind="calibration_verdict", timestamp=record.now(), git=record.git_state(),
                       runtime=record.runtime(), contract_digest=DIGEST, seed=seed,
                       J_star=J_star, runs=runs, censored=cens, J0_star=J0_star, runs0=runs0, censored0=cens0,
                       J0_fallback=fallback0, J0_used=J0_used, reread=reread), results_path)
    log(f"calibration: g=0.3 runs {runs} -> J* {J_star} (censored {cens}); g=0 runs {runs0} -> J0* {J0_star}, "
        f"fallback {fallback0}, used {J0_used}")
    for M, rr in reread.items():
        for name, a in rr.items():
            log(f"  re-read M={M} {name} J={a['J']} g={a['g']}: joint {a['joint']:.3f} D1 {a['D1']:.3f} D2 {a['D2']:.3f} "
                f"D3 {a['D3']:.3f} D4 {a['D4']:.3f} latency {a['latency_ms_median']} hd {a['hd_ratio']}")
    return J_star, J0_used, reread


def run_seed(c, seed, J_star, J0, gated, results_path=record.RESULTS, log=print, loads=GATE_M + REPORT_M,
             gate_loads=GATE_M, struct_M=STRUCT_M):
    t0 = time.time()
    main = E3(c, seed)
    plain = e1.E1(dict(c, J=e1.CONTRACT["J"]), seed)
    rec = dict(experiment="P2-E3", kind="kill_test_seed", seed=seed, gated=gated, J_star=J_star, J0=J0,
               contract_digest=DIGEST, loads={}, validity={})
    unchanged, fwd_equal = True, True
    for M in loads:
        main.learn(M)
        e = copy.deepcopy(main)
        fwd, fb = e.store.keys.copy(), e.fb.keys.copy()
        out, raster, n_ticks, onsets, drift = run_phase(e, M)
        unchanged &= bool(np.array_equal(fwd, e.store.keys) and np.array_equal(fb, e.fb.keys))
        arms = readout(e, M, raster, n_ticks, onsets, np.array([J_star, J0, J_star]), np.array([G, 0.0, 0.0]))
        load = dict(main=arms[0], matched_g0=arms[1], g0_at_J_star=arms[2], memory=memory_summary(out),
                    converge_mv=drift[0], drift_signed_mv=drift[1], learning=learning_summary(main, M),
                    fwd_digest=digest(main.store.keys), fb_digest=digest(main.fb.keys))
        if M in gate_loads:
            plain.learn(M)
            same = digest(plain.store.keys) == load["fwd_digest"]
            fwd_equal &= same
            load["fwd_equals_p2e1"] = same
        if M == struct_M:
            sh = readout(e, M, raster, n_ticks, onsets, np.array([J_star]), np.array([G]), store=shuffled_store(e, M))[0]
            ps, pi = permuted_store(e, M)
            pm = readout(e, M, raster, n_ticks, onsets, np.array([J_star]), np.array([G]), store=ps, pi=pi)[0]
            pl = readout(e, M, raster, n_ticks, onsets, np.array([J_star]), np.array([G]), store=e.fb_plateau)[0]
            load.update(shuffled=sh, label_permuted=pm, plateau_set=pl)
        rec["loads"][str(M)] = load
        a, mm = load["main"], load["memory"]
        log(f"seed {seed} M={M}: joint {a['joint']:.3f} D1 {a['D1']:.3f} D2 {a['D2']:.3f} D3 {a['D3']:.3f} D4 {a['D4']:.3f} "
            f"| memory C1 {mm['C1']:.3f} C2 {mm['C2']:.3f} C3 {mm['C3']:.3f} | matched g0 joint {load['matched_g0']['joint']:.3f} "
            f"| g0@J* joint {load['g0_at_J_star']['joint']:.3f} | conv {drift[0]:.3f} ({drift[1]:+.3f}) mV"
            + (f" | shuffled D1 {load['shuffled']['D1']:.3f}" if M == struct_M else ""))
    L = rec["loads"]
    v = rec["validity"]
    v.update(stores_unchanged_by_tests=bool(unchanged), fwd_equals_p2e1=bool(fwd_equal),
             converged=all(L[str(M)]["converge_mv"] <= e2.CONVERGE_BAR_MV for M in gate_loads),
             mean_elig_frac=float(np.mean(main.learn_log["elig_frac"])),
             mean_A=float(np.mean([x.size for x in main.A[:struct_M]])))
    v["elig_ok"] = v["mean_elig_frac"] >= e1.BARS["elig_valid"]
    v["mean_A_ok"] = e1.BARS["mean_A_lo"] <= v["mean_A"] <= e1.BARS["mean_A_hi"]
    valid = all(v[k] for k in ("stores_unchanged_by_tests", "fwd_equals_p2e1", "converged", "elig_ok", "mean_A_ok"))
    content = all(L[str(M)]["main"]["passes"] for M in gate_loads)
    memory = all(L[str(M)]["memory"]["gate_ok"] for M in gate_loads)
    void_ok = L[str(struct_M)]["shuffled"]["joint"] < FRAC
    rec.update(valid=valid, content=content, memory=memory, void_ok=void_ok,
               passed=bool(valid and content and memory and void_ok), timestamp=record.now(), git=record.git_state(),
               runtime=record.runtime(), wall_s=round(time.time() - t0, 1))
    record.append(rec, results_path)
    log(f"seed {seed} ({'gated' if gated else 'reported'}): {'PASS' if rec['passed'] else 'NOT PASS'} valid={valid} "
        f"content={content} memory={memory} void_ok={void_ok} wall {rec['wall_s']} s")
    return rec


def verdict(recs, J_star, J0, j0_calibrated, results_path=record.RESULTS, log=print):
    gated = [r for r in recs if r["gated"]]
    void = not all(r["void_ok"] for r in gated)
    valid = all(r["valid"] for r in gated)
    content = all(r["content"] for r in gated)
    memory = all(r["memory"] for r in gated)
    if void:
        label = "VOID"
    elif not valid:
        label = "INVALID"
    elif content and memory:
        label = "PASS"
    elif content:
        label = "CONTENT PASS / P2-E2 REPLICATION FAIL"
    else:
        label = "FAIL"
    matched = [r["loads"][str(M)]["matched_g0"]["passes"] for r in gated for M in GATE_M]
    secondary = "inhibition unnecessary" if (j0_calibrated and gated and all(matched)) else "inhibition required"
    v = dict(experiment="P2-E3", kind="kill_test_verdict", timestamp=record.now(), git=record.git_state(),
             runtime=record.runtime(), contract_digest=DIGEST, J_star=J_star, J0=J0, seeds=[r["seed"] for r in gated],
             verdict=label, valid=valid, void=void, content=content, memory=memory, secondary=secondary,
             j0_calibrated=j0_calibrated,
             per_seed={str(r["seed"]): r["passed"] for r in gated})
    record.append(v, results_path)
    log(f"P2-E3 kill test: {label} (secondary: {secondary}) {v['per_seed']}")
    return v


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("calibrate")
    vp = sub.add_parser("verdict", help="verdict over the latest gated kill_test_seed records at these J values")
    vp.add_argument("--J", type=float, required=True)
    vp.add_argument("--J0", type=float, required=True)
    vp.add_argument("--j0-fallback", action="store_true")
    r = sub.add_parser("run")
    r.add_argument("--J", type=float, required=True)
    r.add_argument("--J0", type=float, required=True)
    r.add_argument("--seeds", type=int, nargs="+", required=True)
    r.add_argument("--gated", action="store_true")
    r.add_argument("--verdict", action="store_true")
    r.add_argument("--j0-fallback", action="store_true", help="J0 is the fallback (g = 0 had no calibration window)")
    args = ap.parse_args(argv)
    logf = record.cache_dir("p2_e3") / f"{args.cmd}.log"

    def log(msg):
        print(msg, flush=True)
        with logf.open("a", encoding="utf-8") as fh:
            fh.write(f"{record.now()} {msg}\n")

    if args.cmd == "calibrate":
        calibrate(log=log)
        return 0
    if args.cmd == "verdict":
        import json
        rows = [json.loads(l) for l in record.RESULTS.read_text().splitlines()]
        latest = {}
        for r in rows:
            if (r.get("experiment") == "P2-E3" and r.get("kind") == "kill_test_seed" and r.get("gated")
                    and r.get("J_star") == args.J and r.get("J0") == args.J0 and r.get("contract_digest") == DIGEST):
                latest[r["seed"]] = r
        missing = [s for s in GATED_SEEDS if s not in latest]
        if missing:
            raise SystemExit(f"no gated record for seeds {missing}")
        verdict([latest[s] for s in GATED_SEEDS], args.J, args.J0, j0_calibrated=not args.j0_fallback, log=log)
        return 0
    recs = [run_seed(CONTRACT, s, args.J, args.J0, args.gated, log=log) for s in args.seeds]
    if args.verdict:
        verdict(recs, args.J, args.J0, j0_calibrated=not args.j0_fallback, log=log)
    return 0


if __name__ == "__main__":
    sys.exit(main())
