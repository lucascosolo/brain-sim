"""P2-E2: load-independent operating point by slow threshold accommodation.

Contract: docs/plant2/P2-E2-accommodation.md (predeclared). P2-E1's network, learning, cues and
criteria are reused unchanged (plant2.experiments.p2_e1_btsp); only the memory cells' threshold
accommodates, and no test phase resets state.

    python3 -m plant2.experiments.p2_e2_accommodation calibrate          # seed 0, J grid -> J*
    python3 -m plant2.experiments.p2_e2_accommodation run --J 1.6 --seeds 6 7 8 9 10 --gated
    python3 -m plant2.experiments.p2_e2_accommodation run --J 1.6 --seeds 1 2 3 4 5
"""
import argparse
import copy
import hashlib
import sys
import time

import numpy as np

from plant2 import record
from plant2.experiments import p2_e1_btsp as e1

ACC_TAU_MS = 10_000
SETTLE_MS = 5 * ACC_TAU_MS
CONVERGE_WINDOW_MS = 10_000
CONVERGE_BAR_MV = 0.2
J_GRID = tuple(round(1.40 + 0.05 * i, 2) for i in range(11))
GATE_M = (250, 500, 1000)
REPORT_M = (1500, 2000)
CAL_SEED = 0
GATED_SEEDS = (6, 7, 8, 9, 10)
PAIRED_SEEDS = (1, 2, 3, 4, 5)
REPEATS, REPEAT_ITEMS = 10, 20
RANDOM_STORE = 8  # stream id for the matched-density random store
SETTLE_PHASE = 100  # stream offset: the settle before phase p uses phase id SETTLE_PHASE + p
CONTRACT = dict(e1.CONTRACT, acc_tau=ACC_TAU_MS, settle=SETTLE_MS, converge_window=CONVERGE_WINDOW_MS, persist_at=1000)


class E2(e1.E1):
    """P2-E1's network with accommodating memory cells; presentations never reset state."""

    def __init__(self, cfg, seed, accommodate=True):
        super().__init__(cfg, seed)
        self.mem.set_accommodation(cfg["acc_tau"] if accommodate else None)

    def set_J(self, J):
        self.c = dict(self.c, J=J)
        self._load()

    def present(self, cues, rng):
        c = self.c
        self._rates(None)
        for _ in range(c["t_gap"]):
            self.net.step(rng)
        out = []
        first = np.full(c["n"], -1, np.int64)
        for cue in cues:
            first[:] = -1
            self._rates(cue)
            for k in range(c["t_cue"]):
                s = self.net.step(rng)["mem"]
                if s.size:
                    s = s[first[s] < 0]
                    first[s] = k
            hit = np.flatnonzero(first >= 0)
            out.append((hit, first[hit].copy()))
            self._rates(None)
            for _ in range(c["t_gap"]):
                self.net.step(rng)
        return out

    def settle(self, M, phase):
        """Background for SETTLE_MS; returns mean |vbar change| (mV) over its last 10 s."""
        rng = e1.stream(self.seed, e1.TEST_IN, M, SETTLE_PHASE + phase)
        self._rates(None)
        for _ in range(self.c["settle"] - self.c["converge_window"]):
            self.net.step(rng)
        before = self.mem.vbar.copy()
        for _ in range(self.c["converge_window"]):
            self.net.step(rng)
        return float(np.abs(self.mem.vbar - before).mean())

    def randomise_store(self):
        """Matched-density random store: each cell keeps its strong count, inputs drawn uniformly."""
        rng = e1.stream(self.seed, RANDOM_STORE)
        counts = self.store.per_post_count()
        m, n = self.c["m"], self.c["n"]
        keys = [np.sort(rng.choice(m, k, replace=False)) * n + i for i, k in enumerate(counts) if k]
        self.store.keys = np.sort(np.concatenate(keys)) if keys else np.empty(0, np.int64)
        self._load()


