"""K1.1 rerun, hpc afferent-elimination exemption (SPEC.md section 8.3).

Fast tests pin the new `struct_prune_exc` plant flag (params, engine mask, driver
context manager and flag parsing) plus the byte-identity guard on the unchanged
default. The single @pytest.mark.s1 test runs the rerun (hpc_prune_exc=False) and
checks criterion 2 only, per the contract. tests/k11_binding.py's additions (the
`hpc_struct_prune_exc` context manager and the `hpc_prune_exc=` kwarg of
`run_experiment`) do not exist yet: every fast test that touches them is expected
to fail today with AttributeError/TypeError, not an ImportError in this file.
"""
import copy
import sys
import types

import numpy as np
import pytest

from brainsim import params
from brainsim.engine import Engine


def _k11():
    from tests import k11_binding as k11
    return k11


def _ns_with_flag(hpc_flag):
    """API.md's exact recipe: a SimpleNamespace of every UPPER_CASE module attr,
    with REGIONS deep-copied (params.REGIONS is otherwise shared by reference,
    per tests/k03_pairing._deepcopyable_params) so mutating the copy's hpc entry
    cannot leak back into the real module."""
    ns = types.SimpleNamespace(**{k: getattr(params, k) for k in dir(params) if k.isupper()})
    ns.REGIONS = copy.deepcopy(params.REGIONS)
    ns.REGIONS["hpc"]["struct_prune_exc"] = hpc_flag
    return ns


def _died_pre_post(eng):
    """Snapshot net.pre/net.post BEFORE the call (structural_update's kill_synapses
    runs inside it), force every cell "above target", and return (died_pre, died_post)
    read from the pre-call snapshot indexed by the returned died array."""
    pre_before = eng.net.pre.copy()
    post_before = eng.net.post.copy()
    is_exc = eng.net.is_exc.copy()
    born, died = eng.structural_update(np.full(eng.net.n, -1.0, np.float32))
    died = np.asarray(died)
    die_pre = pre_before[died]
    die_post = post_before[died]
    return die_pre, die_post, is_exc


def _region_of(idx, net):
    for name, sl in net.region_slice.items():
        if sl.start <= idx < sl.stop:
            return name
    return None


# --------------------------------------------------------------------------- #
# 1. params pin
# --------------------------------------------------------------------------- #

def test_regions_all_have_struct_prune_exc_true():
    for name, cfg in params.REGIONS.items():
        assert cfg.get("struct_prune_exc") is True, (
            f"REGIONS[{name!r}] must default struct_prune_exc=True (today's plant)"
        )


# --------------------------------------------------------------------------- #
# 2. default digest unchanged (byte-identity guard; already green)
# --------------------------------------------------------------------------- #

def test_default_engine_digest_unchanged():
    from tests.test_engine_determinism import run_schedule, _digest, REFERENCE_DIGEST
    e = run_schedule()
    assert _digest(e) == REFERENCE_DIGEST


# --------------------------------------------------------------------------- #
# 3/4. structural_update mask
# --------------------------------------------------------------------------- #

def test_structural_update_mask_hpc_flag_false_spares_hpc_excitatory():
    eng = Engine(seed=1, params=_ns_with_flag(False))
    eng.step(2000)
    die_pre, die_post, is_exc = _died_pre_post(eng)

    exc_pre = is_exc[die_pre]
    assert exc_pre.any(), "expected at least some excitatory-presynaptic deaths"

    hpc_sl = eng.net.region_slice["hpc"]
    to_hpc = (die_post >= hpc_sl.start) & (die_post < hpc_sl.stop)
    assert not (exc_pre & to_hpc).any(), (
        "with hpc struct_prune_exc=False, no excitatory synapse onto hpc should be "
        "rate-driven-pruned"
    )

    ctx_sl = eng.net.region_slice["ctx"]
    to_ctx = (die_post >= ctx_sl.start) & (die_post < ctx_sl.stop)
    assert (exc_pre & to_ctx).any(), (
        "the rate-driven excitatory prune should still run in ctx (flag True there)"
    )


def test_structural_update_mask_hpc_flag_true_still_prunes_hpc_excitatory():
    eng = Engine(seed=1, params=_ns_with_flag(True))
    eng.step(2000)
    die_pre, die_post, is_exc = _died_pre_post(eng)

    exc_pre = is_exc[die_pre]
    hpc_sl = eng.net.region_slice["hpc"]
    to_hpc = (die_post >= hpc_sl.start) & (die_post < hpc_sl.stop)
    assert (exc_pre & to_hpc).any(), (
        "with hpc struct_prune_exc=True (today's plant), excitatory synapses onto "
        "hpc should still be rate-driven-pruned under a forced above-target error"
    )


