"""K1.1 rerun, encode window on W only (SPEC.md section 8.9).

Unit tests on `hpc_encode_window(eng, ids=)`, `identify_W`, `sparse_cofire_write(...,
W=)`, `_encode_window_pins_ok(pins, on, window_on_w=)`, `_window_on(m, window_on_w=)`,
the `run_experiment(window_on_w=)` guard/kwarg default, `main()`'s `--window-on-w`
flag, the digest guard, and the single @pytest.mark.s1 rerun wrapper (criterion 2
only, as defined). None of the `ids` kwarg, `identify_W`, the `W` kwarg on
`sparse_cofire_write`, or `window_on_w` exist yet: every fast test that touches
them is expected to fail today with AttributeError/TypeError, not an ImportError
in this file.
"""
import copy as copy_module
import inspect
import sys
import types

import numpy as np
import pytest

from brainsim import params
from brainsim.engine import Engine

import tests.k03_pairing as k03


def _k11():
    from tests import k11_binding as k11
    return k11


def _fresh_engine():
    return Engine(seed=1, params=k03._deepcopyable_params())


def _hpc_e_ids(eng):
    hpc = eng.net.region_slice["hpc"]
    n_exc = params.REGIONS["hpc"]["n_exc"]
    return np.arange(hpc.start, hpc.start + n_exc, dtype=np.int64)


def _some_non_hpc_e_id(eng):
    ctx = eng.net.region_slice["ctx"]
    return int(ctx.start)


# --------------------------------------------------------------------------- #
# 1. hpc_encode_window(eng, ids=...)
# --------------------------------------------------------------------------- #

def test_hpc_encode_window_ids_subset_masks_only_those_cells():
    k11 = _k11()
    eng = _fresh_engine()
    net = eng.net
    hpc_e_ids = _hpc_e_ids(eng)
    ids = hpc_e_ids[:5]  # a small subset ("W")
    other_hpc_e = np.setdiff1d(hpc_e_ids, ids)

    a_minus_before = net.a_minus_n.copy()
    mask_before = eng.encode_mask.copy()

    with k11.hpc_encode_window(eng, ids=ids):
        assert np.all(net.a_minus_n[ids] == 0.0)
        assert np.all(eng.encode_mask[ids])
        # every other hpc E cell keeps the plant a_minus and stays unmasked
        assert np.array_equal(net.a_minus_n[other_hpc_e], a_minus_before[other_hpc_e])
        assert not eng.encode_mask[other_hpc_e].any()

    assert np.array_equal(net.a_minus_n, a_minus_before)
    assert np.array_equal(eng.encode_mask, mask_before)


def test_hpc_encode_window_ids_restores_on_exception():
    k11 = _k11()
    eng = _fresh_engine()
    net = eng.net
    hpc_e_ids = _hpc_e_ids(eng)
    ids = hpc_e_ids[:5]
    a_minus_before = net.a_minus_n.copy()
    mask_before = eng.encode_mask.copy()

    with pytest.raises(RuntimeError):
        with k11.hpc_encode_window(eng, ids=ids):
            raise RuntimeError("boom")

    assert np.array_equal(net.a_minus_n, a_minus_before)
    assert np.array_equal(eng.encode_mask, mask_before)


def test_hpc_encode_window_ids_none_keeps_85_behaviour():
    k11 = _k11()
    eng = _fresh_engine()
    net = eng.net
    hpc_e_ids = _hpc_e_ids(eng)

    with k11.hpc_encode_window(eng, ids=None):
        assert np.all(net.a_minus_n[hpc_e_ids] == 0.0)
        assert np.all(eng.encode_mask[hpc_e_ids])


def test_hpc_encode_window_ids_non_hpc_e_cell_raises():
    k11 = _k11()
    eng = _fresh_engine()
    bad_id = _some_non_hpc_e_id(eng)

    with pytest.raises(AssertionError):
        with k11.hpc_encode_window(eng, ids=np.array([bad_id], dtype=np.int64)):
            pass


# --------------------------------------------------------------------------- #
# 2. identify_W: no-side-effect contract on a fake engine
# --------------------------------------------------------------------------- #

def _fake_id_pass_engine():
    eng = types.SimpleNamespace()
    eng.t = 122_000
    net = types.SimpleNamespace()
    net.n = 6
    net.w = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6], dtype=np.float64)
    net.spike_count = np.array([1, 2, 3, 4, 5, 6], dtype=np.int64)
    net.a_minus_n = np.array([0.06] * 6, dtype=np.float64)
    eng.net = net
    eng.encode_mask = np.zeros(6, dtype=bool)
    return eng


