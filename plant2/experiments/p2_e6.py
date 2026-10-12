"""P2-E6 frozen load-gated encoding; run --seed 101, screen, prepare-gate, verdict.

The mechanism and screen are frozen by docs/plant2/P2-E6-load-gated-encoding.md.
Results are append-only; all artifacts have exclusive, versioned names. Full runs
require committed code. Development never opens seeds 102/111..115 automatically.
"""
import argparse
import copy
import hashlib
import json
import os
import re
import signal
import subprocess
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from analysis import p2r1_replay as r1
from plant2 import record
from plant2.experiments import p2_e1_btsp as e1
from plant2.experiments import p2_e3_completion as e3
from plant2.experiments import p2_e5_structured as e5
from plant2.readout import replay

FROZEN_PATH = "docs/plant2/P2-E6-frozen.json"
FROZEN = json.loads((record.REPO / FROZEN_PATH).read_text())
CONTRACT = dict(e5.CONTRACT)
LOADS = tuple(FROZEN["loads"])
ARMS = tuple(FROZEN["arms"])
GATED = tuple(FROZEN["seeds"]["gated"])
RESULTS = record.REPO / "bench/results/p2e6.jsonl"
EVIDENCE = record.REPO / "bench/results/p2e6"
INHERITED = ["plant2/" + p for p in e5.REUSED_FILES] + ["plant2/experiments/p2_e5_structured.py"]
SOURCES = INHERITED + ["plant2/experiments/p2_e6.py", "analysis/p2r1_replay.py", FROZEN_PATH]


class IntegrityError(RuntimeError):
    pass


class ResourceStop(RuntimeError):
    pass


def require(ok, message):
    if not ok:
        raise IntegrityError(message)


def probabilities(history):
    """Exactly 80 float64 bisections over [0,max(H+1)], with fixed flip budget."""
    h = np.asarray(history, np.float64) + 1.0
    if not h.size:
        return h
    lo, hi = np.float64(0), np.max(h)
    target = np.float64(0.5 * h.size)
    for _ in range(80):
        middle = (lo + hi) / 2.0
        if np.minimum(1.0, middle / h).sum(dtype=np.float64) < target:
            lo = middle
        else:
            hi = middle
    p = np.minimum(1.0, ((lo + hi) / 2.0) / h)
    require(bool(np.isfinite(p).all() and (p >= 0).all() and (p <= 1).all()), "probability range")
    require(abs(float(p.sum()) - target) <= 1e-9, "expected flip budget")
    return p


def flip_mask(coins, p, eligible, plateau, seed, item, arm):
    candidate = coins < p[:, None]
    if arm == "candidate":
        selected = candidate
    elif arm == "baseline":
        selected = coins < 0.5
    elif arm == "random":
        selected = np.zeros_like(candidate)
        for col, cell in enumerate(plateau):
            count = int(candidate[:, col].sum())
            idx = e1.stream(seed, 31, item, int(cell)).choice(len(eligible), count, replace=False)
            selected[idx, col] = True
        require(np.array_equal(selected.sum(0), candidate.sum(0)), "random cell-wise flip counts")
    else:
        raise ValueError(arm)
    return selected, candidate.sum(0)


def ragged_digest(arrays):
    h = hashlib.sha256()
    for a in arrays:
        h.update(np.asarray([len(a)], dtype="<i8").tobytes())
        h.update(np.asarray(a, dtype="<i8").tobytes())
    return h.hexdigest()


class E6(e3.E3):
    """E3 learning with only its binary-toggle probabilities replaced."""

    def __init__(self, cfg, seed, arm="candidate", condition="F10"):
        super().__init__(cfg, seed)
        if arm not in ARMS or condition not in FROZEN["conditions"]:
            raise ValueError("unknown arm or condition")
        self.arm, self.condition = arm, condition
        spec = FROZEN["conditions"][condition]
        if spec:
            self._pat = e5.FamilyGen(seed, cfg["m"], cfg["a"], spec["s"], spec["F"])
        self.H = np.zeros(cfg["m"], np.int64)
        self.episodes = 0
        self.p_history, self.candidate_counts, self.actual_counts = [], [], []
        self.input_hashes, self.coin_hashes = [], []
        self._probe_A = None
        self.onset_offsets = []

    def _rates(self, active):
        if active is not None and self._probe_A is not None:
            A = self._probe_A[len(self.onset_offsets)]
            offset = self.mem.threshold() - float(self.mem.v_th)
            self.onset_offsets.append(dict(global_mv=float(offset.mean()),
                                           assigned_mv=float(offset[A].mean()) if A.size else None))
        super()._rates(active)

    def learn_one(self):
        c = self.c
        item = np.sort(self._pat.choice(c["m"], c["a"], replace=False))
        self.items.append(item)
        self.net.quiet()
        self._rates(item)
        plateau = np.flatnonzero(self._plat.random(c["n"]) < c["f_q"])
        counts = np.zeros(c["m"], np.int64)
        mem_spikes, sensory = 0, hashlib.sha256()
        for tick in range(c["t_item"]):
            sp = self.net.step(self._learn_in)
            counts[sp["inp"]] += 1
            mem_spikes += sp["mem"].size
            sensory.update(np.asarray([tick, sp["inp"].size], dtype="<i8").tobytes())
            sensory.update(np.asarray(sp["inp"], dtype="<i8").tobytes())
        eligible = np.flatnonzero(counts >= c["elig_min"])
        p = probabilities(self.H[eligible])
        # E-major, A-minor order is exactly inherited btsp_update's flat draw.
        coins = self._coin.random(eligible.size * plateau.size).reshape(eligible.size, plateau.size)
        selected, candidate_counts = flip_mask(coins, p, eligible, plateau, self.seed, self.episodes + 1, self.arm)
        keys = eligible[:, None] * c["n"] + plateau[None, :]
        pot, dep = self.store.toggle(keys[selected])
        self.H[eligible] += 1  # causal: only AFTER the write
        self.episodes += 1
        self.p_history.append(p)
        self.candidate_counts.append(candidate_counts)
        self.actual_counts.append(selected.sum(0))
        self.input_hashes.append(sensory.hexdigest())
        self.coin_hashes.append(hashlib.sha256(np.asarray(coins, dtype="<f8").tobytes()).hexdigest())
        self._load()
        self.A.append(plateau)
        self.plateaus_per_cell[plateau] += 1
        lg = self.learn_log
        lg["elig_frac"].append(float((counts[item] >= c["elig_min"]).mean()))
        lg["bg_eligible"].append(int(eligible.size - (counts[item] >= c["elig_min"]).sum()))
        lg["potentiated"].append(pot)
        lg["depressed"].append(dep)
        lg["mem_spikes"].append(mem_spikes)
        rng = e1.stream(self.seed, e3.CONT, len(self.items) - 1)
        responded = np.zeros(c["n"], bool)
        for _ in range(c["t_cont"]):
            responded[self.net.step(rng)["mem"]] = True
        R = np.flatnonzero(responded)
        self.fb.add((R[:, None] * c["m"] + eligible[None, :]).ravel())
        self.fb_plateau.add((plateau[:, None] * c["m"] + eligible[None, :]).ravel())
        self.R.append(R)
        self.E.append(eligible)
        self.cont_offset.append(float(self.mem.vbar.mean() - float(self.mem.v_rest)))


