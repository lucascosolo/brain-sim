"""Test-side helpers for the SPEC 8.21 kill test (ported from the 8.18 / 8.19 diagnostic drivers; engine untouched)."""
import copy
import types

import numpy as np

import k03_pairing as k03
import k11_binding as k11
from k816_hetero_write import PATTERN_A, PATTERN_B, READOUT_TICKS, abort
from brainsim import encode

# ---- largest fraction of ctx E / hpc E spiking in one tick, over registered arm engines (not probe copies) ----
TRACK = {"ids": set(), "ctx": 0.0, "hpc": 0.0, "ctx_mask": None, "hpc_mask": None}
_drain = k03._drain_telemetry


def _tracked_drain(eng):
    if id(eng) in TRACK["ids"]:
        for s in eng._buf_spikes:
            for key in ("ctx", "hpc"):
                m = TRACK[key + "_mask"]
                TRACK[key] = max(TRACK[key], np.count_nonzero(m[s]) / np.count_nonzero(m))
    _drain(eng)


def install_tracking(groups, n):
    for key in ("ctx", "hpc"):
        TRACK[key + "_mask"] = np.zeros(n, bool)
        TRACK[key + "_mask"][groups[key]] = True
    k03._drain_telemetry = _tracked_drain


def register(eng):
    TRACK["ids"].add(id(eng))


def unregister(eng):
    TRACK["ids"].discard(id(eng))


def own_params(eng, over):
    """Give eng its own parameter object carrying the overrides; assert they take effect and survive deepcopy."""
    old = eng.p
    eng.p = types.SimpleNamespace(**{k: v for k, v in vars(old).items() if k.isupper()})
    for k, v in over.items():
        setattr(eng.p, k, v)
    assert eng.p is not old
    for k, v in over.items():
        assert getattr(eng.p, k) == v and getattr(old, k) != v, k
        assert getattr(copy.deepcopy(eng).p, k) == v, (k, "deepcopy lost the override")


def check_phase(eng):
    """Wake for the first 60,000 of every 80,000 ticks, sleep for the last 20,000 (params.WAKE_TICKS / SLEEP_TICKS)."""
    m = int(eng.t) % (eng.p.WAKE_TICKS + eng.p.SLEEP_TICKS)
    if 1000 <= m <= eng.p.WAKE_TICKS - 1000 and eng.phase != "wake":
        abort(eng, "wake")
    if eng.p.WAKE_TICKS + 1000 <= m <= eng.p.WAKE_TICKS + eng.p.SLEEP_TICKS - 1000 and eng.phase != "sleep":
        abort(eng, "sleep")


def a_epoch_log(e, a_log):
    h = e.hetero_last
    if h is not None and h["t"] == e.t:
        a_log["cells"] |= set(h["cells"].tolist())
        for pre, post, born, dw, wm in zip(h["pre"].tolist(), h["post"].tolist(), h["born"].tolist(),
                                           h["dw"].tolist(), h["w_max"].tolist()):
            a_log["writes"][(pre, post, born)] = a_log["writes"].get((pre, post, born), 0.0) + dw / wm


def delivered_exc(eng, W, ticks):
    """Steps eng `ticks` ticks; summed excitatory weight delivered onto W, read from each tick's ring bucket."""
    net, p = eng.net, eng.p
    onto = np.zeros(net.n, bool)
    onto[np.asarray(W, np.int64)] = True
    total = 0.0
    for _ in range(ticks):
        bucket = eng.ring[eng.t % (p.D_MAX + 1)]
        if bucket:
            d = np.concatenate(bucket)
            d = d[net.alive[d] & onto[net.post[d]] & net.is_exc[net.pre[d]]]
            total += float(net.w[d].astype(np.float64).sum())
        eng.step(1)
    return total


def probe_full_A(eng, W):
    """50-tick full-A probe, hetero write off, on a deep copy: per-cell counts and delivered weight onto W."""
    e = copy.deepcopy(eng)
    e.hetero_write = False
    e.present(PATTERN_A, READOUT_TICKS)
    before = e.spike_counts().astype(np.int64)
    deliv = delivered_exc(e, W, READOUT_TICKS)
    return e.spike_counts().astype(np.int64) - before, deliv


def probe_counts(eng, kind, A_ids):
    """50-tick half-cue or B probe on a deep copy; per-cell counts."""
    e = copy.deepcopy(eng)
    e.hetero_write = False
    if kind == "half":
        e.inject(encode.cue_ids(A_ids), e.p.PATTERN_AMP_MV, READOUT_TICKS)
    else:
        e.present(PATTERN_B, READOUT_TICKS)
    return k11._step_chunked_counting(e, READOUT_TICKS)


def on_W(c, W):
    return {"spikes": int(c[W].sum()), "cells": int((c[W] > 0).sum())}


def syn_key(net, idx):
    """Identity (pre, post, born) of synapses as one int64."""
    return (net.pre[idx].astype(np.int64) * net.n + net.post[idx]) * (1 << 22) + net.born[idx].astype(np.int64)


def exc_onto(net, ids):
    """Alive excitatory synapses whose postsynaptic cell is in ids."""
    onto = np.zeros(net.n, bool)
    onto[ids] = True
    return np.flatnonzero(net.alive & net.is_exc[net.pre] & onto[net.post])


def identities(net, groups):
    return {k: np.sort(syn_key(net, exc_onto(net, groups[k]))) for k in ("ctx", "hpc")}


def sat_and_died(net, groups, ident0):
    """Saturated fraction (w >= 0.98 w_max_n[post]) among alive exc synapses onto ctx E / hpc E, and the fraction
    of those alive at the reference tick that have died since."""
    sat, died = {}, {}
    alive_keys = syn_key(net, np.flatnonzero(net.alive))
    for k in ("ctx", "hpc"):
        idx = exc_onto(net, groups[k])
        sat[k + "_E"] = float(np.mean(net.w[idx] >= 0.98 * net.w_max_n[net.post[idx]])) if idx.size else 0.0
        died[k + "_E"] = float(1.0 - np.isin(ident0[k], alive_keys).mean())
    return sat, died


def projections(net):
    """Alive excitatory synapses by (pre region > post region): count, mean w / w_max, saturated fraction."""
    idx = np.flatnonzero(net.alive & net.is_exc[net.pre])
    names = net.region_names
    reg_pre, reg_post = net.region[net.pre[idx]], net.region[net.post[idx]]
    frac = net.w[idx].astype(np.float64) / net.w_max_n[net.post[idx]]
    out = {}
    for a, na in enumerate(names):
        for b, nb in enumerate(names):
            m = (reg_pre == a) & (reg_post == b)
            if m.any():
                out[f"{na}>{nb}"] = {"n": int(m.sum()), "mean_w": float(frac[m].mean()), "sat": float((frac[m] >= 0.98).mean())}
    return out


def hz_pair(counts, groups, ticks):
    f = lambda ids: float(np.asarray(counts)[ids].sum()) * 1000.0 / (len(ids) * ticks)
    return {"hpc_E": f(groups["hpc"]), "ctx_E": f(groups["ctx"])}
