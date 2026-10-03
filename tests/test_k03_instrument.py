"""Tests pinning the K0.3 instrument generalisation of ``run_arm``.

Contract under test: ``run_arm`` gains ``pattern=0`` and ``present=True`` keyword
arguments. ``pattern`` selects which ``eng.patterns[pattern]`` is presented at each
trial start (``present=False`` presents nothing). ``offsets`` entries may be empty
tuples meaning no pulse in that trial. The two pinned invariants are:

  1. the default (no keywords given) K0.3 protocol -- present pattern 0, three
     pulses per trial -- is completely unchanged;
  2. the generalisation never emits a postsynaptic injection unless a pulse is
     explicitly scheduled for that trial -- a zero-pulse arm must not "leak" any
     current injection into ctx_a, and must report the resulting NaN/zero
     telemetry cleanly, without warnings.
"""

import math
import warnings

import numpy as np
import pytest

from tests import k03_pairing as k03


@pytest.fixture
def rig(monkeypatch):
    """A cheap (non-120s-warmup) engine + spk ring + ctx_a, TRIALS forced to 2."""
    monkeypatch.setattr(k03, "TRIALS", 2)
    monkeypatch.setattr(k03, "TOTAL_TICKS", 2 * k03.TRIAL_TICKS)

    eng = k03.Engine(seed=1, params=k03._deepcopyable_params())
    spk = np.zeros((k03.D_MAX + 1, eng.net.n), bool)
    for _ in range(k03.D_MAX):
        t = eng.t
        eng.step(1)
        s = eng._buf_spikes[-1]
        k03._drain_telemetry(eng)
        spk[t % (k03.D_MAX + 1)] = False
        spk[t % (k03.D_MAX + 1), s] = True

    ctx_a = k03.select_ctx_a(eng.net, eng.patterns[0])
    if ctx_a.size == 0:
        pytest.skip("no ctx_a cells selected on this seed/warmup")

    A = eng.patterns[0]
    ctx_a_mask = np.zeros(eng.net.n, bool)
    ctx_a_mask[ctx_a] = True
    sense = eng.net.region_slice["sense"]
    T0 = k03._tracked(eng.net, ctx_a_mask, sense)
    a_mask = np.zeros(eng.net.n, bool)
    a_mask[A] = True
    base = {
        "slots": T0, "pre": eng.net.pre[T0].copy(), "post": eng.net.post[T0].copy(),
        "born": eng.net.born[T0].copy(), "w": eng.net.w[T0].copy(),
        "group": a_mask[eng.net.pre[T0]],
    }
    return eng, spk, ctx_a, A, base, sense


def _wrap_inject(eng):
    calls = []
    orig = eng.inject

    def wrapped(ids, amp, ticks):
        calls.append((np.asarray(ids, np.int32).copy(), float(amp), int(ticks), int(eng.t)))
        return orig(ids, amp, ticks)

    eng.inject = wrapped
    return calls


def _is_sense_id(sense, i):
    return sense.start <= i < sense.stop


def test_default_protocol_injects_presentations_and_three_pulses_per_trial(rig):
    eng, spk, ctx_a, A, base, sense = rig
    calls = _wrap_inject(eng)

    res = k03.run_arm(eng, spk, ctx_a, A, [k03.PULSE_OFFSETS] * 2, base)

    assert len(calls) == 8
    for trial in range(2):
        pres = calls[trial * 4]
        assert np.array_equal(pres[0], np.asarray(eng.patterns[0], np.int32))
        assert pres[1] == pytest.approx(eng.p.PATTERN_AMP_MV)
        assert pres[2] == k03.ON_TICKS
        for j in range(3):
            pulse = calls[trial * 4 + 1 + j]
            assert np.array_equal(np.sort(pulse[0]), np.sort(np.asarray(ctx_a, np.int32)))
            assert pulse[1] == pytest.approx(30.0)
            assert pulse[2] == 1

    assert res["pulse_ticks_total"] == 6
    assert res["pattern_presented"] == 0


