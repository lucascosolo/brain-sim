"""Contract tests for analysis/p2r3_branch_rec.py (docs/plant2/P2-R3-branch-reconstruction-replay.md).

Synthetic inputs only. Lines are reconstruction lines (m), memory cells are writer cells (n).
"""
import numpy as np
import pytest

from analysis import p2r3_branch_rec as br  # noqa: E402
from plant2 import readout  # noqa: E402
from plant2.btsp import BinarySynapses  # noqa: E402


def arr(*xs):
    return np.array(sorted(xs), np.int64)


def rng_ids(rng, n, size):
    return np.sort(rng.choice(n, size=size, replace=False)).astype(np.int64)


# ---------------------------------------------------------------- store

def test_episode_round_robin_and_line_counter():
    E = [arr(0, 1), arr(0), arr(0, 2), arr(0), arr(0)]
    R = [arr(1, 2), arr(3, 4), arr(2, 5), arr(6), arr(7, 1)]
    s = br.build_branch_store(E, R, K=2, m=3, n=10)
    assert [int(x) for x in s.counts] == [5, 1, 1]
    assert np.array_equal(s.writers(0, 0), arr(1, 2, 5, 7))   # episodes 0, 2, 4 (union, add-only)
    assert np.array_equal(s.writers(0, 1), arr(3, 4, 6))      # episodes 1, 3
    assert np.array_equal(s.writers(1, 0), arr(1, 2))
    assert s.writers(1, 1).size == 0
    assert np.array_equal(s.writers(2, 0), arr(2, 5))


def test_multiset_keeps_cross_branch_duplicates():
    E = [arr(0), arr(0), arr(0)]
    R = [arr(1, 2), arr(2, 3), arr(2, 5)]
    s = br.build_branch_store(E, R, K=2, m=1, n=6)
    assert np.array_equal(s.writers(0, 0), arr(1, 2, 5))
    assert np.array_equal(s.writers(0, 1), arr(2, 3))
    assert np.array_equal(s.multiset(0), np.array([1, 2, 2, 3, 5]))


def test_unbounded_uses_one_branch_per_write_event_and_ignores_K():
    E = [arr(0), arr(0), arr(0)]
    R = [arr(1, 2), arr(2, 3), arr(4)]
    s = br.build_branch_store(E, R, K=2, m=1, n=6, mode="unbounded")
    for b, expect in enumerate(R):
        assert np.array_equal(s.writers(0, b), expect)
    assert int(s.counts[0]) == 3


def test_k1_episode_store_is_the_frozen_point_store():
    rng = np.random.default_rng(5)
    m, n = 30, 20
    E = [rng_ids(rng, m, 10) for _ in range(6)]
    R = [rng_ids(rng, n, 7) for _ in range(6)]
    s = br.build_branch_store(E, R, K=1, m=m, n=n)
    point = BinarySynapses(n, m)
    for e, r in zip(E, R):
        point.add((r[:, None] * m + e[None, :]).ravel())
    for j in range(m):
        union = np.unique(np.concatenate([r for e, r in zip(E, R) if j in e] or [np.empty(0, np.int64)]))
        assert np.array_equal(s.writers(j, 0), union)
    indptr, post, branch = s.csr()
    p_indptr, p_post = point.csr()
    assert np.array_equal(indptr, p_indptr)
    assert not branch.any()
    for c in range(n):
        assert set(post[indptr[c]:indptr[c + 1]]) == set(p_post[p_indptr[c]:p_indptr[c + 1]])


def test_csr_by_memory_cell_lists_every_line_branch_pair_of_its_writes():
    E = [arr(0, 1), arr(0), arr(0, 1)]
    R = [arr(2, 3), arr(3), arr(3, 4)]
    s = br.build_branch_store(E, R, K=2, m=2, n=5)
    indptr, post, branch = s.csr()
    got = {c: set(zip(post[indptr[c]:indptr[c + 1]].tolist(), branch[indptr[c]:indptr[c + 1]].tolist()))
           for c in range(5)}
    expect = {j_b: s.writers(*j_b) for j_b in [(0, 0), (0, 1), (1, 0), (1, 1)]}
    for c in range(5):
        assert got[c] == {jb for jb, w in expect.items() if c in w}
    assert got[3] == {(0, 0), (0, 1), (1, 0), (1, 1)}


