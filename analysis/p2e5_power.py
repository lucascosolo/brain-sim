"""P2-E5 power reference, computed before the contract is frozen (docs/plant2/P2-E5-structured-items.md, "Power").

Lives outside plant2/ because the plant2 tree is frozen while P2-E4's gated seeds run. It only calls plant2.power.
Rates are exploratory (red-team seeds 44-45, review/plant2/P2-E5/; grid bests from the completeness lens's grid.py,
seed 44 and seed 45, cyclic order); they are inputs to a power calculation, not results.

  PYTHONPATH=. .venv/bin/python analysis/p2e5_power.py [--append]
"""
import hashlib
import json
import math
import sys

import numpy as np

from plant2 import power, record

SEED_SD = power.P2E4_SEED_SD
N = dict(half=200, novel=200, old=100)  # P2-E3's test set: 200 half cues (items 1-100 + 100 random), 200 novel cues
BAR = 0.90
BAR_CUES = 180  # 90 % of 200, the joint bar in cues
MARGIN, MATERIAL = 10, 20  # Part B, in cues of 200: dominance margin and materiality


def s_criteria(r):
    """S1-S4 as (n, p) pairs; S1 is P2-E2's C1-C4 (C4 = C1 and C2 within the oldest 100)."""
    return dict(
        S1=[(N["half"], r["C1"]), (N["half"], r["C2"]), (N["novel"], r["C3"]), (N["old"], r["C4r"]), (N["old"], r["C4s"])],
        S2=[(N["half"], r["joint"])], S3=[(N["novel"], r["D3"])], S4=[(N["old"], r["D4"])])


def rule(rates):
    """Five-seed pass probability per criterion part and load, and of the whole rule (independence across parts)."""
    parts, total = {}, 1.0
    for M, r in rates.items():
        for name, crit in s_criteria(r).items():
            labels = ["C1", "C2", "C3", "C4_recall", "C4_spurious"] if name == "S1" else [name]
            for lab, (n, p) in zip(labels, crit):
                v = power.p_rule([(n, p)], seeds=5, seed_sd=SEED_SD)
                parts[f"{M}:{lab}"] = v
                total *= v
    return parts, total


def clip(r):
    return {k: min(max(v, 0.001), 0.999) for k, v in r.items()}


def mean_runs(runs):
    return {k: float(np.mean([r[k] for r in runs])) for k in runs[0]}


# Exploratory per-cue rates at s = 60, F = 10: implementation lens (out_s60_seed4{4,5}.json) and methodology lens
# (s60_F10.jsonl), seeds 44 and 45. pj/pD4 are the plateau-set store at the frozen readout.
RUNS = {
    500: dict(
        impl44=dict(C1=0.955, C2=0.895, C3=1.0, C4r=0.98, C4s=0.86, joint=0.13, D3=1.0, D4=0.04, pj=0.925, pD4=0.88),
        impl45=dict(C1=0.975, C2=0.91, C3=1.0, C4r=0.99, C4s=0.92, joint=0.10, D3=1.0, D4=0.01, pj=0.935, pD4=0.95),
        meth44=dict(C1=0.97, C2=0.92, C3=1.0, C4r=0.99, C4s=0.91, joint=0.145, D3=1.0, D4=0.02, pj=0.93, pD4=0.92),
        meth45=dict(C1=0.945, C2=0.915, C3=1.0, C4r=0.94, C4s=0.91, joint=0.105, D3=1.0, D4=0.05, pj=0.94, pD4=0.92)),
    1000: dict(
        impl44=dict(C1=0.925, C2=0.495, C3=0.995, C4r=0.93, C4s=0.41, joint=0.0, D3=0.985, D4=0.0, pj=0.16, pD4=0.11),
        impl45=dict(C1=0.955, C2=0.47, C3=1.0, C4r=0.95, C4s=0.35, joint=0.0, D3=0.995, D4=0.0, pj=0.12, pD4=0.08),
        meth44=dict(C1=0.935, C2=0.48, C3=0.995, C4r=0.95, C4s=0.47, joint=0.0, D3=0.99, D4=0.0, pj=0.18, pD4=0.16),
        meth45=dict(C1=0.915, C2=0.465, C3=1.0, C4r=0.93, C4s=0.40, joint=0.0, D3=0.985, D4=0.0, pj=0.155, pD4=0.09)),
}
S60 = {M: mean_runs(list(v.values())) for M, v in RUNS.items()}

# Grid bests (maximum joint over the 72 points; contract Part A), cyclic order, seeds 44 and 45 (completeness lens
# grid.py; seed 45 run by the lead for the verification). Filled from grid_s60_seed4{4,5}_cyclic.json.
GRID = {
    500: dict(ub=[1.0, None], own=[0.565, None], ub_frozen=[0.925, None], own_frozen=[0.13, None]),
    1000: dict(ub=[0.60, None], own=[0.04, None], ub_frozen=[0.16, None], own_frozen=[0.0, None]),
}


