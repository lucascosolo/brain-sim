"""K1.1 hpc binding / pattern completion (SPEC.md section 8.2).

Fast unit tests pin the driver's constants and pure helper functions; the single
@pytest.mark.s1 test runs the full experiment (warm-up + protocol, ~3 minutes) and
checks the predeclared criteria. The driver (tests/k11_binding.py) does not exist yet:
every fast test below is expected to fail today with ImportError.
"""
import numpy as np
import pytest


def _k11():
    from tests import k11_binding as k11
    return k11


def test_constants_pinned():
    k11 = _k11()
    assert k11.SEED == 1
    assert k11.BASE_TICKS == 2000
    assert k11.A_TICKS == 2000
    assert k11.DELAY_TICKS == 1000
    assert k11.CUE_TICKS == 200
    assert k11.WINDOW_TICKS == 50
    assert k11.REPORT_WINDOWS == (50, 100, 200)
    assert k11.EXCESS_HZ == 4.0
    assert k11.ASSEMBLY_MAX == 20
    assert k11.RECALL_MIN == 0.80
    assert k11.SPURIOUS_FRAC == 0.5
    assert k11.VOLLEY_MIN_FRAC == 0.7
    assert k11.PATTERN_A == 0
    assert k11.PATTERN_B == 1
    assert k11.SLEEP_ONSET_TICK == 140_000


def test_cue_ids_returns_sorted_even_positions():
    k11 = _k11()
    pattern = np.arange(40) + 7  # already sorted, 7..46
    cue = k11.cue_ids(pattern)
    expected = np.sort(pattern)[0::2]
    assert cue.shape == (20,)
    assert np.array_equal(cue, expected)
    assert np.array_equal(cue, np.sort(cue))


def test_cue_ids_sorts_unsorted_input_first():
    k11 = _k11()
    rng = np.random.default_rng(0)
    pattern = rng.permutation(np.arange(40) + 7)
    cue = k11.cue_ids(pattern)
    expected = np.sort(pattern)[0::2]
    assert np.array_equal(cue, expected)
    assert np.array_equal(cue, np.sort(cue))


def test_assembly_from_counts_excess_boundary_and_scope():
    k11 = _k11()
    ticks = 2000
    ids = np.array([0, 1, 2, 3, 5])  # cell 4 deliberately excluded from ids
    base = np.zeros(6, dtype=np.int64)
    stim = np.zeros(6, dtype=np.int64)
    # cell 0: exactly 8 excess spikes over 2000 ticks == 4.0 Hz excess -> in
    stim[0] = 8
    # cell 1: 7 excess spikes -> 3.5 Hz excess -> out
    stim[1] = 7
    # cell 2: also 8 excess but with a nonzero baseline, to check the diff is used
    base[2] = 3
    stim[2] = 11
    # cell 3: below-threshold excess -> out
    stim[3] = 5
    # cell 4: would qualify (10 excess) but is not in `ids` -> must never appear
    stim[4] = 10
    # cell 5: 0 excess -> out
    assembly = k11.assembly_from_counts(base, stim, ids, ticks)
    assembly = np.asarray(assembly)
    assert set(assembly.tolist()) == {0, 2}
    assert np.array_equal(assembly, np.sort(assembly))
    assert set(assembly.tolist()) <= set(ids.tolist())
    assert 4 not in assembly.tolist()


def test_expected_spiking_known_rates():
    k11 = _k11()
    rates = [1.0, 1.0, 0.0]
    window_ticks = 50
    got = k11.expected_spiking(rates, window_ticks)
    want = 2 * (1 - np.exp(-0.05))
    assert abs(got - want) < 1e-12