def store_digest(store):
    return hashlib.sha256(store.keys.tobytes()).hexdigest()[:16]


def cue_synapses(e, M):
    """Strong synapses from each cued item's half-cue inputs onto its written cells."""
    cued, masks, _ = e1.test_sets(e.c, e.seed, M)
    n = e.c["n"]
    per_cell = []
    for i, mk in zip(cued, masks):
        cue, A = e.items[i][mk], e.A[i]
        if A.size:
            hits = np.isin((cue[:, None] * n + A[None, :]).ravel(), e.store.keys).reshape(cue.size, A.size)
            per_cell.extend(hits.sum(0).tolist())
    per_cell = np.array(per_cell)
    return dict(mean=float(per_cell.mean()), sd=float(per_cell.std()), predicted=24.66,
                frac_below_22=float((per_cell < 22).mean()))


def offsets(e):
    off = e.mem.threshold() - float(e.mem.v_th)
    k = e.store.per_post_count()
    corr = float(np.corrcoef(off, k)[0, 1]) if off.std() > 0 and k.std() > 0 else None
    return dict(mean_mv=float(off.mean()), p95_mv=float(np.percentile(off, 95)), corr_with_strong=corr)


def other_assembly_recall(e, M, out):
    """Label-shuffled chance: recall of the next cued item's assembly under each half cue."""
    cued = out["cued"]
    rec = []
    for idx in range(len(cued)):
        A_other = e.A[cued[(idx + 1) % len(cued)]]
        rec.append(float(np.isin(A_other, e1.responders(out["_half"][idx], e.c["window"])).mean()) if A_other.size else 0.0)
    return float(np.median(rec)), float(np.mean(rec))


def evaluate(e, M, phase, persist=False):
    """P2-E1's evaluation (same cue sets, metrics and criteria) on an E2 network, keeping responses."""
    captured = {}
    orig = e.present

    def present(cues, rng):
        r = orig(cues, rng)
        captured.setdefault("calls", []).append(r)
        return r
    e.present = present
    try:
        out = e1.evaluate(e, M, phase=phase, persist=persist)
    finally:
        del e.present
    out["_half"] = captured["calls"][0]
    return out


def repeated_cue(e, M):
    """Each of REPEAT_ITEMS half cues shown REPEATS times in a row; mean recall per repetition."""
    c = e.c
    cued, masks, _ = e1.test_sets(c, e.seed, M)
    cues, owners = [], []
    for i, mk in list(zip(cued, masks))[:REPEAT_ITEMS]:
        cues += [e.items[i][mk]] * REPEATS
        owners += [i] * REPEATS
    res = e.present(cues, e1.stream(e.seed, e1.TEST_IN, M, 77))
    per_rep = np.zeros(REPEATS)
    for j, (r, i) in enumerate(zip(res, owners)):
        A = e.A[i]
        per_rep[j % REPEATS] += np.isin(A, e1.responders(r, c["window"])).mean() / REPEAT_ITEMS
    return [round(float(x), 4) for x in per_rep]


def summary(out):
    cr = out["criteria"]
    lat_h = [x for x in out["latency_half"] if x is not None]
    lat_f = [x for x in out.get("latency_full", []) if x is not None]
    return dict(criteria=cr, gate_ok=bool(cr["C1"] and cr["C2"] and cr["C3"] and cr["C4"]),
                recall_median={str(w): float(np.median(out["recall"][w])) for w in (25, 50, 100)},
                latency_half_median_ms=float(np.median(lat_h)) if lat_h else None,
                latency_full_median_ms=float(np.median(lat_f)) if lat_f else None,
                hub_cells=out["hub_cells"])