def state_digest(e):
    return hashlib.sha256(r1.json_bytes(dict(live=r1.live_digest(e), H=r1.sha_array(e.H), episodes=e.episodes,
        items=ragged_digest(e.items), A=ragged_digest(e.A), E=ragged_digest(e.E),
        learning=e.learn_log, inputs=e.input_hashes, coins=e.coin_hashes))).hexdigest()


def matched_digests(e):
    return dict(items=ragged_digest(e.items), A=ragged_digest(e.A), E=ragged_digest(e.E), H=r1.sha_array(e.H),
                sensory=hashlib.sha256(r1.json_bytes(e.input_hashes)).hexdigest(),
                coins=hashlib.sha256(r1.json_bytes(e.coin_hashes)).hexdigest(),
                candidate_counts=ragged_digest(e.candidate_counts))


class Budget:
    def __init__(self, start=None):
        self.start = start

    def check(self, new_load=False):
        if self.start is None:
            return
        limit = 3600 if new_load else 4200
        if time.time() >= self.start + limit:
            raise ResourceStop("60-minute ceiling" if new_load else "10-minute grace exhausted")


@contextmanager
def bounded_steps(e, budget):
    original, ticks = e.net.step, 0

    def step(rng):
        nonlocal ticks
        ticks += 1
        if ticks % 2048 == 0:
            budget.check()
        return original(rng)
    e.net.step = step
    try:
        yield
    finally:
        del e.net.step


def responders(raster, onset, window=50):
    parts = [raster[t] for t in range(onset, onset + window) if t in raster]
    return np.unique(np.concatenate(parts)) if parts else np.empty(0, np.int64)


def index_evidence(e, M, cues, out, raster, offsets=None):
    rows = r1.cue_evidence(e, cues, out)
    for q, row in zip(cues, rows):
        R = responders(raster, q["onset"])
        row["total50"] = int(R.size)
        if q["kind"] != "novel":
            A = e.A[q["index"]]
            row.update(own50=int(np.isin(A, R).sum()), spurious50=int(np.setdiff1d(R, A).size),
                       A_size=int(A.size), age_items=M - 1 - int(q["index"]))
        if offsets is not None:
            row["threshold_offset"] = offsets[row["cue_id"]]
    half = [r for r in rows if r["kind"] == "half"]
    joint = [r["recall50"] >= .8 and r["spurious50"] < .5 * r["A_size"] for r in half]
    c = out["criteria"]
    metrics = {name: c[name + "_frac"] for name in ("C1", "C2", "C3", "C4_recall", "C4_spurious")}
    metrics.update(joint_index=float(np.mean(joint)), joint_index_count=int(sum(joint)),
                   counts=r1.index_counts(out, e.c), recall_median=e3.memory_summary(out)["recall_median"],
                   latency_half_ms=e3.memory_summary(out)["latency_half_ms"])
    ages = {}
    for lo, hi in ((0, 99), (100, 499), (500, 999)):
        group = [r for r in half if lo <= r["age_items"] <= hi]
        ages[f"{lo}-{hi}"] = dict(n=len(group), C1=float(np.mean([r["recall50"] >= .8 for r in group])) if group else None,
            C2=float(np.mean([r["spurious50"] < .5 * r["A_size"] for r in group])) if group else None)
    metrics["age_strata"] = ages
    return rows, metrics


