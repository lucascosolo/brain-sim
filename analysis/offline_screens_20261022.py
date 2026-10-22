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


def spurious_classes(rows, A, responders_by_cue, first_engagement, F=10, return_cells=False):
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
        cells = dict(early_cells=[], late_cells=[], other_cells=[])
        for c in np.setdiff1d(resp, own).tolist():
            same = [k for k in plateau_items.get(c, []) if fam(k) == fam(q)]
            cls = "other_family_only" if not same else "same_family_early" if any(early(k) for k in same) else "same_family_late"
            counts[cls] += 1
            cells[{"other_family_only": "other_cells", "same_family_early": "early_cells",
                   "same_family_late": "late_cells"}[cls]].append(int(c))
        row = dict(cue_index=q, spurious=int(len(resp) - len(own)), **counts)
        per_cue.append(dict(row, **cells) if return_cells else row)
    mean = lambda key: float(np.mean([c[key] for c in per_cue])) if per_cue else None
    members = [[k for k in range(len(A)) if fam(k) == f] for f in range(F)]
    chance = [sum(early(k) for k in m) / len(m) for m in members if m]
    return dict(cues=len(per_cue), spurious_per_cue=mean("spurious"),
                same_family_early_per_cue=mean("same_family_early"),
                same_family_late_per_cue=mean("same_family_late"),
                other_family_only_per_cue=mean("other_family_only"),
                items_before_engagement=int(sum(early(k) for k in range(len(A)))),
                early_chance=float(np.mean(chance)), per_cue=per_cue)



# ------------------------------------------------------------------ screens F and E-prime

F_LABEL = "offline, development seed 121; proxy (counterfactual on the binary trajectory)"
EP_LABEL = "offline, development seed 121"
RULES = ("binary", "graded", "surplus_only")
BLOCK = 100


def rebuild_feedback_csr(R_seq, E_seq, upto, m, n):
    W = np.zeros((n, m), bool)
    for R, E in zip(R_seq[:upto], E_seq[:upto]):
        W[np.ix_(np.asarray(R, np.int64), np.asarray(E, np.int64))] = True
    return _csr(W) + (np.flatnonzero(W).astype(np.int64),)


def _csr(W):
    r, c = np.nonzero(W)
    return np.concatenate(([0], np.cumsum(np.bincount(r, minlength=W.shape[0])))).astype(np.int64), c.astype(np.int64)


def lockstep_rec(raster, indptr, post, m, J=2.8, g=0.3, tau_m=20.0, v_rest=-70.0, v_reset=-65.0, v_th=-50.0,
                 t_ref=2, n_ticks=75):
    f32 = np.float32
    gJ = f32(np.float64(g) * np.float64(J))
    J32 = f32(J)
    decay = f32(np.exp(-1.0 / tau_m))
    v_c = f32(v_rest * (1.0 - decay))
    rest = f32(v_rest)
    v = np.full(m, v_rest, f32)
    t_last = np.full(m, -10_000, np.int64)
    ring = np.zeros((3, m), f32)
    dmax = np.zeros(m, f32)
    fired = np.zeros(m, bool)
    for t in range(n_ticks):
        slot = ring[t % 3]
        np.multiply(v, decay, out=v)
        v += v_c
        v += slot
        slot[:] = 0.0
        np.maximum(dmax, v - rest, out=dmax)
        hit = (v >= v_th) & (t - t_last > t_ref)
        if hit.any():
            v[hit] = v_reset
            t_last[hit] = t
            fired |= hit
        s = raster.get(t)
        if s is not None and len(s):
            s = np.asarray(s, np.int64)
            lo, cnt = indptr[s], indptr[s + 1] - indptr[s]
            n_ev = int(cnt.sum())
            if n_ev:
                idx = np.repeat(lo, cnt) + (np.arange(n_ev) - np.repeat(np.cumsum(cnt) - cnt, cnt))
                counts = np.bincount(post[idx], minlength=m)
                nxt = ring[(t + 1) % 3]
                for kk in range(1, int(counts.max()) + 1):
                    nxt += J32 * (counts >= kk).astype(f32)
            ring[(t + 2) % 3] -= f32(gJ * s.size)
    return np.flatnonzero(fired).astype(np.int64), dmax.astype(np.float64)


