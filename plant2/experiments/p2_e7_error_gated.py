"""P2-E7 prediction-gated forward eligibility with a conserved flip budget; run, summary, riders.

Contract: docs/plant2/P2-E7-error-gated-eligibility.md, constants in docs/plant2/P2-E7-frozen.json.
Stage 1 learns the F10 candidate, stage 2 every other trajectory (worker processes), stage 3 the
coordinator tests every arm and load from persisted states. Every artifact goes through
plant2.evidence; results are append-only.

    python -m plant2.experiments.p2_e7_error_gated run --seed 121 [--workers 4]
    python -m plant2.experiments.p2_e7_error_gated summary
    python -m plant2.experiments.p2_e7_error_gated riders --seed 121
"""
import argparse
import copy
import hashlib
import json
import os
import re
import subprocess
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from analysis import p2r1_replay as r1
from plant2 import evidence, record
from plant2.experiments import p2_e1_btsp as e1
from plant2.experiments import p2_e3_completion as e3
from plant2.experiments import p2_e5_structured as e5
from plant2.experiments import p2_e6 as e6
from plant2.readout import replay

FROZEN_PATH = "docs/plant2/P2-E7-frozen.json"
FROZEN = json.loads((record.REPO / FROZEN_PATH).read_text())
CONTRACT = dict(e5.CONTRACT)
LOADS = tuple(FROZEN["loads"])
ARMS = tuple(dict.fromkeys(a for arms in FROZEN["arms"].values() for a in arms))
REGISTRY = (FROZEN["seeds"]["development"], FROZEN["seeds"]["held_out"], *FROZEN["seeds"]["gated"])
GATED = tuple(FROZEN["seeds"]["gated"])
STREAMS = FROZEN["streams"]
MECH = FROZEN["mechanism"]
RESULTS = record.REPO / "bench/results/p2e7.jsonl"
EVIDENCE = record.REPO / "bench/results/p2e7"
PIN_BASELINE = ["plant2/engine.py", "plant2/btsp.py", "plant2/readout.py", "plant2/record.py",
                "plant2/experiments/p2_e1_btsp.py", "plant2/experiments/p2_e2_accommodation.py",
                "plant2/experiments/p2_e3_completion.py", "plant2/experiments/p2_e4_online.py",
                "plant2/experiments/p2_e5_structured.py"]
PIN_CONTRACT = ["plant2/experiments/p2_e6.py", "plant2/evidence.py", "analysis/p2r1_replay.py"]
# The contract text is append-only after its freezing commit: the frozen blob must be a prefix of the
# current file, and the current file must itself be committed at HEAD (so every appended note is in history).
PIN_CONTRACT_DOC = [FROZEN["contract_path"]]
PIN_FROZEN_JSON = [FROZEN_PATH]
FROZEN_JSON_COMMIT = "e38a6b0"
PIN_SELF = ["plant2/experiments/p2_e7_error_gated.py", "analysis/p2e7_riders.py"]
EMPTY = np.empty(0, np.int64)
IntegrityError, ResourceStop, require = e6.IntegrityError, e6.ResourceStop, e6.require


# ---------------------------------------------------------------- generators

class _State:
    def __init__(self, owner):
        self._o = owner

    @property
    def state(self):
        return dict(generator="p2e7_mixed", seed=self._o.seed, k=self._o.k)


class MixedGen:
    """Odd 1-based episodes: F10 exemplar (k + 1) / 2; even: sorted draw from stream (seed, 36, k)."""

    def __init__(self, seed, m, a, s, F):
        self.seed, self.m, self.a, self.F = seed, m, a, F
        self.family_gen = e5.FamilyGen(seed, m, a, s, F)
        self.protos, self.union = self.family_gen.protos, self.family_gen.union
        self.k, self.labels, self.fam = 0, [], []
        self.bit_generator = _State(self)

    @staticmethod
    def subset(k):
        return "F10" if k % 2 else "independent"

    def choice(self, m, a, replace=False):
        if m != self.m or a != self.a or replace:
            raise ValueError("the mixed generator only draws items of the configured size without replacement")
        self.k += 1
        label = self.subset(self.k)
        self.labels.append(label)
        if label == "F10":
            j = (self.k + 1) // 2
            self.fam.append(self.family_gen.family(j))
            return self.family_gen.exemplar(j)
        self.fam.append(None)
        return np.sort(e1.stream(self.seed, STREAMS["mixed_independent"], self.k).choice(m, a, replace=False))


def make_gen(condition, cfg, seed):
    spec = FROZEN["conditions"][condition]
    if condition == "mixed":
        return MixedGen(seed, cfg["m"], cfg["a"], spec["s"], spec["F"])
    return e5.FamilyGen(seed, cfg["m"], cfg["a"], spec["s"], spec["F"]) if spec else None


def _set_gen(e, condition):
    if condition not in FROZEN["conditions"]:
        raise ValueError("unknown condition")
    gen = make_gen(condition, e.c, e.seed)
    if gen is not None:
        e._pat = gen


# ---------------------------------------------------------------- mechanism helpers

def predict_set(raster, store, m):
    """G(x): lines the frozen readout fires at ticks 0..74 from the memory raster through the feedback store."""
    call = MECH["replay_call"]
    indptr, post = store.csr()
    trace = []
    cue = dict(onset=0, item=EMPTY, cue=EMPTY, missing=EMPTY, other_missing=EMPTY)
    replay(raster, call["n_ticks"], indptr, post, m, np.array(call["J"]), np.array(call["g"]), [cue],
           window=call["window"], short=call["short"], span=call["span"], trace=trace)
    last = MECH["prediction_window_ticks"] - 1
    return np.unique(np.array([j for t, _, j in trace if t <= last], np.int64))


def veto_probability(n_eligible, n_kept):
    if n_kept <= 0:
        return float(MECH["p_when_Eprime_empty"])
    return float(min(MECH["p_cap"], MECH["budget_per_eligible"] * n_eligible / n_kept))


def gated_flip_mask(coins, keep, p):
    return (np.asarray(coins) < p) & np.asarray(keep, bool)[:, None]


def drop_random(E, count, seed, k):
    E = np.asarray(E, np.int64)
    return E[e1.stream(seed, STREAMS["random_drop"], k).choice(len(E), int(count), replace=False)]


def drop_history(E, count, H, seed, k):
    E = np.asarray(E, np.int64)
    w = (np.asarray(H)[E] + 1).astype(np.float64)
    return E[e1.stream(seed, STREAMS["history_drop"], k).choice(len(E), int(count), replace=False, p=w / w.sum())]


def load_veto_counts(descriptor):
    """The candidate's persisted per-episode applied |V|, refused unless its digest verifies."""
    return np.asarray(evidence.load_npz_artifact(descriptor)["applied_V_size"], np.int64)


def _frac(num, den):
    return float(num / den) if den else None


# ---------------------------------------------------------------- learners

def _capture_rates(self, active):
    """E6's onset-offset capture: the threshold offset at each cue onset, then the inherited rates."""
    if active is not None and self._probe_A is not None:
        A = self._probe_A[len(self.onset_offsets)]
        offset = self.mem.threshold() - float(self.mem.v_th)
        self.onset_offsets.append(dict(global_mv=float(offset.mean()), assigned_mv=float(offset[A].mean()) if A.size else None))
    e1.E1._rates(self, active)


class Baseline(e3.E3):
    """The literal E3 learner; only the pattern generator is swapped for the condition's."""

    def __init__(self, cfg, seed, condition="F10"):
        super().__init__(cfg, seed)
        _set_gen(self, condition)
        self.condition, self.arm = condition, "baseline"


class _TestBaseline(Baseline):
    """Test-time wrapper: the onset-offset capture and the statistics evaluate_load reads; learning untouched."""

    _rates = _capture_rates


