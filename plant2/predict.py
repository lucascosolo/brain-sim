"""Single-cell predictions for contracts: P(first spike within a window) under Poisson input.

A contract's quantitative predictions are made with this before any run of its experiment.
It simulates many independent copies of one plant2 LIF cell (same membrane update as
plant2.engine.LIF) receiving `n_cue` strong synapses whose inputs switch from `r_bg` to `r_cue`
at onset and `n_bg` strong synapses that stay at `r_bg`. The cell is first run for
`settle_ms` of background so it starts from its background steady state.

`accommodation`, when not None, is the time constant (ms) of a threshold that tracks the
cell's own mean membrane potential (theta = v_th + vbar - v_rest), integrated the same way
plant2 does.
"""
import numpy as np


def p_first_spike(n_cue, n_bg, J, window=50, r_cue=40.0, r_bg=0.5, trials=20_000, settle_ms=3000,
                  accommodation=None, tau_m=20.0, v_rest=-70.0, v_reset=-65.0, v_th=-50.0, t_ref=2,
                  seed=0):
    rng = np.random.default_rng(seed)
    n_cue = np.broadcast_to(np.asarray(n_cue, np.int64), (trials,))
    n_bg = np.broadcast_to(np.asarray(n_bg, np.int64), (trials,))
    decay = np.exp(-1.0 / tau_m)
    v = np.full(trials, v_rest)
    vbar = np.full(trials, v_rest)
    a = 0.0 if accommodation is None else 1.0 / accommodation
    t_last = np.full(trials, -10_000)
    first = np.full(trials, -1)
    for t in range(settle_ms + window):
        on = t - 1 >= settle_ms  # sources switch at onset; their spikes arrive one tick later
        lam = (n_cue * (r_cue if on else r_bg) + n_bg * r_bg) / 1000.0
        v = v_rest + (v - v_rest) * decay + J * rng.poisson(lam)
        if a:
            vbar += (v - vbar) * a
        th = v_th + (vbar - v_rest) if a else v_th
        s = (v >= th) & (t - t_last > t_ref)
        v[s] = v_reset
        t_last[s] = t
        if on:
            new = s & (first < 0)
            first[new] = t - settle_ms
    return float((first >= 0).mean())
