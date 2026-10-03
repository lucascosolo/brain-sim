"""Contract tests for tests/k822_rules.py (SPEC 8.22 Part B): per-tick maths of the
Graupner-Brunel 2012 calcium rule (no noise), a running-mean rate, and the R3 helpers.
Expected values are hand-computed here from the formulas, never by the code under test."""
import math

import numpy as np
import pytest

from tests.k822_rules import (
    GB, gb_ca_decay, gb_calcium, gb_step, r3_cj, r3_multiplier, rate_step,
)

K = 1.0 / (688.355 * 1000.0)  # dt_ms / (tau_s * 1000) at dt = 1 ms, g = 1


def _expected(rho, c, g=1.0):
    d = -rho * (1 - rho) * (0.5 - rho)
    if c > 1.3:
        d += 1645.59 * (1 - rho)
    if c > 1.0:
        d -= 313.0965 * rho
    return min(1.0, max(0.0, rho + g * K * d))


def _one(rho, c, **kw):
    return float(gb_step(np.array([rho]), np.array([c]), **kw)[0])


def test_constants_are_published_values():
    assert GB == dict(tau_c_ms=48.8373, delay_ticks=19, c_pre=1.0, c_post=0.275865,
                      theta_d=1.0, theta_p=1.3, gamma_d=313.0965, gamma_p=1645.59,
                      tau_s=688.355, rho_star=0.5)


def test_ca_decay_value():
    assert gb_ca_decay() == pytest.approx(math.exp(-1 / 48.8373), rel=1e-12)


def test_calcium_linear_combination():
    pre, post = np.array([0.0, 1.0, 2.0, 0.5]), np.array([0.0, 0.0, 1.0, 4.0])
    exp = 1.0 * pre + 0.275865 * post
    assert np.allclose(gb_calcium(pre, post), exp, rtol=1e-12, atol=0)


def test_single_spikes_cross_no_threshold():
    one = np.array([1.0]); zero = np.array([0.0])
    assert gb_calcium(one, zero)[0] == 1.0          # pre alone: exactly theta_d
    assert gb_calcium(zero, one)[0] == pytest.approx(0.275865)
    for c in (1.0, 0.275865):                        # neither exceeds theta_d: cubic only
        for rho in (0.25, 0.75):
            assert _one(rho, c) == pytest.approx(_expected(rho, 0.0), rel=1e-12)


def test_below_thresholds_only_cubic():
    assert _one(0.25, 0.5) == pytest.approx(0.25 - 0.046875 * K, rel=1e-12)
    assert _one(0.75, 0.5) == pytest.approx(0.75 + 0.046875 * K, rel=1e-12)
    assert _one(0.25, 0.5) < 0.25 < 0.5 < 0.75 < _one(0.75, 0.5)


@pytest.mark.parametrize("rho", [0.0, 0.5, 1.0])
def test_cubic_fixed_points(rho):
    assert _one(rho, 0.0) == pytest.approx(rho, abs=1e-15)


def test_between_thresholds_depression_only():
    out = _one(0.25, 1.2)
    assert out == pytest.approx(0.25 + K * (-0.046875 - 313.0965 * 0.25), rel=1e-12)
    assert out < 0.25


def test_above_theta_p_both_terms():
    out = _one(0.25, 1.5)
    assert out == pytest.approx(
        0.25 + K * (-0.046875 + 1645.59 * 0.75 - 313.0965 * 0.25), rel=1e-12)
    assert out > 0.25  # potentiation wins at gamma_p*(1-rho) > gamma_d*rho


def test_thresholds_are_strict():
    assert _one(0.25, 1.0) == pytest.approx(_expected(0.25, 0.0), rel=1e-12)
    assert _one(0.25, 1.3) == pytest.approx(_expected(0.25, 1.1), rel=1e-12)  # depression only
    assert _one(0.25, 1.3 + 1e-9) == pytest.approx(_expected(0.25, 1.4), rel=1e-9)


def test_g_scales_change_linearly():
    base = _one(0.4, 1.5) - 0.4
    assert _one(0.4, 1.5, g=0.3) - 0.4 == pytest.approx(0.3 * base, rel=1e-9)
    assert _one(0.4, 1.5, g=0.0) == 0.4


def test_dt_scales_change_linearly():
    base = _one(0.4, 1.5) - 0.4
    assert _one(0.4, 1.5, dt_ms=2.0) - 0.4 == pytest.approx(2.0 * base, rel=1e-9)


