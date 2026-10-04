"""K1.1 rerun, sparse co-fire write proxy (SPEC.md section 8.6).

Unit tests on `select_winners` and `sparse_cofire_write` (pure / fake-net), the
`run_experiment(sparse_write=)` guard and kwarg default, `main()`'s
`--sparse-write` flag, the digest guard, and the single @pytest.mark.s1 rerun
wrapper (criterion 2, assembly-defined, only). None of `k11.SPARSE_K`,
`k11.SPARSE_DELTA_FRAC`, `k11.select_winners`, `k11.sparse_cofire_write`, or the
`sparse_write` kwarg/flag exist yet: every fast test that touches them is
expected to fail today with AttributeError/TypeError, not an ImportError in
this file.
"""
import inspect
import sys
import types

import numpy as np
import pytest


def _k11():
    from tests import k11_binding as k11
    return k11


# --------------------------------------------------------------------------- #
# 1. constants
# --------------------------------------------------------------------------- #

def test_sparse_k_constant():
    k11 = _k11()
    assert k11.SPARSE_K == 16


def test_sparse_delta_frac_constant():
    k11 = _k11()
    assert k11.SPARSE_DELTA_FRAC == 0.15


# --------------------------------------------------------------------------- #
# 2. select_winners (pure)
# --------------------------------------------------------------------------- #

def test_select_winners_top_k_sorted():
    k11 = _k11()
    counts = np.zeros(10, dtype=np.int64)
    counts[0] = 1
    counts[2] = 5
    counts[3] = 9
    counts[4] = 2
    hpc_e_ids = np.array([0, 2, 3, 4], dtype=np.int64)
    w = k11.select_winners(counts, hpc_e_ids, 2)
    assert list(w) == [2, 3]
    assert np.asarray(w).dtype == np.int64
    assert list(w) == sorted(w)


def test_select_winners_tie_broken_by_lower_id():
    k11 = _k11()
    counts = np.zeros(10, dtype=np.int64)
    counts[0] = 5
    counts[2] = 5
    counts[3] = 9
    counts[4] = 1
    hpc_e_ids = np.array([0, 2, 3, 4], dtype=np.int64)
    w = k11.select_winners(counts, hpc_e_ids, 2)
    # id3 (9) is the clear top; the tie between id0 and id2 (both 5) for the
    # second slot must break to the lower id.
    assert list(w) == [0, 3]


def test_select_winners_k_larger_than_candidates_returns_all_sorted():
    k11 = _k11()
    counts = np.zeros(10, dtype=np.int64)
    counts[3] = 9
    counts[0] = 5
    counts[2] = 1
    hpc_e_ids = np.array([3, 0, 2], dtype=np.int64)  # unsorted input
    w = k11.select_winners(counts, hpc_e_ids, 5)
    assert list(w) == [0, 2, 3]


# --------------------------------------------------------------------------- #
# 3. sparse_cofire_write on a tiny hand-built fake net
# --------------------------------------------------------------------------- #

def _fake_net():
    # 6 cells: 0,1 ctx E; 2,3,4 hpc E; 5 hpc I.
    net = types.SimpleNamespace()
    net.n = 6
    net.is_exc = np.array([True, True, True, True, True, False])
    net.w_max_n = np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.0], dtype=np.float64)
    # 8 synapses, indices 0..7:
    #  0: donor(0) -> W(2), alive           bumped
    #  1: donor(0) -> W(3), alive, at wmax  bumped, clamped
    #  2: non-spiking ctx(1) -> W(2), alive untouched (pre not a donor)
    #  3: donor(0) -> non-W hpc E(4), alive untouched
    #  4: donor(0) -> W(2), dead            untouched
    #  5: hpc E(2) -> W(3), alive           untouched (pre not a donor)
    #  6: donor(0) -> hpc I(5), alive       untouched
    #  7: donor(0) -> W(3), alive           bumped
    net.pre = np.array([0, 0, 1, 0, 0, 2, 0, 0], dtype=np.int64)
    net.post = np.array([2, 3, 2, 4, 2, 3, 5, 3], dtype=np.int64)
    net.w = np.array([0.50, 1.00, 0.30, 0.20, 0.60, 0.40, 0.70, 0.10], dtype=np.float64)
    net.alive = np.array([True, True, True, True, False, True, True, True])
    return net


