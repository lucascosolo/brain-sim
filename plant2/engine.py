"""plant2 engine: LIF populations, Poisson sources and sparse delayed projections, dt 1 ms.

The membrane update is the plant's (SPEC 2.1 without the adaptive threshold): exact leak decay
toward rest, then the delta inputs that arrive this tick; a cell spikes at threshold unless it
spiked within the last `t_ref` ticks, and resets. Each population owns its state arrays and a
delay ring of future input, and projections are CSR by presynaptic cell, so a population is a
shard that could live in another process or device and exchange only spike indices.
"""
import numpy as np

f32 = np.float32


class Poisson:
    """Spike sources: each cell fires in a tick with probability rate_hz * dt / 1000."""

    def __init__(self, name, n, dt=1.0):
        self.name, self.n, self.dt = name, n, dt
        self.rate_hz = np.zeros(n, np.float64)
        self._p = np.zeros(n, np.float64)
        self._buf = np.empty(n, np.float64)

    def set_rates(self, rate_hz):
        self.rate_hz[:] = rate_hz
        np.multiply(self.rate_hz, self.dt / 1000.0, out=self._p)

    def step(self, rng):
        return np.flatnonzero(rng.random(self.n, out=self._buf) < self._p)


class LIF:
    """Leaky integrate-and-fire cells with delta synapses (mV per spike).

    With `acc_tau` (ms) set, each cell's threshold accommodates: it sits `v_th - v_rest` above
    the cell's own running mean membrane potential `vbar` (P2-E2, labelled proxy for slow
    threshold accommodation) instead of above rest. `vbar` is adaptive state: `quiet()` keeps it.
    """

    def __init__(self, name, n, d_max, tau_m=20.0, v_rest=-70.0, v_reset=-65.0, v_th=-50.0,
                 t_ref=2, dt=1.0, acc_tau=None):
        self.name, self.n, self.d_max, self.dt = name, n, d_max, dt
        self.v_rest, self.v_reset, self.v_th, self.t_ref = f32(v_rest), f32(v_reset), f32(v_th), t_ref
        self.decay = f32(np.exp(-dt / tau_m))
        self._v_c = f32(v_rest * (1.0 - self.decay))
        self.v = np.full(n, v_rest, np.float32)
        self.t_last = np.full(n, -10_000, np.int64)
        self.ring = np.zeros((d_max + 1, n), np.float32)
        self.vbar = np.full(n, float(v_rest), np.float64)
        self.set_accommodation(acc_tau)

    def set_accommodation(self, acc_tau):
        self.acc_tau = acc_tau
        self._acc = None if acc_tau is None else self.dt / float(acc_tau)

    def threshold(self):
        if self._acc is None:
            return np.full(self.n, self.v_th, np.float64)
        return self.vbar + float(self.v_th - self.v_rest)

    def quiet(self):
        """State after a long input-free interval: rest, no pending input, not refractory.

        Adaptive state (`vbar`) is not reset."""
        self.v[:] = self.v_rest
        self.t_last[:] = -10_000
        self.ring[:] = 0.0

    def step(self, t):
        slot = self.ring[t % (self.d_max + 1)]
        v = self.v
        np.multiply(v, self.decay, out=v)
        v += self._v_c
        v += slot
        slot[:] = 0.0
        if self._acc is None:
            s = np.flatnonzero(v >= self.v_th)
        else:
            self.vbar += (v - self.vbar) * self._acc
            s = np.flatnonzero(v >= self.vbar + float(self.v_th - self.v_rest))
        if s.size:
            s = s[t - self.t_last[s] > self.t_ref]
            v[s] = self.v_reset
            self.t_last[s] = t
        return s


class Projection:
    """Static sparse synapses src -> dst stored CSR by presynaptic cell."""

    def __init__(self, src, dst, pre, post, weight, delay):
        self.src, self.dst = src, dst
        self.set_synapses(pre, post, weight, delay)

    def set_synapses(self, pre, post, weight, delay):
        pre = np.asarray(pre, np.int64)
        order = np.argsort(pre, kind="stable")
        self.post = np.asarray(post, np.int64)[order]
        self.weight = np.broadcast_to(np.asarray(weight, np.float32), pre.shape)[order].copy()
        self.delay = np.broadcast_to(np.asarray(delay, np.int64), pre.shape)[order].copy()
        if self.delay.size and (self.delay.min() < 1 or self.delay.max() > self.dst.d_max):
            raise ValueError("delays must lie in 1..d_max of the target population")
        self.indptr = np.searchsorted(pre[order], np.arange(self.src.n + 1))

    def set_csr(self, indptr, post, weight, delay):
        """Load synapses already in CSR order (indptr over src cells, one post index per synapse)."""
        self.indptr = np.asarray(indptr, np.int64)
        self.post = np.asarray(post, np.int64)
        self.weight = np.broadcast_to(np.asarray(weight, np.float32), self.post.shape).copy()
        self.delay = np.broadcast_to(np.asarray(delay, np.int64), self.post.shape).copy()
        if self.delay.size and (self.delay.min() < 1 or self.delay.max() > self.dst.d_max):
            raise ValueError("delays must lie in 1..d_max of the target population")
        if self.indptr.size != self.src.n + 1 or self.indptr[-1] != self.post.size:
            raise ValueError("indptr does not match the source size and synapse count")

    def deliver(self, spikes, t):
        if not spikes.size:
            return
        lo, cnt = self.indptr[spikes], self.indptr[spikes + 1] - self.indptr[spikes]
        k = int(cnt.sum())
        if not k:
            return
        idx = np.repeat(lo, cnt) + (np.arange(k) - np.repeat(np.cumsum(cnt) - cnt, cnt))
        ring = self.dst.ring
        slots = (t + self.delay[idx]) % ring.shape[0]
        np.add.at(ring, (slots, self.post[idx]), self.weight[idx])


class Net:
    """Ticks sources and LIF populations and routes spikes through projections."""

    def __init__(self, sources, populations, projections):
        self.sources, self.populations, self.projections = sources, populations, projections
        self.t = 0

    def step(self, rng):
        spikes = {s.name: s.step(rng) for s in self.sources}
        for pop in self.populations:
            spikes[pop.name] = pop.step(self.t)
        for proj in self.projections:
            proj.deliver(spikes[proj.src.name], self.t)
        self.t += 1
        return spikes

    def quiet(self):
        for pop in self.populations:
            pop.quiet()
