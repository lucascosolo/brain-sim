"""K1.5 selective-write fixture: pure helpers of tests/k815_selective_write.py (SPEC.md 8.15).

Tiny synthetic inputs only. Expected to fail with ImportError until the driver lands.
"""
import math

import numpy as np
import pytest

from brainsim.net import Network


def _k815():
    from tests import k815_selective_write as k815
    return k815


def _net(ws, posts=None, pres=None, n=8, w_max=2.0):
    m = len(ws)
    pres = pres if pres is not None else list(range(1, m + 1))
    posts = posts if posts is not None else [0] * m
    syn = [(pres[i], posts[i], ws[i], 1) for i in range(m)]
    return Network.tiny(n, [True] * n, syn, w_max=w_max)


def _snap(entries, w_max=2.0):
    """entries: (pre, post, born, w, alive) per slot."""
    a = list(zip(*entries))
    return {"pre": np.array(a[0], np.int32), "post": np.array(a[1], np.int32),
            "born": np.array(a[2], np.int64), "w": np.array(a[3], np.float32),
            "alive": np.array(a[4], bool),
            "w_max_post": np.full(len(entries), w_max, np.float32)}


# --- split_marks -----------------------------------------------------------

def test_split_ranks_by_donor_count_ties_by_id_odd_count():
    k = _k815()
    net = _net([0.5] * 5)  # slot i has pre i+1, post 0
    counts = np.zeros(8)
    counts[[1, 2, 3, 4, 5]] = [5, 9, 5, 1, 7]
    U, D = k.split_marks(net, [0], counts, [1, 2, 3, 4, 5])
    assert sorted(U.tolist()) == [0, 1, 4]  # pre 2 (9), pre 5 (7), pre 1 (5, lower id than pre 3)
    assert sorted(D.tolist()) == [2, 3]


def test_split_even_count_halves_and_is_disjoint_partition():
    k = _k815()
    net = _net([0.5] * 4)
    counts = np.zeros(8)
    counts[[1, 2, 3, 4]] = [5, 9, 5, 1]
    U, D = k.split_marks(net, [0], counts, [1, 2, 3, 4])
    assert sorted(U.tolist()) == [0, 1] and sorted(D.tolist()) == [2, 3]
    assert not set(U.tolist()) & set(D.tolist())


def test_split_single_mark_goes_to_u():
    k = _k815()
    net = _net([0.5])
    U, D = k.split_marks(net, [0], np.ones(8), [1])
    assert U.tolist() == [0] and len(D) == 0


def test_split_only_alive_w_post_and_src_marks_per_cell():
    k = _k815()
    # slots: 0 (1->0), 1 (2->0) killed, 2 (3->0) pre outside src, 3 (1->5) post outside W, 4 (2->1)
    net = _net([0.5] * 5, posts=[0, 0, 0, 5, 1], pres=[1, 2, 3, 1, 2])
    net.kill_synapses(np.array([1], np.int32))
    U, D = k.split_marks(net, [0, 1], np.ones(8), [1, 2])
    assert sorted(U.tolist() + D.tolist()) == [0, 4]
    assert sorted(U.tolist()) == [0, 4] and len(D) == 0  # one mark per cell -> each in U


# --- selective_write -------------------------------------------------------

def test_selective_write_preserves_per_cell_sum():
    k = _k815()
    net = _net([0.5, 0.5, 1.0, 1.0])
    rec = k.selective_write(net, np.array([0, 1]), np.array([2, 3]), delta_frac=0.15)
    assert net.w[[0, 1]] == pytest.approx([0.8, 0.8])
    assert net.w[[2, 3]] == pytest.approx([0.7, 0.7])
    assert rec["n_U"] == 2 and rec["n_D"] == 2
    assert rec["n_clamped_up"] == 0 and rec["n_clamped_down"] == 0
    assert rec["residual_per_cell"][0] == pytest.approx(0.0, abs=1e-6)
    assert rec["max_abs_residual"] == pytest.approx(0.0, abs=1e-6)


def test_selective_write_clamps_u_at_w_max_and_D_pays_actual_increase():
    k = _k815()
    net = _net([1.9, 0.5, 1.0, 1.0])
    rec = k.selective_write(net, np.array([0, 1]), np.array([2, 3]))
    assert net.w[0] == pytest.approx(2.0)
    assert net.w[1] == pytest.approx(0.8)
    assert net.w[[2, 3]] == pytest.approx([0.8, 0.8])  # total_up = 0.1 + 0.3 = 0.4, /2
    assert rec["n_clamped_up"] == 1
    assert rec["residual_per_cell"][0] == pytest.approx(0.0, abs=1e-6)


def test_selective_write_floor_clamp_leaves_nonzero_residual():
    k = _k815()
    net = _net([0.5, 0.5, 0.25, 1.0])
    rec = k.selective_write(net, np.array([0, 1]), np.array([2, 3]))
    assert net.w[2] == pytest.approx(0.2)  # floor 0.10 * 2.0
    assert net.w[3] == pytest.approx(0.7)
    assert rec["n_clamped_down"] == 1
    assert rec["residual_per_cell"][0] == pytest.approx(0.25, abs=1e-6)
    assert rec["max_abs_residual"] == pytest.approx(0.25, abs=1e-6)


