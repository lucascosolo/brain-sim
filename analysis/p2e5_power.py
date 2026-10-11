"""P2-E5 power reference, computed before the contract is frozen (docs/plant2/P2-E5-structured-items.md, "Power").

Lives outside plant2/ because the plant2 tree is frozen while P2-E4's gated seeds run. It only calls plant2.power.
Rates are exploratory (red-team seeds 44-45, review/plant2/P2-E5/); they are inputs to a power calculation, not results.

  PYTHONPATH=. .venv/bin/python analysis/p2e5_power.py [--append]
"""
import hashlib
import math
import sys

import numpy as np

from plant2 import power, record

SEED_SD = power.P2E4_SEED_SD
N = dict(half=200, novel=200, old=100)  # P2-E3's test set: 200 half cues (items 1-100 + 100 random), 200 novel cues
BAR = 0.90


def s_criteria(r):
    """S1-S4 as (n, p) pairs; S1 is P2-E2's C1-C4 (C4 = C1 and C2 within the oldest 100)."""
    return dict(
        S1=[(N["half"], r["C1"]), (N["half"], r["C2"]), (N["novel"], r["C3"]), (N["old"], r["C4r"]), (N["old"], r["C4s"])],
        S2=[(N["half"], r["joint"])], S3=[(N["novel"], r["D3"])], S4=[(N["old"], r["D4"])])


def rule(rates):
    """Five-seed pass probability per criterion part and load, and of the whole rule (independence assumed)."""
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


def mean2(a, b):
    return {k: (a[k] + b[k]) / 2 for k in a}


# exploratory per-cue rates (implementation lens, out_s60_seed4{4,5}.json; methodology lens agrees)
S60 = {
    500: mean2(dict(C1=0.955, C2=0.895, C3=1.0, C4r=0.98, C4s=0.86, joint=0.13, D3=1.0, D4=0.04, pj=0.925, pD4=0.88),
               dict(C1=0.975, C2=0.91, C3=1.0, C4r=0.99, C4s=0.92, joint=0.10, D3=1.0, D4=0.01, pj=0.935, pD4=0.95)),
    1000: mean2(dict(C1=0.925, C2=0.495, C3=0.995, C4r=0.93, C4s=0.41, joint=0.0, D3=0.985, D4=0.0, pj=0.16, pD4=0.11),
                dict(C1=0.955, C2=0.47, C3=1.0, C4r=0.95, C4s=0.35, joint=0.0, D3=0.995, D4=0.0, pj=0.12, pD4=0.08)),
}


def idealised(base):
    """A system as item-specific on correlated items as P2-E3 is on independent items."""
    out = {}
    for M, r in base.items():
        out[M] = clip(dict(C1=r["C1"], C2=r["C2"], C3=r["C3"], C4r=r["old_recall"], C4s=r["C2"], joint=r["joint"],
                           D3=r["D3"], D4=r["D4"]))
    return out


def oracle():
    """The plateau-set store at the frozen readout on the structured index (the index is unchanged)."""
    return {M: clip(dict(r, joint=r["pj"], D4=r["pD4"])) for M, r in S60.items()}


def main_arm():
    return {M: clip({k: v for k, v in r.items() if k not in ("pj", "pD4")}) for M, r in S60.items()}


def p_invalid(mean=0.11, sd=0.03, bar=0.2, seeds=5):
    """Convergence under P2-E3's unchanged rule (mean |dvbar| <= 0.2 mV), normal model of the M = 1,000 values."""
    per = 0.5 * math.erfc((bar - mean) / (sd * math.sqrt(2)))
    return dict(model=dict(mean=mean, sd=sd, bar=bar), per_seed=per, any_of_5=1 - (1 - per) ** seeds,
                observed_max_mean_abs_dvbar=0.130)


