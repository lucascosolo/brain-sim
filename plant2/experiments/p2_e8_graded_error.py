"""P2-E8 graded prediction-error weighting of the conserved flip budget; run, summary, riders.

Contract: docs/plant2/P2-E8-graded-error-eligibility.md, constants in docs/plant2/P2-E8-frozen.json.
Stage 1 learns the F10 graded arm and applies its kill rules, stage 2 every other trajectory
(worker processes), stage 3 the coordinator tests every arm and load from persisted states. The
binary and label_oracle arms are unchanged P2-E7 learners; every artifact goes through
plant2.evidence; results are append-only.

    python -m plant2.experiments.p2_e8_graded_error run --seed 123 [--workers 4]
    python -m plant2.experiments.p2_e8_graded_error summary
    python -m plant2.experiments.p2_e8_graded_error riders --seed 123
"""
import argparse
import hashlib
import json
import os
import re
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

from analysis import offline_screens_20261022 as osx
from analysis import p2r1_replay as r1
from plant2 import evidence, record
from plant2.btsp import BinarySynapses
from plant2.experiments import p2_e1_btsp as e1
from plant2.experiments import p2_e3_completion as e3
from plant2.experiments import p2_e5_structured as e5
from plant2.experiments import p2_e6 as e6
from plant2.experiments import p2_e7_error_gated as e7

FROZEN_PATH = "docs/plant2/P2-E8-frozen.json"
FROZEN = json.loads((record.REPO / FROZEN_PATH).read_text())
# The commit that added docs/plant2/P2-E8-frozen.json (git log -n 1 --format=%H -- docs/plant2/P2-E8-frozen.json).
FROZEN_JSON_COMMIT = "42be1fd4d0d0efba3d8321a534a563e4d5b0f7bf"
CONTRACT = dict(e5.CONTRACT)
LOADS = tuple(FROZEN["loads"])
ARMS = FROZEN["arms"]
GRADED_ARMS = ("graded", "gate_off", "graded_shuffled", "history_rank", "surplus_only")
REGISTRY = (FROZEN["seeds"]["development"], FROZEN["seeds"]["held_out"], *FROZEN["seeds"]["gated"])
GATED = tuple(FROZEN["seeds"]["gated"])
STREAMS = FROZEN["streams"]
MECH = FROZEN["mechanism"]
RESULTS = record.REPO / "bench/results/p2e8.jsonl"
EVIDENCE = record.REPO / "bench/results/p2e8"
ACCEPTANCE_REL = FROZEN["acceptance_path"]
ACCEPTANCE_PATH = record.REPO / ACCEPTANCE_REL
PINS = FROZEN["pins"]
PIN_GROUPS = (
    ("e3_era", e7.PIN_BASELINE, PINS["e3_era"]),
    ("contract_group", e7.PIN_CONTRACT, PINS["contract_group"]),
    ("p2_e7_driver_and_riders", ["plant2/experiments/p2_e7_error_gated.py", "analysis/p2e7_riders.py"],
     PINS["p2_e7_driver_and_riders"]),
    ("p2_e7_contract_append_only", [e7.FROZEN["contract_path"]], PINS["p2_e7_contract_append_only"]),
    ("p2_e7_frozen_json", [e7.FROZEN_PATH], PINS["p2_e7_frozen_json"]),
    ("offline_screens", ["analysis/offline_screens_20261022.py"], PINS["offline_screens"]),
    ("p2_e8_contract_append_only", [FROZEN["contract_path"]], FROZEN["contract_commit"]),
    ("p2_e8_frozen_json", [FROZEN_PATH], FROZEN_JSON_COMMIT),
    ("self", ["plant2/experiments/p2_e8_graded_error.py", "plant2/tests/test_p2_e8.py", "analysis/p2e8_riders.py"], "HEAD"),
)
APPEND_ONLY = ("p2_e7_contract_append_only", "p2_e8_contract_append_only")
EMPTY = np.empty(0, np.int64)
IntegrityError, ResourceStop, require = e6.IntegrityError, e6.ResourceStop, e6.require


# ---------------------------------------------------------------- mechanism

def lockstep_predict(raster, store, m):
    """Spike set G and peak drive d (mV above rest, before reset) of the frozen rec layer over ticks 0..74."""
    indptr, post = store.csr()
    return osx.lockstep_rec(raster, indptr, post, m, J=FROZEN["frozen"]["J_fb"], g=FROZEN["frozen"]["g"],
                            n_ticks=MECH["prediction_window_ticks"])


def graded_weights(E, G, d):
    """w over E: 0 on predicted lines, else 1 - clip(d / 20 mV, 0, 1)."""
    in_G = np.isin(np.asarray(E, np.int64), np.asarray(G, np.int64))
    return np.where(in_G, 0.0, 1.0 - np.clip(np.asarray(d, float) / MECH["normaliser_mv"], 0.0, 1.0))