def water_fill(w, budget):
    w = np.asarray(w, float)
    p = np.zeros(w.size)
    pos = np.flatnonzero(w > 0)
    if budget <= 0 or not pos.size:
        return p, False
    if pos.size <= budget:
        p[pos] = 1.0
        return p, bool(pos.size < budget)
    order = pos[np.argsort(-w[pos], kind="stable")]
    sw = w[order]
    tail = np.concatenate((np.cumsum(sw[::-1])[::-1], [0.0]))
    for c in range(order.size):
        lam = (budget - c) / tail[c]
        if lam * sw[c] <= 1.0:
            p[order[c:]] = lam * sw[c:]
            p[order[:c]] = 1.0
            return p, False
    p[order] = 1.0
    return p, False


def surplus_only_p(E, G, d):
    E = np.asarray(E, np.int64)
    in_G = np.isin(E, np.asarray(G, np.int64))
    surplus = 0.5 * int(in_G.sum())
    p = np.where(in_G, 0.0, 0.5)
    w = np.where(in_G, 0.0, 1.0 - np.clip(np.asarray(d, float) / 20.0, 0.0, 1.0))
    q, _ = water_fill(w, 2.0 * surplus)
    extra = 0.5 * q
    return p + extra, float(surplus - extra.sum())


def counterfactual_p(E, G, d, rule):
    E = np.asarray(E, np.int64)
    if rule == "surplus_only":
        return surplus_only_p(E, G, d)[0]
    if rule not in ("binary", "graded"):
        raise ValueError(f"unknown rule {rule!r}")
    in_G = np.isin(E, np.asarray(G, np.int64))
    if rule == "binary":
        n_free = int((~in_G).sum())
        if n_free == 0:
            return np.zeros(E.size)
        return np.where(in_G, 0.0, min(1.0, 0.5 * E.size / n_free))
    w = np.where(in_G, 0.0, 1.0 - np.clip(np.asarray(d, float) / 20.0, 0.0, 1.0))
    return water_fill(w, 0.5 * E.size)[0]


def auc(positives, negatives):
    pos, neg = np.asarray(positives, float), np.sort(np.asarray(negatives, float))
    if not pos.size or not neg.size:
        return None
    less, leq = np.searchsorted(neg, pos, "left"), np.searchsorted(neg, pos, "right")
    return float((less + 0.5 * (leq - less)).sum() / (pos.size * neg.size))


def expected_flips(E, P, p):
    in_P = np.isin(np.asarray(E, np.int64), np.asarray(P, np.int64))
    p = np.asarray(p, float)
    return float(p[in_P].sum()), float(p[~in_P].sum())


def _gate_col(gate_log, key):
    if isinstance(gate_log, dict):
        return list(gate_log[key])
    return [row[key] for row in gate_log]


def _raster_dict(ticks, cells):
    ticks, cells = np.asarray(ticks, np.int64), np.asarray(cells, np.int64)
    return {int(t): cells[ticks == t] for t in np.unique(ticks)}


def _window_summary(rows, lo, hi):
    w = rows[lo:hi]
    pos = np.concatenate([r["pos"] for r in w]) if w else np.empty(0)
    neg = np.concatenate([r["neg"] for r in w]) if w else np.empty(0)
    out = dict(episodes=len(w), auc=auc(pos, neg), n_missed_proto=int(pos.size), n_unpredicted_nonproto=int(neg.size),
               missed_proto_ge10=_fraction(int((pos >= 10).sum()), pos.size), rules={})
    for rule in RULES:
        out["rules"][rule] = dict(proto=float(np.mean([r[rule]["proto"] for r in w])),
                                  nonproto=float(np.mean([r[rule]["nonproto"] for r in w])),
                                  tv_mean_abs_dev_from_half=float(np.mean([r[rule]["tv"] for r in w])),
                                  any_p_below_049=float(np.mean([r[rule]["any_below"] for r in w])))
    base = out["rules"]["binary"]["proto"]
    out["graded_over_binary"] = _fraction(out["rules"]["graded"]["proto"], base)
    out["surplus_over_binary"] = _fraction(out["rules"]["surplus_only"]["proto"], base)
    out["graded_capped_episodes"] = int(sum(r["graded_capped"] for r in w))
    out["surplus_unspent_episodes"] = int(sum(r["surplus_unspent"] > 0 for r in w))
    return out