def calibrate(c=CONTRACT, seed=CAL_SEED, grid=J_GRID, loads=GATE_M, results_path=record.RESULTS, log=print):
    main = E2(c, seed)
    passing = {J: True for J in grid}
    for M in loads:
        main.learn(M)
        for J in grid:
            t0 = time.time()
            arm = copy.deepcopy(main)
            arm.set_J(J)
            conv = arm.settle(M, phase=1)
            out = evaluate(arm, M, phase=1, persist=True)
            s = summary(out)
            passing[J] = passing[J] and s["gate_ok"]
            cr = s["criteria"]
            record.append(dict(experiment="P2-E2", kind="calibration_point", timestamp=record.now(),
                               git=record.git_state(), runtime=record.runtime(), seed=seed, M=M, J=J,
                               contract_digest=record.digest(c), converge_mv=conv, **s,
                               wall_s=round(time.time() - t0, 1)), results_path)
            log(f"cal M={M} J={J:.2f}: C1 {cr['C1_frac']:.3f} C2 {cr['C2_frac']:.3f} C3 {cr['C3_frac']:.3f} "
                f"C4 {cr['C4_recall_frac']:.3f}/{cr['C4_spurious_frac']:.3f} conv {conv:.3f} mV")
    ok = [J for J in grid if passing[J]]
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
    J_star = round((best[0] + best[-1]) / 2, 3) if best else None
    record.append(dict(experiment="P2-E2", kind="calibration_verdict", timestamp=record.now(),
                       git=record.git_state(), runtime=record.runtime(), seed=seed,
                       contract_digest=record.digest(c), passing=ok, runs=runs, J_star=J_star), results_path)
    log(f"calibration: passing {ok} -> J* = {J_star}")
    return J_star, ok


def run_seed(c, seed, J, gated, results_path=record.RESULTS, log=print, loads=GATE_M + REPORT_M, gate_loads=GATE_M):
    t0 = time.time()
    c = dict(c, J=J)
    main = E2(c, seed)
    rec = dict(experiment="P2-E2", kind="kill_test_seed", seed=seed, gated=gated, J=J,
               contract_digest=record.digest(dict(c, J=None)), loads={}, validity={})
    unchanged = True
    for M in loads:
        main.learn(M)
        pre = copy.deepcopy(main)
        conv = main.settle(M, phase=1)
        ph1 = evaluate(main, M, phase=1)
        unchanged &= ph1["weights_unchanged"]
        fixed = copy.deepcopy(pre)
        fixed.mem.set_accommodation(None)
        fixed.settle(M, phase=1)
        fx = evaluate(fixed, M, phase=1)
        load = dict(main=summary(ph1), fixed_threshold=summary(fx), converge_mv=conv,
                    offsets=offsets(main), cue_synapses=cue_synapses(main, M),
                    other_assembly_recall=other_assembly_recall(main, M, ph1))
        if M == c["persist_at"]:
            rnd = copy.deepcopy(pre)
            rnd.randomise_store()
            rnd.settle(M, phase=1)
            load["random_store"] = summary(evaluate(rnd, M, phase=1, persist=True))
            load["repeated_cue"] = repeated_cue(copy.deepcopy(main), M)
            keys = main.store.keys.copy()
            main.background(c["t_persist"], e1.stream(seed, e1.TEST_IN, M, 99))
            ph2 = evaluate(main, M, phase=2, persist=True)
            unchanged &= ph2["weights_unchanged"] and bool(np.array_equal(keys, main.store.keys))
            load["after_60s"] = summary(ph2)
            plain = e1.E1(c, seed)
            plain.learn(M)
            rec["validity"]["store_digest"] = store_digest(main.store)
            rec["validity"]["store_equals_p2e1"] = store_digest(plain.store) == store_digest(main.store)
            rec["validity"]["mean_A"] = float(np.mean([a.size for a in main.A]))
            rec["validity"]["mean_elig_frac"] = float(np.mean(main.learn_log["elig_frac"]))
        rec["loads"][str(M)] = load
        cr, fcr = load["main"]["criteria"], load["fixed_threshold"]["criteria"]
        log(f"seed {seed} M={M}: C1 {cr['C1_frac']:.3f} C2 {cr['C2_frac']:.3f} C3 {cr['C3_frac']:.3f} "
            f"C4 {cr['C4_recall_frac']:.3f}/{cr['C4_spurious_frac']:.3f} | fixed C1 {fcr['C1_frac']:.3f} "
            f"C2 {fcr['C2_frac']:.3f} C3 {fcr['C3_frac']:.3f} | conv {conv:.3f} mV | offset {load['offsets']['mean_mv']:.2f} mV")
    L = rec["loads"]
    v = rec["validity"]
    v["weights_unchanged"] = bool(unchanged)
    v["converged"] = all(L[str(M)]["converge_mv"] <= CONVERGE_BAR_MV for M in loads)
    v["elig_ok"] = v["mean_elig_frac"] >= e1.BARS["elig_valid"]
    v["mean_A_ok"] = e1.BARS["mean_A_lo"] <= v["mean_A"] <= e1.BARS["mean_A_hi"]
    valid = all(v[k] for k in ("weights_unchanged", "converged", "elig_ok", "mean_A_ok", "store_equals_p2e1"))
    gate = all(L[str(M)]["main"]["gate_ok"] for M in gate_loads)
    P = str(c["persist_at"])
    a60 = L[P]["after_60s"]["criteria"]
    c5 = bool(a60["C1"] and a60["C2"] and a60["C3"])
    fixed_fails = not (L[P]["fixed_threshold"]["criteria"]["C2"] and L[P]["fixed_threshold"]["criteria"]["C3"])
    random_fails = not L[P]["random_store"]["criteria"]["C1"]
    rec.update(valid=valid, gate=gate, C5=c5, void_A_ok=fixed_fails, void_B_ok=random_fails,
               passed=bool(valid and gate and c5 and fixed_fails and random_fails),
               timestamp=record.now(), git=record.git_state(), runtime=record.runtime(),
               wall_s=round(time.time() - t0, 1))
    record.append(rec, results_path)
    log(f"seed {seed} ({'gated' if gated else 'reported'}): {'PASS' if rec['passed'] else 'FAIL'} valid={valid} "
        f"gate={gate} C5={c5} V-A ok={fixed_fails} V-B ok={random_fails} wall {rec['wall_s']} s")
    return rec