def water_filled(w, n_eligible):
    """(p, lambda, p_capped, n_p_eq_1) for weights w under the conserved budget 0.5 * |E|."""
    w = np.asarray(w, float)
    budget = MECH["budget_per_eligible"] * n_eligible
    p = osx.water_fill(w, budget)[0]
    pos = np.flatnonzero(w > 0)
    if pos.size == 0:
        return p, 0.0, False, 0
    if pos.size <= budget:
        return p, None, True, 0
    # lambda of water_fill's sorted search: the same order, tail sums and stopping index, checked against its p.
    order = pos[np.argsort(-w[pos], kind="stable")]
    sw = w[order]
    tail = np.concatenate((np.cumsum(sw[::-1])[::-1], [0.0]))
    lams = (budget - np.arange(order.size)) / tail[:-1]
    stop = np.flatnonzero(lams * sw <= 1.0)
    lam = float(lams[stop[0]]) if stop.size else None
    require(lam is None or np.array_equal(p[order[stop[0]:]], lam * sw[stop[0]:]), "water-filling lambda disagrees with water_fill")
    return p, lam, False, int((p == 1.0).sum())


def graded_p(E, G, d):
    return water_filled(graded_weights(E, G, d), len(E))


def _free_positions(E, G):
    E = np.asarray(E, np.int64)
    idx = np.flatnonzero(~np.isin(E, np.asarray(G, np.int64)))
    return idx[np.argsort(E[idx], kind="stable")]


def shuffled_w(w, E, G, seed, k):
    """graded_shuffled: w over E' (ascending line order) permuted by stream (seed, 37, k)."""
    w = np.asarray(w, float)
    idx = _free_positions(E, G)
    out = np.zeros(w.size)
    out[idx] = w[idx[e1.stream(seed, STREAMS["graded_shuffled"], k).permutation(idx.size)]]
    return out


def history_rank_w(w, E, G, H):
    """history_rank: E's own w multiset over E', the most-used line (H) taking the smallest w, ties to the lower id."""
    w, E, H = np.asarray(w, float), np.asarray(E, np.int64), np.asarray(H)
    idx = _free_positions(E, G)
    order = idx[np.lexsort((E[idx], -H[E[idx]]))]
    out = np.zeros(w.size)
    out[order] = np.sort(w[idx], kind="stable")
    return out


# ---------------------------------------------------------------- learners

class E8(e7.E7):
    """P2-E7's learner with the per-line flip probability from the graded residual error."""

    def __init__(self, cfg, seed, arm="graded", condition="F10"):
        if arm not in GRADED_ARMS:
            raise ValueError(f"arm {arm!r} is not a graded-class arm")
        e3.E3.__init__(self, cfg, seed)
        e7._set_gen(self, condition)
        self.arm, self.condition, self.veto_counts = arm, condition, None
        self.H = np.zeros(cfg["m"], np.int64)
        self.episodes = 0
        self.gate_log, self.encoding_rasters, self.cont_counts = [], [], []
        self.input_hashes, self.coin_hashes, self.p_history = [], [], []
        self.dmax_log, self.p_log = [], []
        self._probe_A, self.onset_offsets = None, []

    def _rule(self, E, G, d, w, k):
        if self.arm == "gate_off":
            return np.full(E.size, .5), (.5 if E.size else 0.0), False, 0
        if self.arm == "surplus_only":
            p = osx.counterfactual_p(E, G, d, "surplus_only")
            return p, None, False, int((p == 1.0).sum())
        if self.arm == "graded_shuffled":
            w = shuffled_w(w, E, G, self.seed, k)
        elif self.arm == "history_rank":
            w = history_rank_w(w, E, G, self.H)
        return water_filled(w, E.size)

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
        E = np.flatnonzero(counts >= c["elig_min"])
        k = len(self.items)
        spikes, dmax = lockstep_predict(raster, self.fb, c["m"])
        G = e7.predict_set(raster, self.fb, c["m"])
        if not np.array_equal(spikes, G):
            self.lockstep_failure = dict(episode=k, lockstep_size=int(len(spikes)), predict_set_size=int(G.size),
                                         symmetric_difference=int(np.setxor1d(spikes, G).size))
        require(np.array_equal(spikes, G), f"lockstep spike set differs from predict_set at episode {k}")
        d = dmax[E]
        w = graded_weights(E, G, d)
        p, lam, capped, n1 = self._rule(E, G, d, w, k)
        in_G = np.isin(E, G)
        V = E[in_G]
        n_keep = int((~in_G).sum())
        if E.size and plateau.size:
            coins = self._coin.random(E.size * plateau.size).reshape(E.size, plateau.size)
        else:
            coins = np.empty((E.size, plateau.size))
        mask = coins < p[:, None]
        pot, dep = self.store.toggle((E[:, None] * c["n"] + plateau[None, :])[mask])
        self.H[E] += 1  # only after the write
        self.episodes += 1
        self._load()
        self.A.append(plateau)
        self.plateaus_per_cell[plateau] += 1
        lg = self.learn_log
        lg["elig_frac"].append(float((counts[item] >= c["elig_min"]).mean()))
        lg["bg_eligible"].append(int(E.size - (counts[item] >= c["elig_min"]).sum()))
        lg["potentiated"].append(pot)
        lg["depressed"].append(dep)
        lg["mem_spikes"].append(mem_spk)
        rng = e1.stream(self.seed, e3.CONT, len(self.items) - 1)
        cont = np.zeros(c["n"], np.int64)
        for _ in range(c["t_cont"]):
            cont[self.net.step(rng)["mem"]] += 1
        R = np.flatnonzero(cont)
        m = c["m"]
        self.fb.add((R[:, None] * m + E[None, :]).ravel())
        self.fb_plateau.add((plateau[:, None] * m + E[None, :]).ravel())
        self.R.append(R)
        self.E.append(E)
        self.cont_offset.append(float(self.mem.vbar.mean() - float(self.mem.v_rest)))
        self.encoding_rasters.append(raster)
        self.cont_counts.append(cont.astype(np.int16))
        self.input_hashes.append(sensory.hexdigest())
        self.coin_hashes.append(hashlib.sha256(np.asarray(coins, dtype="<f8").tobytes()).hexdigest())
        self.dmax_log.append(d)
        self.p_log.append(np.asarray(p, float))
        P = self._proto(item)
        in_P = None if P is None else np.isin(E, P)
        EP = None if P is None else E[in_P]
        non = None if P is None else E[~in_P]
        pb = osx.counterfactual_p(E, G, d, "binary")
        mean_w = lambda sel: float(w[sel].mean()) if sel.any() else None
        labels = getattr(self._pat, "labels", None)
        self.gate_log.append(dict(
            E_size=int(E.size), G_size=int(G.size), V_size=int(V.size),
            applied_V_size=0 if self.arm == "gate_off" else int(V.size),
            p=float(p[~in_G].mean()) if n_keep else 0.0, p_capped=capped, Eprime_empty=n_keep == 0,
            veto_proto_fraction=None if P is None or not V.size else e7._frac(np.isin(V, P).sum(), V.size),
            proto_predicted=None if P is None else e7._frac(np.isin(EP, G).sum(), EP.size),
            nonproto_predicted=None if P is None else e7._frac(np.isin(non, G).sum(), non.size),
            subset=labels[-1] if labels else None, potentiated=pot, depressed=dep,
            forward_size=self.store.size, feedback_size=self.fb.size,
            expected_proto_flips=None if P is None else float(p[in_P].sum()),
            expected_nonproto_flips=None if P is None else float(p[~in_P].sum()),
            expected_proto_flips_binary_cf=None if P is None else float(pb[in_P].sum()),
            w_mean_proto_unpredicted=None if P is None else mean_w(in_P & ~in_G),
            w_mean_nonproto_unpredicted=None if P is None else mean_w(~in_P & ~in_G),
            tv_mean_abs_dev_from_half=float(np.abs(p - .5).mean()) if E.size else 0.0,
            n_p_eq_1=n1, **{"lambda": lam}))