def raw_save(path, e, M, raster, n_ticks, cues, out, meta):
    payload = dict(metadata_json=np.asarray(r1.json_bytes(dict(meta, cfg=e.c, M=M, n_ticks=n_ticks,
                   probability_role="candidate probabilities; baseline deploys p=.5; random matches realized candidate counts")).decode()),
                   memory_out_json=np.asarray(r1.json_bytes(out).decode()), H=e.H, forward_keys=e.store.keys,
                   feedback_keys=e.fb.keys, assigned_feedback_keys=e.fb_plateau.keys,
                   learning_json=np.asarray(r1.json_bytes(e.learn_log).decode()),
                   raster_ticks=np.asarray(sorted(raster), np.int64),
                   cue_kind=np.asarray([q["kind"] for q in cues]), cue_index=np.asarray([q["index"] for q in cues]),
                   cue_onset=np.asarray([q["onset"] for q in cues]),
                   learned_mem_v=e.mem.v, learned_mem_vbar=e.mem.vbar, learned_mem_ring=e.mem.ring,
                   learned_mem_t_last=e.mem.t_last)
    for key in ("items", "A", "E", "R", "candidate_counts", "actual_counts"):
        r1.pack_ragged(payload, key, getattr(e, key))
    # Probabilities are float64; the integer ragged helper is intentionally not used.
    payload["p_offsets"] = np.concatenate(([0], np.cumsum([len(p) for p in e.p_history])))
    payload["probabilities"] = np.concatenate(e.p_history) if e.p_history else np.empty(0, np.float64)
    r1.pack_ragged(payload, "raster_cells", [raster[t] for t in sorted(raster)])
    for key in ("item", "cue", "missing", "other_missing"):
        r1.pack_ragged(payload, "cue_" + key, [q[key] for q in cues])
    with path.open("xb") as f:
        np.savez_compressed(f, **payload)
    return r1.file_info(path)


def content_evidence(e, raster, n_ticks, cues, store, budget):
    budget.check()
    indptr, post = store.csr()
    res, latency, oow = replay(raster, n_ticks, indptr, post, e.c["m"], np.array([2.8]), np.array([.3]), cues,
                              window=75, short=50, span=e.c["t_cue"] + e.c["t_gap"])
    budget.check()
    summary = {k: v for k, v in e3.score(res, latency, cues, e.c["n_old"], 1)[0].items() if k != "passes"}
    summary.update(counts=r1.content_counts(res, cues, e.c["n_old"]), out_of_window_spikes=int(oow[0]))
    summary["absolute_content_bars"] = {k: bool(summary[k] >= .9) for k in ("joint", "D3", "D4")}
    cols = list(res)
    portable = dict(columns=["cue_id"] + cols + ["latency_ms"],
        rows=[[i] + [int(res[k][i, 0]) for k in cols] + [float(latency[i, 0]) if np.isfinite(latency[i, 0]) else None]
              for i in range(len(cues))])
    return summary, portable


def evaluate_load(main, M, raw_path, evidence_path, meta, budget):
    before = state_digest(main)
    e = copy.deepcopy(main)
    cued, _, _ = e1.test_sets(e.c, e.seed, M)
    count = 2 * len(cued) + e.c["n_novel"]
    planned = e3.build_cues(e, M, [0] * count)
    e._probe_A = [e.A[q["index"]] if q["kind"] != "novel" else np.empty(0, np.int64) for q in planned]
    e.onset_offsets = []
    with bounded_steps(e, budget):
        out, raster, n_ticks, onsets, drift = e3.run_phase(e, M, phase=1)
    e._probe_A = None
    cues = e3.build_cues(e, M, onsets)
    require(len(e.onset_offsets) == len(cues), "cue onset threshold capture")
    digest = r1.raster_digest(raster, n_ticks, main.c["n"])
    raw = raw_save(raw_path, main, M, raster, n_ticks, cues, out, meta)
    rows, metrics = index_evidence(e, M, cues, out, raster, e.onset_offsets)
    summaries, portable_content = {}, {}
    stores = {"inherited": main.fb}
    if main.arm == "candidate":
        stores["assigned_A"] = main.fb_plateau
    for name, store in stores.items():
        summaries[name], portable_content[name] = content_evidence(e, raster, n_ticks, cues, store, budget)
        require(r1.raster_digest(raster, n_ticks, e.c["n"]) == digest, "content mutated memory raster")
    require(state_digest(main) == before, "tests changed main weights/H/RNGs/counter/neural state")
    require(np.array_equal(main.store.keys, e.store.keys) and np.array_equal(main.H, e.H), "evaluation write")
    mean_A = float(np.mean([a.size for a in main.A]))
    protocol = dict(eligibility=bool(np.mean(main.learn_log["elig_frac"]) >= .95),
                    mean_A_1000=bool(18.5 <= mean_A <= 21.5) if M == 1000 else None,
                    settled=bool(drift[0] <= .2))
    stats = dict(mean_A=mean_A, eligibility_mean=float(np.mean(main.learn_log["elig_frac"])), drift_mv=list(drift),
                 potentiated=int(sum(main.learn_log["potentiated"])), depressed=int(sum(main.learn_log["depressed"])),
                 forward_size=main.store.size, forward_density=main.store.size / (main.c["m"] * main.c["n"]),
                 probability_min=float(min((p.min() for p in main.p_history if p.size), default=0)),
                 probability_max=float(max((p.max() for p in main.p_history if p.size), default=0)),
                 max_expected_budget_error=max((abs(float(p.sum()) - len(p) / 2) for p in main.p_history), default=0))
    compact = dict(meta, M=M, index_cues=rows, content=portable_content, index=metrics, content_summaries=summaries,
                   protocol=protocol, learning=stats, raster_sha256=digest, raw=raw,
                   limitation="C3 uses inherited independent novel cues, not related unseen exemplars")
    with evidence_path.open("xb") as f:
        f.write(r1.json_bytes(compact))
    return dict(M=M, condition=main.condition, arm=main.arm, index=metrics, content=summaries, protocol=protocol,
                learning=stats, matching=matched_digests(main), actual_flip_counts=ragged_digest(main.actual_counts),
                forward_sha256=r1.sha_array(main.store.keys), feedback_sha256=r1.sha_array(main.fb.keys),
                H_sha256=r1.sha_array(main.H), raster_sha256=digest, integrity=True, raw=raw,
                portable=r1.file_info(evidence_path, relative=evidence_path.is_relative_to(record.REPO)))


