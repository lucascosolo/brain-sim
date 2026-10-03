import numpy as np

ETA_DEFAULT = 0.004


def eta(p):
    return getattr(p, "INH_ETA", ETA_DEFAULT)


def alpha(r_target_hz, tau_ms):
    return 2.0 * r_target_hz * tau_ms / 1000.0


def on_pre(w, y_post, alpha, m_max, eta, g=1.0):
    """Inhibitory spike delivered: the magnitude m = -w moves with (y_post - alpha)."""
    return -np.clip(-w + g * eta * m_max * (y_post - alpha), 0.0, m_max)


def on_post(w, x_pre, m_max, eta, g=1.0):
    """Postsynaptic spike: the magnitude m = -w grows with the presynaptic trace."""
    return -np.clip(-w + g * eta * m_max * x_pre, 0.0, m_max)
