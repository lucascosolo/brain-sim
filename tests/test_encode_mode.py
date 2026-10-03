"""Encode-mode: one labelled plant schedule (SPEC.md section 8.12), branch
`encode-mode`.

Covers: the four ``ENCODE_*`` constants in `brainsim/params.py`; the new
`brainsim/encode.py` pure-function module; the `Engine` attributes
`encode_mode`/`encode_stage`/`encode_W`/`encode_record` and the schedule that
`present()` arms while the mode is on; the `encode` frame key and the four
`encode_*` config keys in `brainsim/telemetry.py`; the `half_patterns` layout
key; the worker's `{"cmd": "encode"}` command; and text-level checks that
`ui/index.html` and `ui/app.js` carry the new panel without hard-coding any
W id.

None of `brainsim.encode`, `Engine.encode_mode`/`encode_stage`/`present`
arming/`_encode_tick`, the `encode` frame/config/layout keys, or the worker's
`encode` command exist yet: every test below is expected to fail today with
ImportError, AttributeError, KeyError or AssertionError, not a collection
error in this file (`brainsim.encode` is imported lazily inside tests).
"""
import re

import numpy as np
import pytest

from brainsim import params, telemetry
from brainsim.engine import Engine

import tests.k03_pairing as k03


def _encode():
    from brainsim import encode
    return encode


def _fresh_engine():
    return Engine(seed=1, params=k03._deepcopyable_params())


def _hpc_e_ids(eng):
    hpc = eng.net.region_slice["hpc"]
    n_exc = params.REGIONS["hpc"]["n_exc"]
    return np.arange(hpc.start, hpc.start + n_exc, dtype=np.int64)


def _ctx_e_ids(eng):
    ctx = eng.net.region_slice["ctx"]
    n_exc = params.REGIONS["ctx"]["n_exc"]
    return np.arange(ctx.start, ctx.start + n_exc, dtype=np.int64)


# --------------------------------------------------------------------------- #
# 1. params constants
# --------------------------------------------------------------------------- #

def test_encode_params_constants_have_fixed_values():
    assert params.ENCODE_K == 16
    assert params.ENCODE_DELTA_FRAC == 0.15
    assert params.ENCODE_RECURRENT_DELTA_FRAC == 0.05
    assert params.ENCODE_GRACE_TICKS == 1000


# --------------------------------------------------------------------------- #
# 2. Engine defaults
# --------------------------------------------------------------------------- #

def test_engine_encode_defaults():
    eng = _fresh_engine()
    assert eng.encode_mode is False
    assert eng.encode_stage == "off"
    assert isinstance(eng.encode_W, np.ndarray) and eng.encode_W.size == 0
    assert eng.encode_record is None


# --------------------------------------------------------------------------- #
# 3. mode off -> plain path
# --------------------------------------------------------------------------- #

def test_present_mode_off_is_plain_path():
    eng = _fresh_engine()
    mask_before = eng.encode_mask.copy()
    rec = eng.present(0, 30)
    assert rec is not None and rec["n_cells"] > 0
    assert eng.encode_record is None
    assert np.array_equal(eng.encode_mask, mask_before)
    assert not eng.encode_mask.any()


# --------------------------------------------------------------------------- #
# 4. mode on + sense_gated -> present returns None, arms nothing
# --------------------------------------------------------------------------- #

def test_present_mode_on_sense_gated_returns_none_arms_nothing():
    eng = _fresh_engine()
    eng.encode_mode = True
    eng.set_sleep(True)
    rec = eng.present(0, 30)
    assert rec is None
    assert eng.encode_stage == "idle"
    assert eng.encode_record is None
    assert eng.encode_W.size == 0
    assert not eng.encode_mask.any()


# --------------------------------------------------------------------------- #
# 5. mode on, fresh engine, present() arms the schedule
# --------------------------------------------------------------------------- #

