"""K0.3 (STDP) at unit level, plus structural primitives on Network."""
import numpy as np
import pytest

from brainsim.net import Network
from brainsim.engine import Engine

REP_TICKS = 1000  # 1 s at dt = 1 ms
GAP_TICKS = 10


def _run_pairing(pre_first: bool) -> tuple[float, float, np.ndarray]:
    net = Network.tiny(2, [True, True], [(0, 1, 1.0, 1)])
    eng = Engine(seed=1, net=net, noise_sigma=0.0)
    w0 = float(net.w[0])
    for _ in range(60):
        if pre_first:
            eng.inject(np.array([0]), 30.0, 1)
            eng.step(1)
            eng.step(GAP_TICKS - 1)
            eng.inject(np.array([1]), 30.0, 1)
            eng.step(1)
        else:
            eng.inject(np.array([1]), 30.0, 1)
            eng.step(1)
            eng.step(GAP_TICKS - 1)
            eng.inject(np.array([0]), 30.0, 1)
            eng.step(1)
        eng.step(REP_TICKS - (GAP_TICKS + 1))
    w_final = float(net.w[0])
    return w0, w_final, eng.spike_counts()


def test_stdp_pre_before_post_potentiates():
    w0, w_final, counts = _run_pairing(pre_first=True)
    assert w_final > w0
    assert counts[0] > 0
    assert counts[1] > 0


def test_stdp_post_before_pre_depresses():
    w0, w_final, counts = _run_pairing(pre_first=False)
    assert w_final < w0
    assert counts[0] > 0
    assert counts[1] > 0


def test_add_synapses_returns_ids_and_raises_synapse_count():
    net = Network.tiny(3, [True, True, True], [])
    before = net.n_alive
    ids = net.add_synapses(np.array([0]), np.array([1]), np.array([1.0]),
                            np.array([1], dtype=np.uint8), t=0)
    ids = np.asarray(ids)
    assert ids.dtype.kind in "iu"
    assert net.n_alive == before + len(ids)


def test_add_synapses_raises_past_s_max():
    net = Network.tiny(3, [True, True, True], [])
    smax = net.s_max
    for _ in range(smax):
        net.add_synapses(np.array([0]), np.array([1]), np.array([1.0]),
                          np.array([1], dtype=np.uint8), t=0)
    assert net.n_alive == smax
    with pytest.raises(Exception):
        net.add_synapses(np.array([0]), np.array([1]), np.array([1.0]),
                          np.array([1], dtype=np.uint8), t=0)


def _find_id(net: Network, pre: int, post: int) -> int:
    ids = np.where((net.pre == pre) & (net.post == post) & net.alive)[0]
    assert len(ids) == 1
    return int(ids[0])


def test_kill_synapses_lowers_n_alive_and_zeroes_weight():
    net = Network.tiny(4, [True, True, True, True],
                        [(0, 2, 1.0, 1), (1, 2, 1.0, 1), (0, 3, 1.0, 1)])
    before = net.n_alive
    id02 = _find_id(net, 0, 2)
    net.kill_synapses(np.array([id02]))
    assert net.n_alive == before - 1
    assert net.alive[id02] == False  # noqa: E712
    assert float(net.w[id02]) == 0.0


def test_in_degree_counts_only_alive_incoming():
    net = Network.tiny(4, [True, True, True, True],
                        [(0, 2, 1.0, 1), (1, 2, 1.0, 1), (0, 3, 1.0, 1)])
    assert net.in_degree(np.array([2]))[0] == 2
    id02 = _find_id(net, 0, 2)
    net.kill_synapses(np.array([id02]))
    assert net.in_degree(np.array([2]))[0] == 1


def test_rebuild_index_runs():
    net = Network.tiny(4, [True, True, True, True],
                        [(0, 2, 1.0, 1), (1, 2, 1.0, 1), (0, 3, 1.0, 1)])
    net.rebuild_index(0)  # must not raise
    assert net.n_alive == 3


_K03_CACHE = {}


def _k03_result():
    """Run the K0.3 weak-current pairing record experiment once per session and cache it."""
    if "result" not in _K03_CACHE:
        from tests import k03_pairing as k03
        _K03_CACHE["module"] = k03
        _K03_CACHE["result"] = k03.run_experiment()
    return _K03_CACHE["module"], _K03_CACHE["result"]


