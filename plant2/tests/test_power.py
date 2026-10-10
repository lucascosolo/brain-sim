import math

from plant2 import power as pw


def test_binomial_tails_and_bars():
    assert pw.bar_count(180, 0.90) == 162 and pw.bar_count(30, 0.90) == 27 and pw.bar_count(80, 0.90) == 72
    assert math.isclose(pw.binom_tail(60, 54, 0.95), 0.9703, abs_tol=1e-4)
    assert math.isclose(pw.binom_tail(40, 36, 0.946), 0.937, abs_tol=2e-3)
    assert pw.binom_tail(10, 0, 0.3) == 1.0 and pw.binom_tail(10, 11, 0.9) == 0.0


def test_seed_effect_lowers_power_near_the_bar_and_rule_multiplies():
    assert pw.p_criterion(180, 0.944, seed_sd=0.18) < pw.p_criterion(180, 0.944)
    one = pw.p_criterion(80, 0.954)
    assert math.isclose(pw.p_rule([(80, 0.954)], seeds=5), one ** 5)


def test_paired_rules_separate_noise_from_habituation():
    kw = dict(sims=4000, seeds=5, loads=2)
    assert pw.p_paired_late_window(0.95, 0.09, **kw) > 0.95       # no habituation: passes
    assert pw.p_paired_late_window(0.95, 0.09, late_factor=0.85, **kw) < 0.01  # modest habituation: fails
    assert pw.p_paired_majority(0.95, 0.09, **kw) > 0.95
    assert pw.p_paired_majority(0.85, 0.09, **kw) < 0.2