def test_present_mode_on_arms_present_stage_and_mask_on_w_only():
    encode = _encode()
    eng = _fresh_engine()
    eng.encode_mode = True
    rec = eng.present(0, 30)
    assert rec is not None
    assert eng.encode_stage == "present"
    assert eng.encode_W.size == 16
    assert np.array_equal(np.sort(eng.encode_W), eng.encode_W)
    assert np.isin(eng.encode_W, encode.hpc_e_ids(eng.net)).all()

    mask_ids = np.flatnonzero(eng.encode_mask)
    assert set(mask_ids.tolist()) == set(eng.encode_W.tolist())


def test_present_mode_on_a_minus_zero_on_w_unchanged_elsewhere():
    eng = _fresh_engine()
    a_minus_before = eng.net.a_minus_n.copy()
    eng.encode_mode = True
    eng.present(0, 30)
    assert np.all(eng.net.a_minus_n[eng.encode_W] == 0.0)
    other = np.setdiff1d(np.arange(eng.net.n), eng.encode_W)
    assert np.array_equal(eng.net.a_minus_n[other], a_minus_before[other])


def test_present_mode_on_encode_record_id_pass_shape():
    eng = _fresh_engine()
    eng.encode_mode = True
    eng.present(0, 30)
    rec = eng.encode_record
    assert rec is not None
    assert rec["done"] is False
    assert rec["W"] == sorted(int(x) for x in eng.encode_W)
    assert rec["id_pass"]["W"] == rec["W"]
    assert rec["sparse_write"] is None
    assert rec["recurrent_write"] is None


def test_present_mode_on_frame_mirrors_encode_state():
    eng = _fresh_engine()
    eng.encode_mode = True
    eng.present(0, 30)
    f = eng.frame()
    enc = f["encode"]
    assert enc["mode"] is True
    assert enc["stage"] == "present"
    assert enc["W"] == sorted(int(x) for x in eng.encode_W)
    assert enc["t_present_end"] == eng.t + 30
    assert enc["t_grace_end"] == eng.t + 30 + params.ENCODE_GRACE_TICKS


def test_present_mode_on_w_matches_independent_identify_w():
    """W must equal brainsim.encode.identify_W run on a deep copy the test
    itself makes before present(), from the identical pre-present state."""
    import copy as copy_mod
    encode = _encode()
    eng = _fresh_engine()
    eng.encode_mode = True
    ref = copy_mod.deepcopy(eng)
    ref.encode_mode = False

    eng.present(0, 30)

    W_ref, _ = encode.identify_W(ref, 0, 30, params.ENCODE_K)
    assert np.array_equal(np.sort(eng.encode_W), np.sort(W_ref))


def test_second_present_while_present_stage_is_plain_and_unchanged():
    eng = _fresh_engine()
    eng.encode_mode = True
    eng.present(0, 30)
    rec1 = eng.encode_record
    W1 = eng.encode_W.copy()
    rec2 = eng.present(1, 10)
    assert rec2 is not None
    assert rec2["n_cells"] > 0
    assert eng.encode_record is rec1
    assert np.array_equal(eng.encode_W, W1)


# --------------------------------------------------------------------------- #
# 6. stepping to t_present_end: grace begins, weights bumped
# --------------------------------------------------------------------------- #

def _armed_engine(ticks=50):
    eng = _fresh_engine()
    eng.encode_mode = True
    eng.present(0, ticks)
    return eng


def test_present_end_tick_transitions_to_grace_and_restores_a_minus():
    eng = _armed_engine(50)
    a_minus_W_saved = eng.net.a_minus_n[eng.encode_W].copy()
    assert np.all(a_minus_W_saved == 0.0)
    eng.step(50)
    assert eng.t == eng._encode["t_present_end"] if eng._encode else True
    assert eng.encode_stage == "grace"
    assert np.all(eng.net.a_minus_n[eng.encode_W] > 0.0)
    assert np.all(eng.encode_mask[eng.encode_W])
    assert eng.encode_record["sparse_write"] is not None
    assert isinstance(eng.encode_record["sparse_write"]["n_synapses_bumped"], int)
    assert eng.encode_record["recurrent_write"] is not None
    assert isinstance(eng.encode_record["recurrent_write"]["n_synapses_bumped"], int)