def test_engine_reads_flag_only_at_construction():
    """Engine.__init__ reads REGIONS at construction only; flipping the flag after
    construction must have no effect (API.md 'Facts you need')."""
    ns = _ns_with_flag(True)
    eng = Engine(seed=1, params=ns)
    ns.REGIONS["hpc"]["struct_prune_exc"] = False  # too late, post-construction
    eng.step(2000)
    die_pre, die_post, is_exc = _died_pre_post(eng)
    exc_pre = is_exc[die_pre]
    hpc_sl = eng.net.region_slice["hpc"]
    to_hpc = (die_post >= hpc_sl.start) & (die_post < hpc_sl.stop)
    assert (exc_pre & to_hpc).any(), (
        "the engine must have latched the True flag at construction, ignoring the "
        "post-construction flip to False"
    )


# --------------------------------------------------------------------------- #
# 5. context manager
# --------------------------------------------------------------------------- #

def test_hpc_struct_prune_exc_context_manager_sets_and_restores():
    k11 = _k11()
    assert params.REGIONS["hpc"]["struct_prune_exc"] is True
    with k11.hpc_struct_prune_exc(False):
        assert params.REGIONS["hpc"]["struct_prune_exc"] is False
    assert params.REGIONS["hpc"]["struct_prune_exc"] is True


def test_hpc_struct_prune_exc_context_manager_restores_on_exception():
    k11 = _k11()
    assert params.REGIONS["hpc"]["struct_prune_exc"] is True
    with pytest.raises(RuntimeError):
        with k11.hpc_struct_prune_exc(False):
            assert params.REGIONS["hpc"]["struct_prune_exc"] is False
            raise RuntimeError("boom")
    assert params.REGIONS["hpc"]["struct_prune_exc"] is True


# --------------------------------------------------------------------------- #
# 6. main() flag parsing
# --------------------------------------------------------------------------- #

def test_main_parses_hpc_prune_off_flag(monkeypatch):
    k11 = _k11()
    calls = {}

    def fake_run_experiment(*args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs
        return {"stub": True}

    def fake_report(out, wall):
        pass

    monkeypatch.setattr(k11, "run_experiment", fake_run_experiment)
    monkeypatch.setattr(k11, "report", fake_report)
    monkeypatch.setattr(sys, "argv", ["k11_binding.py", "--hpc-prune-off"])

    k11.main()

    assert calls["kwargs"].get("hpc_prune_exc") is False, (
        f"--hpc-prune-off must map to hpc_prune_exc=False, got kwargs={calls['kwargs']} "
        f"args={calls['args']}"
    )


def test_main_defaults_hpc_prune_exc_true_without_flag(monkeypatch):
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

    got = calls["kwargs"].get("hpc_prune_exc", True)
    assert got is True, (
        f"without --hpc-prune-off, hpc_prune_exc must default True, got kwargs={calls['kwargs']}"
    )


# --------------------------------------------------------------------------- #
# s1: the rerun itself, criterion 2 only
# --------------------------------------------------------------------------- #

_K11_PRUNE_OFF_CACHE = {}


def _k11_prune_off_result():
    if "result" not in _K11_PRUNE_OFF_CACHE:
        k11 = _k11()
        _K11_PRUNE_OFF_CACHE["module"] = k11
        _K11_PRUNE_OFF_CACHE["result"] = k11.run_experiment(hpc_prune_exc=False)
    return _K11_PRUNE_OFF_CACHE["module"], _K11_PRUNE_OFF_CACHE["result"]


@pytest.mark.s1
def test_k1_1_binding_hpc_prune_off():
    """K1.1 rerun (SPEC.md 8.3): the afferent-elimination exemption on hpc. Pass or
    fail on criterion 2 only; criteria 1 and 3 and validity are reported, not
    asserted (except that an invalid run fails outright, same as 8.2)."""
    k11, out = _k11_prune_off_result()

    assert out["hpc_prune_exc"] is False
    assert out["engine_pins"]["struct_prune_exc"] == {"sense": True, "ctx": True, "hpc": False}
    # the module-level default must be restored after the run, exception or not.
    assert params.REGIONS["hpc"]["struct_prune_exc"] is True

    assembly = out["assembly"]
    assembly_B = out["assembly_B"]
    cue = out["arms"]["cue"]
    full = out["arms"]["full"]
    none = out["arms"]["none"]
    synapses = out["synapses"]
    validity = out["validity"]
    criteria = out["criteria"]

    outcome_report = (
        f"hpc_prune_exc={out['hpc_prune_exc']} "
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
        assert ok is True, f"K1.1 (hpc prune off) INVALID experiment: validity[{name}] failed\n{outcome_report}"

    # Criterion 2 only, per SPEC.md 8.3 ("Pass or fail on criterion 2 only").
    assert out["criteria"]["c2_recall_50"], (
        "K1.1 (hpc prune off) FAIL (c2 >= 80 % of the assembly within 50 ticks): " + outcome_report
    )