def _minimal_out(*, valid_all=True, all_valid_true=True, size=10,
                  recall50=0.9, spurious50=1.0):
    """Build the smallest `out` dict report() needs, per API.md, with knobs to
    steer the verdict precedence being tested."""
    validity = {
        "wake_throughout": all_valid_true,
        "a_volley": all_valid_true,
        "cue_volley": all_valid_true,
        "inject_sense_only": all_valid_true,
        "engine_pins_ok": all_valid_true,
        "valid_all": valid_all,
    }
    criteria = {
        "c1_forms_sparse": 1 <= size <= 20,
        "c2_recall_50": recall50 >= 0.80,
        "c3_no_other_assembly": spurious50 < 0.5 * size,
    }
    criteria["pass"] = bool(criteria["c1_forms_sparse"] and criteria["c2_recall_50"]
                            and criteria["c3_no_other_assembly"])  # derived, never a free knob
    rates_ema = {r: {"E": 1.0, "I": 6.0 if r in ("hpc", "ctx") else None}
                 for r in ("sense", "ctx", "hpc")}
    arm = {
        "recall": {50: recall50, 100: recall50, 200: recall50},
        "assembly_spiking_50": int(round(recall50 * size)),
        "nonassembly_spiking_50": 0,
        "nonassembly_expected_50": 0.0,
        "spurious_excess_50": spurious50,
        "hpc_e_rate_window_hz": 1.0,
        "hpc_i_rate_window_hz": 6.0,
        "first_assembly_spike_tick": 40,
        "stim_volley_frac": 0.9,
    }
    none_arm = dict(arm)
    none_arm["stim_volley_frac"] = float("nan")
    return {
        "seed": 1,
        "t_warm_end": 120000,
        "t_end": 125200,
        "phase_end": "wake",
        "rates": {"baseline": {}, "a": {}},
        "assembly": {"ids": list(range(size)), "size": size, "i_responders": 0,
                     "rate_a_hz": 5.0, "rate_base_hz": 1.0,
                     "other_e_rate_a_hz": 1.0, "other_e_rate_base_hz": 1.0,
                     "hpc_i_rate_a_hz": 6.0, "hpc_i_rate_base_hz": 6.0,
                     "ctx_e_rate_a_hz": 4.0, "ctx_e_rate_base_hz": 4.0,
                     "a_volley_frac": 0.9},
        "assembly_B": {"ids": [], "size": 0, "overlap_with_A": 0,
                       "overlap_frac_of_A": float("nan")},
        "arms": {"cue": arm, "full": dict(arm), "none": none_arm},
        "synapses": {
            "sense_to_hpc": {"n": 0, "mean_w_over_wmax": float("nan")},
            "ctx_to_hpc_onto_assembly": {"n_before": 1, "mean_before": 0.5,
                                          "n_after": 1, "mean_after": 0.5},
            "ctx_to_hpc_onto_other_e": {"n_before": 1, "mean_before": 0.5,
                                         "n_after": 1, "mean_after": 0.5},
            "hpc_hpc_within_assembly": {"n_before": 1, "mean_before": 0.5,
                                         "n_after": 1, "mean_after": 0.5},
            "hpc_hpc_assembly_to_other_e": {"n_before": 1, "mean_before": 0.5,
                                             "n_after": 1, "mean_after": 0.5},
            "hpc_hpc_other_e_to_assembly": {"n_before": 1, "mean_before": 0.5,
                                             "n_after": 1, "mean_after": 0.5},
            "indegree_assembly_e_mean": 30.0,
            "indegree_other_e_mean": 30.0,
        },
        "rates_ema_hz_at_warm_end": rates_ema,
        "engine_pins": {"has_plasticity_mode": False, "has_stdp_rule": False,
                         "a_plus_hpc": 0.05, "a_minus_hpc": 0.06, "w_max_hpc": 3.0,
                         "r_target_hpc_e": 1.0, "r_target_hpc_i": 6.0,
                         "pattern_amp_mv": 1.3, "pattern_size": 40,
                         "sense_to_hpc_projection": False},
        "validity": validity,
        "criteria": criteria,
        "inject_log": [],
        "A_ids": [], "cue_ids": [], "B_ids": [],
    }


def test_report_verdict_invalid_beats_fail(capsys):
    k11 = _k11()
    out = _minimal_out(valid_all=False, all_valid_true=False, size=0,
                        recall50=0.0, spurious50=10.0)
    k11.report(out, 1.0)
    captured = capsys.readouterr()
    lines = [l for l in captured.out.splitlines() if l.strip()]
    assert lines[-1].startswith("K1.1 VERDICT: INVALID")


def test_report_verdict_fail_when_valid_but_criteria_fail(capsys):
    k11 = _k11()
    out = _minimal_out(valid_all=True, all_valid_true=True, size=10,
                        recall50=0.0625, spurious50=1.0)
    k11.report(out, 1.0)
    captured = capsys.readouterr()
    lines = [l for l in captured.out.splitlines() if l.strip()]
    assert lines[-1].startswith("K1.1 VERDICT: FAIL (")
    assert "0.0625" in lines[-1]  # the c2 reason carries the measured recall, not a placeholder
    assert "c1" not in lines[-1] and "c3" not in lines[-1]


