"""K0.3 population test: imposed pre-before-post pairing on a warmed network.

Question
--------
Does deliberately imposed pre-before-post pairing produce pathway selectivity of
pattern-A sense inputs onto a fixed ctx target set, under the *unchanged* pair-STDP
rule, unchanged scaling, structure, noise, spontaneous activity and phase schedule?

Postsynaptic current injection is an **experimental intervention**. A pass here
demonstrates that the population responds to imposed pairing; it does not
demonstrate autonomous sensory learning.

Pulse schedule rationale
------------------------
The three synchronous A volleys measured on the warmed seed-1 network peak 29, 59
and 91 ticks after presentation onset (after ~110 ticks the A spikes are spread
uniformly at ~25 Hz). Each pulse is placed 10 ticks after a volley peak -- the same
lag the two-neuron K0.3 test uses, and longer than every A->ctx_A delay (1..4
ticks), so the paired pre spikes are delivered before the induced post spike.
3 pulses x 20 trials = 60 pairings, the two-neuron test's count. 30 mV x 1 tick is
the two-neuron test's pulse; measured on the warmed network it fires 89 % of ctx_A
in the pulse tick. The schedule is fixed here and is not tuned to the outcome.

Nothing in this module changes engine behaviour. The engine RNG is never drawn
from by test-side code; the only RNG created here is
``np.random.default_rng(CONTROL_RNG_SEED)`` for the control schedule. No spike
flags are forced, no state is reset, turnover is not frozen, ``set_sleep`` and
``frame`` are never called, and the phase schedule runs as it is.
"""

import copy
import os
import sys
import time
import types

import numpy as np

if __package__ in (None, ""):  # run directly as `python tests/k03_pairing.py`
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brainsim import params
from brainsim.engine import Engine

SEED = 1
WARMUP_TICKS = 120_000
TRIALS = 20
ON_TICKS = 300
OFF_TICKS = 700
PULSE_OFFSETS = (39, 69, 101)   # ticks after presentation onset
PULSE_AMP_MV = 30.0
PULSE_TICKS = 1
CONTROL_RNG_SEED = 20260911
CONTROL_MIN_SPACING = 5         # ticks
LAG_WINDOW = 50                 # ms, pair-count window

D_MAX = params.D_MAX
TRIAL_TICKS = ON_TICKS + OFF_TICKS
TOTAL_TICKS = TRIALS * TRIAL_TICKS
CEIL_FRAC = 0.999


# --------------------------------------------------------------------------- #
# engine construction
# --------------------------------------------------------------------------- #

def _deepcopyable_params():
    return types.SimpleNamespace(**{k: getattr(params, k) for k in dir(params) if k.isupper()})


def _drain_telemetry(eng):
    eng._buf_spikes = []
    eng._buf_touched = []
    eng._buf_ticks = 0


def warm_engine(seed=SEED):
    """Build the engine and run it forward WARMUP_TICKS with nothing imposed."""
    eng = Engine(seed=seed, params=_deepcopyable_params())
    remaining = WARMUP_TICKS - D_MAX
    while remaining:
        chunk = min(1000, remaining)
        eng.step(chunk)
        remaining -= chunk
        _drain_telemetry(eng)
    # last D_MAX ticks one at a time so the first trial's deliveries are attributable
    spk = np.zeros((D_MAX + 1, eng.net.n), bool)
    for _ in range(D_MAX):
        t = eng.t
        eng.step(1)
        s = eng._buf_spikes[-1]
        _drain_telemetry(eng)
        spk[t % (D_MAX + 1)] = False
        spk[t % (D_MAX + 1), s] = True
    assert eng.t == WARMUP_TICKS, eng.t
    assert eng.phase == "wake", eng.phase
    return eng, spk


def select_ctx_a(net, A):
    """ctx cells whose alive incoming sense synapses are more than half from A."""
    sense = net.region_slice["sense"]
    ctx = net.region_slice["ctx"]
    pre, post = net.pre, net.post
    m = (net.alive
         & (pre >= sense.start) & (pre < sense.stop)
         & (post >= ctx.start) & (post < ctx.stop))
    ids = np.flatnonzero(m)
    in_a = np.isin(pre[ids], A)
    tot = np.bincount(post[ids], minlength=net.n)
    n_a = np.bincount(post[ids][in_a], minlength=net.n)
    return np.flatnonzero((tot > 0) & (n_a * 2 > tot)).astype(np.int64)


def control_schedule(rng):
    """TRIALS triples of pulse offsets, uniform in [0, ON_TICKS), spacing >= CONTROL_MIN_SPACING."""
    out = []
    for _ in range(TRIALS):
        while True:
            o = np.sort(rng.integers(0, ON_TICKS, 3))
            if np.all(np.diff(o) >= CONTROL_MIN_SPACING):
                break
        out.append(tuple(int(v) for v in o))
    return out


# --------------------------------------------------------------------------- #
# one arm
# --------------------------------------------------------------------------- #

def _tracked(net, ctx_a_mask, sense):
    pre, post = net.pre, net.post
    return np.flatnonzero(net.alive
                          & ctx_a_mask[post]
                          & (pre >= sense.start) & (pre < sense.stop)).astype(np.int64)


