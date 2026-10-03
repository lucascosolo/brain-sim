"""Encode-mode helpers (SPEC.md section 8.12).

Pure functions moved verbatim (same numerics) out of `tests/k11_binding.py`:
the hpc/ctx excitatory id sets, the half cue, the winner selection, the
identification pass on a deep copy, and the two one-shot co-fire writes. The
schedule that calls them lives in `Engine`; nothing here touches `Engine`
state apart from `identify_W`'s discarded copy. This is a labelled proxy, not
biology.
"""
import copy
import types

import numpy as np

from . import params


def hpc_e_ids(net):
    """The hpc excitatory cell ids, checked against the engine's built is_exc mask
    (not only against params) so the proxy cannot land on the wrong cells."""
    hpc = net.region_slice["hpc"]
    ids = np.arange(hpc.start, hpc.start + params.REGIONS["hpc"]["n_exc"], dtype=np.int64)
    assert net.is_exc[ids].all() and not net.is_exc[ids[-1] + 1:hpc.stop].any()
    return ids


def ctx_e_ids(net):
    """The ctx excitatory cell ids (the donor pool of the sparse write)."""
    ctx = net.region_slice["ctx"]
    return np.arange(ctx.start, ctx.start + params.REGIONS["ctx"]["n_exc"], dtype=np.int64)


def cue_ids(pattern_ids):
    """The cells at even positions of the sorted pattern (a fixed half)."""
    return np.sort(np.asarray(pattern_ids, np.int64))[0::2]


def select_winners(counts, ids, k):
    """The min(k, n) ids among `ids` with the highest counts[id], ties broken by
    the lower id. Pure; returns a sorted int64 array."""
    ids = np.asarray(ids, np.int64)
    counts = np.asarray(counts).astype(np.int64)  # unsigned counts would wrap under negation
    n = min(int(k), ids.size)
    order = np.lexsort((ids, -counts[ids]))[:n]
    return np.sort(ids[order]).astype(np.int64)


def identify_W(eng, pattern_id, ticks, k):
    """Deep-copy eng, present pattern_id on the copy for ticks under the default
    plant (mode off, no window, no bump), and return (W, record) with W the
    sorted int64 top-k hpc E ids by the copy's spike counts. The copy is
    discarded; eng is unchanged (t, net arrays, rng state, encode_mask, _inj)."""
    # A caller's instance-level inject wrapper closes over the caller's engine and
    # log; it is lifted off before the deep copy and put back after, so the copy
    # runs the plain method and the caller's wrapper is untouched.
    assert eng._encode is None, "identify_W needs an idle plant: a schedule is already active"
    saved_inject = eng.__dict__.pop("inject", None)
    try:
        # A params module cannot be deep-copied and is read-only, so the copy shares
        # it; any other params object (a mutable namespace) is copied as usual.
        memo = {id(eng.p): eng.p} if isinstance(eng.p, types.ModuleType) else None
        eng_copy = copy.deepcopy(eng, memo)
        eng_copy.encode_mode = False
        eng_copy.slow_weights = False   # the default plant (SPEC 8.13): no latch on the copy
        net = eng_copy.net
        t0 = eng_copy.t
        before = net.spike_count.astype(np.int64)
        eng_copy.present(pattern_id, ticks)
        eng_copy.step(ticks)
        counts = net.spike_count.astype(np.int64) - before
        t1 = eng_copy.t
        ids = hpc_e_ids(net)
    finally:
        if saved_inject is not None:
            eng.inject = saved_inject
    W = select_winners(counts, ids, k)
    record = {
        "W": [int(x) for x in W],
        "k": int(k),
        "ticks": int(ticks),
        "copy_t_start": int(t0),
        "copy_t_end": int(t1),
        "mean_count_W": float(counts[W].mean()),
        "mean_count_hpc_e_not_W": float(counts[np.setdiff1d(ids, W)].mean()),
    }
    del eng_copy
    return W, record


