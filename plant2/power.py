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
# recorded settled rates per cue: memory measures pooled over P2-E2 seeds 6-10 and P2-E3 seeds 11-15,
# content measures from P2-E3 seeds 11-15; recorded 1.000 enters as 0.999
P2E4_RATES = {
    500: dict(C1=0.969, C2=0.999, C3=0.999, joint=0.994, D3=0.999, old_recall=0.969, D4=0.998),
    1000: dict(C1=0.9435, C2=0.986, C3=0.9955, joint=0.975, D3=0.998, old_recall=0.953, D4=0.972),
}
P2E4_RATES_E3_ONLY = {
    500: dict(P2E4_RATES[500], C1=0.972, old_recall=0.972),
    1000: dict(P2E4_RATES[1000], C1=0.938, C2=0.989, C3=0.994, old_recall=0.954),
}
P2E4_COUNTS = dict(half=200, novel=20, cohort=100, hab_items=50, min_eligible=25, recovery_cues=5, recovery_need=3)
P2E4_ICC = 0.09


def p2e4_o1_o3(rates, n=P2E4_COUNTS, seed_sd=P2E4_SEED_SD):
    loads, total = {}, 1.0
    for M, r in rates.items():
        crit = dict(O1=[(n["half"], r["C1"]), (n["half"], r["C2"]), (n["novel"], r["C3"])],
                    O2=[(n["half"], r["joint"]), (n["novel"], r["D3"])],
                    O3=[(n["cohort"], r["old_recall"]), (n["cohort"], r["D4"])])
        loads[str(M)] = {k: p_rule(v, seeds=5, seed_sd=seed_sd) for k, v in crit.items()}
        for v in loads[str(M)].values():
            total *= v
    return loads, total


def p2e4_o4_o5(both, n=P2E4_COUNTS, late_factor=1.0):
    """O4 and O5 over five seeds, per load (both: {M: per-cue 'both' rate}), multiplied over loads."""
    out = dict(O4=1.0, O5_recovery=1.0, O5_collateral=1.0)
    for i, (M, b) in enumerate(sorted(both.items())):
        out["O4"] *= p_paired_late_window(b, P2E4_ICC, items=n["hab_items"], min_eligible=n["min_eligible"], loads=1,
                                          late_factor=late_factor, rng_seed=11 + i)
        kw = dict(items=n["hab_items"], cues=n["recovery_cues"], need=n["recovery_need"], min_eligible=n["min_eligible"],
                  loads=1)
        out["O5_recovery"] *= p_paired_majority(b, P2E4_ICC, rng_seed=21 + i, **kw)
        out["O5_collateral"] *= p_paired_majority(b, P2E4_ICC, rng_seed=31 + i, **kw)
    return out


def p2e4_reference():
    """Zero-online-cost pass probabilities of P2-E4's full acceptance rule (all criteria, both loads, five seeds)."""
    loads, o13 = p2e4_o1_o3(P2E4_RATES)
    _, o13_e3 = p2e4_o1_o3(P2E4_RATES_E3_ONLY)
    _, o13_draft = p2e4_o1_o3(P2E4_RATES, dict(P2E4_COUNTS, half=120, novel=60, cohort=40))
    full = {}
    for name, both in (("product", {500: 0.963, 1000: 0.920}), ("settled_C1", {500: 0.968, 1000: 0.944})):
        h = p2e4_o4_o5(both)
        hab = p2e4_o4_o5(both, late_factor=0.85)["O4"]
        full[name] = dict(both=both, **h, O4_if_late_rate_x085=hab,
                          p_pass_pooled=o13 * h["O4"] * h["O5_recovery"] * h["O5_collateral"],
                          p_pass_e3_only=o13_e3 * h["O4"] * h["O5_recovery"] * h["O5_collateral"])
    rng = np.random.default_rng(3)
    draft = {}
    for nl in (1, 2):  # the draft's unpaired O4 rule: >= 8 of 10 late passes for >= 90 % of scored items
        ok = np.ones(20000, bool)
        for _ in range(5 * nl):
            p = beta_items(rng, 0.93, P2E4_ICC, (20000, 50))
            sc = rng.random(p.shape) < p
            late = rng.binomial(10, p) >= 8
            ok &= (sc & late).sum(1) >= np.ceil(0.9 * sc.sum(1) - 1e-9)
        draft[f"loads_{nl}"] = float(ok.mean())
    return dict(seed_sd=P2E4_SEED_SD, icc=P2E4_ICC, rates=P2E4_RATES, rates_e3_only=P2E4_RATES_E3_ONLY, counts=P2E4_COUNTS,
                loads=loads, p_O1_O3_pooled=o13, p_O1_O3_e3_only=o13_e3, p_O1_O3_draft_counts=o13_draft, full_rule=full,
                draft_unpaired_O4_at_093=draft)


if __name__ == "__main__":
    import sys

    from plant2 import record
    import hashlib
    contract = record.REPO / "docs" / "plant2" / "P2-E4-online-memory.md"
    rec = dict(experiment="P2-E4", kind="power_reference", **p2e4_reference(),
               contract_sha256=hashlib.sha256(contract.read_bytes()).hexdigest(), timestamp=record.now(),
               git=record.git_state(), runtime=record.runtime())
    if "--append" in sys.argv:
        record.append(rec)
    print({k: rec[k] for k in ("loads", "p_O1_O3_pooled", "p_O1_O3_e3_only",
                                                             "p_O1_O3_draft_counts", "full_rule", "draft_unpaired_O4_at_093")})