def idealised(base):
    """A system as item-specific on correlated items as P2-E3 is on independent items."""
    return {M: clip(dict(C1=r["C1"], C2=r["C2"], C3=r["C3"], C4r=r["old_recall"], C4s=r["C2"], joint=r["joint"],
                         D3=r["D3"], D4=r["D4"])) for M, r in base.items()}


def oracle(rates=S60):
    """The plateau-set store at the frozen readout on the structured index (the index is unchanged)."""
    return {M: clip({k: v for k, v in dict(r, joint=r["pj"], D4=r["pD4"]).items() if k not in ("pj", "pD4")})
            for M, r in rates.items()}


def main_arm(rates=S60):
    return {M: clip({k: v for k, v in r.items() if k not in ("pj", "pD4")}) for M, r in rates.items()}


def p_s1_dependent(r, sims=200000, rng_seed=3):
    """P(S1 holds on all five seeds at one load) with a seed effect shared by every S1 part, and C4 scored on the
    oldest 100 of C2's (and C1's) 200 half cues."""
    rng = np.random.default_rng(rng_seed)
    z = rng.normal(0, SEED_SD, (sims, 5))

    def eff(p):
        p = min(max(p, 0.001), 0.999)
        return 1 / (1 + np.exp(-(math.log(p / (1 - p)) + z)))
    ok = np.ones((sims, 5), bool)
    for whole, old in (("C1", "C4r"), ("C2", "C4s")):
        p_old, p_rest = r[old], min(max(2 * r[whole] - r[old], 0.001), 0.999)
        k_old = rng.binomial(N["old"], eff(p_old))
        k_rest = rng.binomial(N["half"] - N["old"], eff(p_rest))
        ok &= (k_old + k_rest >= BAR_CUES) & (k_old >= 90)
    ok &= rng.binomial(N["novel"], eff(r["C3"])) >= BAR_CUES
    return float(ok.all(1).mean())


def p_invalid(mean=0.11, sds=(0.03, 0.04), bar=0.2, seeds=5):
    """Convergence under P2-E3's unchanged rule (mean |dvbar| <= 0.2 mV), normal model of the M = 1,000 values.
    Gated-condition exploratory values 0.090, 0.096, 0.120, 0.122; the largest exploratory value overall is 0.130
    (s = 40, seed 45)."""
    out = {}
    for sd in sds:
        per = 0.5 * math.erfc((bar - mean) / (sd * math.sqrt(2)))
        out[f"sd_{sd}"] = dict(per_seed=per, any_of_5=1 - (1 - per) ** seeds)
    return dict(model_mean=mean, bar=bar, **out)


def p_replication_per_seed_load(rates):
    """P(P2-E3's gate holds on one seed at one load) at the given independent-item rates."""
    out = {}
    for M, r in rates.items():
        out[M] = float(np.prod([power.p_criterion(n, p, BAR, SEED_SD) for crit in s_criteria(r).values() for n, p in crit]))
    return out