def sparse_cofire_write(net, counts, hpc_e_ids, ctx_e_ids, k=params.ENCODE_K,
                        delta_frac=params.ENCODE_DELTA_FRAC, W=None):
    """Once: W = top-k hpc_e_ids by counts (or the given W); donors = ctx_e_ids
    with counts > 0; on the existing alive synapses donor -> W only,
    w += delta_frac * w_max_n[post], clamped at w_max_n[post]. No new synapses,
    nothing else touched."""
    real_top_k = select_winners(counts, hpc_e_ids, k)
    if W is None:
        W = real_top_k
        W_source = "counts"
    else:
        W = np.sort(np.asarray(W, np.int64))
        assert W.size == k
        assert np.unique(W).size == k
        assert np.isin(W, hpc_e_ids).all()
        W_source = "given"
    counts = np.asarray(counts)
    ctx_e_ids = np.asarray(ctx_e_ids, np.int64)
    donors = ctx_e_ids[counts[ctx_e_ids] > 0]
    donor_mask = np.zeros(net.n, bool)
    donor_mask[donors] = True
    w_mask = np.zeros(net.n, bool)
    w_mask[W] = True
    idx = np.flatnonzero(net.alive & donor_mask[net.pre] & w_mask[net.post])

    wmax_post = net.w_max_n[net.post[idx]].astype(np.float64)
    before_ratio = net.w[idx].astype(np.float64) / wmax_post
    mean_before = float(before_ratio.mean()) if idx.size else float("nan")

    net.w[idx] = np.minimum(net.w[idx] + delta_frac * wmax_post, wmax_post)

    after_ratio = net.w[idx].astype(np.float64) / wmax_post
    mean_after = float(after_ratio.mean()) if idx.size else float("nan")
    n_clamped = int(np.count_nonzero(net.w[idx] >= wmax_post))

    return {
        "W": [int(x) for x in W],
        "W_size": int(W.size),
        "W_source": W_source,
        "real_top_k": [int(x) for x in real_top_k],
        "overlap_W_with_real_top_k": int(np.intersect1d(W, real_top_k).size),
        "donors": int(donors.size),
        "donor_ids": [int(x) for x in np.sort(donors)],
        "n_synapses_bumped": int(idx.size),
        "n_clamped": n_clamped,
        "mean_w_over_wmax_onto_W_before": mean_before,
        "mean_w_over_wmax_onto_W_after": mean_after,
    }


def recurrent_cofire_write(net, W, delta_frac=params.ENCODE_RECURRENT_DELTA_FRAC):
    """Once: on the existing alive hpc E -> hpc E synapses with both ends in W,
    w += delta_frac * w_max_n[post], clamped at w_max_n[post]. No new synapses,
    nothing W -> non-W or non-W -> W touched."""
    W = np.asarray(W, np.int64)
    W_mask = np.zeros(net.n, bool)
    W_mask[W] = True
    idx = np.flatnonzero(net.alive & W_mask[net.pre] & W_mask[net.post])

    wmax_post = net.w_max_n[net.post[idx]].astype(np.float64)
    before_ratio = net.w[idx].astype(np.float64) / wmax_post
    mean_before = float(before_ratio.mean()) if idx.size else float("nan")
    n_at_wmax_before = int(np.count_nonzero(before_ratio >= 1.0))

    net.w[idx] = np.minimum(net.w[idx] + delta_frac * wmax_post, wmax_post)

    after_ratio = net.w[idx].astype(np.float64) / wmax_post
    mean_after = float(after_ratio.mean()) if idx.size else float("nan")
    n_clamped = int(np.count_nonzero(net.w[idx] >= wmax_post))
    n_increased = int(np.count_nonzero(after_ratio > before_ratio))

    return {
        "n_existing": int(idx.size),
        "n_increased": n_increased,
        "n_synapses_bumped": int(idx.size),
        "n_clamped": n_clamped,
        "n_at_wmax_before": n_at_wmax_before,
        "mean_w_over_wmax_within_W_before": mean_before,
        "mean_w_over_wmax_within_W_after": mean_after,
        "delta_frac": float(delta_frac),
    }