def test_sparse_cofire_write_bumps_donor_to_w_by_exact_delta_only():
    """Pure-function check of brainsim.encode.sparse_cofire_write, independent
    of whatever plasticity the engine keeps running elsewhere."""
    encode = _encode()
    eng = _fresh_engine()
    net = eng.net
    eng.step(50)  # produce a real, non-trivial counts vector

    hpc_ids = encode.hpc_e_ids(net)
    ctx_ids = encode.ctx_e_ids(net)
    W = np.sort(hpc_ids[:params.ENCODE_K])
    counts = net.spike_count.astype(np.int64).copy()

    w_before = net.w.copy()
    w_max_n = net.w_max_n.copy()

    encode.sparse_cofire_write(net, counts, hpc_ids, ctx_ids, params.ENCODE_K,
                               params.ENCODE_DELTA_FRAC, W)

    donors = ctx_ids[counts[ctx_ids] > 0]
    donor_mask = np.zeros(net.n, bool)
    donor_mask[donors] = True
    w_mask = np.zeros(net.n, bool)
    w_mask[W] = True
    idx = np.flatnonzero(net.alive & donor_mask[net.pre] & w_mask[net.post])
    assert idx.size > 0, "test plant produced no donor->W synapses to check"

    expected = np.minimum(w_before[idx] + params.ENCODE_DELTA_FRAC * w_max_n[net.post[idx]],
                          w_max_n[net.post[idx]])
    assert np.allclose(net.w[idx], expected, atol=1e-5)

    other = np.setdiff1d(np.arange(net.w.size), idx)
    assert np.array_equal(net.w[other], w_before[other])


def test_recurrent_cofire_write_bumps_w_to_w_by_exact_delta_only():
    """Pure-function check of brainsim.encode.recurrent_cofire_write."""
    encode = _encode()
    eng = _fresh_engine()
    net = eng.net
    eng.step(50)

    hpc_ids = encode.hpc_e_ids(net)
    W = np.sort(hpc_ids[:params.ENCODE_K])
    w_before = net.w.copy()
    w_max_n = net.w_max_n.copy()

    encode.recurrent_cofire_write(net, W, params.ENCODE_RECURRENT_DELTA_FRAC)

    w_mask = np.zeros(net.n, bool)
    w_mask[W] = True
    idx = np.flatnonzero(net.alive & w_mask[net.pre] & w_mask[net.post])
    if idx.size == 0:
        pytest.skip("no W->W synapses exist among the first 16 hpc E ids on this seed")
    expected = np.minimum(
        w_before[idx] + params.ENCODE_RECURRENT_DELTA_FRAC * w_max_n[net.post[idx]],
        w_max_n[net.post[idx]])
    assert np.allclose(net.w[idx], expected, atol=1e-5)

    other = np.setdiff1d(np.arange(net.w.size), idx)
    assert np.array_equal(net.w[other], w_before[other])