def _fake_counts():
    # counts[id]: 0=5 (donor, ctx E), 1=0 (non-donor, ctx E), 2=10, 3=8, 4=1 (hpc E), 5=0 (hpc I)
    return np.array([5, 0, 10, 8, 1, 0], dtype=np.int64)


def test_sparse_cofire_write_weights_and_record():
    k11 = _k11()
    net = _fake_net()
    counts = _fake_counts()
    hpc_e_ids = np.array([2, 3, 4], dtype=np.int64)
    ctx_e_ids = np.array([0, 1], dtype=np.int64)

    pre_before = net.pre.copy()
    post_before = net.post.copy()
    alive_before = net.alive.copy()

    rec = k11.sparse_cofire_write(net, counts, hpc_e_ids, ctx_e_ids, k=2, delta_frac=0.15)

    # winners: top 2 of hpc E by count -> ids 2 (10) and 3 (8)
    assert list(rec["W"]) == [2, 3]
    assert rec["W_size"] == 2
    # donors: ctx E ids with counts > 0 -> just id 0
    assert rec["donors"] == 1

    expected_w = np.array([0.65, 1.00, 0.30, 0.20, 0.60, 0.40, 0.70, 0.25])
    np.testing.assert_allclose(net.w, expected_w, rtol=0, atol=1e-9)

    assert rec["n_synapses_bumped"] == 3   # idx 0, 1, 7
    assert rec["n_clamped"] == 1           # idx 1 only

    # means over the bumped set (idx 0, 1, 7), w/w_max_n[post], before and after
    before_mean = (0.50 + 1.00 + 0.10) / 3.0
    after_mean = (0.65 + 1.00 + 0.25) / 3.0
    assert rec["mean_w_over_wmax_onto_W_before"] == pytest.approx(before_mean)
    assert rec["mean_w_over_wmax_onto_W_after"] == pytest.approx(after_mean)
    assert rec["mean_w_over_wmax_onto_W_after"] > rec["mean_w_over_wmax_onto_W_before"]

    # topology and identity arrays untouched: only w changed
    assert np.array_equal(net.pre, pre_before)
    assert np.array_equal(net.post, post_before)
    assert np.array_equal(net.alive, alive_before)


def test_sparse_cofire_write_does_not_touch_non_matching_synapses():
    k11 = _k11()
    net = _fake_net()
    counts = _fake_counts()
    hpc_e_ids = np.array([2, 3, 4], dtype=np.int64)
    ctx_e_ids = np.array([0, 1], dtype=np.int64)

    k11.sparse_cofire_write(net, counts, hpc_e_ids, ctx_e_ids, k=2, delta_frac=0.15)

    # idx 2 (non-spiking ctx -> W), idx 3 (donor -> non-W hpc E), idx 4 (dead),
    # idx 5 (hpc E pre, not a donor), idx 6 (donor -> hpc I): all untouched.
    for idx, expected in ((2, 0.30), (3, 0.20), (4, 0.60), (5, 0.40), (6, 0.70)):
        assert net.w[idx] == pytest.approx(expected), f"synapse {idx} must be untouched"


# --------------------------------------------------------------------------- #
# 4. run_experiment: kwarg default and the guard
# --------------------------------------------------------------------------- #

def test_run_experiment_sparse_write_default_false():
    k11 = _k11()
    sig = inspect.signature(k11.run_experiment)
    assert sig.parameters["sparse_write"].default is False


def test_sparse_write_without_window_raises_before_running(monkeypatch):
    k11 = _k11()

    def boom(*args, **kwargs):
        raise AssertionError("warm_engine must not be called when the guard should fire first")

    monkeypatch.setattr(k11.k03, "warm_engine", boom)

    with pytest.raises((AssertionError, ValueError)):
        k11.run_experiment(hpc_encode_window=False, sparse_write=True)


