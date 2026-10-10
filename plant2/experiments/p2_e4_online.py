"""P2-E4: online memory, recall while learning continues.

Contract: docs/plant2/P2-E4-online-memory.md, frozen at commit cd17cde before this file existed.
The P2-E3 system runs unchanged on one continuous timeline: no quiet(), no settle, one probe slot
after every item, and the reconstruction layer `rec` simulated live in the engine. E3 is subclassed,
not edited. Gated numbers come from the continuous simulation; the replay serves only the settled
twins' P2-E3-comparable readouts.

    python3 -m plant2.experiments.p2_e4_online explore --seeds 42 43
    python3 -m plant2.experiments.p2_e4_online predict
    python3 -m plant2.experiments.p2_e4_online run --seeds 16 17 18 19 20 --gated
    python3 -m plant2.experiments.p2_e4_online verdict
"""
import argparse
import copy
import gzip
import hashlib
import json
import math
import sys
import time

import numpy as np

from plant2 import power, record
from plant2.btsp import btsp_update
from plant2.engine import LIF, GlobalInhibition, Projection
from plant2.experiments import p2_e1_btsp as e1
from plant2.experiments import p2_e2_accommodation as e2
from plant2.experiments import p2_e3_completion as e3
from plant2.readout import replay

BG, SLOT_IN, ROLL, BLOCK, HAB, NOVEL_K, ARMS = 12, 13, 14, 15, 16, 17, 18  # stream ids (contract table)
ARM_TWIN, ARM_TWIN_B, ARM_WPS, ARM_OOD, ARM_DUTY = 1, 2, 3, 4, 5
GATED_SEEDS = (16, 17, 18, 19, 20)
EXPLORE_SEEDS = (42, 43)
HALF = ("recent", "uniform", "cohort", "oldest")

CONTRACT = dict(
    e3.CONTRACT, J_fb=2.80, pre=50, slot=100, post=100, gate_M=(500, 1000), stress_M=(1500, 2000, 3000),
    block=240, sub_blocks=10, sub_mix=(("recent", 5), ("uniform", 5), ("cohort", 10), ("novel", 2), ("blank", 2)),
    age0_blank_subblocks=(0, 2, 4, 6, 8), c500_uniform_spread=(2, 2, 2, 2, 2, 1, 1, 1, 1, 1),
    stress_mix=(("recent", 100), ("uniform", 60), ("novel", 40), ("blank", 20), ("full", 20)), stress_recent_max_age=100,
    pool=200, cohort=100, recent_max_age=20, uniform_min_age=21,
    rolling=(("recent", 0.20), ("uniform", 0.20), ("oldest", 0.10), ("novel", 0.25), ("full", 0.10), ("blank", 0.15)),
    hab_items=50, hab_reps=100, hab_late=10, hab_pause=20, hab_recovery=5, hab_controls=89,
    late_need=8, max_drop=2, recovery_need=3, min_eligible=25, recovery_power_bar=0.8,
    win_mem=50, win_rec=75, win_short=50, joint_missing=40, joint_intrusions=10, novel_lines=10, frac=0.90,
    recall_bar=0.80, spurious_of_A=0.5, ignition_of_meanA=0.5,
    leak_margin=0.05, leak_max_recalled=1, posctl_bar=0.5,
    duty_post=1850, wps_steps=200, ood_each=40, ood_frac=0.3, ood_noise=10, lure_shared=50,
    elig_valid=0.95, mean_A_lo=18.5, mean_A_hi=21.5, final_M=3000,
)
DIGEST = record.digest(CONTRACT)


def stream(seed, *key):
    return e1.stream(seed, *key)


