"""P2-E1: one-shot episodic storage by BTSP. Contract: docs/plant2/P2-E1-btsp.md (predeclared).

    python3 -m plant2.experiments.p2_e1_btsp                 # kill test, seeds 1-5
    python3 -m plant2.experiments.p2_e1_btsp --capacity      # reported capacity curve, seed 1

Random streams are keyed by purpose, so learning the first M items is the same whatever is run
after it, and the capacity run's M = 1,000 point reproduces the kill test's seed 1 numbers.
"""
import argparse
import sys
import time

import numpy as np

from plant2 import record
from plant2.btsp import BinarySynapses, btsp_update
from plant2.engine import LIF, Net, Poisson, Projection

CONTRACT = dict(
    m=4000, n=4000, a=100, r_on=40.0, r_off=0.5, t_item=200, elig_min=3, f_q=0.005, p_flip=0.5,
    J=1.12, M=1000, n_old=100, n_rand=100, n_novel=200, t_cue=100, t_gap=200, window=50,
    t_persist=60_000, tau_m=20.0, v_rest=-70.0, v_reset=-65.0, v_th=-50.0, t_ref=2,
)
BARS = dict(recall=0.80, item_frac=0.90, spurious_of_A=0.5, ignition_of_meanA=0.5,
            elig_valid=0.95, mean_A_lo=18.5, mean_A_hi=21.5)
SEEDS = (1, 2, 3, 4, 5)
CAPACITY_M = (250, 500, 1000, 2000, 4000)
# stream ids
PATTERNS, LEARN_IN, PLATEAU, COIN, TEST_PICK, TEST_IN, NOVEL = range(7)


def stream(seed, sid, *extra):
    return np.random.default_rng([seed, sid, *extra])


class E1:
    def __init__(self, cfg, seed, trained=True):
        self.c, self.seed = cfg, seed
        c = cfg
        self.inp = Poisson("inp", c["m"])
        self.mem = LIF("mem", c["n"], d_max=1, tau_m=c["tau_m"], v_rest=c["v_rest"],
                       v_reset=c["v_reset"], v_th=c["v_th"], t_ref=c["t_ref"])
        self.store = BinarySynapses(c["m"], c["n"])
        self.proj = Projection(self.inp, self.mem, [], [], c["J"], 1)
        self.net = Net([self.inp], [self.mem], [self.proj])
        self.trained = trained
        self._pat = stream(seed, PATTERNS)
        self._learn_in, self._plat, self._coin = stream(seed, LEARN_IN), stream(seed, PLATEAU), stream(seed, COIN)
        nov = stream(seed, NOVEL)
        self.novel = [np.sort(nov.choice(c["m"], c["a"], replace=False)) for _ in range(c["n_novel"])]
        self.items, self.A = [], []
        self.plateaus_per_cell = np.zeros(c["n"], np.int64)
        self.learn_log = dict(elig_frac=[], bg_eligible=[], potentiated=[], depressed=[], mem_spikes=[])

    def _load(self):
        indptr, post = self.store.csr()
        self.proj.set_csr(indptr, post, self.c["J"], 1)

    def _rates(self, active):
        r = np.full(self.c["m"], self.c["r_off"])
        if active is not None:
            r[active] = self.c["r_on"]
        self.inp.set_rates(r)

    def learn_one(self):
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
        if not self.trained:
            plateau = plateau[:0]
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

    def learn(self, upto):
        while len(self.items) < upto:
            self.learn_one()

    def present(self, cues, rng):
        """Show each cue for t_cue ms then t_gap ms of background; return per-cue first-spike times.

        Each entry is (cells, ms after onset) for memory cells that spiked in [onset, onset + t_cue).
        """
        c = self.c
        self.net.quiet()
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

    def background(self, ticks, rng):
        self._rates(None)
        for _ in range(ticks):
            self.net.step(rng)


def responders(entry, window):
    cells, t = entry
    return cells[t < window]


