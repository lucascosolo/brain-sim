"""K1.1 rerun, hpc encode window proxy (SPEC.md section 8.5).

Fast tests pin `Engine.encode_mask` (the scaling and rate-driven-elimination
exemptions it drives in `_slow_sweep` / `structural_update`), the new
`hpc_encode_window` context manager and `run_experiment(hpc_encode_window=)` kwarg,
and `main()`'s `--hpc-encode-window` flag. The single @pytest.mark.s1 test runs the
rerun (hpc_encode_window=True) and checks criterion 2 only, per the contract.
tests/k11_binding.py's additions and brainsim/engine.py's `encode_mask` do not
exist yet: every fast test that touches them is expected to fail today with
AttributeError/TypeError, not an ImportError in this file.
"""
import inspect
import sys

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


# --------------------------------------------------------------------------- #
# 1. Engine.encode_mask exists, all-False, engine never sets it
# --------------------------------------------------------------------------- #

def test_encode_mask_exists_all_false_bool_shape_n():
    eng = _fresh_engine()
    mask = eng.encode_mask
    assert mask.dtype == np.bool_
    assert mask.shape == (eng.net.n,)
    assert not mask.any()


def test_encode_mask_stays_all_false_after_stepping():
    eng = _fresh_engine()
    eng.step(2000)
    assert not eng.encode_mask.any()


# --------------------------------------------------------------------------- #
# 2. scaling exemption in _slow_sweep
# --------------------------------------------------------------------------- #

def test_slow_sweep_does_not_scale_used_synapses_onto_masked_cells():
    eng = _fresh_engine()
    net = eng.net
    eng.step(1500)  # nonzero counts since the last sweep base

    hpc_e_ids = _hpc_e_ids(eng)
    ctx = net.region_slice["ctx"]
    n_ctx_exc = params.REGIONS["ctx"]["n_exc"]
    ctx_e_ids = np.arange(ctx.start, ctx.start + n_ctx_exc, dtype=np.int64)

    # Force the scaling factor to its clip for every cell (rate far above target).
    net.rate[:] = 1000.0  # the sweep blends this with the real rate (EMA alpha 0.4) before computing the factor; 1000 keeps every cell at the clip after the blend
    counts = net.spike_count - eng._sweep_base
    pre_spiking = counts[net.pre] > 0

    alive = net.alive.copy()
    pre_exc = net.is_exc[net.pre]

    hpc_e_mask = np.zeros(net.n, bool)
    hpc_e_mask[hpc_e_ids] = True
    ctx_e_mask = np.zeros(net.n, bool)
    ctx_e_mask[ctx_e_ids] = True

    onto_hpc_e = np.flatnonzero(alive & pre_exc & pre_spiking & hpc_e_mask[net.post])
    onto_ctx_e = np.flatnonzero(alive & pre_exc & pre_spiking & ctx_e_mask[net.post])
    assert onto_hpc_e.size > 0, "test setup needs at least one used E->hpc_E synapse"
    assert onto_ctx_e.size > 0, "test setup needs at least one used E->ctx_E synapse"

    w_before_hpc = net.w[onto_hpc_e].copy()
    w_before_ctx = net.w[onto_ctx_e].copy()
    w_max_ctx = net.w_max_n[net.post[onto_ctx_e]].copy()

    pre_before, post_before = net.pre.copy(), net.post.copy()

    eng.encode_mask[hpc_e_ids] = True
    eng._slow_sweep()

    # "survived" = the slot is alive AND still holds the same synapse (the sweep's weight
    # prune frees slots that growth can reuse within the same call)
    def same_synapse(idx):
        return net.alive[idx] & (net.pre[idx] == pre_before[idx]) & (net.post[idx] == post_before[idx])

    survived_hpc = same_synapse(onto_hpc_e)
    assert survived_hpc.any(), "expected at least one masked-post synapse to survive the sweep"
    np.testing.assert_allclose(
        net.w[onto_hpc_e[survived_hpc]], w_before_hpc[survived_hpc], rtol=0, atol=1e-6,
        err_msg="masked-post used synapses must not be scaled by _slow_sweep",
    )

    survived_ctx = same_synapse(onto_ctx_e)
    assert survived_ctx.any(), "expected at least one unmasked-post synapse to survive the sweep"
    expected_ctx = np.clip(
        w_before_ctx[survived_ctx] * (1.0 - params.SCALING_CLIP), 0.0, w_max_ctx[survived_ctx]
    )
    np.testing.assert_allclose(
        net.w[onto_ctx_e[survived_ctx]], expected_ctx, rtol=1e-4, atol=1e-6,
        err_msg="unmasked-post used synapses must still be scaled by (1 - SCALING_CLIP)",
    )