@pytest.mark.record
def test_k0_3_population_imposed_pairing():
    """Retired as a Stage 0 kill test on 2026-09-12 (owner decision): the population
    contrast clause is not a Stage 0 requirement. The two-neuron tests above are the Stage 0
    claim about the pair rule. Kept, unchanged in protocol and threshold (1.2), as the record
    of the weak-current pairing result (ratio 0.861 at deedcc8); deselected unless pytest is
    given --record.

    K0.3 population test: does a weak sustained postsynaptic current, injected into
    ctx_a for the whole presentation window at the same tick pattern-A is presented,
    potentiate pattern-A pathways onto a fixed ctx target set more than non-A pathways?
    Postsynaptic current injection is an experimental intervention, not autonomous
    sensory learning: the current is not driven by presynaptic spikes, it is a fixed
    weak bias timed to overlap the A presentation window."""
    k03, result = _k03_result()

    # 1. Protocol pins: the module constants must equal the contract's values so the
    # schedule cannot silently drift.
    assert k03.SEED == 1
    assert k03.WARMUP_TICKS == 120_000
    assert k03.TRIALS == 20
    assert k03.ON_TICKS == 300
    assert k03.OFF_TICKS == 700
    assert k03.PULSE_OFFSETS == (0,)
    assert k03.WEAK_AMP_MV == 0.2
    assert k03.PULSE_AMP_MV == 0.2
    assert k03.PULSE_TICKS == 300
    assert k03.LAG_WINDOW == 50

    pairing = result["pairing"]
    control = result["control"]

    # 2. Preconditions.
    assert result["ctx_a"] is not None and len(result["ctx_a"]) > 0, (
        f"n_ctx_a={len(result['ctx_a'])}"
    )
    assert pairing["n_ctx_a"] > 0, f"n_ctx_a={pairing['n_ctx_a']}"
    assert pairing["groups"]["A"]["n_baseline"] > 0, (
        f"A n_baseline={pairing['groups']['A']['n_baseline']}"
    )
    assert pairing["groups"]["nonA"]["n_baseline"] > 0, (
        f"nonA n_baseline={pairing['groups']['nonA']['n_baseline']}"
    )
    assert pairing["t_start"] == 120_000, f"t_start={pairing['t_start']}"
    assert pairing["phase_start"] == "wake", f"phase_start={pairing['phase_start']}"
    assert pairing["t_end"] == 140_000, f"t_end={pairing['t_end']}"
    assert pairing["phases_seen"] == ["wake"], f"phases_seen={pairing['phases_seen']}"

    # 2b. Architecture-review addition: control arm ran the same current schedule,
    # with no presentation.
    assert control["pattern_presented"] is None, (
        f"control pattern_presented={control['pattern_presented']}"
    )
    assert control["pulse_ticks_total"] == 6000, (
        f"control pulse_ticks_total={control['pulse_ticks_total']}"
    )
    assert control["t_end"] == 140_000, f"control t_end={control['t_end']}"
    assert control["phases_seen"] == ["wake"], (
        f"control phases_seen={control['phases_seen']}"
    )

    # 2c. Addendum F: final-group sanity, both arms and both groups.
    for arm_name, arm in (("pairing", pairing), ("control", control)):
        for g in ("A", "nonA"):
            grp = arm["groups"][g]
            assert grp["n_final_alive"] > 0, (
                f"{arm_name} group {g}: n_final_alive={grp['n_final_alive']}"
            )
            assert grp["n_survivors"] > 0, (
                f"{arm_name} group {g}: n_survivors={grp['n_survivors']}"
            )
        assert arm["groups"]["nonA"]["mean_w_final"] > 0, (
            f"{arm_name} nonA mean_w_final={arm['groups']['nonA']['mean_w_final']} "
            f"(primary ratio's denominator must be nonzero)"
        )

    # 3. Instrument self-checks, both arms.
    for arm_name, arm in (("pairing", pairing), ("control", control)):
        assert arm["instrument_max_residual_nonsweep"] < 1e-5, (
            f"{arm_name}: instrument_max_residual_nonsweep="
            f"{arm['instrument_max_residual_nonsweep']}"
        )
        for g in ("A", "nonA"):
            resid = arm["groups"][g]["closure_residual"]
            assert abs(resid) < 1e-5, f"{arm_name} group {g}: closure_residual={resid}"
        assert arm["scaling_pred_vs_resid_max_abs"] < 1e-5, (
            f"{arm_name}: scaling_pred_vs_resid_max_abs="
            f"{arm['scaling_pred_vs_resid_max_abs']}"
        )
        for g in ("A", "nonA"):
            grp = arm["groups"][g]
            diff = abs(grp["scaling_pred_mean"] - grp["scaling_mean"])
            assert diff < 1e-5, (
                f"{arm_name} group {g}: scaling_pred_mean={grp['scaling_pred_mean']} "
                f"scaling_mean={grp['scaling_mean']} diff={diff}"
            )
        assert arm["pair_count_crosscheck_ok"] is True, (
            f"{arm_name}: pair_count_crosscheck_ok={arm['pair_count_crosscheck_ok']}"
        )

    # 4. Intervention happened.
    assert pairing["pulse_ticks_total"] == 6000, (
        f"pulse_ticks_total={pairing['pulse_ticks_total']}"
    )
    assert pairing["pulse_spike_frac_mean"] > 0, (
        f"pulse_spike_frac_mean={pairing['pulse_spike_frac_mean']}"
    )

    gA = pairing["groups"]["A"]
    gN = pairing["groups"]["nonA"]

    # The weight outcome and pair counts, included in every failure message below so an
    # invalid run still records what the weights did (the run takes minutes).
    outcome_report = (
        f"mean_w_final A={gA['mean_w_final']} nonA={gN['mean_w_final']} "
        f"(need A >= 1.2 * nonA); "
        f"ratio_baseline={pairing['ratio_baseline']} ratio_final={pairing['ratio_final']}; "
        f"A: mean_w_baseline={gA['mean_w_baseline']} mean_w_final={gA['mean_w_final']} "
        f"mean_w_over_wmax_baseline={gA['mean_w_over_wmax_baseline']} "
        f"mean_w_over_wmax_final={gA['mean_w_over_wmax_final']} "
        f"frac_ceiling_baseline={gA['frac_ceiling_baseline']} "
        f"frac_ceiling_final={gA['frac_ceiling_final']} "
        f"ltp_mean={gA['ltp_mean']} ltd_mean={gA['ltd_mean']} scaling_mean={gA['scaling_mean']} "
        f"causal_pairs={gA['causal_pairs']} anticausal_pairs={gA['anticausal_pairs']} "
        f"causal_trace_sum={gA['causal_trace_sum']} "
        f"anticausal_trace_sum={gA['anticausal_trace_sum']} "
        f"pulse_causal_pairs={gA['pulse_causal_pairs']} "
        f"pulse_anticausal_pairs={gA['pulse_anticausal_pairs']} "
        f"pulse_causal_lag_median={gA['pulse_causal_lag_median']} "
        f"pulse_lag_peak={gA['pulse_lag_peak']}; "
        f"nonA: mean_w_baseline={gN['mean_w_baseline']} mean_w_final={gN['mean_w_final']} "
        f"mean_w_over_wmax_baseline={gN['mean_w_over_wmax_baseline']} "
        f"mean_w_over_wmax_final={gN['mean_w_over_wmax_final']} "
        f"frac_ceiling_baseline={gN['frac_ceiling_baseline']} "
        f"frac_ceiling_final={gN['frac_ceiling_final']} "
        f"ltp_mean={gN['ltp_mean']} ltd_mean={gN['ltd_mean']} scaling_mean={gN['scaling_mean']} "
        f"causal_pairs={gN['causal_pairs']} anticausal_pairs={gN['anticausal_pairs']} "
        f"causal_trace_sum={gN['causal_trace_sum']} "
        f"anticausal_trace_sum={gN['anticausal_trace_sum']} "
        f"pulse_causal_pairs={gN['pulse_causal_pairs']} "
        f"pulse_anticausal_pairs={gN['pulse_anticausal_pairs']} "
        f"pulse_causal_lag_median={gN['pulse_causal_lag_median']} "
        f"pulse_lag_peak={gN['pulse_lag_peak']}; "
        f"control: ratio_final={control['ratio_final']} "
        f"A causal_pairs={control['groups']['A']['causal_pairs']} "
        f"A anticausal_pairs={control['groups']['A']['anticausal_pairs']}"
    )

    # 4b. Predeclared validity preconditions: unless these hold, the experiment did
    # not actually deliver a paired A-volley + postsynaptic-current protocol, and the
    # endpoint below would not be evidence of anything.
    assert pairing["a_volley_frac_mean"] >= 0.7, (
        f"INVALID experiment: pairing a_volley_frac_mean="
        f"{pairing['a_volley_frac_mean']} (< 0.7 -- pattern A did not reliably drive "
        f"its sense cells during the presentation window)"
        + " | " + outcome_report
    )
    assert gA["pulse_causal_pairs"] > gA["pulse_anticausal_pairs"], (
        f"INVALID experiment: pairing group A pulse_causal_pairs="
        f"{gA['pulse_causal_pairs']} <= pulse_anticausal_pairs="
        f"{gA['pulse_anticausal_pairs']} (no causal pre-before-post pairing signal "
        f"in the current-active window)"
        + " | " + outcome_report
    )
    assert 1 <= gA["pulse_lag_peak"] <= 10, (
        f"INVALID experiment: pairing group A pulse_lag_peak={gA['pulse_lag_peak']} "
        f"not in [1, 10] (the dominant pre-before-post lag is not where a causal "
        f"A -> ctx_A pathway should place it)"
        + " | " + outcome_report
    )
    assert pairing["ctx_a_window_frac_mean"] >= 0.5, (
        f"INVALID experiment: pairing ctx_a_window_frac_mean="
        f"{pairing['ctx_a_window_frac_mean']} (< 0.5 -- the injected current did not "
        f"reliably drive ctx_a spikes during the presentation window)"
        + " | " + outcome_report
    )
    for arm_name, arm in (("pairing", pairing), ("control", control)):
        assert arm["ctx_burst_max_frac"] <= 0.20, (
            f"INVALID experiment: {arm_name} ctx_burst_max_frac="
            f"{arm['ctx_burst_max_frac']} (> 0.20 -- a runaway synchronous ctx burst, "
            f"not a graded pairing signal)"
            + " | " + outcome_report
        )

    # 5. Primary (kill criterion): pattern-A pathways onto ctx_a potentiate more than
    # non-A pathways under imposed pairing. Unchanged threshold, raw (not
    # baseline-normalised) mean_w_final.
    assert gA["n_final_alive"] > 0 and gN["n_final_alive"] > 0, (
        f"non-vacuity: n_final_alive A={gA['n_final_alive']} nonA={gN['n_final_alive']}"
    )
    assert gN["mean_w_final"] > 0, (
        f"non-vacuity: nonA mean_w_final={gN['mean_w_final']} "
        f"(kill criterion denominator must be nonzero, not 0.0 >= 0.0)"
    )
    assert gA["mean_w_final"] >= 1.2 * gN["mean_w_final"], (
        "K0.3 weak-current pairing selectivity failed: " + outcome_report
    )


