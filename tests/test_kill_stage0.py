"""Stage 0 kill tests K0.1, K0.2, K0.4, K0.5, K0.6 (SPEC.md section 7), seed=1 throughout."""
import time
import types

import numpy as np
import pytest

from brainsim.engine import Engine
from brainsim import params
from brainsim.params import S_MAX

pytestmark = pytest.mark.kill


def test_k0_1_event_cost_and_silent_wall_time():
    # Nominal wall time: warm up, then time 1000 ticks of background-driven activity.
    eng = Engine(seed=1)
    eng.step(2000)
    t0 = time.perf_counter()
    eng.step(1000)
    t_nominal = time.perf_counter() - t0

    eng.set_noise(0.0)
    eng.set_sense_spont(0.0)
    eng.step(500)  # let activity die out
    t0 = time.perf_counter()
    eng.step(1000)
    t_silent = time.perf_counter() - t0

    assert t_silent <= 0.25 * t_nominal

    # syn_touched per tick must witness event-driven cost, not a dense pass.
    eng2 = Engine(seed=1)
    eng2.step(2000)
    touched = []
    for _ in range(1000):
        eng2.step(1)
        touched.append(eng2.stats["syn_touched_last"])
    mean_touched = sum(touched) / len(touched)
    assert mean_touched < eng2.net.n_alive / 10


@pytest.mark.kill
def test_k0_2_stability_over_60s_wake():
    eng = Engine(seed=1)
    net = eng.net
    chunk = 50
    total_ticks = 120_000
    window_ticks = 20_000
    early_start, early_end = 40_000, 60_000

    ctx_slice = net.region_slice["ctx"]
    n_ctx = ctx_slice.stop - ctx_slice.start
    ctx_exc_mask = net.is_exc[ctx_slice]

    region_spike_sum = {name: 0 for name in net.region_names}
    max_ctx_frac = 0.0
    region_spike_sum_early = {name: 0 for name in net.region_names}
    max_ctx_frac_early = 0.0
    ctx_e_rate_early = None

    ticks_done = 0
    while ticks_done < total_ticks:
        eng.step(chunk)
        f = eng.frame()
        ticks_done += chunk

        if early_start < ticks_done <= early_end:
            for name, rd in f["regions"].items():
                region_spike_sum_early[name] += sum(rd["spikes_per_tick"])
            for c in f["regions"]["ctx"]["spikes_per_tick"]:
                frac = c / n_ctx
                if frac > max_ctx_frac_early:
                    max_ctx_frac_early = frac
        if ticks_done == early_end:
            ctx_e_rate_early = float(net.rate[ctx_slice][ctx_exc_mask].mean())

        if ticks_done > total_ticks - window_ticks:
            for name, rd in f["regions"].items():
                region_spike_sum[name] += sum(rd["spikes_per_tick"])
            for c in f["regions"]["ctx"]["spikes_per_tick"]:
                frac = c / n_ctx
                if frac > max_ctx_frac:
                    max_ctx_frac = frac

    min_region_rate_early = min(
        region_spike_sum_early[name] / (net.region_slice[name].stop - net.region_slice[name].start)
        / (window_ticks / 1000)
        for name in net.region_names
    )
    early_msg = (
        f"early(40-60s): ctxE={ctx_e_rate_early:.3f} "
        f"maxfrac={max_ctx_frac_early:.3f} minregion={min_region_rate_early:.3f}"
    )

    assert max_ctx_frac <= 0.20, early_msg

    for name in net.region_names:
        rs = net.region_slice[name]
        n_region = rs.stop - rs.start
        rate_hz = region_spike_sum[name] / n_region / (window_ticks / 1000)
        assert rate_hz >= 0.2, f"{name} rate {rate_hz} Hz under 0.2 Hz; {early_msg}"

    ctx_e_rate = float(net.rate[ctx_slice][ctx_exc_mask].mean())
    assert 1.0 <= ctx_e_rate <= 15.0, early_msg