def test_drift_sign_flips_above_theta_p():
    pos = 0.5 + K * (0.0 + 1645.59 * 0.5 - 313.0965 * 0.5)      # rho=0.5, c=1.5
    neg = 0.9 + K * (0.036 + 1645.59 * 0.1 - 313.0965 * 0.9)    # rho=0.9, c=1.5
    assert _one(0.5, 1.5) == pytest.approx(pos, rel=1e-12) and pos > 0.5
    assert _one(0.9, 1.5) == pytest.approx(neg, rel=1e-12) and neg < 0.9


def test_clipping():
    assert _one(1e-12, 1.2, g=1e9) == 0.0
    assert _one(1.0 - 1e-12, 1.5, g=1e9) <= 1.0
    assert _one(0.5, 1.5, g=1e9) == 1.0   # drift positive at rho=0.5
    assert _one(0.9, 1.5, g=1e9) == 0.0   # drift negative at rho=0.9
    assert _one(0.0, 0.0, g=1e9) == 0.0


def test_input_not_mutated_and_new_array():
    rho = np.array([0.2, 0.6]); c = np.array([1.5, 1.2])
    rho0, c0 = rho.copy(), c.copy()
    out = gb_step(rho, c)
    assert out is not rho
    assert np.array_equal(rho, rho0) and np.array_equal(c, c0)


def test_vectorised():
    rho = np.array([0.1, 0.25, 0.5, 0.75, 0.9]); c = np.array([0.0, 1.2, 1.5, 0.5, 2.0])
    exp = [_expected(r, k) for r, k in zip(rho, c)]
    out = gb_step(rho, c)
    assert out.shape == rho.shape and out.dtype == np.float64
    assert np.allclose(out, exp, rtol=1e-12, atol=0)


def test_rate_step_converges_to_true_rate():
    r = np.zeros(1)
    for t in range(1, 200001):
        r = rate_step(r, np.array([t % 100 == 0]))
    assert r[0] == pytest.approx(0.01, rel=0.05)


def test_rate_step_decay_and_spike():
    assert rate_step(np.array([0.02]), np.array([False]))[0] == pytest.approx(
        0.02 * math.exp(-1 / 10000), rel=1e-12)
    assert rate_step(np.array([0.0]), np.array([True]))[0] == pytest.approx(1 / 10000, rel=1e-12)
    assert rate_step(np.array([0.02]), np.array([1]), tau_ticks=100)[0] == pytest.approx(
        0.02 * math.exp(-0.01) + 0.01, rel=1e-12)


def test_r3_cj_balances():
    ltp = np.array([3.0, 0.5, 10.0]); ltd = np.array([-1.5, -2.0, -0.25])
    cj = r3_cj(ltp, ltd)
    assert np.allclose(cj, [2.0, 0.25, 40.0], rtol=1e-12)
    assert np.allclose(ltp + cj * ltd, 0.0, atol=1e-12)


def test_r3_cj_guards_keep_one():
    ltp = np.array([0.0, 2.0, 0.0, -1.0, 2.0]); ltd = np.array([-1.0, 0.0, 0.0, -1.0, 1.0])
    assert np.array_equal(r3_cj(ltp, ltd), [1.0, 1.0, 1.0, 1.0, 1.0])


def test_r3_multiplier_quadratic():
    cj = np.array([2.0, 0.5, 1.0]); base = np.array([0.01, 0.02, 0.04])
    assert np.allclose(r3_multiplier(cj, base, base), cj, rtol=1e-12)
    assert np.allclose(r3_multiplier(cj, 2 * base, base), 4 * cj, rtol=1e-12)
    assert np.allclose(r3_multiplier(cj, 0.5 * base, base), 0.25 * cj, rtol=1e-12)
    assert np.allclose(r3_multiplier(cj, np.array([0.03, 0.01, 0.0]), base),
                       cj * (np.array([0.03, 0.01, 0.0]) / base) ** 2, rtol=1e-12)


def test_r3_multiplier_base_guard():
    cj = np.array([2.0, 3.0, 4.0]); base = np.array([0.0, -1.0, 0.01])
    out = r3_multiplier(cj, np.array([0.5, 0.5, 0.02]), base)
    assert np.allclose(out, [2.0, 3.0, 16.0], rtol=1e-12)