def test_k0_7_isolated_neuron_rate_below_target():
    """K0.7: an isolated neuron driven only by noise/spont input stays well below r_target."""
    from brainsim import params

    for name in ("ctx", "hpc"):
        net = Network.tiny(1, [True], [])
        eng = Engine(seed=1, net=net, noise_sigma=params.NOISE_SIGMA_MV[name])
        eng.step(30_000)
        rate_hz = eng.spike_counts()[0] / 30
        target = params.REGIONS[name]["r_target_exc"]
        assert rate_hz <= 0.3 * target, (
            f"{name}: isolated-neuron rate {rate_hz:.3f} Hz exceeds 30% of "
            f"r_target_exc={target} Hz"
        )


def test_k0_8_conduction_delay():
    """K0.8: a freshly born synapse conducts only after CONDUCT_DELAY_TICKS, not before."""
    from brainsim import params

    net = Network.tiny(2, [True, True], [])
    eng = Engine(seed=1, net=net, noise_sigma=0.0)

    (syn_id,) = net.add_synapses(
        np.array([0], np.int32),
        np.array([1], np.int32),
        np.array([30.0], np.float32),
        np.array([1], np.uint8),
        t=0,
    )
    assert net.conduct[syn_id] == 0 + params.CONDUCT_DELAY_TICKS

    eng.step(500 - eng.t)
    eng.inject(np.array([0]), 30.0, 1)
    eng.step(20)
    counts_before = eng.spike_counts().copy()
    assert counts_before[1] == 0

    eng.step(1500 - eng.t)
    eng.inject(np.array([0]), 30.0, 1)
    eng.step(20)
    counts_after = eng.spike_counts()

    assert counts_after[1] == counts_before[1] + 1
    assert counts_after[0] == 2