@pytest.mark.kill
def test_k0_4_structural_turnover_over_240s():
    eng = Engine(seed=1)
    net = eng.net
    immature_init = net.n_alive

    chunk = 50
    window_ticks = 10_000
    total_ticks = 240_000
    n_windows = total_ticks // window_ticks

    window_born = [0] * n_windows
    window_died = [0] * n_windows
    alive_at = {}
    max_alive = immature_init

    ticks_done = 0
    cur_window = 0
    while ticks_done < total_ticks:
        eng.step(chunk)
        f = eng.frame()
        ticks_done += chunk
        window_born[cur_window] += f["born_count"]
        window_died[cur_window] += f["died_count"]
        max_alive = max(max_alive, f["n_syn_alive"])
        if ticks_done in (90_000, 190_000, 220_000, 240_000):
            alive_at[ticks_done] = f["n_syn_alive"]
        if ticks_done % window_ticks == 0:
            cur_window += 1

    assert (immature_init - alive_at[90_000]) / immature_init >= 0.20

    for i in range(1, n_windows):
        assert window_born[i] > 0, f"window {i} had no births"
        assert window_died[i] > 0, f"window {i} had no deaths"

    change_last30 = abs(alive_at[220_000] - alive_at[190_000]) / alive_at[190_000]
    assert change_last30 < 0.03

    sense_slice = net.region_slice["sense"]
    all_ids = np.arange(net.n)
    outside_sense = (all_ids < sense_slice.start) | (all_ids >= sense_slice.stop)
    non_sense_e_ids = np.where(net.is_exc & outside_sense)[0]
    assert net.in_degree(non_sense_e_ids, exc_only=True).min() >= 5

    assert max_alive < 0.9 * S_MAX


@pytest.mark.kill
def test_k0_5_frames_match_engine_counters_over_10s():
    eng = Engine(seed=1)
    net = eng.net

    spike_total_before = eng.stats["spike_total"]
    syn_born_before = eng.stats["syn_born_total"]
    syn_died_before = eng.stats["syn_died_total"]

    sum_spikes_len = 0
    sum_born_count = 0
    sum_died_count = 0
    any_truncated = False

    ticks_done = 0
    while ticks_done < 10_000:
        eng.step(50)
        f = eng.frame()
        ticks_done += 50

        assert f["n_syn_alive"] == net.alive.sum()
        assert len(f["born"]) <= f["born_count"]
        assert len(f["died"]) <= f["died_count"]

        sum_spikes_len += len(f["spikes"])
        sum_born_count += f["born_count"]
        sum_died_count += f["died_count"]
        any_truncated = any_truncated or f["truncated"]

    spike_total_after = eng.stats["spike_total"]
    syn_born_after = eng.stats["syn_born_total"]
    syn_died_after = eng.stats["syn_died_total"]

    if not any_truncated:
        assert sum_spikes_len == spike_total_after - spike_total_before
    assert sum_born_count == syn_born_after - syn_born_before
    assert sum_died_count == syn_died_after - syn_died_before


@pytest.mark.kill
def test_k0_6_sleep_gates_sense_and_keeps_ctx_active():
    eng = Engine(seed=1)
    net = eng.net
    sense_slice = net.region_slice["sense"]
    ctx_slice = net.region_slice["ctx"]
    n_sense = sense_slice.stop - sense_slice.start
    n_ctx = ctx_slice.stop - ctx_slice.start

    eng.set_sleep(True)
    eng.present(0, 5000)
    sense_spikes = 0
    ctx_spikes = 0
    ticks_done = 0
    while ticks_done < 5000:
        eng.step(50)
        f = eng.frame()
        ticks_done += 50
        assert f["g"] == 0.3
        assert f["phase"] == "sleep"
        sense_spikes += sum(f["regions"]["sense"]["spikes_per_tick"])
        ctx_spikes += sum(f["regions"]["ctx"]["spikes_per_tick"])

    sense_rate = sense_spikes / n_sense / (5000 / 1000)
    ctx_rate = ctx_spikes / n_ctx / (5000 / 1000)
    assert sense_rate < 0.1
    assert ctx_rate > 0.2

    eng.set_sleep(False)
    eng.present(0, 2000)
    sense_spikes2 = 0
    ticks_done = 0
    while ticks_done < 2000:
        eng.step(50)
        f = eng.frame()
        ticks_done += 50
        sense_spikes2 += sum(f["regions"]["sense"]["spikes_per_tick"])

    sense_rate2 = sense_spikes2 / n_sense / (2000 / 1000)
    assert sense_rate2 > 2.0


