import numpy as np

FRAME_KEYS = frozenset({
    "t", "phase", "age_s", "g", "g_struct", "sense_gated", "ticks", "n_syn_alive",
    "syn_born_total", "syn_died_total", "born_per_s", "died_per_s", "spike_total",
    "syn_touched_mean", "born_count", "died_count", "regions", "spikes", "truncated",
    "born", "died", "wall_ratio", "growth_halted", "store_clamped",
    "stim_active", "stim_events", "seq",
})

CONFIG_KEYS = frozenset({
    "dt_ms", "batch_ticks", "pattern_amp_mv", "pattern_ticks", "wake_ticks", "sleep_ticks",
    "g_wake", "g_sleep", "sweep_ticks", "rate_ema_alpha", "frame_spike_cap", "v_trace_ticks",
    "hist_bins", "n_patterns", "pattern_frac", "stimlog_max", "seed",
})

REPLY_KEYS = {
    "frame": FRAME_KEYS | {"type", "run_id"},
    "inspect": frozenset({"type", "id", "region", "is_exc", "v", "theta", "rate_hz",
                          "in_deg", "out_deg", "top_in", "v_trace", "run_id"}),
    "region": frozenset({"type", "name", "n", "rate_hz", "n_syn_in", "n_syn_out",
                         "w_hist", "rate_hist", "run_id"}),
    "layout": frozenset({"type", "regions", "x", "y", "region", "is_exc", "synapse_sample",
                         "patterns", "run_id"}),
    "status": frozenset({"type", "running", "speed", "t", "run_id"}),
    "error": frozenset({"type", "cmd", "msg", "req", "run_id"}),
    "config": CONFIG_KEYS | {"type", "run_id"},
    "stimlog": frozenset({"type", "run_id", "entries", "active"}),
    "result": frozenset({"type", "run_id", "req", "cmd", "t", "status", "reason", "stim_id",
                         "n_cells", "amp_mv", "t_accept", "t_end_planned", "t_target",
                         "phase_before", "phase_after", "changed", "phase_clock_reset",
                         "factor"}),
    "hello": frozenset({"type", "client_id"}),
}


def _incoming(net, i):
    ids = net.in_ids[net.in_ptr[i]:net.in_ptr[i + 1]]
    return ids[net.alive[ids]]


def _outgoing(net, i):
    ids = net.out_ids[net.out_ptr[i]:net.out_ptr[i + 1]]
    return ids[net.alive[ids]]


def make_frame(e):
    p, net = e.p, e.net
    e._frame_seq += 1
    ticks = max(1, e._buf_ticks)
    spikes, total = [], 0
    per_region = np.zeros((len(net.region_names), e._buf_ticks), np.int32)
    for dt, s in enumerate(e._buf_spikes):
        total += s.size
        if s.size:
            per_region[:, dt] = np.bincount(net.region[s], minlength=len(net.region_names))
            if len(spikes) < p.FRAME_SPIKE_CAP:
                room = p.FRAME_SPIKE_CAP - len(spikes)
                spikes.extend([int(i), dt] for i in s[:room])
    regions = {}
    for rid, name in enumerate(net.region_names):
        sl = net.region_slice[name]
        n = sl.stop - sl.start
        regions[name] = dict(rate_hz=float(per_region[rid].sum() / n / (ticks / 1000.0)),
                             spikes_per_tick=per_region[rid].tolist())
    touched = e._buf_touched or [0]
    frame = dict(
        t=e.t, phase=e.phase, age_s=e.age_s, g=e.g, g_struct=e.g_struct,
        sense_gated=e.sense_gated, born_per_s=e.born_per_s, died_per_s=e.died_per_s,
        ticks=e._buf_ticks,
        n_syn_alive=net.n_alive, syn_born_total=e.stats["syn_born_total"],
        syn_died_total=e.stats["syn_died_total"], spike_total=e.stats["spike_total"],
        syn_touched_mean=float(np.mean(touched)), born_count=e._born_count,
        died_count=e._died_count, regions=regions,
        spikes=spikes, truncated=total > p.FRAME_SPIKE_CAP,
        born=[list(b) for b in e._buf_born[:p.FRAME_STRUCT_CAP]],
        died=[list(d) for d in e._buf_died[:p.FRAME_STRUCT_CAP]],
        wall_ratio=None, growth_halted=dict(e.growth_halted), store_clamped=e.store_clamped,
        seq=e._frame_seq, stim_active=e.stims_active(), stim_events=e._buf_stim_events)
    e._buf_stim_events = []
    e._buf_spikes, e._buf_touched, e._buf_born, e._buf_died, e._buf_ticks = [], [], [], [], 0
    e._born_count = e._died_count = 0
    assert set(frame) == FRAME_KEYS, set(frame) ^ FRAME_KEYS
    return frame


