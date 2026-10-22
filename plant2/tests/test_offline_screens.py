"""Contract tests for analysis/offline_screens_20261022.py (docs/plant2/OFFLINE-SCREENS-20261022.md).

Synthetic inputs only; every file lives under the run_dir fixture.
"""
import json

import numpy as np
import pytest

from analysis import offline_screens_20261022 as osx  # noqa: E402
from plant2 import evidence  # noqa: E402
from plant2.btsp import BinarySynapses, btsp_update  # noqa: E402
from plant2.experiments import p2_e1_btsp as e1  # noqa: E402


def arr(*xs):
    return np.array(sorted(xs), np.int64)


# ---------------------------------------------------------------- count rule

def test_count_rule_threshold_values():
    assert osx.count_rule_threshold(0) == 8      # ceil(7.14)
    assert osx.count_rule_threshold(2) == 8      # ceil(7.74)
    assert osx.count_rule_threshold(3) == 9      # ceil(8.04)
    assert osx.count_rule_threshold(10) == 11    # ceil(10.14)
    assert osx.count_rule_threshold(20) == 14    # ceil(13.14)


# ---------------------------------------------------------------- screen A

PROTOS = [arr(10, 13), arr(11, 12)]
ITEMS = [arr(10, 11, 12, 20), arr(10, 13, 14), arr(10, 11, 12, 13), arr(10, 11, 13)]
A_ = [arr(1), arr(4), arr(1), arr(9)]
E_ = [arr(10, 11, 12), arr(10, 11, 13), arr(10, 12, 13), arr(10, 11)]
R_ = [arr(1, 2, 3), arr(2, 3, 4), arr(1, 2, 3, 5), arr(2, 5, 9)]


def _family(k):
    return (k + 1) % 2


def _rows(thresholds=(1, 2, 3)):
    return osx.gate_prescreen(ITEMS, A_, E_, R_, PROTOS, _family, thresholds=thresholds)


def test_gate_prescreen_row_shape_and_sizes():
    rows = _rows()
    assert [r["episode"] for r in rows] == [0, 1, 2, 3]
    assert [r["q_size"] for r in rows] == [2, 2, 3, 2]
    assert [r["p_size"] for r in rows] == [2, 2, 2, 2]
    assert [r["theta_primary"] for r in rows] == [8, 8, 9, 8]
    for r in rows:
        for key in ("t_primary", "t_1", "t_2", "t_3"):
            assert set(r[key]) >= {"V_size", "proto_predicted", "nonproto_predicted", "veto_precision"}


def test_gate_prescreen_empty_store_first_episode_and_none_veto():
    r = _rows()[0]["t_1"]
    assert r["V_size"] == 0
    assert r["proto_predicted"] == 0.0           # P0 and E0 share {11, 12}
    assert r["nonproto_predicted"] == 0.0        # E0 minus P0 is {10}
    assert r["veto_precision"] is None           # G and E0 do not meet


def test_gate_prescreen_hand_enumerated_threshold_two():
    rows = _rows()
    r1 = rows[1]["t_2"]   # lines 10, 11, 12 each have writers {2, 3} in Q1
    assert r1["V_size"] == 2
    assert r1["proto_predicted"] == pytest.approx(0.5)
    assert r1["nonproto_predicted"] == pytest.approx(1.0)
    assert r1["veto_precision"] == pytest.approx(0.5)
    r2 = rows[2]["t_2"]
    assert r2["V_size"] == 3
    assert r2["proto_predicted"] == pytest.approx(1.0)
    assert r2["nonproto_predicted"] == pytest.approx(1.0)
    assert r2["veto_precision"] == pytest.approx(1 / 3)
    r3 = rows[3]["t_2"]
    assert r3["V_size"] == 1
    assert r3["proto_predicted"] == pytest.approx(1.0)
    assert r3["nonproto_predicted"] == pytest.approx(0.0)
    assert r3["veto_precision"] == pytest.approx(1.0)


def test_gate_prescreen_threshold_one_on_last_episode():
    r = _rows()[3]["t_1"]
    assert r["V_size"] == 2
    assert r["nonproto_predicted"] == pytest.approx(1.0)
    assert r["veto_precision"] == pytest.approx(0.5)


def test_gate_prescreen_excludes_own_write_and_plateau_cells():
    # Episode 2: Q2 = {2, 3, 5}. Counting its own write (cell 5 on lines 10, 12, 13) or the
    # plateau cell 1 (A2) as a writer would lift some line to 3; the contract keeps all out.
    rows = _rows()
    for k in (1, 2, 3):
        assert rows[k]["t_3"]["V_size"] == 0
        assert rows[k]["t_3"]["veto_precision"] is None