def _kEI(net, ids):
    kE = net.in_degree(ids, exc_only=True)
    kI = net.in_degree(ids, exc_only=False) - kE
    return kE, kI


def test_k0_9_two_sign_controller_grows_e_and_respects_motif():
    """(a) e=+1: E sum grows; per-neuron I never drops below min(before, motif)."""
    from brainsim import params

    eng = Engine(seed=1)
    net = eng.net
    ctx = net.region_slice["ctx"]
    ids = np.arange(ctx.start, ctx.stop)

    kE_before, kI_before = _kEI(net, ids)
    motif = np.floor(params.EI_MOTIF * kE_before).astype(int)

    e = np.zeros(net.n, np.float32)
    e[ctx] = 1.0
    born, died = eng.structural_update(e)
    born = np.asarray(born)

    kE_after, kI_after = _kEI(net, ids)
    assert kE_after.sum() > kE_before.sum()
    assert (kI_after >= np.minimum(kI_before, motif)).all()

    assert net.alive[born].all()
    assert (net.conduct[born] > eng.t).all()


def test_k0_9_two_sign_controller_shrinks_e_grows_i():
    """(b) e=-1: E sum shrinks, I sum grows; new I synapses are local (pre in ctx, inhibitory)."""
    eng = Engine(seed=1)
    net = eng.net
    ctx = net.region_slice["ctx"]
    ids = np.arange(ctx.start, ctx.stop)

    kE_before, kI_before = _kEI(net, ids)

    e = np.zeros(net.n, np.float32)
    e[ctx] = -1.0
    born, died = eng.structural_update(e)
    born, died = np.asarray(born), np.asarray(died)

    kE_after, kI_after = _kEI(net, ids)
    assert kE_after.sum() < kE_before.sum()
    assert kI_after.sum() > kI_before.sum()

    pre_born = net.pre[born]
    assert (~net.is_exc[pre_born]).all()
    assert ((pre_born >= ctx.start) & (pre_born < ctx.stop)).all()
    assert (~net.alive[died]).all()