# --------------------------------------------------------------------------- #
# 3. rate-driven excitatory-elimination exemption in structural_update
# --------------------------------------------------------------------------- #

def _died_pre_post(eng):
    pre_before = eng.net.pre.copy()
    post_before = eng.net.post.copy()
    is_exc = eng.net.is_exc.copy()
    born, died = eng.structural_update(np.full(eng.net.n, -1.0, np.float32))
    died = np.asarray(died)
    return pre_before[died], post_before[died], is_exc


def test_structural_update_masked_hpc_e_cells_spared_from_excitatory_prune():
    eng = _fresh_engine()
    eng.step(2000)
    hpc_e_ids = _hpc_e_ids(eng)
    eng.encode_mask[hpc_e_ids] = True

    hpc_e_set = set(hpc_e_ids.tolist())
    die_pre, die_post, is_exc = _died_pre_post(eng)
    exc_pre = is_exc[die_pre]
    onto_hpc_e = np.array([p in hpc_e_set for p in die_post.tolist()], bool)

    assert not np.any(exc_pre & onto_hpc_e), (
        "no excitatory-presynaptic synapse onto a masked hpc E cell may die "
        "from the rate-driven excitatory prune"
    )


def test_structural_update_unmasked_hpc_e_cells_still_pruned():
    eng = _fresh_engine()
    eng.step(2000)
    hpc_e_ids = _hpc_e_ids(eng)
    hpc_e_set = set(hpc_e_ids.tolist())

    die_pre, die_post, is_exc = _died_pre_post(eng)
    exc_pre = is_exc[die_pre]
    onto_hpc_e = np.array([p in hpc_e_set for p in die_post.tolist()], bool)

    assert np.any(exc_pre & onto_hpc_e), (
        "with the mask all False (today's plant) some excitatory-presynaptic "
        "synapses onto hpc E cells must still die under a forced above-target error"
    )


# --------------------------------------------------------------------------- #
# 4. hpc_encode_window context manager
# --------------------------------------------------------------------------- #

def test_hpc_encode_window_sets_mask_and_zeroes_a_minus_and_restores():
    k11 = _k11()
    eng = _fresh_engine()
    net = eng.net
    hpc_e_ids = _hpc_e_ids(eng)
    hpc = net.region_slice["hpc"]
    hpc_i_ids = np.arange(hpc.start + params.REGIONS["hpc"]["n_exc"], hpc.stop, dtype=np.int64)

    mask_before = eng.encode_mask.copy()
    a_minus_before = net.a_minus_n.copy()
    a_plus_before = net.a_plus_n.copy()

    with k11.hpc_encode_window(eng):
        mask_expected = np.zeros(net.n, bool)
        mask_expected[hpc_e_ids] = True
        assert np.array_equal(eng.encode_mask, mask_expected)
        assert np.all(net.a_minus_n[hpc_e_ids] == 0.0)
        # untouched during the window: a_plus everywhere, hpc I a_minus, other regions
        assert np.array_equal(net.a_plus_n, a_plus_before)
        assert np.array_equal(net.a_minus_n[hpc_i_ids], a_minus_before[hpc_i_ids])
        other_mask = np.ones(net.n, bool)
        other_mask[hpc.start:hpc.stop] = False
        assert np.array_equal(net.a_minus_n[other_mask], a_minus_before[other_mask])

    assert np.array_equal(eng.encode_mask, mask_before)
    assert np.array_equal(net.a_minus_n, a_minus_before)
    assert np.array_equal(net.a_plus_n, a_plus_before)


def test_hpc_encode_window_restores_on_exception():
    k11 = _k11()
    eng = _fresh_engine()
    net = eng.net
    mask_before = eng.encode_mask.copy()
    a_minus_before = net.a_minus_n.copy()

    with pytest.raises(RuntimeError):
        with k11.hpc_encode_window(eng):
            raise RuntimeError("boom")

    assert np.array_equal(eng.encode_mask, mask_before)
    assert np.array_equal(net.a_minus_n, a_minus_before)


# --------------------------------------------------------------------------- #
# 5. run_experiment kwarg default
# --------------------------------------------------------------------------- #

def test_run_experiment_hpc_encode_window_default_false():
    k11 = _k11()
    sig = inspect.signature(k11.run_experiment)
    assert sig.parameters["hpc_encode_window"].default is False