def wrap_for_test(baseline):
    w = copy.deepcopy(baseline)
    w.__class__ = _TestBaseline
    w._probe_A, w.onset_offsets, w.p_history = None, [], []
    m = w.c["m"]
    w.H = np.bincount(np.concatenate(w.E), minlength=m).astype(np.int64) if w.E else np.zeros(m, np.int64)
    return w


class E7(e3.E3):
    """E3 learning with only the toggled lines and their probability replaced by the arm's rule."""

    _rates = _capture_rates

    def __init__(self, cfg, seed, arm="candidate", condition="F10", veto_counts=None):
        super().__init__(cfg, seed)
        if arm not in ARMS or arm == "baseline":
            raise ValueError("unknown gated arm")
        if arm.endswith("_drop") and veto_counts is None:
            raise ValueError("drop controls need the candidate's persisted veto counts")
        _set_gen(self, condition)
        self.arm, self.condition = arm, condition
        self.veto_counts = None if veto_counts is None else np.asarray(veto_counts, np.int64)
        self.H = np.zeros(cfg["m"], np.int64)
        self.episodes = 0
        self.gate_log, self.encoding_rasters, self.cont_counts = [], [], []
        self.input_hashes, self.coin_hashes, self.p_history = [], [], []
        self._probe_A, self.onset_offsets = None, []

    def _proto(self, item):
        fam = getattr(self._pat, "fam", None)
        if not fam or fam[-1] is None:
            return None
        return np.intersect1d(item, self._pat.protos[fam[-1]])

    def _applied(self, E, V, P, k):
        if self.arm == "gate_off":
            return EMPTY
        if self.arm == "label_oracle":
            return np.intersect1d(E, P)
        if self.arm == "random_drop":
            return drop_random(E, self.veto_counts[k - 1], self.seed, k)
        if self.arm == "history_drop":
            return drop_history(E, self.veto_counts[k - 1], self.H, self.seed, k)
        return V

    def learn_one(self):
        c = self.c
        item = np.sort(self._pat.choice(c["m"], c["a"], replace=False))
        self.items.append(item)
        self.net.quiet()
        self._rates(item)
        plateau = np.flatnonzero(self._plat.random(c["n"]) < c["f_q"])
        counts = np.zeros(c["m"], np.int64)
        mem_spk, raster, sensory = 0, {}, hashlib.sha256()
        for tick in range(c["t_item"]):
            sp = self.net.step(self._learn_in)
            counts[sp["inp"]] += 1
            mem_spk += sp["mem"].size
            if tick < MECH["prediction_window_ticks"] and sp["mem"].size:
                raster[tick] = sp["mem"].copy()
            sensory.update(np.asarray([tick, sp["inp"].size], dtype="<i8").tobytes())
            sensory.update(np.asarray(sp["inp"], dtype="<i8").tobytes())
        eligible = np.flatnonzero(counts >= c["elig_min"])
        k = len(self.items)
        teacher = self.fb_plateau if self.arm == "assigned_A_teacher" else self.fb
        G = predict_set(raster, teacher, c["m"])
        V = np.intersect1d(eligible, G)
        P = self._proto(item)
        applied = self._applied(eligible, V, P, k)
        keep = ~np.isin(eligible, applied)
        n_keep = int(keep.sum())
        if self.arm == "gate_off" or (self.arm == "no_conservation" and n_keep):
            p = .5
        else:
            p = veto_probability(eligible.size, n_keep)
        if eligible.size and plateau.size:
            coins = self._coin.random(eligible.size * plateau.size).reshape(eligible.size, plateau.size)
        else:
            coins = np.empty((eligible.size, plateau.size))
        mask = gated_flip_mask(coins, keep, p)
        pot, dep = self.store.toggle((eligible[:, None] * c["n"] + plateau[None, :])[mask])
        self.H[eligible] += 1  # only after the write
        self.episodes += 1
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
        cont = np.zeros(c["n"], np.int64)
        for _ in range(c["t_cont"]):
            cont[self.net.step(rng)["mem"]] += 1
        R = np.flatnonzero(cont)
        m = c["m"]
        self.fb.add((R[:, None] * m + eligible[None, :]).ravel())
        self.fb_plateau.add((plateau[:, None] * m + eligible[None, :]).ravel())
        self.R.append(R)
        self.E.append(eligible)
        self.cont_offset.append(float(self.mem.vbar.mean() - float(self.mem.v_rest)))
        self.encoding_rasters.append(raster)
        self.cont_counts.append(cont.astype(np.int16))
        self.input_hashes.append(sensory.hexdigest())
        self.coin_hashes.append(hashlib.sha256(np.asarray(coins, dtype="<f8").tobytes()).hexdigest())
        EP = None if P is None else np.intersect1d(eligible, P)
        non = None if P is None else np.setdiff1d(eligible, P)
        labels = getattr(self._pat, "labels", None)
        self.gate_log.append(dict(
            E_size=int(eligible.size), G_size=int(G.size), V_size=int(V.size), applied_V_size=int(eligible.size - n_keep),
            p=p, p_capped=p == 1.0, Eprime_empty=n_keep == 0,
            veto_proto_fraction=None if P is None or not V.size else _frac(np.isin(V, P).sum(), V.size),
            proto_predicted=None if EP is None else _frac(np.isin(EP, G).sum(), EP.size),
            nonproto_predicted=None if non is None else _frac(np.isin(non, G).sum(), non.size),
            subset=labels[-1] if labels else None, potentiated=pot, depressed=dep,
            forward_size=self.store.size, feedback_size=self.fb.size))


# ---------------------------------------------------------------- structural check