# --------------------------------------------------------------------------- #
# 5. main() flag parsing
# --------------------------------------------------------------------------- #

def test_main_parses_sparse_write_flag_implies_window(monkeypatch):
    k11 = _k11()
    calls = {}

    def fake_run_experiment(*args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs
        return {"stub": True}

    monkeypatch.setattr(k11, "run_experiment", fake_run_experiment)
    monkeypatch.setattr(k11, "report", lambda out, wall: None)
    monkeypatch.setattr(sys, "argv", ["k11_binding.py", "--sparse-write"])

    k11.main()

    assert calls["kwargs"].get("sparse_write") is True, (
        f"--sparse-write must map to sparse_write=True, got kwargs={calls['kwargs']}"
    )
    assert calls["kwargs"].get("hpc_encode_window") is True, (
        f"--sparse-write must imply hpc_encode_window=True, got kwargs={calls['kwargs']}"
    )


def test_main_defaults_sparse_write_false_without_flag(monkeypatch):
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

    got_sparse = calls["kwargs"].get("sparse_write", False)
    got_window = calls["kwargs"].get("hpc_encode_window", False)
    assert got_sparse is False
    assert got_window is False


# --------------------------------------------------------------------------- #
# 6. default digest unchanged (byte-identity guard; already green)
# --------------------------------------------------------------------------- #

def test_default_engine_digest_unchanged():
    from tests.test_engine_determinism import run_schedule, _digest, REFERENCE_DIGEST
    e = run_schedule()
    assert _digest(e) == REFERENCE_DIGEST


# --------------------------------------------------------------------------- #
# s1: the rerun itself, criterion 2 (assembly-defined) only
# --------------------------------------------------------------------------- #

_K11_SPARSE_WRITE_CACHE = {}


def _k11_sparse_write_result():
    if "result" not in _K11_SPARSE_WRITE_CACHE:
        k11 = _k11()
        _K11_SPARSE_WRITE_CACHE["module"] = k11
        _K11_SPARSE_WRITE_CACHE["result"] = k11.run_experiment(
            hpc_encode_window=True, sparse_write=True)
    return _K11_SPARSE_WRITE_CACHE["module"], _K11_SPARSE_WRITE_CACHE["result"]


@pytest.mark.s1
def test_k1_1_binding_sparse_write():
    """K1.1 rerun (SPEC.md 8.6): sparse co-fire write proxy on top of the 8.5
    encode window. Pass or fail on criterion 2, as defined (the assembly), only;
    c2_recall_50_W is reported, not asserted."""
    k11, out = _k11_sparse_write_result()

    assert out["hpc_encode_window"] is True
    assert out["sparse_write"] is True

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
        f"assembly size={assembly['size']} "
        f"W={sw_a['W']} W_overlap_with_assembly={sw_a.get('W_overlap_with_assembly')} "
        f"B size={assembly_B['size']} overlap_frac_of_A={assembly_B['overlap_frac_of_A']} "
        f"cue recall={cue['recall']} recall_W={cue.get('recall_W')} "
        f"full recall={full['recall']} recall_W={full.get('recall_W')} "
        f"none recall={none['recall']} recall_W={none.get('recall_W')} "
        f"ctx_to_hpc_onto_W={synapses.get('ctx_to_hpc_onto_W')} "
        f"ctx_to_hpc_onto_hpc_e_not_W={synapses.get('ctx_to_hpc_onto_hpc_e_not_W')} "
        f"sparse_write_A={sw_a} "
        f"validity={validity} criteria={criteria}"
    )

    for name, ok in validity.items():
        assert ok is True, f"K1.1 (sparse write) INVALID experiment: validity[{name}] failed\n{outcome_report}"

    # Criterion 2 as defined (the assembly) only, per SPEC.md 8.6.
    assert out["criteria"]["c2_recall_50"], (
        "K1.1 (sparse write) FAIL (c2 >= 80 % of the assembly within 50 ticks): " + outcome_report
    )