def screen_f(items, E, R, A, enc_tick, enc_cell, feedback_keys, gate_log, protos, family, m, n):
    G_size, V_size = _gate_col(gate_log, "G_size"), _gate_col(gate_log, "V_size")
    W = np.zeros((n, m), bool)
    rows = []
    for k in range(len(items)):
        indptr, post = _csr(W)
        spikes, dmax = lockstep_rec(_raster_dict(enc_tick[k], enc_cell[k]), indptr, post, m)
        Ek = np.asarray(E[k], np.int64)
        V = np.intersect1d(spikes, Ek)
        if len(spikes) != G_size[k] or len(V) != V_size[k]:
            raise ValueError(f"lockstep gate fails at episode {k}: |G| {len(spikes)} vs {G_size[k]}, "
                             f"|G and E| {len(V)} vs {V_size[k]}")
        P = np.intersect1d(items[k], protos[family(k)])
        if P.size != 40:
            raise ValueError(f"P_k has {P.size} lines at episode {k}")
        d = dmax[Ek]
        in_G, in_P = np.isin(Ek, V), np.isin(Ek, P)
        row = dict(pos=d[in_P & ~in_G], neg=d[~in_P & ~in_G])
        for rule in RULES:
            p = counterfactual_p(Ek, V, d, rule)
            proto, nonproto = expected_flips(Ek, P, p)
            row[rule] = dict(proto=proto, nonproto=nonproto, tv=float(np.mean(np.abs(p - 0.5))) if p.size else 0.0,
                             any_below=bool((p < 0.49).any()))
        row["graded_capped"] = bool(water_fill(np.where(in_G, 0.0, 1.0 - np.clip(d / 20.0, 0, 1)), 0.5 * Ek.size)[1])
        row["surplus_unspent"] = surplus_only_p(Ek, V, d)[1]
        rows.append(row)
        W[np.ix_(np.asarray(R[k], np.int64), Ek)] = True
    if not np.array_equal(np.flatnonzero(W).astype(np.int64), np.asarray(feedback_keys, np.int64)):
        raise ValueError("rebuilt S_1000 keys differ from persisted feedback_keys")
    n_ep = len(rows)
    out = dict(blocks=[_window_summary(rows, lo, lo + BLOCK) for lo in range(0, n_ep, BLOCK)],
               w501_1000=_window_summary(rows, 500, n_ep), w1_300=_window_summary(rows, 0, 300),
               all=_window_summary(rows, 0, n_ep),
               tv_definition="mean over eligible lines of |p - 0.5|, then mean over episodes")
    proto_pred = _gate_col(gate_log, "proto_predicted")
    out["b017_gate_log_proto_predicted_101_500"] = dict(mean=float(np.mean(proto_pred[100:500])), reference=0.595)
    per_episode = [dict(episode=k, n_missed_proto=int(r["pos"].size), n_unpredicted_nonproto=int(r["neg"].size),
                        **{f"proto_{rule}": r[rule]["proto"] for rule in RULES}) for k, r in enumerate(rows)]
    return out, per_episode


def p2e8_kill_reading(auc_501_1000, graded_over_binary_501_1000, ramp_graded_over_binary_1_300,
                      eprime_low_coverage_share):
    fired, undecided = [], []
    if auc_501_1000 is None or auc_501_1000 < 0.70:
        fired.append("auc_501_1000 < 0.70")
    if graded_over_binary_501_1000 is None or graded_over_binary_501_1000 > 0.6:
        fired.append("graded_over_binary_501_1000 > 0.6")
    if ramp_graded_over_binary_1_300 is not None and ramp_graded_over_binary_1_300 > 0.85:
        if eprime_low_coverage_share is None:
            undecided.append("ramp ratio > 0.85 and E-prime low-coverage share > 0.5 (E-prime not yet run)")
        elif eprime_low_coverage_share > 0.5:
            fired.append("ramp ratio > 0.85 and E-prime low-coverage share > 0.5")
    return dict(auc_501_1000=auc_501_1000, graded_over_binary_501_1000=graded_over_binary_501_1000,
                ramp_graded_over_binary_1_300=ramp_graded_over_binary_1_300,
                eprime_low_coverage_share=eprime_low_coverage_share, killed=bool(fired),
                rules_fired=fired, undecided=undecided)


EP_BINS = ("<0.25", "0.25-0.75", ">=0.75")


def _ep_bin(x):
    return EP_BINS[0] if x < 0.25 else EP_BINS[1] if x < 0.75 else EP_BINS[2]