def test_gate_prescreen_primary_threshold_is_the_count_rule():
    rows = _rows()
    for r in rows:
        assert r["t_primary"]["V_size"] == 0   # no line has 8 or more writers here


def test_gate_prescreen_default_thresholds_keys():
    rows = osx.gate_prescreen(ITEMS, A_, E_, R_, PROTOS, _family)
    for key in ("t_primary", "t_8", "t_12", "t_16", "t_19", "t_24"):
        assert key in rows[0]


def test_gate_prescreen_none_when_proto_or_nonproto_denominator_zero():
    protos = [arr(11, 12), arr(11, 12)]
    # E subset of P: nothing outside the prototype set
    rows = osx.gate_prescreen([arr(11, 12)], [arr(1)], [arr(11, 12)], [arr(2, 3)], protos,
                              lambda k: 0, thresholds=(1,))
    assert rows[0]["t_1"]["nonproto_predicted"] is None
    assert rows[0]["t_1"]["proto_predicted"] == 0.0
    # P disjoint from E
    rows = osx.gate_prescreen([arr(11, 12, 30)], [arr(1)], [arr(30, 31)], [arr(2, 3)], protos,
                              lambda k: 0, thresholds=(1,))
    assert rows[0]["t_1"]["proto_predicted"] is None
    assert rows[0]["p_size"] == 2


# ---------------------------------------------------------------- screen B

M_, N_ = 60, 40


def _episodes(n_ep, a_size=3, e_size=12, seed=7, disjoint=False):
    rng = np.random.default_rng(seed)
    A, E = [], []
    for k in range(n_ep):
        A.append(np.sort(rng.choice(N_, a_size, replace=False)).astype(np.int64))
        if disjoint:
            E.append(np.arange(k * e_size, (k + 1) * e_size, dtype=np.int64))
        else:
            E.append(np.sort(rng.choice(M_, e_size, replace=False)).astype(np.int64))
    return A, E


def _point_expected(seed, A, E, n):
    store = BinarySynapses(M_, n)
    rng = e1.stream(seed, e1.COIN)
    for a, e in zip(A, E):
        btsp_update(store, a, e, rng)
    return store.keys


def test_rebuild_forward_store_matches_btsp_update():
    A, E = _episodes(10)
    got = osx.rebuild_forward_store(11, A, E, N_)
    want = _point_expected(11, A, E, N_)
    assert want.size > 0
    assert got.dtype == np.int64
    assert np.array_equal(got, want)
    assert np.all(np.diff(got) > 0)


def test_rebuild_forward_store_depends_on_seed():
    A, E = _episodes(10)
    assert not np.array_equal(osx.rebuild_forward_store(11, A, E, N_),
                              osx.rebuild_forward_store(12, A, E, N_))


def test_integrity_gate_exact_equality():
    k = arr(1, 5, 9)
    assert osx.integrity_gate(k, k.copy()) is True
    assert osx.integrity_gate(k, arr(1, 5, 10)) is False
    assert osx.integrity_gate(k, arr(1, 5)) is False
    assert osx.integrity_gate(k, arr(1, 5, 9, 12)) is False


def _branch_expected(seed, A, E, n, K):
    rng = e1.stream(seed, e1.COIN)
    plateaus = np.zeros(n, np.int64)
    held = set()
    for a, e in zip(A, E):
        cand = (e[:, None] * n + a[None, :]).ravel()
        flips = cand[rng.random(cand.size) < 0.5]
        for key in np.unique(flips).tolist():
            pre, cell = divmod(key, n)
            held ^= {pre * (n * K) + cell * K + int(plateaus[cell] % K)}
        plateaus[a] += 1
    return np.array(sorted(held), np.int64)


