"""K0.12: synaptic scaling is held for a group latched by the anti-windup stall latch at the
*previous* sweep (one-sweep lag), released on the sweep the group's sign flips, and otherwise
behaves exactly as before (used-input, sleep, per-group isolation). Pins brainsim/engine.py
Engine._scale_hold / _scaling_step / _update_windup / _slow_sweep. Seed=1 throughout."""
import hashlib
import types

import numpy as np
import pytest

from brainsim import params
from brainsim.engine import Engine

pytestmark = pytest.mark.kill


def _ns(**overrides):
    ns = types.SimpleNamespace(**{k: getattr(params, k) for k in dir(params) if k.isupper()})
    for k, v in overrides.items():
        setattr(ns, k, v)
    return ns


def _survivor_mask(net, ids, pre0, post0, born0):
    """Identity = same slot, still alive, same (pre, post, born) -- born changes on rebirth."""
    return (net.alive[ids] & (net.pre[ids] == pre0) & (net.post[ids] == post0)
            & (net.born[ids] == born0))


def _exc_syn(net):
    alive = np.flatnonzero(net.alive)
    return alive[net.is_exc[net.pre[alive]]]


def test_k0_12a_fresh_network_scales_unheld():
    """A fresh, never-latched network: nothing is held, and used ctx->ctx E weights move."""
    ns_w = _ns(G_WAKE=0.0)
    eng = Engine(seed=1, params=ns_w)
    net = eng.net
    ctx = net.region_slice["ctx"]

    alive0 = np.flatnonzero(net.alive)
    pre0, post0 = net.pre[alive0], net.post[alive0]
    cc_mask = (net.is_exc[pre0] & (pre0 >= ctx.start) & (pre0 < ctx.stop)
               & (post0 >= ctx.start) & (post0 < ctx.stop))
    ids_cc = alive0[cc_mask]
    assert ids_cc.size > 0
    pre_cc0, post_cc0, born_cc0 = net.pre[ids_cc].copy(), net.post[ids_cc].copy(), net.born[ids_cc].copy()
    w_cc0 = net.w[ids_cc].copy()

    eng.step(1000)

    assert not any(eng.growth_halted.values())
    assert not eng._scale_hold.any()

    surv = _survivor_mask(net, ids_cc, pre_cc0, post_cc0, born_cc0)
    assert surv.any()
    assert not np.array_equal(net.w[ids_cc[surv]], w_cc0[surv]), \
        "used ctx->ctx E weights were not scaled on a fresh, unheld network"


def test_k0_12b_latched_group_is_not_scaled_in_either_direction():
    """ctx_E/ctx_I latched synthetically; scaling must not move any ctx E weight in either
    direction, while an unlatched group (hpc_E) still scales, in the direction its error implies."""
    eng = Engine(seed=1)
    net = eng.net
    ctx = net.region_slice["ctx"]
    hpc = net.region_slice["hpc"]

    e = np.zeros(net.n, np.float32)
    e[ctx] = 0.1
    for _ in range(params.WINDUP_WINDOW_SWEEPS + 1):
        eng.structural_update(e)
    assert eng.growth_halted["ctx_E"] is True
    assert eng.growth_halted["ctx_I"] is True
    assert eng.growth_halted["hpc_E"] is False
    assert eng._scale_hold[ctx].all()
    assert not eng._scale_hold[hpc].any()

    ctx_ids = np.arange(ctx.start, ctx.stop)
    half = ctx_ids.size // 2
    net.rate[ctx_ids[:half]] = net.r_target[ctx_ids[:half]] * 2.0  # rate>target -> factor<1
    net.rate[ctx_ids[half:]] = net.r_target[ctx_ids[half:]] * 0.5  # rate<target -> factor>1
    hpc_ids = np.arange(hpc.start, hpc.stop)
    net.rate[hpc_ids] = net.r_target[hpc_ids] * 0.5  # rate<target -> factor>1, hpc never latched

    counts = np.ones(net.n, np.float32)
    exc_syn = _exc_syn(net)
    w_before = net.w.copy()

    eng._scaling_step(counts, exc_syn)

    ctx_e_syn = exc_syn[(net.post[exc_syn] >= ctx.start) & (net.post[exc_syn] < ctx.stop)]
    assert ctx_e_syn.size > 0
    assert np.array_equal(net.w[ctx_e_syn], w_before[ctx_e_syn]), \
        "latched ctx group was scaled despite the hold"

    hpc_e_syn = exc_syn[(net.post[exc_syn] >= hpc.start) & (net.post[exc_syn] < hpc.stop)]
    assert hpc_e_syn.size > 0
    assert not np.array_equal(net.w[hpc_e_syn], w_before[hpc_e_syn]), \
        "unlatched hpc_E group was not scaled (group isolation broken)"

    post_hpc = net.post[hpc_e_syn]
    below = hpc_e_syn[net.rate[post_hpc] < net.r_target[post_hpc]][:5]
    assert below.size > 0
    assert (net.w[below] >= w_before[below]).all(), \
        "weights onto below-target hpc cells decreased; factor sign is wrong"