def test_report_verdict_pass_when_everything_true(capsys):
    k11 = _k11()
    out = _minimal_out(valid_all=True, all_valid_true=True, size=10,
                        recall50=0.9, spurious50=1.0)
    k11.report(out, 1.0)
    captured = capsys.readouterr()
    lines = [l for l in captured.out.splitlines() if l.strip()]
    assert lines[-1] == "K1.1 VERDICT: PASS"


_K11_CACHE = {}


def _k11_result():
    """Run the K1.1 binding experiment once per session and cache it."""
    if "result" not in _K11_CACHE:
        k11 = _k11()
        _K11_CACHE["module"] = k11
        _K11_CACHE["result"] = k11.run_experiment()
    return _K11_CACHE["module"], _K11_CACHE["result"]


@pytest.mark.s1
def test_k1_1_binding_pattern_completion():
    """K1.1: does the binder form a sparse hpc assembly for pattern A and complete it
    from a 50% cue within 50 ticks, without igniting a spurious second assembly?"""
    k11, out = _k11_result()

    assembly = out["assembly"]
    assembly_B = out["assembly_B"]
    cue = out["arms"]["cue"]
    full = out["arms"]["full"]
    none = out["arms"]["none"]
    synapses = out["synapses"]
    validity = out["validity"]
    criteria = out["criteria"]

    outcome_report = (
        f"assembly size={assembly['size']} i_responders={assembly['i_responders']} "
        f"assembly rate_base={assembly['rate_base_hz']} rate_a={assembly['rate_a_hz']} "
        f"other_e rate_base={assembly['other_e_rate_base_hz']} "
        f"rate_a={assembly['other_e_rate_a_hz']} "
        f"hpc_i rate_base={assembly['hpc_i_rate_base_hz']} rate_a={assembly['hpc_i_rate_a_hz']} "
        f"ctx_e rate_base={assembly['ctx_e_rate_base_hz']} rate_a={assembly['ctx_e_rate_a_hz']} "
        f"cue recall={cue['recall']} full recall={full['recall']} "
        f"cue assembly_spiking_50={cue['assembly_spiking_50']} "
        f"nonassembly_spiking_50={cue['nonassembly_spiking_50']} "
        f"nonassembly_expected_50={cue['nonassembly_expected_50']} "
        f"spurious_excess_50={cue['spurious_excess_50']} "
        f"none nonassembly_spiking_50={none['nonassembly_spiking_50']} "
        f"cue first_assembly_spike_tick={cue['first_assembly_spike_tick']} "
        f"full first_assembly_spike_tick={full['first_assembly_spike_tick']} "
        f"B size={assembly_B['size']} overlap_frac_of_A={assembly_B['overlap_frac_of_A']} "
        f"synapses={synapses} "
        f"rates_ema_hz_at_warm_end={out['rates_ema_hz_at_warm_end']} "
        f"engine_pins={out['engine_pins']} "
        f"validity={validity}"
    )

    # Protocol pins.
    assert out["t_warm_end"] == 120000, outcome_report
    assert len(out["A_ids"]) == 40, outcome_report
    assert len(out["cue_ids"]) == 20, outcome_report
    assert set(out["cue_ids"]) <= set(out["A_ids"]), outcome_report
    assert out["engine_pins"]["sense_to_hpc_projection"] is False, outcome_report

    # Validity: an invalid run cannot be read as a task result either way.
    for name, ok in validity.items():
        assert ok is True, f"INVALID experiment: validity[{name}] failed\n{outcome_report}"

    # The criteria booleans must equal their definitions recomputed from the raw
    # numbers, so the driver cannot drift from the contract.
    size = assembly["size"]
    assert criteria["c1_forms_sparse"] == (1 <= size <= 20), outcome_report
    assert criteria["c2_recall_50"] == (cue["recall"][50] >= 0.80), outcome_report
    assert criteria["c3_no_other_assembly"] == (
        cue["spurious_excess_50"] < 0.5 * size
    ), outcome_report

    # Criterion 1: the assembly forms and is sparse.
    assert criteria["c1_forms_sparse"], (
        f"K1.1 FAIL (c1 assembly forms and is sparse): {outcome_report}"
    )
    # Criterion 2: >= 80% of the assembly recalled within 50 ticks of the cue.
    assert criteria["c2_recall_50"], (
        f"K1.1 FAIL (c2 >= 80 % of the assembly within 50 ticks): {outcome_report}"
    )
    # Criterion 3: no other (spurious) assembly ignites in the same window.
    assert criteria["c3_no_other_assembly"], (
        f"K1.1 FAIL (c3 no other assembly ignites): {outcome_report}"
    )
    assert criteria["pass"], outcome_report
