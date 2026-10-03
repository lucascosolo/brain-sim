"""Pure rule functions for the SPEC 8.22 Part B offline screen: Graupner-Brunel 2012 calcium rule (no noise),
a running-mean rate filter and the R3 helpers. No engine access."""
import math

import numpy as np

# Graupner and Brunel 2012, hippocampal slice set (SPEC 8.22).
GB = dict(tau_c_ms=48.8373, delay_ticks=19, c_pre=1.0, c_post=0.275865, theta_d=1.0, theta_p=1.3,
          gamma_d=313.0965, gamma_p=1645.59, tau_s=688.355, rho_star=0.5)


def gb_ca_decay(dt_ms=1.0):
    return math.exp(-dt_ms / GB["tau_c_ms"])


def gb_calcium(pre_tr, post_tr):
    return GB["c_pre"] * np.asarray(pre_tr, np.float64) + GB["c_post"] * np.asarray(post_tr, np.float64)


def gb_step(rho, c, g=1.0, dt_ms=1.0):
    """One Euler step of d rho/dt, deterministic; g scales the rate of change; result clipped to [0, 1]."""
    rho = np.asarray(rho, np.float64)
    c = np.asarray(c, np.float64)
    d = -rho * (1.0 - rho) * (GB["rho_star"] - rho)
    d = d + GB["gamma_p"] * (1.0 - rho) * (c > GB["theta_p"]) - GB["gamma_d"] * rho * (c > GB["theta_d"])
    return np.clip(rho + g * dt_ms / (GB["tau_s"] * 1000.0) * d, 0.0, 1.0)


def rate_step(rate, spiked, tau_ticks=10000):
    """Running mean rate in spikes per tick: exponential decay then spikes / tau."""
    return np.asarray(rate, np.float64) * math.exp(-1.0 / tau_ticks) + np.asarray(spiked, np.float64) / tau_ticks


def r3_cj(ltp, ltd):
    """Constant making ltp + c * ltd zero (ltd negative); 1 where there is no potentiation or no depression."""
    ltp, ltd = np.asarray(ltp, np.float64), np.asarray(ltd, np.float64)
    ok = (ltp > 0) & (ltd < 0)
    return np.where(ok, -ltp / np.where(ok, ltd, -1.0), 1.0)


def r3_multiplier(cj, rate, base):
    """Depression multiplier c_j * (rate / base)^2; where base <= 0 the ratio is taken as 1."""
    cj, rate, base = (np.asarray(x, np.float64) for x in (cj, rate, base))
    good = base > 0
    return cj * np.where(good, rate / np.where(good, base, 1.0), 1.0) ** 2