def test_present_end_tick_calls_sparse_then_recurrent_write_with_engine_args():
    """Wiring check: Engine._encode_tick must call brainsim.encode's two write
    functions exactly once each, at t == t_present_end, with W == eng.encode_W
    and the fixed delta_frac params, sparse before recurrent, and each call's
    own before/after net.w satisfying the exact per-synapse rule on that
    call's own index set."""
    import brainsim.encode as encode_mod

    eng = _fresh_engine()
    eng.encode_mode = True

    calls = []
    real_sparse = encode_mod.sparse_cofire_write
    real_recurrent = encode_mod.recurrent_cofire_write

    def sparse_wrapper(net, counts, hpc_e_ids, ctx_e_ids, k, delta_frac, W=None):
        before = net.w.copy()
        out = real_sparse(net, counts, hpc_e_ids, ctx_e_ids, k, delta_frac, W)
        calls.append(dict(name="sparse", t=eng.t, W=np.array(W), delta_frac=delta_frac,
                          before=before, after=net.w.copy(), pre=net.pre.copy(),
                          post=net.post.copy(), alive=net.alive.copy(),
                          w_max_n=net.w_max_n.copy(),
                          donor_mask=np.isin(net.pre, ctx_e_ids[counts[ctx_e_ids] > 0])))
        return out

    def recurrent_wrapper(net, W, delta_frac):
        before = net.w.copy()
        out = real_recurrent(net, W, delta_frac)
        calls.append(dict(name="recurrent", t=eng.t, W=np.array(W), delta_frac=delta_frac,
                          before=before, after=net.w.copy(), pre=net.pre.copy(),
                          post=net.post.copy(), alive=net.alive.copy(),
                          w_max_n=net.w_max_n.copy(), donor_mask=None))
        return out

    import pytest as _pytest
    mp = _pytest.MonkeyPatch()
    mp.setattr(encode_mod, "sparse_cofire_write", sparse_wrapper)
    mp.setattr(encode_mod, "recurrent_cofire_write", recurrent_wrapper)
    try:
        eng.present(0, 50)
        t_present_end = eng.encode_record["t_present_end"]
        eng.step(50)
    finally:
        mp.undo()

    assert [c["name"] for c in calls] == ["sparse", "recurrent"]
    for c in calls:
        assert c["t"] == t_present_end
        assert np.array_equal(np.sort(c["W"]), np.sort(eng.encode_W))
        w_mask = np.zeros(eng.net.n, bool)
        w_mask[c["W"]] = True
        if c["name"] == "sparse":
            assert c["delta_frac"] == params.ENCODE_DELTA_FRAC
            idx = np.flatnonzero(c["alive"] & c["donor_mask"] & w_mask[c["post"]])
        else:
            assert c["delta_frac"] == params.ENCODE_RECURRENT_DELTA_FRAC
            idx = np.flatnonzero(c["alive"] & w_mask[c["pre"]] & w_mask[c["post"]])
        assert idx.size > 0
        expected = np.minimum(c["before"][idx] + c["delta_frac"] * c["w_max_n"][c["post"][idx]],
                              c["w_max_n"][c["post"][idx]])
        assert np.allclose(c["after"][idx], expected, atol=1e-5)


# --------------------------------------------------------------------------- #
# 7. stepping to t_grace_end
# --------------------------------------------------------------------------- #

def test_grace_end_tick_clears_mask_marks_done_keeps_w():
    eng = _armed_engine(30)
    W = eng.encode_W.copy()
    eng.step(30)  # reach t_present_end -> grace
    assert eng.encode_stage == "grace"
    eng.step(params.ENCODE_GRACE_TICKS)  # reach t_grace_end -> idle
    assert eng.encode_stage == "idle"
    assert not eng.encode_mask.any()
    assert eng.encode_record["done"] is True
    assert np.array_equal(np.sort(eng.encode_W), np.sort(W))
    assert eng._encode is None


# --------------------------------------------------------------------------- #
# 8. frame telemetry: spiked_last_50, RNG-free reads
# --------------------------------------------------------------------------- #

def test_frame_spiked_last_50_matches_own_recorded_spikes():
    eng = _armed_engine(30)
    W = set(int(x) for x in eng.encode_W)
    seen = set()
    for _ in range(60):
        eng.step(1)
        s = eng._buf_spikes[-1]
        seen |= (set(int(x) for x in s) & W)
    f = eng.frame()
    last50 = set(f["encode"]["spiked_last_50"])
    assert last50 <= W
    # deque holds only the most recent 50 ticks stepped
    assert last50 == seen or last50 <= seen


def test_frame_reads_consume_no_rng_with_encode_mode():
    e_read = _armed_engine(30)
    assert e_read.encode_stage == "present"  # schedule must actually be armed
    e_plain = _armed_engine(30)
    for _ in range(5):
        e_read.step(20)
        e_read.frame()
        e_plain.step(20)
    assert e_read.rng.bit_generator.state == e_plain.rng.bit_generator.state
    assert np.array_equal(e_read.net.v, e_plain.net.v)