def test_k0_9_two_sign_controller_restores_i_deficit():
    """(c) after killing all I onto ctx, e=+1 still raises ctx I in-degree from 0, plus E."""
    eng = Engine(seed=1)
    net = eng.net
    ctx = net.region_slice["ctx"]
    ids = np.arange(ctx.start, ctx.stop)

    ids_kill = np.flatnonzero(
        net.alive & ~net.is_exc[net.pre] & (net.post >= ctx.start) & (net.post < ctx.stop)
    )
    net.kill_synapses(ids_kill)
    net.rebuild_index(eng.t)

    kE_before, kI_before = _kEI(net, ids)
    assert kI_before.sum() == 0

    e = np.zeros(net.n, np.float32)
    e[ctx] = 1.0
    eng.structural_update(e)

    kE_after, kI_after = _kEI(net, ids)
    assert kI_after.sum() > 0
    assert kE_after.sum() > kE_before.sum()


def test_k0_9_two_sign_controller_trims_excess_i():
    """(d) with I beyond the motif, e=+1 shrinks I sum but never below each neuron's motif."""
    from brainsim import params

    eng = Engine(seed=1)
    net = eng.net
    ctx = net.region_slice["ctx"]
    ids = np.arange(ctx.start, ctx.stop)

    inh_ctx = np.where(~net.is_exc[ctx.start:ctx.stop])[0] + ctx.start
    rng = np.random.default_rng(1)
    targets = ids[:200]
    pre = rng.choice(inh_ctx, size=200 * 20)
    post = np.repeat(targets, 20)
    w = np.full(pre.size, -1.0, np.float32)
    delay = np.ones(pre.size, np.uint8)
    net.add_synapses(pre, post, w, delay, t=eng.t)
    net.rebuild_index(eng.t)

    kE_before, kI_before = _kEI(net, ids)
    motif = np.floor(params.EI_MOTIF * kE_before).astype(int)

    e = np.zeros(net.n, np.float32)
    e[ctx] = 1.0
    eng.structural_update(e)

    kE_after, kI_after = _kEI(net, ids)
    target_mask = np.isin(ids, targets)
    assert kI_after[target_mask].sum() < kI_before[target_mask].sum()
    assert (kI_after >= np.minimum(kI_before, motif)).all()


