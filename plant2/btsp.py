"""Behavioural-timescale synaptic plasticity with binary weights (labelled model).

Wu & Maass 2025 (Nat Commun 16:342), Eq. 1, simplified from CA1 data (Bittner et al. 2017;
Milstein et al. 2021): when a memory cell has a dendritic plateau, every input that was active
inside the plateau's seconds-long window flips its binary weight with probability 0.5 (0 -> 1,
1 -> 0). The rule never reads the memory cell's spikes. Plateaus and eligibility are inputs to
this module; how they are produced is the experiment's (labelled) choice.

Only weight-1 synapses are stored, as sorted int64 keys pre * n_post + post, so storage grows
with what was written rather than with the potential connectivity, and a CSR view by
presynaptic cell falls out of the sort order.
"""
import numpy as np


class BinarySynapses:
    def __init__(self, n_pre, n_post):
        self.n_pre, self.n_post = n_pre, n_post
        self.keys = np.empty(0, np.int64)

    @property
    def size(self):
        return int(self.keys.size)

    def pre_post(self):
        return self.keys // self.n_post, self.keys % self.n_post

    def csr(self):
        """(indptr over presynaptic cells, postsynaptic index per stored synapse)."""
        indptr = np.searchsorted(self.keys, np.arange(self.n_pre + 1, dtype=np.int64) * self.n_post)
        return indptr, self.keys % self.n_post

    def per_post_count(self):
        return np.bincount(self.keys % self.n_post, minlength=self.n_post)

    def toggle(self, flip_keys):
        """Flip the weight of each synapse in flip_keys (unique keys): stored ones go, others come."""
        flip_keys = np.unique(np.asarray(flip_keys, np.int64))
        if not flip_keys.size:
            return 0, 0
        pos = np.searchsorted(self.keys, flip_keys)
        present = pos < self.keys.size
        present[present] = self.keys[pos[present]] == flip_keys[present]
        keep = np.ones(self.keys.size, bool)
        keep[pos[present]] = False
        kept = self.keys[keep]
        add = flip_keys[~present]
        self.keys = np.insert(kept, np.searchsorted(kept, add), add)
        return int(add.size), int(present.sum())


    def add(self, new_keys):
        """Set the given synapses to 1 (a clipped, one-shot write); already-stored keys are unchanged."""
        new_keys = np.unique(np.asarray(new_keys, np.int64))
        if not new_keys.size:
            return 0
        new_keys = new_keys[~np.isin(new_keys, self.keys, assume_unique=True)]
        self.keys = np.insert(self.keys, np.searchsorted(self.keys, new_keys), new_keys)
        return int(new_keys.size)


def btsp_update(store, plateau_cells, eligible_inputs, rng, p_flip=0.5):
    """Apply Wu & Maass Eq. 1 for one episode. Returns (potentiated, depressed) counts."""
    plateau_cells = np.asarray(plateau_cells, np.int64)
    eligible_inputs = np.asarray(eligible_inputs, np.int64)
    if not plateau_cells.size or not eligible_inputs.size:
        return 0, 0
    cand = (eligible_inputs[:, None] * store.n_post + plateau_cells[None, :]).ravel()
    return store.toggle(cand[rng.random(cand.size) < p_flip])
