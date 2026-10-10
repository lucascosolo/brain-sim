"""Power of predeclared acceptance rules (owner's ruling of 2026-10-10: power checks must account
for dependent measurements and the full all-seeds, all-loads acceptance rule).

Binomial criteria (each cue scored once, distinct items within a block) use exact binomial tails.
A seed random effect on the logit scale covers seed-to-seed spread. Repeated-measure criteria (the
same item cued many times) use a beta model of per-item reliability with a given intraclass
correlation, by Monte Carlo.
"""
import math

import numpy as np


def binom_tail(n, k, p):
    """P(Binomial(n, p) >= k)."""
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    return float(sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1)))


def bar_count(n, frac):
    """Smallest count meeting a fraction bar (>= frac of n)."""
    return math.ceil(frac * n - 1e-9)


def p_criterion(n, p, frac=0.90, seed_sd=0.0, grid=41):
    """P(one seed passes) for a fraction bar on n independent cues, averaging over a logit-normal seed effect."""
    k = bar_count(n, frac)
    if seed_sd <= 0:
        return binom_tail(n, k, p)
    z, w = np.polynomial.hermite_e.hermegauss(grid)
    w = w / w.sum()
    lp = math.log(p / (1 - p))
    return float(sum(wi * binom_tail(n, k, 1 / (1 + math.exp(-(lp + seed_sd * zi)))) for zi, wi in zip(z, w)))


def p_rule(criteria, seeds=5, frac=0.90, seed_sd=0.0):
    """P(every criterion passes on every seed); criteria is a list of (n, p). Independence across
    criteria is assumed, which is conservative when criteria are positively correlated."""
    per_seed = 1.0
    for n, p in criteria:
        per_seed *= p_criterion(n, p, frac, seed_sd)
    return per_seed ** seeds


def beta_items(rng, mean, icc, size):
    """Per-item pass probabilities with the given mean and intraclass correlation (beta model)."""
    if icc <= 0:
        return np.full(size, mean)
    s = 1.0 / icc - 1.0
    return rng.beta(mean * s, (1 - mean) * s, size)


def p_paired_late_window(mean, icc, items=50, late=10, need=8, max_drop=2, frac=0.90, min_eligible=25, seeds=5,
                         loads=2, sims=20000, rng_seed=1, late_factor=1.0):
    """Pass probability of the paired late-window rule over all seeds and loads.

    Per item: repetition 1 must pass (scored); the control copy's late window (`late` cues) must reach
    `need` passes (eligible); the item habituated if the repeated copy's late window has more than
    `max_drop` fewer passes than the control's. The rule passes a seed and load when at least
    `min_eligible` items are eligible and >= frac of them did not habituate. With late_factor = 1 (no
    habituation) both windows draw from the same per-item probability; late_factor < 1 scales the
    repeated copy's late-window probability (habituation).
    """
    rng = np.random.default_rng(rng_seed)
    ok = np.ones(sims, bool)
    for _ in range(seeds * loads):
        p = beta_items(rng, mean, icc, (sims, items))
        scored = rng.random((sims, items)) < p
        l_ctl = rng.binomial(late, p)
        l_rep = rng.binomial(late, p * late_factor)
        elig = scored & (l_ctl >= need)
        n_el = elig.sum(1)
        n_ok = (elig & (l_rep >= l_ctl - max_drop)).sum(1)
        ok &= (n_el >= min_eligible) & (n_ok >= np.ceil(frac * n_el - 1e-9))
    return float(ok.mean())


def p_paired_majority(mean, icc, items=50, cues=3, need=2, frac=0.90, min_eligible=25, seeds=5, loads=2,
                      sims=20000, rng_seed=2):
    """Zero-effect pass probability of a paired majority rule (recovery or collateral cues).

    Per item: eligible when the control copy's `cues` cues reach `need` passes; passes when the
    repeated copy's do too. With no effect both draw from the same per-item probability.
    """
    rng = np.random.default_rng(rng_seed)
    ok = np.ones(sims, bool)
    for _ in range(seeds * loads):
        p = beta_items(rng, mean, icc, (sims, items))
        elig = rng.binomial(cues, p) >= need
        rep = rng.binomial(cues, p) >= need
        n_el = elig.sum(1)
        n_ok = (elig & rep).sum(1)
        ok &= (n_el >= min_eligible) & (n_ok >= np.ceil(frac * n_el - 1e-9))
    return float(ok.mean())


# P2-E4's zero-online-cost reference (contract docs/plant2/P2-E4-online-memory.md, "Power").
P2E4_SEED_SD = 0.18
P2E4_RATES = {  # recorded settled rates of P2-E2 and P2-E3's gated seeds, per cue
    500: dict(C1=0.970, C2=0.999, C3=0.999, joint=0.994, D3=0.999, old_recall=0.972, D4=0.998),
    1000: dict(C1=0.944, C2=0.989, C3=0.994, joint=0.975, D3=0.998, old_recall=0.954, D4=0.972),
}
P2E4_COUNTS = dict(half=180, novel=30, cohort=80, hab_items=50, min_eligible=25)


def p2e4_reference():
    """P(each criterion and the whole O1-O3 rule pass on all five seeds) at settled rates, and the
    zero-habituation O4/O5 pass probabilities over a range of per-cue rates."""
    n = P2E4_COUNTS
    out = dict(seed_sd=P2E4_SEED_SD, rates=P2E4_RATES, counts=n, loads={}, habituation={})
    total = 1.0
    for M, r in P2E4_RATES.items():
        crit = dict(O1=[(n["half"], r["C1"]), (n["half"], r["C2"]), (n["novel"], r["C3"])],
                    O2=[(n["half"], r["joint"]), (n["novel"], r["D3"])],
                    O3=[(n["cohort"], r["old_recall"]), (n["cohort"], r["D4"])])
        d = {k: p_rule(v, seeds=5, seed_sd=P2E4_SEED_SD) for k, v in crit.items()}
        out["loads"][str(M)] = d
        for v in d.values():
            total *= v
    out["p_O1_O3_all"] = total
    for mean in (0.97, 0.95, 0.93, 0.90, 0.85):
        o4 = p_paired_late_window(mean, 0.09, items=n["hab_items"], min_eligible=n["min_eligible"])
        rec = p_paired_majority(mean, 0.09, items=n["hab_items"], min_eligible=n["min_eligible"], rng_seed=2)
        col = p_paired_majority(mean, 0.09, items=n["hab_items"], min_eligible=n["min_eligible"], rng_seed=5)
        hab = p_paired_late_window(mean, 0.09, items=n["hab_items"], min_eligible=n["min_eligible"], late_factor=0.85)
        out["habituation"][str(mean)] = dict(O4=o4, O4_if_late_rate_x085=hab, O5_recovery=rec, O5_collateral=col,
                                             O5_both=rec * col)
    return out


if __name__ == "__main__":
    import sys

    from plant2 import record
    rec = dict(experiment="P2-E4", kind="power_reference", **p2e4_reference(), timestamp=record.now(),
               git=record.git_state(), runtime=record.runtime())
    if "--append" in sys.argv:
        record.append(rec)
    print({k: rec[k] for k in ("loads", "p_O1_O3_all", "habituation")})