# --------------------------------------------------------------------------- #
# 6. main() flag parsing
# --------------------------------------------------------------------------- #

def test_main_parses_hpc_encode_window_flag(monkeypatch):
    k11 = _k11()
    calls = {}

    def fake_run_experiment(*args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs
        return {"stub": True}

    monkeypatch.setattr(k11, "run_experiment", fake_run_experiment)
    monkeypatch.setattr(k11, "report", lambda out, wall: None)
    monkeypatch.setattr(sys, "argv", ["k11_binding.py", "--hpc-encode-window"])

    k11.main()

    assert calls["kwargs"].get("hpc_encode_window") is True, (
        f"--hpc-encode-window must map to hpc_encode_window=True, got kwargs={calls['kwargs']} "
        f"args={calls['args']}"
    )


def test_main_defaults_hpc_encode_window_false_without_flag(monkeypatch):
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

    got = calls["kwargs"].get("hpc_encode_window", False)
    assert got is False, (
        f"without --hpc-encode-window, hpc_encode_window must default False, "
        f"got kwargs={calls['kwargs']}"
    )


def test_main_positional_seed_still_works(monkeypatch):
    k11 = _k11()
    calls = {}

    def fake_run_experiment(*args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs
        return {"stub": True}

    monkeypatch.setattr(k11, "run_experiment", fake_run_experiment)
    monkeypatch.setattr(k11, "report", lambda out, wall: None)
    monkeypatch.setattr(sys, "argv", ["k11_binding.py", "7"])

    k11.main()

    seed_arg = calls["args"][0] if calls["args"] else calls["kwargs"].get("seed")
    assert seed_arg == 7


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

_K11_ENCODE_WINDOW_CACHE = {}


def _k11_encode_window_result():
    if "result" not in _K11_ENCODE_WINDOW_CACHE:
        k11 = _k11()
        _K11_ENCODE_WINDOW_CACHE["module"] = k11
        _K11_ENCODE_WINDOW_CACHE["result"] = k11.run_experiment(hpc_encode_window=True)
    return _K11_ENCODE_WINDOW_CACHE["module"], _K11_ENCODE_WINDOW_CACHE["result"]


@pytest.mark.s1
def test_k1_1_binding_hpc_encode_window():
    """K1.1 rerun (SPEC.md 8.5): hpc encode window proxy. Pass or fail on
    criterion 2 only; criteria 1 and 3 are reported, not asserted (except that an
    invalid run fails outright, same as 8.2/8.3/8.4)."""
    k11, out = _k11_encode_window_result()

    assert out["hpc_encode_window"] is True

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

    assembly = out["assembly"]
    assembly_B = out["assembly_B"]
    cue = out["arms"]["cue"]
    full = out["arms"]["full"]
    none = out["arms"]["none"]
    synapses = out["synapses"]
    validity = out["validity"]
    criteria = out["criteria"]

    outcome_report = (
        f"hpc_encode_window={out['hpc_encode_window']} "
        f"assembly size={assembly['size']} "
        f"B size={assembly_B['size']} overlap_frac_of_A={assembly_B['overlap_frac_of_A']} "
        f"cue recall={cue['recall']} full recall={full['recall']} none recall={none['recall']} "
        f"ctx_to_hpc_onto_assembly n_before={synapses['ctx_to_hpc_onto_assembly']['n_before']} "
        f"n_after={synapses['ctx_to_hpc_onto_assembly']['n_after']} "
        f"mean_before={synapses['ctx_to_hpc_onto_assembly']['mean_before']} "
        f"mean_after={synapses['ctx_to_hpc_onto_assembly']['mean_after']} "
        f"hpc_hpc_within_assembly n_before={synapses['hpc_hpc_within_assembly']['n_before']} "
        f"n_after={synapses['hpc_hpc_within_assembly']['n_after']} "
        f"mean_before={synapses['hpc_hpc_within_assembly']['mean_before']} "
        f"mean_after={synapses['hpc_hpc_within_assembly']['mean_after']} "
        f"validity={validity} criteria={criteria}"
    )

    for name, ok in validity.items():
        assert ok is True, f"K1.1 (hpc encode window) INVALID experiment: validity[{name}] failed\n{outcome_report}"

    # Criterion 2 only, per SPEC.md 8.5 ("Pass or fail on criterion 2 only").
    assert out["criteria"]["c2_recall_50"], (
        "K1.1 (hpc encode window) FAIL (c2 >= 80 % of the assembly within 50 ticks): " + outcome_report
    )