def test_identify_w_no_side_effects_and_record_shape(monkeypatch):
    k11 = _k11()
    eng = _fake_id_pass_engine()

    t_before = eng.t
    w_before = eng.net.w.copy()
    spike_count_before = eng.net.spike_count.copy()
    a_minus_before = eng.net.a_minus_n.copy()
    mask_before = eng.encode_mask.copy()

    real_deepcopy = copy_module.deepcopy
    deepcopy_calls = {"n": 0}

    def fake_deepcopy(obj, memo=None):
        deepcopy_calls["n"] += 1
        return real_deepcopy(obj) if memo is None else real_deepcopy(obj, memo)

    monkeypatch.setattr(k11.copy, "deepcopy", fake_deepcopy)

    volley_calls = []

    def stub_volley(eng_arg, pattern_id, ticks, pattern_ids):
        volley_calls.append(eng_arg)
        counts = np.array([0, 0, 10, 8, 3, 2], dtype=np.int64)
        hit = np.zeros(eng_arg.net.n, dtype=bool)
        return counts, hit

    monkeypatch.setattr(k11, "_present_recording_volley", stub_volley)

    hpc_e_ids = np.array([2, 3, 4, 5], dtype=np.int64)
    W, record = k11.identify_W(
        eng, pattern_id=0, ticks=2000,
        pattern_ids=np.array([0, 1, 2, 3], dtype=np.int64),
        hpc_e_ids=hpc_e_ids, k=2,
    )

    # top-2 of counts[2,3,4,5] = (10, 8, 3, 2) -> ids 2, 3
    assert list(W) == [2, 3]
    assert np.asarray(W).dtype == np.int64
    assert list(W) == sorted(W)

    assert set(record.keys()) == {
        "W", "k", "ticks", "copy_t_start", "copy_t_end",
        "mean_count_W", "mean_count_hpc_e_not_W",
    }
    assert record["k"] == 2
    assert record["ticks"] == 2000

    assert deepcopy_calls["n"] >= 1, "identify_W must deep-copy the engine"
    assert len(volley_calls) >= 1
    assert volley_calls[0] is not eng, "the pattern must be presented on the copy, not eng"

    # the real engine is byte-identical after the call
    assert eng.t == t_before
    assert np.array_equal(eng.net.w, w_before)
    assert np.array_equal(eng.net.spike_count, spike_count_before)
    assert np.array_equal(eng.net.a_minus_n, a_minus_before)
    assert np.array_equal(eng.encode_mask, mask_before)


# --------------------------------------------------------------------------- #
# 3. sparse_cofire_write(..., W=given)
# --------------------------------------------------------------------------- #