def unpack(archive, name):
    offsets = archive[name + "_offsets"]
    values = archive[name]
    return [values[a:b].copy() for a, b in zip(offsets[:-1], offsets[1:])]


def sanity_loads(candidate, cache, evidence, meta, budget, append):
    """Identity permutation and genuinely untrained empty twin; neither feeds learning."""
    with np.load(candidate["raw"]["path"], allow_pickle=False) as z:
        cfg = json.loads(str(z["metadata_json"]))["cfg"]
        n_ticks = json.loads(str(z["metadata_json"]))["n_ticks"]
        items, A = unpack(z, "items"), unpack(z, "A")
        raster = dict(zip(z["raster_ticks"].tolist(), unpack(z, "raster_cells")))
        onsets = z["cue_onset"].tolist()
    seed, M = meta["seed"], candidate["M"]
    budget.check(new_load=True)
    pi = e1.stream(seed, 32, M).permutation(cfg["n"])
    wrong = {t: pi[s] for t, s in raster.items()}
    require(all(len(wrong[t]) == len(s) for t, s in raster.items()), "wrong-label tick counts")
    target = SimpleNamespace(c=cfg, seed=seed, items=items, A=A)
    cued, _, _ = e1.test_sets(cfg, seed, M)
    half = []
    for j, i in enumerate(cued):
        R = responders(wrong, onsets[j])
        own = int(np.isin(A[i], R).sum())
        half.append(dict(index_0based=int(i), A_size=int(A[i].size), own50=own, total50=int(R.size),
                         spurious50=int(R.size - own), recall50=own / A[i].size if A[i].size else 0.0))
    wrong_result = dict(kind="wrong_label", C1=float(np.mean([r["recall50"] >= .8 for r in half])),
                        count_preserved=True, original_raw=candidate["raw"],
                        raster_sha256=r1.raster_digest(wrong, n_ticks, cfg["n"]),
                        permutation_sha256=r1.sha_array(pi), per_cue=half)
    raw_path = cache / "F10-wrong-label-M1000.npz"
    with raw_path.open("xb") as f:
        np.savez_compressed(f, permutation=pi, metadata_json=np.asarray(r1.json_bytes(meta).decode()))
    wrong_result["raw"] = r1.file_info(raw_path)
    path = evidence / (meta["attempt"] + "-F10-wrong-label-M1000.json")
    with path.open("xb") as f:
        f.write(r1.json_bytes(dict(meta, **wrong_result)))
    wrong_result["portable"] = r1.file_info(path, relative=path.is_relative_to(record.REPO))
    append("sanity_load", sanity={k: v for k, v in wrong_result.items() if k != "per_cue"})
    budget.check(new_load=True)
    empty = e3.E3(cfg, seed)
    empty.items, empty.A = [x.copy() for x in items], [x.copy() for x in A]
    empty.H = np.zeros(cfg["m"], np.int64)
    for key in ("candidate_counts", "actual_counts", "p_history"):
        setattr(empty, key, [])
    require(empty.store.size == empty.fb.size == empty.fb_plateau.size == 0, "empty twin received training")
    with bounded_steps(empty, budget):
        out, eraster, eticks, eonsets, drift = e3.run_phase(empty, M, phase=1)
    cues = e3.build_cues(empty, M, eonsets)
    rows, metrics = index_evidence(empty, M, cues, out, eraster)
    for q, row in zip(cues, rows):
        row["total100"] = int(responders(eraster, q["onset"], cfg["t_cue"]).size)
    empty_result = dict(kind="empty_store", responders=sum(r["total100"] for r in rows),
                        total_raster_spikes=sum(s.size for s in eraster.values()), index=metrics,
                        drift_mv=list(drift), stores_empty=empty.store.size == empty.fb.size == empty.fb_plateau.size == 0)
    raw_path = cache / "F10-empty-store-M1000.npz"
    empty_result["raw"] = raw_save(raw_path, empty, M, eraster, eticks, cues, out, meta)
    path = evidence / (meta["attempt"] + "-F10-empty-store-M1000.json")
    with path.open("xb") as f:
        f.write(r1.json_bytes(dict(meta, **empty_result, per_cue=rows)))
    empty_result["portable"] = r1.file_info(path, relative=path.is_relative_to(record.REPO))
    append("sanity_load", sanity=empty_result)
    return {"wrong_label": {k: v for k, v in wrong_result.items() if k != "per_cue"}, "empty_store": empty_result}


def paired(candidate, control):
    """Descriptive paired counts, with the same item/cue identity asserted."""
    def read(row):
        path = Path(row["portable"]["path"])
        if not path.is_absolute():
            path = record.REPO / path
        return [q for q in json.loads(path.read_text())["index_cues"] if q["kind"] == "half"]
    a, b = read(candidate), read(control)
    require([r["index_0based"] for r in a] == [r["index_0based"] for r in b], "paired item identity")
    out = {}
    for name, predicate in (("recall", lambda r: r["recall50"] >= .8),
                            ("specificity", lambda r: r["spurious50"] < .5 * r["A_size"]),
                            ("joint", lambda r: r["recall50"] >= .8 and r["spurious50"] < .5 * r["A_size"])):
        ca, cb = np.asarray([predicate(r) for r in a]), np.asarray([predicate(r) for r in b])
        out[name] = dict(n=len(a), candidate_only=int((ca & ~cb).sum()), control_only=int((~ca & cb).sum()),
                         both=int((ca & cb).sum()), neither=int((~ca & ~cb).sum()),
                         candidate_fraction=float(ca.mean()), control_fraction=float(cb.mean()))
    return out