def verdict(recs, J, results_path=record.RESULTS, log=print):
    gated = [r for r in recs if r["gated"]]
    void = not all(r["void_A_ok"] and r["void_B_ok"] for r in gated)
    v = dict(experiment="P2-E2", kind="kill_test_verdict", timestamp=record.now(), git=record.git_state(),
             runtime=record.runtime(), contract_digest=gated[0]["contract_digest"] if gated else None,
             J=J, seeds=[r["seed"] for r in gated], valid=all(r["valid"] for r in gated), void=void,
             passed=bool(gated) and not void and all(r["passed"] for r in gated),
             per_seed={str(r["seed"]): r["passed"] for r in gated})
    record.append(v, results_path)
    log(f"P2-E2 kill test: {'VOID' if void else ('PASS' if v['passed'] else 'FAIL')} (valid={v['valid']}) {v['per_seed']}")
    return v


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("calibrate")
    r = sub.add_parser("run")
    r.add_argument("--J", type=float, required=True)
    r.add_argument("--seeds", type=int, nargs="+", required=True)
    r.add_argument("--gated", action="store_true")
    r.add_argument("--verdict", action="store_true", help="append the verdict over these seeds")
    args = ap.parse_args(argv)
    logf = record.cache_dir("p2_e2") / f"{args.cmd}.log"

    def log(msg):
        print(msg, flush=True)
        with logf.open("a", encoding="utf-8") as fh:
            fh.write(f"{record.now()} {msg}\n")

    if args.cmd == "calibrate":
        calibrate(log=log)
        return 0
    recs = [run_seed(CONTRACT, s, args.J, args.gated, log=log) for s in args.seeds]
    if args.verdict:
        verdict(recs, args.J, log=log)
    return 0


if __name__ == "__main__":
    sys.exit(main())