def run_arm(eng, spk, ctx_a, A, offsets, base, pattern=0, present=True):
    """Run TRIALS presentations with the given per-trial pulse offsets, instrumented.

    ``base`` is the shared baseline snapshot dict (identical for both arms, taken
    before the deepcopy).  ``pattern`` selects which pattern is presented at each
    trial start (``eng.present(pattern, ON_TICKS)``) when ``present`` is True;
    ``present=False`` runs the trial with no presentation at all. ``offsets``
    entries may be ``()`` (no pulse that trial). Returns the result dict
    described in the contract.
    """
    net = eng.net
    n = net.n
    sense = net.region_slice["sense"]
    ctx = net.region_slice["ctx"]
    n_ctx = ctx.stop - ctx.start
    ring_mod = D_MAX + 1

    ctx_a = np.asarray(ctx_a, np.int64)
    ctx_a_mask = np.zeros(n, bool)
    ctx_a_mask[ctx_a] = True
    ctx_a_pos = np.full(n, -1, np.int64)
    ctx_a_pos[ctx_a] = np.arange(ctx_a.size)
    a_mask = np.zeros(n, bool)
    a_mask[A] = True

    ltp_acc = np.zeros(net.s_max, np.float64)
    ltd_acc = np.zeros(net.s_max, np.float64)
    scal_acc = np.zeros(net.s_max, np.float64)
    scal_pred_acc = np.zeros(net.s_max, np.float64)
    deliver_scratch = np.zeros(net.s_max, bool)
    pre_win = np.zeros(n, bool)          # pre cells that spiked in the current sweep window

    t_start = eng.t
    phase_start = eng.phase
    phases_seen = set()
    g_seen = set()
    max_resid = 0.0
    scal_pred_max = 0.0
    n_sweeps = 0
    ring_vs_spk_disagreements = 0
    ring_vs_spk_disagreement_slots = 0
    ring_vs_spk_events = []

    pulse_ticks = []                     # absolute entry ticks carrying a pulse
    pulse_frac = []
    ctx_count = np.zeros(TOTAL_TICKS, np.int32)
    pre_spk = np.zeros((sense.stop - sense.start, TOTAL_TICKS), np.float32)
    ctxa_spk = np.zeros((ctx_a.size, TOTAL_TICKS), np.float32)
    a_on = a_off = nona_on = nona_off = 0
    cae_on = cae_off = cai_on = cai_off = 0
    ctx_on = ctx_off = 0
    n_on = TRIALS * ON_TICKS
    n_off = TRIALS * OFF_TICKS

    ctx_a_exc = ctx_a[net.is_exc[ctx_a]]
    ctx_a_inh = ctx_a[~net.is_exc[ctx_a]]
    nona_sense = np.setdiff1d(np.arange(sense.start, sense.stop), np.asarray(A))

    mode = getattr(eng.p, "HOMEOSTAT", "scaling")
    theta_h_ctx_a_trace = []

    tr_decay = eng._tr_decay
    T = preT = postT = bornT = excT = am0 = ap0 = wmax0 = None

    def refresh():
        """Recompute the tracked set and its window-start identity/per-neuron constants."""
        nonlocal T, preT, postT, bornT, excT, am0, ap0, wmax0
        T = _tracked(net, ctx_a_mask, sense)
        preT, postT, bornT = net.pre[T], net.post[T], net.born[T]
        excT = net.is_exc[preT]
        am0, ap0, wmax0 = net.a_minus_n[postT], net.a_plus_n[postT], net.w_max_n[postT]

    refresh()

    k_global = 0
    for trial in range(TRIALS):
        offs = set(int(o) for o in offsets[trial])
        if present:
            eng.present(pattern, ON_TICKS)
        for k in range(TRIAL_TICKS):
            t = eng.t
            is_pulse = k in offs
            if is_pulse:
                eng.inject(ctx_a, PULSE_AMP_MV, PULSE_TICKS)
                pulse_ticks.append(t)

            phases_seen.add(eng.phase)
            g = eng.g
            g_seen.add(float(g))
            idx_t = (t // 1000) * 1000

            # --- pre-step snapshot -------------------------------------------------
            w0 = net.w[T].copy()
            y0 = net.y_post[postT].copy()
            x0 = net.x_pre[preT].copy()
            trans = net.conduct[T] <= idx_t

            bucket = eng.ring[t % ring_mod]
            if bucket:
                d = bucket[0] if len(bucket) == 1 else np.concatenate(bucket)
                d = d[net.alive[d]]
                de = d[net.is_exc[net.pre[d]]]
            else:
                de = np.empty(0, np.int32)
            deliver_scratch[de] = True
            delivered = deliver_scratch[T]
            deliver_scratch[de] = False

            # The contract's spike-ring prediction, kept as a cross-check only.  The
            # delivery mask actually used above is read from the engine's own ring
            # bucket, which is exact.  A nonzero disagreement count is EXPECTED across
            # sweep boundaries: the engine fixes a synapse's membership when the pre
            # spiked (it was pushed into the ring from the OUT index of tick t-d), while
            # this prediction tests membership at the delivery tick t (conduct <= idx_t)
            # and reads the slot's CURRENT pre.  So a synapse that gained conduction, or
            # a slot that was killed and reborn as a different synapse, at a sweep
            # between t-d and t will disagree.  Every disagreement is logged with its
            # tick and whether it falls within D_MAX ticks after a sweep boundary.
            pred = trans & spk[(t - net.delay[T].astype(np.int64)) % ring_mod, preT]
            n_dis = int(np.count_nonzero(pred != delivered))
            if n_dis:
                ring_vs_spk_disagreements += 1
                ring_vs_spk_disagreement_slots += n_dis
                ring_vs_spk_events.append((int(t), n_dis, bool(t % 1000 < D_MAX)))

            g32 = np.float32(g)
            w1 = np.where(delivered,
                          np.maximum(w0 * (np.float32(1.0) - (g32 * am0) * y0), np.float32(0.0)),
                          w0).astype(np.float32)
            ltd = w1.astype(np.float64) - w0.astype(np.float64)

            # --- the engine tick ---------------------------------------------------
            eng.step(1)
            s = eng._buf_spikes[-1]
            _drain_telemetry(eng)

            spiked = np.zeros(n, bool)
            spiked[s] = True
            xu = (x0 * tr_decay).astype(np.float32)
            # `& excT` mirrors engine.py:256 (`is_exc[pre[inc]]`); all sense cells are
            # excitatory today, so it is a no-op now but not a no-op by construction.
            ltp32 = np.where(spiked[postT] & trans & excT,
                             ((g32 * ap0) * xu) * (wmax0 - w1),
                             np.float32(0.0)).astype(np.float32)
            w_pred = (w1 + ltp32).astype(np.float32)
            w2 = net.w[T]
            resid = w2.astype(np.float64) - w_pred.astype(np.float64)

            ltp_acc[T] += ltp32.astype(np.float64)
            ltd_acc[T] += ltd

            pre_win[s] = True
            swept = (t + 1) % 1000 == 0
            if swept:
                n_sweeps += 1
                # identity compared against the identity T was refreshed with, so this
                # is meaningful for slots born after the baseline snapshot too
                keep = (net.alive[T]
                        & (net.pre[T] == preT) & (net.post[T] == postT)
                        & (net.born[T] == bornT))
                scal_acc[T[keep]] += resid[keep]

                # --- independent prediction of the sweep's scaling step (addendum A) ---
                # eng.phase read after the step: the phase flip, if any, happens before
                # the sweep in the same step, so this is the phase the sweep saw.
                rt = np.maximum(net.r_target, np.float32(1e-6))
                factor = np.float32(1.0) + np.clip(
                    params.ETA_SCALING * (net.r_target - net.rate) / rt,
                    -params.SCALING_CLIP, params.SCALING_CLIP).astype(np.float32)
                factor[net.r_target <= 0] = np.float32(1.0)
                if mode == "intrinsic":
                    scal_pred = np.zeros_like(w_pred)
                else:
                    used = pre_win[preT] & excT & (eng.phase != "sleep")
                    scaled = np.clip(w_pred * factor[postT], np.float32(0.0), wmax0)
                    scal_pred = np.where(used, scaled, w_pred).astype(np.float32) - w_pred
                scal_pred_acc[T[keep]] += scal_pred[keep].astype(np.float64)
                if keep.any():
                    scal_pred_max = max(scal_pred_max,
                                        float(np.abs(scal_pred[keep].astype(np.float64)
                                                     - resid[keep]).max()))
                pre_win[:] = False
                th_a = net.theta_h[ctx_a]
                theta_h_ctx_a_trace.append((int(t + 1), float(th_a.mean()),
                                            float(th_a.min()), float(th_a.max())))
            else:
                if resid.size:
                    max_resid = max(max_resid, float(np.abs(resid).max()))

            # --- telemetry ---------------------------------------------------------
            spk[t % ring_mod] = False
            spk[t % ring_mod, s] = True

            in_ctx = (s >= ctx.start) & (s < ctx.stop)
            ctx_count[k_global] = int(in_ctx.sum())
            sm = s[(s >= sense.start) & (s < sense.stop)]
            pre_spk[sm - sense.start, k_global] = 1.0
            cm = ctx_a_pos[s]
            cm = cm[cm >= 0]
            ctxa_spk[cm, k_global] = 1.0

            n_a_sp = int(a_mask[sm].sum())
            n_sense_sp = sm.size
            sc = s[ctx_a_mask[s]]
            n_ca = sc.size
            n_cae = int(net.is_exc[sc].sum())
            n_cai = n_ca - n_cae
            if k < ON_TICKS:
                a_on += n_a_sp
                nona_on += n_sense_sp - n_a_sp
                cae_on += n_cae
                cai_on += n_cai
                ctx_on += int(in_ctx.sum())
            else:
                a_off += n_a_sp
                nona_off += n_sense_sp - n_a_sp
                cae_off += n_cae
                cai_off += n_cai
                ctx_off += int(in_ctx.sum())

            if is_pulse:
                pulse_frac.append(n_ca / max(1, ctx_a.size))

            if swept:
                refresh()

            k_global += 1

    t_end = eng.t
    res = {
        "t_start": int(t_start), "t_end": int(t_end),
        "phase_start": phase_start, "phase_end": eng.phase,
        "sense_gated_end": bool(eng.sense_gated), "g_end": float(eng.g),
        "phases_seen": sorted(phases_seen), "g_seen": sorted(g_seen),
        "n_ctx_a": int(ctx_a.size),
        "n_ctx_a_exc": int(ctx_a_exc.size), "n_ctx_a_inh": int(ctx_a_inh.size),
        "pattern_presented": pattern if present else None,
        "pulse_ticks_total": len(pulse_ticks),
        "pulse_spike_frac_mean": float(np.mean(pulse_frac)) if pulse_frac else 0.0,
        "pulse_spike_frac_min": float(np.min(pulse_frac)) if pulse_frac else 0.0,
        "instrument_max_residual_nonsweep": float(max_resid),
        "scaling_pred_vs_resid_max_abs": float(scal_pred_max),
        "n_sweeps": int(n_sweeps),
        "ring_vs_spk_disagreements": int(ring_vs_spk_disagreements),
        "ring_vs_spk_disagreement_slots": int(ring_vs_spk_disagreement_slots),
        "ring_vs_spk_events": ring_vs_spk_events,
        "homeostat": mode,
        "theta_h_ctx_a_trace": theta_h_ctx_a_trace,
        "theta_h_ctx_a_final": (theta_h_ctx_a_trace[-1][1:] if theta_h_ctx_a_trace
                                else (0.0, 0.0, 0.0)),
    }

    b = int(np.argmax(ctx_count))
    res["ctx_burst_max_frac"] = float(ctx_count[b] / n_ctx)
    res["ctx_burst_max_t"] = int(t_start + b)
    pulse_set = set(pulse_ticks)
    res["ctx_burst_max_at_pulse"] = bool(res["ctx_burst_max_t"] in pulse_set)

    def hz(count, cells, ticks):
        return float(count * 1000.0 / max(1, cells * ticks))

    res["rates_hz"] = {
        "a_on": hz(a_on, len(A), n_on), "a_off": hz(a_off, len(A), n_off),
        "nona_sense_on": hz(nona_on, nona_sense.size, n_on),
        "nona_sense_off": hz(nona_off, nona_sense.size, n_off),
        "ctx_a_exc_on": hz(cae_on, ctx_a_exc.size, n_on),
        "ctx_a_exc_off": hz(cae_off, ctx_a_exc.size, n_off),
        "ctx_a_inh_on": hz(cai_on, ctx_a_inh.size, n_on),
        "ctx_a_inh_off": hz(cai_off, ctx_a_inh.size, n_off),
        "ctx_all_on": hz(ctx_on, n_ctx, n_on), "ctx_all_off": hz(ctx_off, n_ctx, n_off),
    }

    # ------------------------------------------------------------------ groups
    T0 = base["slots"]
    born0, pre0, post0, w_base = base["born"], base["pre"], base["post"], base["w"]
    grp0 = base["group"]
    surv_mask = (net.alive[T0] & (net.pre[T0] == pre0)
                 & (net.post[T0] == post0) & (net.born[T0] == born0))

    T_fin = _tracked(net, ctx_a_mask, sense)
    grp_fin = a_mask[net.pre[T_fin]]
    surv_slots = set(T0[surv_mask].tolist())
    is_birth = np.array([int(x) not in surv_slots for x in T_fin], bool) if T_fin.size \
        else np.zeros(0, bool)

    pulse_mask_t = np.zeros(TOTAL_TICKS, bool)
    pulse_rel = [p - t_start for p in pulse_ticks]
    pulse_mask_t[pulse_rel] = True
    lag, ck = _pair_timing(base, ctx_a_pos, pre_spk, ctxa_spk, pulse_mask_t, sense)
    res.update(ck)
    res.update(_per_trial(base, ctx_a_pos, pre_spk, ctxa_spk, pulse_rel, pulse_frac,
                          ctx_count, n_ctx, sense))

    groups = {}
    for name, sel0, self_ in (("A", grp0, grp_fin), ("nonA", ~grp0, ~grp_fin)):
        b0 = T0[sel0]
        sv = T0[sel0 & surv_mask]
        fin = T_fin[self_]
        bir = T_fin[self_ & is_birth] if T_fin.size else T_fin
        wb = w_base[sel0].astype(np.float64)
        wf = net.w[fin].astype(np.float64)
        wmb = net.w_max_n[post0[sel0]].astype(np.float64)
        wmf = net.w_max_n[net.post[fin]].astype(np.float64)
        wsb = w_base[sel0 & surv_mask].astype(np.float64)
        wsf = net.w[sv].astype(np.float64)
        dw = float(np.mean(wsf - wsb)) if sv.size else 0.0
        ltp_m = float(ltp_acc[sv].mean()) if sv.size else 0.0
        ltd_m = float(ltd_acc[sv].mean()) if sv.size else 0.0
        sc_m = float(scal_acc[sv].mean()) if sv.size else 0.0
        scp_m = float(scal_pred_acc[sv].mean()) if sv.size else 0.0
        g = {
            "n_baseline": int(b0.size), "n_final_alive": int(fin.size),
            "n_survivors": int(sv.size), "n_deaths": int(b0.size - sv.size),
            "n_births": int(bir.size),
            "mean_w_baseline": float(wb.mean()) if wb.size else 0.0,
            "mean_w_final": float(wf.mean()) if wf.size else 0.0,
            "mean_w_over_wmax_baseline": float((wb / wmb).mean()) if wb.size else 0.0,
            "mean_w_over_wmax_final": float((wf / wmf).mean()) if wf.size else 0.0,
            "frac_ceiling_baseline": float((wb >= CEIL_FRAC * wmb).mean()) if wb.size else 0.0,
            "frac_ceiling_final": float((wf >= CEIL_FRAC * wmf).mean()) if wf.size else 0.0,
            "mean_w_survivors_baseline": float(wsb.mean()) if sv.size else 0.0,
            "mean_w_survivors_final": float(wsf.mean()) if sv.size else 0.0,
            "mean_dw_survivors": dw,
            "mean_w_births_final": float(net.w[bir].astype(np.float64).mean()) if bir.size else 0.0,
            "ltp_mean": ltp_m, "ltd_mean": ltd_m, "scaling_mean": sc_m,
            "scaling_pred_mean": scp_m,
            # By construction closure_residual is the signed sum of the NON-sweep
            # residuals over survivors: every sweep-tick residual is booked to
            # scaling_mean.  It therefore cannot detect an error in the scaling step.
            # scaling_pred_mean / scaling_pred_vs_resid_max_abs is the independent
            # check that covers sweep ticks.
            "closure_residual": dw - (ltp_m + ltd_m + sc_m),
        }
        g.update(lag[name])
        gp = g["pulse_lag_hist"]
        if pulse_ticks:
            g["pulse_causal_over_anticausal"] = (
                float(g["pulse_causal_pairs"] / g["pulse_anticausal_pairs"])
                if g["pulse_anticausal_pairs"] else float("inf"))
            peak_i = int(np.argmax(gp))
            med = float(np.median(gp))
            g["pulse_lag_peak"] = peak_i - LAG_WINDOW
            g["pulse_lag_peak_over_median"] = float(gp[peak_i] / med) if med else float("inf")
        else:
            # zero-pulse arm: no pulse-window pairs exist at all, so the
            # causal/anticausal ratio and the peak/median ratio are undefined.
            g["pulse_causal_over_anticausal"] = float("nan")
            g["pulse_lag_peak"] = 0
            g["pulse_lag_peak_over_median"] = float("nan")
        groups[name] = g
    res["groups"] = groups

    def ratio(a, b):
        return float(a / b) if b else float("inf")

    res["ratio_baseline"] = ratio(groups["A"]["mean_w_baseline"], groups["nonA"]["mean_w_baseline"])
    res["ratio_final"] = ratio(groups["A"]["mean_w_final"], groups["nonA"]["mean_w_final"])
    res["ratio_final_survivors"] = ratio(groups["A"]["mean_w_survivors_final"],
                                         groups["nonA"]["mean_w_survivors_final"])

    m_old = (net.alive
             & (net.pre >= sense.start) & (net.pre < sense.stop)
             & (net.post >= ctx.start) & (net.post < ctx.stop))
    old = np.flatnonzero(m_old)
    old_a = a_mask[net.pre[old]]
    res["old_measure_ratio_final"] = ratio(
        float(net.w[old[old_a]].mean()) if old_a.any() else 0.0,
        float(net.w[old[~old_a]].mean()) if (~old_a).any() else 0.0)
    return res


# --------------------------------------------------------------------------- #
# pair timing (offline)
# --------------------------------------------------------------------------- #

def _pair_timing(base, ctx_a_pos, pre_spk, ctxa_spk, pulse_mask_t, sense):
    """Cross-correlate baseline-synapse pre/post spike trains, vectorised over pre cells."""
    n_pre = pre_spk.shape[0]
    n_ca = ctxa_spk.shape[0]
    L = LAG_WINDOW

    B = np.zeros((n_pre, n_ca), np.float32)
    rows = base["pre"] - sense.start
    cols = ctx_a_pos[base["post"]]
    np.add.at(B, (rows, cols), 1.0)

    post_sum = B @ ctxa_spk                       # [n_pre, TOTAL_TICKS]
    trains = {"": post_sum, "pulse_": post_sum * pulse_mask_t}

    out = {"A": {}, "nonA": {}}
    grp = base["group"]
    a_rows = np.zeros(n_pre, bool)
    a_rows[base["pre"][grp] - sense.start] = True

    for prefix, P in trains.items():
        # the same path the brute-force crosscheck validates
        hist = {"A": _lag_counts(pre_spk[a_rows], P[a_rows]),
                "nonA": _lag_counts(pre_spk[~a_rows], P[~a_rows])}
        for name in ("A", "nonA"):
            h = hist[name]
            causal = h[L + 1:]
            anti = h[:L]
            d_pos = np.arange(1, L + 1)
            out[name][prefix + "lag_hist"] = [float(v) for v in h]
            out[name][prefix + "causal_pairs"] = float(causal.sum())
            out[name][prefix + "anticausal_pairs"] = float(anti.sum())
            out[name][prefix + "simultaneous_pairs"] = float(h[L])
            out[name][prefix + "causal_trace_sum"] = float((causal * np.exp(-d_pos / 20.0)).sum())
            out[name][prefix + "anticausal_trace_sum"] = float(
                (anti[::-1] * np.exp(-d_pos / 20.0)).sum())
            if prefix == "pulse_":
                out[name]["pulse_causal_lag_median"] = _weighted_median(d_pos, causal)

    ck = _crosscheck(base, ctx_a_pos, pre_spk, ctxa_spk, sense)
    return out, ck


def _lag_counts(pre_rows, post_rows):
    """Σ_t pre[j,t] * post[j,t+Δ] per pre row, for Δ = −LAG_WINDOW..LAG_WINDOW."""
    L = LAG_WINDOW
    m = post_rows.shape[1]
    pad = np.zeros((post_rows.shape[0], m + 2 * L), np.float32)
    pad[:, L:L + m] = post_rows
    h = np.zeros(2 * L + 1, np.float64)
    for i, dl in enumerate(range(-L, L + 1)):
        h[i] = float((pre_rows * pad[:, L + dl:L + dl + m]).sum(dtype=np.float64))
    return h


def _crosscheck(base, ctx_a_pos, pre_spk, ctxa_spk, sense):
    """Brute-force validation of the vectorised pair counts (addendum D).

    40 baseline A + 40 baseline non-A synapses, drawn with a test-side rng(7) (never
    the engine RNG).  For each, the lag histogram is built directly from the two
    cells' spike times with np.subtract.outer, and compared to the same vectorised
    code path restricted to exactly those synapses.  Only the all-post-spikes variant
    is checked: the pulse-only variant is the identical code with a tick mask applied
    to the post trains, so it adds no new arithmetic.
    """
    rng = np.random.default_rng(7)
    L = LAG_WINDOW
    grp = base["group"]
    ok = True
    n_checked = 0
    for name, sel in (("A", grp), ("nonA", ~grp)):
        idx = np.flatnonzero(sel)
        pick = idx if idx.size <= 40 else rng.choice(idx, 40, replace=False)
        n_checked += int(pick.size)
        pre_ids = base["pre"][pick] - sense.start
        post_ids = ctx_a_pos[base["post"][pick]]

        brute = np.zeros(2 * L + 1, np.float64)
        for j, i in zip(pre_ids, post_ids):
            t_pre = np.flatnonzero(pre_spk[j])
            t_post = np.flatnonzero(ctxa_spk[i])
            if t_pre.size == 0 or t_post.size == 0:
                continue
            d = np.subtract.outer(t_post, t_pre).ravel()
            d = d[np.abs(d) <= L]
            brute += np.bincount(d + L, minlength=2 * L + 1)

        rows = np.unique(pre_ids)
        pos = {int(r): k for k, r in enumerate(rows)}
        Bs = np.zeros((rows.size, ctxa_spk.shape[0]), np.float32)
        np.add.at(Bs, ([pos[int(j)] for j in pre_ids], post_ids), 1.0)
        vec = _lag_counts(pre_spk[rows], Bs @ ctxa_spk)
        ok = ok and bool(np.array_equal(np.rint(brute).astype(np.int64),
                                        np.rint(vec).astype(np.int64)))
    return {"pair_count_crosscheck_ok": bool(ok), "pair_count_crosscheck_n": int(n_checked)}


def _per_trial(base, ctx_a_pos, pre_spk, ctxa_spk, pulse_rel, pulse_frac,
               ctx_count, n_ctx, sense):
    """Per-trial pulse-window pair counts for group A (addendum C)."""
    L = LAG_WINDOW
    grp = base["group"]
    a_rows = np.unique(base["pre"][grp] - sense.start)
    pos = {int(r): k for k, r in enumerate(a_rows)}
    B = np.zeros((a_rows.size, ctxa_spk.shape[0]), np.float32)
    np.add.at(B, ([pos[int(j)] for j in base["pre"][grp] - sense.start],
                  ctx_a_pos[base["post"][grp]]), 1.0)
    post_sum = B @ ctxa_spk                        # [n_A_pre, TOTAL_TICKS]

    pre_pad = np.zeros((a_rows.size, TOTAL_TICKS + 2 * L), np.float32)
    pre_pad[:, L:L + TOTAL_TICKS] = pre_spk[a_rows]

    causal, anti, med, frac, burst = [], [], [], [], []
    fracs = np.asarray(pulse_frac, np.float64).reshape(TRIALS, -1)
    for k in range(TRIALS):
        lo, hi = k * TRIAL_TICKS, (k + 1) * TRIAL_TICKS
        mask = np.zeros(TRIAL_TICKS, np.float32)
        for p in pulse_rel:
            if lo <= p < hi:
                mask[p - lo] = 1.0
        Pw = post_sum[:, lo:hi] * mask
        h = np.zeros(2 * L + 1, np.float64)
        for i, dl in enumerate(range(-L, L + 1)):
            seg = pre_pad[:, lo + L - dl:lo + L - dl + TRIAL_TICKS]
            h[i] = float((Pw * seg).sum(dtype=np.float64))
        d_pos = np.arange(1, L + 1)
        causal.append(float(h[L + 1:].sum()))
        anti.append(float(h[:L].sum()))
        med.append(_weighted_median(d_pos, h[L + 1:]))
        frac.append(float(fracs[k].mean()) if fracs.shape[1] else 0.0)
        burst.append(float(ctx_count[lo:hi].max() / n_ctx))
    return {"per_trial_pulse_causal": causal, "per_trial_pulse_anticausal": anti,
            "per_trial_pulse_lag_median": med, "per_trial_pulse_spike_frac": frac,
            "per_trial_ctx_burst_max_frac": burst}


def _weighted_median(values, weights):
    tot = float(weights.sum())
    if tot <= 0:
        return float("nan")
    c = np.cumsum(weights)
    return float(values[int(np.searchsorted(c, tot / 2.0))])


# --------------------------------------------------------------------------- #
# experiment
# --------------------------------------------------------------------------- #

def run_experiment(seed=SEED):
    eng, spk = warm_engine(seed)
    net = eng.net
    sense = net.region_slice["sense"]
    A = eng.patterns[0]
    ctx_a = select_ctx_a(net, A)
    assert ctx_a.size > 0, "no ctx_a cells selected"

    ctx_a_mask = np.zeros(net.n, bool)
    ctx_a_mask[ctx_a] = True
    T0 = _tracked(net, ctx_a_mask, sense)
    a_mask = np.zeros(net.n, bool)
    a_mask[A] = True
    base = {
        "slots": T0, "pre": net.pre[T0].copy(), "post": net.post[T0].copy(),
        "born": net.born[T0].copy(), "w": net.w[T0].copy(),
        "group": a_mask[net.pre[T0]],
    }
    assert base["group"].any(), "group A empty"
    assert (~base["group"]).any(), "group nonA empty"

    ctrl = copy.deepcopy(eng)
    ctrl_spk = spk.copy()
    ctrl_offsets = control_schedule(np.random.default_rng(CONTROL_RNG_SEED))

    pairing = run_arm(eng, spk, ctx_a, A, [PULSE_OFFSETS] * TRIALS, base)
    control = run_arm(ctrl, ctrl_spk, ctx_a, A, ctrl_offsets, base)
    return {"ctx_a": ctx_a.tolist(), "pairing": pairing, "control": control,
            "control_offsets": ctrl_offsets}


# --------------------------------------------------------------------------- #
# report
# --------------------------------------------------------------------------- #

def _row(label, a, b, fmt="{: .6g}"):
    def f(v):
        if isinstance(v, bool) or isinstance(v, str):
            return str(v)
        return fmt.format(v)
    return f"  {label:<34}{f(a):>20}{f(b):>20}"


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("intrinsic", "scaling"), default=None)
    args, _ = ap.parse_known_args()
    prev_mode = params.HOMEOSTAT
    if args.mode is not None:
        params.HOMEOSTAT = args.mode
    try:
        t0 = time.time()
        out = run_experiment()
        wall = time.time() - t0
    finally:
        params.HOMEOSTAT = prev_mode
    p, c = out["pairing"], out["control"]

    print("=" * 76)
    print("K0.3 population imposed-pairing report")
    print(f"homeostat: {p['homeostat']}")
    print("=" * 76)
    print(f"run_experiment wall time: {wall:.1f} s")
    print(f"pulse offsets (pairing): {PULSE_OFFSETS}   amp {PULSE_AMP_MV} mV x {PULSE_TICKS} tick")
    print(f"control offsets: {out['control_offsets']}")
    print(f"ctx_a size: {p['n_ctx_a']} (exc {p['n_ctx_a_exc']}, inh {p['n_ctx_a_inh']})")
    print()
    print(f"  {'':<34}{'PAIRING':>20}{'CONTROL':>20}")
    for k in ("t_start", "t_end", "phase_start", "phase_end", "sense_gated_end", "g_end",
              "n_sweeps", "pulse_ticks_total", "pulse_spike_frac_mean", "pulse_spike_frac_min",
              "ctx_burst_max_frac", "ctx_burst_max_t", "ctx_burst_max_at_pulse",
              "instrument_max_residual_nonsweep", "scaling_pred_vs_resid_max_abs",
              "pair_count_crosscheck_ok", "pair_count_crosscheck_n",
              "ring_vs_spk_disagreements", "ring_vs_spk_disagreement_slots",
              "ratio_baseline", "ratio_final", "ratio_final_survivors",
              "old_measure_ratio_final"):
        print(_row(k, p[k], c[k]))
    print(_row("phases_seen", str(p["phases_seen"]), str(c["phases_seen"])))
    print(_row("g_seen", str(p["g_seen"]), str(c["g_seen"])))
    print()
    print("  rates (Hz)")
    for k in p["rates_hz"]:
        print(_row("  " + k, p["rates_hz"][k], c["rates_hz"][k]))

    for grp in ("A", "nonA"):
        print()
        print(f"  group {grp}")
        gp, gc = p["groups"][grp], c["groups"][grp]
        for k in ("n_baseline", "n_final_alive", "n_survivors", "n_deaths", "n_births",
                  "mean_w_baseline", "mean_w_final",
                  "mean_w_over_wmax_baseline", "mean_w_over_wmax_final",
                  "frac_ceiling_baseline", "frac_ceiling_final",
                  "mean_w_survivors_baseline", "mean_w_survivors_final", "mean_dw_survivors",
                  "mean_w_births_final", "ltp_mean", "ltd_mean", "scaling_mean",
                  "scaling_pred_mean", "closure_residual",
                  "causal_pairs", "anticausal_pairs", "simultaneous_pairs",
                  "causal_trace_sum", "anticausal_trace_sum",
                  "pulse_causal_pairs", "pulse_anticausal_pairs", "pulse_simultaneous_pairs",
                  "pulse_causal_trace_sum", "pulse_anticausal_trace_sum",
                  "pulse_causal_lag_median", "pulse_causal_over_anticausal",
                  "pulse_lag_peak", "pulse_lag_peak_over_median"):
            print(_row("  " + k, gp[k], gc[k]))
        print(f"    lag_hist (d=-50..50)       {[int(v) for v in gp['lag_hist']]}")
        print(f"    pulse_lag_hist (d=-50..50) {[int(v) for v in gp['pulse_lag_hist']]}")

    for arm, r in (("PAIRING", p), ("CONTROL", c)):
        print()
        print(f"  per-trial pulse-window pairs, group A ({arm})")
        print(f"    {'trial':>5}{'causal':>12}{'anticausal':>13}{'ratio':>9}"
              f"{'lag_median':>12}{'pulse_frac':>12}{'burst_frac':>12}")
        for k in range(TRIALS):
            ca = r["per_trial_pulse_causal"][k]
            an = r["per_trial_pulse_anticausal"][k]
            rt = ca / an if an else float("inf")
            print(f"    {k:>5}{ca:>12.0f}{an:>13.0f}{rt:>9.3f}"
                  f"{r['per_trial_pulse_lag_median'][k]:>12.1f}"
                  f"{r['per_trial_pulse_spike_frac'][k]:>12.4f}"
                  f"{r['per_trial_ctx_burst_max_frac'][k]:>12.4f}")
        rr = [ca / an if an else float("inf") for ca, an
              in zip(r["per_trial_pulse_causal"], r["per_trial_pulse_anticausal"])]
        print(f"    per-trial causal:anticausal min {min(rr):.3f}  max {max(rr):.3f}")

    print()
    print("  note: lags are somatic spike times; LTD delivery adds the synapse delay (1..4 ticks).")
    print("  note: closure_residual is, by construction, the signed sum of the NON-sweep")
    print("        residuals over survivors -- every sweep-tick residual is booked to")
    print("        scaling_mean, so closure cannot detect an error in the scaling step.")
    print("        scaling_pred_mean and scaling_pred_vs_resid_max_abs are the independent")
    print("        prediction of the sweep's scaling step and are the check that covers it.")
    print("  note: ring_vs_spk_disagreements is the number of ticks where the delivery mask")
    print("        read from the engine's ring bucket (the mask actually used, exact) differed")
    print("        from the mask predicted from the instrument's own recorded spikes and the")
    print("        slots' current delays; ring_vs_spk_disagreement_slots is the number of slot")
    print("        instances involved. These arise across sweep boundaries: the engine fixed")
    print("        membership when the pre spiked (out index of tick t-d) while the prediction")
    print("        tests conduct <= idx_t and the slot's current pre, so a synapse that gained")
    print("        conduction, or a slot killed and reborn, at a sweep in between disagrees.")
    for arm, r in (("PAIRING", p), ("CONTROL", c)):
        for tick, n_slots, near in r["ring_vs_spk_events"]:
            print(f"        {arm}: tick {tick}, {n_slots} slot(s), "
                  f"within {D_MAX} ticks after a sweep boundary: {near}")

    print()
    gA_p, gA_c = p["groups"]["A"], c["groups"]["A"]
    ok_pair = gA_p["pulse_causal_pairs"] > gA_p["pulse_anticausal_pairs"]
    print(f"VERDICT pairing established (pulse causal > anticausal, group A): {ok_pair}")
    print(f"VERDICT ratio_final >= 1.2: {p['ratio_final'] >= 1.2} "
          f"(ratio_final = {p['ratio_final']:.4f})")
    print(f"        ratios (not used for the timing verdict): pairing {p['ratio_final']:.6f}, "
          f"control {c['ratio_final']:.6f}")
    r_p, r_c = gA_p["pulse_causal_over_anticausal"], gA_c["pulse_causal_over_anticausal"]
    m_p, m_c = gA_p["pulse_lag_peak_over_median"], gA_c["pulse_lag_peak_over_median"]
    l_p, l_c = gA_p["pulse_lag_peak"], gA_c["pulse_lag_peak"]
    print(f"VERDICT control timing: A pulse-window causal:anticausal {r_c:.4f} "
          f"(pairing {r_p:.4f}); histogram peak at {l_c} ms, peak/median {m_c:.4f} "
          f"(pairing: peak at {l_p}, {m_p:.4f}); control disrupted pairing: "
          f"{abs(r_c - 1) < abs(r_p - 1) and m_c < m_p}")
    return out


if __name__ == "__main__":
    main()