def _scramble_inputs():
    rng = np.random.default_rng(11)
    m, n, M = 6, 60, 40
    E = [rng_ids(rng, m, 5) for _ in range(M)]
    R = [rng_ids(rng, n, 20) for _ in range(M)]
    return E, R, m, n


def test_scramble_preserves_each_line_writer_multiset_and_counts():
    E, R, m, n = _scramble_inputs()
    ep = br.build_branch_store(E, R, K=4, m=m, n=n)
    sc = br.build_branch_store(E, R, K=4, m=m, n=n, mode="scramble", scramble_seed=121)
    assert [int(x) for x in sc.counts] == [int(x) for x in ep.counts]
    for j in range(m):
        assert np.array_equal(sc.multiset(j), ep.multiset(j))
    assert any(not np.array_equal(sc.writers(j, b), ep.writers(j, b)) for j in range(m) for b in range(4))


def test_scramble_is_deterministic_in_its_seed():
    E, R, m, n = _scramble_inputs()
    a = br.build_branch_store(E, R, K=4, m=m, n=n, mode="scramble", scramble_seed=121)
    b = br.build_branch_store(E, R, K=4, m=m, n=n, mode="scramble", scramble_seed=121)
    c = br.build_branch_store(E, R, K=4, m=m, n=n, mode="scramble", scramble_seed=122)
    same = all(np.array_equal(a.writers(j, k), b.writers(j, k)) for j in range(m) for k in range(4))
    other = all(np.array_equal(a.writers(j, k), c.writers(j, k)) for j in range(m) for k in range(4))
    assert same and not other


# ---------------------------------------------------------------- replay

def _cue(onset, m, rng):
    ids = lambda k: rng_ids(rng, m, k)
    return dict(onset=onset, item=ids(14), cue=ids(7), missing=ids(7), other_missing=ids(7))


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_k1_branch_replay_equals_frozen_replay_bit_for_bit(seed):
    rng = np.random.default_rng(seed)
    m, n, n_ticks = 48, 24, 300
    E = [rng_ids(rng, m, 20) for _ in range(6)]
    R = [rng_ids(rng, n, 12) for _ in range(6)]
    store = br.build_branch_store(E, R, K=1, m=m, n=n)
    point = BinarySynapses(n, m)
    for e, r in zip(E, R):
        point.add((r[:, None] * m + e[None, :]).ravel())
    indptr, post = point.csr()
    raster = {t: rng_ids(rng, n, int(rng.integers(0, 9))) for t in range(n_ticks)}
    cues = [_cue(o, m, rng) for o in (0, 100, 200)]
    J, g = np.array([2.8, 4.0, 2.8]), np.array([0.0, 0.0, 0.3])
    want = readout.replay(raster, n_ticks, indptr, post, m, J, g, cues, window=75, short=50, span=75)
    got = br.branch_replay(raster, n_ticks, store, m, J, g, cues, window=75, short=50, span=75)
    assert want[0]["total"].sum() > 0
    assert set(got[0]) == set(want[0])
    for key in want[0]:
        assert np.array_equal(got[0][key], want[0][key]), key
    np.testing.assert_array_equal(got[1], want[1])
    np.testing.assert_array_equal(got[2], want[2])


def _line0_store():
    """One line, two branches: branch 0 holds cells 0-9, branch 1 holds cells 10-19."""
    E = [arr(0), arr(0)]
    R = [np.arange(0, 10), np.arange(10, 20)]
    return br.build_branch_store(E, R, K=2, m=1, n=20)


def _one_cue(onset):
    return [dict(onset=onset, item=arr(0), cue=arr(0), missing=arr(0), other_missing=arr(0))]


def _run(raster, onset=50, n_ticks=150):
    store = _line0_store()
    return br.branch_replay(raster, n_ticks, store, 1, np.array([2.8]), np.array([0.0]),
                            _one_cue(onset), window=75, short=50, span=75)


def test_two_sub_threshold_branches_do_not_sum():
    raster = {55: np.concatenate([np.arange(0, 5), np.arange(10, 15)])}   # 5 + 5 writers at once
    res, _, _ = _run(raster)
    assert res["missing"][0, 0] == 0
    # the point store (union of both branches) would cross: 10 coincident writers x 2.8 mV
    point = BinarySynapses(20, 1)
    point.add(np.arange(0, 20))
    indptr, post = point.csr()
    ref, _, _ = readout.replay(raster, 150, indptr, post, 1, np.array([2.8]), np.array([0.0]),
                               _one_cue(50), window=75, short=50, span=75)
    assert ref["missing"][0, 0] == 1