def inspect_neuron(e, neuron_id):
    net = e.net
    i = int(neuron_id)
    inc = _incoming(net, i)
    exc = inc[net.is_exc[net.pre[inc]]]
    inh = inc[~net.is_exc[net.pre[inc]]]
    top = np.concatenate([exc[np.argsort(-net.w[exc])[:10]], inh[np.argsort(net.w[inh])[:10]]])
    return dict(id=i, region=net.region_names[int(net.region[i])], is_exc=bool(net.is_exc[i]),
                v=float(net.v[i]), theta=float(net.theta[i]), rate_hz=float(net.rate[i]),
                in_deg=int(inc.size), out_deg=int(_outgoing(net, i).size),
                top_in=[[int(net.pre[j]), float(net.w[j])] for j in top],
                v_trace=list(e._v_trace) if e._watch_id == i else [])


def _hist(vals, bins):
    counts, edges = np.histogram(vals, bins=bins)
    return dict(edges=edges.tolist(), counts=counts.tolist())


def region_stats(e, name):
    net = e.net
    sl = net.region_slice[name]
    alive = np.flatnonzero(net.alive)
    in_m = (net.post[alive] >= sl.start) & (net.post[alive] < sl.stop)
    out_m = (net.pre[alive] >= sl.start) & (net.pre[alive] < sl.stop)
    w = np.abs(net.w[alive[in_m]])
    rates = net.rate[sl]
    return dict(name=name, n=sl.stop - sl.start, rate_hz=float(rates.mean()),
                n_syn_in=int(in_m.sum()), n_syn_out=int(out_m.sum()),
                w_hist=_hist(w if w.size else np.zeros(1), e.p.HIST_BINS),
                rate_hist=_hist(rates, e.p.HIST_BINS))


def layout(e):
    net = e.net
    regions = {}
    for rid, name in enumerate(net.region_names):
        sl = net.region_slice[name]
        regions[name] = dict(id=rid, n=sl.stop - sl.start,
                             n_exc=int(net.is_exc[sl].sum()))
    ids = e.syn_sample
    ids = ids[net.alive[ids]]
    return dict(regions=regions, x=net.x.tolist(), y=net.y.tolist(),
                region=net.region.tolist(), is_exc=net.is_exc.tolist(),
                patterns=[pat.tolist() for pat in e.patterns],
                synapse_sample=[[int(i), int(net.pre[i]), int(net.post[i])] for i in ids])


def config(e, batch_ticks, pattern_ticks):
    p = e.p
    return dict(dt_ms=p.DT_MS, batch_ticks=int(batch_ticks), pattern_amp_mv=p.PATTERN_AMP_MV,
                pattern_ticks=int(pattern_ticks), wake_ticks=p.WAKE_TICKS,
                sleep_ticks=p.SLEEP_TICKS, g_wake=p.G_WAKE, g_sleep=p.G_SLEEP,
                sweep_ticks=p.SWEEP_TICKS, rate_ema_alpha=p.RATE_EMA_ALPHA,
                frame_spike_cap=p.FRAME_SPIKE_CAP, v_trace_ticks=p.V_TRACE_TICKS,
                hist_bins=p.HIST_BINS, n_patterns=len(e.patterns),
                pattern_frac=p.PATTERN_FRAC, stimlog_max=p.STIMLOG_MAX, seed=e.seed)


def stimlog(e):
    return dict(entries=[dict(r) for r in e.stimlog], active=e.stims_active())