def _ei_births_onto_ctx(net, born, ctx):
    """Split synapse ids born onto ctx by whether their source is excitatory or inhibitory."""
    born = np.asarray(born)
    if len(born) == 0:
        return 0, 0
    post = net.post[born]
    onto_ctx = (post >= ctx.start) & (post < ctx.stop)
    pre_onto_ctx = net.pre[born[onto_ctx]]
    is_e = net.is_exc[pre_onto_ctx]
    return int(is_e.sum()), int((~is_e).sum())


def test_k0_10a_stall_latch_holds_growth_and_releases_on_sign_flip():
    """K0.10(a): anti-windup stall latch on ctx_E/ctx_I, release on sign flip and re-grow."""
    from brainsim import params

    eng = Engine(seed=1)
    net = eng.net
    ctx = net.region_slice["ctx"]

    e = np.zeros(net.n, np.float32)
    e[ctx] = 0.1

    for _ in range(params.WINDUP_WINDOW_SWEEPS):
        born, died = eng.structural_update(e)
        n_e, n_i = _ei_births_onto_ctx(net, born, ctx)
        assert n_e > 0
        assert eng.growth_halted["ctx_E"] is False

    born, died = eng.structural_update(e)
    n_e, n_i = _ei_births_onto_ctx(net, born, ctx)
    assert eng.growth_halted["ctx_E"] is True
    assert eng.growth_halted["ctx_I"] is True
    assert n_e == 0
    assert n_i > 0  # deficit restoration is never held
    assert eng.stats["stall_halt_sweeps"] >= 2

    e[ctx] = -0.1
    eng.structural_update(e)
    assert eng.growth_halted["ctx_E"] is False
    assert eng.growth_halted["ctx_I"] is False

    e[ctx] = 0.1
    born, died = eng.structural_update(e)
    n_e, n_i = _ei_births_onto_ctx(net, born, ctx)
    assert n_e > 0

    assert set(eng.growth_halted) == {"sense_E", "ctx_E", "ctx_I", "hpc_E", "hpc_I"}
    assert eng.growth_halted["hpc_E"] is False
    assert eng.growth_halted["hpc_I"] is False


def _e_deaths_onto_ctx(net, died, ctx):
    """Count synapse ids among died whose post is in ctx and whose pre is excitatory."""
    died = np.asarray(died)
    if len(died) == 0:
        return 0
    post = net.post[died]
    onto_ctx = (post >= ctx.start) & (post < ctx.stop)
    pre_onto_ctx = net.pre[died[onto_ctx]]
    return int(net.is_exc[pre_onto_ctx].sum())


def test_k0_10d_latch_holds_error_driven_pruning():
    """K0.10(d): the stall latch holds error-driven pruning too, not just growth."""
    from brainsim import params

    eng = Engine(seed=1)
    net = eng.net
    ctx = net.region_slice["ctx"]

    e = np.zeros(net.n, np.float32)
    e[ctx] = -0.1

    W = params.WINDUP_WINDOW_SWEEPS

    for _ in range(W):
        born, died = eng.structural_update(e)
        n_e_died = _e_deaths_onto_ctx(net, died, ctx)
        assert n_e_died > 0
        assert eng.growth_halted["ctx_E"] is False

    born, died = eng.structural_update(e)
    n_e_died = _e_deaths_onto_ctx(net, died, ctx)
    assert eng.growth_halted["ctx_E"] is True
    assert n_e_died == 0


_K013_CACHE = {}


def _k013_result():
    """Run the K0.13 autonomous-onset-learning experiment once per session and cache it.

    tests/k013_onset.py does a bare ``import k03_pairing`` (it is designed to also run
    as a standalone script from inside tests/), so tests/ must be on sys.path before it
    is imported as a package submodule.
    """
    if "result" not in _K013_CACHE:
        import os
        import sys
        tests_dir = os.path.dirname(os.path.abspath(__file__))
        if tests_dir not in sys.path:
            sys.path.insert(0, tests_dir)
        from tests import k013_onset as k013
        _K013_CACHE["module"] = k013
        _K013_CACHE["result"] = k013.run_experiment()
    return _K013_CACHE["module"], _K013_CACHE["result"]


