"""P2-R3: episode-clustered reconstruction store with line-local branches, an exact reported replay
(docs/plant2/P2-R3-branch-reconstruction-replay.md).

Zero-seed replay on the persisted P2-E7 seed-121 evidence. Nothing here is a capability, a gate or
a credit. Library functions are pure and tested on synthetic inputs; the CLI (`step0`, `run`,
`summary`) reads verified artifacts and appends to bench/results/p2r3.jsonl.
"""
import argparse
import hashlib
import json
import math
import time
from pathlib import Path

import numpy as np

from analysis import p2r1_replay as r1
from plant2 import evidence, record
from plant2.btsp import BinarySynapses
from plant2.experiments import p2_e1_btsp as e1
from plant2.experiments import p2_e3_completion as e3
from plant2.readout import replay

f32 = np.float32
ATTEMPT = "seed121-1792699741870086415-c573e46d"
SEED = 121
SCRAMBLE_STREAM = 37
K_RULE, K_DOSE = 32, 8
J_FB, G_INH = 2.80, 0.30
WINDOW, SHORT = 75, 50
RESULTS = record.REPO / "bench/results/p2r3.jsonl"
EVIDENCE = record.REPO / "bench/results/p2r3"
JOURNAL = EVIDENCE / "seed121.journal.jsonl"
E7_DIR = record.REPO / "bench/results/p2e7"
FROZEN = ("plant2/readout.py", "plant2/btsp.py", "plant2/evidence.py", "plant2/record.py",
          "plant2/experiments/p2_e1_btsp.py", "plant2/experiments/p2_e3_completion.py")
# (condition, arm, role, loads)
SUBSTRATES = (("F10", "gate_off", "deployable; exact", (500, 1000)),
              ("F10", "label_oracle", "clean-index diagnostic; exact; never credited", (500, 1000)),
              ("F10", "candidate", "stacking diagnostic; reported only", (1000,)),
              ("independent", "candidate", "non-regression; exact", (500, 1000)),
              ("mixed", "baseline", "non-regression on the independent subset; exact", (1000,)))
STEP0_SUBSTRATES = (("F10", "gate_off"), ("F10", "label_oracle"))
STORES = (("inherited", "R"), ("assigned_A", "A"))
ARMS = (("K1", "episode", 1, "R"), ("K32", "episode", K_RULE, "R"), ("scramble", "scramble", K_RULE, "R"),
        ("assigned_A_K32", "episode", K_RULE, "A"), ("K8", "episode", K_DOSE, "R"),
        ("unbounded", "unbounded", K_RULE, "R"))


# ------------------------------------------------------------------ store