@pytest.mark.parametrize("K", [2, 8])
def test_rebuild_branch_store_round_robin_two_plateaus(K):
    n = 4
    A = [arr(1), arr(0, 2), arr(1), arr(0)]
    E = [np.arange(0, 12, dtype=np.int64), np.arange(0, 12, dtype=np.int64),
         np.arange(12, 24, dtype=np.int64), np.arange(24, 36, dtype=np.int64)]
    got = osx.rebuild_branch_store(5, A, E, n, K)
    assert np.array_equal(got, _branch_expected(5, A, E, n, K))
    cell0 = got[(got % (n * K)) // K == 0]
    branch = cell0 % K
    pre = cell0 // (n * K)
    assert np.any(branch == 0) and np.any(branch == 1)
    assert set(branch.tolist()) == {0, 1}
    assert set(pre[branch == 0].tolist()) <= set(E[1].tolist())   # cell 0's first plateau: episode 1
    assert set(pre[branch == 1].tolist()) <= set(E[3].tolist())   # its second plateau: episode 3


def test_rebuild_branch_store_collapses_to_point_store_when_no_reuse():
    A, E = _episodes(6, disjoint=True)
    K = 8
    branch = osx.rebuild_branch_store(3, A, E, N_, K)
    point = osx.rebuild_forward_store(3, A, E, N_)
    collapsed = np.unique((branch // (N_ * K)) * N_ + (branch % (N_ * K)) // K)
    assert np.array_equal(collapsed, point)


def test_rebuild_branch_store_k1_equals_point_store_with_overlap():
    A, E = _episodes(12, e_size=20, seed=21)
    branch = osx.rebuild_branch_store(9, A, E, N_, 1)
    assert np.array_equal(branch, osx.rebuild_forward_store(9, A, E, N_))


def test_cue_counts_hand_checked():
    n = 4
    keys = np.array(sorted([0 * n + 0, 1 * n + 0, 2 * n + 0, 0 * n + 1, 1 * n + 1, 5 * n + 1, 2 * n + 3]),
                    np.int64)
    out = osx.cue_counts(keys, n, [0, 1, 2])
    assert out.tolist() == [3, 2, 0, 1]
    assert len(out) == n


def test_branch_max_counts_hand_checked():
    n, K = 3, 2

    def key(j, cell, b):
        return j * (n * K) + cell * K + b

    keys = np.array(sorted([key(0, 0, 0), key(1, 0, 0),
                            key(0, 0, 1), key(1, 0, 1), key(2, 0, 1),
                            key(0, 1, 0), key(1, 1, 1),
                            key(7, 2, 0)]), np.int64)
    out = osx.branch_max_counts(keys, n, K, [0, 1, 2])
    assert out.tolist() == [3, 1, 0]      # cell 1 has two cue lines but on different branches


# ---------------------------------------------------------------- screen C

def test_latency_split_percentiles_and_counts():
    own = list(range(11))
    spikes = [[c, 10 + c] for c in own] + [[100, 40]]
    d = osx.latency_split(spikes, own)
    assert d["n_own"] == 11 and d["n_spurious"] == 1
    assert d["own_median"] == pytest.approx(15)
    assert d["own_p10"] == pytest.approx(11)
    assert d["own_p90"] == pytest.approx(19)
    assert d["spurious_median"] == d["spurious_p10"] == d["spurious_p90"] == 40


def test_latency_split_empty_group_is_none():
    d = osx.latency_split([[0, 12], [1, 14]], [0, 1])
    assert d["n_spurious"] == 0
    assert d["spurious_median"] is None and d["spurious_p10"] is None and d["spurious_p90"] is None
    assert d["own_median"] == pytest.approx(13)


def test_latency_cut_arithmetic():
    own = [0, 1, 2, 3, 4]
    spikes = [[0, 10], [1, 22], [2, 28], [3, 41], [4, 60],
              [10, 15], [11, 33], [12, 47]]
    out = osx.latency_cut(spikes, own, 5)
    assert set(out) == {20, 25, 30, 35, 40, 45, 50}
    expect = {20: (0.2, 1, False, True), 25: (0.4, 1, False, True), 30: (0.6, 1, False, True),
              35: (0.6, 2, False, True), 40: (0.6, 2, False, True), 45: (0.8, 2, True, True),
              50: (0.8, 3, True, False)}
    for cut, (recall, spurious, c1, c2) in expect.items():
        assert out[cut]["recall"] == pytest.approx(recall)
        assert out[cut]["spurious"] == spurious
        assert out[cut]["C1"] is c1
        assert out[cut]["C2"] is c2


# ---------------------------------------------------------------- screen D

def test_saturation_summary_per_kind_quartiles():
    columns = ["cue_id", "x", "total"]
    # (cue_id, total); rows are not in cue_id order, so alignment must go by cue_id
    pairs = [(3, 300), (0, 10), (4, 50), (1, 20), (2, 30), (5, 200), (6, 100)]
    rows = [[cid, 0, tot] for cid, tot in pairs]
    kinds = ["full", "full", "full", "full", "full", "half", "half"]
    # cue 3 is full (index 3), cue 5 and 6 are half; so full = {10, 20, 30, 300, 50}
    out = osx.saturation_summary(columns, rows, kinds)
    assert set(out) == {"full", "half"}
    assert out["full"]["median"] == pytest.approx(30)
    assert out["full"]["q1"] == pytest.approx(20)
    assert out["full"]["q3"] == pytest.approx(50)
    assert out["half"]["median"] == pytest.approx(150)
    assert out["half"]["q1"] == pytest.approx(125)
    assert out["half"]["q3"] == pytest.approx(175)


def test_saturation_summary_absent_total():
    out = osx.saturation_summary(["cue_id", "x"], [[0, 1], [1, 2]], ["full", "half"])
    assert out == {"absent": True}


# ---------------------------------------------------------------- evidence and records

def test_verify_input_accepts_real_and_rejects_tampered_descriptor(run_dir):
    desc = evidence.write_json_artifact(run_dir / "input.json", {"a": [1, 2, 3]})
    assert isinstance(osx.verify_input(desc), dict)
    bad = dict(desc, sha256="0" * 64)
    with pytest.raises(evidence.EvidenceError):
        osx.verify_input(bad)


def test_record_screen_writes_verified_artifact_record_and_journal(run_dir):
    results = run_dir / "offline.jsonl"
    journal = evidence.Journal(run_dir / "run.journal.jsonl", "w0")
    in_desc = evidence.write_json_artifact(run_dir / "in.json", {"x": 1})
    obj = {"rows": [{"episode": 0, "v": 1}]}
    rec = osx.record_screen(results, run_dir / "ev", "A", 105, "ORIGINAL", 1000, "offline proxy",
                            {"mean_V": 1.0}, obj, {"in": in_desc}, journal)
    lines = results.read_text().splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed == rec
    assert parsed["kind"] == "offline_screen"
    for key, val in (("screen", "A"), ("seed", 105), ("arm", "ORIGINAL"), ("M", 1000),
                     ("label", "offline proxy"), ("summary", {"mean_V": 1.0}), ("inputs", {"in": in_desc})):
        assert parsed[key] == val
    assert json.loads(evidence.verify_artifact(parsed["artifact"]).decode()) == obj
    assert str(run_dir / "ev") in str(evidence._resolve(parsed["artifact"]["path"]))
    assert len(evidence.verify_journal(run_dir / "run.journal.jsonl")) >= 1


def test_record_invalid_after_integrity_mismatch(run_dir):
    results = run_dir / "offline-invalid.jsonl"
    journal = evidence.Journal(run_dir / "invalid.journal.jsonl", "w0")
    assert osx.integrity_gate(arr(1, 2, 3), arr(1, 2, 4)) is False
    rec = osx.record_invalid(results, "B", 105, "rebuilt forward keys differ from persisted", journal)
    parsed = json.loads(results.read_text().splitlines()[0])
    assert parsed == rec
    assert parsed["status"] == "INVALID"
    assert parsed["reason"] == "rebuilt forward keys differ from persisted"
    assert parsed["screen"] == "B" and parsed["seed"] == 105
    assert not parsed.get("summary")
    assert len(evidence.verify_journal(run_dir / "invalid.journal.jsonl")) >= 1


def test_records_append_one_line_each(run_dir):
    results = run_dir / "both.jsonl"
    journal = evidence.Journal(run_dir / "both.journal.jsonl", "w0")
    osx.record_screen(results, run_dir / "ev", "D", 106, "ORIGINAL", 500, "offline", {"n": 1},
                      {"o": 1}, {}, journal)
    first = results.read_text().splitlines()[0]
    osx.record_invalid(results, "B", 106, "mismatch", journal)
    lines = results.read_text().splitlines()
    assert len(lines) == 2 and lines[0] == first


# ---------------------------------------------------------------- screen E

# F=3, family of 0-based episode k is (k + 1) % 3: family 1 = {0, 3, 6}, family 2 = {1, 4, 7},
# family 0 = {2, 5, 8}. Cell 13 sits in the plateaus of episodes 5 (family 0) and 6 (family 1).
E_A = [arr(1, 2), arr(3, 4), arr(5, 6), arr(7, 8), arr(9, 10), arr(11, 12, 13), arr(13, 14),
       arr(15, 16), arr(17, 18)]
# family 1 engaged at episode 3, family 2 never, family 0 at episode 1
E_FIRST = {1: 3, 2: None, 0: 1}


def _e_rows():
    return [
        {"index_0based": 3, "kind": "half", "own50": 2, "spurious50": 3},
        {"index_0based": 4, "kind": "half", "own50": 1, "spurious50": 3},
    ]


def _e_resp():
    # cue 3 (family 1): 1 early (episode 0), 13 late (episode 6, also episode 5 of family 0), 3 other
    # cue 4 (family 2, never engaged): 3 and 15 early, 5 other
    return {3: arr(1, 7, 8, 3, 13), 4: arr(3, 5, 9, 15)}


def test_spurious_classes_hand_built_toy():
    out = osx.spurious_classes(_e_rows(), E_A, _e_resp(), E_FIRST, F=3)
    assert out["cues"] == 2
    assert out["spurious_per_cue"] == pytest.approx(3.0)
    assert out["same_family_early_per_cue"] == pytest.approx(1.5)
    assert out["same_family_late_per_cue"] == pytest.approx(0.5)
    assert out["other_family_only_per_cue"] == pytest.approx(1.0)
    assert out["items_before_engagement"] == 4  # episode 0 (family 1) + 3 of family 2 + none of family 0
    assert out["early_chance"] == pytest.approx((1 / 3 + 1.0 + 0.0) / 3)
    assert out["per_cue"] == [
        {"cue_index": 3, "spurious": 3, "same_family_early": 1, "same_family_late": 1,
         "other_family_only": 1},
        {"cue_index": 4, "spurious": 3, "same_family_early": 2, "same_family_late": 0,
         "other_family_only": 1},
    ]


def test_spurious_classes_never_engaged_family_counts_everything_early():
    out = osx.spurious_classes(_e_rows()[1:], E_A, {4: _e_resp()[4]}, {1: None, 2: None, 0: None}, F=3)
    assert out["items_before_engagement"] == 9
    assert out["early_chance"] == pytest.approx(1.0)
    assert out["per_cue"][0]["same_family_early"] == 2


def test_spurious_classes_identity_check_raises_on_mismatch():
    bad = _e_resp()
    bad[3] = arr(1, 7, 8, 3, 13, 9)  # six responders against own50 + spurious50 = 5
    with pytest.raises(ValueError):
        osx.spurious_classes(_e_rows(), E_A, bad, E_FIRST, F=3)
    # own is counted by identity with A(q): a responder set of the right size but missing an own cell
    swapped = _e_resp()
    swapped[3] = arr(1, 7, 3, 13, 15)  # 5 cells, only one own cell (7) instead of two
    with pytest.raises(ValueError):
        osx.spurious_classes(_e_rows(), E_A, swapped, E_FIRST, F=3)


def test_spurious_classes_ignores_non_half_rows():
    rows = _e_rows() + [
        {"index_0based": 5, "kind": "full", "own50": 99, "spurious50": 99},
        {"index_0based": 6, "kind": "novel", "own50": 0, "spurious50": 7},
    ]
    out = osx.spurious_classes(rows, E_A, _e_resp(), E_FIRST, F=3)
    assert out["cues"] == 2
    assert [c["cue_index"] for c in out["per_cue"]] == [3, 4]
    assert out["spurious_per_cue"] == pytest.approx(3.0)


def test_early_chance_arithmetic_unequal_engagement():
    # F=2 (family of k is (k + 1) % 2): family 1 = {0, 2}, family 0 = {1, 3}; engaged at 1 and 3
    A = [arr(1), arr(2), arr(3), arr(4)]
    rows = [{"index_0based": 0, "kind": "half", "own50": 1, "spurious50": 0}]
    out = osx.spurious_classes(rows, A, {0: arr(1)}, {1: 1, 0: 3}, F=2)
    # family 1 early = {0}: 1/2; family 0 early = {1}: 1/2 -> 0.5; items before = 2
    assert out["items_before_engagement"] == 2
    assert out["early_chance"] == pytest.approx(0.5)
    out2 = osx.spurious_classes(rows, A, {0: arr(1)}, {1: 2, 0: None}, F=2)
    # family 1 (engaged at 2): only episode 0 of {0, 2} is early -> 1/2; family 0 all early -> 1.0
    assert out2["items_before_engagement"] == 3
    assert out2["early_chance"] == pytest.approx(0.75)


def test_responders_from_raster_window_and_duplicates():
    ticks = [99, 100, 101, 120, 149, 150, 160, 400]
    cells = [arr(4), arr(5, 3), arr(3, 5), arr(7), arr(9, 9), arr(11), arr(2), arr(8)]
    out = osx.responders_from_raster(ticks, cells, [0, 1, 2], [100, 150, 400], ["half", "half", "full"])
    assert sorted(out) == [0, 1]  # the full cue is not a half cue
    assert list(out[0]) == [3, 5, 7, 9]  # cell 4 (tick 99) and 11 (tick 150) fall outside [100, 150)
    assert list(out[1]) == [2, 11]       # window [150, 200); cell 8 at tick 400 excluded
