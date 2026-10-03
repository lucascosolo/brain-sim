"""K1.1 rerun, labelled proxy "encode-mode" (SPEC.md section 8.12), replacing
the five driver flags with the engine's own `encode_mode` (SPEC 8.11 -> the
8.12 plant). Unit tests on `run_experiment`'s signature, `main()`'s
`--encode-mode` flag, the removal of the five old flags and the driver's own
copies of the encode helpers, `_encode_pins_ok(pins)`, and the single
@pytest.mark.s1 replay wrapper.

None of `run_experiment(encode_mode=...)`, `--encode-mode`, or
`_encode_pins_ok` exist yet on this branch: every fast test below is expected
to fail today with TypeError/AttributeError, not an ImportError in this file.
"""
import inspect
import sys

import pytest


def _k11():
    from tests import k11_binding as k11
    return k11


# --------------------------------------------------------------------------- #
# 1. run_experiment signature
# --------------------------------------------------------------------------- #

def test_run_experiment_has_encode_mode_kwarg_defaulting_false():
    k11 = _k11()
    sig = inspect.signature(k11.run_experiment)
    assert "encode_mode" in sig.parameters
    assert sig.parameters["encode_mode"].default is False


def test_run_experiment_no_longer_has_old_flag_kwargs():
    k11 = _k11()
    sig = inspect.signature(k11.run_experiment)
    for old in ("hpc_encode_window", "sparse_write", "window_on_w", "small_ww", "grace"):
        assert old not in sig.parameters, old


# --------------------------------------------------------------------------- #
# 2. main() flag parsing
# --------------------------------------------------------------------------- #

