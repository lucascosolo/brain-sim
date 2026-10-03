"""K1.1 rerun, restricted donors proxy (SPEC.md section 8.8).

Unit tests on the `donor_k` clause of `sparse_cofire_write` (pure / fake-net),
`k11.DONOR_K`, the `run_experiment(restricted_donors=)` guard and kwarg
default, `main()`'s `--restricted-donors` flag, the digest guard, and the
single @pytest.mark.s1 rerun wrapper (criterion 2, assembly-defined, only).
None of `k11.DONOR_K`, the `donor_k` parameter on `sparse_cofire_write`, or
the `restricted_donors` kwarg/flag exist yet: every fast test that touches
them is expected to fail today with AttributeError/TypeError, not an
ImportError in this file.
"""
import inspect
import sys

import numpy as np
import pytest


def _k11():
    from tests import k11_binding as k11
    return k11


# --------------------------------------------------------------------------- #
# 1. constant
# --------------------------------------------------------------------------- #

def test_donor_k_constant():
    k11 = _k11()
    assert k11.DONOR_K == 64


# --------------------------------------------------------------------------- #
# 2. sparse_cofire_write with donor_k, on a hand-built fake net
# --------------------------------------------------------------------------- #

def _fake_net_donor_k():
    # 8 cells: 0-4 ctx E (candidate donors), 5-7 hpc E (candidate W).
    import types
    net = types.SimpleNamespace()
    net.n = 8
    net.is_exc = np.array([True] * 8)
    # DIFFERENT w_max_n per postsynaptic cell, to pin the "postsynaptic
    # w_max" clause under donor_k too.
    net.w_max_n = np.array([1.0, 1.0, 1.0, 1.0, 1.0, 2.0, 4.0, 3.0], dtype=np.float64)
    # 4 synapses:
    #  0: donor(0) -> W(5), alive   bumped 0.15*2.0=0.3   1.0 -> 1.3
    #  1: donor(3) -> W(6), alive   bumped 0.15*4.0=0.6   3.9 -> clamped 4.0
    #  2: spiking non-donor(1) -> W(5), alive             untouched (not top-2)
    #  3: non-donor(4) -> W(6), alive                     untouched (not top-2)
    net.pre = np.array([0, 3, 1, 4], dtype=np.int64)
    net.post = np.array([5, 6, 5, 6], dtype=np.int64)
    net.w = np.array([1.0, 3.9, 0.7, 0.2], dtype=np.float64)
    net.alive = np.array([True, True, True, True])
    return net


def _fake_counts_donor_k():
    # ctx E ids 0..4: counts 5, 3, 0, 7, 1. hpc E ids 5..7: counts 10, 8, 1.
    return np.array([5, 3, 0, 7, 1, 10, 8, 1], dtype=np.int64)


def test_sparse_cofire_write_donor_k_restricts_donors_and_bumps_only_top_donors():
    k11 = _k11()
    net = _fake_net_donor_k()
    counts = _fake_counts_donor_k()
    hpc_e_ids = np.array([5, 6, 7], dtype=np.int64)
    ctx_e_ids = np.array([0, 1, 2, 3, 4], dtype=np.int64)

    rec = k11.sparse_cofire_write(
        net, counts, hpc_e_ids, ctx_e_ids, k=2, delta_frac=0.15, donor_k=2)

    # W: top 2 of hpc E by count -> ids 5 (10), 6 (8).
    assert list(rec["W"]) == [5, 6]
    # donors: top 2 of ctx E by count -> id3 (7), id0 (5) -> sorted [0, 3].
    assert rec["donor_ids"] == [0, 3]
    assert rec["donors"] == 2
    assert rec["donor_k"] == 2

    expected_w = np.array([1.3, 4.0, 0.7, 0.2])
    np.testing.assert_allclose(net.w, expected_w, rtol=0, atol=1e-9)
    assert rec["n_synapses_bumped"] == 2
    assert rec["n_clamped"] == 1  # idx 1 only, clamped at w_max_n[6]=4.0


def test_sparse_cofire_write_donor_k_none_keeps_8_6_rule():
    k11 = _k11()
    net = _fake_net_donor_k()
    counts = _fake_counts_donor_k()
    hpc_e_ids = np.array([5, 6, 7], dtype=np.int64)
    ctx_e_ids = np.array([0, 1, 2, 3, 4], dtype=np.int64)

    rec = k11.sparse_cofire_write(
        net, counts, hpc_e_ids, ctx_e_ids, k=2, delta_frac=0.15, donor_k=None)

    # every spiking ctx E id (count > 0): 0, 1, 3, 4 (id 2 has count 0).
    assert rec["donor_ids"] == [0, 1, 3, 4]
    assert rec["donors"] == 4
    assert rec["donor_k"] is None


def test_sparse_cofire_write_donor_k_default_is_none():
    k11 = _k11()
    sig = inspect.signature(k11.sparse_cofire_write)
    assert sig.parameters["donor_k"].default is None