def test_one_crossing_branch_spikes_at_the_point_readouts_tick():
    raster = {55: np.arange(0, 10)}
    res, lat, oow = _run(raster)
    point = BinarySynapses(20, 1)
    point.add(np.arange(0, 20))
    indptr, post = point.csr()
    ref, ref_lat, ref_oow = readout.replay(raster, 150, indptr, post, 1, np.array([2.8]), np.array([0.0]),
                                           _one_cue(50), window=75, short=50, span=75)
    assert res["missing"][0, 0] == 1 == ref["missing"][0, 0]
    np.testing.assert_array_equal(lat, ref_lat)
    np.testing.assert_array_equal(oow, ref_oow)


def test_branch_resets_are_independent_and_line_spike_is_an_or():
    # before the cue window: branch 0 crosses at tick 6; branch 1 crosses alone at tick 8
    # (5 writers at tick 5, 5 more at tick 7). A reset shared across branches would stop the second.
    raster = {5: np.concatenate([np.arange(0, 10), np.arange(10, 15)]), 7: np.arange(15, 20)}
    _, _, oow = _run(raster)
    assert int(oow[0]) == 2


def test_two_branches_crossing_on_one_tick_make_one_line_spike():
    raster = {5: np.arange(0, 20)}
    _, _, oow = _run(raster)
    assert int(oow[0]) == 1


# ---------------------------------------------------------------- parity_check

def test_parity_check_exact_equality_of_result_dicts():
    a = {"missing": np.array([[1, 2]], np.int32), "total": np.array([[3, 4]], np.int32)}
    b = {k: v.copy() for k, v in a.items()}
    assert br.parity_check(a, b) is True
    b["total"][0, 1] += 1
    assert br.parity_check(a, b) is False
    assert br.parity_check(a, {"missing": a["missing"]}) is False


# ---------------------------------------------------------------- step 0
# Assumed input shapes (contract does not fix them): rows_content[i] = {"missing": lines recovered,
# "intrusions": count, "intrusion_lines": array of line ids}; rows_cues[i] = cue dict with "onset";
# active_counts[i] = N_active for cue i; the active cells of a cue are the raster cells in
# ticks onset .. onset + 74. Result: {"rows": [per cue], "fraction_summation": float}; a row has
# "class" in {"D1", "intrusion", "both", None} and "lines": {line: {"episodes": {k: n_active_writers},
# "single_episode_reaches": bool}}.

def _step0_inputs():
    E = [arr(5), arr(5), arr(7)]
    R = [np.arange(0, 10), np.arange(10, 20), np.arange(20, 40)]
    point = BinarySynapses(40, 8)
    for e, r in zip(E, R):
        point.add((r[:, None] * 8 + e[None, :]).ravel())
    cue = dict(item=arr(1), cue=arr(1), missing=arr(1), other_missing=arr(2))
    rows_cues = [dict(cue, onset=o) for o in (0, 100, 200, 300)]
    rows_content = [
        dict(missing=10, intrusions=0, intrusion_lines=arr()),          # D1 failure only
        dict(missing=45, intrusions=12, intrusion_lines=arr(5)),        # spans episodes 0 and 1
        dict(missing=45, intrusions=12, intrusion_lines=arr(7)),        # one episode reaches
        dict(missing=45, intrusions=2, intrusion_lines=arr()),          # passes
    ]
    raster = {101: np.arange(0, 20), 201: np.arange(20, 40)}
    active_counts = [0, 20, 20, 0]
    return rows_content, rows_cues, R, E, point, raster, active_counts


def test_step0_classifies_failures_and_span_structure():
    out = br.step0_decompose(*_step0_inputs())
    classes = [r["class"] for r in out["rows"]]
    assert classes[:3] == ["D1", "intrusion", "intrusion"]
    assert classes[3] in (None, "none", "pass")
    l5 = out["rows"][1]["lines"][5]
    assert l5["episodes"] == {0: 10, 1: 10}
    assert l5["single_episode_reaches"] is False       # ceil(0.3*20 + 7.14) = 14
    l7 = out["rows"][2]["lines"][7]
    assert l7["episodes"] == {2: 20}
    assert l7["single_episode_reaches"] is True


def test_step0_aggregate_fraction_counts_only_cross_episode_summation_failures():
    out = br.step0_decompose(*_step0_inputs())
    assert out["fraction_summation"] == pytest.approx(1 / 3)   # 1 of 3 failing cues