def structural_fields(e, condition):
    log = list(e.gate_log)
    n = len(log)
    split = 500 if n >= 1000 else n // 2
    early, late = log[:split], log[split:min(n, 1000)]
    mean = lambda xs: float(np.mean(xs)) if xs else 0.0
    vetoed = [g for g in late if g["V_size"] and g["veto_proto_fraction"] is not None]
    total = sum(g["V_size"] for g in vetoed)
    proto_rows = [] if condition == "independent" else [g for g in late if g["subset"] in (None, "F10")]
    pp = [g["proto_predicted"] for g in proto_rows if g["proto_predicted"] is not None]
    npp = [g["nonproto_predicted"] for g in proto_rows if g["nonproto_predicted"] is not None]
    fields = dict(
        mean_V_1_500=mean([g["V_size"] for g in early]), mean_V_501_1000=mean([g["V_size"] for g in late]),
        max_V=max((g["V_size"] for g in log), default=0),
        veto_precision_501_1000=_frac(sum(round(g["veto_proto_fraction"] * g["V_size"]) for g in vetoed), total),
        proto_predicted_501_1000=float(np.mean(pp)) if pp else None,
        nonproto_predicted_501_1000=float(np.mean(npp)) if npp else None,
        veto_episode_fraction=_frac(sum(g["V_size"] > 0 for g in log), n) or 0.0,
        veto_episode_fraction_501_1000=_frac(sum(g["V_size"] > 0 for g in late), len(late)) or 0.0,
        veto_episode_fraction_independent_subset=None, veto_episode_fraction_independent_subset_501_1000=None,
        empty_Eprime_episodes=[k for k, g in enumerate(log) if g["Eprime_empty"]],
        p_capped_episodes=sum(bool(g["p_capped"]) for g in log), first_engagement_by_family={})
    if condition == "mixed":
        ind = [g for g in log if g["subset"] == "independent"]
        fields["veto_episode_fraction_independent_subset"] = _frac(sum(g["V_size"] > 0 for g in ind), len(ind)) or 0.0
        ind = [g for g in late if g["subset"] == "independent"]
        fields["veto_episode_fraction_independent_subset_501_1000"] = _frac(sum(g["V_size"] > 0 for g in ind), len(ind)) or 0.0
    if condition != "independent":
        F = FROZEN["conditions"][condition]["F"]
        first = {f: None for f in range(F)}
        for k, g in enumerate(log):
            if condition == "mixed":
                if k % 2:
                    continue
                f = (k // 2 + 1) % F
            else:
                f = (k + 1) % F
            if g["V_size"] and first[f] is None:
                first[f] = k
        fields["first_engagement_by_family"] = first
    return fields


KILL_WINDOW = "501-1000"


def _window(fields, name):
    """The kill table's 501-1,000 value; a field dict without it (built before the window field existed) gives its whole-run value."""
    return fields.get(name + "_501_1000", fields.get(name))


def structural_kills(fields, condition):
    s = FROZEN["structural_kill"]
    fired = []
    if condition == "F10":
        if fields["mean_V_501_1000"] < s["min_mean_V"]:
            fired.append("no engagement")
        if fields["veto_precision_501_1000"] is not None and fields["veto_precision_501_1000"] < s["min_veto_precision"]:
            fired.append("contamination-driven veto")
        if fields["nonproto_predicted_501_1000"] is not None and fields["nonproto_predicted_501_1000"] > s["max_nonproto_predicted"]:
            fired.append("saturated teacher")
        if fields["proto_predicted_501_1000"] is not None and fields["proto_predicted_501_1000"] < s["min_proto_predicted"]:
            fired.append("no structure")
    elif condition == "independent":
        if _window(fields, "veto_episode_fraction") > s["max_veto_episode_fraction_uncorrelated"]:
            fired.append("false engagement")
    elif condition == "mixed":
        value = _window(fields, "veto_episode_fraction_independent_subset")
        if value is not None and value > s["max_veto_episode_fraction_uncorrelated"]:
            fired.append("false engagement, mixed")
    return fired


# ---------------------------------------------------------------- scoring

def recompute_criteria(rows, cfg=None):
    half = [r for r in rows if r["kind"] == "half"]
    old = [r for r in half if r["oldest"]]
    c1 = lambda r: r["recall50"] >= e1.BARS["recall"]
    c2 = lambda r: r["spurious50"] < e1.BARS["spurious_of_A"] * r["A_size"]
    out = dict(n_cues=len(half), n_oldest_cues=len(old), C1_count=sum(map(c1, half)), C2_count=sum(map(c2, half)),
               joint_index_count=sum(c1(r) and c2(r) for r in half),
               C4_recall_count=sum(map(c1, old)), C4_spurious_count=sum(map(c2, old)))
    for name in ("C1", "C2", "joint_index"):
        out[name] = _frac(out[name + "_count"], len(half))
    for name in ("C4_recall", "C4_spurious"):
        out[name] = _frac(out[name + "_count"], len(old))
    return out


def subset_scores(rows, labels):
    half = [r for r in rows if r["kind"] == "half"]
    return {s: recompute_criteria([r for r in half if labels[r["index_0based"]] == s]) for s in ("F10", "independent")}


def screen(loads, sanity, structural, uniform, invalid=False, checkpoints=LOADS):
    """The frozen development screen. Missing evidence never becomes a success."""
    bars, mg = FROZEN["bars"], FROZEN["margins"]
    by = {(r["condition"], r["arm"], r["M"]): r for r in loads}
    missing = [f"{c}/{a}/{M}" for c, arms in FROZEN["arms"].items() for a in arms for M in checkpoints if (c, a, M) not in by]
    v = {}
    invalid = bool(invalid) or not uniform or any(not r.get("integrity", False) for r in loads)
    ge = lambda x, y: bool(x + 1e-12 >= y)
    for M in checkpoints:
        B, O = by.get(("F10", "baseline", M)), by.get(("F10", "gate_off", M))
        if B and O and B["forward_sha256"] != O["forward_sha256"]:
            invalid = True
        for cond in ("F10", "independent"):
            C, B = by.get((cond, "candidate", M)), by.get((cond, "baseline", M))
            if C:
                for k, bar in bars.items():
                    v[f"index/{cond}/{M}/{k}"] = ge(C["index"][k], bar)
            if C and B:
                v[f"index/{cond}/{M}/C1_nonregression"] = ge(C["index"]["C1"], B["index"]["C1"] - mg["C1_nonregression"])
                if cond == "independent":
                    v[f"index/{cond}/{M}/C2_nonregression"] = ge(C["index"]["C2"], B["index"]["C2"] - mg["independent_C2_nonregression"])
                    for k in ("joint", "D4"):
                        v[f"content/{cond}/{M}/{k}_nonregression"] = ge(
                            C["content"]["inherited"][k], B["content"]["inherited"][k] - mg[f"independent_content_{k}_nonregression"])
        C, B = by.get(("mixed", "candidate", M)), by.get(("mixed", "baseline", M))
        if C and B:
            for k in ("C1", "C2"):
                v[f"index/mixed/{M}/independent_subset_{k}_cues"] = (
                    B["index_by_subset"]["independent"][k + "_count"] - C["index_by_subset"]["independent"][k + "_count"]
                    < mg["mixed_independent_subset_index_nonregression_cues"])
            v[f"content/mixed/{M}/independent_subset_joint_cues"] = (
                B["content_by_subset"]["independent"]["joint_count"] - C["content_by_subset"]["independent"]["joint_count"]
                < mg["mixed_independent_subset_content_nonregression_cues"])
        for cond in ("F10", "independent", "mixed"):
            for arm in FROZEN["arms"][cond]:
                r = by.get((cond, arm, M))
                for k, ok in (r["protocol"].items() if r else ()):
                    if ok is not None:
                        v[f"protocol/{cond}/{arm}/{M}/{k}"] = bool(ok)
    last = checkpoints[-1]
    C = by.get(("F10", "candidate", last))
    if C:
        for name, arm, margin in (("baseline", "baseline", mg["F10_C2_vs_baseline"]), ("random", "random_drop", mg["F10_C2_vs_random"]),
                                  ("history", "history_drop", mg["F10_C2_vs_history"])):
            ctl = by.get(("F10", arm, last))
            if ctl:
                v[f"index/F10/{last}/C2_vs_{name}"] = ge(C["index"]["C2"], ctl["index"]["C2"] + margin)
                if name != "history":
                    v[f"index/F10/{last}/joint_vs_{name}"] = ge(C["index"]["joint_index"], ctl["index"]["joint_index"] + mg["F10_joint_vs_each"])
        B = by.get(("F10", "baseline", last))
        if B:
            v[f"index/F10/{last}/C4_recall_nonregression"] = ge(C["index"]["C4_recall"], B["index"]["C4_recall"] - mg["F10_M1000_C4_recall_nonregression"])
    for name in ("wrong_label", "empty_store"):
        if name not in sanity:
            missing.append("sanity/" + name)
    if "wrong_label" in sanity:
        v["sanity/wrong_label_C1"] = bool(sanity["wrong_label"]["C1"] < FROZEN["sanity"]["wrong_label_C1_strict_upper"])
        invalid |= not sanity["wrong_label"].get("count_preserved", True)
    if "empty_store" in sanity:
        v["sanity/empty_store_responders"] = sanity["empty_store"]["responders"] == FROZEN["sanity"]["empty_store_responders"]
        invalid |= not sanity["empty_store"].get("stores_empty", True)
    for cond in ("F10", "independent", "mixed"):
        if cond not in structural:
            missing.append("structural/" + cond)
        for rule in structural.get(cond, ()):
            v[f"structural/{cond}/{rule}"] = False
    failed = [k for k, ok in v.items() if not ok]
    verdict = "INVALID" if invalid else "FEASIBILITY FAIL" if failed else "PARTIAL" if missing else "FEASIBILITY PASS"
    out = dict(verdict=verdict, failed=failed, missing=missing, vectors=v, complete=not missing, integrity=not invalid)
    fired = any(structural.get(c) for c in ("F10", "independent", "mixed"))
    if C and .70 <= C["index"]["C2"] < .90 and not fired:
        out["informative"] = True
    return out


# ---------------------------------------------------------------- provenance and the seed guard

def _git(*args):
    p = subprocess.run(["git", "-C", str(record.REPO), *args], capture_output=True)
    return p.stdout if p.returncode == 0 else None


def source_manifest(require_committed=False):
    """Every pinned file's SHA-256 and the blob comparison it passed. All git reads happen here."""
    files = {}
    for paths, pin, rev in ((PIN_BASELINE, "55e16eb", FROZEN["source_baseline"]),
                            (PIN_CONTRACT, "contract", FROZEN["contract_commit"]),
                            (PIN_CONTRACT_DOC, "contract_append_only", FROZEN["contract_commit"]),
                            (PIN_FROZEN_JSON, "frozen_json", FROZEN_JSON_COMMIT), (PIN_SELF, "self", "HEAD")):
        for path in paths:
            raw = (record.REPO / path).read_bytes()
            blob = _git("cat-file", "blob", f"{rev}:{path}")
            equal = raw == blob
            if pin == "contract_append_only":
                head_blob = _git("cat-file", "blob", f"HEAD:{path}")
                equal = blob is not None and raw.startswith(blob) and raw == head_blob
            passed = True if pin == "self" and not require_committed else equal
            files[path] = dict(pin=pin, rev=rev, sha256=hashlib.sha256(raw).hexdigest(), passed=bool(passed),
                               equals_pinned_blob=bool(raw == blob),
                               pinned_blob_sha256=hashlib.sha256(blob).hexdigest() if blob is not None else None)
            if pin == "contract_append_only":
                files[path]["append_only_ok"] = bool(equal)
                files[path]["appended_bytes"] = (len(raw) - len(blob)) if blob is not None else None
    if require_committed:
        bad = [p for p, f in files.items() if not f["passed"]]
        if bad:
            raise ValueError("uncommitted or drifted source: " + ", ".join(bad))
    commit = _git("rev-parse", "HEAD")
    head = commit.decode().strip() if commit else None
    return dict(commit=head, files=files, require_committed=require_committed,
                self_files={p: dict(sha256=files[p]["sha256"], committed_at_head=files[p]["equals_pinned_blob"], head=head)
                            for p in PIN_SELF},
                code_sha256=hashlib.sha256(r1.json_bytes({p: f["sha256"] for p, f in files.items()})).hexdigest())


def read_records(path=RESULTS, committed=False):
    if committed:
        try:
            rel = Path(path).resolve().relative_to(record.REPO)
        except ValueError:
            return []
        raw = _git("show", f"HEAD:{rel}")
        raw = raw.decode() if raw else ""
    else:
        raw = Path(path).read_text() if Path(path).exists() else ""
    return [json.loads(line) for line in raw.splitlines() if line.strip()]


def _passing(records, seed, code):
    return [r for r in records if r.get("kind") == "seed_screen" and r.get("seed") == seed and r.get("full_size")
            and r.get("source", {}).get("code_sha256") == code and r.get("screen", {}).get("verdict") == "FEASIBILITY PASS"]


def seed_guard(seed, manifest, committed, existing):
    if seed not in REGISTRY:
        raise ValueError(f"seed {seed} is outside the P2-E7 registry {REGISTRY}")
    for r in list(committed) + list(existing):
        if r.get("kind") == "seed_screen" and r.get("seed") in REGISTRY and r.get("screen", {}).get("verdict") == "INVALID":
            raise ValueError(f"an INVALID screen on seed {r['seed']} locks every remaining seed")
    if any(r.get("kind") == "seed_started" and r.get("seed") == seed and r.get("full_size") for r in existing):
        raise ValueError(f"seed {seed} already has a full-size attempt; a rerun needs an explicit owner ruling")
    code = manifest["code_sha256"]
    if seed == FROZEN["seeds"]["development"]:
        return dict(stage="development", prerequisite_attempts={})
    needed = (121,) if seed == FROZEN["seeds"]["held_out"] else (121, 122)
    prerequisites = {}
    for previous in needed:
        good = _passing(committed, previous, code)
        if not good:
            raise ValueError(f"seed {seed} locked: a committed FEASIBILITY PASS on {previous} with this source digest is required")
        prerequisites[str(previous)] = good[-1].get("attempt")
    if seed not in GATED:
        return dict(stage="held_out", prerequisite_attempts=prerequisites)
    ready = [r for r in committed if r.get("kind") == "gate_ready" and r.get("source", {}).get("code_sha256") == code
             and r.get("predictions") == FROZEN["predictions"]
             and r.get("feasibility_attempts", prerequisites) == prerequisites]
    if not ready:
        raise ValueError("gated seeds locked: a committed gate_ready with this source digest and the frozen predictions is required")
    return dict(stage="gated", prerequisite_attempts=prerequisites,
                committed_gate_ready_sha256=hashlib.sha256(r1.json_bytes(ready[-1])).hexdigest())


def uniform_integrity():
    cfg = dict(CONTRACT, m=160, n=80, n_novel=2, f_q=.05)
    seed = FROZEN["seeds"]["development"]
    learners = [Baseline(cfg, seed, "independent"), E7(cfg, seed, "gate_off", "independent"), e3.E3(cfg, seed)]
    for e in learners:
        e.learn(4)
    digests = {r1.live_digest(e) for e in learners}
    require(len(digests) == 1, "baseline or gate_off does not reproduce frozen E3 learning")
    require(all(np.array_equal(a, b) for a, b in zip(learners[0].E, learners[2].E)), "uniform eligibility mismatch")
    return True


# ---------------------------------------------------------------- persisted learner state

def _pack(payload, name, arrays):
    r1.pack_ragged(payload, name, [np.asarray(a, np.int64) for a in arrays])


def _ragged(z, name):
    return e6.unpack(z, name)


def snapshot(e):
    """Everything needed to rebuild the learner bit for bit, plus the per-episode logs (once per checkpoint)."""
    gated = hasattr(e, "gate_log")
    pat = e._pat.bit_generator.state if isinstance(e._pat, np.random.Generator) else dict(k=e._pat.k)
    meta = dict(cfg=e.c, seed=e.seed, condition=e.condition, arm=e.arm, items=len(e.items), net_t=e.net.t,
                rngs={k: getattr(e, k).bit_generator.state for k in ("_learn_in", "_plat", "_coin")}, pat=pat,
                learn_log=e.learn_log, cont_offset=e.cont_offset, live_sha256=r1.live_digest(e),
                labels=getattr(e._pat, "labels", None))
    if gated:
        meta.update(gate_log=e.gate_log, input_hashes=e.input_hashes, coin_hashes=e.coin_hashes, episodes=e.episodes)
    p = dict(metadata_json=np.asarray(r1.json_bytes(meta).decode()), forward_keys=e.store.keys, feedback_keys=e.fb.keys,
             plateau_keys=e.fb_plateau.keys, mem_v=e.mem.v, mem_vbar=e.mem.vbar, mem_ring=e.mem.ring,
             mem_t_last=e.mem.t_last, inp_rate=e.inp.rate_hz, plateaus_per_cell=e.plateaus_per_cell)
    for key in ("items", "A", "E", "R"):
        _pack(p, key, getattr(e, key))
    if gated:
        p["H"] = e.H
        p["veto_counts"] = e.veto_counts if e.veto_counts is not None else EMPTY
        ticks = [np.concatenate([np.full(len(r[t]), t, np.int64) for t in sorted(r)]) if r else EMPTY for r in e.encoding_rasters]
        cells = [np.concatenate([r[t] for t in sorted(r)]) if r else EMPTY for r in e.encoding_rasters]
        _pack(p, "enc_tick", ticks)
        _pack(p, "enc_cell", cells)
        p["cont_counts"] = np.asarray(e.cont_counts, np.int16).reshape(len(e.cont_counts), e.c["n"])
        p["applied_V_size"] = np.asarray([g["applied_V_size"] for g in e.gate_log], np.int64)
    return p


def restore(descriptor):
    """Rebuild a learner from its verified state artifact; its live digest must equal the persisted one."""
    z = evidence.load_npz_artifact(descriptor)
    meta = json.loads(str(z["metadata_json"]))
    cfg, seed, cond, arm = meta["cfg"], meta["seed"], meta["condition"], meta["arm"]
    if arm == "baseline":
        e = Baseline(cfg, seed, cond)
    else:
        e = E7(cfg, seed, arm, cond, veto_counts=z["veto_counts"] if arm.endswith("_drop") else None)
        e.H = z["H"].astype(np.int64)
        e.gate_log, e.input_hashes, e.coin_hashes = meta["gate_log"], meta["input_hashes"], meta["coin_hashes"]
        e.episodes = meta["episodes"]
        e.cont_counts = list(z["cont_counts"])
        e.encoding_rasters = []
        for t, c in zip(_ragged(z, "enc_tick"), _ragged(z, "enc_cell")):
            e.encoding_rasters.append({int(k): c[t == k] for k in np.unique(t)})
    for key in ("items", "A", "E", "R"):
        setattr(e, key, _ragged(z, key))
    for k, state in meta["rngs"].items():
        getattr(e, k).bit_generator.state = state
    if isinstance(e._pat, np.random.Generator):
        e._pat.bit_generator.state = meta["pat"]
    else:
        for _ in range(meta["pat"]["k"]):
            e._pat.choice(cfg["m"], cfg["a"], replace=False)
    e.store.keys, e.fb.keys, e.fb_plateau.keys = z["forward_keys"], z["feedback_keys"], z["plateau_keys"]
    e.mem.v[:], e.mem.vbar[:], e.mem.ring[:], e.mem.t_last[:] = z["mem_v"], z["mem_vbar"], z["mem_ring"], z["mem_t_last"]
    e.inp.set_rates(z["inp_rate"])
    e.plateaus_per_cell[:] = z["plateaus_per_cell"]
    e.learn_log, e.cont_offset, e.net.t = meta["learn_log"], meta["cont_offset"], meta["net_t"]
    e._load()
    require(r1.live_digest(e) == meta["live_sha256"], f"restored {cond}/{arm} state differs from the persisted learner")
    return e


def matching(e):
    out = dict(items=e6.ragged_digest(e.items), A=e6.ragged_digest(e.A), E=e6.ragged_digest(e.E))
    if hasattr(e, "gate_log"):
        out.update(H=r1.sha_array(e.H), sensory=hashlib.sha256(r1.json_bytes(e.input_hashes)).hexdigest(),
                   coins=hashlib.sha256(r1.json_bytes(e.coin_hashes)).hexdigest())
    else:
        out["H"] = r1.sha_array(wrap_for_test(e).H)
    return out


# ---------------------------------------------------------------- stage 1/2 worker

class Sink:
    """One worker's journal and manifest."""

    def __init__(self, evidence_dir, seed, worker):
        self.worker = worker
        self.journal = evidence.Journal(Path(evidence_dir) / f"seed{seed}-{worker}.journal.jsonl", worker)
        self.manifest = evidence.Manifest()

    def put(self, name, descriptor):
        self.manifest.add(name, descriptor)
        self.journal.append(dict(kind="artifact_written", name=name, descriptor=descriptor))
        return descriptor

    def npz(self, path, **arrays):
        return self.put(Path(path).name, evidence.write_npz_artifact(path, **arrays))

    def json(self, path, obj):
        return self.put(Path(path).name, evidence.write_artifact(path, r1.json_bytes(obj)))


def learn_worker(spec):
    seed, cfg, cond, arm, meta = spec["seed"], spec["cfg"], spec["condition"], spec["arm"], spec["meta"]
    budget, cache = e6.Budget(spec["budget_start"]), Path(spec["cache"])
    sink = Sink(spec["evidence"], seed, f"{cond}-{arm}")
    sink.journal.append(dict(kind="worker_started", attempt=meta["attempt"], condition=cond, arm=arm, pid=os.getpid()))

    def append(kind, **fields):
        record.append(dict(meta, kind=kind, timestamp=record.now(), condition=cond, arm=arm, **fields), spec["results"])
    counts = load_veto_counts(spec["veto"]) if arm.endswith("_drop") else None
    e = Baseline(cfg, seed, cond) if arm == "baseline" else E7(cfg, seed, arm, cond, veto_counts=counts)
    out = dict(condition=cond, arm=arm, worker=sink.worker, journal=str(sink.journal.path), states={})
    grace = e6.hard_grace(budget) if not spec["in_process"] else e6.hard_grace(e6.Budget())
    with grace:
        for M in spec["loads"]:
            budget.check(new_load=True)
            append("load_started", stage="learn", M=M)
            with e6.bounded_steps(e, budget):
                e.learn(M)
            out["states"][str(M)] = sink.npz(cache / f"{cond}-{arm}-M{M}-state.npz", **snapshot(e))
    if arm != "baseline":
        fields = structural_fields(e, cond)
        fields["V_sequence"] = sink.npz(cache / f"{cond}-{arm}-V_sequence.npz",
                                        applied_V_size=np.asarray([g["applied_V_size"] for g in e.gate_log], np.int64))
        kills = structural_kills(fields, cond) if arm == "candidate" else []
        decided_by = {"F10": "mean_V/veto_precision/proto_predicted/nonproto_predicted_501_1000",
                      "independent": "veto_episode_fraction_501_1000",
                      "mixed": "veto_episode_fraction_independent_subset_501_1000"}.get(cond) if arm == "candidate" else None
        append("structural_check", gate=fields, kills=kills, episodes=e.episodes, kill_window=KILL_WINDOW, kill_fields=decided_by)
        out.update(structural=fields, kills=kills)
    sink.journal.append(dict(kind="worker_finished", states=sorted(out["states"])))
    out["manifest"] = sink.manifest.entries
    return out


# ---------------------------------------------------------------- stage 3 evaluation

def _test_raw(e, M, raster, n_ticks, cues, out, meta):
    p = dict(metadata_json=np.asarray(r1.json_bytes(dict(meta, cfg=e.c, M=M, n_ticks=n_ticks)).decode()),
             memory_out_json=np.asarray(r1.json_bytes(out).decode()), raster_ticks=np.asarray(sorted(raster), np.int64),
             cue_kind=np.asarray([q["kind"] for q in cues]), cue_index=np.asarray([q["index"] for q in cues], np.int64),
             cue_onset=np.asarray([q["onset"] for q in cues], np.int64),
             onset_offsets_json=np.asarray(r1.json_bytes(e.onset_offsets).decode()))
    _pack(p, "raster_cells", [raster[t] for t in sorted(raster)])
    for key in ("item", "cue", "missing", "other_missing"):
        _pack(p, "cue_" + key, [q[key] for q in cues])
    return p


def read_test_raw(z):
    """Raster, n_ticks, cues and cfg from a persisted test-phase artifact."""
    meta = json.loads(str(z["metadata_json"]))
    raster = dict(zip(z["raster_ticks"].tolist(), _ragged(z, "raster_cells")))
    parts = {k: _ragged(z, "cue_" + k) for k in ("item", "cue", "missing", "other_missing")}
    cues = [dict(kind=str(z["cue_kind"][i]), index=int(z["cue_index"][i]), onset=int(z["cue_onset"][i]),
                 **{k: parts[k][i] for k in parts}) for i in range(len(z["cue_kind"]))]
    return raster, meta["n_ticks"], cues, meta


def _diagnostics(e, cues, rows, raster):
    half = [r for r in rows if r["kind"] == "half"]
    own_lat, spur_lat = [], []
    for q in cues:
        if q["kind"] != "half":
            continue
        seen, A = set(), e.A[q["index"]]
        for t in range(q["onset"], q["onset"] + e.c["window"]):
            for cell in raster.get(t, EMPTY).tolist():
                if cell not in seen:
                    seen.add(cell)
                    (own_lat if cell in set(A.tolist()) else spur_lat).append(t - q["onset"])
    stats = lambda xs: dict(n=len(xs), median=float(np.median(xs)), p10=float(np.percentile(xs, 10)),
                            p90=float(np.percentile(xs, 90))) if xs else dict(n=0, median=None, p10=None, p90=None)
    offsets = [r["threshold_offset"]["assigned_mv"] for r in half if r.get("threshold_offset", {}).get("assigned_mv") is not None]
    mean = lambda key: float(np.mean([r[key] for r in half])) if half else None
    return dict(own50_mean=mean("own50"), spurious50_mean=mean("spurious50"), total50_mean=mean("total50"),
                latency_split=dict(own=stats(own_lat), spurious=stats(spur_lat)),
                assigned_threshold_offset_mv=float(np.mean(offsets)) if offsets else None)


def _content_subset(portable, cues, labels, subset):
    cols = portable["columns"]
    rows = [dict(zip(cols, r)) for r in portable["rows"]]
    joint = [r["missing"] >= e3.JOINT_MISSING and r["total"] - r["item"] < e3.JOINT_INTRUSIONS
             for r, q in zip(rows, cues) if q["kind"] == "half" and labels[q["index"]] == subset]
    return dict(joint=_frac(sum(joint), len(joint)), joint_count=int(sum(joint)), n_cues=len(joint))


def evaluate_load(main, M, state, cache, evidence_dir, meta, budget, sink):
    before = r1.live_digest(main)
    baseline = not hasattr(main, "gate_log")
    e = wrap_for_test(main) if baseline else copy.deepcopy(main)
    cued, _, _ = e1.test_sets(e.c, e.seed, M)
    planned = e3.build_cues(e, M, [0] * (2 * len(cued) + e.c["n_novel"]))
    e._probe_A = [e.A[q["index"]] if q["kind"] != "novel" else EMPTY for q in planned]
    e.onset_offsets = []
    with e6.bounded_steps(e, budget):
        out, raster, n_ticks, onsets, drift = e3.run_phase(e, M, phase=1)
    e._probe_A = None
    cues = e3.build_cues(e, M, onsets)
    require(len(e.onset_offsets) == len(cues), "cue onset threshold capture")
    digest = r1.raster_digest(raster, n_ticks, main.c["n"])
    tag = f"{main.condition}-{main.arm}-M{M}"
    raw = sink.npz(Path(cache) / f"{tag}-test.npz", **_test_raw(e, M, raster, n_ticks, cues, out, meta))
    rows, metrics = e6.index_evidence(e, M, cues, out, raster, e.onset_offsets)
    summaries, portable = {}, {}
    for name, store in (("inherited", main.fb), ("assigned_A", main.fb_plateau)):
        summaries[name], portable[name] = e6.content_evidence(e, raster, n_ticks, cues, store, budget)
        require(r1.raster_digest(raster, n_ticks, e.c["n"]) == digest, "content replay mutated the memory raster")
    require(r1.live_digest(main) == before, "the test phase changed the learned state")
    require(np.array_equal(main.store.keys, e.store.keys), "evaluation wrote the forward store")
    lg = main.learn_log
    mean_A = float(np.mean([a.size for a in main.A]))
    protocol = dict(eligibility=bool(np.mean(lg["elig_frac"]) >= FROZEN["protocol"]["eligibility_min"]),
                    mean_A_1000=bool(FROZEN["protocol"]["mean_A_1000"][0] <= mean_A <= FROZEN["protocol"]["mean_A_1000"][1]) if M == 1000 else None,
                    settled=bool(drift[0] <= FROZEN["protocol"]["drift_max_mv"]))
    union = getattr(main._pat, "union", None)
    degree = np.bincount(main.store.keys // main.c["n"], minlength=main.c["m"])
    learning = dict(forward_density=main.store.size / (main.c["m"] * main.c["n"]), forward_size=main.store.size,
                    max_prototype_out_degree=int(degree[union].max()) if union is not None else None,
                    potentiated=int(sum(lg["potentiated"])), depressed=int(sum(lg["depressed"])),
                    mean_A=mean_A, eligibility_mean=float(np.mean(lg["elig_frac"])), drift_mv=list(drift))
    value = dict(M=M, condition=main.condition, arm=main.arm, index=metrics,
                 content={k: {x: y for x, y in s.items()} for k, s in summaries.items()},
                 protocol=protocol, learning=learning, diagnostics=_diagnostics(e, cues, rows, raster),
                 matching=matching(main), forward_sha256=r1.sha_array(main.store.keys),
                 feedback_sha256=r1.sha_array(main.fb.keys), raster_sha256=digest, integrity=True, raw=raw, state=state)
    if main.condition == "mixed":
        labels = main._pat.labels
        value["index_by_subset"] = subset_scores(rows, labels)
        value["content_by_subset"] = {s: _content_subset(portable["inherited"], cues, labels, s) for s in ("F10", "independent")}
    value["portable"] = sink.json(Path(evidence_dir) / f"{meta['attempt']}-{tag}.json",
                                  dict(meta, **{k: x for k, x in value.items() if k != "portable"}, index_cues=rows, content_rows=portable))
    return value


def sanity_loads(candidate, cache, evidence_dir, meta, budget, sink, append):
    """Wrong-label permutation (stream 35) of the F10 candidate's test raster and a never-trained empty twin."""
    seed, M = meta["seed"], candidate["M"]
    st = evidence.load_npz_artifact(candidate["state"])
    items, A = _ragged(st, "items"), _ragged(st, "A")
    raster, n_ticks, cues, tmeta = read_test_raw(evidence.load_npz_artifact(candidate["raw"]))
    cfg = tmeta["cfg"]
    budget.check(new_load=True)
    pi = e1.stream(seed, STREAMS["wrong_label_permutation"], M).permutation(cfg["n"])
    wrong = {t: pi[s] for t, s in raster.items()}
    half = []
    for q in cues:
        if q["kind"] == "half":
            R, a = e6.responders(wrong, q["onset"]), A[q["index"]]
            own = int(np.isin(a, R).sum())
            half.append(dict(index_0based=q["index"], own50=own, total50=int(R.size), A_size=int(a.size),
                             recall50=own / a.size if a.size else 0.0))
    wrong_result = dict(kind="wrong_label", C1=float(np.mean([r["recall50"] >= .8 for r in half])),
                        count_preserved=all(len(wrong[t]) == len(s) for t, s in raster.items()),
                        raster_sha256=r1.raster_digest(wrong, n_ticks, cfg["n"]), permutation_sha256=r1.sha_array(pi),
                        original_raw=candidate["raw"])
    wrong_result["raw"] = sink.npz(Path(cache) / f"F10-wrong-label-M{M}.npz", permutation=pi)
    wrong_result["portable"] = sink.json(Path(evidence_dir) / f"{meta['attempt']}-F10-wrong-label-M{M}.json",
                                         dict(meta, **wrong_result, per_cue=half))
    append("sanity_load", sanity=wrong_result, wrong_label=dict(C1=wrong_result["C1"], count_preserved=wrong_result["count_preserved"]))
    budget.check(new_load=True)
    empty = e3.E3(cfg, seed)
    empty.items, empty.A = items, A
    require(empty.store.size == empty.fb.size == empty.fb_plateau.size == 0, "empty twin received training")
    with e6.bounded_steps(empty, budget):
        out, eraster, eticks, eonsets, drift = e3.run_phase(empty, M, phase=1)
    ecues = e3.build_cues(empty, M, eonsets)
    rows, metrics = e6.index_evidence(empty, M, ecues, out, eraster)
    for q, row in zip(ecues, rows):
        row["total100"] = int(e6.responders(eraster, q["onset"], cfg["t_cue"]).size)
    empty_result = dict(kind="empty_store", responders=sum(r["total100"] for r in rows), index=metrics, drift_mv=list(drift),
                        total_raster_spikes=int(sum(s.size for s in eraster.values())),
                        stores_empty=empty.store.size == empty.fb.size == empty.fb_plateau.size == 0)
    empty_result["portable"] = sink.json(Path(evidence_dir) / f"{meta['attempt']}-F10-empty-store-M{M}.json",
                                         dict(meta, **empty_result, per_cue=rows))
    append("sanity_load", sanity=empty_result, empty_store=dict(responders=empty_result["responders"], stores_empty=empty_result["stores_empty"]))
    return {"wrong_label": wrong_result, "empty_store": empty_result}


def cross_arm(values, loads):
    """Matching digests across arms and the gate_off == baseline forward-store check, per condition and load."""
    out, ok = {}, True
    for cond in FROZEN["arms"]:
        for M in loads:
            rows = {r["arm"]: r for r in values if r["condition"] == cond and r["M"] == M}
            gated = [r["matching"] for a, r in rows.items() if a != "baseline"]
            same = all(m == gated[0] for m in gated)
            base = rows.get("baseline")
            base_ok = all(base["matching"][k] == m[k] for m in gated for k in ("items", "A", "E", "H")) if base else None
            entry = dict(gated_matching_equal=same, baseline_matching_equal=base_ok)
            if cond == "F10":
                off = rows.get("gate_off")
                entry["gate_off_equals_baseline"] = bool(off and base and off["forward_sha256"] == base["forward_sha256"])
            out[f"{cond}/{M}"] = entry
            ok &= same and base_ok is not False and entry.get("gate_off_equals_baseline", True)
    return out, ok


def verification_record(worker, manifest_entries, journal_path):
    failures, verified = [], 0
    for name, desc in manifest_entries.items():
        try:
            evidence.verify_artifact(desc)
            verified += 1
        except evidence.EvidenceError as e:
            failures.append(f"{name}: {e}")
    try:
        evidence.verify_journal(journal_path)
        journal_ok = True
    except (evidence.EvidenceError, OSError) as e:
        journal_ok = False
        failures.append(f"journal: {e}")
    return dict(worker=worker, artifacts_verified=verified, failures=failures, journal_ok=journal_ok,
                passed=not failures and journal_ok)


# ---------------------------------------------------------------- the run

def resource_budget(process_start, workers, attempt):
    """E6's experiment-wide clock; refuses when the machine would exceed four simulation processes."""
    import fcntl
    directory = record.cache_dir("p2e7")
    with (directory / "resource-lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        active = 0
        for entry in Path("/proc").iterdir():
            if not entry.name.isdigit() or int(entry.name) == os.getpid():
                continue
            try:
                words = (entry / "cmdline").read_bytes().decode().split("\0")
            except (OSError, UnicodeError):
                continue
            active += any(w.startswith("plant2.experiments.p2_e") or w.startswith("analysis.p2") for w in words)
        if active + workers > FROZEN["resource"]["max_simulation_processes"]:
            raise ResourceStop(f"{active} other simulation processes plus {workers} workers exceed the limit")
        path = directory / f"resource-window-{attempt}.json"
        if not path.exists():
            evidence.write_artifact(path, r1.json_bytes(dict(start_unix=process_start, start=record.now(), first_pid=os.getpid())))
        start = json.loads(path.read_text())["start_unix"]
    budget = e6.Budget(start)
    budget.path = str(path.resolve())
    return budget


def run_seed(seed, results_path=RESULTS, evidence_dir=EVIDENCE, cfg=None, loads=LOADS, attempt=None, log=print,
             workers=4, enforce_kills=None):
    process_start = time.time()
    full = cfg is None
    if not full and (seed != FROZEN["seeds"]["development"] or Path(results_path) == RESULTS or Path(evidence_dir) == EVIDENCE):
        raise ValueError("small integrity runs require seed 121 and explicit non-production output paths")
    if full and tuple(loads) != LOADS:
        raise ValueError("full runs require the 500, 1000 checkpoints")
    if not 1 <= workers <= FROZEN["resource"]["max_simulation_processes"]:
        raise ValueError("workers must lie in 1..4")
    if full and enforce_kills is False:
        raise ValueError("full-size runs always enforce the structural kill rules")
    enforce_kills = True if full else bool(enforce_kills)
    openblas = os.environ.get("OPENBLAS_NUM_THREADS")
    if full and openblas != "1":
        raise ValueError(f"full-size runs require OPENBLAS_NUM_THREADS=1 (found {openblas!r})")
    cfg = dict(CONTRACT if cfg is None else cfg)
    loads = tuple(loads)
    source = source_manifest(require_committed=full)
    authorization = (seed_guard(seed, source, read_records(results_path, committed=True), read_records(results_path))
                     if full else dict(stage="integrity_test"))
    attempt = attempt or f"seed{seed}-{time.time_ns()}-{uuid.uuid4().hex[:8]}"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", attempt):
        raise ValueError("attempt must be a filename component")
    cache, evidence_dir = record.cache_dir("p2e7", attempt), Path(evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    meta = dict(experiment="P2-E7", schema=1, attempt=attempt, seed=seed, source=source, git_commit=source["commit"],
                runtime=dict(record.runtime(), openblas_num_threads=openblas), full_size=full, authorization=authorization,
                contract_commit=FROZEN["contract_commit"], predictions=FROZEN["predictions"])
    evidence.write_artifact(cache / "attempt.json", r1.json_bytes(meta))

    def append(kind, **fields):
        record.append(dict(meta, kind=kind, timestamp=record.now(), wall_s=round(time.time() - process_start, 3), **fields), results_path)

    append("seed_started", openblas_num_threads=openblas, process_start_unix=process_start, requested_loads=list(loads), workers=workers, enforce_kills=enforce_kills)
    coord = Sink(evidence_dir, seed, "coordinator")
    sinks = {"coordinator": (coord.manifest.entries, coord.journal.path)}
    values, sanity, structural, kills_fired = [], {}, {}, []
    invalid, interrupted, current, uniform, cross = False, None, None, False, {}
    try:
        budget = resource_budget(process_start, workers, attempt) if full else e6.Budget()
        append("resource_window", window_path=getattr(budget, "path", None), start_unix=budget.start, deadline_unix=budget.start + FROZEN["resource"]["wall_seconds"] if full else None,
               grace_deadline_unix=budget.start + FROZEN["resource"]["wall_seconds"] + FROZEN["resource"]["grace_seconds"] if full else None)
        uniform = uniform_integrity()
        append("uniform_integrity", baseline_equals_e3=uniform)
        spec = dict(seed=seed, cfg=cfg, loads=loads, meta=meta, results=str(results_path), evidence=str(evidence_dir),
                    cache=str(cache), budget_start=budget.start, veto=None)
        with e6.hard_grace(budget):
            current = ("F10", "candidate", "stage 1")
            first = learn_worker(dict(spec, condition="F10", arm="candidate", in_process=True))
            trajectories = {("F10", "candidate"): first}
            sinks[first["worker"]] = (first["manifest"], first["journal"])
            structural["F10"] = first["kills"]
            log(f"stage 1: F10 candidate structural {first['structural']['mean_V_501_1000']:.2f} mean |V|, kills {first['kills']}")
            if first["kills"]:
                kills_fired.append(("F10", first["kills"]))
                append("structural_kill", condition="F10", arm="candidate", rules=first["kills"], enforced=enforce_kills)
            if not (kills_fired and enforce_kills):
                current = ("stage 2",)
                todo = [dict(spec, condition=c, arm=a, veto=first["structural"]["V_sequence"], in_process=workers == 1)
                        for c, arms in FROZEN["arms"].items() for a in arms if (c, a) != ("F10", "candidate")]
                errors = []
                if workers == 1:
                    results = [learn_worker(s) for s in todo]
                else:
                    results = []
                    with ProcessPoolExecutor(max_workers=workers) as pool:
                        futures = [pool.submit(learn_worker, s) for s in todo]
                        for f in as_completed(futures):
                            try:
                                results.append(f.result())
                            except BaseException as exc:  # recorded below; the remaining workers finish
                                errors.append(exc)
                for res in results:
                    trajectories[(res["condition"], res["arm"])] = res
                    sinks[res["worker"]] = (res["manifest"], res["journal"])
                if errors:
                    raise errors[0]
                persisted = {r["condition"]: r["kills"] for r in read_records(results_path)
                             if r.get("attempt") == attempt and r.get("kind") == "structural_check" and r.get("arm") == "candidate"}
                for cond in ("independent", "mixed"):
                    require(cond in persisted, f"persisted structural_check for the {cond} candidate is missing")
                    kills = persisted[cond]
                    structural[cond] = kills
                    if kills:
                        kills_fired.append((cond, kills))
                        append("structural_kill", condition=cond, arm="candidate", rules=kills, enforced=enforce_kills)
                log(f"stage 2: {len(results)} trajectories learned; kills {kills_fired}")
            if not (kills_fired and enforce_kills):
                for cond, arms in FROZEN["arms"].items():
                    for arm in arms:
                        for M in loads:
                            current = (cond, arm, M)
                            budget.check(new_load=True)
                            append("load_started", stage="test", condition=cond, arm=arm, M=M)
                            state = trajectories[(cond, arm)]["states"][str(M)]
                            value = evaluate_load(restore(state), M, state, cache, evidence_dir,
                                                  dict(meta, condition=cond, arm=arm), budget, coord)
                            values.append(value)
                            append("load", load=value)
                            log(f"{cond} {arm} M={M}: C1={value['index']['C1']:.3f} C2={value['index']['C2']:.3f} "
                                f"joint={value['index']['joint_index']:.3f}")
                cross, ok = cross_arm(values, loads)
                invalid |= not ok
                candidate = next(r for r in values if (r["condition"], r["arm"], r["M"]) == ("F10", "candidate", loads[-1]))
                current = ("F10", "sanity", loads[-1])
                sanity = sanity_loads(candidate, cache, evidence_dir, meta, budget, coord, append)
    except (IntegrityError, evidence.EvidenceError) as exc:
        invalid, interrupted = True, repr(exc)
    except (ResourceStop, KeyboardInterrupt) as exc:
        interrupted = repr(exc)
    except Exception as exc:
        invalid, interrupted = True, repr(exc)
    for row in read_records(results_path):
        if row.get("attempt") == attempt and row.get("kind") == "sanity_load":
            sanity.setdefault(row["sanity"]["kind"], row["sanity"])
    if interrupted:
        append("interrupted", current=current, error=interrupted, integrity_defect=invalid,
               completed_loads=[(r["condition"], r["arm"], r["M"]) for r in values])
    coord.journal.append(dict(kind="coordinator_finished", loads=len(values)))
    verifications = []
    for worker, (entries, journal) in sinks.items():
        rec = verification_record(worker, entries, journal)
        verifications.append(rec)
        append("evidence_verification", **rec)
    invalid |= not all(v["passed"] for v in verifications)
    decision = screen(values, sanity, structural, uniform, invalid=invalid, checkpoints=loads)
    transfer = {str(M): {r["arm"]: {k: bool(r["index"][k] >= b) for k, b in FROZEN["bars"].items()}
                         for r in values if r["condition"] == "F40" and r["M"] == M} for M in loads}
    result = dict(meta, kind="seed_screen", timestamp=record.now(), screen=decision, cross_arm=cross, structural=structural,
                  kills_fired=kills_fired, transfer=transfer, interrupted=interrupted, completed_loads=len(values),
                  verifications_passed=all(v["passed"] for v in verifications), end_unix=time.time(),
                  wall_s=round(time.time() - process_start, 3))
    record.append(result, results_path)
    return result


def prepare_gate(results_path=RESULTS):
    source = source_manifest(require_committed=True)
    committed = read_records(results_path, committed=True)
    attempts = {}
    for seed in (121, 122):
        good = _passing(committed, seed, source["code_sha256"])
        if not good:
            raise ValueError(f"commit a passing screen on {seed} before preparing the gate")
        attempts[str(seed)] = good[-1]["attempt"]
    value = dict(experiment="P2-E7", kind="gate_ready", timestamp=record.now(), source=source,
                 feasibility_attempts=attempts, predictions=FROZEN["predictions"])
    record.append(value, results_path)
    return value


def verdict(records):
    screens = {}
    for r in records:
        if r.get("kind") == "seed_screen" and r.get("full_size") and r.get("seed") in GATED:
            screens.setdefault(r["seed"], []).append(r)
    verdicts = {s: rows[-1]["screen"]["verdict"] for s, rows in screens.items()}
    duplicates = [s for s, rows in screens.items() if len(rows) > 1]
    missing = [s for s in GATED if s not in screens]
    status = ("INVALID" if duplicates or "INVALID" in verdicts.values() else "PARTIAL" if missing or "PARTIAL" in verdicts.values()
              else "FAIL" if any(v != "FEASIBILITY PASS" for v in verdicts.values()) else "PASS")
    return dict(experiment="P2-E7", kind="gated_verdict", verdict=status, seeds=verdicts, missing_seeds=missing,
                duplicate_seeds=duplicates)


def small_cfg():
    return dict(CONTRACT, m=160, n=80, f_q=.05, n_novel=2)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--seed", type=int, required=True)
    run.add_argument("--workers", type=int, default=4)
    run.add_argument("--attempt")
    run.add_argument("--small", action="store_true", help="small integrity configuration (non-production paths required)")
    run.add_argument("--loads", type=int, nargs="+", default=list(LOADS))
    for p in (run, sub.add_parser("summary"), sub.add_parser("riders"), sub.add_parser("prepare-gate"), sub.add_parser("verdict")):
        p.add_argument("--results", type=Path, default=RESULTS)
        p.add_argument("--evidence", type=Path, default=EVIDENCE)
    sub.choices["riders"].add_argument("--seed", type=int, required=True)
    sub.choices["riders"].add_argument("--attempt")
    args = parser.parse_args(argv)
    say = lambda msg: print(f"[{record.now()}] {msg}", flush=True)
    if args.command == "run":
        result = run_seed(args.seed, args.results, args.evidence, cfg=small_cfg() if args.small else None,
                          loads=args.loads, attempt=args.attempt, log=say, workers=args.workers)
        print(json.dumps(dict(verdict=result["screen"]["verdict"], failed=result["screen"]["failed"],
                              missing=result["screen"]["missing"]), sort_keys=True), flush=True)
        return 0 if result["screen"]["verdict"] in ("FEASIBILITY PASS", "FEASIBILITY FAIL") else 2
    if args.command == "riders":
        from analysis import p2e7_riders
        for row in p2e7_riders.run(args.seed, args.results, args.evidence, attempt=args.attempt, log=say):
            print(json.dumps(dict(M=row["M"], void=row["void"]), sort_keys=True), flush=True)
    elif args.command == "prepare-gate":
        print(json.dumps(prepare_gate(args.results), sort_keys=True))
    elif args.command == "verdict":
        value = dict(verdict(read_records(args.results, committed=True)), timestamp=record.now())
        record.append(value, args.results)
        print(json.dumps(value, sort_keys=True))
    else:
        for row in read_records(args.results):
            if row.get("kind") == "seed_screen":
                print(json.dumps(dict(seed=row["seed"], attempt=row["attempt"], full_size=row["full_size"],
                                      verdict=row["screen"]["verdict"], failed=row["screen"]["failed"],
                                      missing=row["screen"]["missing"]), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