def test_sparse_cofire_write_donor_k_tie_broken_by_lower_id():
    k11 = _k11()
    net = _fake_net_donor_k()
    # ctx E ids 0 and 1 tied at the top; donor_k=1 must keep the lower id.
    counts = np.array([9, 9, 0, 3, 1, 10, 8, 1], dtype=np.int64)
    hpc_e_ids = np.array([5, 6, 7], dtype=np.int64)
    ctx_e_ids = np.array([0, 1, 2, 3, 4], dtype=np.int64)

    rec = k11.sparse_cofire_write(
        net, counts, hpc_e_ids, ctx_e_ids, k=2, delta_frac=0.15, donor_k=1)

    assert rec["donor_ids"] == [0]
    assert rec["donors"] == 1
    assert rec["donor_k"] == 1


def test_sparse_cofire_write_existing_behaviour_unaffected():
    """donor_k is additive: with no donor_k argument at all the 8.6 call
    signature and behaviour must be exactly as before (regression guard for
    the sibling test file's own fake-net case)."""
    k11 = _k11()
    net = _fake_net_donor_k()
    counts = _fake_counts_donor_k()
    hpc_e_ids = np.array([5, 6, 7], dtype=np.int64)
    ctx_e_ids = np.array([0, 1, 2, 3, 4], dtype=np.int64)

    rec = k11.sparse_cofire_write(net, counts, hpc_e_ids, ctx_e_ids, k=2, delta_frac=0.15)

    assert rec["donor_ids"] == [0, 1, 3, 4]
    assert rec["donors"] == 4
    assert rec["donor_k"] is None


# --------------------------------------------------------------------------- #
# 3. run_experiment: kwarg default and the guard
# --------------------------------------------------------------------------- #

def test_run_experiment_restricted_donors_default_false():
    k11 = _k11()
    sig = inspect.signature(k11.run_experiment)
    assert sig.parameters["restricted_donors"].default is False


def test_restricted_donors_without_sparse_write_raises_before_running(monkeypatch):
    k11 = _k11()

    def boom(*args, **kwargs):
        raise AssertionError("warm_engine must not be called when the guard should fire first")

    monkeypatch.setattr(k11.k03, "warm_engine", boom)

    with pytest.raises((AssertionError, ValueError)):
        k11.run_experiment(hpc_encode_window=False, sparse_write=False, restricted_donors=True)


# --------------------------------------------------------------------------- #
# 4. main() flag parsing
# --------------------------------------------------------------------------- #