def test_k0_12c_release_on_sign_flip_then_scaling_resumes():
    """One structural_update with a flipped sign releases ctx_E/ctx_I and clears the hold;
    the following _scaling_step then moves ctx weights again."""
    eng = Engine(seed=1)
    net = eng.net
    ctx = net.region_slice["ctx"]

    e = np.zeros(net.n, np.float32)
    e[ctx] = 0.1
    for _ in range(params.WINDUP_WINDOW_SWEEPS + 1):
        eng.structural_update(e)
    assert eng.growth_halted["ctx_E"] is True
    assert eng._scale_hold[ctx].all()

    e[ctx] = -0.1
    eng.structural_update(e)
    assert eng.growth_halted["ctx_E"] is False
    assert eng.growth_halted["ctx_I"] is False
    assert not eng._scale_hold[ctx].any()

    ctx_ids = np.arange(ctx.start, ctx.stop)
    net.rate[ctx_ids] = net.r_target[ctx_ids] * 0.5
    counts = np.ones(net.n, np.float32)
    exc_syn = _exc_syn(net)
    ctx_e_syn = exc_syn[(net.post[exc_syn] >= ctx.start) & (net.post[exc_syn] < ctx.stop)]
    assert ctx_e_syn.size > 0
    w_before = net.w[ctx_e_syn].copy()

    eng._scaling_step(counts, exc_syn)

    assert not np.array_equal(net.w[ctx_e_syn], w_before), \
        "scaling did not resume on ctx after the hold released"


def test_k0_12d_one_sweep_lag_through_the_real_sweep():
    """Through the real _slow_sweep (not a direct call): the sweep that first latches ctx_E
    still scales that sweep (one-sweep lag, since _slow_sweep scales before structural_update
    runs _update_windup); every later sweep, while the latch holds, does not move used
    sense->ctx survivor weights across the sweep tick. The hold can persist indefinitely: run
    20+ sweeps past the latch and the group never releases while its error keeps its sign, so
    scaling never resumes.

    G_WAKE = 0.0 so the only weight change possible on the sweep tick itself is scaling (STDP
    is silent), making the across-tick comparison exact.
    """
    ns_w = _ns(WINDUP_WINDOW_SWEEPS=2,
               NOISE_SIGMA_MV={"sense": 0.0, "ctx": 0.0, "hpc": 0.0}, G_WAKE=0.0)
    eng = Engine(seed=1, params=ns_w)
    eng.set_sense_spont(0)
    net = eng.net
    sense = net.region_slice["sense"]
    ctx = net.region_slice["ctx"]
    drive_ids = np.arange(sense.start, sense.start + 40)

    alive0 = np.flatnonzero(net.alive)
    pre0, post0 = net.pre[alive0], net.post[alive0]
    sc_mask = (pre0 >= sense.start) & (pre0 < sense.stop) & (post0 >= ctx.start) & (post0 < ctx.stop)
    ids_sc = alive0[sc_mask]
    assert ids_sc.size > 0

    ctx_exc_mask = net.is_exc[ctx]
    latch_sweep = None
    changed_on_latch_sweep = None
    n_sweeps = 25

    for sweep in range(1, n_sweeps + 1):
        eng.inject(drive_ids, 1.0, 1000)

        pre_b, post_b, born_b = net.pre[ids_sc].copy(), net.post[ids_sc].copy(), net.born[ids_sc].copy()
        alive_b = net.alive[ids_sc].copy()
        w_b = net.w[ids_sc].copy()

        eng.step(999)
        eng.step(1)  # exactly the sweep tick

        surv = alive_b & _survivor_mask(net, ids_sc, pre_b, post_b, born_b)
        assert surv.any()
        changed = not np.array_equal(net.w[ids_sc[surv]], w_b[surv])
        halted = eng.growth_halted["ctx_E"]

        # error must keep its (positive, below-target) sign throughout for the "never
        # releases" claim below to be meaningful.
        r = float(net.rate[ctx][ctx_exc_mask].mean())
        rt = float(net.r_target[ctx][ctx_exc_mask].mean())
        assert r < rt, f"sweep {sweep}: ctx_E rate {r} not below target {rt}; amplitude assumption broken"

        if halted and latch_sweep is None:
            latch_sweep = sweep
            changed_on_latch_sweep = changed
        elif latch_sweep is not None:
            assert halted is True, f"ctx_E released at sweep {sweep}; hold should persist while error keeps sign"
            assert not changed, f"sweep {sweep}: used sense->ctx survivors moved while ctx_E was held"

    assert latch_sweep is not None and latch_sweep > 0
    assert changed_on_latch_sweep is True, \
        "the sweep that first sets the latch should still have scaled (one-sweep lag)"
    assert eng.growth_halted["ctx_E"] is True
    assert sweep - latch_sweep >= 20, "did not run 20+ sweeps past the latch"