def ranking(grid=GRID, sims=20000, rng_seed=7, lo_levels=(0.07, 0.15, 0.25, 0.35, 0.45), ub_override=None,
            excl=None):
    """Probability of each Part B reading per load, simulated in integer cues of 200.

    Per seed: Jub, Jown ~ Binomial(200, grid-best rate with a logit seed effect); L_c = max(0, min(Jub, 180) -
    min(Jown, 180)); L_i = max(0, 180 - Jub); L_o ~ Binomial(200, lo) (net online loss, clipped at 0). A seed's
    dominant failure is X if L_X >= 20 and L_X exceeds both others by >= 10; a seed is excluded (NOT ATTRIBUTABLE) with
    probability excl[M]. A load reads X-DOMINANT if X dominates on >= 4 seeds and on every attributable seed beyond
    the fifth's allowance (>= 4 of the attributable seeds, with >= 4 attributable); NO MATERIAL LOSS if every loss is
    < 20 on >= 4 attributable seeds; NOT ATTRIBUTABLE if < 4 seeds are attributable; else SPLIT."""
    rng = np.random.default_rng(rng_seed)
    out = {}
    for M, g in grid.items():
        ub_rate = ub_override if (ub_override is not None and M == 1000) else float(np.mean([v for v in g["ub"] if v is not None]))
        own_rate = float(np.mean([v for v in g["own"] if v is not None]))
        for lo in lo_levels:
            def draw(p):
                p = min(max(p, 0.001), 0.999)
                lp = math.log(p / (1 - p))
                return rng.binomial(N["half"], 1 / (1 + np.exp(-(lp + rng.normal(0, SEED_SD, (sims, 5))))))
            ub, own = draw(ub_rate), draw(own_rate)
            Lc = np.maximum(0, np.minimum(ub, BAR_CUES) - np.minimum(own, BAR_CUES))
            Li = np.maximum(0, BAR_CUES - ub)
            Lo = rng.binomial(N["half"], lo, (sims, 5))
            L = np.stack([Lc, Li, Lo], -1)
            dom = np.full((sims, 5), -1)
            for j in range(3):
                others = np.delete(L, j, -1).max(-1)
                dom = np.where((L[..., j] >= MATERIAL) & (L[..., j] - others >= MARGIN), j, dom)
            attr = rng.random((sims, 5)) >= (excl or {}).get(M, 0.0)
            n_attr = attr.sum(-1)
            res = {}
            for j, name in enumerate(("CONTAMINATION", "INDEX", "OPERATING_POINT")):
                res[name] = ((dom == j) & attr).sum(-1)
            none = ((L < MATERIAL).all(-1) & attr).sum(-1)
            enough = n_attr >= 4
            read = dict(NOT_ATTRIBUTABLE=float((~enough).mean()))
            taken = ~enough
            for name in ("CONTAMINATION", "INDEX", "OPERATING_POINT"):
                hit = enough & ~taken & (res[name] >= 4)
                read[name + "_DOMINANT"] = float(hit.mean())
                taken |= hit
            hit = enough & ~taken & (none >= 4)
            read["NO_MATERIAL_LOSS"] = float(hit.mean())
            taken |= hit
            read["SPLIT"] = float((~taken).mean())
            material = {nm: float((((L[..., j] >= MATERIAL) & attr).sum(-1) >= 4).mean())
                        for j, nm in enumerate(("contamination", "index", "operating_point"))}
            out[f"{M}:L_o={lo}"] = dict(readings=read, material=material, ub_rate=ub_rate, own_rate=own_rate)
    return out


def reference():
    ideal, ideal_e3 = idealised(power.P2E4_RATES), idealised(power.P2E4_RATES_E3_ONLY)
    parts_i, p_i = rule(ideal)
    parts_e3, p_e3 = rule(ideal_e3)
    parts_o, p_o = rule(oracle())
    _, p_o500 = rule({500: oracle()[500]})
    parts_m, p_m = rule(main_arm())
    s1_500 = {}
    for name, r in list(RUNS[500].items()) + [("all_four", S60[500])]:
        s1_500[name] = dict(independent=power.p_rule(s_criteria(clip(r))["S1"], seeds=5, seed_sd=SEED_SD),
                            dependent=p_s1_dependent(clip(r)))
    oracle_500_by_run = {name: rule({500: oracle({500: r})[500]})[1] for name, r in RUNS[500].items()}
    rep_seed_load = p_replication_per_seed_load(ideal_e3)
    excl = {M: 1 - v for M, v in rep_seed_load.items()}
    rank = ranking(excl=excl)
    rank_ub_sens = {str(ub): ranking(lo_levels=(0.25,), ub_override=ub, excl=excl)["1000:L_o=0.25"]
                    for ub in (0.50, 0.53, 0.55, 0.59)}
    return dict(seed_sd=SEED_SD, counts=N, bar=BAR, part_b=dict(margin_cues=MARGIN, material_cues=MATERIAL),
                runs=RUNS, grid=GRID,
                idealised=dict(rates=ideal, parts=parts_i, p_pass=p_i),
                idealised_e3_only=dict(rates=ideal_e3, parts=parts_e3, p_pass=p_e3),
                oracle_plateau_frozen=dict(rates=oracle(), parts=parts_o, p_pass=p_o, p_pass_M500_only=p_o500,
                                           p_pass_M500_only_by_run=oracle_500_by_run),
                main_arm=dict(rates=main_arm(), parts=parts_m, p_pass=p_m, p_S1_M500=s1_500),
                replication_s100=dict(p_holds_pooled=p_i, p_holds_e3_only=p_e3, p_per_seed_load_e3_only=rep_seed_load),
                invalid=p_invalid(), ranking=rank, ranking_ub_sensitivity_M1000_Lo025=rank_ub_sens)


if __name__ == "__main__":
    if any(v is None for g in GRID.values() for vs in g.values() for v in vs):
        raise SystemExit("GRID has unfilled seed-45 values")
    ref = reference()
    contract = record.REPO / "docs" / "plant2" / "P2-E5-structured-items.md"
    rec = dict(experiment="P2-E5", kind="power_reference", **ref,
               contract_sha256=hashlib.sha256(contract.read_bytes()).hexdigest(),
               timestamp=record.now(), git=record.git_state(), runtime=record.runtime())
    if "--append" in sys.argv:
        record.append(rec)
    print(json.dumps({k: v for k, v in rec.items() if k not in ("git", "runtime", "runs")}, indent=1, default=str))