def test_k0_13_autonomous_onset_learning():
    """K0.13: does the network, run completely unchanged (no postsynaptic injection,
    every stimulus an ordinary sense-only Engine.present), autonomously learn pathway
    selectivity of pattern-A sense inputs onto ctx_A from repeated brief onsets alone?

    This is a red kill-style test, like K0.3's population test: it is expected to FAIL
    today (weight-endpoint ratio ~0.922 vs the 1.2 threshold; evoked_A after_A ~0.43 vs
    after_none ~0.86 -- training is currently *suppressing* the natural response, not
    building it). A pass would demonstrate autonomous selectivity under brief onsets on
    this engine and this schedule alone -- it says nothing about retention (no
    retention run is in scope), nor about any other schedule, seed or mechanism.
    """
    k013, result = _k013_result()

    # 1. Protocol pins -- the module constants must equal the frozen contract values.
    assert k013.SEED == 1
    assert k013.TRIALS == 60
    assert k013.ON_TICKS == 40
    assert k013.TRIAL_TICKS == 300
    assert k013.PROBE_N == 5
    assert k013.PROBE_LEAD == 20
    assert k013.PROBE_PERIOD == 300
    assert k013.RESP_WIN == (25, 45)
    assert k013.BASE_WIN == (-20, 0)
    assert k013.VOLLEY_MIN_FRAC == 0.7
    assert k013.F1_MIN == 0.15
    assert k013.SEL_MIN_SUM == 0.05
    assert k013.NATURAL_MIN == 0.05
    assert k013.RATIO_THRESHOLD == 1.2
    assert k013.RATIO_GAP == 0.1
    assert k013.PATTERN_A == 0
    assert k013.PATTERN_B == 1

    validity = result["validity"]
    inject_log = result["inject_log"]

    # 2. Preconditions: an invalid run cannot be read as a task result either way.
    for key, ok in validity.items():
        assert ok is True, f"INVALID experiment: validity[{key!r}] is not True ({ok})"

    n_non_sense = sum(1 for e in inject_log if not e[4])
    assert n_non_sense == 0, (
        f"INVALID experiment: {n_non_sense} inject call(s) targeted non-sense cells"
    )
    assert len(inject_log) == result["expected_inject_calls"], (
        f"INVALID experiment: inject call count {len(inject_log)} != "
        f"expected {result['expected_inject_calls']}"
    )

    for name, arm in result["arms"].items():
        assert arm["instrument_max_residual_nonsweep"] == 0, (
            f"INVALID experiment: arm_{name} instrument_max_residual_nonsweep="
            f"{arm['instrument_max_residual_nonsweep']}"
        )
        assert arm["scaling_pred_vs_resid_max_abs"] == 0, (
            f"INVALID experiment: arm_{name} scaling_pred_vs_resid_max_abs="
            f"{arm['scaling_pred_vs_resid_max_abs']}"
        )
        assert arm["pair_count_crosscheck_ok"] is True, (
            f"INVALID experiment: arm_{name} pair_count_crosscheck_ok="
            f"{arm['pair_count_crosscheck_ok']}"
        )

    # 3. Performance precondition: the natural (pre-training) response must exist for
    # the selectivity question to even be meaningful.
    evA_before = result["probe_table"]["before"]["ctx_A"]["evoked_A"]
    assert evA_before >= k013.NATURAL_MIN, (
        f"weak natural response (task failure, not invalidity): "
        f"evoked_A(before, ctx_A)={evA_before} < NATURAL_MIN={k013.NATURAL_MIN}"
    )

    # 4. The task result itself -- both criteria are EXPECTED TO FAIL today.
    ratio_a = result["arms"]["A"]["ratio_final"]
    ratio_b = result["arms"]["B"]["ratio_final"]
    ratio_n = result["arms"]["none"]["ratio_final"]
    evA_after_A = result["probe_table"]["after_A"]["ctx_A"]["evoked_A"]
    evA_after_B = result["probe_table"]["after_B"]["ctx_A"]["evoked_A"]
    evA_after_none = result["probe_table"]["after_none"]["ctx_A"]["evoked_A"]

    assert result["weight_pass"] is True, (
        f"weight endpoint fails: ratio_final A={ratio_a} B={ratio_b} none={ratio_n} "
        f"(need A>={k013.RATIO_THRESHOLD}, A-B>={k013.RATIO_GAP}, A-none>={k013.RATIO_GAP})"
    )
    assert result["f1_pass"] is True, (
        f"functional F1 fails: evoked_A before={evA_before} after_A={evA_after_A} "
        f"after_B={evA_after_B} after_none={evA_after_none} "
        f"(need after_A-after_none>={k013.F1_MIN} and after_A-after_B>={k013.F1_MIN})"
    )