@pytest.mark.kill
def test_k0_11_scaling_skips_silent_presynaptic_input():
    # Wake: silent sense presynaptic input must not be scaled, while active
    # ctx->ctx E input onto the same cells is scaled. G_WAKE = 0 silences STDP,
    # so the ctx->ctx movement below can only be scaling.
    ns_w = types.SimpleNamespace(**{k: getattr(params, k) for k in dir(params) if k.isupper()})
    ns_w.G_WAKE = 0.0
    eng = Engine(seed=1, params=ns_w)
    eng.set_sense_spont(0)
    net = eng.net
    sense = net.region_slice["sense"]
    ctx = net.region_slice["ctx"]

    alive = np.flatnonzero(net.alive)
    pre, post = net.pre, net.post
    ids_sc = alive[(pre[alive] >= sense.start) & (pre[alive] < sense.stop) &
                   (post[alive] >= ctx.start) & (post[alive] < ctx.stop)]
    ids_cc = alive[(pre[alive] >= ctx.start) & (pre[alive] < ctx.stop) &
                   net.is_exc[pre[alive]] &
                   (post[alive] >= ctx.start) & (post[alive] < ctx.stop)]
    assert ids_sc.size > 0 and ids_cc.size > 0
    w_sc0 = net.w[ids_sc].copy()
    w_cc0 = net.w[ids_cc].copy()
    pp_sc0 = (pre[ids_sc].copy(), post[ids_sc].copy())
    pp_cc0 = (pre[ids_cc].copy(), post[ids_cc].copy())

    eng.step(1000)  # exactly one slow sweep at t = 1000
    assert eng.phase == "wake" and eng.g == 0.0

    # A killed slot can be reborn as a different synapse in the same sweep, so
    # "survived" means alive with the same (pre, post), not just alive.
    m_sc = net.alive[ids_sc] & (pre[ids_sc] == pp_sc0[0]) & (post[ids_sc] == pp_sc0[1])
    m_cc = net.alive[ids_cc] & (pre[ids_cc] == pp_cc0[0]) & (post[ids_cc] == pp_cc0[1])
    assert m_sc.any() and m_cc.any()
    assert np.array_equal(net.w[ids_sc[m_sc]], w_sc0[m_sc]), \
        "silent-presynaptic sense->ctx weights were scaled"
    assert not np.array_equal(net.w[ids_cc[m_cc]], w_cc0[m_cc]), \
        "used ctx->ctx input was not scaled in wake"

    # Sleep: with G_SLEEP = 0, STDP is silent and scaling must be frozen for
    # every alive E synapse onto ctx (any presynaptic region), across two
    # further sweeps inside the sleep regime.
    ns = types.SimpleNamespace(**{k: getattr(params, k) for k in dir(params) if k.isupper()})
    ns.G_SLEEP = 0.0
    eng2 = Engine(seed=1, params=ns)
    net2 = eng2.net
    eng2.set_sleep(True)
    eng2.step(1000)  # one sweep: settle into the sleep regime

    alive2 = np.flatnonzero(net2.alive)
    pre2, post2 = net2.pre, net2.post
    ids_e_ctx2 = alive2[net2.is_exc[pre2[alive2]] &
                         (post2[alive2] >= ctx.start) & (post2[alive2] < ctx.stop)]
    assert ids_e_ctx2.size > 0
    w_e_ctx2_0 = net2.w[ids_e_ctx2].copy()
    pp2_0 = (pre2[ids_e_ctx2].copy(), post2[ids_e_ctx2].copy())

    eng2.step(2000)  # two more slow sweeps, still inside sleep

    m_e_ctx2 = (net2.alive[ids_e_ctx2] & (pre2[ids_e_ctx2] == pp2_0[0])
                & (post2[ids_e_ctx2] == pp2_0[1]))
    assert m_e_ctx2.any()
    assert np.array_equal(net2.w[ids_e_ctx2[m_e_ctx2]], w_e_ctx2_0[m_e_ctx2]), \
        "alive E->ctx weights were scaled during sleep with G_SLEEP = 0"
    assert eng2.phase == "sleep"
    assert eng2.g == 0.0


@pytest.mark.kill
def test_k0_10b_store_clamp_prevents_overflow_without_abort():
    """K0.10(b): with WINDUP_CAP_FRAC * S_MAX below the immature wiring count, the store
    clamp halts all growth instead of aborting with 'synapse store full'."""
    from brainsim import params

    ns = types.SimpleNamespace(**{k: getattr(params, k) for k in dir(params) if k.isupper()})
    ns.S_MAX = 380_000

    eng = Engine(seed=1, params=ns)

    any_clamped = False
    for _ in range(30):
        eng.step(1000)
        f = eng.frame()
        if f["store_clamped"]:
            any_clamped = True
            assert f["born_count"] == 0
        assert f["n_syn_alive"] <= ns.S_MAX

    assert eng.stats["store_clamp_sweeps"] > 0
    assert any_clamped