def eprime_bins(per_cue_classes, cell_items, family_of, proto_predicted_by_episode, first_engagement):
    counts, weights, n_late = dict.fromkeys(EP_BINS, 0), dict.fromkeys(EP_BINS, 0), 0
    for row in per_cue_classes:
        f = family_of(int(row["cue_index"]))
        for c in row["late_cells"]:
            same = [k for k in cell_items[c] if family_of(k) == f]
            b = _ep_bin(min(proto_predicted_by_episode[k] for k in same))
            counts[b] += 1
            weights[b] += len(same)
            n_late += 1
    n_cues, wsum = len(per_cue_classes), sum(weights.values())
    return dict(counts_per_cue={b: (counts[b] / n_cues if n_cues else None) for b in EP_BINS},
                shares={b: _fraction(counts[b], n_late) for b in EP_BINS},
                items_weighted_shares={b: _fraction(weights[b], wsum) for b in EP_BINS}, n_late=n_late)


def _state_inputs(file_stem):
    path = E7_DIR / f"{E7_ATTEMPT}-{file_stem}-M1000.json"
    pdesc = dict(path=str(path.relative_to(record.REPO)), bytes=path.stat().st_size,
                 sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    d = json.loads(path.read_bytes().decode())
    state_desc = d["state"]
    z = evidence.load_npz_artifact(verify_input(state_desc))
    meta = json.loads(str(z["metadata_json"]))
    return d, z, meta, dict(portable=pdesc, state=state_desc)


def _screen_f(arm, stem):
    from plant2.experiments import p2_e5_structured as e5
    d, z, meta, inputs = _state_inputs(stem)
    cfg = meta.get("cfg", {})
    m, n = cfg.get("m", 4000), cfg.get("n", 4000)
    protos = e5.FamilyGen(121, 4000, 100, 60, 10).protos
    items, E, R, A = (_unpack(z, k) for k in ("items", "E", "R", "A"))
    obj, per_episode = screen_f(items, E, R, A, _unpack(z, "enc_tick"), _unpack(z, "enc_cell"), z["feedback_keys"],
                                meta["gate_log"], protos, lambda k: (k + 1) % 10, m, n)
    summary = dict(w501_1000=obj["w501_1000"], w1_300=obj["w1_300"], all=obj["all"],
                   b017=obj["b017_gate_log_proto_predicted_101_500"], blocks=obj["blocks"])
    return summary, dict(obj, per_episode=per_episode), inputs


def _latest_summary(screen, arm):
    if not RESULTS.exists():
        return None
    found = None
    for line in RESULTS.read_text().splitlines():
        r = json.loads(line)
        if r.get("kind") == "offline_screen" and r.get("screen") == screen and r.get("arm") == arm \
                and r.get("status") == "COMPLETE":
            found = r["summary"]
    return found


def _run_jobs(screen, label, jobs, log):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    journal_path = EVIDENCE / f"{screen}-seed121.journal.jsonl"
    journal = evidence.Journal(journal_path, f"{screen}121")
    journal.append(dict(kind="run_started", screen=screen, seed=121, runtime=record.runtime(),
                        script_sha256=_script_sha256()))
    manifest = evidence.Manifest()
    for arm, fn in jobs:
        try:
            summary, obj, inputs = fn()
        except (evidence.EvidenceError, OSError, KeyError, ValueError) as e:
            log(record_invalid(RESULTS, screen, 121, f"{arm}/M1000: {type(e).__name__}: {e}", journal)["reason"])
            continue
        rec = record_screen(RESULTS, EVIDENCE, screen, 121, arm, 1000, label, summary, obj, inputs, journal)
        manifest.add(Path(rec["artifact"]["path"]).name, rec["artifact"])
        log(f"{screen} seed 121 {arm} M1000 COMPLETE")
    ver = _verification(manifest, journal_path)
    record.append(dict(ver, screen=screen, seed=121, timestamp=record.now()), RESULTS)
    journal.append(ver)
    return ver["passed"]


def run_f(log=print):
    results = {}

    def job(arm, stem):
        def go():
            summary, obj, inputs = _screen_f(arm, stem)
            results[arm] = summary
            if arm == "candidate" and "gate_off" in results:
                eprime = _latest_summary("Eprime", "candidate")
                share = eprime["shares"]["<0.25"] if eprime else None
                summary["p2e8_kill_reading"] = p2e8_kill_reading(
                    summary["w501_1000"]["auc"], summary["w501_1000"]["graded_over_binary"],
                    results["gate_off"]["w1_300"]["graded_over_binary"], share)
            return summary, obj, inputs
        return go

    jobs = [("gate_off", job("gate_off", "F10-gate_off")), ("candidate", job("candidate", "F10-candidate")),
            ("independent", job("independent", "independent-candidate"))]
    return _run_jobs("F", F_LABEL, jobs, log)


def _screen_eprime():
    e = _e7_load("candidate")
    A = e["A"]
    cell_items = {}
    for k, cells in enumerate(A):
        for c in np.asarray(cells).tolist():
            cell_items.setdefault(c, []).append(k)
    out = spurious_classes(e["d"]["index_cues"], A, e["resp"], e["first"], return_cells=True)
    gate = e["meta"]["gate_log"]
    pp = dict(enumerate(_gate_col(gate, "proto_predicted")))
    p = _gate_col(gate, "p")
    bins = eprime_bins(out["per_cue"], cell_items, lambda k: (k + 1) % 10, pp, e["first"])
    eps = sorted({k for r in out["per_cue"] for c in r["late_cells"] for k in cell_items[c]
                  if (k + 1) % 10 == (r["cue_index"] + 1) % 10})
    pe = np.asarray([p[k] for k in eps], float)
    p_dist = dict(episodes=len(eps), p10=float(np.percentile(pe, 10)), median=float(np.median(pe)),
                  p90=float(np.percentile(pe, 90))) if eps else dict(episodes=0)
    screen_e = _latest_summary("E", "candidate")
    e_late = (screen_e["same_family_late_per_cue"] * screen_e["cues"]) if screen_e else None
    summary = dict(bins, p_distribution_on_late_item_episodes=p_dist, late_count_recomputed=bins["n_late"],
                   late_count_from_screen_e_record=None if e_late is None else round(e_late),
                   late_count_matches=None if e_late is None else bool(round(e_late) == bins["n_late"]))
    return summary, dict(summary=summary, per_cue=[{k: v for k, v in r.items()} for r in out["per_cue"]]), e["inputs"]


def run_eprime(log=print):
    return _run_jobs("Eprime", EP_LABEL, [("candidate", _screen_eprime)], log)


def _engagement(arm):
    for line in E7_RESULTS.read_text().splitlines():
        r = json.loads(line)
        if (r.get("kind") == "structural_check" and r.get("arm") == arm and r.get("condition") == "F10"
                and r.get("attempt") == E7_ATTEMPT):
            return {int(f): v for f, v in r["gate"]["first_engagement_by_family"].items()}
    return {f: None for f in range(10)}


def _e7_load(arm):
    path = E7_DIR / f"{E7_ATTEMPT}-F10-{arm}-M1000.json"
    pdesc = dict(path=str(path.relative_to(record.REPO)), bytes=path.stat().st_size,
                 sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    d = json.loads(path.read_bytes().decode())
    raster = evidence.load_npz_artifact(verify_input(d["raw"]))
    state_desc = d["state"]
    state = evidence.load_npz_artifact(verify_input(state_desc))
    ragged = _unpack(raster, "raster_cells")
    resp = responders_from_raster(raster["raster_ticks"], ragged, raster["cue_index"].tolist(),
                                  raster["cue_onset"].tolist(), raster["cue_kind"].tolist())
    return dict(d=d, A=_unpack(state, "A"), resp=resp, first=_engagement(arm),
                meta=json.loads(str(state["metadata_json"])),
                inputs=dict(portable=pdesc, raster=d["raw"], state=state_desc))


def _screen_e(arm):
    e = _e7_load(arm)
    out = spurious_classes(e["d"]["index_cues"], e["A"], e["resp"], e["first"])
    summary = {k: v for k, v in out.items() if k != "per_cue"}
    summary["first_engagement"] = {str(f): v for f, v in sorted(e["first"].items())}
    return summary, dict(summary=summary, per_cue=out["per_cue"]), e["inputs"]


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
    runner.add_argument("--screen", required=True, choices=("A", "B", "C", "D", "E", "F", "Eprime"))
    runner.add_argument("--seed", type=int, action="append", choices=SEEDS)
    commands.add_parser("summary")
    args = parser.parse_args(argv)
    if args.command == "summary":
        print(json.dumps(summary(), sort_keys=True))
        return 0
    log = lambda x: print(f"[{record.now()}] {x}", flush=True)
    if args.screen in ("E", "F", "Eprime"):
        return 0 if {"E": run_e, "F": run_f, "Eprime": run_eprime}[args.screen](log=log) else 1
    ok = run(args.screen, args.seed or list(SEEDS), log=log)
    if args.screen == "D" and not args.seed:
        ok = run_e6(log=log) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