def make_learner(cfg, seed, arm, condition):
    if arm == "binary":
        return e7.E7(cfg, seed, "candidate", condition)
    if arm == "label_oracle":
        return e7.E7(cfg, seed, "label_oracle", condition)
    if arm == "baseline":
        return e7.Baseline(cfg, seed, condition)
    return E8(cfg, seed, arm, condition)


# ---------------------------------------------------------------- structural check

def _windows(n):
    if n >= 1000:
        return (0, 300), (500, 1000)
    return (0, max(1, 3 * n // 10)), (n // 2, n)


def graded_structural_fields(e, condition):
    fields = e7.structural_fields(e, condition)
    log = list(e.gate_log)
    (a0, a1), (b0, b1) = _windows(len(log))

    def mean(rows, key):
        xs = [g[key] for g in rows if g.get(key) is not None]
        return float(np.mean(xs)) if xs else None
    for key, name in (("expected_proto_flips", "expected_proto_flips"),
                      ("expected_proto_flips_binary_cf", "expected_proto_flips_binary_cf"),
                      ("tv_mean_abs_dev_from_half", "tv_mean")):
        fields[name + "_1_300"] = mean(log[a0:a1], key)
        fields[name + "_501_1000"] = mean(log[b0:b1], key)
    fields["lambda_mean"] = mean(log, "lambda")
    fields["n_p_eq_1_episodes"] = sum(g["n_p_eq_1"] > 0 for g in log)
    return fields


def graded_structural_kills(fields, condition, reference_tv_1_300=None):
    s = FROZEN["structural_kill"]
    fired = e7.structural_kills(fields, condition)
    if condition == "F10":
        num, den = fields.get("expected_proto_flips_501_1000"), fields.get("expected_proto_flips_binary_cf_501_1000")
        if not den or num is None or num / den > s["max_within_arm_graded_over_binary_cf"]:
            fired.append("no graded reduction")
    elif condition == "independent":
        if reference_tv_1_300 is None:
            raise ValueError("the independent perturbation rule needs the F10 graded tv_mean_1_300 of this run")
        tv = fields.get("tv_mean_501_1000")
        require(tv is not None, "the independent graded arm has no tv_mean_501_1000")
        if tv > reference_tv_1_300:
            fired.append("independent perturbation")
    return fired


# ---------------------------------------------------------------- screen

def _band(invalid, structural_fired, delta, kills, failed, missing, critical_missing):
    bands = FROZEN["delta_bands"]
    if invalid:
        return "invalid_or_partial"
    if structural_fired:
        return "structural_kill"
    if critical_missing or delta is None:
        return "invalid_or_partial"
    if delta + 1e-12 < bands["refuted_below"]:
        return "refuted"
    if delta + 1e-12 < bands["kill_below"]:
        return "kill_delta_below_0_05"
    if kills:
        return "kill_other_rule"
    if failed:
        return "informative_fail"
    return "invalid_or_partial" if missing else "pass"


def screen(loads, sanity, structural, uniform, invalid=False, checkpoints=LOADS):
    """The frozen development screen with the graded comparisons and outcome bands."""
    bars, mg = FROZEN["bars"], FROZEN["margins"]
    by = {(r["condition"], r["arm"], r["M"]): r for r in loads}
    missing = [f"{c}/{a}/{M}" for c, arms in ARMS.items() for a in arms for M in checkpoints if (c, a, M) not in by]
    v, bar_keys = {}, set()
    invalid = bool(invalid) or not uniform or any(not r.get("integrity", False) for r in loads)
    ge = lambda x, y: bool(x + 1e-12 >= y)
    for M in checkpoints:
        B, O = by.get(("F10", "baseline", M)), by.get(("F10", "gate_off", M))
        if B and O and B["forward_sha256"] != O["forward_sha256"]:
            invalid = True
        for cond in ("F10", "independent"):
            C, B = by.get((cond, "graded", M)), by.get((cond, "baseline", M))
            if C:
                for k, bar in bars.items():
                    v[f"index/{cond}/{M}/{k}"] = ge(C["index"][k], bar)
                    if k != "C3":
                        bar_keys.add(f"index/{cond}/{M}/{k}")
            if C and B:
                v[f"index/{cond}/{M}/C1_nonregression"] = ge(C["index"]["C1"], B["index"]["C1"] - mg["C1_nonregression"])
                if cond == "independent":
                    v[f"index/{cond}/{M}/C2_nonregression"] = ge(C["index"]["C2"], B["index"]["C2"] - mg["independent_C2_nonregression"])
                    for k in ("joint", "D4"):
                        v[f"content/{cond}/{M}/{k}_nonregression"] = ge(
                            C["content"]["inherited"][k], B["content"]["inherited"][k] - mg[f"independent_content_{k}_nonregression"])
        C, B = by.get(("mixed", "graded", M)), by.get(("mixed", "baseline", M))
        if C and B:
            for k in ("C1", "C2"):
                v[f"index/mixed/{M}/independent_subset_{k}_cues"] = (
                    B["index_by_subset"]["independent"][k + "_count"] - C["index_by_subset"]["independent"][k + "_count"]
                    < mg["mixed_independent_subset_index_nonregression_cues"])
            v[f"content/mixed/{M}/independent_subset_joint_cues"] = (
                B["content_by_subset"]["independent"]["joint_count"] - C["content_by_subset"]["independent"]["joint_count"]
                < mg["mixed_independent_subset_content_nonregression_cues"])
        for cond in ("F10", "independent", "mixed"):
            for arm in ARMS[cond]:
                r = by.get((cond, arm, M))
                for k, ok in (r["protocol"].items() if r else ()):
                    if ok is not None:
                        v[f"protocol/{cond}/{arm}/{M}/{k}"] = bool(ok)
    last = checkpoints[-1]
    C, delta = by.get(("F10", "graded", last)), None
    if C:
        for name, arm in (("baseline", "baseline"), ("binary", "binary"), ("shuffled", "graded_shuffled"),
                          ("history_rank", "history_rank")):
            ctl = by.get(("F10", arm, last))
            if ctl:
                v[f"index/F10/{last}/C2_vs_{name}"] = ge(C["index"]["C2"], ctl["index"]["C2"] + mg[f"F10_C2_vs_{name}"])
        for name in ("baseline", "binary"):
            ctl = by.get(("F10", name, last))
            if ctl:
                v[f"index/F10/{last}/joint_vs_{name}"] = ge(C["index"]["joint_index"], ctl["index"]["joint_index"] + mg[f"F10_joint_vs_{name}"])
        B, binary = by.get(("F10", "baseline", last)), by.get(("F10", "binary", last))
        if B:
            v[f"index/F10/{last}/C4_recall_nonregression"] = ge(C["index"]["C4_recall"], B["index"]["C4_recall"] - mg["F10_M1000_C4_recall_nonregression"])
        if binary:
            delta = float(C["index"]["C2"] - binary["index"]["C2"])
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
    kills = [k for k in failed if k not in bar_keys]
    fired = any(structural.get(c) for c in ("F10", "independent", "mixed"))
    needed = [f"F10/{a}/{last}" for a in ("graded", "binary", "graded_shuffled", "history_rank", "baseline")]
    critical = [x for x in missing if x in needed or x.startswith(("sanity/", "structural/"))]
    verdict = ("INVALID" if invalid else "FEASIBILITY FAIL" if fired else "PARTIAL" if critical
               else "FEASIBILITY FAIL" if failed else "PARTIAL" if missing else "FEASIBILITY PASS")
    band = _band(invalid, fired, delta, kills, failed, missing, critical)
    return dict(verdict=verdict, failed=failed, kills=kills, missing=missing, vectors=v, complete=not missing,
                integrity=not invalid, delta_C2_vs_binary=delta, band=band, informative=band == "informative_fail")


# ---------------------------------------------------------------- provenance and the seed guard

def source_manifest(require_committed=False):
    """Every pinned file's SHA-256 and the blob comparison it passed. All git reads happen here."""
    files = {}
    groups = list(PIN_GROUPS)
    if ACCEPTANCE_PATH.exists():
        groups.append(("acceptance", [ACCEPTANCE_REL], "HEAD"))
    for pin, paths, rev in groups:
        for path in paths:
            raw = (record.REPO / path).read_bytes()
            blob = e7._git("cat-file", "blob", f"{rev}:{path}")
            equal = raw == blob
            if pin in APPEND_ONLY:
                equal = blob is not None and raw.startswith(blob) and raw == e7._git("cat-file", "blob", f"HEAD:{path}")
            passed = True if pin == "self" and not require_committed else equal
            files[path] = dict(pin=pin, rev=rev, sha256=hashlib.sha256(raw).hexdigest(), passed=bool(passed),
                               equals_pinned_blob=bool(raw == blob),
                               pinned_blob_sha256=hashlib.sha256(blob).hexdigest() if blob is not None else None)
            if pin in APPEND_ONLY:
                files[path]["append_only_ok"] = bool(equal)
                files[path]["appended_bytes"] = (len(raw) - len(blob)) if blob is not None else None
    if require_committed:
        bad = [p for p, f in files.items() if not f["passed"]]
        if bad:
            raise ValueError("uncommitted or drifted source: " + ", ".join(bad))
    commit = e7._git("rev-parse", "HEAD")
    head = commit.decode().strip() if commit else None
    code = {p: f["sha256"] for p, f in files.items() if f["pin"] != "acceptance"}
    return dict(commit=head, files=files, require_committed=require_committed,
                acceptance_sha256=files[ACCEPTANCE_REL]["sha256"] if ACCEPTANCE_REL in files else None,
                self_files={p: dict(sha256=f["sha256"], committed_at_head=f["equals_pinned_blob"], head=head)
                            for p, f in files.items() if f["pin"] == "self"},
                code_sha256=hashlib.sha256(r1.json_bytes(code)).hexdigest())


def read_records(path=RESULTS, committed=False):
    return e7.read_records(path, committed=committed)


def acceptance_valid(acceptance):
    return (isinstance(acceptance, dict) and acceptance.get("question") == "f" and acceptance.get("accepted") is True
            and acceptance.get("by") == "owner" and bool(acceptance.get("date")) and bool(acceptance.get("source")))


def seed_guard(seed, manifest, committed, existing, acceptance=None, full_size=True):
    if seed not in REGISTRY:
        raise ValueError(f"seed {seed} is outside the P2-E8 registry {REGISTRY}")
    for r in list(committed) + list(existing):
        if r.get("kind") == "seed_screen" and r.get("seed") in REGISTRY and r.get("screen", {}).get("verdict") == "INVALID":
            raise ValueError(f"an INVALID screen on seed {r['seed']} locks every remaining seed")
    if full_size and any(r.get("kind") == "seed_started" and r.get("seed") == seed and r.get("full_size") for r in existing):
        raise ValueError(f"seed {seed} already has a full-size attempt; a rerun needs an explicit owner ruling")
    if full_size and not acceptance_valid(acceptance):
        raise ValueError(f"full-size seeds need the owner's committed yes to question (f) in {ACCEPTANCE_REL}")
    code = manifest["code_sha256"]
    if seed == FROZEN["seeds"]["development"]:
        return dict(stage="development", prerequisite_attempts={})
    dev, held = FROZEN["seeds"]["development"], FROZEN["seeds"]["held_out"]
    prerequisites = {}
    for previous in ((dev,) if seed == held else (dev, held)):
        good = e7._passing(committed, previous, code)
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
    """gate_off and baseline reproduce E3 over four episodes; a graded learner on its empty store reproduces E3's first."""
    cfg = dict(CONTRACT, m=160, n=80, n_novel=2, f_q=.05)
    seed = FROZEN["seeds"]["development"]
    learners = [e7.Baseline(cfg, seed, "independent"), E8(cfg, seed, "gate_off", "independent"), e3.E3(cfg, seed)]
    for e in learners:
        e.learn(4)
    require(len({r1.live_digest(e) for e in learners}) == 1, "baseline or gate_off does not reproduce frozen E3 learning")
    require(all(np.array_equal(a, b) for a, b in zip(learners[0].E, learners[2].E)), "uniform eligibility mismatch")
    first = [E8(cfg, seed, "graded", "independent"), e3.E3(cfg, seed)]
    for e in first:
        e.learn(1)
    require(r1.live_digest(first[0]) == r1.live_digest(first[1]), "the empty-store graded learner does not reproduce E3")
    return True


# ---------------------------------------------------------------- persisted learner state

def snapshot(e):
    p = e7.snapshot(e)
    if isinstance(e, E8):
        p["dmax_log"] = np.concatenate(e.dmax_log).astype(np.float64) if e.dmax_log else np.empty(0)
        p["p_log"] = np.concatenate(e.p_log).astype(np.float64) if e.p_log else np.empty(0)
    return p


def _split(flat, E):
    ends = np.cumsum([len(x) for x in E])
    return [flat[a:b].copy() for a, b in zip(np.concatenate(([0], ends[:-1])), ends)]


def restore(descriptor):
    """Rebuild a learner from its verified state artifact; its live digest must equal the persisted one."""
    z = evidence.load_npz_artifact(descriptor)
    meta = json.loads(str(z["metadata_json"]))
    cfg, seed, cond, arm = meta["cfg"], meta["seed"], meta["condition"], meta["arm"]
    if arm == "baseline":
        e = e7.Baseline(cfg, seed, cond)
    else:
        e = E8(cfg, seed, arm, cond) if arm in GRADED_ARMS else e7.E7(cfg, seed, arm, cond)
        e.H = z["H"].astype(np.int64)
        e.gate_log, e.input_hashes, e.coin_hashes = meta["gate_log"], meta["input_hashes"], meta["coin_hashes"]
        e.episodes = meta["episodes"]
        e.cont_counts = list(z["cont_counts"])
        e.encoding_rasters = []
        for t, c in zip(e7._ragged(z, "enc_tick"), e7._ragged(z, "enc_cell")):
            e.encoding_rasters.append({int(k): c[t == k] for k in np.unique(t)})
    for key in ("items", "A", "E", "R"):
        setattr(e, key, e7._ragged(z, key))
    if isinstance(e, E8):
        e.dmax_log, e.p_log = _split(z["dmax_log"], e.E), _split(z["p_log"], e.E)
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


# ---------------------------------------------------------------- stage 1/2 worker

def binary_counterfactual(e):
    """Reported only: the binary trajectory's expected prototype flips beside the graded counterfactual (screen F's procedure)."""
    ticks = [np.concatenate([np.full(len(r[t]), t, np.int64) for t in sorted(r)]) if r else EMPTY for r in e.encoding_rasters]
    cells = [np.concatenate([r[t] for t in sorted(r)]) if r else EMPTY for r in e.encoding_rasters]
    F = FROZEN["conditions"][e.condition]["F"]
    try:
        out, _ = osx.screen_f(e.items, e.E, e.R, e.A, ticks, cells, e.fb.keys, e.gate_log, e._pat.protos,
                              lambda k: (k + 1) % F, e.c["m"], e.c["n"])
    except ValueError as exc:
        return dict(error=str(exc))
    finite = lambda x: float(x) if x is not None and np.isfinite(x) else None
    return {w: dict(binary=finite(out[w]["rules"]["binary"]["proto"]), graded=finite(out[w]["rules"]["graded"]["proto"]),
                    graded_over_binary=finite(out[w]["graded_over_binary"]), episodes=out[w]["episodes"])
            for w in ("w1_300", "w501_1000")}


def learn_worker(spec):
    seed, cfg, cond, arm, meta = spec["seed"], spec["cfg"], spec["condition"], spec["arm"], spec["meta"]
    budget, cache = e6.Budget(spec["budget_start"]), Path(spec["cache"])
    sink = e7.Sink(spec["evidence"], seed, f"{cond}-{arm}")
    sink.journal.append(dict(kind="worker_started", attempt=meta["attempt"], condition=cond, arm=arm, pid=os.getpid()))

    def append(kind, **fields):
        record.append(dict(meta, kind=kind, timestamp=record.now(), condition=cond, arm=arm, **fields), spec["results"])
    e = make_learner(cfg, seed, arm, cond)
    out = dict(condition=cond, arm=arm, worker=sink.worker, journal=str(sink.journal.path), states={})
    grace = e6.hard_grace(budget) if not spec["in_process"] else e6.hard_grace(e6.Budget())
    with grace:
        for M in spec["loads"]:
            budget.check(new_load=True)
            append("load_started", stage="learn", M=M)
            try:
                with e6.bounded_steps(e, budget):
                    e.learn(M)
            except IntegrityError:
                if getattr(e, "lockstep_failure", None):
                    append("lockstep_failure", **e.lockstep_failure)
                raise
            out["states"][str(M)] = sink.npz(cache / f"{cond}-{arm}-M{M}-state.npz", **snapshot(e))
    if arm != "baseline":
        graded = isinstance(e, E8)
        fields = graded_structural_fields(e, cond) if graded else e7.structural_fields(e, cond)
        kills = graded_structural_kills(fields, cond) if (cond, arm) == ("F10", "graded") else []
        decided_by = {"F10": "E7 four rules plus expected_proto_flips_501_1000 / expected_proto_flips_binary_cf_501_1000",
                      "independent": "veto_episode_fraction_501_1000 and tv_mean_501_1000 against F10 graded tv_mean_1_300",
                      "mixed": "veto_episode_fraction_independent_subset_501_1000"}.get(cond) if arm == "graded" and cond != "F40" else None
        extra = dict(binary_counterfactual=binary_counterfactual(e)) if arm == "binary" else {}
        append("structural_check", gate=fields, kills=kills, episodes=e.episodes, kill_window=e7.KILL_WINDOW,
               kill_fields=decided_by, learner_arm=e.arm, lockstep_asserted_episodes=e.episodes if graded else 0, **extra)
        out.update(structural=fields, kills=kills)
    sink.journal.append(dict(kind="worker_finished", states=sorted(out["states"])))
    out["manifest"] = sink.manifest.entries
    return out


# ---------------------------------------------------------------- stage 3

def sanity_loads(graded, cache, evidence_dir, meta, budget, sink, append):
    """Wrong-label permutation (stream 38) of the F10 graded arm's test raster and a never-trained empty twin."""
    seed, M = meta["seed"], graded["M"]
    st = evidence.load_npz_artifact(graded["state"])
    items, A = e7._ragged(st, "items"), e7._ragged(st, "A")
    raster, n_ticks, cues, tmeta = e7.read_test_raw(evidence.load_npz_artifact(graded["raw"]))
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
                        stream=STREAMS["wrong_label_permutation"], original_raw=graded["raw"])
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
    """Matching digests across P2-E8's arms and the gate_off == baseline forward-store check, per condition and load."""
    out, ok = {}, True
    for cond in ARMS:
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


def resource_check(workers):
    """Refuses (no record, no window file) when the machine would exceed four simulation processes."""
    import fcntl
    with (record.cache_dir("p2e8") / "resource-lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        _count_processes(workers)


def _count_processes(workers):
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


def resource_budget(process_start, workers, attempt):
    """E6's experiment-wide clock; refuses when the machine would exceed four simulation processes."""
    import fcntl
    directory = record.cache_dir("p2e8")
    with (directory / "resource-lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        _count_processes(workers)
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
        raise ValueError("small integrity runs require seed 123 and explicit non-production output paths")
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
    source = source_manifest()
    acceptance = None
    if ACCEPTANCE_REL in source["files"] and source["files"][ACCEPTANCE_REL]["passed"]:
        acceptance = json.loads(ACCEPTANCE_PATH.read_text())
    if full:
        if ACCEPTANCE_REL not in source["files"]:
            raise ValueError(f"full-size seeds stay closed: {ACCEPTANCE_REL} is absent (no recorded owner yes to question (f))")
        if acceptance is None:
            raise ValueError(f"full-size seeds stay closed: {ACCEPTANCE_REL} is not committed (HEAD blob differs from the working file)")
        source = source_manifest(require_committed=True)
    authorization = (seed_guard(seed, source, read_records(results_path, committed=True), read_records(results_path),
                                acceptance=acceptance, full_size=True)
                     if full else dict(stage="integrity_test"))
    attempt = attempt or f"seed{seed}-{time.time_ns()}-{uuid.uuid4().hex[:8]}"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", attempt):
        raise ValueError("attempt must be a filename component")
    if full:
        resource_check(workers)
    cache, evidence_dir = record.cache_dir("p2e8", attempt), Path(evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    meta = dict(experiment="P2-E8", schema=1, attempt=attempt, seed=seed, source=source, git_commit=source["commit"],
                runtime=dict(record.runtime(), openblas_num_threads=openblas), full_size=full, authorization=authorization,
                contract_commit=FROZEN["contract_commit"], predictions=FROZEN["predictions"])
    evidence.write_artifact(cache / "attempt.json", r1.json_bytes(meta))

    def append(kind, **fields):
        record.append(dict(meta, kind=kind, timestamp=record.now(), wall_s=round(time.time() - process_start, 3), **fields), results_path)

    append("seed_started", openblas_num_threads=openblas, process_start_unix=process_start, requested_loads=list(loads),
           workers=workers, enforce_kills=enforce_kills, acceptance_sha256=source["acceptance_sha256"], acceptance=acceptance)
    coord = e7.Sink(evidence_dir, seed, "coordinator")
    sinks = {"coordinator": (coord.manifest.entries, coord.journal.path)}
    values, sanity, structural, kills_fired = [], {}, {}, []
    invalid, interrupted, current, uniform, cross = False, None, None, False, {}
    try:
        budget = resource_budget(process_start, workers, attempt) if full else e6.Budget()
        append("resource_window", window_path=getattr(budget, "path", None), start_unix=budget.start,
               deadline_unix=budget.start + FROZEN["resource"]["wall_seconds"] if full else None,
               grace_deadline_unix=budget.start + FROZEN["resource"]["wall_seconds"] + FROZEN["resource"]["grace_seconds"] if full else None)
        uniform = uniform_integrity()
        append("uniform_integrity", baseline_equals_e3=uniform, gate_off_equals_e3=uniform, empty_store_graded_equals_e3=uniform)
        spec = dict(seed=seed, cfg=cfg, loads=loads, meta=meta, results=str(results_path), evidence=str(evidence_dir),
                    cache=str(cache), budget_start=budget.start)
        with e6.hard_grace(budget):
            current = ("F10", "graded", "stage 1")
            first = learn_worker(dict(spec, condition="F10", arm="graded", in_process=True))
            trajectories = {("F10", "graded"): first}
            sinks[first["worker"]] = (first["manifest"], first["journal"])
            structural["F10"] = first["kills"]
            reference = first["structural"]["tv_mean_1_300"]
            log(f"stage 1: F10 graded mean |V| {first['structural']['mean_V_501_1000']:.2f}, kills {first['kills']}")
            if first["kills"]:
                kills_fired.append(("F10", first["kills"]))
                append("structural_kill", condition="F10", arm="graded", rules=first["kills"], enforced=enforce_kills)
            if not (kills_fired and enforce_kills):
                current = ("stage 2",)
                todo = [dict(spec, condition=c, arm=a, in_process=workers == 1)
                        for c, arms in ARMS.items() for a in arms if (c, a) != ("F10", "graded")]
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
                    integrity = [x for x in errors if isinstance(x, (IntegrityError, evidence.EvidenceError))]
                    raise (integrity or errors)[0]
                persisted = {r["condition"]: r["gate"] for r in read_records(results_path)
                             if r.get("attempt") == attempt and r.get("kind") == "structural_check" and r.get("arm") == "graded"}
                for cond in ("independent", "mixed"):
                    require(cond in persisted, f"persisted structural_check for the {cond} graded arm is missing")
                    kills = graded_structural_kills(persisted[cond], cond, reference_tv_1_300=reference)
                    structural[cond] = kills
                    append("structural_rules_applied", condition=cond, arm="graded", rules=kills, reference_tv_1_300=reference)
                    if kills:
                        kills_fired.append((cond, kills))
                        append("structural_kill", condition=cond, arm="graded", rules=kills, enforced=enforce_kills)
                log(f"stage 2: {len(results)} trajectories learned; kills {kills_fired}")
            if not (kills_fired and enforce_kills):
                for cond, arms in ARMS.items():
                    for arm in arms:
                        for M in loads:
                            current = (cond, arm, M)
                            budget.check(new_load=True)
                            append("load_started", stage="test", condition=cond, arm=arm, M=M)
                            state = trajectories[(cond, arm)]["states"][str(M)]
                            value = e7.evaluate_load(restore(state), M, state, cache, evidence_dir,
                                                     dict(meta, condition=cond, arm=arm), budget, coord)
                            value["learner_arm"], value["arm"] = value["arm"], arm
                            values.append(value)
                            append("load", load=value)
                            log(f"{cond} {arm} M={M}: C1={value['index']['C1']:.3f} C2={value['index']['C2']:.3f} "
                                f"joint={value['index']['joint_index']:.3f}")
                cross, ok = cross_arm(values, loads)
                invalid |= not ok
                graded = next(r for r in values if (r["condition"], r["arm"], r["M"]) == ("F10", "graded", loads[-1]))
                current = ("F10", "sanity", loads[-1])
                sanity = sanity_loads(graded, cache, evidence_dir, meta, budget, coord, append)
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
        rec = e7.verification_record(worker, entries, journal)
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
    for seed in (FROZEN["seeds"]["development"], FROZEN["seeds"]["held_out"]):
        good = e7._passing(committed, seed, source["code_sha256"])
        if not good:
            raise ValueError(f"commit a passing screen on {seed} before preparing the gate")
        attempts[str(seed)] = good[-1]["attempt"]
    value = dict(experiment="P2-E8", kind="gate_ready", timestamp=record.now(), source=source,
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
    return dict(experiment="P2-E8", kind="gated_verdict", verdict=status, seeds=verdicts, missing_seeds=missing,
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
        s = result["screen"]
        print(json.dumps(dict(verdict=s["verdict"], band=s["band"], delta_C2_vs_binary=s["delta_C2_vs_binary"],
                              failed=s["failed"], missing=s["missing"]), sort_keys=True), flush=True)
        return 0 if s["verdict"] in ("FEASIBILITY PASS", "FEASIBILITY FAIL") else 2
    if args.command == "riders":
        from analysis import p2e8_riders
        for row in p2e8_riders.run(args.seed, args.results, args.evidence, attempt=args.attempt, log=say):
            print(json.dumps({k: row.get(k) for k in ("kind", "arm", "M", "void")}, sort_keys=True), flush=True)
    elif args.command == "prepare-gate":
        print(json.dumps(prepare_gate(args.results), sort_keys=True))
    elif args.command == "verdict":
        value = dict(verdict(read_records(args.results, committed=True)), timestamp=record.now())
        record.append(value, args.results)
        print(json.dumps(value, sort_keys=True))
    else:
        for row in read_records(args.results):
            if row.get("kind") == "seed_screen":
                s = row["screen"]
                print(json.dumps(dict(seed=row["seed"], attempt=row["attempt"], full_size=row["full_size"], verdict=s["verdict"],
                                      band=s.get("band"), delta_C2_vs_binary=s.get("delta_C2_vs_binary"),
                                      failed=s["failed"], missing=s["missing"]), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
