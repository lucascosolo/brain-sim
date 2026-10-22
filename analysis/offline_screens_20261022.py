"""Offline screens on persisted evidence (docs/plant2/OFFLINE-SCREENS-20261022.md).

Zero-seed analyses of the P2-R2b artifacts. Every output is labelled offline; nothing here is a
capability or a gate. Library functions are pure and tested on synthetic inputs; the CLI reads
the verified P2-R2b artifacts and their raw learned checkpoints.
"""
import argparse
import hashlib
import json
import math
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from plant2 import evidence, record
from plant2.btsp import BinarySynapses, btsp_update
from plant2.experiments import p2_e1_btsp as e1

SEEDS = (105, 106)
ARMS = ("ORIGINAL", "DEGREE_NULL")
LOADS = (500, 1000)
RESULTS = record.REPO / "bench/results/offline-screens-20261022.jsonl"
EVIDENCE = record.REPO / "bench/results/offline-screens-20261022"
R2B_EVIDENCE = record.REPO / "bench/results/p2r2b"
CACHE_ROOT = Path.home() / ".cache/brain-sim/plant2-research-20261022/offline-screens"
THRESHOLDS = (8, 12, 16, 19, 24)
CUTS = (20, 25, 30, 35, 40, 45, 50)
FROZEN = ("plant2/btsp.py", "plant2/evidence.py", "plant2/record.py",
          "plant2/experiments/p2_e1_btsp.py", "plant2/experiments/p2_e3_completion.py",
          "plant2/experiments/p2_e5_structured.py")
LABELS = {"A": "offline proxy (continuation responders, count rule)", "B": "offline static count",
          "C": "offline descriptive", "D": "offline descriptive"}


# ------------------------------------------------------------------ screen A

def count_rule_threshold(q_size):
    return math.ceil(round(0.3 * q_size + 7.14, 9))


def _fraction(num, den):
    return None if den == 0 else num / den


def gate_prescreen(items, A, E, R, protos, family, thresholds=THRESHOLDS):
    lines = max(int(max(e.max() for e in E if len(e))), int(max(i.max() for i in items if len(i)))) + 1
    cells = max(int(max(r.max() for r in R if len(r))), int(max(a.max() for a in A if len(a)))) + 1
    writers = np.zeros((lines, cells), bool)
    rows = []
    for k in range(len(items)):
        A_k, E_k, R_k = (np.asarray(x, np.int64) for x in (A[k], E[k], R[k]))
        Q = np.setdiff1d(R_k, A_k)
        P = np.intersect1d(items[k], protos[family(k)])
        PE, NE = np.intersect1d(P, E_k), np.setdiff1d(E_k, P)
        counts = writers[:, Q].sum(axis=1)
        row = dict(episode=k, q_size=int(Q.size), p_size=int(P.size), theta_primary=count_rule_threshold(Q.size))
        for key, theta in [("t_primary", row["theta_primary"])] + [(f"t_{t}", t) for t in thresholds]:
            G = np.flatnonzero(counts >= theta)
            V, GP = np.intersect1d(G, E_k), np.intersect1d(G, PE)
            row[key] = dict(V_size=int(V.size), proto_predicted=_fraction(GP.size, PE.size),
                            nonproto_predicted=_fraction(np.intersect1d(G, NE).size, NE.size),
                            veto_precision=_fraction(GP.size, V.size))
        rows.append(row)
        writers[np.ix_(E_k, R_k)] = True
    return rows


# ------------------------------------------------------------------ screen B

def rebuild_forward_store(seed, A, E, n):
    n_pre = max([int(e.max()) + 1 for e in E if len(e)] or [1])
    store = BinarySynapses(n_pre, n)
    rng = e1.stream(seed, e1.COIN)
    for a, e in zip(A, E):
        btsp_update(store, a, e, rng)
    return store.keys


def integrity_gate(rebuilt, persisted):
    return bool(np.array_equal(np.asarray(rebuilt, np.int64), np.asarray(persisted, np.int64)))