def test_k0_12g_release_side_lag_through_the_real_sweep():
    """Mirror of 12d for the release side: the sweep on which ctx_E's sign flips (so
    growth_halted goes True -> False) is STILL held -- _scaling_step in that sweep's
    _slow_sweep ran before structural_update evaluated the flip -- and scaling resumes only
    on the following sweep.

    Same deterministic setup as 12d (WINDUP_WINDOW_SWEEPS=2, zero noise, no sense spont,
    G_WAKE=0). ctx_E is first driven under-target (40 sense cells at 1.0 mV) so it latches
    with positive error, exactly as in 12d. After it has held for a few sweeps, the drive is
    raised (120 sense cells at 4.0 mV) until the group's EMA rate crosses above its 4 Hz
    target, flipping the sign of its mean error and releasing the latch.
    """
    ns_w = _ns(WINDUP_WINDOW_SWEEPS=2,
               NOISE_SIGMA_MV={"sense": 0.0, "ctx": 0.0, "hpc": 0.0}, G_WAKE=0.0)
    eng = Engine(seed=1, params=ns_w)
    eng.set_sense_spont(0)
    net = eng.net
    sense = net.region_slice["sense"]
    ctx = net.region_slice["ctx"]
    low_drive_ids = np.arange(sense.start, sense.start + 40)
    high_drive_ids = np.arange(sense.start, sense.start + 120)

    alive0 = np.flatnonzero(net.alive)
    pre0, post0 = net.pre[alive0], net.post[alive0]
    sc_mask = (pre0 >= sense.start) & (pre0 < sense.stop) & (post0 >= ctx.start) & (post0 < ctx.stop)
    ids_sc = alive0[sc_mask]
    assert ids_sc.size > 0

    ctx_exc_mask = net.is_exc[ctx]
    n_sweeps = 11
    boost_from_sweep = 6  # sweeps 1-5 latch it positive (as in 12d); 6+ pushes it negative
    prev_halted = False
    release_sweep = None
    changed_on_release_sweep = None
    rate_before_boost_flip = rate_at_release = None

    for sweep in range(1, n_sweeps + 1):
        if sweep < boost_from_sweep:
            eng.inject(low_drive_ids, 1.0, 1000)
        else:
            eng.inject(high_drive_ids, 4.0, 1000)

        pre_b, post_b, born_b = net.pre[ids_sc].copy(), net.post[ids_sc].copy(), net.born[ids_sc].copy()
        alive_b = net.alive[ids_sc].copy()
        w_b = net.w[ids_sc].copy()

        eng.step(999)
        eng.step(1)  # exactly the sweep tick

        surv = alive_b & _survivor_mask(net, ids_sc, pre_b, post_b, born_b)
        assert surv.any()
        changed = not np.array_equal(net.w[ids_sc[surv]], w_b[surv])
        halted = eng.growth_halted["ctx_E"]
        r = float(net.rate[ctx][ctx_exc_mask].mean())

        if prev_halted and not halted and release_sweep is None:
            release_sweep = sweep
            changed_on_release_sweep = changed
            rate_at_release = r
        elif release_sweep is not None and sweep == release_sweep + 1:
            # the sweep right after release: scaling should have resumed.
            assert not halted
            assert changed, "scaling did not resume the sweep after release"
            mean_before, mean_after = w_b[surv].mean(), net.w[ids_sc[surv]].mean()
            assert mean_after < mean_before, \
                "ctx_E is above target post-release; factor < 1 should not raise mean weight"
        elif sweep == boost_from_sweep - 1:
            rate_before_boost_flip = r

        prev_halted = halted

    rt = float(net.r_target[ctx][ctx_exc_mask].mean())
    assert rate_before_boost_flip is not None and rate_before_boost_flip < rt, \
        "ctx_E was not below target (positive error) right before the boost"
    assert release_sweep is not None, "ctx_E never released after the drive was raised"
    assert rate_at_release > rt, \
        "ctx_E was not above target (sign not actually flipped) on the release sweep"
    assert changed_on_release_sweep is False, \
        "used sense->ctx survivors moved on the release sweep itself; hold should still lag by one sweep"
    assert release_sweep < n_sweeps, "release sweep must have a following sweep to check resumed scaling"