def screen(loads, sanity, invalid=False, paired_evidence=None):
    """Executable prospective screen. Missing evidence never becomes a success."""
    by = {(r["condition"], r["arm"], r["M"]): r for r in loads}
    vectors = {name: {} for name in ("index", "content", "protocol", "sanity")}
    missing = []

    def row(cond, arm, M):
        key = (cond, arm, M)
        if key not in by and str(key) not in missing:
            missing.append(str(key))
        return by.get(key)

    for cond in ("F10", "independent"):
        for M in LOADS:
            B, C, R = (row(cond, arm, M) for arm in ARMS)
            label = f"{cond}/{M}"
            if C:
                for k, bar in FROZEN["bars"].items():
                    vectors["index"][f"{label}/{k}"] = bool(C["index"][k] >= bar)
            if C and B:
                vectors["index"][f"{label}/C1_nonregression"] = bool(C["index"]["C1"] + 1e-12 >= B["index"]["C1"] - .03)
                if cond == "independent":
                    vectors["index"][f"{label}/C2_nonregression"] = bool(C["index"]["C2"] + 1e-12 >= B["index"]["C2"] - .03)
                    for k in ("joint", "D4"):
                        vectors["content"][f"{label}/{k}_nonregression"] = bool(
                            C["content"]["inherited"][k] + 1e-12 >= B["content"]["inherited"][k] - .05)
            for arm, value in (("baseline", B), ("candidate", C), ("random", R)):
                if value:
                    for k, ok in value["protocol"].items():
                        if ok is not None:
                            vectors["protocol"][f"{label}/{arm}/{k}"] = bool(ok)
                    invalid |= not value.get("integrity", False)
    C, B, R = (by.get(("F10", a, 1000)) for a in ("candidate", "baseline", "random"))
    for name, ctl, margin in (("baseline", B, .20), ("random", R, .10)):
        if C and ctl:
            vectors["index"][f"F10/1000/C2_vs_{name}"] = bool(C["index"]["C2"] + 1e-12 >= ctl["index"]["C2"] + margin)
            vectors["index"][f"F10/1000/joint_vs_{name}"] = bool(C["index"]["joint_index"] + 1e-12 >= ctl["index"]["joint_index"] + .10)
    for name in ("wrong_label", "empty_store"):
        if name not in sanity:
            missing.append(name)
    if "wrong_label" in sanity:
        vectors["sanity"]["wrong_label_C1"] = bool(sanity["wrong_label"]["C1"] < .10)
        invalid |= not sanity["wrong_label"]["count_preserved"]
    if "empty_store" in sanity:
        vectors["sanity"]["empty_store_zero_responders"] = sanity["empty_store"]["responders"] == 0
        invalid |= not sanity["empty_store"]["stores_empty"]
    if paired_evidence is not None:
        for cond in ("F10", "independent"):
            for M in LOADS:
                for arm in ("baseline", "random"):
                    key = f"{cond}/{M}/{arm}"
                    if key not in paired_evidence:
                        missing.append("paired/" + key)
    failed = [f"{category}/{k}" for category, values in vectors.items() for k, v in values.items() if not v]
    index_failed = any(not ok for category in ("index", "sanity", "protocol") for ok in vectors[category].values())
    pure = "INVALID" if invalid else "FAIL" if index_failed else "PARTIAL" if missing else "PASS"
    status = "INVALID" if invalid else "FEASIBILITY FAIL" if failed else "FEASIBILITY PASS"
    if missing and not invalid:
        status = "PARTIAL + FEASIBILITY FAIL" if failed else "PARTIAL"
    return dict(verdict=status, pure_index_verdict=pure, vectors=vectors, failed_parts=failed,
                missing=missing, complete=not missing, integrity=not invalid,
                scope="index feasibility and separate independent content regression; not Stage 1 or a content PASS")


def git_read(*args):
    p = subprocess.run(["git", "-C", str(record.REPO), *args], capture_output=True)
    if p.returncode:
        raise ValueError("required committed source/evidence absent: " + " ".join(args))
    return p.stdout


def source_manifest():
    hashes = {}
    for path in SOURCES:
        raw = (record.REPO / path).read_bytes()
        require(raw == git_read("show", "HEAD:" + path), "uncommitted executable source: " + path)
        if path in INHERITED:
            require(raw == git_read("show", FROZEN["source_baseline"] + ":" + path), "inherited source drift: " + path)
        hashes[path] = hashlib.sha256(raw).hexdigest()
    contract = FROZEN["contract_path"]
    require((record.REPO / contract).read_bytes() == git_read("show", FROZEN["contract_commit"] + ":" + contract), "contract drift")
    return dict(commit=git_read("rev-parse", "HEAD").decode().strip(),
                plant2_tree=git_read("rev-parse", "HEAD:plant2").decode().strip(), files=hashes,
                code_sha256=hashlib.sha256(r1.json_bytes(hashes)).hexdigest(),
                contract_sha256=hashlib.sha256((record.REPO / contract).read_bytes()).hexdigest())