def ranking(sims=20000, rng_seed=7):
    """Probability of each predeclared reading per load, by simulation of per-seed losses on 200 half cues.

    L_c = J_ub* - J_own*, L_i = max(0, 0.90 - J_ub*), L_o = assumed net online index loss (unmeasured on structured
    items; scenarios). A seed's dominant failure is the largest loss if it exceeds the next by >= 0.05; a load's
    reading is X-DOMINANT when X dominates on >= 4 of 5 seeds, NO MATERIAL LOSS when every loss < 0.05 on >= 4 of 5,
    else SPLIT. J_ub* and J_own* are grid-best joints (seed 44 grid, cyclic and random order; optimistic)."""
    rng = np.random.default_rng(rng_seed)
    best = {500: dict(ub=0.9975, own=0.56), 1000: dict(ub=0.59, own=0.025)}
    out = {}
    for M, b in best.items():
        for lo in (0.07, 0.15, 0.25, 0.35, 0.45):
            def draw(p):
                lp = math.log(p / (1 - p))
                eff = rng.normal(0, SEED_SD, (sims, 5))
                return rng.binomial(N["half"], 1 / (1 + np.exp(-(lp + eff)))) / N["half"]
            ub, own = draw(b["ub"]), draw(b["own"])
            o = rng.binomial(N["half"], lo, (sims, 5)) / N["half"]
            L = np.stack([np.maximum(0, ub - own), np.maximum(0, BAR - ub), o], -1)  # c, i, o
            srt = np.sort(L, -1)
            dom = np.where(srt[..., -1] - srt[..., -2] >= 0.05, L.argmax(-1), -1)
            none = (L < 0.05).all(-1)
            res = dict(CONTAMINATION=0, INDEX=0, OPERATING_POINT=0, NO_MATERIAL_LOSS=0, SPLIT=0)
            cnt = [(dom == j).sum(-1) for j in range(3)]
            for j, name in enumerate(("CONTAMINATION", "INDEX", "OPERATING_POINT")):
                res[name] = float((cnt[j] >= 4).mean())
            res["NO_MATERIAL_LOSS"] = float(((none.sum(-1) >= 4) & ~np.any([c >= 4 for c in cnt], 0)).mean())
            res["SPLIT"] = 1 - sum(res.values())
            material_index = float(((L[..., 1] >= 0.10).sum(-1) >= 4).mean())
            out[f"{M}:L_o={lo}"] = dict(readings=res, index_material=material_index)
    return out


def reference():
    ideal, ideal_e3 = idealised(power.P2E4_RATES), idealised(power.P2E4_RATES_E3_ONLY)
    parts_i, p_i = rule(ideal)
    parts_e3, p_e3 = rule(ideal_e3)
    parts_o, p_o = rule(oracle())
    parts_o500, p_o500 = rule({500: oracle()[500]})
    parts_m, p_m = rule(main_arm())
    s1_500 = power.p_rule(s_criteria(main_arm()[500])["S1"], seeds=5, seed_sd=SEED_SD)
    return dict(seed_sd=SEED_SD, counts=N, bar=BAR,
                idealised=dict(rates=ideal, parts=parts_i, p_pass=p_i),
                idealised_e3_only=dict(rates=ideal_e3, parts=parts_e3, p_pass=p_e3),
                oracle_plateau_frozen=dict(rates=oracle(), parts=parts_o, p_pass=p_o, p_pass_M500_only=p_o500),
                main_arm=dict(rates=main_arm(), parts=parts_m, p_pass=p_m, p_S1_M500=s1_500),
                # the s = 100 arm on the gated seeds is P2-E3's generator: P2-E3's gate (D1/2, D3, D4, D5 = C1-C4) is the
                # same rule at these rates
                replication_s100=dict(p_holds=p_i),
                invalid=p_invalid(), ranking=ranking())


if __name__ == "__main__":
    ref = reference()
    contract = record.REPO / "docs" / "plant2" / "P2-E5-structured-items.md"
    rec = dict(experiment="P2-E5", kind="power_reference", **ref,
               contract_sha256=hashlib.sha256(contract.read_bytes()).hexdigest() if contract.exists() else None,
               timestamp=record.now(), git=record.git_state(), runtime=record.runtime())
    if "--append" in sys.argv:
        record.append(rec)
    import json
    print(json.dumps({k: v for k, v in rec.items() if k not in ("git", "runtime")}, indent=1, default=str))