def test_k0_12e_existing_sleep_and_used_input_clauses_unchanged():
    """While ctx is latched (synthetic): sleep freezes scaling everywhere, and with wake but
    zero counts for sense presynaptic cells, sense->ctx is untouched while used hpc input
    still scales -- the base K0.11 clauses are unaffected by the hold."""
    eng = Engine(seed=1)
    net = eng.net
    ctx = net.region_slice["ctx"]
    sense = net.region_slice["sense"]
    hpc = net.region_slice["hpc"]

    e = np.zeros(net.n, np.float32)
    e[ctx] = 0.1
    for _ in range(params.WINDUP_WINDOW_SWEEPS + 1):
        eng.structural_update(e)
    assert eng.growth_halted["ctx_E"] is True

    hpc_ids = np.arange(hpc.start, hpc.stop)
    net.rate[hpc_ids] = net.r_target[hpc_ids] * 0.5
    exc_syn = _exc_syn(net)

    eng.set_sleep(True)
    counts_all = np.ones(net.n, np.float32)
    w_before = net.w.copy()
    eng._scaling_step(counts_all, exc_syn)
    assert np.array_equal(net.w, w_before), "sleep must freeze scaling for every synapse"

    eng.set_sleep(False)
    counts = np.ones(net.n, np.float32)
    counts[sense.start:sense.stop] = 0.0  # sense presynaptic cells are silent this sweep
    sc_syn = exc_syn[(net.pre[exc_syn] >= sense.start) & (net.pre[exc_syn] < sense.stop)]
    hpc_e_syn = exc_syn[(net.post[exc_syn] >= hpc.start) & (net.post[exc_syn] < hpc.stop)]
    assert sc_syn.size > 0 and hpc_e_syn.size > 0
    w_sc0 = net.w[sc_syn].copy()
    w_hpc0 = net.w[hpc_e_syn].copy()

    eng._scaling_step(counts, exc_syn)

    assert np.array_equal(net.w[sc_syn], w_sc0), "silent presynaptic sense input was scaled"
    assert not np.array_equal(net.w[hpc_e_syn], w_hpc0), "used hpc input was not scaled"


@pytest.mark.kill
def test_k0_12f_latch_crossing_run_is_deterministic_and_frame_neutral():
    """Two default engines stepped 15,000 ticks in 50-tick chunks, one exercising telemetry
    reads after every chunk, both cross ctx_E's latch activation; end state and a state digest
    are bit-identical, and telemetry reads consume no extra RNG / state."""
    e_read = Engine(seed=1)
    e_plain = Engine(seed=1)
    n_total = 15_000
    chunk = 50

    first_halt_read = first_halt_plain = None
    ticks_done = 0
    while ticks_done < n_total:
        e_read.step(chunk)
        e_read.frame()
        e_read.stims_active()
        list(e_read.stimlog)
        e_plain.step(chunk)
        ticks_done += chunk
        if e_read.growth_halted["ctx_E"] and first_halt_read is None:
            first_halt_read = ticks_done // params.SWEEP_TICKS
        if e_plain.growth_halted["ctx_E"] and first_halt_plain is None:
            first_halt_plain = ticks_done // params.SWEEP_TICKS

    assert first_halt_read is not None and first_halt_read > 0
    assert first_halt_plain is not None and first_halt_plain > 0
    assert first_halt_read == first_halt_plain

    assert e_read.rng.bit_generator.state == e_plain.rng.bit_generator.state
    assert np.array_equal(e_read.net.v, e_plain.net.v)
    assert np.array_equal(e_read.net.w, e_plain.net.w)
    assert np.array_equal(e_read.net.alive, e_plain.net.alive)
    assert np.array_equal(e_read.net.spike_count, e_plain.net.spike_count)

    def _digest(e):
        h = hashlib.sha256()
        h.update(int(e.t).to_bytes(8, "little"))
        h.update(e.net.spike_count.tobytes())
        h.update(e.net.w.tobytes())
        h.update(e.net.alive.tobytes())
        h.update(e.net.v.tobytes())
        return h.hexdigest()

    d_read, d_plain = _digest(e_read), _digest(e_plain)
    print("K0.12f digest:", d_read)
    assert d_read == d_plain