def read_records(path=RESULTS, committed=False):
    if committed:
        try:
            raw = git_read("show", "HEAD:" + str(Path(path).relative_to(record.REPO))).decode()
        except ValueError:
            return []
    else:
        raw = Path(path).read_text() if Path(path).exists() else ""
    return [json.loads(line) for line in raw.splitlines() if line.strip()]


def verified_screen(row, records, code, require_complete=True):
    """Recompute a complete full-size screen from one exact attempt's journal."""
    if not row.get("full_size") or row.get("source", {}).get("code_sha256") != code:
        return False
    attempt = row.get("attempt")
    lineage = [r for r in records if r.get("attempt") == attempt]
    if any(not r.get("full_size") or r.get("seed") != row.get("seed") or
           r.get("source", {}).get("code_sha256") != code for r in lineage):
        return False
    starts = [r for r in lineage if r.get("kind") == "seed_started"]
    ends = [r for r in lineage if r.get("kind") == "seed_screen"]
    if len(starts) != 1 or len(ends) != 1 or starts[0].get("requested_loads") != list(LOADS):
        return False
    expected_stage = "development" if row["seed"] == 101 else "feasibility" if row["seed"] == 102 else "gated"
    if starts[0].get("authorization", {}).get("stage") != expected_stage:
        return False
    loads = [r["load"] for r in lineage if r.get("kind") == "load"]
    identities = [(r["condition"], r["arm"], r["M"]) for r in loads]
    if len(identities) != len(set(identities)):
        return False
    sanity_rows = [r["sanity"] for r in lineage if r.get("kind") == "sanity_load"]
    if len({r["kind"] for r in sanity_rows}) != len(sanity_rows):
        return False
    pairs = {r["comparison_key"]: r["paired"] for r in lineage if r.get("kind") == "paired"}
    if any(r.get("kind") == "interrupted" and r.get("integrity_defect") for r in lineage):
        return False
    recomputed = screen(loads, {r["kind"]: r for r in sanity_rows}, paired_evidence=pairs)
    return (recomputed == row.get("screen") and (recomputed["complete"] or not require_complete)
            and recomputed["integrity"])


def passing_screens(records, code):
    screens = [r for r in records if r.get("kind") == "seed_screen" and r.get("full_size")
               and r.get("source", {}).get("code_sha256") == code]
    rejected = {r["seed"] for r in screens if r["screen"]["verdict"] == "INVALID" or r["screen"]["failed_parts"]}
    return {r["seed"]: r for r in screens if r["seed"] not in rejected and
            verified_screen(r, records, code) and r["screen"]["verdict"] == "FEASIBILITY PASS"}


def verify_committed_evidence(screen_row, committed):
    for row in committed:
        if row.get("attempt") != screen_row["attempt"]:
            continue
        value = row.get("load") if row.get("kind") == "load" else row.get("sanity") if row.get("kind") == "sanity_load" else None
        if value:
            descriptor = value["portable"]
            path = Path(descriptor["path"])
            if path.is_absolute():
                path = path.relative_to(record.REPO)
            actual = hashlib.sha256(git_read("show", "HEAD:" + str(path))).hexdigest()
            require(actual == descriptor["sha256"], "uncommitted/mismatched portable feasibility evidence")


def seed_guard(seed, manifest, committed, existing):
    if seed not in (101, 102) + GATED:
        raise ValueError("only development101, contingent102 and fresh111..115 are authorized")
    if seed == 101:
        return dict(stage="development", prerequisite_attempts={})
    code = manifest["code_sha256"]
    feasibility = passing_screens(committed, code)
    needed = (101,) if seed == 102 else (101, 102)
    for previous in needed:
        if previous not in feasibility or feasibility[previous]["screen"]["verdict"] != "FEASIBILITY PASS":
            raise ValueError(f"seed {seed} locked: committed passing screen on {previous} with exact source required")
        verify_committed_evidence(feasibility[previous], committed)
    prerequisites = {str(s): feasibility[s]["attempt"] for s in needed}
    if seed in GATED:
        ready = [r for r in committed if r.get("kind") == "gate_ready" and r.get("source", {}).get("code_sha256") == code
                 and r.get("feasibility_attempts") == prerequisites and r.get("predictions") == FROZEN["predictions"]]
        if not ready:
            raise ValueError("gated seeds locked: commit prepare-gate evidence/predictions/source hashes first")
        if any(r.get("seed") == seed and r.get("full_size") and r.get("kind") == "seed_started" for r in existing):
            raise ValueError("gated seed already attempted; an explicit owner ruling is required for a rerun")
        if any(r.get("seed") in GATED and r.get("full_size") and r.get("kind") == "seed_screen" and r["screen"]["verdict"] == "INVALID" for r in existing):
            raise ValueError("gating stopped after an integrity failure; explicit owner ruling required")
        return dict(stage="gated", prerequisite_attempts=prerequisites,
                    committed_gate_ready_sha256=hashlib.sha256(r1.json_bytes(ready[-1])).hexdigest())
    return dict(stage="feasibility", prerequisite_attempts=prerequisites)


def uniform_integrity():
    cfg = dict(CONTRACT, m=160, n=80, n_novel=2, f_q=.05)
    wrapper = E6(cfg, 101, "baseline", "independent")
    frozen = e3.E3(cfg, 101)
    wrapper.learn(4)
    frozen.learn(4)
    require(r1.live_digest(wrapper) == r1.live_digest(frozen), "uniform wrapper does not reproduce frozen E3")
    require(all(np.array_equal(a, b) for a, b in zip(wrapper.E, frozen.E)), "uniform eligibility mismatch")
    return True


