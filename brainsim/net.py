import numpy as np

from .params import CONDUCT_DELAY_TICKS


def _gumbel_topk(logp, k, rng):
    keys = logp + rng.gumbel(size=logp.shape)
    idx = np.argpartition(-keys, k - 1, axis=1)[:, :k]
    return idx


class Network:
    def __init__(self, n, s_max, region_names, region_slice):
        self.n, self.s_max = n, s_max
        self.region_names, self.region_slice = region_names, region_slice
        self.region = np.zeros(n, np.uint8)
        self.is_exc = np.ones(n, bool)
        self.x = np.zeros(n, np.float32)
        self.y = np.zeros(n, np.float32)
        self.v = np.zeros(n, np.float32)
        self.theta = np.zeros(n, np.float32)
        self.x_pre = np.zeros(n, np.float32)
        self.y_post = np.zeros(n, np.float32)
        self.rate = np.zeros(n, np.float32)
        self.act = np.zeros(n, np.float32)
        self.t_last_spike = np.full(n, -10_000, np.int32)
        self.spike_count = np.zeros(n, np.uint32)
        self.w_max_n = np.zeros(n, np.float32)
        self.a_plus_n = np.zeros(n, np.float32)
        self.a_minus_n = np.zeros(n, np.float32)
        self.r_target = np.zeros(n, np.float32)
        self.pre = np.zeros(s_max, np.int32)
        self.post = np.zeros(s_max, np.int32)
        self.w = np.zeros(s_max, np.float32)
        # Slow weight component (SPEC 8.13): a floor under w; all zeros unless Engine.slow_weights
        self.w_slow = np.zeros(s_max, np.float32)
        self.delay = np.ones(s_max, np.uint8)
        self.alive = np.zeros(s_max, bool)
        self.born = np.zeros(s_max, np.int32)
        self.conduct = np.zeros(s_max, np.int32)
        self.s_used = 0
        self.free = []
        self.homeostasis = True
        self.allowed_src = {}
        self.rebuild_index(0)

    @classmethod
    def build(cls, params_module, rng):
        p = params_module
        names = list(p.REGIONS)
        sizes = [p.REGIONS[r]["n_exc"] + p.REGIONS[r]["n_inh"] for r in names]
        n = sum(sizes)
        slices, off = {}, 0
        for name, sz in zip(names, sizes):
            slices[name] = slice(off, off + sz)
            off += sz
        net = cls(n, p.S_MAX, names, slices)
        for rid, name in enumerate(names):
            cfg, sl = p.REGIONS[name], slices[name]
            net.region[sl] = rid
            net.is_exc[sl.start + cfg["n_exc"]:sl.stop] = False
            net.w_max_n[sl] = cfg["w_max"]
            net.a_plus_n[sl] = cfg["a_plus"]
            net.a_minus_n[sl] = cfg["a_minus"]
            net.r_target[sl.start:sl.start + cfg["n_exc"]] = cfg["r_target_exc"]
            net.r_target[sl.start + cfg["n_exc"]:sl.stop] = cfg["r_target_inh"]
        net.x[:] = rng.random(n)
        net.y[:] = rng.random(n)
        net.v[:] = p.V_REST_MV
        net.theta[:] = p.THETA_0_MV
        for src, dst, k_in, sigma in p.PROJECTIONS:
            net.allowed_src.setdefault(dst, []).append((src, k_in, sigma))
            s, d = slices[src], slices[dst]
            k = int(round(k_in * p.K_IN_IMMATURE_FACTOR))
            srcs = np.arange(s.start, s.stop)
            dsts = np.arange(d.start, d.stop)
            d2 = net._dist2(dsts, srcs)
            logp = -d2 / (2 * sigma ** 2)
            if src == dst:
                logp[np.arange(len(dsts)), np.arange(len(srcs))] = -np.inf
            cols = _gumbel_topk(logp, k, rng)
            pre = srcs[cols].ravel()
            post = np.repeat(dsts, k)
            dist = np.sqrt(d2[np.repeat(np.arange(len(dsts)), k), cols.ravel()])
            net.add_synapses(pre, post, net._init_w(pre, post, dist.size, rng, p),
                             net._delay_from(dist, p), 0, conduct=0)
        net.rebuild_index(0)
        return net

    def _dist2(self, dsts, srcs):
        dx = self.x[dsts][:, None] - self.x[srcs][None, :]
        dy = self.y[dsts][:, None] - self.y[srcs][None, :]
        return (dx * dx + dy * dy).astype(np.float32)

    def _init_w(self, pre, post, size, rng, p):
        mag = rng.uniform(p.W_INIT_LO, p.W_INIT_HI, size) * self.w_max_n[post]
        sign = np.where(self.is_exc[pre], 1.0, -p.I_GAIN)
        return (mag * sign).astype(np.float32)

    @staticmethod
    def _delay_from(dist, p):
        d = 1 + np.round(p.DELAY_SPREAD * dist / np.sqrt(2.0))
        return np.clip(d, 1, p.D_MAX).astype(np.uint8)

    @classmethod
    def tiny(cls, n, is_exc, synapses, w_max=2.0):
        from . import params as p
        net = cls(n, max(16, len(synapses) * 4), ["tiny"], {"tiny": slice(0, n)})
        net.homeostasis = False
        net.is_exc[:] = np.asarray(is_exc, bool)
        net.w_max_n[:] = w_max
        net.a_plus_n[:] = p.REGIONS["ctx"]["a_plus"]
        net.a_minus_n[:] = p.REGIONS["ctx"]["a_minus"]
        net.r_target[:] = p.REGIONS["ctx"]["r_target_exc"]
        net.v[:] = p.V_REST_MV
        net.theta[:] = p.THETA_0_MV
        if synapses:
            a = list(zip(*synapses))
            net.add_synapses(np.asarray(a[0], np.int32), np.asarray(a[1], np.int32),
                             np.asarray(a[2], np.float32), np.asarray(a[3], np.uint8), 0, conduct=0)
        net.rebuild_index(0)
        return net

    @property
    def n_alive(self):
        return int(self.alive.sum())

    def in_degree(self, ids, exc_only=True):
        m = self.alive.copy()
        if exc_only:
            m &= self.is_exc[self.pre]
        counts = np.bincount(self.post[m], minlength=self.n)
        return counts[np.asarray(ids)]

    def rebuild_index(self, t):
        ids = np.flatnonzero(self.alive & (self.conduct <= t)).astype(np.int32)
        for key, name in ((self.pre, "out"), (self.post, "in")):
            k = key[ids]
            order = np.argsort(k, kind="stable")
            ptr = np.zeros(self.n + 1, np.int64)
            np.cumsum(np.bincount(k, minlength=self.n), out=ptr[1:])
            setattr(self, name + "_ids", ids[order])
            setattr(self, name + "_ptr", ptr)

    def add_synapses(self, pre, post, w, delay, t, conduct=None):
        pre = np.asarray(pre, np.int32)
        m = len(pre)
        if m == 0:
            return np.empty(0, np.int32)
        take = min(len(self.free), m)
        ids = np.empty(m, np.int32)
        if take:
            ids[:take] = self.free[-take:]
            del self.free[-take:]
        rest = m - take
        if rest:
            if self.s_used + rest > self.s_max:
                raise RuntimeError("synapse store full")
            ids[take:] = np.arange(self.s_used, self.s_used + rest, dtype=np.int32)
            self.s_used += rest
        self.pre[ids] = pre
        self.post[ids] = np.asarray(post, np.int32)
        self.w[ids] = w
        self.w_slow[ids] = 0.0
        self.delay[ids] = delay
        self.alive[ids] = True
        self.born[ids] = t
        self.conduct[ids] = t + CONDUCT_DELAY_TICKS if conduct is None else conduct
        return ids

    def kill_synapses(self, ids):
        ids = np.asarray(ids, np.int32)
        if ids.size == 0:
            return
        self.alive[ids] = False
        self.w[ids] = 0.0
        self.w_slow[ids] = 0.0
        self.free.extend(ids.tolist())

    def pair_keys(self):
        ids = np.flatnonzero(self.alive)
        return np.sort(self.pre[ids].astype(np.int64) * self.n + self.post[ids])
