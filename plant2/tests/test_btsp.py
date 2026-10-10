import numpy as np

from plant2.btsp import BinarySynapses, btsp_update


def dense(store):
    m = np.zeros((store.n_pre, store.n_post), bool)
    pre, post = store.pre_post()
    m[pre, post] = True
    return m


def test_flips_half_of_the_candidates_from_zero():
    s = BinarySynapses(200, 50)
    pot, dep = btsp_update(s, np.arange(10), np.arange(100), np.random.default_rng(1))
    assert dep == 0 and 420 <= pot <= 580 and s.size == pot


def test_depresses_half_of_the_candidates_already_at_one():
    s = BinarySynapses(200, 50)
    cand = (np.arange(100)[:, None] * 50 + np.arange(10)[None, :]).ravel()
    s.toggle(cand)
    pot, dep = btsp_update(s, np.arange(10), np.arange(100), np.random.default_rng(2))
    assert pot == 0 and 420 <= dep <= 580 and s.size == 1000 - dep


def test_only_plateau_cells_and_eligible_inputs_change():
    rng = np.random.default_rng(3)
    s = BinarySynapses(100, 40)
    s.toggle(np.unique(rng.integers(0, 100 * 40, 600)))
    before = dense(s)
    plateau, eligible = np.array([2, 9, 31]), np.array([0, 5, 17, 60, 99])
    btsp_update(s, plateau, eligible, rng)
    changed = before ^ dense(s)
    allowed = np.zeros_like(changed)
    allowed[np.ix_(eligible, plateau)] = True
    assert changed.any() and not (changed & ~allowed).any()


def test_toggle_twice_restores_the_store():
    rng = np.random.default_rng(4)
    s = BinarySynapses(80, 80)
    s.toggle(np.unique(rng.integers(0, 6400, 900)))
    keys = s.keys.copy()
    flip = np.unique(rng.integers(0, 6400, 300))
    s.toggle(flip)
    s.toggle(flip)
    assert np.array_equal(keys, s.keys)


def test_csr_view_matches_the_dense_matrix():
    rng = np.random.default_rng(6)
    s = BinarySynapses(30, 20)
    s.toggle(np.unique(rng.integers(0, 600, 150)))
    indptr, post = s.csr()
    m = np.zeros((30, 20), bool)
    for j in range(30):
        m[j, post[indptr[j]:indptr[j + 1]]] = True
    assert np.array_equal(m, dense(s)) and np.all(np.diff(s.keys) > 0)


def test_same_seed_same_writes():
    def run(seed):
        s = BinarySynapses(100, 100)
        rng = np.random.default_rng(seed)
        for _ in range(20):
            btsp_update(s, rng.choice(100, 5, replace=False), rng.choice(100, 10, replace=False), rng)
        return s.keys
    assert np.array_equal(run(7), run(7)) and not np.array_equal(run(7), run(8))