def resource_budget(process_start):
    """One permanent experiment-wide clock; includes other active takeover simulations."""
    import fcntl
    directory = record.cache_dir("p2e6")
    with (directory / "resource-lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        active = []
        for entry in Path("/proc").iterdir():
            if not entry.name.isdigit():
                continue
            try:
                words = (entry / "cmdline").read_bytes().decode().split("\0")
            except (OSError, UnicodeError):
                continue
            if any(w.startswith("plant2.experiments.p2_e") or w in ("analysis.p2r1_replay", "analysis.p2e4_diagnosis") for w in words):
                active.append(int(entry.name))
        if len(active) > 4:
            raise ResourceStop("more than four active takeover simulation processes")
        path = directory / "resource-window.json"
        if not path.exists():
            with path.open("xb") as f:
                f.write(r1.json_bytes(dict(start_unix=process_start, start=record.now(), first_pid=os.getpid(), max_processes=4)))
        start = json.loads(path.read_text())["start_unix"]
    return Budget(start)


@contextmanager
def hard_grace(budget):
    if budget.start is None:
        yield
        return
    prior = signal.getsignal(signal.SIGALRM)

    def stop(signum, frame):
        raise ResourceStop("experiment-wide 10-minute grace exhausted")
    signal.signal(signal.SIGALRM, stop)
    signal.setitimer(signal.ITIMER_REAL, max(.001, budget.start + 4200 - time.time()))
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, prior)


def run_seed(seed, results_path=RESULTS, evidence_dir=EVIDENCE, cfg=None, loads=LOADS, attempt=None, log=print):
    process_start = time.time()
    full = cfg is None
    if not full and (seed != 101 or Path(results_path) == RESULTS or Path(evidence_dir) == EVIDENCE):
        raise ValueError("small integrity runs require development101 and explicit non-production output paths")
    cfg = dict(CONTRACT if cfg is None else cfg)
    if full and tuple(loads) != LOADS:
        raise ValueError("full runs require nested 500,1000 checkpoints")
    source = source_manifest() if full else dict(code_sha256="SMALL_INTEGRITY_TEST_ONLY", files={})
    authorization = seed_guard(seed, source, read_records(results_path, committed=True), read_records(results_path)) if full else dict(stage="integrity_test")
    attempt = attempt or f"seed{seed}-{time.time_ns()}-{uuid.uuid4().hex[:8]}"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", attempt):
        raise ValueError("attempt must be a filename component")
    cache, evidence = record.cache_dir("p2e6", attempt), Path(evidence_dir)
    evidence.mkdir(parents=True, exist_ok=True)
    meta = dict(experiment="P2-E6", schema=1, attempt=attempt, seed=seed, source=source, runtime=record.runtime(),
                full_size=full, authorization=authorization, contract_commit=FROZEN["contract_commit"], predictions=FROZEN["predictions"])
    with (cache / "attempt.json").open("xb") as f:
        f.write(r1.json_bytes(meta))

    def append(kind, **fields):
        record.append(dict(meta, kind=kind, timestamp=record.now(), wall_s=round(time.time() - process_start, 3), **fields), results_path)

    append("seed_started", process_start_unix=process_start, requested_loads=list(loads))
    values, sanity, comparisons = [], {}, {}
    invalid, interrupted, current = False, None, None
    try:
        budget = resource_budget(process_start) if full else Budget()
        append("resource_window", start_unix=budget.start, deadline_unix=budget.start + 3600 if full else None,
               grace_deadline_unix=budget.start + 4200 if full else None)
        uniform_integrity()
        with hard_grace(budget):
            for condition in ("F10", "independent", "F40"):
                if condition == "F40":
                    candidate = next((r for r in values if r["condition"] == "F10" and r["arm"] == "candidate" and r["M"] == loads[-1]), None)
                    if candidate:
                        current = ("F10", "sanity", loads[-1])
                        sanity = sanity_loads(candidate, cache, evidence, meta, budget, append)
                for arm in (ARMS if condition != "F40" else ("baseline", "candidate")):
                    main = E6(cfg, seed, arm, condition)
                    for M in loads:
                        current = (condition, arm, M)
                        budget.check(new_load=True)
                        append("load_started", condition=condition, arm=arm, M=M)
                        with bounded_steps(main, budget):
                            main.learn(M)
                        paths = (cache / f"{condition}-{arm}-M{M}.npz", evidence / f"{attempt}-{condition}-{arm}-M{M}.json")
                        value = evaluate_load(main, M, *paths, dict(meta, condition=condition, arm=arm), budget)
                        previous = [r for r in values if r["condition"] == condition and r["M"] == M]
                        for other in previous:
                            require(value["matching"] == other["matching"], "cross-arm items/A/E/H/sensory/coin/candidate-count mismatch")
                            if {arm, other["arm"]} == {"candidate", "random"}:
                                require(value["actual_flip_counts"] == other["actual_flip_counts"], "random/candidate realized flip counts differ")
                        values.append(value)
                        append("load", load=value)
                        C = next((r for r in values if (r["condition"], r["arm"], r["M"]) == (condition, "candidate", M)), None)
                        for control in ("baseline", "random"):
                            B = next((r for r in values if (r["condition"], r["arm"], r["M"]) == (condition, control, M)), None)
                            key = f"{condition}/{M}/{control}"
                            if C and B and key not in comparisons:
                                comparisons[key] = paired(C, B)
                                append("paired", comparison_key=key, paired=comparisons[key])
                        log(f"{condition} {arm} M={M}: C1={value['index']['C1']:.3f} C2={value['index']['C2']:.3f} joint={value['index']['joint_index']:.3f}")
    except IntegrityError as exc:
        invalid, interrupted = True, repr(exc)
    except (ResourceStop, KeyboardInterrupt) as exc:
        interrupted = repr(exc)
    except Exception as exc:
        invalid, interrupted = True, repr(exc)
    # Recover completed sanity evidence even if the second check was interrupted.
    for row in read_records(results_path):
        if row.get("attempt") == attempt and row.get("kind") == "sanity_load":
            sanity[row["sanity"]["kind"]] = row["sanity"]
    decision = screen(values, sanity, invalid, comparisons)
    if interrupted:
        append("interrupted", current=current, error=interrupted, integrity_defect=invalid,
               completed_loads=[(r["condition"], r["arm"], r["M"]) for r in values])
    transfer = {}
    for M in LOADS:
        group = {r["arm"]: r for r in values if r["condition"] == "F40" and r["M"] == M}
        transfer[str(M)] = {arm: dict(absolute_index_bars={k: bool(r["index"][k] >= bar) for k, bar in FROZEN["bars"].items()},
                                     protocol=r["protocol"]) for arm, r in group.items()}
    result = dict(meta, kind="seed_screen", timestamp=record.now(), screen=decision, paired=comparisons, transfer=transfer,
                  end_unix=time.time(), process_start_unix=process_start, wall_s=round(time.time() - process_start, 3),
                  interrupted=interrupted, completed_loads=len(values), transfer_complete=sum(r["condition"] == "F40" for r in values) == 4)
    record.append(result, results_path)
    return result