def test_zero_pulses_pattern_b_emits_only_sense_presentations(rig):
    eng, spk, ctx_a, A, base, sense = rig
    calls = _wrap_inject(eng)
    stimlog_len_before = len(eng.stimlog)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        res = k03.run_arm(eng, spk, ctx_a, A, [()] * 2, base, pattern=1, present=True)

    assert len(calls) == 2
    for c in calls:
        assert np.array_equal(c[0], np.asarray(eng.patterns[1], np.int32))
        assert c[1] == pytest.approx(eng.p.PATTERN_AMP_MV)
        assert c[2] == k03.ON_TICKS
        for i in c[0]:
            assert _is_sense_id(sense, int(i))

    assert res["pulse_ticks_total"] == 0
    assert res["pulse_spike_frac_mean"] == 0.0
    assert res["pulse_spike_frac_min"] == 0.0
    assert res["pattern_presented"] == 1

    for name in ("A", "nonA"):
        g = res["groups"][name]
        assert math.isnan(g["pulse_causal_over_anticausal"])
        assert math.isnan(g["pulse_lag_peak_over_median"])
        assert math.isnan(g["pulse_causal_lag_median"])
        assert g["pulse_lag_peak"] == 0

    for v in res["per_trial_pulse_lag_median"]:
        assert math.isnan(v)
    for v in res["per_trial_pulse_spike_frac"]:
        assert v == 0.0

    assert len(eng.stimlog) == stimlog_len_before + 2
    for rec in eng.stimlog:
        assert rec["n_sense_cells"] == rec["n_cells"]
        assert rec["amp_mv"] == pytest.approx(eng.p.PATTERN_AMP_MV)


def test_present_false_emits_nothing(rig):
    eng, spk, ctx_a, A, base, sense = rig
    calls = _wrap_inject(eng)
    seq_before = eng._stim_seq
    stimlog_len_before = len(eng.stimlog)

    res = k03.run_arm(eng, spk, ctx_a, A, [()] * 2, base, present=False)

    assert calls == []
    assert eng._stim_seq == seq_before
    assert len(eng.stimlog) == stimlog_len_before
    assert res["pattern_presented"] is None
    assert res["pulse_ticks_total"] == 0
    assert res["t_end"] - res["t_start"] == 2 * k03.TRIAL_TICKS


def test_zero_pulse_arm_attribution_closes(rig):
    eng, spk, ctx_a, A, base, sense = rig
    res = k03.run_arm(eng, spk, ctx_a, A, [()] * 2, base, pattern=1, present=True)

    assert res["instrument_max_residual_nonsweep"] == 0.0
    assert res["scaling_pred_vs_resid_max_abs"] == 0.0
    assert res["pair_count_crosscheck_ok"] is True
    for name in ("A", "nonA"):
        assert abs(res["groups"][name]["closure_residual"]) < 1e-6


def test_pulse_offsets_beyond_on_window_still_fire(rig):
    eng, spk, ctx_a, A, base, sense = rig
    calls = _wrap_inject(eng)
    t_start = eng.t

    res = k03.run_arm(eng, spk, ctx_a, A, [(500,)] * 2, base)

    pulse_calls = [c for c in calls if c[2] == 1]
    assert len(pulse_calls) == 2
    for trial, c in enumerate(pulse_calls):
        expected_t = t_start + trial * k03.TRIAL_TICKS + 500
        assert c[3] == expected_t
    assert res["pulse_ticks_total"] == 2


def test_default_path_numeric_pin(rig):
    # Pinned 2026-09-12 on this cheap (2-trial) rig's default path, the same day the
    # full-protocol (TRIALS=20) result of record -- ratio_final 0.927473 (pairing) /
    # 0.869582 (control) -- was reproduced exactly. This pin exists to catch drift of
    # the unchanged default path if the instrument is generalised further.
    eng, spk, ctx_a, A, base, sense = rig
    res = k03.run_arm(eng, spk, ctx_a, A, [k03.PULSE_OFFSETS] * 2, base)

    assert res["ratio_final"] == pytest.approx(0.9839534924881074, abs=0, rel=1e-12)
    assert res["pattern_presented"] == 0
    assert res["pulse_ticks_total"] == 6