def test_main_parses_restricted_donors_flag_implies_sparse_write_and_window(monkeypatch):
    k11 = _k11()
    calls = {}

    def fake_run_experiment(*args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs
        return {"stub": True}

    monkeypatch.setattr(k11, "run_experiment", fake_run_experiment)
    monkeypatch.setattr(k11, "report", lambda out, wall: None)
    monkeypatch.setattr(sys, "argv", ["k11_binding.py", "--restricted-donors"])

    k11.main()

    assert calls["kwargs"].get("restricted_donors") is True, (
        f"--restricted-donors must map to restricted_donors=True, got kwargs={calls['kwargs']}"
    )
    assert calls["kwargs"].get("sparse_write") is True, (
        f"--restricted-donors must imply sparse_write=True, got kwargs={calls['kwargs']}"
    )
    assert calls["kwargs"].get("hpc_encode_window") is True, (
        f"--restricted-donors must imply hpc_encode_window=True, got kwargs={calls['kwargs']}"
    )


def test_main_defaults_restricted_donors_false_without_flag(monkeypatch):
    k11 = _k11()
    calls = {}

    def fake_run_experiment(*args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs
        return {"stub": True}

    monkeypatch.setattr(k11, "run_experiment", fake_run_experiment)
    monkeypatch.setattr(k11, "report", lambda out, wall: None)
    monkeypatch.setattr(sys, "argv", ["k11_binding.py"])

    k11.main()

    assert calls["kwargs"].get("restricted_donors", False) is False
    assert calls["kwargs"].get("sparse_write", False) is False
    assert calls["kwargs"].get("hpc_encode_window", False) is False


def test_main_positional_seed_still_works_with_restricted_donors(monkeypatch):
    k11 = _k11()
    calls = {}

    def fake_run_experiment(*args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs
        return {"stub": True}

    monkeypatch.setattr(k11, "run_experiment", fake_run_experiment)
    monkeypatch.setattr(k11, "report", lambda out, wall: None)
    monkeypatch.setattr(sys, "argv", ["k11_binding.py", "7", "--restricted-donors"])

    k11.main()

    assert calls["args"][0] == 7 or calls["kwargs"].get("seed") == 7


# --------------------------------------------------------------------------- #
# 5. default digest unchanged (byte-identity guard; already green)
# --------------------------------------------------------------------------- #

def test_default_engine_digest_unchanged():
    from tests.test_engine_determinism import run_schedule, _digest, REFERENCE_DIGEST
    e = run_schedule()
    assert _digest(e) == REFERENCE_DIGEST


# --------------------------------------------------------------------------- #
# s1: the rerun itself, criterion 2 (assembly-defined) only
# --------------------------------------------------------------------------- #

_K11_RESTRICTED_DONORS_CACHE = {}


def _k11_restricted_donors_result():
    if "result" not in _K11_RESTRICTED_DONORS_CACHE:
        k11 = _k11()
        _K11_RESTRICTED_DONORS_CACHE["module"] = k11
        _K11_RESTRICTED_DONORS_CACHE["result"] = k11.run_experiment(
            hpc_encode_window=True, sparse_write=True, restricted_donors=True)
    return _K11_RESTRICTED_DONORS_CACHE["module"], _K11_RESTRICTED_DONORS_CACHE["result"]


@pytest.mark.s1
def test_k1_1_binding_restricted_donors():
    """K1.1 rerun (SPEC.md 8.8): restricted-donors proxy (top 64 ctx E cells by
    spike count) on top of the 8.6 sparse co-fire write. Pass or fail on
    criterion 2, as defined (the assembly), only; c2_recall_50_W is reported,
    not asserted."""
    k11, out = _k11_restricted_donors_result()

    assert out["hpc_encode_window"] is True
    assert out["sparse_write"] is True
    assert out["restricted_donors"] is True

    pins = out["engine_pins"]["encode_window"]
    on_a_minus = [0.06, 0.0, 0.0, 0.06, 0.0, 0.0, 0.06]
    on_hpc_e = [0.0, 1.0, 1.0, 0.0, 1.0, 1.0, 0.0]
    keys = ("before_A", "during_A", "during_A_end", "after_A", "during_B", "during_B_end", "after_B")
    for key, want in zip(keys, on_a_minus):
        assert pins["a_minus_hpc_e"][key] == pytest.approx(want), key
    for key, want in zip(keys, on_hpc_e):
        assert pins["mask_hpc_e_frac"][key] == pytest.approx(want), key
    for key in keys:
        assert pins["mask_other_frac"][key] == pytest.approx(0.0), key

    sw_a = out["sparse_write_A"]
    sw_b = out["sparse_write_B"]
    assert sw_a["W_size"] == 16
    assert sw_a["donors"] == 64
    assert sw_a["donor_k"] == 64
    assert sw_b["donor_k"] == 64
    assert sw_a["applied_inside_window"] is True
    assert sw_b["applied_inside_window"] is True
    assert sw_a["n_synapses_bumped"] > 0
    assert sw_a["mean_w_over_wmax_onto_W_after"] > sw_a["mean_w_over_wmax_onto_W_before"]

    assembly = out["assembly"]
    assembly_B = out["assembly_B"]
    cue = out["arms"]["cue"]
    full = out["arms"]["full"]
    none = out["arms"]["none"]
    synapses = out["synapses"]
    validity = out["validity"]
    criteria = out["criteria"]

    outcome_report = (
        f"hpc_encode_window={out['hpc_encode_window']} sparse_write={out['sparse_write']} "
        f"restricted_donors={out['restricted_donors']} "
        f"assembly size={assembly['size']} "
        f"W={sw_a['W']} W_overlap_with_assembly={sw_a.get('W_overlap_with_assembly')} "
        f"B size={assembly_B['size']} overlap_frac_of_A={assembly_B['overlap_frac_of_A']} "
        f"cue recall={cue['recall']} recall_W={cue.get('recall_W')} "
        f"cue hpc_e_rate_window_hz={cue.get('hpc_e_rate_window_hz')} "
        f"full recall={full['recall']} recall_W={full.get('recall_W')} "
        f"full hpc_e_rate_window_hz={full.get('hpc_e_rate_window_hz')} "
        f"none recall={none['recall']} recall_W={none.get('recall_W')} "
        f"none hpc_e_rate_window_hz={none.get('hpc_e_rate_window_hz')} "
        f"donor_to_W={synapses.get('donor_to_W')} "
        f"other_ctx_e_to_W={synapses.get('other_ctx_e_to_W')} "
        f"ctx_to_hpc_onto_hpc_e_not_W={synapses.get('ctx_to_hpc_onto_hpc_e_not_W')} "
        f"sparse_write_A={sw_a} "
        f"validity={validity} criteria={criteria}"
    )

    for name, ok in validity.items():
        assert ok is True, (
            f"K1.1 (restricted donors) INVALID experiment: validity[{name}] failed\n{outcome_report}"
        )

    # The donor groups partition the 8.6-comparable series (all ctx E -> W); donor_to_W
    # must be a strict subset of it, or the series has been silently redefined.
    onto_w = synapses["ctx_to_hpc_onto_W"]
    d2w = synapses["donor_to_W"]
    o2w = synapses["other_ctx_e_to_W"]
    assert d2w["n_before"] + o2w["n_before"] == onto_w["n_before"], outcome_report
    assert 0 < d2w["n_before"] < onto_w["n_before"], outcome_report
    assert sw_a["donors"] == k11.DONOR_K == sw_a["donor_k"], outcome_report
    assert sw_a["n_at_wmax_before"] <= sw_a["n_clamped"], outcome_report

    # Criterion 2 as defined (the assembly) only, per SPEC.md 8.8.
    assert out["criteria"]["c2_recall_50"], (
        "K1.1 (restricted donors) FAIL (c2 >= 80 % of the assembly within 50 ticks): "
        + outcome_report
    )