def rebuild_branch_store(seed, A, E, n, K):
    rng = e1.stream(seed, e1.COIN)
    plateaus = np.zeros(n, np.int64)
    held = np.empty(0, np.int64)
    for a, e in zip(A, E):
        a, e = np.asarray(a, np.int64), np.asarray(e, np.int64)
        if a.size and e.size:
            cand = (e[:, None] * n + a[None, :]).ravel()
            flips = np.unique(cand[rng.random(cand.size) < 0.5])
            pre, cell = flips // n, flips % n
            keys = pre * (n * K) + cell * K + plateaus[cell] % K
            held = np.setxor1d(held, keys, assume_unique=True)
        plateaus[a] += 1
    return held.astype(np.int64)


def cue_counts(keys, n, cue_lines):
    keys = np.asarray(keys, np.int64)
    kept = keys[np.isin(keys // n, np.asarray(cue_lines, np.int64))]
    return np.bincount(kept % n, minlength=n)


def branch_max_counts(keys, n, K, cue_lines):
    keys = np.asarray(keys, np.int64)
    kept = keys[np.isin(keys // (n * K), np.asarray(cue_lines, np.int64))]
    per_branch = np.bincount((kept % (n * K)), minlength=n * K).reshape(n, K)
    return per_branch.max(axis=1)


# ------------------------------------------------------------------ screen C

def _pcts(values):
    if len(values) == 0:
        return None, None, None
    p10, med, p90 = np.percentile(np.asarray(values, float), [10, 50, 90])
    return float(p10), float(med), float(p90)


def latency_split(first_spikes, own):
    own = set(int(c) for c in own)
    own_t = [t for c, t in first_spikes if int(c) in own]
    spur_t = [t for c, t in first_spikes if int(c) not in own]
    out = dict(n_own=len(own_t), n_spurious=len(spur_t))
    for name, vals in (("own", own_t), ("spurious", spur_t)):
        p10, med, p90 = _pcts(vals)
        out.update({f"{name}_median": med, f"{name}_p10": p10, f"{name}_p90": p90})
    return out


def latency_cut(first_spikes, own, a_size):
    own = set(int(c) for c in own)
    out = {}
    for cut in CUTS:
        kept = [(int(c), t) for c, t in first_spikes if t <= cut]
        own_n = sum(1 for c, _ in kept if c in own)
        spur = len(kept) - own_n
        recall = own_n / a_size
        out[cut] = dict(recall=recall, spurious=spur, C1=bool(recall >= 0.8), C2=bool(spur < 0.5 * a_size))
    return out


# ------------------------------------------------------------------ screen D

def saturation_summary(columns, rows, cue_kinds):
    if "total" not in columns:
        return {"absent": True}
    id_col, total_col = columns.index("cue_id"), columns.index("total")
    groups = {}
    for row in rows:
        groups.setdefault(cue_kinds[int(row[id_col])], []).append(row[total_col])
    out = {}
    for kind, vals in groups.items():
        q1, med, q3 = np.percentile(np.asarray(vals, float), [25, 50, 75])
        out[kind] = dict(median=float(med), q1=float(q1), q3=float(q3), n=len(vals))
    return out


# ------------------------------------------------------------------ evidence and records

def verify_input(descriptor):
    evidence.verify_artifact(descriptor)
    return descriptor


def _script_sha256():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _source():
    frozen = {p: hashlib.sha256((record.REPO / p).read_bytes()).hexdigest() for p in FROZEN}
    return dict(git=record.git_state(), runtime=record.runtime(), script_sha256=_script_sha256(),
                frozen_sha256=frozen)


def _na(value):
    return "NA" if value is None else value


def record_screen(results_path, evidence_dir, screen, seed, arm, M, label, summary, obj, inputs, journal):
    name = f"{screen}-seed{seed}-{_na(arm)}-M{_na(M)}.json"
    desc = evidence.write_json_artifact(Path(evidence_dir) / name, obj)
    journal.append(dict(kind="artifact_written", name=name, descriptor=desc))
    rec = dict(kind="offline_screen", status="COMPLETE", screen=screen, seed=seed, arm=arm, M=M, label=label,
               summary=summary, artifact=desc, inputs=inputs, source=_source(), timestamp=record.now())
    record.append(rec, results_path)
    return rec


def record_invalid(results_path, screen, seed, reason, journal):
    rec = dict(kind="offline_screen", status="INVALID", screen=screen, seed=seed, reason=reason,
               source=_source(), timestamp=record.now())
    journal.append(dict(kind="offline_screen_invalid", screen=screen, seed=seed, reason=reason))
    record.append(rec, results_path)
    return rec


# ------------------------------------------------------------------ CLI inputs

def _combined(seed, arm, M):
    """Verified combined artifact and its descriptor, found through the seed's journal."""
    name = f"seed{seed}-{arm}-M{M}.json"
    records = evidence.verify_journal(R2B_EVIDENCE / f"seed{seed}.journal.jsonl")
    desc = next(r["descriptor"] for r in records if r.get("kind") == "artifact_written" and r["name"] == name)
    verify_input(desc)
    return json.loads(evidence.verify_artifact(desc).decode()), desc


def _unpack(z, name):
    off, flat = z[name + "_offsets"], z[name]
    return [flat[off[i]:off[i + 1]] for i in range(len(off) - 1)]


def _learned(combined):
    desc = verify_input(combined["raw"]["learned"])
    z = evidence.load_npz_artifact(desc)
    meta = json.loads(str(z["metadata_json"]))
    return dict(z, items=_unpack(z, "items"), A=_unpack(z, "A"), E=_unpack(z, "E"), R=_unpack(z, "R"),
                cfg=meta["cfg"]), desc


def _family_inputs(seed, items):
    from plant2.experiments import p2_e5_structured as e5
    gen = e5.FamilyGen(seed, 4000, 100, 60, 10)
    return gen.protos, (lambda k: (k + 1) % 10)


def _mean(values):
    vals = [v for v in values if v is not None]
    return float(np.mean(vals)) if vals else None


def _screen_a(seed, run):
    combined, cdesc = _combined(seed, "ORIGINAL", 1000)
    z, ldesc = _learned(combined)
    protos, family = _family_inputs(seed, z["items"])
    rows = gate_prescreen(z["items"], z["A"], z["E"], z["R"], protos, family)
    if any(r["p_size"] != 40 for r in rows):
        return None, None, None, "P_k does not have 40 lines for every episode"
    keys = [k for k in rows[0] if k.startswith("t_")]
    fields = ("V_size", "proto_predicted", "nonproto_predicted", "veto_precision")
    summary = dict(blocks={}, late_501_1000={})
    for key in keys:
        summary["blocks"][key] = [{f: _mean([r[key][f] for r in rows[lo:lo + 100]]) for f in fields}
                                  for lo in range(0, len(rows), 100)]
        summary["late_501_1000"][key] = {f: _mean([r[key][f] for r in rows[500:]]) for f in fields}
    return summary, dict(rows=rows), dict(combined=cdesc, learned=ldesc), None


def _half_cues(z, seed, M):
    from plant2.experiments import p2_e3_completion as e3
    cfg = z["cfg"]
    novel = [np.arange(cfg["a"], dtype=np.int64)] * cfg["n_novel"]
    stub = SimpleNamespace(c=cfg, seed=seed, items=z["items"], novel=novel)
    count = 2 * len(e1.test_sets(cfg, seed, M)[0]) + cfg["n_novel"]
    return [q for q in e3.build_cues(stub, M, [0] * count) if q["kind"] == "half"]


def _screen_b(seed, run):
    combined, cdesc = _combined(seed, "ORIGINAL", 1000)
    z, ldesc = _learned(combined)
    n = z["cfg"]["n"]
    inputs = dict(combined=cdesc, learned=ldesc)
    rebuilt = rebuild_forward_store(seed, z["A"], z["E"], n)
    if not integrity_gate(rebuilt, z["forward_keys"]):
        return None, None, None, "rebuilt forward keys differ from persisted"
    cues = _half_cues(z, seed, 1000)
    rows = [r for r in combined["index_cues"] if r["kind"] == "half"]
    if [int(q["index"]) for q in cues] != [r["index_0based"] for r in rows]:
        return None, None, None, "reproduced cue items differ from the artifact index_0based"
    stores = {K: rebuild_branch_store(seed, z["A"], z["E"], n, K) for K in (8, 4)}
    Ts = range(9, 15)
    per_cue = []
    for q in cues:
        own = np.zeros(n, bool)
        own[z["A"][int(q["index"])]] = True
        counts = {"point": cue_counts(rebuilt, n, q["cue"])}
        counts.update({f"K{K}": branch_max_counts(s, n, K, q["cue"]) for K, s in stores.items()})
        cue = {}
        for name, c in counts.items():
            cue[name] = {f"T{T}": dict(non_own=int(((c >= T) & ~own).sum()), own=int(((c >= T) & own).sum()))
                         for T in Ts}
            cue[name]["own_mean"] = float(c[own].mean())
        per_cue.append(dict(index=int(q["index"]), counts=cue))
    summary = {}
    for name in ("point", "K8", "K4"):
        summary[name] = {f"T{T}": {part: float(np.mean([c["counts"][name][f"T{T}"][part] for c in per_cue]))
                                   for part in ("non_own", "own")} for T in Ts}
        summary[name]["own_mean"] = float(np.mean([c["counts"][name]["own_mean"] for c in per_cue]))
    return summary, dict(per_cue=per_cue, integrity=True), inputs, None


def _screen_c(seed, arm, M, run):
    combined, cdesc = _combined(seed, arm, M)
    z, ldesc = _learned(combined)
    rows = [r for r in combined["index_cues"] if r["kind"] == "half"]
    own_t, spur_t, per_cue = [], [], []
    cut_acc = {c: [] for c in CUTS}
    for r in rows:
        own = z["A"][r["index_0based"]]
        split = latency_split(r["first_spikes100"], own)
        cuts = latency_cut(r["first_spikes100"], own, r["A_size"])
        per_cue.append(dict(index=r["index_0based"], split=split, cuts={str(c): v for c, v in cuts.items()}))
        ownset = set(int(c) for c in own)
        own_t += [t for c, t in r["first_spikes100"] if c in ownset]
        spur_t += [t for c, t in r["first_spikes100"] if c not in ownset]
        for c, v in cuts.items():
            cut_acc[c].append(v)
    pooled = {}
    for name, vals in (("own", own_t), ("spurious", spur_t)):
        p10, med, p90 = _pcts(vals)
        pooled[name] = dict(n=len(vals), p10=p10, median=med, p90=p90)
    cut_summary = {str(c): dict(recall=float(np.mean([v["recall"] for v in vs])),
                                spurious=float(np.mean([v["spurious"] for v in vs])),
                                C1=float(np.mean([v["C1"] for v in vs])), C2=float(np.mean([v["C2"] for v in vs])),
                                joint=float(np.mean([v["C1"] and v["C2"] for v in vs])))
                   for c, vs in cut_acc.items()}
    recorded = dict(C1=float(np.mean([r["recall50"] >= 0.8 for r in rows])),
                    C2=float(np.mean([r["spurious50"] < 0.5 * r["A_size"] for r in rows])),
                    joint=float(np.mean([r["own50"] >= 0.8 * r["A_size"] and r["spurious50"] < 0.5 * r["A_size"]
                                         for r in rows])))
    summary = dict(pooled=pooled, cuts=cut_summary, recorded_50ms=recorded, n_cues=len(rows))
    return summary, dict(per_cue=per_cue, summary=summary), dict(combined=cdesc, learned=ldesc), None


def _screen_d(seed, arm, M, run):
    combined, cdesc = _combined(seed, arm, M)
    z, ldesc = _learned(combined)
    table = combined["content"]["inherited"]
    kinds = [r["kind"] for r in combined["index_cues"]]
    if len(kinds) != len(table["rows"]):
        return None, None, None, "content rows and index cues differ in length"
    cfg = z["cfg"]
    summary = dict(saturation=saturation_summary(table["columns"], table["rows"], kinds),
                   feedback_density=int(z["feedback_keys"].size) / (cfg["m"] * cfg["n"]),
                   forward_density=combined["learning"].get("forward_density"))
    return summary, dict(summary=summary), dict(combined=cdesc, learned=ldesc), None


E6_DIR = record.REPO / "bench/results/p2e6"
E6_FILES = tuple((f"{c}-{a}", M) for c, a, M in (("F10", "baseline", 500), ("F10", "baseline", 1000),
                 ("F10", "candidate", 500), ("F10", "candidate", 1000),
                 ("independent", "baseline", 1000), ("independent", "candidate", 1000)))
E6_LABEL = "offline, descriptive, P2-E6 development seed 101 (exploratory)"
ABSENT = {"absent": True}


def _e6_descriptor(path):
    data = path.read_bytes()
    rel = str(path.relative_to(record.REPO))
    tracked = subprocess.run(["git", "-C", str(record.REPO), "ls-files", "--error-unmatch", rel],
                             capture_output=True).returncode == 0
    return dict(path=rel, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), committed_at_head=tracked), data


def _screen_d_e6(name, M):
    desc, data = _e6_descriptor(E6_DIR / f"e6-s101-v1-{name}-M{M}.json")
    d = json.loads(data.decode())
    table = d.get("content", {}).get("inherited")
    cues = d.get("index_cues")
    if table and cues and len(cues) == len(table["rows"]):
        saturation = saturation_summary(table["columns"], table["rows"], [r["kind"] for r in cues])
    else:
        saturation = dict(ABSENT)
    summary = dict(saturation=saturation, feedback_density=dict(ABSENT),
                   forward_density=d.get("learning", {}).get("forward_density", dict(ABSENT)))
    return summary, dict(summary=summary), dict(source=desc)


def run_e6(log=print):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    journal_path = EVIDENCE / "D-seed101.journal.jsonl"
    journal = evidence.Journal(journal_path, "D101")
    journal.append(dict(kind="run_started", screen="D", seed=101, runtime=record.runtime(),
                        script_sha256=_script_sha256()))
    manifest = evidence.Manifest()
    for name, M in E6_FILES:
        try:
            summary, obj, inputs = _screen_d_e6(name, M)
        except (OSError, KeyError, ValueError) as e:
            log(record_invalid(RESULTS, "D", 101, f"{name}/M{M}: input failure: {type(e).__name__}: {e}",
                               journal)["reason"])
            continue
        rec = record_screen(RESULTS, EVIDENCE, "D", 101, name, M, E6_LABEL, summary, obj, inputs, journal)
        manifest.add(Path(rec["artifact"]["path"]).name, rec["artifact"])
        log(f"D seed 101 {name} M{M} COMPLETE")
    ver = _verification(manifest, journal_path)
    record.append(dict(ver, screen="D", seed=101, timestamp=record.now()), RESULTS)
    journal.append(ver)
    return ver["passed"]


# ------------------------------------------------------------------ screen E

E7_DIR = record.REPO / "bench/results/p2e7"
E7_RESULTS = record.REPO / "bench/results/p2e7.jsonl"
E7_ATTEMPT = "seed121-1792699741870086415-c573e46d"
E7_ARMS = ("baseline", "candidate", "random_drop", "history_drop", "gate_off", "no_conservation",
           "label_oracle", "assigned_A_teacher")
E_LABEL = "offline, descriptive, development seed 121"


def responders_from_raster(raster_ticks, raster_cells, cue_index, cue_onset, cue_kind, window=50):
    ticks = np.asarray(raster_ticks, np.int64)
    out = {}
    for idx, onset, kind in zip(cue_index, cue_onset, cue_kind):
        if str(kind) != "half":
            continue
        lo, hi = np.searchsorted(ticks, [int(onset), int(onset) + window])
        cells = [np.asarray(raster_cells[i], np.int64) for i in range(lo, hi)]
        out[int(idx)] = np.unique(np.concatenate(cells)) if cells else np.empty(0, np.int64)
    return out


def spurious_classes(rows, A, responders_by_cue, first_engagement, F=10):
    plateau_items = {}
    for k, cells in enumerate(A):
        for c in np.asarray(cells).tolist():
            plateau_items.setdefault(c, []).append(k)
    fam = lambda k: (k + 1) % F
    first = lambda f: first_engagement.get(f)
    early = lambda k: first(fam(k)) is None or k < first(fam(k))
    per_cue = []
    for r in rows:
        if r["kind"] != "half":
            continue
        q = int(r["index_0based"])
        resp = np.asarray(responders_by_cue[q], np.int64)
        own = np.intersect1d(resp, np.asarray(A[q], np.int64))
        if len(resp) != r["own50"] + r["spurious50"] or len(own) != r["own50"]:
            raise ValueError(f"cue {q}: responders do not match own50 + spurious50")
        counts = dict(same_family_early=0, same_family_late=0, other_family_only=0)
        for c in np.setdiff1d(resp, own).tolist():
            same = [k for k in plateau_items.get(c, []) if fam(k) == fam(q)]
            counts["other_family_only" if not same else
                   "same_family_early" if any(early(k) for k in same) else "same_family_late"] += 1
        per_cue.append(dict(cue_index=q, spurious=int(len(resp) - len(own)), **counts))
    mean = lambda key: float(np.mean([c[key] for c in per_cue])) if per_cue else None
    members = [[k for k in range(len(A)) if fam(k) == f] for f in range(F)]
    chance = [sum(early(k) for k in m) / len(m) for m in members if m]
    return dict(cues=len(per_cue), spurious_per_cue=mean("spurious"),
                same_family_early_per_cue=mean("same_family_early"),
                same_family_late_per_cue=mean("same_family_late"),
                other_family_only_per_cue=mean("other_family_only"),
                items_before_engagement=int(sum(early(k) for k in range(len(A)))),
                early_chance=float(np.mean(chance)), per_cue=per_cue)


def _engagement(arm):
    for line in E7_RESULTS.read_text().splitlines():
        r = json.loads(line)
        if (r.get("kind") == "structural_check" and r.get("arm") == arm and r.get("condition") == "F10"
                and r.get("attempt") == E7_ATTEMPT):
            return {int(f): v for f, v in r["gate"]["first_engagement_by_family"].items()}
    return {f: None for f in range(10)}


def _screen_e(arm):
    path = E7_DIR / f"{E7_ATTEMPT}-F10-{arm}-M1000.json"
    pdesc = dict(path=str(path.relative_to(record.REPO)), bytes=path.stat().st_size,
                 sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    d = json.loads(path.read_bytes().decode())
    raster = evidence.load_npz_artifact(verify_input(d["raw"]))
    state_desc = d["state"]
    state = evidence.load_npz_artifact(verify_input(state_desc))
    A = _unpack(state, "A")
    ragged = _unpack(raster, "raster_cells")
    resp = responders_from_raster(raster["raster_ticks"], ragged, raster["cue_index"].tolist(),
                                  raster["cue_onset"].tolist(), raster["cue_kind"].tolist())
    first = _engagement(arm)
    out = spurious_classes(d["index_cues"], A, resp, first)
    summary = {k: v for k, v in out.items() if k != "per_cue"}
    summary["first_engagement"] = {str(f): v for f, v in sorted(first.items())}
    return summary, dict(summary=summary, per_cue=out["per_cue"]), dict(portable=pdesc, raster=d["raw"], state=state_desc)


def run_e(log=print):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    journal_path = EVIDENCE / "E-seed121.journal.jsonl"
    journal = evidence.Journal(journal_path, "E121")
    journal.append(dict(kind="run_started", screen="E", seed=121, runtime=record.runtime(),
                        script_sha256=_script_sha256()))
    manifest = evidence.Manifest()
    for arm in E7_ARMS:
        try:
            summary, obj, inputs = _screen_e(arm)
        except (evidence.EvidenceError, OSError, KeyError, ValueError) as e:
            log(record_invalid(RESULTS, "E", 121, f"{arm}/M1000: input failure: {type(e).__name__}: {e}",
                               journal)["reason"])
            continue
        rec = record_screen(RESULTS, EVIDENCE, "E", 121, arm, 1000, E_LABEL, summary, obj, inputs, journal)
        manifest.add(Path(rec["artifact"]["path"]).name, rec["artifact"])
        log(f"E seed 121 {arm} M1000 COMPLETE")
    ver = _verification(manifest, journal_path)
    record.append(dict(ver, screen="E", seed=121, timestamp=record.now()), RESULTS)
    journal.append(ver)
    return ver["passed"]


def _verification(manifest, journal_path):
    failures = []
    try:
        manifest.verify_all()
    except evidence.EvidenceError as e:
        failures.append(str(e))
    try:
        evidence.verify_journal(journal_path)
        journal_ok = True
    except (evidence.EvidenceError, OSError) as e:
        journal_ok, failures = False, failures + [f"journal: {e}"]
    return dict(kind="evidence_verification", artifacts_verified=len(manifest.entries), failures=failures,
                journal_ok=journal_ok, passed=not failures and journal_ok)


def run(screen, seeds, log=print):
    os.environ.setdefault("BRAINSIM_CACHE", str(CACHE_ROOT))
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    ok = True
    for seed in seeds:
        journal_path = EVIDENCE / f"{screen}-seed{seed}.journal.jsonl"
        journal = evidence.Journal(journal_path, f"{screen}{seed}")
        journal.append(dict(kind="run_started", screen=screen, seed=seed, runtime=record.runtime(),
                            script_sha256=_script_sha256()))
        manifest = evidence.Manifest()
        jobs = ([("ORIGINAL", 1000)] if screen in "AB" else [(a, M) for a in ARMS for M in LOADS])
        for arm, M in jobs:
            try:
                if screen == "A":
                    out = _screen_a(seed, run)
                elif screen == "B":
                    out = _screen_b(seed, run)
                elif screen == "C":
                    out = _screen_c(seed, arm, M, run)
                else:
                    out = _screen_d(seed, arm, M, run)
                summary, obj, inputs, reason = out
            except (evidence.EvidenceError, OSError, StopIteration, KeyError) as e:
                summary, obj, inputs, reason = None, None, None, f"input failure: {type(e).__name__}: {e}"
            if reason:
                ok = False
                log(record_invalid(RESULTS, screen, seed, f"{arm}/M{M}: {reason}", journal)["reason"])
                continue
            rec = record_screen(RESULTS, EVIDENCE, screen, seed, arm, M, LABELS[screen], summary, obj, inputs, journal)
            manifest.add(Path(rec["artifact"]["path"]).name, rec["artifact"])
            log(f"{screen} seed {seed} {arm} M{M} COMPLETE")
        ver = _verification(manifest, journal_path)
        record.append(dict(ver, screen=screen, seed=seed, timestamp=record.now()), RESULTS)
        journal.append(ver)
        ok = ok and ver["passed"]
    return ok


def summary():
    rows = [json.loads(x) for x in RESULTS.read_text().splitlines() if x.strip()] if RESULTS.exists() else []
    shown = [dict(screen=r["screen"], seed=r["seed"], arm=r.get("arm"), M=r.get("M"), status=r["status"],
                  summary=r.get("summary"), reason=r.get("reason")) for r in rows if r["kind"] == "offline_screen"]
    checks = [r["passed"] for r in rows if r["kind"] == "evidence_verification"]
    return dict(records=shown, verifications_passed=sum(checks), verifications_failed=len(checks) - sum(checks))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    runner = commands.add_parser("run")
    runner.add_argument("--screen", required=True, choices=("A", "B", "C", "D", "E"))
    runner.add_argument("--seed", type=int, action="append", choices=SEEDS)
    commands.add_parser("summary")
    args = parser.parse_args(argv)
    if args.command == "summary":
        print(json.dumps(summary(), sort_keys=True))
        return 0
    log = lambda x: print(f"[{record.now()}] {x}", flush=True)
    if args.screen == "E":
        return 0 if run_e(log=log) else 1
    ok = run(args.screen, args.seed or list(SEEDS), log=log)
    if args.screen == "D" and not args.seed:
        ok = run_e6(log=log) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