def mask_draw(rng, a):
    return np.sort(rng.choice(a, a // 2, replace=False))


# ---------------------------------------------------------------- schedule (indices only, no simulation)

class Schedule:
    """Every slot of the main timeline, from step indices alone (items are 1-based: item k is learned at step k)."""

    def __init__(self, seed, c):
        self.seed, self.c = seed, c
        perm = stream(seed, BLOCK, 0).permutation(c["pool"]) + 1
        g0, g1 = c["gate_M"]
        self.cohort = {g0: np.sort(perm[:c["cohort"]]), g1: np.sort(perm[c["cohort"]:2 * c["cohort"]])}
        self.reserved = np.sort(np.concatenate(list(self.cohort.values())))
        self.blocks, self.attempts = {}, {}
        for M in c["gate_M"]:
            self.blocks[M], self.attempts[M] = self._build(M, gated=True)
        for M in c["stress_M"]:
            self.blocks[M], self.attempts[M] = self._build(M, gated=False)
        self.block_of = {k: M for M, b in self.blocks.items() for k in b}

    def unreserved(self, lo, hi):
        ids = np.arange(max(lo, 1), hi + 1)
        return ids[~np.isin(ids, self.reserved)] if ids.size else ids

    def oldest_pool(self, k):
        passed = [self.cohort[M] for M in self.c["gate_M"] if k > M]
        return np.concatenate(passed) if passed else np.empty(0, np.int64)

    def eligible(self, kind, k, max_age=None):
        c = self.c
        max_age = c["recent_max_age"] if max_age is None else max_age
        if kind in ("recent", "blank"):
            return self.unreserved(k - max_age, k)
        if kind == "uniform":
            return self.unreserved(1, k - c["uniform_min_age"])
        if kind == "full":
            return self.unreserved(1, k)
        if kind == "oldest":
            return self.oldest_pool(k)
        raise ValueError(kind)

    def _build(self, M, gated):
        c, a = self.c, self.c["a"]
        steps = list(range(M - c["block"] + 1, M + 1))
        for attempt in range(10_000):
            r = stream(self.seed, BLOCK, M, attempt)
            kinds, age0, c500 = [], [], []
            if gated:
                per = c["block"] // c["sub_blocks"]
                for j in range(c["sub_blocks"]):
                    sub = [kd for kd, n in c["sub_mix"] for _ in range(n)]
                    assert len(sub) == per
                    sub = [sub[i] for i in r.permutation(per)]
                    first_blank = sub.index("blank")
                    n_c500 = c["c500_uniform_spread"][j] if M == c["gate_M"][1] else 0
                    u = [i for i, kd in enumerate(sub) if kd == "uniform"][:n_c500]
                    kinds += sub
                    age0 += [j in c["age0_blank_subblocks"] and i == first_blank for i in range(per)]
                    c500 += [i in u for i in range(per)]
            else:
                pool = [kd for kd, n in c["stress_mix"] for _ in range(n)]
                assert len(pool) == c["block"]
                kinds = [pool[i] for i in r.permutation(len(pool))]
                age0 = c500 = [False] * len(kinds)
            used, slots, ok = set(), {}, True
            for k, kind, is0, is500 in zip(steps, kinds, age0, c500):
                slot = dict(kind=kind, block=M, age0=bool(is0), c500=bool(is500), target=None, mask=None, pseudo=None)
                if kind == "novel":
                    if gated:
                        el = np.array([i for i in self.eligible("blank", k) if int(i) not in used], np.int64)
                        if not el.size:
                            ok = False
                            break
                        slot["pseudo"] = (int(r.choice(el)), mask_draw(r, a))
                    slots[k] = slot
                    continue
                if kind == "blank" and is0:
                    el = np.array([k]) if not np.isin(k, self.reserved) else np.empty(0, np.int64)
                elif kind == "blank":
                    el = self.unreserved(k - c["recent_max_age"], k - 1)
                elif kind == "recent":
                    el = self.eligible("recent", k, None if gated else c["stress_recent_max_age"])
                elif kind == "uniform" and is500:
                    el = self.cohort[c["gate_M"][0]]
                elif kind == "cohort":
                    el = self.cohort[M]
                else:
                    el = self.eligible(kind, k)
                el = np.array([i for i in el if int(i) not in used], np.int64)
                if not el.size:
                    ok = False
                    break
                t = int(r.choice(el))
                used.add(t)
                slot.update(target=t, mask=mask_draw(r, a))
                slots[k] = slot
            if ok:
                return slots, attempt
        raise RuntimeError(f"block {M}: no feasible schedule")

    def rolling(self, k):
        c, a = self.c, self.c["a"]
        r = stream(self.seed, ROLL, k)
        u, acc, kind = r.random(), 0.0, "novel"
        for kd, share in c["rolling"]:
            acc += share
            if u < acc:
                kind = kd
                break
        slot = dict(kind=kind, block=None, age0=False, c500=False, target=None, mask=None, pseudo=None)
        if kind != "novel":
            el = self.eligible(kind, k)
            if not el.size:
                slot["kind"] = "novel"
            else:
                slot.update(target=int(r.choice(el)), mask=mask_draw(r, a))
        return slot

    def slot(self, k):
        M = self.block_of.get(k)
        return dict(self.blocks[M][k]) if M is not None else self.rolling(k)


def audit_schedule(sched, upto):
    """Validity 7 rules on the planned (or realised) slots of steps 1..upto. Returns a list of violations."""
    c, bad = sched.c, []
    g0, g1 = c["gate_M"]
    for k in range(1, upto + 1):
        s = sched.slot(k)
        t = s["target"]
        if t is None:
            continue
        if not 1 <= t <= k:
            bad.append((k, "target not yet learned"))
        for M, coh in sched.cohort.items():
            if t in coh:
                allowed = ((s["block"] == M and s["kind"] == "cohort")
                           or (s["kind"] == "oldest" and k > M)
                           or (M == g0 and s["block"] == g1 and s["c500"]))
                if not allowed:
                    bad.append((k, f"cohort {M} item {t} cued as {s['kind']}"))
        if s["pseudo"] is not None and s["pseudo"][0] in sched.reserved:
            bad.append((k, "reserved pseudo-target"))
    for M in c["gate_M"]:
        if M > upto:
            continue
        b = sched.blocks[M]
        kinds = [s["kind"] for s in b.values()]
        want = {kd: n * c["sub_blocks"] for kd, n in c["sub_mix"]}
        if {kd: kinds.count(kd) for kd in want} != want:
            bad.append((M, "block counts"))
        targets = [s["target"] for s in b.values() if s["target"] is not None]
        if len(targets) != len(set(targets)):
            bad.append((M, "repeat within block"))
        if sum(s["age0"] for s in b.values()) != len(c["age0_blank_subblocks"]):
            bad.append((M, "age-0 blank count"))
    return bad


# ---------------------------------------------------------------- the online network

class Online(e3.E3):
    """P2-E3's network on one continuous timeline: no quiet(), a probe slot after every item, rec live."""

    def __init__(self, cfg, seed, schedule=None, post=None, bg_key=None, novel_duty=False):
        super().__init__(cfg, seed)
        c = cfg
        self.rec = LIF("rec", c["m"], d_max=2)
        self.fb_proj = Projection(self.mem, self.rec, [], [], c["J_fb"], 1)
        self.inh = GlobalInhibition(self.mem, self.rec, c["g"] * c["J_fb"], 2)
        self.net.populations.append(self.rec)
        self.net.projections += [self.fb_proj, self.inh]
        self.fb_version = self.proj_version = 0
        self.sched = schedule if schedule is not None else Schedule(seed, c)
        self.post = c["post"] if post is None else post
        self.bg_key = bg_key  # None: stream (seed, 12, k); else a tuple prefix, e.g. (18, 5) for the duty arm
        self.novel_duty = novel_duty
        self.cont_frac, self.log, self.validity_slots = [], [], []
        self.probe_writes = None  # writes-during-probes arm: list of writes when enabled
        self._rec_log = None

    # learning: E3.learn_one statement for statement, without quiet(), then the live projection reload
    def learn_one(self):
        c = self.c
        item = np.sort(self._pat.choice(c["m"], c["a"], replace=False))
        self.items.append(item)
        self._rates(item)
        plateau = np.flatnonzero(self._plat.random(c["n"]) < c["f_q"])
        counts = np.zeros(c["m"], np.int64)
        mem_spk = 0
        for _ in range(c["t_item"]):
            sp = self.net.step(self._learn_in)
            counts[sp["inp"]] += 1
            mem_spk += sp["mem"].size
        eligible = np.flatnonzero(counts >= c["elig_min"])
        pot, dep = btsp_update(self.store, plateau, eligible, self._coin, c["p_flip"])
        self._load()
        self.A.append(plateau)
        self.plateaus_per_cell[plateau] += 1
        lg = self.learn_log
        lg["elig_frac"].append(float((counts[item] >= c["elig_min"]).mean()))
        lg["bg_eligible"].append(int(eligible.size - (counts[item] >= c["elig_min"]).sum()))
        lg["potentiated"].append(pot)
        lg["depressed"].append(dep)
        lg["mem_spikes"].append(mem_spk)
        rng = e1.stream(self.seed, e3.CONT, len(self.items) - 1)
        responded = np.zeros(c["n"], bool)
        for _ in range(c["t_cont"]):
            responded[self.net.step(rng)["mem"]] = True
        R = np.flatnonzero(responded)
        m = c["m"]
        self.fb.add((R[:, None] * m + eligible[None, :]).ravel())
        self.fb_plateau.add((plateau[:, None] * m + eligible[None, :]).ravel())
        self.R.append(R)
        self.E.append(eligible)
        self.cont_offset.append(float(self.mem.vbar.mean() - float(self.mem.v_rest)))
        self.cont_frac.append(float(responded[plateau].mean()) if plateau.size else 0.0)
        self.fb_version += 1
        self.reload_fb()

    def reload_fb(self):
        indptr, post = self.fb.csr()
        self.fb_proj.set_csr(indptr, post, self.c["J_fb"], 1)
        self.proj_version = self.fb_version

    def _step(self, rng):  # E3's raster recording, plus the carried rec when logging (settled twins)
        t = self.net.t - self._t0
        sp = self.net.step(rng)
        s = sp["mem"]
        if s.size:
            self._raster[t] = s.copy()
        if self._rec_log is not None and sp["rec"].size:
            self._rec_log.append(t * self.c["m"] + sp["rec"].astype(np.int64))
        return s

    # one probe slot ------------------------------------------------------------------------
    def novel_item(self, k, key=None):
        r = stream(self.seed, *(key or (NOVEL_K, k)))
        item = np.sort(r.choice(self.c["m"], self.c["a"], replace=False))
        return item, mask_draw(r, self.c["a"])

    def resolve(self, k, slot):
        """Cue lines and scoring targets of a planned slot."""
        s = dict(slot, step=k)
        kind = s["kind"]
        if kind == "blank":
            s["cue"] = None
        elif self.novel_duty:  # every cue slot holds a novel cue of the same form; blank stays blank
            item, mk = self.novel_item(k, (ARMS, ARM_TWIN, k))
            s.update(kind="novel", novel_item=item, cue=item if kind == "full" else item[mk], target=None)
        elif kind == "novel":
            item, mk = self.novel_item(k)
            s.update(novel_item=item, cue=item[mk])
        elif kind == "full":
            s["cue"] = self.items[s["target"] - 1]
        else:
            s["cue"] = self.items[s["target"] - 1][s["mask"]]
        return s

    def run_slot(self, s, bg, sl, post):
        """Pre-gap, slot, post-gap. Returns first-spike ticks of mem and rec in the slot (and inp counts)."""
        c = self.c
        self._rates(None)
        for _ in range(c["pre"]):
            self.net.step(bg)
        onset = dict(offset=float(self.mem.vbar.mean() - float(self.mem.v_rest)), rec_v=float(self.rec.v.mean()),
                     keys=(self.store.keys, self.fb.keys), versions=(self.fb_version, self.proj_version),
                     inh=float(self.inh.weight))
        self._rates(s["cue"])
        fm = np.full(c["n"], -1, np.int64)
        fr = np.full(c["m"], -1, np.int64)
        inp = np.zeros(c["m"], np.int64) if self.probe_writes is not None else None
        late = np.zeros(c["n"], bool) if self.probe_writes is not None else None
        for t in range(c["slot"]):
            sp = self.net.step(sl)
            m_s, r_s = sp["mem"], sp["rec"]
            if late is not None and t >= c["slot"] - 50:
                late[m_s] = True
            if m_s.size:
                m_s = m_s[fm[m_s] < 0]
                fm[m_s] = t
            if r_s.size:
                r_s = r_s[fr[r_s] < 0]
                fr[r_s] = t
            if inp is not None:
                inp[sp["inp"]] += 1
        self._rates(None)
        writes_ok = self.store.keys is onset["keys"][0] and self.fb.keys is onset["keys"][1]
        if self.probe_writes is not None and s["kind"] != "blank":
            self._probe_write(s, inp, late)
        for _ in range(post):
            self.net.step(bg)
        return fm, fr, onset, writes_ok

    def step_k(self, k, score=True):
        """Learn item k, then its interval and probe slot."""
        assert len(self.items) == k - 1
        self.learn_one()
        s = self.resolve(k, self.sched.slot(k))
        bg = stream(self.seed, BG, k) if self.bg_key is None else stream(self.seed, *self.bg_key, k)
        sl = stream(self.seed, SLOT_IN, k)
        fm, fr, onset, writes_ok = self.run_slot(s, bg, sl, self.post)
        if score:
            d = score_slot(self, s, fm, fr)
            d.update(offset=onset["offset"], rec_v=onset["rec_v"], writes_ok=bool(writes_ok),
                     proj_current=bool(onset["versions"][0] == onset["versions"][1]),
                     inh_ok=bool(np.float32(onset["inh"]) == np.float32(self.c["g"] * self.c["J_fb"])))
            self.log.append(d)
        return s

    def run_to(self, M, score=True):
        while len(self.items) < M:
            self.step_k(len(self.items) + 1, score)

    # writes-during-probes stress arm -----------------------------------------------------------
    def _probe_write(self, s, inp, late):
        c, k = self.c, s["step"]
        r = stream(self.seed, ARMS, ARM_WPS, k)
        plateau = np.flatnonzero(r.random(c["n"]) < c["f_q"])
        eligible = np.flatnonzero(inp >= c["elig_min"])
        pot, dep = btsp_update(self.store, plateau, eligible, r, c["p_flip"])
        self._load()
        R = np.flatnonzero(late)
        self.fb.add((R[:, None] * c["m"] + eligible[None, :]).ravel())
        self.fb_version += 1
        self.reload_fb()
        self.probe_writes.append(dict(step=k, plateau=plateau, cue=np.asarray(s["cue"]), eligible=int(eligible.size),
                                      pot=int(pot), dep=int(dep)))


def score_slot(e, s, fm, fr):
    """Per-cue measures of one slot (definitions in the contract)."""
    c = e.c
    R50 = np.flatnonzero((fm >= 0) & (fm < c["win_mem"]))
    rec = np.flatnonzero((fr >= 0) & (fr < c["win_rec"]))
    rec_s = np.flatnonzero((fr >= 0) & (fr < c["win_short"]))
    d = dict(step=s["step"], kind=s["kind"], block=s["block"], age0=s["age0"], c500=s["c500"], n_R50=int(R50.size),
             n_rec=int(rec.size))
    t = s["target"]
    if s["kind"] in HALF or s["kind"] == "full":
        A, item = e.A[t - 1], e.items[t - 1]
        cue = s["cue"]
        missing = np.setdiff1d(item, cue)
        recall = float(np.isin(A, R50).mean()) if A.size else 0.0
        spur = int(np.setdiff1d(R50, A).size)
        miss = int(np.isin(missing, rec).sum())
        intr = int(np.setdiff1d(rec, item).size)
        miss_s = int(np.isin(missing, rec_s).sum())
        intr_s = int(np.setdiff1d(rec_s, item).size)
        joint = miss >= c["joint_missing"] and intr < c["joint_intrusions"]
        d.update(target=t, age=s["step"] - t, A=int(A.size), recall=recall, spurious=spur,
                 spur_ok=bool(spur < c["spurious_of_A"] * A.size), missing=miss, n_missing=int(missing.size),
                 intrusions=intr, joint=bool(joint), joint_50ms=bool(miss_s >= c["joint_missing"] and intr_s < c["joint_intrusions"]),
                 both=bool(recall >= c["recall_bar"] and joint))
    elif s["kind"] == "novel":
        d.update(ignition=int(R50.size), lines=int(rec.size))
        if s.get("pseudo") is not None:
            d.update(leak_A=_leak_A(e, s["pseudo"][0], R50), leak_C=_leak_C(e, *s["pseudo"], rec))
    elif s["kind"] == "blank" and t is not None:
        d.update(target=t, age=s["step"] - t, leak_A=_leak_A(e, t, R50), leak_C=_leak_C(e, t, s["mask"], rec))
        d["recall"] = d["leak_A"]
    return d


def _leak_A(e, t, R50):
    A = e.A[t - 1]
    return float(np.isin(A, R50).mean()) if A.size else 0.0


def _leak_C(e, t, mask, rec):
    item = e.items[t - 1]
    miss = np.setdiff1d(item, item[mask])
    return float(np.isin(miss, rec).sum() / max(1, miss.size))


# ---------------------------------------------------------------- block criteria (O1-O3) and validity 9

def frac(x):
    return float(np.mean(x)) if len(x) else None


def ge(x, bar):
    return x is not None and x >= bar


def block_criteria(e, M):
    c = e.c
    L = [d for d in e.log if d["block"] == M]
    half = [d for d in L if d["kind"] in ("recent", "uniform", "cohort")]
    coh = [d for d in L if d["kind"] == "cohort"]
    nov = [d for d in L if d["kind"] == "novel"]
    blank = [d for d in L if d["kind"] == "blank"]
    meanA = float(np.mean([a.size for a in e.A[:M]]))
    C1 = frac([d["recall"] >= c["recall_bar"] for d in half])
    C2 = frac([d["spur_ok"] for d in half])
    C3 = frac([d["ignition"] < c["ignition_of_meanA"] * meanA for d in nov])
    joint = frac([d["joint"] for d in half])
    D3 = frac([d["lines"] < c["novel_lines"] for d in nov])
    O3m = frac([d["recall"] >= c["recall_bar"] for d in coh])
    O3c = frac([d["joint"] for d in coh])
    f = c["frac"]
    vec = dict(O1_C1=ge(C1, f), O1_C2=ge(C2, f), O1_C3=ge(C3, f), O2_joint=ge(joint, f), O2_D3=ge(D3, f),
               O3_memory=ge(O3m, f), O3_content=ge(O3c, f))
    kinds = {}
    for kd in ("recent", "uniform", "cohort"):
        sub = [d for d in half if d["kind"] == kd]
        kinds[kd] = dict(n=len(sub), C1=frac([d["recall"] >= c["recall_bar"] for d in sub]), joint=frac([d["joint"] for d in sub]),
                         both=frac([d["both"] for d in sub]))
    c500 = [d for d in L if d["c500"]]
    kinds["uniform_cohort500"] = dict(n=len(c500), C1=frac([d["recall"] >= c["recall_bar"] for d in c500]),
                                      joint=frac([d["joint"] for d in c500]))
    leak = dict(recalled=int(sum(d["recall"] >= c["recall_bar"] for d in blank)), L_A=frac([d["leak_A"] for d in blank]),
                L_C=frac([d["leak_C"] for d in blank]), B_A=frac([d["leak_A"] for d in nov]), B_C=frac([d["leak_C"] for d in nov]),
                posctl=frac([e.cont_frac[d["step"] - 1] for d in blank]),
                age0=dict(n=int(sum(d["age0"] for d in blank)), L_A=frac([d["leak_A"] for d in blank if d["age0"]])))
    leak["ok"] = bool(leak["recalled"] <= c["leak_max_recalled"] and None not in (leak["L_A"], leak["B_A"], leak["L_C"], leak["B_C"])
                      and leak["L_A"] <= leak["B_A"] + c["leak_margin"] and leak["L_C"] <= leak["B_C"] + c["leak_margin"]
                      and ge(leak["posctl"], c["posctl_bar"]))
    # reported: cued (recent half cues) against blank targets, by age (0 and 1-20)
    leak["cued_vs_blank_by_age"] = {
        name: dict(cued_recall=frac([d["recall"] for d in half if d["kind"] == "recent" and lo <= d["age"] <= hi]),
                   blank_L_A=frac([d["leak_A"] for d in blank if lo <= d["age"] <= hi]))
        for name, (lo, hi) in (("age0", (0, 0)), ("age1_20", (1, 20)))}
    ages = [d["age"] for d in half if d["kind"] == "recent"]
    return dict(
        n=dict(half=len(half), cohort=len(coh), novel=len(nov), blank=len(blank)), mean_A=meanA,
        rates=dict(C1=C1, C2=C2, C3=C3, joint=joint, D3=D3, O3_memory=O3m, O3_content=O3c,
                   joint_50ms=frac([d["joint_50ms"] for d in half]), both=frac([d["both"] for d in half])),
        vector=vec, per_kind=kinds, leak=leak,
        recent_age_hist=np.bincount(ages, minlength=c["recent_max_age"] + 1).tolist() if ages else [],
        offset_mv=dict(first=frac([d["offset"] for d in L[:24]]), last=frac([d["offset"] for d in L[-24:]]),
                       mean=frac([d["offset"] for d in L])),
        rec_onset_v=frac([d["rec_v"] for d in L]),
        slot_checks=dict(writes_ok=bool(all(d["writes_ok"] for d in L)), proj_current=bool(all(d["proj_current"] for d in L)),
                         inh_ok=bool(all(d["inh_ok"] for d in L))),
    )


# ---------------------------------------------------------------- habituation (O4, O5) on copies

def state_digest(e):
    h = hashlib.sha256()
    for a in (e.store.keys, e.fb.keys, e.fb_plateau.keys, e.mem.vbar, e.mem.v, e.mem.t_last, e.mem.ring, e.rec.v,
              e.rec.t_last, e.rec.ring, e.inp.rate_hz, e.fb_proj.indptr, e.fb_proj.post, e.proj.indptr, e.proj.post):
        h.update(np.ascontiguousarray(a).tobytes())
    h.update(str((e.net.t, len(e.items), e.fb_version, e.proj_version)).encode())
    for g in (e._pat, e._learn_in, e._plat, e._coin):
        h.update(json.dumps(g.bit_generator.state, sort_keys=True, default=str).encode())
    return h.hexdigest()[:16]


def sham_step(e, r, cue, keep_raster=False, onset=None):
    """A copy step: sham encoding (fresh pattern, no plateau, BTSP or feedback write), gaps and the slot.

    `onset`, when a list, receives the mean rec v at slot onset."""
    c = e.c
    pattern = np.sort(r.choice(c["m"], c["a"], replace=False))
    raster = [] if keep_raster else None
    e._rates(pattern)
    for _ in range(c["t_item"] + c["t_cont"]):
        sp = e.net.step(r)
        if raster is not None:
            raster.append((sp["mem"].tolist(), sp["rec"].tolist()))
    e._rates(None)
    for _ in range(c["pre"]):
        sp = e.net.step(r)
        if raster is not None:
            raster.append((sp["mem"].tolist(), sp["rec"].tolist()))
    if onset is not None:
        onset.append(float(e.rec.v.mean()))
    e._rates(cue)
    fm = np.full(c["n"], -1, np.int64)
    fr = np.full(c["m"], -1, np.int64)
    for t in range(c["slot"]):
        sp = e.net.step(r)
        if raster is not None:
            raster.append((sp["mem"].tolist(), sp["rec"].tolist()))
        m_s, r_s = sp["mem"], sp["rec"]
        if m_s.size:
            m_s = m_s[fm[m_s] < 0]
            fm[m_s] = t
        if r_s.size:
            r_s = r_s[fr[r_s] < 0]
            fr[r_s] = t
    e._rates(None)
    for _ in range(c["post"]):
        sp = e.net.step(r)
        if raster is not None:
            raster.append((sp["mem"].tolist(), sp["rec"].tolist()))
    return fm, fr, raster


def hab_selection(S, M):
    c = S.c
    sel = stream(S.seed, HAB, M, 0)
    C = S.sched.unreserved(1, M - c["uniform_min_age"])
    items = sel.choice(C, c["hab_items"], replace=False)
    rest = np.setdiff1d(C, items)
    plans = []
    for x in items:
        Ax = S.A[x - 1]
        ov = np.array([np.intersect1d(Ax, S.A[y - 1]).size for y in rest])
        ties = rest[ov == ov.max()]
        y = int(sel.choice(ties))
        controls = sel.choice(np.setdiff1d(rest, [y]), c["hab_controls"], replace=False)
        mx, my = mask_draw(sel, c["a"]), mask_draw(sel, c["a"])
        mc = [mask_draw(sel, c["a"]) for _ in controls]
        plans.append(dict(x=int(x), y=y, overlap=int(ov.max()), controls=controls.astype(int).tolist(), mx=mx, my=my, mc=mc))
    return plans


def hab_copy(S, M, i, plan, control):
    """Run one habituation copy; returns per-copy-step 'both' outcomes of the slot's target, and step 1's raster."""
    c = S.c
    e = copy.deepcopy(S)
    reps, late, pause, rec_n = c["hab_reps"], c["hab_late"], c["hab_pause"], c["hab_recovery"]
    out, raster1, vbar_x, rec_onset = [], None, [], []
    x, y = plan["x"], plan["y"]
    Ax = e.A[x - 1]
    for s in range(1, reps + pause + 2 * rec_n + 1):
        r = stream(S.seed, HAB, M, i + 1, s)
        if s <= reps:
            if control and 2 <= s <= reps - late:
                t, mk = plan["controls"][s - 2], plan["mc"][s - 2]
            else:
                t, mk = x, plan["mx"]
        elif s <= reps + pause:
            t, mk = None, None
        else:
            j = s - reps - pause
            t, mk = (x, plan["mx"]) if j % 2 == 1 else (y, plan["my"])
        cue = None if t is None else e.items[t - 1][mk]
        fm, fr, raster = sham_step(e, r, cue, keep_raster=(s == 1), onset=rec_onset)
        if s == 1:
            raster1 = raster
        if t is not None:
            sl = dict(kind="recent", target=t, mask=mk, cue=cue, step=M, block=None, age0=False, c500=False, pseudo=None)
            d = score_slot(e, sl, fm, fr)
            out.append((s, t, bool(d["both"]), d["recall"], bool(d["joint"])))
        vbar_x.append(float(e.mem.vbar[Ax].mean() - float(e.mem.v_rest)) if Ax.size else float("nan"))
    glob = float(e.mem.vbar.mean() - float(e.mem.v_rest))
    return out, raster1, dict(assembly_offset_first=vbar_x[0], assembly_offset_rep_end=vbar_x[reps - 1],
                              global_offset_end=glob, rec_v_onset_mean=float(np.mean(rec_onset)),
                              rec_v_onset_last20=float(np.mean(rec_onset[-20:])))


def habituation(S, M, log=print):
    c = S.c
    before = state_digest(S)
    plans = hab_selection(S, M)
    reps, late, pause, rec_n = c["hab_reps"], c["hab_late"], c["hab_pause"], c["hab_recovery"]
    items, rep1_identical = [], True
    per_copy_ok = True
    for i, plan in enumerate(plans):
        d0 = state_digest(S)
        rep, ras_r, info_r = hab_copy(S, M, i, plan, control=False)
        ctl, ras_c, info_c = hab_copy(S, M, i, plan, control=True)
        per_copy_ok &= state_digest(S) == d0
        rep1_identical &= ras_r == ras_c
        R = {s: b for s, t, b, *_ in rep}
        Cc = {s: b for s, t, b, *_ in ctl}
        lw = range(reps - late + 1, reps + 1)
        rx = [reps + pause + j for j in range(1, 2 * rec_n + 1, 2)]
        ry = [reps + pause + j for j in range(2, 2 * rec_n + 1, 2)]
        items.append(dict(  # stream_pos: copy input streams are (seed, 16, M, stream_pos, s), x + 1 in the contract's key
            x=plan["x"], y=plan["y"], stream_pos=i + 1, overlap=plan["overlap"], age_x=M - plan["x"], age_y=M - plan["y"],
            scored=bool(R[1]), L_rep=int(sum(R[s] for s in lw)), L_ctl=int(sum(Cc[s] for s in lw)),
            rec_rep=int(sum(R[s] for s in rx)), rec_ctl=int(sum(Cc[s] for s in rx)),
            col_rep=int(sum(R[s] for s in ry)), col_ctl=int(sum(Cc[s] for s in ry)),
            per_rep_both=[int(R[s]) for s in range(1, reps + 1)],
            per_rep_recall=[round(rc, 4) for s, t, b, rc, j in rep if s <= reps],
            steps=dict(rep=[list(x) for x in rep], ctl=[list(x) for x in ctl]),
            info_rep=info_r, info_ctl=info_c))
        if (i + 1) % 10 == 0:
            log(f"  habituation M={M}: {i + 1}/{len(plans)} items")
    after = state_digest(S)
    return items, dict(main_untouched=bool(before == after and per_copy_ok), rep1_identical=bool(rep1_identical))


def hab_criteria(c, items):
    need, drop, rn, me, f = c["late_need"], c["max_drop"], c["recovery_need"], c["min_eligible"], c["frac"]
    el = [d for d in items if d["scored"] and d["L_ctl"] >= need]
    hab = [d for d in el if d["L_rep"] <= d["L_ctl"] - drop - 1]
    o4_est = len(el) >= me
    o4 = o4_est and len(hab) <= 0.10 * len(el) + 1e-9

    def paired(rep_key, ctl_key):
        e_ = [d for d in items if d[ctl_key] >= rn]
        ok_ = [d for d in e_ if d[rep_key] >= rn]
        est = len(e_) >= me
        return est and len(ok_) >= math.ceil(f * len(e_) - 1e-9), est, len(e_), len(ok_)
    o5r, est_r, n_r, k_r = paired("rec_rep", "rec_ctl")
    o5c, est_c, n_c, k_c = paired("col_rep", "col_ctl")
    # observed per-cue 'both' rates on the control copies' recovery and collateral cues
    rate_r = float(np.mean([d["rec_ctl"] for d in items]) / c["hab_recovery"]) if items else 0.0
    rate_c = float(np.mean([d["col_ctl"] for d in items]) / c["hab_recovery"]) if items else 0.0

    def p0(rate):
        if not 0 < rate < 1:
            return float(rate >= 1)
        return power.p_paired_majority(rate, power.P2E4_ICC, items=c["hab_items"], cues=c["hab_recovery"], need=rn,
                                       min_eligible=me, seeds=1, loads=1, sims=20000, rng_seed=7)
    pr, pc = p0(rate_r), p0(rate_c)
    hab_detail = [d["L_rep"] - d["L_ctl"] for d in el]
    scored = [d for d in items if d["scored"]]
    b = sum(1 for d in scored if d["L_rep"] < need <= d["L_ctl"])
    cc = sum(1 for d in scored if d["L_ctl"] < need <= d["L_rep"])
    rate_pooled = float(np.mean([d["rec_ctl"] + d["col_ctl"] for d in items]) / (2 * c["hab_recovery"])) if items else 0.0
    return dict(
        n_scored=int(sum(d["scored"] for d in items)), n_eligible=len(el), n_habituated=len(hab),
        O4=bool(o4), O4_estimable=bool(o4_est),
        O5_recovery=bool(o5r), O5_recovery_estimable=bool(pr >= c["recovery_power_bar"]), O5_recovery_n=[n_r, k_r],
        O5_collateral=bool(o5c), O5_collateral_estimable=bool(pc >= c["recovery_power_bar"]), O5_collateral_n=[n_c, k_c],
        ctl_rate_recovery=rate_r, ctl_rate_collateral=rate_c, p0_recovery=pr, p0_collateral=pc,
        ctl_rate_pooled=rate_pooled, p0_pooled=p0(rate_pooled),
        diff_hist={str(k): hab_detail.count(k) for k in sorted(set(hab_detail))}, mcnemar_scored=dict(b=b, c=cc),
        recovery_among_habituated=frac([d["rec_rep"] >= rn for d in hab]),
        per_rep_both=np.mean([d["per_rep_both"] for d in items], 0).round(3).tolist() if items else [],
        per_rep_recall=np.mean([d["per_rep_recall"] for d in items], 0).round(4).tolist() if items else [],
        vector_state=dict(
            O4="pass" if o4 else ("fail" if o4_est else "fail (not estimable)"),
            O5_recovery="pass" if o5r else ("fail" if pr >= c["recovery_power_bar"] else "fail (not estimable)"),
            O5_collateral="pass" if o5c else ("fail" if pc >= c["recovery_power_bar"] else "fail (not estimable)")),
        collateral_overlap=np.bincount([d["overlap"] for d in items]).tolist() if items else [],
    )


# ---------------------------------------------------------------- validity helpers

def fb_union_ok(e):
    m = e.c["m"]
    parts = [(r[:, None] * m + E[None, :]).ravel() for r, E in zip(e.R, e.E) if r.size and E.size]
    union = np.unique(np.concatenate(parts)) if parts else np.empty(0, np.int64)
    return bool(np.array_equal(union, e.fb.keys))


def p2e1_digests(c, seed, loads):
    """Forward-store digests of unmodified P2-E1 learning at each load (one learning pass)."""
    plain = e1.E1(dict(c, J=e1.CONTRACT["J"]), seed)
    out = {}
    for M in sorted(loads):
        plain.learn(M)
        out[M] = e3.digest(plain.store.keys)
    return out


def realised_audit(e, upto):
    """Validity 7 on the realised log of the main line."""
    sched, bad = e.sched, list(audit_schedule(e.sched, upto))
    for d in e.log:
        if d["step"] > upto:
            break
        planned = sched.slot(d["step"])
        if d["kind"] != planned["kind"] or d.get("target") != planned["target"]:
            if not (planned["kind"] == "blank" and planned["target"] is None):
                bad.append((d["step"], "realised slot differs from plan"))
    return bad


# ---------------------------------------------------------------- reported arms

def twin_A(S, M, ref_store=None):
    """Settled twin A (P2-E3's run_phase on a copy, carried rec logged) and twin B branched after the settle."""
    c = S.c
    e = copy.deepcopy(S)
    drift = e.settle_drift(M, 1)
    offset_settled = float(e.mem.vbar.mean() - float(e.mem.v_rest))
    B = copy.deepcopy(e)
    e._raster, e._onsets, e._t0 = {}, [], e.net.t
    e._rec_log = []
    out = e2.evaluate(e, M, phase=1)
    n_ticks = e.net.t - e._t0
    raster, onsets = e._raster, list(e._onsets)
    J, g = np.array([c["J_fb"]]), np.array([c["g"]])
    main = e3.readout(e, M, raster, n_ticks, onsets, J, g)[0]
    trace = []
    indptr, post = e.fb.csr()
    replay(raster, n_ticks, indptr, post, c["m"], J, g, [], trace=trace)
    m = c["m"]
    rp = np.unique(np.fromiter((t * m + j for t, _, j in trace), np.int64, len(trace)))
    del trace
    live = np.unique(np.concatenate(e._rec_log)) if e._rec_log else np.empty(0, np.int64)
    # the joint scored from the carried live rec, for the mismatch's effect on the joint
    cues = e3.build_cues(e, M, onsets)
    w = c["rec_window"]
    lt, lj = live // m, live % m
    joint_live = []
    for cue in cues:
        if cue["kind"] != "half":
            continue
        sel = (lt >= cue["onset"]) & (lt < cue["onset"] + w)
        lines = np.unique(lj[sel])
        miss = np.isin(cue["missing"], lines).sum()
        intr = np.setdiff1d(lines, cue["item"]).size
        joint_live.append(miss >= c["joint_missing"] and intr < c["joint_intrusions"])
    res = dict(memory=e3.memory_summary(out), main=main, drift=list(drift), offset_settled=offset_settled,
               replay_mismatch=dict(replay_only=int(np.setdiff1d(rp, live).size), live_only=int(np.setdiff1d(live, rp).size),
                                    replay_spikes=int(rp.size), joint_live=frac(joint_live),
                                    joint_live_minus_replay=(frac(joint_live) - main["joint"]) if joint_live else None),
               swap_plateau=e3.readout(e, M, raster, n_ticks, onsets, J, g, store=e.fb_plateau)[0])
    if ref_store is not None:
        res["swap_reference"] = e3.readout(e, M, raster, n_ticks, onsets, J, g, store=ref_store)[0]
    return res, B


def twin_B(B, S, M):
    """The block's 200 half cues, same masks and order, after the settle, at P2-E3's cue rhythm."""
    c = B.c
    r = stream(S.seed, ARMS, ARM_TWIN_B, M)
    B._rates(None)
    for _ in range(200):
        B.net.step(r)
    online = [d for d in S.log if d["block"] == M and d["kind"] in ("recent", "uniform", "cohort")]
    paired = []
    for d in online:
        k = d["step"]
        sl = dict(S.sched.slot(k), step=k)
        sl["cue"] = B.items[sl["target"] - 1][sl["mask"]]
        B._rates(sl["cue"])
        fm = np.full(c["n"], -1, np.int64)
        fr = np.full(c["m"], -1, np.int64)
        for t in range(c["t_cue"]):
            sp = B.net.step(r)
            m_s, r_s = sp["mem"], sp["rec"]
            if m_s.size:
                m_s = m_s[fm[m_s] < 0]
                fm[m_s] = t
            if r_s.size:
                r_s = r_s[fr[r_s] < 0]
                fr[r_s] = t
        B._rates(None)
        for _ in range(c["t_gap"]):
            B.net.step(r)
        s_ = score_slot(B, sl, fm, fr)
        paired.append((d["kind"], d["recall"] >= c["recall_bar"], s_["recall"] >= c["recall_bar"], d["joint"], s_["joint"]))
    out = {}
    for kd in ("all", "recent", "uniform", "cohort"):
        P = [p for p in paired if kd == "all" or p[0] == kd]
        if not P:
            continue
        mo, ms_, co, cs = (np.array([p[i] for p in P]) for i in (1, 2, 3, 4))
        out[kd] = dict(n=len(P), memory_online=float(mo.mean()), memory_settled=float(ms_.mean()),
                       content_online=float(co.mean()), content_settled=float(cs.mean()),
                       mcnemar_memory=[int((mo & ~ms_).sum()), int((~mo & ms_).sum())],
                       mcnemar_content=[int((co & ~cs).sum()), int((~co & cs).sum())])
    return out


def responder_stats(e, bins=((1, 250), (251, 500), (501, 750), (751, 1000))):
    out = {}
    for lo, hi in bins:
        if len(e.R) < hi:
            continue
        R, A = e.R[lo - 1:hi], e.A[lo - 1:hi]
        jac = [np.intersect1d(r, a).size / max(1, np.union1d(r, a).size) for r, a in zip(R, A)]
        out[f"{lo}-{hi}"] = dict(R=float(np.mean([r.size for r in R])), R_minus_A=float(np.mean([np.setdiff1d(r, a).size for r, a in zip(R, A)])),
                                 jaccard=float(np.mean(jac)), cont_offset=float(np.mean(e.cont_offset[lo - 1:hi])))
    return out


def rolling_summary(e, lo, hi, any_block=False):
    c = e.c
    L = [d for d in e.log if lo <= d["step"] <= hi and (any_block or d["block"] is None) and d["kind"] in HALF]
    return dict(n=len(L), C1=frac([d["recall"] >= c["recall_bar"] for d in L]), joint=frac([d["joint"] for d in L]),
                age_median=float(np.median([d["age"] for d in L])) if L else None)


def retention_by_age(e, bins=((0, 20), (21, 100), (101, 300), (301, 600), (601, 3000))):
    c = e.c
    out = {}
    for lo, hi in bins:
        L = [d for d in e.log if d["kind"] in HALF and lo <= d.get("age", -1) <= hi]
        out[f"{lo}-{hi}"] = dict(n=len(L), C1=frac([d["recall"] >= c["recall_bar"] for d in L]), joint=frac([d["joint"] for d in L]))
    return out


def ood_arm(S):
    """A copy at M with the sham rhythm: lures, 30 % cues and noisy half cues of stored unreserved items."""
    c, M = S.c, len(S.items)
    e = copy.deepcopy(S)
    r0 = stream(S.seed, ARMS, ARM_OOD, 0)
    n = c["ood_each"]
    kinds = np.array(["lure"] * n + ["frac30"] * n + ["noisy"] * n)[r0.permutation(3 * n)]
    targets = r0.choice(S.sched.unreserved(1, M - c["uniform_min_age"]), 3 * n, replace=False)
    res = {"lure": [], "frac30": [], "noisy": []}
    for s, (kd, z) in enumerate(zip(kinds, targets), start=1):
        item = e.items[z - 1]
        others = np.setdiff1d(np.arange(c["m"]), item)
        if kd == "lure":
            cue = np.sort(np.concatenate([r0.choice(item, c["lure_shared"], replace=False),
                                          r0.choice(others, c["a"] - c["lure_shared"], replace=False)]))
        elif kd == "frac30":
            cue = np.sort(r0.choice(item, int(round(c["ood_frac"] * c["a"])), replace=False))
        else:
            half = r0.choice(item, c["a"] // 2, replace=False)
            cue = np.sort(np.concatenate([half[c["ood_noise"]:], r0.choice(others, c["ood_noise"], replace=False)]))
        fm, fr, _ = sham_step(e, stream(S.seed, ARMS, ARM_OOD, 1, s), cue)
        R50 = np.flatnonzero((fm >= 0) & (fm < c["win_mem"]))
        rec = np.flatnonzero((fr >= 0) & (fr < c["win_rec"]))
        A = e.A[z - 1]
        missing = np.setdiff1d(item, cue)
        res[kd].append((float(np.isin(A, R50).mean()) if A.size else 0.0, float(np.isin(missing, rec).mean()) if missing.size else 0.0,
                        int(np.setdiff1d(rec, np.union1d(item, cue)).size)))
    return {kd: dict(n=len(v), C1=frac([x[0] >= c["recall_bar"] for x in v]), recall_median=float(np.median([x[0] for x in v])),
                     regenerated_median=float(np.median([x[1] for x in v])), intrusions_median=float(np.median([x[2] for x in v])))
            for kd, v in res.items()}


def wps_arm(S, main_final):
    """Writes during probe slots: a copy from step M runs wps_steps more steps with probe-slot writes."""
    c, M = S.c, len(S.items)
    e = copy.deepcopy(S)
    e.probe_writes = []
    e.log = []
    e.run_to(M + c["wps_steps"])
    stored = []
    for j, w in enumerate(e.probe_writes):
        fm, fr, _ = sham_step(e, stream(S.seed, ARMS, ARM_WPS, 0, j + 1), w["cue"])
        R50 = np.flatnonzero((fm >= 0) & (fm < c["win_mem"]))
        A = w["plateau"]
        stored.append(float(np.isin(A, R50).mean()) if A.size else 0.0)
    span = (M + 1, M + c["wps_steps"])
    episodes = M + c["wps_steps"] + len(e.probe_writes)
    return dict(writes=len(e.probe_writes), stored_frac=frac([s >= c["recall_bar"] for s in stored]),
                depressed=int(sum(w["dep"] for w in e.probe_writes)), potentiated=int(sum(w["pot"] for w in e.probe_writes)),
                rolling_copy=rolling_summary(e, *span), rolling_main_matched_items=rolling_summary(main_final, *span),
                plateau_episodes=episodes,
                rolling_main_matched_episodes=rolling_summary(main_final, max(M + 1, episodes - 70), episodes + 70,
                                                              any_block=True))


def efficiency(e):
    c = e.c
    bits_item = (math.lgamma(c["m"] + 1) - math.lgamma(c["a"] + 1) - math.lgamma(c["m"] - c["a"] + 1)) / math.log(2)
    M = len(e.items)
    return dict(inherited_window_widths=dict(J="1.45-1.60 mV around 1.525 (about +/-5 %)", J_fb="2.00-3.60 mV around 2.80 (about +/-29 %)"),
                bits_per_item=bits_item, bits_per_feedback_synapse=M * bits_item / max(1, e.fb.size),
                bits_per_potential_synapse=M * bits_item / (c["n"] * c["m"]), feedback_density=e.fb.size / (c["n"] * c["m"]))


def stress_summary(e, M):
    c = e.c
    L = [d for d in e.log if d["block"] == M]
    rec = [d for d in L if d["kind"] == "recent"]
    nov = [d for d in L if d["kind"] == "novel"]
    return dict(recent=dict(n=len(rec), C1=frac([d["recall"] >= c["recall_bar"] for d in rec]), joint=frac([d["joint"] for d in rec]),
                            intrusions_median=float(np.median([d["intrusions"] for d in rec])) if rec else None),
                novel=dict(n=len(nov), D3=frac([d["lines"] < c["novel_lines"] for d in nov]),
                           lines_median=float(np.median([d["lines"] for d in nov])) if nov else None))


# ---------------------------------------------------------------- one seed

def dump_logs(seed, kind, payload):
    """Per-slot logs go to the cache (not the results file), referenced from the record by path and sha256."""
    path = record.cache_dir("p2_e4") / f"seed{seed}_{kind}_{record.now().replace(':', '')}.jsonl.gz"
    data = "\n".join(json.dumps(x, sort_keys=True, default=_jsonable) for x in payload).encode()
    with gzip.open(path, "wb") as f:
        f.write(data)
    return dict(path=str(path), sha256=hashlib.sha256(data).hexdigest())


def _jsonable(x):
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, np.ndarray):
        return x.tolist()
    return str(x)


def run_seed(c, seed, gated, results_path=record.RESULTS, log=print, reported=True):
    if str(results_path) == str(record.RESULTS) and record.digest(c) != DIGEST:
        raise SystemExit("only the contract configuration may write to the results file")
    t0 = time.time()
    g0, g1 = c["gate_M"]
    main = Online(c, seed)
    snaps, loads, validity = {}, {}, {}
    hab_steps = {}
    for M in (g0, g1):
        main.run_to(M)
        S = copy.deepcopy(main)
        snaps[M] = S
        crit = block_criteria(main, M)
        r_ = crit["rates"]
        log(f"seed {seed} M={M}: online C1 {r_['C1']:.3f} C2 {r_['C2']:.3f} C3 {r_['C3']:.3f} joint {r_['joint']:.3f} "
            f"D3 {r_['D3']:.3f} | cohort memory {r_['O3_memory']:.3f} content {r_['O3_content']:.3f} | offset "
            f"{crit['offset_mv']['mean']:.2f} mV | leak ok {crit['leak']['ok']} ({time.time() - t0:.0f} s)")
        d_main = state_digest(main)
        items, hv = habituation(S, M, log)
        hv["main_untouched"] = bool(hv["main_untouched"] and state_digest(main) == d_main)
        hc = hab_criteria(c, items)
        log(f"seed {seed} M={M}: habituation eligible {hc['n_eligible']} habituated {hc['n_habituated']} O4 {hc['O4']} | "
            f"recovery {hc['O5_recovery']} collateral {hc['O5_collateral']} ({time.time() - t0:.0f} s)")
        crit["vector"].update(O4=hc["O4"], O5_recovery=hc["O5_recovery"], O5_collateral=hc["O5_collateral"])
        hab_steps[M] = [dict(x=d["x"], **d.pop("steps")) for d in items]
        loads[str(M)] = dict(block=crit, habituation=hc, hab_items=items, hab_validity=hv, fb_union_ok=fb_union_ok(S),
                             fwd_digest=e3.digest(S.store.keys), fb_digest=e3.digest(S.fb.keys))
    v = validity
    ref_digests = p2e1_digests(c, seed, (g0, g1))
    v["fwd_equals_p2e1"] = all(ref_digests[M] == loads[str(M)]["fwd_digest"] for M in (g0, g1))
    v["mean_elig_frac"] = float(np.mean(main.learn_log["elig_frac"][:g1]))
    v["mean_A"] = float(np.mean([a.size for a in main.A[:g1]]))
    v["elig_ok"] = v["mean_elig_frac"] >= c["elig_valid"]
    v["mean_A_ok"] = c["mean_A_lo"] <= v["mean_A"] <= c["mean_A_hi"]
    v["fb_union_ok"] = all(loads[str(M)]["fb_union_ok"] for M in (g0, g1))
    v["slot_checks_ok"] = all(all(loads[str(M)]["block"]["slot_checks"].values()) for M in (g0, g1)) and all(
        d["writes_ok"] for d in main.log)
    v["main_untouched"] = all(loads[str(M)]["hab_validity"]["main_untouched"] for M in (g0, g1))
    v["rep1_identical"] = all(loads[str(M)]["hab_validity"]["rep1_identical"] for M in (g0, g1))
    v["audit"] = [list(map(str, x)) for x in realised_audit(main, g1)]
    v["audit_ok"] = not v["audit"]
    v["leak_ok"] = all(loads[str(M)]["block"]["leak"]["ok"] for M in (g0, g1))
    v["schedule_attempts"] = {str(M): main.sched.attempts[M] for M in (g0, g1)}
    valid = all(v[k] for k in ("fwd_equals_p2e1", "elig_ok", "mean_A_ok", "fb_union_ok", "slot_checks_ok", "main_untouched",
                               "rep1_identical", "audit_ok", "leak_ok"))
    vec = {M: loads[M]["block"]["vector"] for M in loads}
    logs = dict(main=dump_logs(seed, "main", [d for d in main.log if d["step"] <= g1]),
                habituation=dump_logs(seed, "habituation", [dict(M=M, **x) for M in (g0, g1) for x in hab_steps[M]]))
    rec = dict(experiment="P2-E4", kind="kill_test_seed" if gated else "exploration_seed", seed=seed, gated=gated,
               contract_digest=record.digest(c), loads=loads, validity=v, valid=bool(valid), vector=vec, logs=logs,
               passed=bool(valid and all(all(x.values()) for x in vec.values())), timestamp=record.now(),
               git=record.git_state(), runtime=record.runtime(), wall_s=round(time.time() - t0, 1))
    record.append(rec, results_path)
    log(f"seed {seed} ({'gated' if gated else 'exploration'}): valid={valid} passed={rec['passed']} wall {rec['wall_s']} s")
    if reported:
        run_reported(c, seed, gated, main, snaps, results_path, log)
    return rec


def run_reported(c, seed, gated, main, snaps, results_path, log):
    t0 = time.time()
    out = dict(experiment="P2-E4", kind="reported_arms", seed=seed, gated=gated, contract_digest=record.digest(c), loads={},
               validity={})
    d_main = state_digest(main)
    snap_digest = {M: state_digest(S) for M, S in snaps.items()}
    ref = e3.E3(c, seed)
    ref_stores, ref_tests = {}, {}
    J, g = np.array([c["J_fb"]]), np.array([c["g"]])
    for M in c["gate_M"]:
        ref.learn(M)
        ref_stores[M] = copy.deepcopy(ref.fb)
        t = copy.deepcopy(ref)
        o, raster, n_ticks, onsets, drift = e3.run_phase(t, M)
        ref_tests[M] = dict(memory=e3.memory_summary(o), main=e3.readout(t, M, raster, n_ticks, onsets, J, g)[0])
    out["reference_responders"] = responder_stats(ref)
    log(f"seed {seed}: reference line done ({time.time() - t0:.0f} s)")
    for M in c["gate_M"]:
        S = snaps[M]
        A, B = twin_A(S, M, ref_stores[M])
        out["loads"][str(M)] = dict(twin_A=A, twin_B=twin_B(B, main, M), reference=ref_tests[M],
                                    offset_settled=A["offset_settled"],
                                    offset_online_block=block_criteria(main, M)["offset_mv"]["mean"])
        log(f"seed {seed} M={M}: twin A joint {A['main']['joint']:.3f} (plateau swap {A['swap_plateau']['joint']:.3f}, "
            f"reference swap {A['swap_reference']['joint']:.3f}) replay mismatch {A['replay_mismatch']} ({time.time() - t0:.0f} s)")
    g1 = c["gate_M"][1]
    out["ood"] = ood_arm(snaps[g1])
    out["responders_main"] = responder_stats(main)
    out["retention_main"] = retention_by_age(main)
    out["M250_rolling"] = rolling_summary(main, 221, 250)
    out["efficiency_at_gate"] = efficiency(snaps[g1])
    log(f"seed {seed}: OOD done ({time.time() - t0:.0f} s)")
    out["validity"]["snapshots_untouched"] = all(state_digest(S) == snap_digest[M] for M, S in snaps.items())
    out["validity"]["main_untouched_by_twins"] = state_digest(main) == d_main
    for M in c["stress_M"]:
        main.run_to(M)
        out.setdefault("stress", {})[str(M)] = stress_summary(main, M)
        log(f"seed {seed}: stress M={M} {out['stress'][str(M)]} ({time.time() - t0:.0f} s)")
    out["retention_main_final"] = retention_by_age(main)
    out["efficiency_final"] = efficiency(main)
    out["logs_main_continuation"] = dump_logs(seed, "main_continuation", [d for d in main.log if d["step"] > g1])
    d_snap = state_digest(snaps[g1])
    out["wps"] = wps_arm(snaps[g1], main)
    out["validity"]["snapshot_untouched_by_wps"] = state_digest(snaps[g1]) == d_snap
    log(f"seed {seed}: writes-during-probes {out['wps']['writes']} writes ({time.time() - t0:.0f} s)")
    twin = Online(c, seed, novel_duty=True)
    for M in c["gate_M"]:
        twin.run_to(M, score=False)
        A, _ = twin_A(twin, M)
        out["loads"][str(M)]["novel_duty_twin"] = dict(twin_A=A, fb_size=int(twin.fb.size), fb_main=int(snaps[M].fb.size),
                                                       fwd_digest=e3.digest(twin.store.keys), fb_digest=e3.digest(twin.fb.keys),
                                                       fwd_equals_main=e3.digest(twin.store.keys) == e3.digest(snaps[M].store.keys))
    out["responders_novel_duty"] = responder_stats(twin)
    out["validity"]["novel_duty_fb_union_ok"] = fb_union_ok(twin)
    log(f"seed {seed}: novel-duty twin done ({time.time() - t0:.0f} s)")
    duty = Online(c, seed, post=c["duty_post"], bg_key=(ARMS, ARM_DUTY))
    for M in c["gate_M"]:
        duty.run_to(M)
        A, _ = twin_A(duty, M)
        crit = block_criteria(duty, M)
        out["loads"][str(M)]["duty"] = dict(block=dict(rates=crit["rates"], vector=crit["vector"], offset_mv=crit["offset_mv"],
                                                       leak=crit["leak"], slot_checks=crit["slot_checks"]), twin_A=A)
    out["responders_duty"] = responder_stats(duty)
    out["validity"]["duty_fb_union_ok"] = fb_union_ok(duty)
    out.update(timestamp=record.now(), git=record.git_state(), runtime=record.runtime(), wall_s=round(time.time() - t0, 1))
    record.append(out, results_path)
    log(f"seed {seed}: reported arms done, wall {out['wall_s']} s")
    return out


# ---------------------------------------------------------------- verdict, predictions, guard

LABEL_ORDER = ["ONLINE INDEX FAIL", "ONLINE CONTENT FAIL", "HABITUATION FAIL", "HABITUATION NOT ESTIMABLE", "RECOVERY FAIL",
               "RECOVERY NOT ESTIMABLE"]


def labels(c, recs):
    """Failure labels over all seeds and loads. A NOT ESTIMABLE label applies only when every failure of that family is
    not estimable (the contract's 'fails only because' / 'fails only on'), the same reading for both families."""
    lab = set()
    for r in recs:
        for M, L in r["loads"].items():
            v, h = L["block"]["vector"], L["habituation"]
            if not (v["O1_C1"] and v["O1_C2"] and v["O1_C3"] and v["O3_memory"]):
                lab.add("ONLINE INDEX FAIL")
            if not (v["O2_joint"] and v["O2_D3"] and v["O3_content"]):
                lab.add("ONLINE CONTENT FAIL")
            if not h["O4"]:
                lab.add("HABITUATION FAIL" if h["O4_estimable"] else "HABITUATION NOT ESTIMABLE")
            for part in ("recovery", "collateral"):
                if not h[f"O5_{part}"]:
                    lab.add("RECOVERY FAIL" if h[f"O5_{part}_estimable"] else "RECOVERY NOT ESTIMABLE")
    for fam in ("HABITUATION", "RECOVERY"):
        if f"{fam} FAIL" in lab:
            lab.discard(f"{fam} NOT ESTIMABLE")
    return [x for x in LABEL_ORDER if x in lab]


def gated_records(recs):
    """P2-E4 gated seed records under this contract, the first record per seed (re-runs keep the first records)."""
    first = {}
    for r in recs:
        if (r.get("experiment") == "P2-E4" and r.get("kind") == "kill_test_seed" and r.get("gated") is True
                and r.get("contract_digest") == DIGEST and r["seed"] not in first):
            first[r["seed"]] = r
    return [first[s] for s in sorted(first)]


def verdict(recs, results_path=record.RESULTS, log=print):
    gated = gated_records(recs)
    if sorted(r["seed"] for r in gated) != sorted(GATED_SEEDS):
        raise SystemExit(f"verdict needs exactly the gated seeds {GATED_SEEDS}; have {sorted(r['seed'] for r in gated)}")
    invalid = [r["seed"] for r in gated if not r["valid"]]
    labs = ["INVALID"] if invalid else labels(CONTRACT, gated)
    label = "INVALID" if invalid else ("PASS" if not labs else " + ".join(labs))
    loads = list(gated[0]["vector"])
    vector = {M: {k: all(r["vector"][M][k] for r in gated) for k in gated[0]["vector"][M]} for M in loads}
    per_seed = {r["seed"]: {M: dict(rates=r["loads"][M]["block"]["rates"], per_kind=r["loads"][M]["block"]["per_kind"],
                                    habituation_state=r["loads"][M]["habituation"]["vector_state"]) for M in loads}
                for r in gated}
    rec = dict(experiment="P2-E4", kind="kill_test_verdict", seeds=sorted(r["seed"] for r in gated), verdict=label, labels=labs,
               invalid_seeds=invalid, vector=vector, per_seed=per_seed, contract_digest=DIGEST, timestamp=record.now(),
               git=record.git_state(), runtime=record.runtime())
    record.append(rec, results_path)
    log(f"P2-E4 verdict: {label}")
    return rec


def _hab_fast(c, items, p0_table=None):
    """O4 and O5 exactly as hab_criteria decides them; with p0_table, also the estimability used by the labels."""
    need, drop, rn, me, f = c["late_need"], c["max_drop"], c["recovery_need"], c["min_eligible"], c["frac"]
    el = [d for d in items if d["scored"] and d["L_ctl"] >= need]
    hab = [d for d in el if d["L_rep"] <= d["L_ctl"] - drop - 1]
    out = dict(O4=bool(len(el) >= me and len(hab) <= 0.10 * len(el) + 1e-9), O4_estimable=len(el) >= me)
    for name, rk, ck in (("O5_recovery", "rec_rep", "rec_ctl"), ("O5_collateral", "col_rep", "col_ctl")):
        e_ = [d for d in items if d[ck] >= rn]
        out[name] = bool(len(e_) >= me and sum(d[rk] >= rn for d in e_) >= math.ceil(f * len(e_) - 1e-9))
        if p0_table is not None:
            rate = float(np.mean([d[ck] for d in items]) / c["hab_recovery"])
            out[f"{name}_estimable"] = bool(np.interp(rate, *p0_table) >= c["recovery_power_bar"])
    return out


def _p0_table(c):
    grid = np.round(np.arange(0.50, 1.0001, 0.01), 2)
    vals = [power.p_paired_majority(float(min(r, 0.999)), power.P2E4_ICC, items=c["hab_items"], cues=c["hab_recovery"],
                                    need=c["recovery_need"], min_eligible=c["min_eligible"], seeds=1, loads=1, sims=4000,
                                    rng_seed=7) for r in grid]
    return grid, np.array(vals)


def predictions(recs, draws=300, sims=1500, rng_seed=5, results_path=record.RESULTS, log=print):
    """Full-rule power from the exploration seeds (contract: 'After implementation, before any gated seed').

    O1-O3: exact binomials with the seed effect, per posterior draw of each per-cue rate. O4-O5: a bootstrap of whole
    habituation items from the exploration copies (the item pool itself resampled per draw), five seeds per load. Labels:
    a joint simulation of every criterion with the labels() logic. The logit shift that brings P(PASS) to 0.8 moves every
    per-cue rate together (O1-O3 rates directly; O4-O5 through the beta item model at the shifted 'both' rate).
    """
    c = CONTRACT
    g = record.git_state()
    if g["plant2_dirty"]:
        raise SystemExit("predictions: plant2/ has uncommitted changes")
    first = {}
    for r in recs:
        if (r.get("experiment") == "P2-E4" and r.get("kind") == "exploration_seed" and r.get("contract_digest") == DIGEST
                and r["seed"] not in first):
            first[r["seed"]] = r
    ex = [first[s] for s in sorted(first)]
    if sorted(first) != sorted(EXPLORE_SEEDS):
        raise SystemExit(f"predictions need exploration seeds {EXPLORE_SEEDS}; have {sorted(first)}")
    for r in ex:
        if r["git"]["plant2_tree"] != g["plant2_tree"] or r["git"]["plant2_dirty"]:
            raise SystemExit(f"exploration seed {r['seed']} ran on a different or dirty plant2 tree")
    rng = np.random.default_rng(rng_seed)
    counts = dict(C1=200, C2=200, C3=20, joint=200, D3=20, O3_memory=100, O3_content=100)
    loads = [str(M) for M in c["gate_M"]]
    obs = {M: {k: (int(round(sum(r["loads"][M]["block"]["rates"][k] * counts[k] for r in ex))), counts[k] * len(ex))
               for k in counts} for M in loads}
    items = {M: [d for r in ex for d in r["loads"][M]["hab_items"]] for M in loads}
    table = _p0_table(c)
    index_keys = ("C1", "C2", "C3", "O3_memory")

    def p13(rates):
        return {M: {k: power.p_criterion(counts[k], min(max(rates[M][k], 1e-6), 1 - 1e-6), c["frac"], power.P2E4_SEED_SD) ** 5
                    for k in counts} for M in loads}

    def p45_pool(pool, n_sims):
        ok = np.ones(n_sims, bool)
        for M in loads:
            for _ in range(5):
                for i in range(n_sims):
                    if not ok[i]:
                        continue
                    h = _hab_fast(c, [pool[M][j] for j in rng.integers(0, len(pool[M]), c["hab_items"])])
                    ok[i] = h["O4"] and h["O5_recovery"] and h["O5_collateral"]
        return float(ok.mean())
    p_pass = []
    for _ in range(draws):
        rates = {M: {k: rng.beta(kk + 1, n - kk + 1) for k, (kk, n) in obs[M].items()} for M in loads}
        per = p13(rates)
        pool = {M: [items[M][j] for j in rng.integers(0, len(items[M]), len(items[M]))] for M in loads}
        p_pass.append(float(np.prod([v for M in loads for v in per[M].values()])) * p45_pool(pool, 20))
    # joint label simulation at the posterior
    lab_counts, crit_counts, n_pass = {}, {}, 0
    for _ in range(sims):
        rates = {M: {k: rng.beta(kk + 1, n - kk + 1) for k, (kk, n) in obs[M].items()} for M in loads}
        fake = []
        for _seed in range(5):
            L = {}
            for M in loads:
                eff = power.P2E4_SEED_SD * rng.standard_normal()
                vec = {}
                for k, n in counts.items():
                    lp = math.log(rates[M][k] / (1 - rates[M][k]))
                    vec[k] = bool(rng.binomial(n, 1 / (1 + math.exp(-(lp + eff)))) >= math.ceil(c["frac"] * n - 1e-9))
                h = _hab_fast(c, [items[M][j] for j in rng.integers(0, len(items[M]), c["hab_items"])], table)
                block_vec = dict(O1_C1=vec["C1"], O1_C2=vec["C2"], O1_C3=vec["C3"], O2_joint=vec["joint"], O2_D3=vec["D3"],
                                 O3_memory=vec["O3_memory"], O3_content=vec["O3_content"])
                for k, val in list(block_vec.items()) + [("O4", h["O4"]), ("O5_recovery", h["O5_recovery"]),
                                                          ("O5_collateral", h["O5_collateral"])]:
                    crit_counts[f"{M}:{k}"] = crit_counts.get(f"{M}:{k}", 0) + int(val)
                L[M] = dict(block=dict(vector=block_vec), habituation=h)
            fake.append(dict(loads=L))
        labs = labels(c, fake)
        n_pass += not labs
        for lb in labs:
            lab_counts[lb] = lab_counts.get(lb, 0) + 1
    # one common logit shift of all per-cue rates for P(PASS) >= 0.8
    mean_rates = {M: {k: (kk + 1) / (n + 2) for k, (kk, n) in obs[M].items()} for M in loads}
    both = {M: float(np.mean([(d["L_ctl"] / c["hab_late"] + d["rec_ctl"] / c["hab_recovery"] + d["col_ctl"] / c["hab_recovery"]) / 3
                              for d in items[M]])) for M in loads}

    def p_full(delta):
        sh = lambda p: 1 / (1 + math.exp(-(math.log(min(max(p, 1e-6), 1 - 1e-6) / (1 - min(max(p, 1e-6), 1 - 1e-6))) + delta)))
        r_ = {M: {k: sh(p) for k, p in mean_rates[M].items()} for M in loads}
        per = p13(r_)
        p = float(np.prod([v for M in loads for v in per[M].values()]))
        for M in loads:
            b = sh(both[M])
            kw = dict(items=c["hab_items"], min_eligible=c["min_eligible"], seeds=5, loads=1, sims=2000)
            p *= power.p_paired_late_window(b, power.P2E4_ICC, rng_seed=11, **kw)
            p *= power.p_paired_majority(b, power.P2E4_ICC, cues=c["hab_recovery"], need=c["recovery_need"], rng_seed=21, **kw)
            p *= power.p_paired_majority(b, power.P2E4_ICC, cues=c["hab_recovery"], need=c["recovery_need"], rng_seed=31, **kw)
        return p, r_, {M: sh(both[M]) for M in loads}
    lo_d, hi_d = -6.0, 6.0
    if p_full(hi_d)[0] < 0.8:
        shift = dict(delta="unreachable")
    else:
        for _ in range(30):
            mid = (lo_d + hi_d) / 2
            if p_full(mid)[0] >= 0.8:
                hi_d = mid
            else:
                lo_d = mid
        pf, r_, b_ = p_full(hi_d)
        shift = dict(delta=round(hi_d, 3), p_pass_model=pf, rates=r_, both=b_)
    p_pass = np.array(p_pass)
    rec = dict(experiment="P2-E4", kind="power_predictions", exploration_seeds=sorted(first),
               exploration_trees=sorted({r["git"]["plant2_tree"] for r in ex}), observed=obs, both_rate_control=both,
               p_criterion_5seeds={k: v / (5 * sims) for k, v in crit_counts.items()},
               p_label={k: v / sims for k, v in lab_counts.items()}, p_pass_simulated=n_pass / sims,
               p_pass_median=float(np.median(p_pass)), p_pass_interval_5_95=[float(x) for x in np.quantile(p_pass, [0.05, 0.95])],
               p_index_pass={M: float(np.prod([p13(mean_rates)[M][k] for k in index_keys])) for M in loads},
               logit_shift_for_p08=shift, draws=draws, sims=sims, contract_digest=DIGEST, plant2_tree=g["plant2_tree"],
               timestamp=record.now(), git=g, runtime=record.runtime())
    record.append(rec, results_path)
    log(f"P2-E4 predictions: P(PASS) median {rec['p_pass_median']:.3g} {rec['p_pass_interval_5_95']}; simulated "
        f"{rec['p_pass_simulated']:.3g}; labels {rec['p_label']}; shift {shift.get('delta')}")
    return rec


CONTRACT_FROZEN_AT = "cd17cde"
CONTRACT_PATH = "docs/plant2/P2-E4-online-memory.md"


def _git(*args):
    import subprocess
    return subprocess.run(["git", "-C", str(record.REPO), *args], capture_output=True, text=True)


def guard(recs):
    """--gated refuses unless: plant2/ is committed; the contract is unmodified in the working tree and, since its frozen
    commit, has only had lines added (the appended predictions); and HEAD's results file holds a power_predictions record
    made under this contract digest and this plant2 tree. Appends by a parallel gated seed do not trip it."""
    g = record.git_state()
    if g["plant2_dirty"]:
        raise SystemExit("guard: plant2/ has uncommitted changes")
    if _git("diff", "--quiet", "HEAD", "--", CONTRACT_PATH).returncode != 0:
        raise SystemExit("guard: the contract differs from HEAD")
    num = _git("diff", "--numstat", CONTRACT_FROZEN_AT, "HEAD", "--", CONTRACT_PATH).stdout.split()
    if num and int(num[1]) != 0:
        raise SystemExit("guard: the frozen contract text was changed (only additions are allowed)")
    head = _git("show", "HEAD:bench/results/plant2.jsonl").stdout.splitlines()
    pred = [json.loads(l) for l in head if '"power_predictions"' in l]
    pred = [p for p in pred if p.get("experiment") == "P2-E4"]
    if not pred:
        raise SystemExit("guard: no committed power_predictions record")
    p = pred[-1]
    if p["contract_digest"] != DIGEST or p["plant2_tree"] != g["plant2_tree"]:
        raise SystemExit("guard: predictions were made under a different contract digest or plant2 tree")
    return {r["seed"] for r in gated_records(recs)}


def load_records(path=record.RESULTS):
    out = []
    for line in open(path):
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:  # a torn line from a concurrent append is skipped, never repaired
            continue
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("explore", "run"):
        p = sub.add_parser(name)
        p.add_argument("--seeds", type=int, nargs="+", required=True)
        p.add_argument("--gated", action="store_true")
        p.add_argument("--no-reported", action="store_true")
        p.add_argument("--owner-ruled-rerun", action="store_true", help="only with the owner's written ruling")
    sub.add_parser("predict")
    sub.add_parser("verdict")
    a = ap.parse_args(argv)

    def log(msg):
        print(f"[{record.now()}] {msg}", flush=True)
    if a.cmd == "explore":
        for s in dict.fromkeys(a.seeds):
            if s in GATED_SEEDS:
                raise SystemExit("exploration may not use gated seeds")
            run_seed(CONTRACT, s, gated=False, log=log, reported=not a.no_reported)
    elif a.cmd == "run":
        if not a.gated:
            raise SystemExit("use 'explore' for non-gated seeds")
        for s in dict.fromkeys(a.seeds):
            if s not in GATED_SEEDS:
                raise SystemExit(f"{s} is not a gated seed")
            done = guard(load_records())  # re-checked before every seed
            marker = record.cache_dir("p2_e4") / f"gated_seed{s}.started"
            if s in done or (marker.exists() and not a.owner_ruled_rerun):
                raise SystemExit(f"seed {s} was already started or recorded (each gated seed runs once)")
            marker.write_text(record.now())
            run_seed(CONTRACT, s, gated=True, log=log)
    elif a.cmd == "predict":
        predictions(load_records(), log=log)
    elif a.cmd == "verdict":
        verdict(load_records(), log=log)


if __name__ == "__main__":
    sys.exit(main())