def _fake_net_distinct_wmax():
    # 6 cells: 0,1 ctx E; 2,3,4,5 hpc E. Distinct w_max_n per post cell.
    net = types.SimpleNamespace()
    net.n = 6
    net.is_exc = np.array([True, True, True, True, True, True])
    net.w_max_n = np.array([1.0, 1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
    # 0: donor(0) -> given-W(4), alive                bumped
    # 1: donor(0) -> given-W(5), alive                bumped
    # 2: donor(0) -> real-top-k member not in W(2), alive  untouched
    # 3: non-donor(1) -> given-W(4), alive            untouched (pre not a donor)
    # 4: hpc E(2) -> given-W(5), alive                untouched (pre not a donor)
    net.pre = np.array([0, 0, 0, 1, 2], dtype=np.int64)
    net.post = np.array([4, 5, 2, 4, 5], dtype=np.int64)
    net.w = np.array([1.00, 1.00, 1.00, 1.00, 1.00], dtype=np.float64)
    net.alive = np.array([True, True, True, True, True])
    return net


def _fake_counts_distinct():
    # id: 0=5 (donor ctx E), 1=0 (non-donor ctx E), 2=10, 3=8, 4=3, 5=2 (hpc E)
    return np.array([5, 0, 10, 8, 3, 2], dtype=np.int64)


def test_sparse_cofire_write_given_w_bumps_only_donor_to_given_w():
    k11 = _k11()
    net = _fake_net_distinct_wmax()
    counts = _fake_counts_distinct()
    hpc_e_ids = np.array([2, 3, 4, 5], dtype=np.int64)
    ctx_e_ids = np.array([0, 1], dtype=np.int64)
    given_W = np.array([5, 4], dtype=np.int64)  # unsorted on input

    rec = k11.sparse_cofire_write(
        net, counts, hpc_e_ids, ctx_e_ids, k=2, delta_frac=0.15, W=given_W)

    assert list(rec["W"]) == [4, 5]
    assert rec["W_source"] == "given"
    assert list(rec["real_top_k"]) == [2, 3]  # top-2 by counts, unaffected by given W
    assert rec["overlap_W_with_real_top_k"] == 0  # {4,5} n {2,3} = {}
    assert list(rec["donor_ids"]) == [0]

    expected_w = np.array([
        1.00 + 0.15 * 4.0,  # idx0: donor->4, w_max=4.0
        1.00 + 0.15 * 5.0,  # idx1: donor->5, w_max=5.0
        1.00,                # idx2: donor->2, real top-k but not in given W: untouched
        1.00,                # idx3: non-donor pre: untouched
        1.00,                # idx4: hpc E pre, not a donor: untouched
    ])
    np.testing.assert_allclose(net.w, expected_w, rtol=0, atol=1e-9)


def test_sparse_cofire_write_w_none_keeps_86_rule():
    k11 = _k11()
    net = _fake_net_distinct_wmax()
    counts = _fake_counts_distinct()
    hpc_e_ids = np.array([2, 3, 4, 5], dtype=np.int64)
    ctx_e_ids = np.array([0, 1], dtype=np.int64)

    rec = k11.sparse_cofire_write(
        net, counts, hpc_e_ids, ctx_e_ids, k=2, delta_frac=0.15, W=None)

    assert rec["W_source"] == "counts"
    assert list(rec["W"]) == [2, 3]
    assert list(rec["real_top_k"]) == list(rec["W"])
    assert rec["overlap_W_with_real_top_k"] == 2


def test_sparse_cofire_write_given_w_wrong_size_raises():
    k11 = _k11()
    net = _fake_net_distinct_wmax()
    counts = _fake_counts_distinct()
    hpc_e_ids = np.array([2, 3, 4, 5], dtype=np.int64)
    ctx_e_ids = np.array([0, 1], dtype=np.int64)

    with pytest.raises((AssertionError, ValueError)):
        k11.sparse_cofire_write(
            net, counts, hpc_e_ids, ctx_e_ids, k=2, delta_frac=0.15,
            W=np.array([4], dtype=np.int64))


def test_sparse_cofire_write_given_w_outside_hpc_e_ids_raises():
    k11 = _k11()
    net = _fake_net_distinct_wmax()
    counts = _fake_counts_distinct()
    hpc_e_ids = np.array([2, 3, 4, 5], dtype=np.int64)
    ctx_e_ids = np.array([0, 1], dtype=np.int64)

    with pytest.raises((AssertionError, ValueError)):
        k11.sparse_cofire_write(
            net, counts, hpc_e_ids, ctx_e_ids, k=2, delta_frac=0.15,
            W=np.array([4, 1], dtype=np.int64))  # 1 is ctx E, not hpc E


# --------------------------------------------------------------------------- #
# 4. _encode_window_pins_ok(pins, on, window_on_w=True) and _window_on(m, window_on_w=True)
# --------------------------------------------------------------------------- #

_MOMENTS = ("before_A", "during_A", "during_A_end", "after_A",
            "during_B", "during_B_end", "after_B")
_IN_WINDOW = ("during_A", "during_A_end", "during_B", "during_B_end")
_OUT_WINDOW = ("before_A", "after_A", "after_B")
_PLANT = 0.06
_HPC_E_FRAC = 16.0 / 320.0


def _passing_pins_window_on_w():
    a_minus_hpc_e = {m: (_PLANT if m in _OUT_WINDOW else 0.05) for m in _MOMENTS}
    mask_hpc_e_frac = {m: (_HPC_E_FRAC if m in _IN_WINDOW else 0.0) for m in _MOMENTS}
    mask_other_frac = {m: 0.0 for m in _MOMENTS}
    mask_W_frac = {m: (1.0 if m in _IN_WINDOW else 0.0) for m in _MOMENTS}
    a_minus_W = {m: (0.0 if m in _IN_WINDOW else _PLANT) for m in _MOMENTS}
    mask_hpc_e_not_W_frac = {m: 0.0 for m in _MOMENTS}
    a_minus_hpc_e_not_W = {m: _PLANT for m in _MOMENTS}
    return {
        "a_minus_hpc_e": a_minus_hpc_e,
        "mask_hpc_e_frac": mask_hpc_e_frac,
        "mask_other_frac": mask_other_frac,
        "mask_W_frac": mask_W_frac,
        "a_minus_W": a_minus_W,
        "mask_hpc_e_not_W_frac": mask_hpc_e_not_W_frac,
        "a_minus_hpc_e_not_W": a_minus_hpc_e_not_W,
    }


def test_encode_window_pins_ok_window_on_w_passing_shape():
    k11 = _k11()
    pins = _passing_pins_window_on_w()
    assert k11._encode_window_pins_ok(pins, True, window_on_w=True) is True


def test_encode_window_pins_ok_window_on_w_w_cell_unmasked_in_window_fails():
    k11 = _k11()
    pins = _passing_pins_window_on_w()
    pins["mask_W_frac"]["during_A"] = 15.0 / 16.0
    assert k11._encode_window_pins_ok(pins, True, window_on_w=True) is False


def test_encode_window_pins_ok_window_on_w_non_w_cell_masked_in_window_fails():
    k11 = _k11()
    pins = _passing_pins_window_on_w()
    pins["mask_hpc_e_not_W_frac"]["during_A_end"] = 1.0 / 304.0
    assert k11._encode_window_pins_ok(pins, True, window_on_w=True) is False


def test_encode_window_pins_ok_window_on_w_a_minus_hpc_e_not_w_zero_in_window_fails():
    k11 = _k11()
    pins = _passing_pins_window_on_w()
    pins["a_minus_hpc_e_not_W"]["during_A"] = 0.0
    assert k11._encode_window_pins_ok(pins, True, window_on_w=True) is False


def test_encode_window_pins_ok_window_on_w_mask_left_on_after_a_fails():
    k11 = _k11()
    pins = _passing_pins_window_on_w()
    pins["mask_W_frac"]["after_A"] = 1.0
    assert k11._encode_window_pins_ok(pins, True, window_on_w=True) is False


def test_window_on_window_on_w_true_only_when_all_three_hold():
    k11 = _k11()
    good = {"mask_W_frac": 1.0, "a_minus_W": 0.0, "mask_hpc_e_not_W_frac": 0.0}
    assert k11._window_on(good, window_on_w=True) is True

    bad_mask = dict(good, mask_W_frac=0.9375)
    assert k11._window_on(bad_mask, window_on_w=True) is False

    bad_a_minus = dict(good, a_minus_W=0.06)
    assert k11._window_on(bad_a_minus, window_on_w=True) is False

    bad_not_w = dict(good, mask_hpc_e_not_W_frac=0.01)
    assert k11._window_on(bad_not_w, window_on_w=True) is False


# --------------------------------------------------------------------------- #
# 5. run_experiment: window_on_w default and guard
# --------------------------------------------------------------------------- #

def test_run_experiment_window_on_w_default_false():
    k11 = _k11()
    sig = inspect.signature(k11.run_experiment)
    assert sig.parameters["window_on_w"].default is False


def test_window_on_w_without_sparse_write_raises_before_running(monkeypatch):
    k11 = _k11()

    def boom(*args, **kwargs):
        raise AssertionError("warm_engine must not be called when the guard should fire first")

    monkeypatch.setattr(k11.k03, "warm_engine", boom)

    with pytest.raises((AssertionError, ValueError)):
        k11.run_experiment(hpc_encode_window=True, sparse_write=False, window_on_w=True)


# --------------------------------------------------------------------------- #
# 6. main() flag parsing
# --------------------------------------------------------------------------- #

def test_main_parses_window_on_w_flag_implies_sparse_write_and_window(monkeypatch):
    k11 = _k11()
    calls = {}

    def fake_run_experiment(*args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs
        return {"stub": True}

    monkeypatch.setattr(k11, "run_experiment", fake_run_experiment)
    monkeypatch.setattr(k11, "report", lambda out, wall: None)
    monkeypatch.setattr(sys, "argv", ["k11_binding.py", "--window-on-w"])

    k11.main()

    assert calls["kwargs"].get("window_on_w") is True
    assert calls["kwargs"].get("sparse_write") is True
    assert calls["kwargs"].get("hpc_encode_window") is True


def test_main_defaults_window_on_w_false_without_flag(monkeypatch):
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

    assert calls["kwargs"].get("window_on_w", False) is False


def test_main_positional_seed_still_works_with_window_on_w_flag(monkeypatch):
    k11 = _k11()
    calls = {}

    def fake_run_experiment(*args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs
        return {"stub": True}

    monkeypatch.setattr(k11, "run_experiment", fake_run_experiment)
    monkeypatch.setattr(k11, "report", lambda out, wall: None)
    monkeypatch.setattr(sys, "argv", ["k11_binding.py", "--window-on-w", "7"])

    k11.main()

    seed_arg = calls["args"][0] if calls["args"] else calls["kwargs"].get("seed")
    assert seed_arg == 7
    assert calls["kwargs"].get("window_on_w") is True


# --------------------------------------------------------------------------- #
# 7. default digest unchanged (byte-identity guard; already green)
# --------------------------------------------------------------------------- #

def test_default_engine_digest_unchanged():
    from tests.test_engine_determinism import run_schedule, _digest, REFERENCE_DIGEST
    e = run_schedule()
    assert _digest(e) == REFERENCE_DIGEST


# --------------------------------------------------------------------------- #
# s1: the rerun itself, criterion 2 only
# --------------------------------------------------------------------------- #

_K11_WINDOW_ON_W_CACHE = {}


def _k11_window_on_w_result():
    if "result" not in _K11_WINDOW_ON_W_CACHE:
        k11 = _k11()
        _K11_WINDOW_ON_W_CACHE["module"] = k11
        _K11_WINDOW_ON_W_CACHE["result"] = k11.run_experiment(
            1, hpc_encode_window=True, sparse_write=True, window_on_w=True)
    return _K11_WINDOW_ON_W_CACHE["module"], _K11_WINDOW_ON_W_CACHE["result"]


@pytest.mark.s1
def test_k1_1_binding_window_on_w():
    """K1.1 rerun (SPEC.md 8.9): encode window on W only, on top of the 8.6
    sparse co-fire write. Pass or fail on criterion 2 only, as defined; c2 is
    reported against both the assembly and W but asserted on the assembly per
    the 8.5/8.6 precedent (SPEC.md: "Pass or fail on criterion 2 only, as
    defined")."""
    k11, out = _k11_window_on_w_result()

    assert out["window_on_w"] is True
    assert out["hpc_encode_window"] is True
    assert out["sparse_write"] is True

    ew = out["engine_pins"]["encode_window"]
    assert ew["mask_hpc_e_frac"]["during_A"] == pytest.approx(16.0 / 320.0)
    assert ew["mask_hpc_e_frac"]["during_A_end"] == pytest.approx(16.0 / 320.0)
    assert ew["mask_hpc_e_frac"]["before_A"] == pytest.approx(0.0)
    assert ew["mask_hpc_e_frac"]["after_A"] == pytest.approx(0.0)

    id_pass_A = out["id_pass_A"]
    id_pass_B = out["id_pass_B"]
    sw_a = out["sparse_write_A"]
    sw_b = out["sparse_write_B"]

    assert sw_a["applied_inside_window"] is True
    assert sw_b["applied_inside_window"] is True
    assert list(sw_a["W"]) == list(id_pass_A["W"])
    assert sw_a["W_source"] == "given"
    assert 0 <= sw_a["overlap_W_with_real_top_k"] <= 16

    assembly = out["assembly"]
    assembly_B = out["assembly_B"]
    cue = out["arms"]["cue"]
    full = out["arms"]["full"]
    none = out["arms"]["none"]
    synapses = out["synapses"]
    validity = out["validity"]
    criteria = out["criteria"]

    outcome_report = (
        f"window_on_w={out['window_on_w']} assembly size={assembly['size']} "
        f"W={sw_a['W']} id_pass_A_overlap_with_real_top_16={id_pass_A.get('mean_count_W')} "
        f"B size={assembly_B['size']} overlap_frac_of_A={assembly_B['overlap_frac_of_A']} "
        f"cue recall={cue['recall']} recall_W={cue.get('recall_W')} "
        f"hpc_e_rate_window_hz={cue.get('hpc_e_rate_window_hz')} "
        f"full recall={full['recall']} recall_W={full.get('recall_W')} "
        f"hpc_e_rate_window_hz={full.get('hpc_e_rate_window_hz')} "
        f"none recall={none['recall']} recall_W={none.get('recall_W')} "
        f"hpc_e_rate_window_hz={none.get('hpc_e_rate_window_hz')} "
        f"donor_to_W={synapses.get('donor_to_W')} "
        f"other_ctx_e_to_W={synapses.get('other_ctx_e_to_W')} "
        f"ctx_to_hpc_onto_hpc_e_not_W={synapses.get('ctx_to_hpc_onto_hpc_e_not_W')} "
        f"hpc_hpc_within_W={synapses.get('hpc_hpc_within_W')} "
        f"sparse_write_A={sw_a} "
        f"validity={validity} criteria={criteria}"
    )

    for name, ok in validity.items():
        assert ok is True, f"K1.1 (window on W) INVALID experiment: validity[{name}] failed\n{outcome_report}"

    assert out["criteria"]["c2_recall_50"], (
        "K1.1 (window on W) FAIL (c2 >= 80 % of the assembly within 50 ticks): " + outcome_report
    )