# --------------------------------------------------------------------------- #
# 9. telemetry keys: FRAME_KEYS, CONFIG_KEYS, config(), layout()
# --------------------------------------------------------------------------- #

def test_frame_keys_contains_encode():
    assert "encode" in telemetry.FRAME_KEYS


def test_config_keys_contains_encode_keys():
    for k in ("encode_k", "encode_delta_frac", "encode_recurrent_delta_frac",
              "encode_grace_ticks"):
        assert k in telemetry.CONFIG_KEYS


def test_config_reports_encode_param_values():
    e = _fresh_engine()
    cfg = telemetry.config(e, 50, 200)
    assert cfg["encode_k"] == params.ENCODE_K
    assert cfg["encode_delta_frac"] == params.ENCODE_DELTA_FRAC
    assert cfg["encode_recurrent_delta_frac"] == params.ENCODE_RECURRENT_DELTA_FRAC
    assert cfg["encode_grace_ticks"] == params.ENCODE_GRACE_TICKS


def test_layout_half_patterns_matches_cue_ids_per_pattern():
    encode = _encode()
    e = _fresh_engine()
    lay = telemetry.layout(e)
    assert len(lay["half_patterns"]) == len(e.patterns)
    for i, pat in enumerate(e.patterns):
        assert lay["half_patterns"][i] == encode.cue_ids(pat).tolist()


def test_reply_keys_layout_contains_half_patterns():
    assert "half_patterns" in telemetry.REPLY_KEYS["layout"]


# --------------------------------------------------------------------------- #
# 10. brainsim.encode pure functions
# --------------------------------------------------------------------------- #

def test_select_winners_tie_break_and_length():
    encode = _encode()
    ids = np.array([5, 1, 3, 2, 4], dtype=np.int64)
    counts = np.zeros(6, dtype=np.int64)
    counts[[5, 1, 3, 2, 4]] = [10, 10, 3, 10, 1]  # three-way tie at 10: 1,2,5
    out = encode.select_winners(counts, ids, 3)
    assert out.tolist() == [1, 2, 5]
    assert out.dtype == np.int64
    assert np.array_equal(out, np.sort(out))

    out_short = encode.select_winners(counts, ids, 100)
    assert out_short.size == ids.size


def test_cue_ids_even_positions_of_sorted_pattern():
    encode = _encode()
    rng = np.random.default_rng(0)
    pattern = rng.permutation(np.arange(40) + 7)
    cue = encode.cue_ids(pattern)
    expected = np.sort(pattern)[0::2]
    assert np.array_equal(cue, expected)


def test_identify_w_leaves_engine_untouched():
    encode = _encode()
    eng = _fresh_engine()
    t_before = eng.t
    w_before = eng.net.w.copy()
    spikes_before = eng.net.spike_count.copy()
    mask_before = eng.encode_mask.copy()
    rng_before = eng.rng.bit_generator.state

    W, rec = encode.identify_W(eng, 0, 30, params.ENCODE_K)

    assert eng.t == t_before
    assert np.array_equal(eng.net.w, w_before)
    assert np.array_equal(eng.net.spike_count, spikes_before)
    assert np.array_equal(eng.encode_mask, mask_before)
    assert eng.rng.bit_generator.state == rng_before
    assert W.size == params.ENCODE_K
    assert np.array_equal(W, np.sort(W))
    assert np.isin(W, encode.hpc_e_ids(eng.net)).all()


# --------------------------------------------------------------------------- #
# 11. worker: {"cmd": "encode", "on": bool}
# --------------------------------------------------------------------------- #

def _session(seed=1):
    from brainsim import worker
    replies = []
    e = Engine(seed=seed)
    s = worker.Session(e, replies.append, lambda f: None)
    return s, e, replies