def test_sets(c, seed, M):
    pick = stream(seed, TEST_PICK, M)
    old = np.arange(min(c["n_old"], M))
    rest = np.arange(c["n_old"], M)
    rand = np.sort(pick.choice(rest, min(c["n_rand"], rest.size), replace=False)) if rest.size else rest
    cued = np.concatenate([old, rand])
    masks = [np.sort(pick.choice(c["a"], c["a"] // 2, replace=False)) for _ in range(cued.size)]
    nmasks = [np.sort(pick.choice(c["a"], c["a"] // 2, replace=False)) for _ in range(c["n_novel"])]
    return cued, masks, nmasks


def evaluate(e, M, phase, persist=False):
    """Run the half/full/novel cues at load M; return per-item measures and criteria."""
    c, seed = e.c, e.seed
    cued, masks, nmasks = test_sets(c, seed, M)
    half = [e.items[i][mk] for i, mk in zip(cued, masks)]
    novel_half = [e.novel[j][mk] for j, mk in enumerate(nmasks)]
    keys_before = e.store.keys.copy()
    rng = stream(seed, TEST_IN, M, phase)
    r_half = e.present(half, rng)
    r_novel = e.present(novel_half, rng)
    r_full = None if persist else e.present([e.items[i] for i in cued], rng)
    unchanged = bool(np.array_equal(keys_before, e.store.keys))
    w = c["window"]
    out = dict(cued=cued.tolist(), A_size=[], recall={25: [], 50: [], 100: []}, spurious=[], ignition=[],
               latency_half=[], latency_full=[], weights_unchanged=unchanged)
    k_hit = np.zeros(e.plateaus_per_cell.max() + 1, np.int64)
    k_all = np.zeros_like(k_hit)
    for idx, i in enumerate(cued):
        A = e.A[i]
        out["A_size"].append(int(A.size))
        for win in (25, 50, 100):
            R = responders(r_half[idx], win)
            out["recall"][win].append(float(np.isin(A, R).mean()) if A.size else 0.0)
        R = responders(r_half[idx], w)
        out["spurious"].append(int(np.setdiff1d(R, A).size))
        kA = e.plateaus_per_cell[A]
        np.add.at(k_all, kA, 1)
        np.add.at(k_hit, kA[np.isin(A, R)], 1)
        cells, t = r_half[idx]
        hitA = np.isin(cells, A)
        out["latency_half"].append(float(np.median(t[hitA])) if hitA.any() else None)
        if r_full is not None:
            cells, t = r_full[idx]
            hitA = np.isin(cells, A)
            out["latency_full"].append(float(np.median(t[hitA])) if hitA.any() else None)
    out["recall_full50"] = ([float(np.isin(e.A[i], responders(r_full[k], w)).mean()) if e.A[i].size else 0.0
                            for k, i in enumerate(cued)] if r_full is not None else None)
    for entry in r_novel:
        out["ignition"].append(int(responders(entry, w).size))
    # hubs: cells answering more than 5 % of the half cues (learned and novel together)
    hits = np.zeros(c["n"], np.int64)
    for entry in r_half + r_novel:
        hits[responders(entry, w)] += 1
    out["hub_cells"] = int((hits > 0.05 * (len(r_half) + len(r_novel))).sum())
    # reported: written-cell recall at 50 ms by the cell's total plateau count, item recall by |A|
    out["cell_recall_by_plateaus"] = {int(k): [int(k_hit[k]), int(k_all[k])] for k in np.flatnonzero(k_all)}
    sizes, rec = np.array(out["A_size"]), np.array(out["recall"][50])
    bins = ((0, 15), (16, 20), (21, 25), (26, 10_000))
    out["recall_by_A_size"] = {f"{lo}-{hi}": [float(np.median(rec[(sizes >= lo) & (sizes <= hi)])), int(((sizes >= lo) & (sizes <= hi)).sum())]
                               for lo, hi in bins if ((sizes >= lo) & (sizes <= hi)).any()}
    out["criteria"] = criteria(out, e, c)
    return out


def criteria(out, e, c):
    rec = np.array(out["recall"][50])
    A = np.array(out["A_size"])
    sp = np.array(out["spurious"])
    ig = np.array(out["ignition"])
    mean_A = float(np.mean([a.size for a in e.A])) if e.A else 0.0
    old = np.array(out["cued"]) < c["n_old"]
    c1 = float((rec >= BARS["recall"]).mean())
    c2 = float((sp < BARS["spurious_of_A"] * A).mean())
    c3 = float((ig < BARS["ignition_of_meanA"] * mean_A).mean())
    c4a = float((rec[old] >= BARS["recall"]).mean()) if old.any() else None
    c4b = float((sp[old] < BARS["spurious_of_A"] * A[old]).mean()) if old.any() else None
    f = BARS["item_frac"]
    return dict(
        C1_frac=c1, C1=c1 >= f, C2_frac=c2, C2=c2 >= f, C3_frac=c3, C3=c3 >= f,
        C4_recall_frac=c4a, C4_spurious_frac=c4b, C4=(c4a is not None and c4a >= f and c4b >= f),
        mean_A=mean_A, median_recall50=float(np.median(rec)), median_spurious=float(np.median(sp)),
        median_ignition=float(np.median(ig)), max_ignition=int(ig.max()),
    )


def learning_summary(e):
    lg = e.learn_log
    k = e.store.per_post_count()
    return dict(
        mean_elig_frac=float(np.mean(lg["elig_frac"])), mean_bg_eligible=float(np.mean(lg["bg_eligible"])),
        potentiated=int(np.sum(lg["potentiated"])), depressed=int(np.sum(lg["depressed"])),
        mem_rate_hz_learning=float(np.sum(lg["mem_spikes"]) / (len(lg["mem_spikes"]) * e.c["t_item"] / 1000.0) / e.c["n"]),
        store_size=e.store.size, strong_per_cell_mean=float(k.mean()),
        strong_per_cell_pct=[int(x) for x in np.percentile(k, [5, 50, 95, 100])],
        plateaus_per_cell_max=int(e.plateaus_per_cell.max()),
    )


def run_seed(c, seed, results_path, log):
    t0 = time.time()
    e = E1(c, seed)
    e.learn(c["M"])
    t_learn = time.time() - t0
    phase1 = evaluate(e, c["M"], phase=1)
    keys = e.store.keys.copy()
    e.background(c["t_persist"], stream(seed, TEST_IN, c["M"], 99))
    phase2 = evaluate(e, c["M"], phase=2, persist=True)
    unchanged = phase1["weights_unchanged"] and phase2["weights_unchanged"] and bool(np.array_equal(keys, e.store.keys))
    twin = E1(c, seed, trained=False)  # same network, never written: every weight is 0
    cued, masks, _ = test_sets(c, seed, c["M"])
    half = [e.items[i][mk] for i, mk in zip(cued[:20], masks[:20])]
    twin_resp = [int(responders(r, c["window"]).size) for r in twin.present(half, stream(seed, TEST_IN, 0, 7))]
    ls = learning_summary(e)
    p1, p2 = phase1["criteria"], phase2["criteria"]
    validity = dict(
        elig_frac_ok=ls["mean_elig_frac"] >= BARS["elig_valid"], weights_unchanged=unchanged,
        mean_A_ok=BARS["mean_A_lo"] <= p1["mean_A"] <= BARS["mean_A_hi"],
    )
    c5 = bool(p2["C1"] and p2["C2"] and p2["C3"])
    passed = bool(all(validity.values()) and p1["C1"] and p1["C2"] and p1["C3"] and p1["C4"] and c5)
    rec = dict(
        experiment="P2-E1", kind="kill_test_seed", timestamp=record.now(), git=record.git_state(),
        seed=seed, contract_digest=record.digest(c), contract=c, bars=BARS,
        valid=all(validity.values()), validity=validity, passed=passed,
        criteria=dict(phase1=p1, after_60s=p2, C5=c5),
        report=dict(
            learning=ls,
            recall_median={str(w): float(np.median(phase1["recall"][w])) for w in (25, 50, 100)},
            recall_full50_median=float(np.median(phase1["recall_full50"])),
            latency_half_median_ms=float(np.median([x for x in phase1["latency_half"] if x is not None])),
            latency_full_median_ms=float(np.median([x for x in phase1["latency_full"] if x is not None])),
            hub_cells=phase1["hub_cells"], never_trained_twin_responders=twin_resp,
            recall_old_median=float(np.median(np.array(phase1["recall"][50])[:c["n_old"]])),
            recall_rest_median=float(np.median(np.array(phase1["recall"][50])[c["n_old"]:])),
            cell_recall_by_plateaus=phase1["cell_recall_by_plateaus"],
            recall_by_A_size=phase1["recall_by_A_size"],
        ),
        wall_s=dict(learn=round(t_learn, 1), total=round(time.time() - t0, 1)),
    )
    np.savez_compressed(record.cache_dir("p2_e1") / f"seed{seed}.npz",
                        A_size=phase1["A_size"], recall50=phase1["recall"][50], spurious=phase1["spurious"],
                        ignition=phase1["ignition"], recall50_after=phase2["recall"][50],
                        plateaus_per_cell=e.plateaus_per_cell, strong_per_cell=e.store.per_post_count())
    record.append(rec, results_path)
    log(f"seed {seed}: {'PASS' if passed else 'FAIL'} valid={rec['valid']} "
        f"C1 {p1['C1_frac']:.3f} C2 {p1['C2_frac']:.3f} C3 {p1['C3_frac']:.3f} "
        f"C4 {p1['C4_recall_frac']:.3f}/{p1['C4_spurious_frac']:.3f} C5 {c5} "
        f"| median recall {p1['median_recall50']:.3f} spurious {p1['median_spurious']:.1f} "
        f"ignition {p1['median_ignition']:.1f} meanA {p1['mean_A']:.2f} | {rec['wall_s']}")
    return rec


def run_kill_test(c=CONTRACT, seeds=SEEDS, results_path=record.RESULTS, log=print):
    recs = [run_seed(c, s, results_path, log) for s in seeds]
    verdict = dict(
        experiment="P2-E1", kind="kill_test_verdict", timestamp=record.now(), git=record.git_state(),
        contract_digest=record.digest(c), seeds=list(seeds),
        passed=all(r["passed"] for r in recs), valid=all(r["valid"] for r in recs),
        per_seed={str(r["seed"]): r["passed"] for r in recs},
    )
    record.append(verdict, results_path)
    log(f"P2-E1 kill test: {'PASS' if verdict['passed'] else 'FAIL'} (valid={verdict['valid']}) {verdict['per_seed']}")
    return verdict, recs


def run_capacity(c=CONTRACT, seed=1, points=CAPACITY_M, results_path=record.RESULTS, log=print):
    e = E1(c, seed)
    out = []
    for M in points:
        t0 = time.time()
        e.learn(M)
        ph = evaluate(e, M, phase=1)
        cr = ph["criteria"]
        rec = dict(experiment="P2-E1", kind="capacity_point", timestamp=record.now(), git=record.git_state(),
                   seed=seed, M=M, contract_digest=record.digest(c), criteria=cr,
                   all_C1_to_C4=bool(cr["C1"] and cr["C2"] and cr["C3"] and cr["C4"]),
                   learning=learning_summary(e), hub_cells=ph["hub_cells"],
                   recall_median_50=cr["median_recall50"], wall_s=round(time.time() - t0, 1))
        record.append(rec, results_path)
        log(f"capacity M={M}: C1 {cr['C1_frac']:.3f} C2 {cr['C2_frac']:.3f} C3 {cr['C3_frac']:.3f} "
            f"C4 {cr['C4_recall_frac']:.3f}/{cr['C4_spurious_frac']:.3f} median recall {cr['median_recall50']:.3f} "
            f"spurious {cr['median_spurious']:.1f} ignition {cr['median_ignition']:.1f} hubs {ph['hub_cells']}")
        out.append(rec)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--capacity", action="store_true")
    ap.add_argument("--seeds", type=int, nargs="*", default=list(SEEDS))
    args = ap.parse_args(argv)
    logf = record.cache_dir("p2_e1") / ("capacity.log" if args.capacity else "kill_test.log")

    def log(msg):
        print(msg, flush=True)
        with logf.open("a", encoding="utf-8") as fh:
            fh.write(f"{record.now()} {msg}\n")

    if args.capacity:
        run_capacity(log=log)
    else:
        verdict, _ = run_kill_test(seeds=tuple(args.seeds), log=log)
        return 0 if verdict["passed"] else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