def test_main_parses_encode_mode_flag(monkeypatch):
    k11 = _k11()
    calls = {}

    def fake_run_experiment(*args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs
        return {"stub": True}

    monkeypatch.setattr(k11, "run_experiment", fake_run_experiment)
    monkeypatch.setattr(k11, "report", lambda out, wall: None)
    monkeypatch.setattr(sys, "argv", ["k11_binding.py", "--encode-mode"])

    k11.main()

    assert calls["kwargs"].get("encode_mode") is True


def test_main_positional_seed_still_works_with_encode_mode_flag(monkeypatch):
    k11 = _k11()
    calls = {}

    def fake_run_experiment(*args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs
        return {"stub": True}

    monkeypatch.setattr(k11, "run_experiment", fake_run_experiment)
    monkeypatch.setattr(k11, "report", lambda out, wall: None)
    monkeypatch.setattr(sys, "argv", ["k11_binding.py", "--encode-mode", "7"])

    k11.main()

    seed_arg = calls["args"][0] if calls["args"] else calls["kwargs"].get("seed")
    assert seed_arg == 7
    assert calls["kwargs"].get("encode_mode") is True


# --------------------------------------------------------------------------- #
# 3. old driver-level helpers/flags removed
# --------------------------------------------------------------------------- #

def test_old_encode_window_helpers_removed_from_driver():
    k11 = _k11()
    for name in ("hpc_encode_window", "hpc_grace", "_hpc_encode_window_ctx",
                 "_window_on", "_encode_window_pins_ok"):
        assert not hasattr(k11, name), name


# --------------------------------------------------------------------------- #
# 4. _encode_pins_ok(pins)
# --------------------------------------------------------------------------- #

_MOMENTS = ("before_A", "during_A", "during_A_end", "during_delay",
            "during_delay_end", "cue_start", "during_B", "during_B_end")
_MASKED = ("during_A", "during_A_end", "during_delay", "during_B", "during_B_end")
_PLANT = 0.06


def _passing_encode_pins():
    """The 8.12 passing shape: stage present during A and B, grace at
    during_A_end/during_delay/during_B_end, idle at during_delay_end, off at
    cue_start; mask_W_frac 1.0 whenever masked, a_minus_W 0.0 during
    present, restored to plant otherwise; mask_other_frac and
    mask_hpc_e_not_W_frac 0.0 everywhere."""
    stage = {
        "before_A": "idle", "during_A": "present", "during_A_end": "grace",
        "during_delay": "grace", "during_delay_end": "idle", "cue_start": "off",
        "during_B": "present", "during_B_end": "grace",
    }
    mask_W_frac = {m: (1.0 if m in _MASKED else 0.0) for m in _MOMENTS}
    a_minus_W = {m: (0.0 if m in ("during_A", "during_B") else _PLANT) for m in _MOMENTS}
    mask_hpc_e_not_W_frac = {m: 0.0 for m in _MOMENTS}
    mask_other_frac = {m: 0.0 for m in _MOMENTS}
    a_minus_hpc_e_not_W = {m: _PLANT for m in _MOMENTS}
    return {
        "stage": stage,
        "mask_W_frac": mask_W_frac,
        "mask_hpc_e_not_W_frac": mask_hpc_e_not_W_frac,
        "mask_other_frac": mask_other_frac,
        "a_minus_W": a_minus_W,
        "a_minus_hpc_e_not_W": a_minus_hpc_e_not_W,
    }


def test_encode_pins_ok_passing_shape():
    k11 = _k11()
    pins = _passing_encode_pins()
    assert k11._encode_pins_ok(pins) is True


def test_encode_pins_ok_fails_when_stage_wrong_during_a():
    k11 = _k11()
    pins = _passing_encode_pins()
    pins["stage"]["during_A"] = "idle"
    assert k11._encode_pins_ok(pins) is False


def test_encode_pins_ok_fails_when_mask_still_on_at_delay_end():
    k11 = _k11()
    pins = _passing_encode_pins()
    pins["mask_W_frac"]["during_delay_end"] = 1.0
    assert k11._encode_pins_ok(pins) is False


def test_encode_pins_ok_fails_when_a_minus_w_zero_at_a_end():
    k11 = _k11()
    pins = _passing_encode_pins()
    pins["a_minus_W"]["during_A_end"] = 0.0
    assert k11._encode_pins_ok(pins) is False


def test_encode_pins_ok_fails_when_mask_other_frac_nonzero_anywhere():
    k11 = _k11()
    pins = _passing_encode_pins()
    pins["mask_other_frac"]["during_A"] = 1e-6
    assert k11._encode_pins_ok(pins) is False


def test_encode_pins_ok_fails_when_mask_hpc_e_not_w_frac_nonzero_anywhere():
    k11 = _k11()
    pins = _passing_encode_pins()
    pins["mask_hpc_e_not_W_frac"]["during_delay"] = 1.0 / 304.0
    assert k11._encode_pins_ok(pins) is False


# --------------------------------------------------------------------------- #
# s1: the rerun itself, replay of 8.11 exactly
# --------------------------------------------------------------------------- #

_K11_ENCODE_CACHE = {}


def _k11_encode_result():
    if "result" not in _K11_ENCODE_CACHE:
        k11 = _k11()
        _K11_ENCODE_CACHE["module"] = k11
        _K11_ENCODE_CACHE["result"] = k11.run_experiment(1, encode_mode=True)
    return _K11_ENCODE_CACHE["module"], _K11_ENCODE_CACHE["result"]


@pytest.mark.s1
def test_k1_1_binding_encode_mode():
    """K1.1 rerun (SPEC.md 8.12): the encode-mode plant must reproduce the
    8.11 replay exactly (assembly 19; W recall at 50 ticks half 5/16, full
    10/16, none 2/16; marks donor->W n=987, W->W n=47 at the cue); FAIL on
    criterion 2, the K1.1 bar is not lowered."""
    k11, out = _k11_encode_result()

    assert out["encode_mode"] is True

    for name, ok in out["validity"].items():
        assert ok is True, f"K1.1 (encode-mode) INVALID experiment: validity[{name}] failed"

    assembly = out["assembly"]
    assert assembly["size"] == 19

    cue = out["arms"]["cue"]
    full = out["arms"]["full"]
    none = out["arms"]["none"]
    assert cue["recall_W"][50] == pytest.approx(5 / 16)
    assert full["recall_W"][50] == pytest.approx(10 / 16)
    assert none["recall_W"][50] == pytest.approx(2 / 16)

    marks = out["marks"]
    cue_mark = marks["cue_50"]
    assert cue_mark["donor_to_W"]["n"] == 987
    assert cue_mark["hpc_hpc_within_W"]["n"] == 47

    assert not out["criteria"]["c2_recall_50_W"], (
        "K1.1 (encode-mode) should still FAIL criterion 2 (bar not lowered): "
        f"criteria={out['criteria']}"
    )
