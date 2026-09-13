from collections import deque

import numpy as np

from . import params as default_params
from . import telemetry
from .net import Network


def _gather(ptr, ids, sel):
    lo, cnt = ptr[sel], ptr[sel + 1] - ptr[sel]
    k = int(cnt.sum())
    if not k:
        return np.empty(0, np.int32)
    return ids[np.repeat(lo, cnt) + (np.arange(k) - np.repeat(np.cumsum(cnt) - cnt, cnt))]


class Engine:
    def __init__(self, seed=default_params.SEED, net=None, noise_sigma=default_params.NOISE_SIGMA_MV,
                 params=default_params):
        self.p = params
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.net = net if net is not None else Network.build(params, self.rng)
        n = self.net.n
        self.t = 0
        self.phase = "wake"
        self.g = params.G_WAKE
        self.g_struct = params.STRUCT_BASE * 10.0
        self.born_per_s = 0
        self.died_per_s = 0
        self.sense_spont_hz = params.SENSE_SPONT_HZ
        self._sigma_vec = np.zeros(n, np.float32)
        self.set_noise(noise_sigma)
        self.stats = dict(spike_total=0, syn_born_total=0, syn_died_total=0,
                          syn_touched_last=0, syn_touched_sum=0, ticks=0,
                          stall_halt_sweeps=0, store_clamp_sweeps=0)
        self.ring = [[] for _ in range(params.D_MAX + 1)]
        self.i_inj = np.zeros(n, np.float32)
        self._inj = []
        self._stim_seq = 0
        self.stimlog = deque(maxlen=params.STIMLOG_MAX)
        self._buf_stim_events = []
        self._frame_seq = 0
        self._phase_ticks = 0
        self._sweep_base = np.zeros(n, np.uint32)
        f32 = np.float32
        self._m_decay = f32(np.exp(-params.DT_MS / params.TAU_M_MS))
        self._th_decay = f32(np.exp(-params.DT_MS / params.TAU_THETA_MS))
        self._tr_decay = f32(np.exp(-params.DT_MS / params.TAU_TRACE_MS))
        self._v_c = f32(params.V_REST_MV * (1.0 - self._m_decay))
        self._th_c = f32(params.THETA_0_MV * (1.0 - self._th_decay))
        self._noise_buf = np.empty(n, np.float32)
        self._spont_buf = np.empty(self.net.region_slice["sense"].stop
                                   - self.net.region_slice["sense"].start, np.float32) \
            if "sense" in self.net.region_slice else np.empty(0, np.float32)
        self._inj_on = False
        self._sense = self.net.region_slice.get("sense")
        self.sense_gated = False
        self.patterns = self._make_patterns()
        self._buf_spikes = []
        self._buf_touched = []
        self._buf_born = []
        self._buf_died = []
        self._born_count = self._died_count = 0
        self._buf_ticks = 0
        self._watch_id = None
        self._v_trace = []
        self._k_target = np.zeros(n, np.float32)
        for _src, dst, k_in, _sig in params.PROJECTIONS:
            if dst in self.net.region_slice:
                self._k_target[self.net.region_slice[dst]] += k_in
        self.syn_sample = self._sample_synapses()
        self._init_windup(params)

    def _init_windup(self, p):
        net = self.net
        groups = []
        for name in net.region_names:
            sl = net.region_slice[name]
            for tag, is_e in (("E", True), ("I", False)):
                members = np.flatnonzero(net.is_exc[sl.start:sl.stop] == is_e) + sl.start
                if members.size:
                    groups.append((f"{name}_{tag}", members))
        self._windup_groups = groups
        idx = np.full(net.n, -1, np.int64)
        thr = []
        a = p.RATE_EMA_ALPHA
        for gi, (_, members) in enumerate(groups):
            idx[members] = gi
            r_target_q = float(net.r_target[members].mean())
            if r_target_q <= 0:
                thr.append(float("-inf"))
            else:
                thr.append(max(p.WINDUP_MIN_PROGRESS,
                                p.WINDUP_NOISE_SIGMAS * np.sqrt(a / (2 - a)) / np.sqrt(r_target_q * len(members))))
        self._windup_group_idx = idx
        self._windup_thr = thr
        self._windup_hist = [[] for _ in groups]
        self._windup_sign = [0] * len(groups)
        self._windup_halted = [False] * len(groups)
        self.growth_halted = {name: False for name, _ in groups}
        self.store_clamped = False

    def _update_windup(self, e):
        p, net = self.p, self.net
        n_halted = 0
        for gi, (name, members) in enumerate(self._windup_groups):
            eq = float(e[members].mean())
            sgn = 0 if eq == 0.0 else (1 if eq > 0.0 else -1)
            thr = self._windup_thr[gi]
            halted = self._windup_halted[gi]
            if halted:
                if sgn != 0 and sgn != self._windup_sign[gi]:
                    halted = False
                    self._windup_hist[gi] = [eq]
            else:
                hist = self._windup_hist[gi]
                hist.append(eq)
                W = p.WINDUP_WINDOW_SWEEPS
                if len(hist) > W + 1:
                    del hist[:-(W + 1)]
                h = W // 2
                if len(hist) == W + 1:
                    A = np.mean(hist[:h])
                    B = np.mean(hist[-h:])
                    a_sign = 0 if A == 0.0 else (1 if A > 0.0 else -1)
                    b_sign = 0 if B == 0.0 else (1 if B > 0.0 else -1)
                    if a_sign == b_sign != 0 and abs(B) > abs(A) - thr:
                        halted = True
                        self._windup_sign[gi] = b_sign
            self._windup_halted[gi] = halted
            self.growth_halted[name] = halted
            n_halted += halted
        self.stats["stall_halt_sweeps"] += n_halted
        self.store_clamped = net.n_alive >= p.WINDUP_CAP_FRAC * net.s_max
        if self.store_clamped:
            self.stats["store_clamp_sweeps"] += 1
        grow_ok = np.ones(net.n, bool)
        for gi, (_, members) in enumerate(self._windup_groups):
            if self._windup_halted[gi]:
                grow_ok[members] = False
        return grow_ok

    @property
    def age_s(self):
        return self.t * self.p.DT_MS / 1000.0

    def _make_patterns(self):
        if self._sense is None:
            return []
        ids = np.arange(self._sense.start, self._sense.stop)
        k = max(1, int(round(len(ids) * self.p.PATTERN_FRAC)))
        x, y = self.net.x[ids], self.net.y[ids]
        out = []
        for cx, cy in ((0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75))[:self.p.PATTERNS]:
            d2 = (x - cx) ** 2 + (y - cy) ** 2
            out.append(np.sort(ids[np.argsort(d2)[:k]]).astype(np.int32))
        return out

    def _sample_synapses(self):
        ids = np.flatnonzero(self.net.alive)
        if len(ids) > self.p.SYN_SAMPLE:
            ids = self.rng.choice(ids, self.p.SYN_SAMPLE, replace=False)
        return np.sort(ids).astype(np.int32)

    def _is_sense(self, ids):
        if self._sense is None:
            return np.zeros(len(ids), bool)
        return (ids >= self._sense.start) & (ids < self._sense.stop)

    def set_noise(self, sigma_mv):
        if sigma_mv is None:
            sigma_mv = self.p.NOISE_SIGMA_MV
        self.noise_sigma = sigma_mv
        if isinstance(sigma_mv, dict):
            self._sigma_vec[:] = 0.0
            for name, sl in self.net.region_slice.items():
                self._sigma_vec[sl] = sigma_mv.get(name, 0.0)
        else:
            self._sigma_vec[:] = float(sigma_mv)
        self._sigma_any = bool(self._sigma_vec.any())

    def set_sense_spont(self, hz):
        self.sense_spont_hz = float(hz)

    def set_sleep(self, on):
        self.phase = "sleep" if on else "wake"
        self.g = self.p.G_SLEEP if on else self.p.G_WAKE
        self.sense_gated = bool(on) and self._sense is not None
        self._phase_ticks = 0

    def inject(self, ids, amp_mv, ticks):
        """Unchanged current injection; returns the observation record, or None if nothing was queued."""
        ids = np.asarray(ids, np.int32)
        if self.sense_gated:
            ids = ids[~self._is_sense(ids)]
        if ids.size and ticks > 0:
            self._stim_seq += 1
            rec = dict(stim_id=self._stim_seq, n_cells=int(ids.size), amp_mv=float(amp_mv),
                       t_accept=int(self.t), t_end_planned=int(self.t + int(ticks)),
                       n_sense_cells=int(self._is_sense(ids).sum()),
                       t_first_applied=None, t_last_applied=None, delivered_ticks=0,
                       gated_ticks=0, partially_gated_ticks=0, t_dropped=None, done=False)
            self._inj.append((ids, float(amp_mv), self.t + int(ticks), rec,
                              rec["n_sense_cells"]))
            return rec
        return None

    def present(self, pattern_id, ticks, amp_mv=None):
        amp = self.p.PATTERN_AMP_MV if amp_mv is None else amp_mv
        return self.inject(self.patterns[int(pattern_id)], amp, ticks)

    def stims_active(self):
        return [dict(entry[3]) for entry in self._inj]

    def _stim_applied(self, rec, n_sense):
        if self.sense_gated and n_sense:
            if n_sense == rec["n_cells"]:
                rec["gated_ticks"] += 1
                return
            rec["partially_gated_ticks"] += 1
        if rec["t_first_applied"] is None:
            rec["t_first_applied"] = int(self.t)
            self._buf_stim_events.append(
                dict(stim_id=rec["stim_id"], event="started", t=int(self.t)))
        rec["t_last_applied"] = int(self.t)
        rec["delivered_ticks"] += 1

    def _expire_stims(self):
        """Bookkeeping only: entries past t_end_planned add nothing to i_inj either way."""
        live = [e for e in self._inj if e[2] > self.t]
        if len(live) != len(self._inj):
            for e in self._inj:
                if e[2] <= self.t:
                    self._stim_dropped(e[3])
            self._inj = live

    def _stim_dropped(self, rec):
        rec["t_dropped"] = int(self.t)
        rec["done"] = True
        self.stimlog.append(rec)
        self._buf_stim_events.append(dict(
            stim_id=rec["stim_id"], event="ended", t=rec["t_last_applied"],
            t_dropped=rec["t_dropped"], delivered_ticks=rec["delivered_ticks"],
            gated_ticks=rec["gated_ticks"],
            partially_gated_ticks=rec["partially_gated_ticks"]))

    def spike_counts(self):
        return self.net.spike_count.copy()

    def watch(self, neuron_id):
        self._watch_id = int(neuron_id)
        self._v_trace = []

    def step(self, n=1):
        for _ in range(n):
            self._tick()

    def _tick(self):
        p, net = self.p, self.net
        slot = self.t % (p.D_MAX + 1)
        bucket = self.ring[slot]
        self.ring[slot] = []
        touched = 0
        v = net.v
        np.multiply(v, self._m_decay, out=v)
        v += self._v_c
        if bucket:
            d = bucket[0] if len(bucket) == 1 else np.concatenate(bucket)
            touched += d.size
            d = d[net.alive[d]]
            if d.size:
                post = net.post[d]
                v += np.bincount(post, weights=net.w[d], minlength=net.n)
                de = d[net.is_exc[net.pre[d]]]
                if de.size:
                    pd = net.post[de]
                    net.w[de] = np.maximum(
                        net.w[de] * (1.0 - self.g * net.a_minus_n[pd] * net.y_post[pd]), 0.0)

        if self._inj or self._inj_on:
            self._refresh_inj()
            v += self.i_inj
        if self._sigma_any:
            nz = self.rng.standard_normal(net.n, dtype=np.float32, out=self._noise_buf)
            np.multiply(nz, self._sigma_vec, out=nz)
            if self.sense_gated:
                nz[self._sense] = 0.0
            v += nz
        th = net.theta
        np.multiply(th, self._th_decay, out=th)
        th += self._th_c
        if self.sense_spont_hz and not self.sense_gated and self._sense is not None:
            draw = self.rng.random(self._spont_buf.size, dtype=np.float32, out=self._spont_buf)
            hit = self._sense.start + np.flatnonzero(draw < self.sense_spont_hz * p.DT_MS / 1000.0)
            if hit.size:
                v[hit] = np.maximum(v[hit], th[hit] + np.float32(1.0))
        net.x_pre *= self._tr_decay
        net.y_post *= self._tr_decay

        s = np.flatnonzero(v >= th)
        if s.size:
            s = s[self.t - net.t_last_spike[s] > p.T_REF_MS]
        if s.size:
            inc = _gather(net.in_ptr, net.in_ids, s)
            touched += inc.size
            inc = inc[net.alive[inc] & net.is_exc[net.pre[inc]]]
            if inc.size:
                pp, qq = net.post[inc], net.pre[inc]
                net.w[inc] += self.g * net.a_plus_n[pp] * net.x_pre[qq] * (net.w_max_n[pp] - net.w[inc])

            out = _gather(net.out_ptr, net.out_ids, s)
            if out.size:
                dl = net.delay[out]
                order = np.argsort(dl, kind="stable")
                out, dl = out[order], dl[order]
                edges = np.searchsorted(dl, np.arange(2, p.D_MAX + 2))
                start = 0
                for delay in range(1, p.D_MAX + 1):
                    end = edges[delay - 1]
                    if end > start:
                        self.ring[(self.t + delay) % (p.D_MAX + 1)].append(out[start:end])
                    start = end

            net.v[s] = p.V_RESET_MV
            net.theta[s] += p.D_THETA_MV
            net.x_pre[s] += 1.0
            net.y_post[s] += 1.0
            net.t_last_spike[s] = self.t
            net.spike_count[s] += 1
            self.stats["spike_total"] += int(s.size)

        self.stats["syn_touched_last"] = touched
        self.stats["syn_touched_sum"] += touched
        self.stats["ticks"] += 1
        self._buf_spikes.append(s)
        self._buf_touched.append(touched)
        self._buf_ticks += 1
        if self._watch_id is not None:
            self._v_trace.append(float(net.v[self._watch_id]))
            if len(self._v_trace) > p.V_TRACE_TICKS:
                del self._v_trace[:-p.V_TRACE_TICKS]

        self.t += 1
        if self._inj:
            self._expire_stims()
        self._phase_ticks += 1
        limit = p.WAKE_TICKS if self.phase == "wake" else p.SLEEP_TICKS
        if self._phase_ticks >= limit:
            self.set_sleep(self.phase == "wake")
        if self.t % p.SWEEP_TICKS == 0:
            self._slow_sweep()

    def _refresh_inj(self):
        if not self._inj:
            self.i_inj[:] = 0.0
            self._inj_on = False
            return
        self._inj_on = True
        self.i_inj[:] = 0.0
        for ids, amp, _, _rec, _all_sense in self._inj:
            self.i_inj[ids] += amp
        if self.sense_gated:
            self.i_inj[self._sense] = 0.0
        for e in self._inj:
            self._stim_applied(e[3], e[4])

    def _slow_sweep(self):
        p, net = self.p, self.net
        counts = (net.spike_count - self._sweep_base).astype(np.float32)
        self._sweep_base = net.spike_count.copy()
        hz = counts * 1000.0 / p.SWEEP_TICKS
        a = 1.0 if self.t <= p.SWEEP_TICKS else p.RATE_EMA_ALPHA
        net.rate[:] = (1 - a) * net.rate + a * hz
        net.act[:] = (1 - a) * net.act + a * np.minimum(hz / p.ACT_REF_HZ, 1.0)

        if not net.homeostasis:
            net.rebuild_index(self.t)
            return
        rt = np.maximum(net.r_target, 1e-6)
        err = np.clip((net.r_target - net.rate) / rt, -1.0, 1.0)
        err[net.r_target <= 0] = 0.0
        alive = np.flatnonzero(net.alive)
        exc_syn = alive[net.is_exc[net.pre[alive]]]
        used = exc_syn[counts[net.pre[exc_syn]] > 0]
        if used.size and self.phase != "sleep":
            factor = 1.0 + np.clip(p.ETA_SCALING * (net.r_target - net.rate) / rt, -p.SCALING_CLIP, p.SCALING_CLIP)
            factor[net.r_target <= 0] = 1.0
            ps = net.post[used]
            net.w[used] = np.clip(net.w[used] * factor[ps], 0.0, net.w_max_n[ps])

        died = []
        weak = exc_syn[net.w[exc_syn] < p.W_PRUNE_FRAC * net.w_max_n[net.post[exc_syn]]]
        if weak.size:
            died.append(weak)
            net.kill_synapses(weak)
        weak_pre, weak_post = net.pre[weak].copy(), net.post[weak].copy()

        self.g_struct = float(p.STRUCT_BASE * (1.0 + 9.0 * np.exp(-self.age_s / p.STRUCT_AGE_TAU_S)))
        net.rebuild_index(self.t)
        born, died2 = self.structural_update(err)

        self.stats["syn_died_total"] += int(weak.size)
        self.died_per_s += int(weak.size)
        self._died_count += int(weak.size)
        room = p.FRAME_STRUCT_CAP - len(self._buf_died)
        if room > 0:
            self._buf_died.extend(zip(weak_pre[:room].tolist(), weak_post[:room].tolist()))
        self.syn_sample = self._sample_synapses()

    def structural_update(self, e):
        p, net = self.p, self.net
        e = np.asarray(e, np.float32)
        grow_ok = self._update_windup(e)
        G = self.g_struct
        alive = np.flatnonzero(net.alive)
        pre_exc = net.is_exc[net.pre[alive]]
        kE = np.bincount(net.post[alive[pre_exc]], minlength=net.n).astype(np.float32)
        kI = np.bincount(net.post[alive[~pre_exc]], minlength=net.n).astype(np.float32)
        motif = p.EI_MOTIF * kE
        deficit = np.maximum(0.0, motif - kI)
        excess = np.maximum(0.0, kI - motif)
        lo, hi = e > 0, e < 0
        ae = np.abs(e)

        die = [self._prune_incoming(np.where(hi & grow_ok, G * ae * kE, 0.0), kE, True),
               self._prune_incoming(np.where(lo & grow_ok, G * e * excess, 0.0), excess, False)]
        died = np.concatenate(die)
        die_pre, die_post = net.pre[died].copy(), net.post[died].copy()
        n_free = len(net.free)
        net.kill_synapses(died)
        fresh = net.free[n_free:]
        del net.free[n_free:]

        keys = net.pair_keys()
        if self.store_clamped:
            bE = np.empty(0, np.int32)
            bI = np.empty(0, np.int32)
        else:
            bE = self._grow_incoming(np.where(lo & grow_ok, G * e * self._k_target, 0.0), True, keys)
            bI = self._grow_incoming(
                np.where(lo, G * e * deficit,
                         np.where(hi, G * ae * (np.where(grow_ok, p.EI_MOTIF * self._k_target, 0.0) + deficit), 0.0)),
                False, keys)
        born = np.concatenate([bE, bI])
        net.free.extend(fresh)

        self.stats["syn_died_total"] += int(died.size)
        self.stats["syn_born_total"] += int(born.size)
        self.born_per_s, self.died_per_s = int(born.size), int(died.size)
        self._born_count += int(born.size)
        self._died_count += int(died.size)
        cap = p.FRAME_STRUCT_CAP
        room = cap - len(self._buf_died)
        if room > 0:
            self._buf_died.extend(zip(die_pre[:room].tolist(), die_post[:room].tolist()))
        room = cap - len(self._buf_born)
        if room > 0:
            ids = born[:room]
            self._buf_born.extend(zip(net.pre[ids].tolist(), net.post[ids].tolist()))
        return born, died

    def _prune_incoming(self, mean, cap, exc):
        net = self.net
        want = np.minimum(self.rng.poisson(mean), cap.astype(np.int64))
        out = []
        for i in np.flatnonzero(want > 0):
            inc = net.in_ids[net.in_ptr[i]:net.in_ptr[i + 1]]
            inc = inc[net.alive[inc] & (net.is_exc[net.pre[inc]] == exc)]
            m = min(int(want[i]), inc.size)
            if m > 0:
                out.append(inc[np.argpartition(np.abs(net.w[inc]), m - 1)[:m]])
        return np.concatenate(out) if out else np.empty(0, np.int32)

    def _grow_incoming(self, mean, exc, keys):
        p, net = self.p, self.net
        want = self.rng.poisson(mean)
        room = len(net.free) + (net.s_max - net.s_used)
        if int(want.sum()) <= 0 or room <= 0:
            return np.empty(0, np.int32)
        new_pre, new_post = [], []
        for dst, srcs in net.allowed_src.items():
            sl = net.region_slice[dst]
            ids = np.arange(sl.start, sl.stop)
            sel = ids[want[ids] > 0]
            if sel.size == 0:
                continue
            todo = np.repeat(sel, want[sel])
            if exc:
                share = np.array([k for _, k, _ in srcs], float)
                pidx = self.rng.choice(len(srcs), todo.size, p=share / share.sum())
                groups = [(todo[pidx == j],
                           np.arange(net.region_slice[src].start, net.region_slice[src].stop), sig)
                          for j, (src, _k, sig) in enumerate(srcs)]
            else:
                groups = [(todo, ids, p.CONN_SIGMA)]
            for sub, pool, sigma in groups:
                pool = pool[net.is_exc[pool] == exc]
                if sub.size == 0 or pool.size == 0:
                    continue
                for _ in range(8):
                    cand = pool[self.rng.integers(0, pool.size, sub.size)]
                    d2 = (net.x[cand] - net.x[sub]) ** 2 + (net.y[cand] - net.y[sub]) ** 2
                    acc = self.rng.random(sub.size) < (np.exp(-d2 / (2 * sigma ** 2))
                                                       * (1 + p.GROW_BETA * net.act[cand]) / (1 + p.GROW_BETA))
                    new_pre.append(cand[acc])
                    new_post.append(sub[acc])
                    sub = sub[~acc]
                    if sub.size == 0:
                        break
        if not new_pre:
            return np.empty(0, np.int32)
        pre, post = np.concatenate(new_pre), np.concatenate(new_post)
        pk = pre.astype(np.int64) * net.n + post
        ok = ~np.isin(pk, keys) & (pre != post)
        _, first = np.unique(pk[ok], return_index=True)
        sel_idx = np.flatnonzero(ok)[np.sort(first)]
        pre, post = pre[sel_idx], post[sel_idx]
        if pre.size == 0:
            return np.empty(0, np.int32)
        if pre.size > room:
            pre, post = pre[:room], post[:room]
        dist = np.sqrt((net.x[pre] - net.x[post]) ** 2 + (net.y[pre] - net.y[post]) ** 2)
        if exc:
            w = (p.W_GROW_FRAC * net.w_max_n[post]).astype(np.float32)
        else:
            w = -(self.rng.uniform(p.W_INIT_LO, p.W_INIT_HI, pre.size)
                  * net.w_max_n[post] * p.I_GAIN).astype(np.float32)
        return net.add_synapses(pre, post, w, net._delay_from(dist, p), self.t)

    def frame(self):
        return telemetry.make_frame(self)

    def inspect_neuron(self, neuron_id):
        return telemetry.inspect_neuron(self, neuron_id)

    def region_stats(self, name):
        return telemetry.region_stats(self, name)

    def layout(self):
        return telemetry.layout(self)