def test_selective_write_never_raises_d_below_floor_and_skips_outsiders():
    k = _k815()
    net = _net([0.5, 0.5, 0.1, 1.0, 1.3], posts=[0, 0, 0, 0, 3], pres=[1, 2, 3, 4, 5])
    before_alive, n_used = net.alive.copy(), net.s_used
    k.selective_write(net, np.array([0, 1]), np.array([2, 3]))
    assert net.w[2] == pytest.approx(0.1)  # already under the 0.2 floor: unchanged
    assert net.w[4] == pytest.approx(1.3)  # outsider untouched
    assert (net.alive == before_alive).all() and net.s_used == n_used


def test_selective_write_cell_without_d_gets_no_lowering():
    k = _k815()
    net = _net([0.5, 1.0], posts=[0, 1], pres=[1, 2])
    rec = k.selective_write(net, np.array([0]), np.array([1]))
    # cell 0 has only U, cell 1 has only D: U rises, D unchanged
    assert net.w[0] == pytest.approx(0.8) and net.w[1] == pytest.approx(1.0)
    assert rec["n_U"] == 1 and rec["n_D"] == 1


# --- uniform_write ---------------------------------------------------------

def test_uniform_write_raises_all_marks_clamped_leaves_rest():
    k = _k815()
    net = _net([0.5, 1.9, 1.0, 0.7], posts=[0, 0, 0, 2], pres=[1, 2, 3, 4])
    rec = k.uniform_write(net, np.array([0, 1]), np.array([2]))
    assert net.w[[0, 1, 2]] == pytest.approx([0.8, 2.0, 1.3])
    assert net.w[3] == pytest.approx(0.7)
    assert rec["n"] == 3 and rec["n_clamped"] == 1


# --- marks_from / contrast -------------------------------------------------

def _two_cell_snap(**over):
    e = {"u0": (1, 0, 0, 1.0, True), "d0": (2, 0, 0, 0.5, True),
         "u1": (1, 1, 0, 1.6, True), "d1": (2, 1, 0, 0.4, True)}
    e.update(over)
    return _snap([e["u0"], e["d0"], e["u1"], e["d1"]])


MARKS = [(1, 0, 0, True), (2, 0, 0, False), (1, 1, 0, True), (2, 1, 0, False)]


def test_marks_from_records_identity_and_direction():
    k = _k815()
    snap = _two_cell_snap()
    got = k.marks_from(snap, np.array([0, 2]), np.array([1, 3]))
    assert sorted(got) == sorted(MARKS)


def test_contrast_all_alive():
    c = _k815().contrast(_two_cell_snap(), MARKS)
    assert c["C"] == pytest.approx(0.425)  # mean(0.5-0.25, 0.8-0.2)
    assert c["C_survivors"] == pytest.approx(0.425)
    assert c["M"] == pytest.approx(0.4375)
    assert c["U_mean"] == pytest.approx(0.65) and c["D_mean"] == pytest.approx(0.225)
    assert (c["dead_U"], c["dead_D"], c["n_U"], c["n_D"]) == (0, 0, 2, 2)


def test_contrast_dead_u_lowers_C_and_survivors_drop_the_cell():
    snap = _two_cell_snap(u0=(1, 0, 0, 1.0, False))
    c = _k815().contrast(snap, MARKS)
    assert c["C"] == pytest.approx(0.175)  # mean(0 - 0.25, 0.6)
    assert c["C_survivors"] == pytest.approx(0.6)  # cell 0 has no U survivor
    assert c["dead_U"] == 1 and c["dead_D"] == 0


def test_contrast_dead_d_raises_C_survivors_ignores_it():
    snap = _two_cell_snap(d0=(2, 0, 0, 0.5, False))
    c = _k815().contrast(snap, MARKS)
    assert c["C"] == pytest.approx(0.55)  # mean(0.5 - 0, 0.6)
    assert c["C_survivors"] == pytest.approx(0.6)
    assert c["dead_D"] == 1 and c["dead_U"] == 0
    assert c["D_mean"] == pytest.approx(0.1)  # (0 + 0.2) / 2


def test_contrast_reused_slot_with_other_born_is_not_the_mark():
    snap = _two_cell_snap(u0=(1, 0, 7, 2.0, True))  # same pre/post, newborn synapse
    c = _k815().contrast(snap, MARKS)
    assert c["dead_U"] == 1
    assert c["C"] == pytest.approx(0.175)


def test_contrast_survivors_nan_when_no_cell_qualifies():
    snap = _snap([(1, 0, 0, 1.0, False), (2, 0, 0, 0.5, True)])
    c = _k815().contrast(snap, [(1, 0, 0, True), (2, 0, 0, False)])
    assert math.isnan(c["C_survivors"])


# --- retention -------------------------------------------------------------

def test_retention_ratio_and_zero_denominator():
    k = _k815()
    assert k.retention(0.5, 0.2, 0.8, 0.2) == pytest.approx(0.5)  # 0.3 / 0.6
    assert math.isnan(k.retention(0.5, 0.2, 0.3, 0.3))
