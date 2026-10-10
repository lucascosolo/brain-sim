"""Replay of reconstruction-layer readout arms from a recorded memory spike raster (P2-E3).

Many arms (strength J, inhibition ratio g) share one feedback matrix and one memory raster, so
every arm sees identical memory activity. The arithmetic mirrors plant2.engine exactly. Each
`rec` cell is the engine's LIF. Feedback is a Projection with delay 1, adding J once per event.
Inhibition is a GlobalInhibition of -g*J per memory spike with delay 2. So an arm's spikes equal
those of the engine network built with that J and g, bit for bit (tests/test_p2_e3.py).

`cues` lists the scoring windows. Each window (onset, lines-of-interest...) is scored per arm
over ticks onset .. onset + window - 1, and also over the whole cue plus gap (`span` ticks).
"""
import numpy as np

f32 = np.float32


def replay(raster, n_ticks, indptr, post, m, J, g, cues, window=75, short=50, span=300,
           tau_m=20.0, v_rest=-70.0, v_reset=-65.0, v_th=-50.0, t_ref=2, trace=None):
    """raster: dict tick -> memory cell ids spiking at that tick (ticks 0..n_ticks-1).

    indptr/post: CSR of the feedback store by memory cell. J, g: arrays over arms.
    cues: list of dicts with 'onset' and 'item', 'cue', 'missing', 'other_missing' (index arrays; any may be empty).
    trace: optional list; (tick, arm, line) is appended for every rec spike (tests only).
    Returns per-cue per-arm counts plus out-of-window spike totals.
    """
    # inhibition weight as the engine forms it: float32 of the float64 product g * J
    gJ = (np.asarray(g, np.float64) * np.asarray(J, np.float64)).astype(np.float32)
    J = np.asarray(J, np.float32)
    A = J.size
    decay = f32(np.exp(-1.0 / tau_m))
    v_c = f32(v_rest * (1.0 - decay))
    v = np.full((A, m), v_rest, np.float32)
    t_last = np.full((A, m), -10_000, np.int64)
    ring = np.zeros((3, A, m), np.float32)
    win = np.zeros((A, m), bool)
    win_short = None
    win_span = np.zeros((A, m), bool)
    first = np.full((A, m), -1, np.int16)
    starts = {c["onset"]: i for i, c in enumerate(cues)}
    out = {k: np.zeros((len(cues), A), np.int32) for k in
           ("missing", "visible", "item", "total", "missing_short", "item_short", "total_short",
            "total_span", "item_span", "other_missing")}
    latency = np.full((len(cues), A), np.nan)
    out_of_window = np.zeros(A, np.int64)
    active, span_cue = None, None
    dirty = [False, False, False]  # whether each ring slot holds anything; adding a zero slot is a no-op
    since_input = 10_000           # ticks since input last reached v; a cell below threshold with no input stays below
    for t in range(n_ticks):
        if t in starts:
            active = span_cue = starts[t]
            win[:] = False
            win_span[:] = False
            first[:] = -1
        slot = ring[t % 3]
        np.multiply(v, decay, out=v)
        v += v_c
        if dirty[t % 3]:
            v += slot
            slot[:] = 0.0
            dirty[t % 3] = False
            since_input = 0
        else:
            since_input += 1
        hit = None
        if since_input <= t_ref + 1:  # otherwise no cell can be at threshold (exact: identical arithmetic)
            hit = (v >= v_th) & (t - t_last > t_ref)
            if hit.any():
                v[hit] = v_reset
                t_last[hit] = t
                if trace is not None:
                    trace.extend((t, int(a), int(j)) for a, j in zip(*np.nonzero(hit)))
            else:
                hit = None
        if active is not None:
            k = t - cues[active]["onset"]
            if hit is not None:
                win |= hit
                newly = hit & (first < 0)
                first[newly] = k
            if k == short - 1:
                c = cues[active]
                win_short = win.copy()
                out["missing_short"][active] = win_short[:, c["missing"]].sum(1)
                out["item_short"][active] = win_short[:, c["item"]].sum(1)
                out["total_short"][active] = win_short.sum(1)
            if k == window - 1:
                c = cues[active]
                out["missing"][active] = win[:, c["missing"]].sum(1)
                out["visible"][active] = win[:, c["cue"]].sum(1)
                out["item"][active] = win[:, c["item"]].sum(1)
                out["total"][active] = win.sum(1)
                out["other_missing"][active] = win[:, c["other_missing"]].sum(1)
                if c["missing"].size:
                    fm = first[:, c["missing"]].astype(float)
                    fm[~win[:, c["missing"]]] = np.nan
                    with np.errstate(all="ignore"):
                        latency[active] = np.nanmedian(fm, axis=1) if np.isfinite(fm).any() else np.nan
                active = None
        elif hit is not None:
            out_of_window += hit.sum(1)
        if span_cue is not None:
            if hit is not None:
                win_span |= hit
            if t - cues[span_cue]["onset"] == span - 1:
                c = cues[span_cue]
                out["total_span"][span_cue] = win_span.sum(1)
                out["item_span"][span_cue] = win_span[:, c["item"]].sum(1)
                span_cue = None
        s = raster.get(t)
        if s is not None and s.size:
            lo, cnt = indptr[s], indptr[s + 1] - indptr[s]
            n_ev = int(cnt.sum())
            if n_ev:
                idx = np.repeat(lo, cnt) + (np.arange(n_ev) - np.repeat(np.cumsum(cnt) - cnt, cnt))
                counts = np.bincount(post[idx], minlength=m)
                nxt = ring[(t + 1) % 3]
                for kk in range(1, int(counts.max()) + 1):  # J added once per event, as np.add.at does
                    nxt += J[:, None] * (counts >= kk)[None, :]
                dirty[(t + 1) % 3] = True
            ring[(t + 2) % 3] -= (gJ * s.size)[:, None]
            dirty[(t + 2) % 3] = True
    return out, latency, out_of_window