def _results(replies, cmd=None):
    return [r for r in replies if r["type"] == "result" and (cmd is None or r.get("cmd") == cmd)]


def test_encode_command_turns_mode_on_changed_true():
    s, e, replies = _session()
    s.handle({"cmd": "encode", "on": True, "req": "e1"})
    res = _results(replies, "encode")[0]
    assert res["status"] == "accepted"
    assert res["changed"] is True
    assert e.encode_mode is True


def test_encode_command_turning_on_again_changed_false():
    s, e, replies = _session()
    s.handle({"cmd": "encode", "on": True, "req": "e1"})
    replies.clear()
    s.handle({"cmd": "encode", "on": True, "req": "e2"})
    res = _results(replies, "encode")[0]
    assert res["status"] == "accepted"
    assert res["changed"] is False


def test_encode_command_on_int_rejected_invalid():
    s, e, replies = _session()
    s.handle({"cmd": "encode", "on": 1, "req": "e1"})
    res = _results(replies, "encode")[0]
    assert res["status"] == "rejected"
    assert res["reason"] == "invalid: on must be a bool"


def test_encode_command_reply_keys_match_reply_keys():
    s, e, replies = _session()
    s.handle({"cmd": "encode", "on": True, "req": "e1"})
    assert e.encode_mode is True
    for r in replies:
        assert set(r) == telemetry.REPLY_KEYS[r["type"]], r["type"]


def test_present_encode_mode_idle_ticks_over_2000_rejected_invalid():
    """The identification pass deep-copies the engine and steps the copy
    inline inside the command handler, so an idle encode-mode present is
    capped at 2000 ticks (the K1.1 presentation length)."""
    s, e, replies = _session()
    e.encode_mode = True
    assert e.encode_stage == "idle"
    s.handle({"cmd": "present", "pattern": 0, "ticks": 2001, "req": "p1"})
    res = _results(replies, "present")[0]
    assert res["status"] == "rejected"
    assert res["reason"].startswith("invalid:")
    assert e.encode_record is None


def test_present_encode_mode_idle_ticks_at_2000_accepted():
    s, e, replies = _session()
    e.encode_mode = True
    assert e.encode_stage == "idle"
    s.handle({"cmd": "present", "pattern": 0, "ticks": 2000, "req": "p1"})
    res = _results(replies, "present")[0]
    assert res["status"] == "accepted"


def test_present_encode_mode_off_ticks_100000_still_accepted():
    s, e, replies = _session()
    assert e.encode_mode is False
    s.handle({"cmd": "present", "pattern": 0, "ticks": 100000, "req": "p1"})
    res = _results(replies, "present")[0]
    assert res["status"] == "accepted"


# --------------------------------------------------------------------------- #
# 12. UI source: ui/index.html, ui/app.js
# --------------------------------------------------------------------------- #

INDEX_HTML = open("ui/index.html").read()
APP_JS = open("ui/app.js").read()
GLOSS_SENTENCE = ("these cells were the A winners; lighting them after a "
                  "hint is the scribble, not speech.")


def test_index_html_has_encode_panel_ids():
    for ident in ("encodeToggle", "encodestage", "wcard", "wcaption",
                  "encPresentA", "encHalfA", "encNone"):
        assert ident in INDEX_HTML, ident


def test_index_html_has_the_gloss_sentence_verbatim():
    assert GLOSS_SENTENCE in INDEX_HTML


def test_app_js_key_gloss_has_encode_entry():
    block = APP_JS[APP_JS.index("const KEY_GLOSS"):]
    block = block[:block.index("};")]
    glossed = set(re.findall(r'^\s*"?([A-Za-z_][A-Za-z0-9_]*)"?\s*:', block, re.M))
    assert "encode" in glossed


def test_app_js_references_half_patterns_with_no_hard_coded_w_id_list():
    assert "half_patterns" in APP_JS
    # A literal 16-element bracketed list of integers would be a hard-coded W.
    assert not re.search(r"\[\s*(?:\d+\s*,\s*){15}\d+\s*\]", APP_JS)
