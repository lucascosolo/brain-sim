import numpy as np

# Pfister and Gerstner 2006, Table 4, hippocampal culture set, minimal all-to-all triplet rule (SPEC 8.21).
A2_PLUS, A3_PLUS, A2_MINUS = 5.3e-3, 8e-3, 3.5e-3
TAU_PLUS_MS, TAU_MINUS_MS, TAU_Y_MS = 16.8, 33.7, 40.0
K_DEFAULT = {"hpc": 16.5, "ctx": 3.3}


def k_of(p):
    return dict(getattr(p, "TRIPLET_K", K_DEFAULT))


def on_pre(w, o1, w_max, k, g=1.0):
    return np.clip(w - g * k * A2_MINUS * o1 * w_max, 0.0, w_max)


def on_post(w, r1, o2, w_max, k, g=1.0):
    return np.clip(w + g * k * r1 * (A2_PLUS + A3_PLUS * o2) * w_max, 0.0, w_max)