def prepare_gate():
    source = source_manifest()
    committed = read_records(committed=True)
    seed_guard(102, source, committed, read_records())
    good = passing_screens(committed, source["code_sha256"])
    if 102 not in good or good[102]["screen"]["verdict"] != "FEASIBILITY PASS":
        raise ValueError("commit passing calibration102 before preparing gated evidence")
    verify_committed_evidence(good[102], committed)
    value = dict(experiment="P2-E6", kind="gate_ready", timestamp=record.now(), source=source,
                 feasibility_attempts={str(s): good[s]["attempt"] for s in (101, 102)}, predictions=FROZEN["predictions"])
    record.append(value, RESULTS)
    return value


def verdict(records, committed=()):
    full_records = [r for r in records if r.get("full_size")]
    selected, unauthorized, duplicates = {}, [], []
    readiness = {}
    for r in committed:
        if r.get("kind") != "gate_ready":
            continue
        code = r.get("source", {}).get("code_sha256")
        good = passing_screens(committed, code)
        if all(s in good for s in (101, 102)) and r.get("feasibility_attempts") == {str(s): good[s]["attempt"] for s in (101, 102)} and r.get("predictions") == FROZEN["predictions"]:
            readiness[hashlib.sha256(r1.json_bytes(r)).hexdigest()] = code
    for seed in GATED:
        starts = [r for r in full_records if r.get("seed") == seed and r.get("kind") == "seed_started"]
        ends = [r for r in full_records if r.get("seed") == seed and r.get("kind") == "seed_screen"]
        if len(starts) > 1 or len(ends) > 1:
            duplicates.append(seed)
        if len(starts) == len(ends) == 1:
            row = ends[0]
            auth = starts[0].get("authorization", {})
            code = row.get("source", {}).get("code_sha256")
            if readiness.get(auth.get("committed_gate_ready_sha256")) != code or not verified_screen(row, records, code, require_complete=False):
                unauthorized.append(seed)
            selected[seed] = row
    missing = [s for s in GATED if s not in selected]
    invalid = sorted({r["seed"] for r in full_records if r.get("seed") in GATED and r.get("kind") == "seed_screen"
                      and r["screen"]["verdict"] == "INVALID"})
    failed = [s for s, r in selected.items() if r["screen"]["failed_parts"]]
    partial = [s for s, r in selected.items() if not r["screen"]["complete"]]
    sources = {r["source"]["code_sha256"] for r in selected.values()}
    status = "INVALID" if invalid or duplicates or unauthorized or len(sources) > 1 else "PARTIAL" if missing or partial else "FAIL" if failed else "PASS"
    return dict(experiment="P2-E6", kind="gated_verdict", verdict=status, missing_seeds=missing,
                failed_seeds=failed, invalid_seeds=invalid, partial_seeds=partial, duplicate_seeds=duplicates,
                unauthorized_seeds=unauthorized,
                pure_index={str(s): r["screen"]["pure_index_verdict"] for s, r in selected.items()},
                scope="E6 only; neither Stage 1 completion nor a content PASS")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--seed", type=int, required=True, choices=(101, 102) + GATED)
    run.add_argument("--attempt")
    sub.add_parser("prepare-gate")
    sub.add_parser("screen")
    sub.add_parser("verdict")
    args = parser.parse_args(argv)
    if args.command == "run":
        result = run_seed(args.seed, attempt=args.attempt, log=lambda msg: print(f"[{record.now()}] {msg}", flush=True))
        print(json.dumps(result["screen"], sort_keys=True), flush=True)
        return 2 if "PARTIAL" in result["screen"]["verdict"] or result["screen"]["verdict"] == "INVALID" else 0
    if args.command == "prepare-gate":
        print(json.dumps(prepare_gate(), sort_keys=True))
    elif args.command == "verdict":
        value = dict(verdict(read_records(), committed=read_records(committed=True)), timestamp=record.now())
        record.append(value, RESULTS)
        print(json.dumps(value, sort_keys=True))
    else:
        for row in read_records():
            if row.get("kind") == "seed_screen":
                print(json.dumps(dict(seed=row["seed"], attempt=row["attempt"], screen=row["screen"]), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