class BranchStore:
    """Synapses as sorted keys ((line * B + branch) * n + writer); a scramble store keeps duplicates."""

    def __init__(self, keys, counts, m, n, B):
        self.keys, self.counts, self.m, self.n, self.B = keys, counts, m, n, B

    def _slice(self, j, b):
        if not 0 <= b < self.B:
            return self.keys[:0]
        base = (j * self.B + b) * self.n
        lo, hi = np.searchsorted(self.keys, [base, base + self.n])
        return self.keys[lo:hi]

    def writers(self, j, b):
        return np.unique(self._slice(j, b) % self.n)

    def multiset(self, j):
        base = j * self.B * self.n
        lo, hi = np.searchsorted(self.keys, [base, base + self.B * self.n])
        return np.sort(self.keys[lo:hi] % self.n)

    def csr(self):
        """(indptr by memory cell, line, branch) with (line, branch) sorted within each cell."""
        jb, w = self.keys // self.n, self.keys % self.n
        order = np.lexsort((jb, w))
        indptr = np.searchsorted(w[order], np.arange(self.n + 1))
        return indptr, (jb[order] // self.B), (jb[order] % self.B)

    def compact(self):
        """CSR whose posts index only the (line, branch) pairs that have writers, plus each pair's line."""
        jb, w = self.keys // self.n, self.keys % self.n
        uniq, inv = np.unique(jb, return_inverse=True)
        order = np.argsort(w, kind="stable")
        indptr = np.searchsorted(w[order], np.arange(self.n + 1))
        return indptr, inv[order].astype(np.int64), (uniq // self.B).astype(np.int64)


def build_branch_store(E_seq, R_seq, K, m, n, mode="episode", scramble_seed=SEED):
    if mode not in ("episode", "scramble", "unbounded"):
        raise ValueError(f"unknown mode {mode!r}")
    E = [np.asarray(e, np.int64) for e in E_seq]
    R = [np.asarray(r, np.int64) for r in R_seq]
    lines = np.concatenate(E) if E else np.empty(0, np.int64)
    lens = np.asarray([e.size for e in E], np.int64)
    counts = np.bincount(lines, minlength=m).astype(np.int64)
    order = np.argsort(lines, kind="stable")           # episode order is kept within a line
    sorted_lines = lines[order]
    rank = np.empty(lines.size, np.int64)
    rank[order] = np.arange(lines.size) - np.searchsorted(sorted_lines, sorted_lines, side="left")
    if mode == "unbounded":
        B, branch = max(1, int(counts.max()) if counts.size else 1), rank
    else:
        B, branch = K, rank % K
    jb = lines * B + branch
    ends = np.cumsum(lens)
    parts = [(jb[e - c:e][:, None] * n + r[None, :]).ravel() for e, c, r in zip(ends, lens, R)]
    allkeys = np.concatenate(parts) if parts else np.empty(0, np.int64)
    keys, first = np.unique(allkeys, return_index=True)
    if mode == "scramble":
        line = (keys // n) // B
        o = np.lexsort((first, line))                   # write-event order within each line
        line, w = line[o], (keys % n)[o]
        bounds = np.searchsorted(line, np.arange(m + 1))
        new = np.empty(keys.size, np.int64)
        for j in range(m):
            lo, hi = bounds[j], bounds[j + 1]
            if hi > lo:
                b = e1.stream(scramble_seed, SCRAMBLE_STREAM, j).integers(0, K, size=hi - lo)
                new[lo:hi] = (j * B + b) * n + w[lo:hi]
        keys = np.sort(new)
    return BranchStore(keys, counts, m, n, B)


# ------------------------------------------------------------------ replay

def parity_check(a, b):
    return set(a) == set(b) and all(np.array_equal(a[k], b[k]) for k in a)


def branch_replay(raster, n_ticks, store, m, J, g, cues, window=75, short=50, span=75,
                  tau_m=20.0, v_rest=-70.0, v_reset=-65.0, v_th=-50.0, t_ref=2):
    """`readout.replay` over (line, branch) compartments; a line spikes when any of its branches does.

    The line-spike bookkeeping below is replay's, line for line, acting on the OR of the branches.
    """
    indptr, post, comp_line = store.compact()
    C = comp_line.size
    gJ = (np.asarray(g, np.float64) * np.asarray(J, np.float64)).astype(np.float32)
    J = np.asarray(J, np.float32)
    A = J.size
    decay = f32(np.exp(-1.0 / tau_m))
    v_c = f32(v_rest * (1.0 - decay))
    v = np.full((A, C), v_rest, np.float32)
    t_last = np.full((A, C), -10_000, np.int64)
    ring = np.zeros((3, A, C), np.float32)
    win = np.zeros((A, m), bool)
    spans = {}
    first = np.full((A, m), -1, np.int16)
    starts = {c["onset"]: i for i, c in enumerate(cues)}
    if len(starts) != len(cues):
        raise ValueError("two cues share an onset")
    onsets = sorted(starts)
    if any(b - a < window for a, b in zip(onsets, onsets[1:])):
        raise ValueError(f"cue onsets closer than the {window}-tick scoring window")
    if onsets and onsets[-1] + max(window, span) > n_ticks:
        raise ValueError("a scoring window or span runs past the end of the raster")
    out = {k: np.zeros((len(cues), A), np.int32) for k in
           ("missing", "visible", "item", "total", "missing_short", "item_short", "total_short",
            "total_span", "item_span", "other_missing")}
    latency = np.full((len(cues), A), np.nan)
    out_of_window = np.zeros(A, np.int64)
    active = None
    dirty = [False, False, False]
    since_input = 10_000
    for t in range(n_ticks):
        if t in starts:
            active = starts[t]
            win[:] = False
            first[:] = -1
            spans[active] = np.zeros((A, m), bool)
        slot = ring[t % 3]
        np.multiply(v, decay, out=v)
        v += v_c
        if dirty[t % 3]:
            v += slot
            slot[:] = 0.0
            dirty[t % 3] = False
            since_input = 0
        else:
            since_input += 1
        hit = None
        if since_input <= t_ref + 1:
            hit_c = (v >= v_th) & (t - t_last > t_ref)
            if hit_c.any():
                v[hit_c] = v_reset
                t_last[hit_c] = t
                hit = np.zeros((A, m), bool)
                a_i, c_i = np.nonzero(hit_c)
                hit[a_i, comp_line[c_i]] = True
        if active is not None:
            k = t - cues[active]["onset"]
            if hit is not None:
                win |= hit
                newly = hit & (first < 0)
                first[newly] = k
            if k == short - 1:
                c = cues[active]
                win_short = win.copy()
                out["missing_short"][active] = win_short[:, c["missing"]].sum(1)
                out["item_short"][active] = win_short[:, c["item"]].sum(1)
                out["total_short"][active] = win_short.sum(1)
            if k == window - 1:
                c = cues[active]
                out["missing"][active] = win[:, c["missing"]].sum(1)
                out["visible"][active] = win[:, c["cue"]].sum(1)
                out["item"][active] = win[:, c["item"]].sum(1)
                out["total"][active] = win.sum(1)
                out["other_missing"][active] = win[:, c["other_missing"]].sum(1)
                if c["missing"].size:
                    fm = first[:, c["missing"]].astype(float)
                    fm[~win[:, c["missing"]]] = np.nan
                    with np.errstate(all="ignore"):
                        latency[active] = np.nanmedian(fm, axis=1) if np.isfinite(fm).any() else np.nan
                active = None
        elif hit is not None:
            out_of_window += hit.sum(1)
        for i in list(spans):
            if hit is not None:
                spans[i] |= hit
            if t - cues[i]["onset"] == span - 1:
                win_span = spans.pop(i)
                out["total_span"][i] = win_span.sum(1)
                out["item_span"][i] = win_span[:, cues[i]["item"]].sum(1)
        s = raster.get(t)
        if s is not None and s.size:
            lo, cnt = indptr[s], indptr[s + 1] - indptr[s]
            n_ev = int(cnt.sum())
            if n_ev:
                idx = np.repeat(lo, cnt) + (np.arange(n_ev) - np.repeat(np.cumsum(cnt) - cnt, cnt))
                counts = np.bincount(post[idx], minlength=C)
                nxt = ring[(t + 1) % 3]
                for kk in range(1, int(counts.max()) + 1):
                    nxt[:, counts >= kk] += J[:, None]
                dirty[(t + 1) % 3] = True
            ring[(t + 2) % 3] -= (gJ * s.size)[:, None]
            dirty[(t + 2) % 3] = True
    return out, latency, out_of_window


# ------------------------------------------------------------------ step 0

def coincidence_requirement(n_active):
    return math.ceil(round(0.3 * n_active + 7.14, 9))


def step0_decompose(rows_content, rows_cues, R_seq, E_seq, store_point, raster, active_counts):
    """Classify each failing half cue and, for its intrusion lines, the writer span over episodes."""
    episodes_of = {}
    for k, e in enumerate(E_seq):
        for j in np.asarray(e).tolist():
            episodes_of.setdefault(j, []).append(k)
    n_cells = max([int(np.max(r)) + 1 for r in R_seq if len(r)] +
                  [int(np.max(s)) + 1 for s in raster.values() if len(s)] + [1])
    rows, failing, summation = [], 0, 0
    for rc, cue, n_active in zip(rows_content, rows_cues, active_counts):
        d1, intr = rc["missing"] < e3.JOINT_MISSING, rc["intrusions"] >= e3.JOINT_INTRUSIONS
        cls = "both" if d1 and intr else "D1" if d1 else "intrusion" if intr else "pass"
        row = {"class": cls, "lines": {}}
        if cls == "pass":
            rows.append(row)
            continue
        failing += 1
        on = np.zeros(n_cells, bool)
        for t in range(cue["onset"], cue["onset"] + WINDOW):
            s = raster.get(t)
            if s is not None and s.size:
                on[s] = True
        need = coincidence_requirement(n_active)
        cross = 0
        for j in np.asarray(rc["intrusion_lines"]).tolist():
            eps = {k: int(on[R_seq[k]].sum()) for k in episodes_of.get(j, [])}
            reach = any(c >= need for c in eps.values())
            row["lines"][j] = dict(episodes=eps, single_episode_reaches=bool(reach))
            cross += sum(c > 0 for c in eps.values()) >= 2 and not reach
        is_sum = bool(intr and row["lines"] and 2 * cross > len(row["lines"]))
        summation += is_sum
        rows.append(dict(row, summation=is_sum, summation_lines=int(cross), required=need))
    return dict(rows=rows, fraction_summation=(summation / failing) if failing else None)


# ------------------------------------------------------------------ inputs

def _source():
    frozen = {p: hashlib.sha256((record.REPO / p).read_bytes()).hexdigest() for p in FROZEN}
    return dict(git=record.git_state(), runtime=record.runtime(),
                script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), frozen_sha256=frozen)


def _unpack(z, name):
    off, flat = z[name + "_offsets"], z[name]
    return [flat[off[i]:off[i + 1]].astype(np.int64) for i in range(len(off) - 1)]


def _portable_descriptor(cond, arm, M, attempt):
    path = E7_DIR / f"seed{SEED}-{cond}-{arm}.journal.jsonl"
    name = f"{attempt}-{cond}-{arm}-M{M}.json"
    for r in evidence.verify_journal(path):
        if r.get("kind") == "artifact_written" and r.get("name") == name:
            return r["descriptor"]
    raise evidence.EvidenceError(f"{name}: no descriptor in {path.name}")


def load_inputs(cond, arm, M, attempt):
    """Verified inputs of one substrate and load; raises on anything absent or unverifiable."""
    pdesc = _portable_descriptor(cond, arm, M, attempt)
    portable = json.loads(evidence.verify_artifact(pdesc).decode())
    state = evidence.load_npz_artifact(portable["state"])
    test = evidence.load_npz_artifact(portable["raw"])
    smeta, tmeta = json.loads(str(state["metadata_json"])), json.loads(str(test["metadata_json"]))
    raster = dict(zip(test["raster_ticks"].tolist(), _unpack(test, "raster_cells")))
    parts = {k: _unpack(test, "cue_" + k) for k in ("item", "cue", "missing", "other_missing")}
    cues = [dict(kind=str(test["cue_kind"][i]), index=int(test["cue_index"][i]), onset=int(test["cue_onset"][i]),
                 **{k: parts[k][i] for k in parts}) for i in range(len(test["cue_kind"]))]
    return dict(portable=portable, inputs=dict(portable=pdesc, state=portable["state"], raw=portable["raw"]),
                R=_unpack(state, "R"), E=_unpack(state, "E"), A=_unpack(state, "A"),
                feedback_keys=state["feedback_keys"], plateau_keys=state["plateau_keys"],
                labels=smeta.get("labels"), cfg=tmeta["cfg"], raster=raster, n_ticks=tmeta["n_ticks"], cues=cues)


def point_store(keys, n, m):
    s = BinarySynapses(n, m)
    s.keys = np.asarray(keys, np.int64)
    return s


def rebuild_point_keys(writers, E, n, m):
    s = BinarySynapses(n, m)
    s.add(np.concatenate([(np.asarray(w, np.int64)[:, None] * m + np.asarray(e, np.int64)[None, :]).ravel()
                          for w, e in zip(writers, E)]))
    return s.keys


def content_table(res, lat):
    cols = list(res)
    return dict(columns=["cue_id"] + cols + ["latency_ms"],
                rows=[[i] + [int(res[k][i, 0]) for k in cols] + [float(lat[i, 0]) if np.isfinite(lat[i, 0]) else None]
                      for i in range(lat.shape[0])])


def rows_match(table, persisted):
    """Exact equality of a replayed content table with the persisted one."""
    if table["columns"] != persisted["columns"] or len(table["rows"]) != len(persisted["rows"]):
        return False
    same = lambda a, b: a == b or (a is None and b is None)
    return all(all(same(a, b) for a, b in zip(x, y)) for x, y in zip(table["rows"], persisted["rows"]))


def run_arm(d, store, cues=None):
    cfg = d["cfg"]
    t0 = time.time()
    res, lat, oow = branch_replay(d["raster"], d["n_ticks"], store, cfg["m"], np.array([J_FB]), np.array([G_INH]),
                                  d["cues"], window=WINDOW, short=SHORT, span=cfg["t_cue"] + cfg["t_gap"])
    summary = {k: v for k, v in e3.score(res, lat, d["cues"], cfg["n_old"], 1)[0].items() if k != "passes"}
    summary.update(counts=r1.content_counts(res, d["cues"], cfg["n_old"]), out_of_window_spikes=int(oow[0]),
                   wall_seconds=time.time() - t0)
    if d["labels"] is not None:
        rows = [dict(zip(content_table(res, lat)["columns"], r)) for r in content_table(res, lat)["rows"]]
        subset = {}
        for s in ("F10", "independent"):
            joint = [r["missing"] >= e3.JOINT_MISSING and r["total"] - r["item"] < e3.JOINT_INTRUSIONS
                     for r, q in zip(rows, d["cues"]) if q["kind"] == "half" and d["labels"][q["index"]] == s]
            subset[s] = dict(joint=(sum(joint) / len(joint)) if joint else None, joint_count=int(sum(joint)),
                             n_cues=len(joint))
        summary["content_by_subset"] = subset
    jbs = store.keys // store.n
    per_branch = np.bincount(np.unique(jbs, return_inverse=True)[1]) if jbs.size else np.zeros(1, int)
    summary["branches"] = dict(compartments=int(np.unique(jbs).size), synapses=int(store.keys.size),
                               max_writers_per_branch=int(per_branch.max()))
    return res, lat, summary


# ------------------------------------------------------------------ records

def _append(rec):
    record.append(dict(rec, attempt=ATTEMPT, timestamp=record.now()), RESULTS)
    return rec


def _put(journal, name, obj):
    desc = evidence.write_json_artifact(EVIDENCE / name, obj)
    journal.append(dict(kind="artifact_written", name=name, descriptor=desc))
    return desc


def _done(kind):
    if not RESULTS.exists():
        return {}
    rows = [json.loads(x) for x in RESULTS.read_text().splitlines() if x.strip()]
    return {(r.get("condition"), r.get("arm"), r.get("M"), r.get("variant")): r for r in rows
            if r.get("kind") == kind and r.get("status") in ("COMPLETE", "INVALID")}


def _verification(manifest):
    failures = []
    try:
        manifest.verify_all()
    except evidence.EvidenceError as e:
        failures.append(str(e))
    try:
        evidence.verify_journal(JOURNAL)
        ok = True
    except (evidence.EvidenceError, OSError) as e:
        ok, failures = False, failures + [f"journal: {e}"]
    return dict(kind="evidence_verification", artifacts_verified=len(manifest.entries), failures=failures,
                journal_ok=ok, passed=not failures and ok)


def _journal():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    j = evidence.Journal(JOURNAL, "R3-121")
    j.append(dict(kind="run_started", runtime=record.runtime(), script_sha256=_source()["script_sha256"]))
    return j


# ------------------------------------------------------------------ step 0 CLI

def _traced_intrusions(d, keys, half):
    cfg = d["cfg"]
    indptr, post = point_store(keys, cfg["n"], cfg["m"]).csr()
    trace = []
    replay(d["raster"], d["n_ticks"], indptr, post, cfg["m"], np.array([J_FB]), np.array([G_INH]), [],
           window=WINDOW, short=SHORT, span=WINDOW, trace=trace)
    by_tick = {}
    for t, _, line in trace:
        by_tick.setdefault(t, []).append(line)
    out = []
    for q in half:
        seen = {line for t in range(q["onset"], q["onset"] + WINDOW) for line in by_tick.get(t, [])}
        out.append(np.asarray(sorted(seen - set(q["item"].tolist())), np.int64))
    return out


def _active_counts(raster, onset):
    sets = lambda lo, hi: np.unique(np.concatenate([raster[t] for t in range(onset + lo, onset + hi) if t in raster]
                                                   or [np.empty(0, np.int64)]))
    return int(sets(0, WINDOW).size), int(sets(0, SHORT).size), int(sets(SHORT, WINDOW).size)


def step0_one(cond, arm, M, journal, manifest, attempt, log):
    d = load_inputs(cond, arm, M, attempt)
    half = [q for q in d["cues"] if q["kind"] == "half"]
    ids = [i for i, q in enumerate(d["cues"]) if q["kind"] == "half"]
    active = [_active_counts(d["raster"], q["onset"]) for q in half]
    summary, tables = dict(role="step0", n_half=len(half), mean_active_0_74=float(np.mean([a[0] for a in active])),
                           mean_active_0_49=float(np.mean([a[1] for a in active])),
                           mean_active_50_74=float(np.mean([a[2] for a in active]))), {}
    for store, writers in STORES:
        keys = d["feedback_keys"] if store == "inherited" else d["plateau_keys"]
        table = d["portable"]["content_rows"][store]
        cols = table["columns"]
        persisted = [dict(zip(cols, table["rows"][i])) for i in ids]
        lines = _traced_intrusions(d, keys, half)
        rows_content = [dict(missing=r["missing"], intrusions=r["total"] - r["item"], intrusion_lines=ln)
                        for r, ln in zip(persisted, lines)]
        out = step0_decompose(rows_content, half, d["R"] if writers == "R" else d["A"], d["E"], None,
                              d["raster"], [a[0] for a in active])
        classes = [r["class"] for r in out["rows"]]
        summary[store] = dict(failing=sum(c != "pass" for c in classes),
                              **{c: classes.count(c) for c in ("D1", "intrusion", "both", "pass")},
                              fraction_summation=out["fraction_summation"],
                              traced_lines_match_counts=all(len(ln) == rc["intrusions"]
                                                            for ln, rc in zip(lines, rows_content)))
        tables[store] = dict(cue_ids=ids, rows=out["rows"])
    kill = None
    if (cond, arm, M) == ("F10", "label_oracle", 1000):
        frac = summary["inherited"]["fraction_summation"]
        kill = bool(frac is None or frac < 0.5)
    name = f"{attempt}-{cond}-{arm}-M{M}-step0.json"
    desc = _put(journal, name, dict(summary=summary, tables=tables))
    manifest.add(name, desc)
    _append(dict(kind="step0", status="COMPLETE", condition=cond, arm=arm, M=M, summary=summary, kill=kill,
                 artifact=desc, inputs=d["inputs"], source=_source()))
    log(f"step0 {cond}/{arm}/M{M} inherited fraction_summation={summary['inherited']['fraction_summation']} kill={kill}")


def cmd_step0(attempt, log=print):
    journal, manifest = _journal(), evidence.Manifest()
    done = _done("step0")
    for cond, arm in STEP0_SUBSTRATES:
        for M in (500, 1000):
            if (cond, arm, M, None) in done:
                continue
            try:
                step0_one(cond, arm, M, journal, manifest, attempt, log)
            except (evidence.EvidenceError, OSError, KeyError, StopIteration) as e:
                reason = f"input failure: {type(e).__name__}: {e}"
                journal.append(dict(kind="step0_absent", condition=cond, arm=arm, M=M, reason=reason))
                _append(dict(kind="step0", status="ABSENT", condition=cond, arm=arm, M=M, reason=reason))
                log(f"step0 {cond}/{arm}/M{M} ABSENT {reason}")
    ver = _verification(manifest)
    journal.append(ver)
    _append(ver)
    return ver["passed"]


# ------------------------------------------------------------------ run CLI

def step0_kill():
    rows = [r for r in _done("step0").values() if (r["condition"], r["arm"], r["M"]) == ("F10", "label_oracle", 1000)]
    return None if not rows or rows[0].get("kill") is None else rows[0]["kill"]


def run_one(cond, arm, role, M, journal, manifest, attempt, only, log):
    d = load_inputs(cond, arm, M, attempt)
    cfg, m, n = d["cfg"], d["cfg"]["m"], d["cfg"]["n"]
    done = _done("replay")
    rebuilt = rebuild_point_keys(d["R"], d["E"], n, m)
    sha_ok = r1.sha_array(rebuilt) == d["portable"]["feedback_sha256"] and np.array_equal(rebuilt, d["feedback_keys"])
    sha_a = np.array_equal(rebuild_point_keys(d["A"], d["E"], n, m), d["plateau_keys"])
    res1, lat1, s1 = run_arm(d, build_branch_store(d["E"], d["R"], 1, m, n))
    rows_ok = rows_match(content_table(res1, lat1), d["portable"]["content_rows"]["inherited"])
    ok = bool(sha_ok and rows_ok)
    _append(dict(kind="parity", status="COMPLETE" if ok else "INVALID", condition=cond, arm=arm, M=M, role=role,
                 feedback_sha256_equal=bool(sha_ok), content_rows_equal=bool(rows_ok),
                 assigned_A_store_rebuilt=bool(sha_a), inputs=d["inputs"], source=_source()))
    journal.append(dict(kind="parity", condition=cond, arm=arm, M=M, ok=ok))
    log(f"parity {cond}/{arm}/M{M} sha={sha_ok} rows={rows_ok}")
    if not ok:
        return
    for variant, mode, K, side in ARMS:
        if only and variant not in only or (cond, arm, M, variant) in done:
            continue
        if variant == "K1":
            res, lat, summary = res1, lat1, s1
        else:
            writers = d["R"] if side == "R" else d["A"]
            res, lat, summary = run_arm(d, build_branch_store(d["E"], writers, K, m, n, mode=mode,
                                                              scramble_seed=SEED))
        name = f"{attempt}-{cond}-{arm}-M{M}-{variant}.json"
        desc = _put(journal, name, dict(variant=variant, mode=mode, K=K, writers=side,
                                        content=content_table(res, lat)))
        manifest.add(name, desc)
        _append(dict(kind="replay", status="COMPLETE", condition=cond, arm=arm, M=M, role=role, variant=variant,
                     mode=mode, K=K, writers=side, summary=summary, artifact=desc, inputs=d["inputs"],
                     source=_source()))
        log(f"replay {cond}/{arm}/M{M} {variant} joint={summary['joint']:.3f} D1={summary['D1']:.3f} "
            f"({summary['wall_seconds']:.0f}s)")


def cmd_run(attempt, only, log=print):
    kill = step0_kill()
    if kill is None or kill:
        log("refused: " + ("no step0 record for label_oracle at 1000" if kill is None else
                           "the step-0 kill holds (B-015 closes)"))
        return False
    journal, manifest = _journal(), evidence.Manifest()
    for cond, arm, role, loads in SUBSTRATES:
        for M in loads:
            try:
                run_one(cond, arm, role, M, journal, manifest, attempt, only, log)
            except (evidence.EvidenceError, OSError, KeyError, StopIteration) as e:
                reason = f"input failure: {type(e).__name__}: {e}"
                journal.append(dict(kind="replay_absent", condition=cond, arm=arm, M=M, reason=reason))
                _append(dict(kind="replay", status="ABSENT", condition=cond, arm=arm, M=M, reason=reason))
                log(f"replay {cond}/{arm}/M{M} ABSENT {reason}")
    ver = _verification(manifest)
    journal.append(ver)
    _append(ver)
    return ver["passed"]


# ------------------------------------------------------------------ summary

def _records():
    rows = [json.loads(x) for x in RESULTS.read_text().splitlines() if x.strip()] if RESULTS.exists() else []
    return rows


def score_predictions(rows):
    rep = {(r["condition"], r["arm"], r["M"], r["variant"]): r["summary"]
           for r in rows if r.get("kind") == "replay" and r.get("status") == "COMPLETE"}
    par = [r for r in rows if r.get("kind") == "parity"]
    get = lambda c, a, M, v, f="joint": rep.get((c, a, M, v), {}).get(f)
    inside = lambda x, lo, hi: None if x is None else bool(lo <= x <= hi)
    out, kills = {}, {}
    out["P1"] = bool(par) and all(r["status"] == "COMPLETE" for r in par) and len(par) == 8
    O, G = ("F10", "label_oracle", 1000), ("F10", "gate_off", 500)
    p = get(*O, "K1")
    out["P2"] = inside(get(*O, "K32"), .60, .95)
    kills["P2"] = None if p is None or get(*O, "K32") is None else get(*O, "K32") < p + .15
    out["P3"] = inside(get(*O, "assigned_A_K32"), .70, .98)
    out["P4"] = inside(get(*G, "K32"), .50, .95)
    p4 = get(*G, "K1")
    kills["P4"] = None if p4 is None or get(*G, "K32") is None else get(*G, "K32") < p4 + .20
    out["P5"] = inside(get("F10", "gate_off", 1000, "K32"), 0, .30)
    out["P6"] = inside(get("F10", "candidate", 1000, "K32"), .05, .50)
    j5, j10 = get("independent", "candidate", 500, "K32"), get("independent", "candidate", 1000, "K32")
    out["P7"] = None if j5 is None or j10 is None else bool(j5 >= .975 and j10 >= .940)
    drops = [get("independent", "candidate", M, "K1") - get("independent", "candidate", M, "K32")
             for M in (500, 1000) if get("independent", "candidate", M, "K1") is not None
             and get("independent", "candidate", M, "K32") is not None]
    kills["P7"] = any(x > .05 for x in drops) if drops else None
    sub = rep.get(("mixed", "baseline", 1000, "K32"), {}).get("content_by_subset", {}).get("independent")
    out["P8"] = None if sub is None else bool(32 <= sub["joint_count"] <= 80)
    scr, k32 = get(*O, "scramble"), get(*O, "K32")
    out["P9"] = None if scr is None else bool(scr <= .41)
    kills["P9"] = None if scr is None or k32 is None else abs(scr - k32) < .05
    novel = [(get(c, a, M, "K32", "novel_lines_median"), get(c, a, M, "K1", "novel_lines_median"))
             for c, a, _, loads in SUBSTRATES for M in loads]
    out["P10"] = None if any(x is None or y is None for x, y in novel) else all(x <= y for x, y in novel)
    dose = []
    for c, a, M in (O, ("F10", "label_oracle", 500), G, ("F10", "gate_off", 1000)):
        v = [get(c, a, M, k) for k in ("K8", "K32", "unbounded")]
        dose.append(None if None in v else bool(v[0] <= v[1] <= v[2]))
    out["P11"] = None if None in dose else all(dose)
    d1 = [(get(c, a, M, "K32", "D1"), get(c, a, M, "K1", "D1")) for c, a, _, loads in SUBSTRATES for M in loads]
    out["P12"] = None if any(x is None or y is None for x, y in d1) else all(abs(x - y) <= .05 for x, y in d1)
    return out, kills


def cmd_summary(write, log=print):
    rows = _records()
    scores, kills = score_predictions(rows)
    step0 = {f"{r['condition']}/{r['arm']}/{r['M']}": r.get("summary", {}).get("inherited", {}).get("fraction_summation")
             for r in rows if r.get("kind") == "step0" and r.get("status") == "COMPLETE"}
    reading = dict(step0_fraction_summation=step0, step0_kill=step0_kill(), replay_kills=kills, predictions=scores,
                   verifications=[r["passed"] for r in rows if r.get("kind") == "evidence_verification"])
    print(json.dumps(reading, sort_keys=True, indent=1))
    if write:
        _append(dict(kind="summary", status="COMPLETE", **reading))
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--attempt", default=ATTEMPT)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("step0", help="decomposition of the point-store failures on the gate_off and oracle rasters")
    runner = commands.add_parser("run", help="parity then the replay arms on every substrate and load")
    runner.add_argument("--only", action="append", choices=[a[0] for a in ARMS], help="restrict to these arms")
    summarizer = commands.add_parser("summary", help="score P1-P12 from the recorded fields")
    summarizer.add_argument("--write", action="store_true", help="also append a summary record")
    args = parser.parse_args(argv)
    log = lambda x: print(f"[{record.now()}] {x}", flush=True)
    if args.command == "summary":
        return 0 if cmd_summary(args.write, log) else 1
    if args.command == "step0":
        return 0 if cmd_step0(args.attempt, log) else 1
    return 0 if cmd_run(args.attempt, args.only, log) else 1


if __name__ == "__main__":
    raise SystemExit(main())
