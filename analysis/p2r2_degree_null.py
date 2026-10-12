"""P2-R2 fixed-degree input diagnostic; no learning mechanism is changed.

After committing this driver, run two workers with ``run --seed 103`` and
``run --seed 104``. Each executes original/null sequentially. One permanent
experiment clock includes preprocessing; a started seed is never overwritten.
"""
import argparse
import copy
import hashlib
import json
import os
import signal
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path

import numpy as np

from analysis import p2r1_replay as r1
from plant2 import record
from plant2.experiments import p2_e1_btsp as e1
from plant2.experiments import p2_e3_completion as e3
from plant2.experiments import p2_e5_structured as e5
from plant2.readout import replay

CONTRACT_PATH = "docs/plant2/P2-R2-degree-null.md"
CONTRACT_COMMIT = "2454f06603567d7b5d9a3832c2b1e05f519b0279"
BASELINE = "55e16ebff62a90d6402745f44fb860010741eba5"
SEEDS, LOADS, ARMS = (103, 104), (500, 1000), ("ORIGINAL", "DEGREE_NULL")
SNAPSHOTS, BLOCK, TRADES = (0, 2500, 5000, 10000), 100, 10000
CFG = dict(e5.CONTRACT)
RESULTS = record.REPO / "bench/results/p2r2.jsonl"
EVIDENCE = record.REPO / "bench/results/p2r2"
INHERITED = ["plant2/" + p for p in e5.REUSED_FILES] + [
    "plant2/experiments/p2_e5_structured.py", "plant2/record.py"]
SOURCES = INHERITED + ["analysis/p2r1_replay.py", "analysis/p2r2_degree_null.py",
                       "plant2/tests/test_p2_r2.py", CONTRACT_PATH]
EPS = 1e-12


class IntegrityError(RuntimeError):
    pass


class ResourceStop(RuntimeError):
    pass


def require(ok, reason):
    if not ok:
        raise IntegrityError(reason)


class Budget:
    def __init__(self, start=None):
        self.start = start

    def check(self, new_stage=False):
        if self.start is None:
            return
        elapsed = time.time() - self.start
        if elapsed >= 1200:
            raise ResourceStop("20-minute hard stop")
        if new_stage and elapsed >= 1080:
            raise ResourceStop("18-minute new-stage stop")
        if elapsed >= 1140:
            raise ResourceStop("19-minute computation stop; reserve final minute for checkpointing")


@contextmanager
def hard_deadline(budget, checkpoint=False):
    if budget.start is None:
        yield
        return
    previous = signal.getsignal(signal.SIGALRM)

    def stop(signum, frame):
        raise ResourceStop("20-minute hard stop" if checkpoint else "19-minute computation stop; checkpoint reserve")
    signal.signal(signal.SIGALRM, stop)
    signal.setitimer(signal.ITIMER_REAL, max(.001, budget.start + (1200 if checkpoint else 1140) - time.time()))
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


@contextmanager
def bounded_steps(e, budget):
    original, ticks = e.net.step, 0

    def step(rng):
        nonlocal ticks
        ticks += 1
        if ticks % 1024 == 0:
            budget.check()
        return original(rng)
    e.net.step = step
    try:
        yield
    finally:
        del e.net.step


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as f:
        f.write(r1.json_bytes(value))
    return r1.file_info(path, relative=path.is_relative_to(record.REPO))


def write_npz(path, **values):
    with Path(path).open("xb") as f:
        np.savez_compressed(f, **values)
    return r1.file_info(Path(path))


class _AdapterState:
    def __init__(self, adapter):
        self.adapter = adapter

    @property
    def state(self):
        a = self.adapter
        return dict(generator="p2r2_precomputed", matrix_sha256=a.digest, k=a.k)


class MatrixItems:
    """Only choice() exposes the current row to the unchanged E3 learner."""
    def __init__(self, rows, m):
        self.rows = np.asarray(rows, np.int64).copy()
        self.m, self.k = int(m), 0
        require(self.rows.ndim == 2, "input matrix must contain sorted row lists")
        require(bool(((self.rows >= 0) & (self.rows < m)).all()), "input line outside population")
        require(bool((np.diff(self.rows, axis=1) > 0).all()), "input rows must be sorted and unique")
        self.digest = r1.sha_array(self.rows)
        self.rows.flags.writeable = False
        self.bit_generator = _AdapterState(self)

    def choice(self, m, a, replace=False):
        if m != self.m or a != self.rows.shape[1] or replace or self.k >= len(self.rows):
            raise ValueError("unsupported precomputed item request")
        item = self.rows[self.k].copy()
        self.k += 1
        return item


def original_items(seed, F=10, count=1000, m=4000, a=100, s=60):
    gen = e5.FamilyGen(seed, m, a, s, F)
    return np.asarray([gen.choice(m, a, replace=False) for _ in range(count)], np.int64)


def curveball_block(rows, rng, snapshots=SNAPSHOTS, budget=None):
    """Fixed attempted trades, uniform distinct row pair and uniform exclusive allocation."""
    budget = budget or Budget()
    work = np.asarray(rows, np.int64).copy()
    saved, changed, counts = {0: work.copy()}, 0, {0: 0}
    for step in range(1, max(snapshots) + 1):
        if step % 256 == 0:
            budget.check()
        i = int(rng.integers(len(work)))
        j = int(rng.integers(len(work) - 1))
        j += j >= i
        common = np.intersect1d(work[i], work[j], assume_unique=True)
        exclusive = np.setxor1d(work[i], work[j], assume_unique=True)
        take = len(work[i]) - len(common)
        shuffled = rng.permutation(exclusive)
        first = np.sort(np.concatenate((common, shuffled[:take])))
        second = np.sort(np.concatenate((common, shuffled[take:])))
        changed += int(not np.array_equal(first, work[i]))
        work[i], work[j] = first, second
        if step in snapshots:
            saved[step], counts[step] = work.copy(), changed
    return saved, counts


def incidence(rows, m, dtype=np.float64):
    result = np.zeros((len(rows), m), dtype=dtype)
    result[np.arange(len(rows))[:, None], rows] = 1
    return result


def margins(rows, m, block=BLOCK):
    return np.asarray([np.bincount(b.ravel(), minlength=m)
                       for b in np.asarray(rows).reshape(-1, block, rows.shape[1])], np.int64)


def check_margins(original, randomized, m, block=BLOCK):
    require(original.shape == randomized.shape, "null shape changed")
    require(bool(((randomized >= 0) & (randomized < m)).all()), "null line outside population")
    require(bool((np.diff(randomized, axis=1) > 0).all()), "null is not sorted binary membership")
    require(np.array_equal(margins(original, m, block), margins(randomized, m, block)),
            "block column totals changed")
    return True


def structural_metrics(original, randomized, m, F, attempted, changed, block=BLOCK):
    """Float64 BLAS computes exact integer overlaps <=row size without integer overflow."""
    x, y = incidence(original, m), incidence(randomized, m)
    overlap = y @ y.T
    i, j = np.triu_indices(len(y), 1)
    values = overlap[i, j]
    same = ((i + 1) % F) == ((j + 1) % F)
    retention = (x * y).sum(axis=1) / original.shape[1]
    differences = (y - x).reshape(-1, block, m).cumsum(axis=1)
    return dict(D=float(values[same].mean() - values[~same].mean()),
                Q=float(np.square(values).mean()), R=float(retention.mean()),
                mean_overlap=float(values.mean()),
                overlap_histogram=np.bincount(values.astype(np.int64), minlength=original.shape[1] + 1).tolist(),
                lag_means={str(lag): float(np.diag(overlap, lag).mean())
                           for lag in (1, 10, 50, 100) if lag < len(y)},
                attempted_trades=int(attempted), changed_trades=int(changed),
                changed_row_fraction=float((retention < 1).mean()),
                changed_entry_fraction=float(np.count_nonzero(y != x) / y.size),
                within_block_cumulative_max=int(np.abs(differences).max()),
                within_block_cumulative_rms=float(np.sqrt(np.square(differences).mean())))


def structural_decision(chains, late=5000, endpoint=10000):
    """All checks apply to both chains; positive Q denominators are checked explicitly."""
    def close(a, b):
        denom = (a["Q"] + b["Q"]) / 2
        return dict(Q=bool(denom > 0 and abs(a["Q"] - b["Q"]) / denom <= .05 + EPS),
                    R=bool(abs(a["R"] - b["R"]) <= .03 + EPS),
                    D=bool(abs(a["D"] - b["D"]) <= .5 + EPS))
    checks = {}
    for chain in ("0", "1"):
        c = chains[chain]
        checks[chain + "/D_reduced"] = bool(abs(c[str(endpoint)]["D"]) <= max(1, .1 * abs(c["0"]["D"])) + EPS)
        checks.update({chain + "/late/" + k: v for k, v in close(c[str(late)], c[str(endpoint)]).items()})
    checks.update({"between/" + k: v for k, v in close(chains["0"][str(endpoint)], chains["1"][str(endpoint)]).items()})
    return dict(ok=all(checks.values()), checks=checks,
                label="STRUCTURAL CHECKS HOLD" if all(checks.values()) else "STRUCTURAL CONTRAST UNCERTAIN")


def preprocess(seed, F, cache, evidence, budget, meta, log=print, progress=None):
    budget.check(new_stage=True)
    t0 = time.time()
    original = original_items(seed, F)
    if progress is not None:
        progress.update(stage=f"F{F}/preprocessing", preprocessing_original=original, preprocessing_F=F)
    original_digest = r1.sha_array(original)
    # One original pass-through adapter is shared with the null input interface.
    require(MatrixItems(original, 4000).digest == original_digest, "original/sham adapter changed matrix")
    snapshots, trade_counts = {}, {}
    for chain in (0, 1):
        per_step = {step: [] for step in SNAPSHOTS}
        per_count = {step: [] for step in SNAPSHOTS}
        for block_id in range(10):
            rows = original[block_id * BLOCK:(block_id + 1) * BLOCK]
            ss, cc = curveball_block(rows, e1.stream(seed, 40, F, block_id, chain), budget=budget)
            for step in SNAPSHOTS:
                check_margins(rows, ss[step], 4000)
                per_step[step].append(ss[step])
                per_count[step].append(cc[step])
        snapshots[chain] = {step: np.concatenate(per_step[step]) for step in SNAPSHOTS}
        trade_counts[chain] = per_count
    require(r1.sha_array(original) == original_digest, "preprocessing mutated canonical input")
    payload = dict(original=original, block_marginals=margins(original, 4000),
                   metadata_json=np.asarray(r1.json_bytes(dict(meta, F=F, snapshots=SNAPSHOTS)).decode()))
    for chain, ss in snapshots.items():
        for step, rows in ss.items():
            payload[f"chain{chain}_step{step}"] = rows
    raw = write_npz(cache / f"F{F}-inputs.npz", **payload)
    per_load = {}
    for M in LOADS:
        budget.check()
        chains = {}
        for chain in (0, 1):
            chains[str(chain)] = {}
            for step in SNAPSHOTS:
                rows = snapshots[chain][step][:M]
                check_margins(original[:M], rows, 4000)
                metric = structural_metrics(original[:M], rows, 4000, F, step * (M // BLOCK),
                                            sum(trade_counts[chain][step][:M // BLOCK]))
                column_counts = np.bincount(original[:M].ravel(), minlength=4000)
                expected_overlap = float(np.sum(column_counts * (column_counts - 1)) / (M * (M - 1)))
                require(abs(metric["mean_overlap"] - expected_overlap) <= EPS,
                        "overall mean overlap disagrees with exact column margins")
                metric["mean_overlap_invariant"] = True
                metric["matrix_sha256"] = r1.sha_array(rows)
                chains[str(chain)][str(step)] = metric
        decision = structural_decision(chains)
        per_load[str(M)] = dict(chains=chains, decision=decision,
            exact_block_marginals=True, exact_prefix_marginals=True,
            original_sha256=r1.sha_array(original[:M]))
    value = dict(meta, F=F, loads=per_load, raw=raw, original_sha256=original_digest,
                 null_sha256=r1.sha_array(snapshots[0][TRADES]), wall_s=time.time() - t0,
                 original_sham_identical=True, chain_delivered=0,
                 limitations="finite constrained chain; family labels used only for diagnostics; no uniformity certificate")
    value["portable"] = write_json(evidence / f"seed{seed}-F{F}-structure.json", value)
    log(f"seed {seed} F{F} structural checks: {[per_load[str(M)]['decision']['ok'] for M in LOADS]}")
    return original, snapshots[0][TRADES], value


def ragged_digest(arrays):
    h = hashlib.sha256()
    for a in arrays:
        h.update(np.asarray([len(a)], dtype="<i8").tobytes())
        h.update(np.asarray(a, dtype="<i8").tobytes())
    return h.hexdigest()


def parity_check():
    cfg = dict(CFG, m=256, n=256, a=64, f_q=.05)
    gen = e1.stream(103, e1.PATTERNS)
    rows = np.asarray([np.sort(gen.choice(256, 64, replace=False)) for _ in range(20)])
    direct, sham = e3.E3(cfg, 103), e3.E3(cfg, 103)
    sham._pat = MatrixItems(rows, cfg["m"])
    direct.learn(20)
    sham.learn(20)
    for key in ("items", "A", "E", "R"):
        require(ragged_digest(getattr(direct, key)) == ragged_digest(getattr(sham, key)), "parity " + key)
    for key in ("store", "fb", "fb_plateau"):
        require(np.array_equal(getattr(direct, key).keys, getattr(sham, key).keys), "parity " + key)
    for key in ("v", "vbar", "t_last", "ring"):
        require(np.array_equal(getattr(direct.mem, key), getattr(sham.mem, key)), "parity neural " + key)
    for key in ("_learn_in", "_plat", "_coin"):
        require(r1.json_bytes(getattr(direct, key).bit_generator.state) ==
                r1.json_bytes(getattr(sham, key).bit_generator.state), "parity RNG " + key)
    require(direct.learn_log == sham.learn_log and direct.net.t == sham.net.t and sham._pat.k == 20,
            "parity learning log/clock/adapter counter")
    # Reuse the inherited state digest after equating ONLY the replaced generator for comparison.
    sham._pat = copy.deepcopy(direct._pat)
    require(r1.live_digest(direct) == r1.live_digest(sham), "parity complete live neural/projection state")
    return dict(passed=True, seed=103, episodes=20, config=dict(m=256, n=256, a=64, f_q=.05),
                forward_sha256=r1.sha_array(direct.store.keys), A_sha256=ragged_digest(direct.A))


def state_digest(e):
    return hashlib.sha256(r1.json_bytes(dict(live=r1.live_digest(e), items=ragged_digest(e.items),
        A=ragged_digest(e.A), E=ragged_digest(e.E), R=ragged_digest(e.R), learning=e.learn_log))).hexdigest()


def learned_save(path, e, meta):
    payload = dict(metadata_json=np.asarray(r1.json_bytes(dict(meta, cfg=e.c, learned=len(e.items),
                    net_t=e.net.t, rngs={k: getattr(e, k).bit_generator.state
                    for k in ("_pat", "_learn_in", "_plat", "_coin")})).decode()),
                   forward_keys=e.store.keys, feedback_keys=e.fb.keys,
                   assigned_feedback_keys=e.fb_plateau.keys, learned_mem_v=e.mem.v,
                   learned_mem_vbar=e.mem.vbar, learned_mem_ring=e.mem.ring,
                   learned_mem_t_last=e.mem.t_last, learning_json=np.asarray(r1.json_bytes(e.learn_log).decode()))
    for name in ("items", "A", "E", "R"):
        r1.pack_ragged(payload, name, getattr(e, name))
    return write_npz(path, **payload)


def raster_save(path, e, M, raster, n_ticks, cues, out, meta):
    payload = dict(metadata_json=np.asarray(r1.json_bytes(dict(meta, cfg=e.c, M=M, n_ticks=n_ticks)).decode()),
                   memory_out_json=np.asarray(r1.json_bytes(out).decode()),
                   raster_ticks=np.asarray(sorted(raster), np.int64),
                   cue_kind=np.asarray([q["kind"] for q in cues]),
                   cue_index=np.asarray([q["index"] for q in cues]), cue_onset=np.asarray([q["onset"] for q in cues]))
    r1.pack_ragged(payload, "raster_cells", [raster[t] for t in sorted(raster)])
    for key in ("item", "cue", "missing", "other_missing"):
        r1.pack_ragged(payload, "cue_" + key, [q[key] for q in cues])
    return write_npz(path, **payload)


def index_evidence(e, M, cues, out, raster, offsets):
    rows = r1.cue_evidence(e, cues, out)
    for q, row, offset in zip(cues, rows, offsets):
        first, spikes = {}, []
        for tick in range(q["onset"], q["onset"] + e.c["t_cue"]):
            for cell in raster.get(tick, ()):
                first.setdefault(int(cell), tick - q["onset"])
                if tick - q["onset"] < 50:
                    spikes.append(int(cell))
        R = np.asarray(sorted(k for k, v in first.items() if v < 50), np.int64)
        row.update(total50=int(len(R)), spikes50_total=len(spikes),
                   first_spikes100=[[k, first[k]] for k in sorted(first)], threshold_offset=offset)
        if q["kind"] != "novel":
            A = e.A[q["index"]]
            own = int(np.isin(A, R).sum())
            own_spikes = int(np.isin(spikes, A).sum())
            row.update(own50=own, spurious50=int(len(R) - own), A_size=int(len(A)),
                       spikes50_own=own_spikes, spikes50_spurious=len(spikes) - own_spikes,
                       age_items=M - 1 - int(q["index"]))
    half = [r for r in rows if r["kind"] == "half"]
    joint = [r["own50"] >= .8 * r["A_size"] and r["spurious50"] < .5 * r["A_size"] for r in half]
    cr = out["criteria"]
    metrics = {k: cr[k + "_frac"] for k in ("C1", "C2", "C3", "C4_recall", "C4_spurious")}
    metrics.update(joint_index=float(np.mean(joint)), joint_index_count=int(sum(joint)),
                   counts=r1.index_counts(out, e.c), absolute_index_bars={k: bool(cr[k + "_frac"] >= .9)
                   for k in ("C1", "C2", "C3", "C4_recall", "C4_spurious")})
    metrics["age_strata"] = {}
    for lo, hi in ((0, 99), (100, 499), (500, 999)):
        group = [r for r in half if lo <= r["age_items"] <= hi]
        metrics["age_strata"][f"{lo}-{hi}"] = dict(n=len(group),
            C1=float(np.mean([r["recall50"] >= .8 for r in group])) if group else None,
            C2=float(np.mean([r["spurious50"] < .5 * r["A_size"] for r in group])) if group else None)
    return rows, metrics


def content_evidence(e, raster, n_ticks, cues, store):
    indptr, post = store.csr()
    res, latency, oow = replay(raster, n_ticks, indptr, post, e.c["m"], np.array([2.8]), np.array([.3]), cues,
                              window=75, short=50, span=e.c["t_cue"] + e.c["t_gap"])
    summary = {k: v for k, v in e3.score(res, latency, cues, e.c["n_old"], 1)[0].items() if k != "passes"}
    summary.update(counts=r1.content_counts(res, cues, e.c["n_old"]), out_of_window_spikes=int(oow[0]),
                   store_size=store.size, store_sha256=r1.sha_array(store.keys))
    summary["absolute_content_bars"] = {k: bool(summary[k] >= .9) for k in ("joint", "D3", "D4")}
    cols = list(res)
    portable = dict(columns=["cue_id"] + cols + ["latency_ms"],
        rows=[[i] + [int(res[k][i, 0]) for k in cols] +
              [float(latency[i, 0]) if np.isfinite(latency[i, 0]) else None] for i in range(len(cues))])
    return summary, portable


def evaluate_load(main, M, cache, evidence, meta, budget, learned_raw, emit, progress=None):
    budget.check(new_stage=True)
    before, e = state_digest(main), copy.deepcopy(main)
    if progress is not None:
        progress.update(stage=f"{meta['arm']}/{M}/settling", evaluation=e)
    count = 2 * len(e1.test_sets(e.c, e.seed, M)[0]) + e.c["n_novel"]
    planned = e3.build_cues(e, M, [0] * count)
    offsets, timing = [], {}
    original_rates, original_settle = e._rates, e.settle_drift

    def rates(active):
        if active is not None:
            q = planned[len(offsets)]
            A = e.A[q["index"]] if q["kind"] != "novel" else np.empty(0, np.int64)
            offset = e.mem.threshold() - float(e.mem.v_th)
            offsets.append(dict(global_mv=float(offset.mean()), assigned_mv=float(offset[A].mean()) if A.size else None))
        original_rates(active)

    def settle(load, phase):
        t = time.time()
        budget.check(new_stage=True)
        result = original_settle(load, phase)
        timing["settling_s"] = time.time() - t
        budget.check(new_stage=True)  # presentation is a separate new stage
        if progress is not None:
            progress["stage"] = f"{meta['arm']}/{M}/presentation"
        return result

    e._rates, e.settle_drift = rates, settle
    t = time.time()
    try:
        with bounded_steps(e, budget):
            out, raster, n_ticks, onsets, drift = e3.run_phase(e, M, phase=1)
    finally:
        del e._rates
        del e.settle_drift
    timing["evaluation_s"] = time.time() - t - timing["settling_s"]
    cues = e3.build_cues(e, M, onsets)
    require(len(offsets) == len(cues), "cue-onset state capture mismatch")
    require(state_digest(main) == before, "evaluation changed learning state")
    require(np.array_equal(main.store.keys, e.store.keys) and np.array_equal(main.fb.keys, e.fb.keys)
            and np.array_equal(main.fb_plateau.keys, e.fb_plateau.keys), "evaluation changed copied synapses")
    raster_digest = r1.raster_digest(raster, n_ticks, e.c["n"])
    stem = f"seed{main.seed}-{meta['arm']}-M{M}"
    raw = raster_save(cache / (stem + "-raster.npz"), main, M, raster, n_ticks, cues, out, meta)
    rows, index = index_evidence(e, M, cues, out, raster, offsets)
    mean_A = float(np.mean([len(A) for A in main.A]))
    protocol = dict(eligibility=bool(np.mean(main.learn_log["elig_frac"]) >= .95),
                    mean_A_1000=bool(18.5 <= mean_A <= 21.5) if M == 1000 else None,
                    settled=bool(drift[0] <= .2))
    learning = dict(mean_A=mean_A, eligibility_mean=float(np.mean(main.learn_log["elig_frac"])),
        drift_mv=list(drift), forward_size=main.store.size,
        forward_density=main.store.size / (main.c["m"] * main.c["n"]),
        pre_degree=np.diff(main.store.csr()[0]).tolist(), post_degree=main.store.per_post_count().tolist(),
        coin_draws_per_episode=[int(len(E) * len(A)) for E, A in zip(main.E, main.A)],
        eligibility_block_counts=[np.bincount(np.concatenate(main.E[k:k + BLOCK]), minlength=main.c["m"]).tolist()
                                  for k in range(0, M, BLOCK)],
        potentiated=int(sum(main.learn_log["potentiated"])), depressed=int(sum(main.learn_log["depressed"])))
    compact = dict(meta, M=M, index=index, index_cues=rows, protocol=protocol, learning=learning,
                   content={}, content_summaries={}, timing=timing, raster_sha256=raster_digest,
                   raw=dict(learned=learned_raw, raster=raw), integrity=True,
                   matching=dict(A=ragged_digest(main.A), items=ragged_digest(main.items), E=ragged_digest(main.E),
                       novel=ragged_digest(main.novel)), limitation="shared initial RNGs, not identical sensory spikes or BTSP candidate coins")
    index_file = write_json(evidence / (stem + "-index.json"), compact)
    emit("index_load", arm=meta["arm"], M=M, index=index, protocol=protocol, portable=index_file)
    for name, store in (("inherited", main.fb), ("assigned_A", main.fb_plateau)):
        budget.check(new_stage=True)
        if progress is not None:
            progress["stage"] = f"{meta['arm']}/{M}/replay/{name}"
        t = time.time()
        summary, portable = content_evidence(e, raster, n_ticks, cues, store)
        timing["replay_" + name + "_s"] = time.time() - t
        require(state_digest(main) == before, "replay changed learning state")
        require(r1.raster_digest(raster, n_ticks, e.c["n"]) == raster_digest, "replay changed memory raster")
        half = [r for r in rows if r["kind"] == "half"]
        crow = [dict(zip(portable["columns"], r)) for r in portable["rows"]]
        summary["joint_index_and_content"] = float(np.mean([
            r["own50"] >= .8 * r["A_size"] and r["spurious50"] < .5 * r["A_size"] and
            crow[r["cue_id"]]["missing"] >= 40 and crow[r["cue_id"]]["total"] - crow[r["cue_id"]]["item"] < 10
            for r in half]))
        content_file = write_json(evidence / (stem + "-" + name + ".json"),
                                 dict(meta, M=M, store=name, summary=summary, cues=portable, raster_sha256=raster_digest))
        compact["content"][name], compact["content_summaries"][name] = portable, summary
        emit("content_load", arm=meta["arm"], M=M, store=name, summary=summary, portable=content_file)
    path = write_json(evidence / (stem + ".json"), compact)
    return dict(arm=meta["arm"], M=M, index=index, content=compact["content_summaries"], protocol=protocol,
                learning=learning, matching=compact["matching"], timing=timing, integrity=True,
                raw=compact["raw"], portable=path)


def checkpoint_interrupted(main, progress, exc, path, meta):
    """Forensic state only; mid-episode snapshots are never marked learned or resumed.

    Inherited replay has no checkpoint callback. The exception traceback retains
    its actual paused reconstruction arrays; capture numeric locals without
    changing the numerical algorithm or introducing a scientific stage.
    """
    payload, details = {}, dict(meta, stage=progress.get("stage"), error=repr(exc),
        resumable=False, role="forensic in-flight checkpoint; not a completed episode/load")
    def stash(name, value):
        if isinstance(value, np.ndarray) and value.dtype.kind in "biufUS":
            payload[name] = value
        elif isinstance(value, dict):
            for key, val in value.items():
                stash(name + "_" + str(key), val)
        elif isinstance(value, (tuple, list)):
            for i, val in enumerate(value):
                stash(name + "_" + str(i), val)
        elif isinstance(value, (int, float, bool, np.number)):
            payload[name] = np.asarray(value)
    for prefix, e in (("main", main), ("evaluation", progress.get("evaluation"))):
        if e is None:
            continue
        details[prefix] = dict(started_items=len(e.items), assigned_sets=len(e.A),
            eligibility_sets=len(e.E), responder_sets=len(e.R), completed_continuation_offsets=len(e.cont_offset),
            net_t=e.net.t, rngs={k: getattr(e, k).bit_generator.state for k in ("_pat", "_learn_in", "_plat", "_coin")})
        for key in ("store", "fb", "fb_plateau"):
            payload[prefix + "_" + key] = getattr(e, key).keys
        for key in ("v", "vbar", "t_last", "ring"):
            payload[prefix + "_mem_" + key] = getattr(e.mem, key)
        for key in ("items", "A", "E", "R"):
            r1.pack_ragged(payload, prefix + "_" + key, getattr(e, key))
        if hasattr(e, "_raster"):
            ticks = sorted(e._raster)
            payload[prefix + "_raster_ticks"] = np.asarray(ticks, np.int64)
            r1.pack_ragged(payload, prefix + "_raster_cells", [e._raster[t] for t in ticks])
            details[prefix]["raster_t0"] = e._t0
            details[prefix]["onsets"] = e._onsets
    if "preprocessing_original" in progress:
        payload["preprocessing_original"] = progress["preprocessing_original"]
    watched = {e3.E3.learn_one.__code__: {"item", "plateau", "counts", "eligible", "responded", "R", "_", "pot", "dep", "mem_spk"},
               replay.__code__: {"v", "t_last", "ring", "win", "win_short", "first", "out", "latency",
                                  "out_of_window", "spans", "active", "t", "since_input", "dirty"},
               curveball_block.__code__: {"work", "saved", "counts", "step", "changed"},
               preprocess.__code__: {"original", "snapshots", "per_step", "chain", "block_id", "ss"},
               structural_metrics.__code__: {"original", "randomized"}}
    trace, frames = exc.__traceback__, []
    while trace is not None:
        frame = trace.tb_frame
        if frame.f_code in watched:
            prefix = "paused_" + frame.f_code.co_name
            frames.append(dict(function=frame.f_code.co_name, line=trace.tb_lineno))
            for name in watched[frame.f_code]:
                if name in frame.f_locals:
                    stash(prefix + "_" + name, frame.f_locals[name])
        trace = trace.tb_next
    details["paused_frames"] = frames
    payload["metadata_json"] = np.asarray(r1.json_bytes(details).decode())
    return write_npz(path, **payload)


def classify(original, null):
    delta = {k: null[k] - original[k] for k in ("C1", "C2", "C3", "C4_recall", "C4_spurious", "joint_index")}
    if delta["C1"] < -.03 - EPS or delta["C4_recall"] < -.03 - EPS:
        label = "RECALL TRADE-OFF"
    elif delta["C2"] >= .15 - EPS and delta["joint_index"] >= .10 - EPS:
        label = "MATERIAL STRUCTURE SENSITIVITY"
    elif (original["C2"] < .9 and null["C2"] < .9 and abs(delta["C2"]) <= .05 + EPS
          and abs(delta["joint_index"]) <= .05 + EPS):
        label = "FAILURE PERSISTS WITH SMALL MEASURED BENEFIT"
    else:
        label = "MIXED/INTERMEDIATE"
    return dict(label=label, delta=delta, C2_bar_deficit_removed=(delta["C2"] / (.9 - original["C2"]))
                if original["C2"] < .9 else None)


def paired_evidence(original, null):
    a = json.loads(Path(original["portable"]["path"]).read_text()) if Path(original["portable"]["path"]).is_absolute() else json.loads((record.REPO / original["portable"]["path"]).read_text())
    b = json.loads(Path(null["portable"]["path"]).read_text()) if Path(null["portable"]["path"]).is_absolute() else json.loads((record.REPO / null["portable"]["path"]).read_text())
    require(original["matching"]["A"] == null["matching"]["A"], "assigned assemblies differ across inputs")
    require(original["matching"]["novel"] == null["matching"]["novel"], "independent novel cues differ")
    aa, bb = a["index_cues"], b["index_cues"]
    require(len(aa) == len(bb) and all((x["kind"], x["index_0based"], x["onset"]) ==
            (y["kind"], y["index_0based"], y["onset"]) for x, y in zip(aa, bb)), "paired cue schedules differ")
    def discordance(x, y):
        return dict(n=len(x), original_only=int(sum(u and not v for u, v in zip(x, y))),
                    null_only=int(sum(v and not u for u, v in zip(x, y))))
    ah, bh = [r for r in aa if r["kind"] == "half"], [r for r in bb if r["kind"] == "half"]
    bits = lambda rows: {"C1": [r["recall50"] >= .8 for r in rows],
                        "C2": [r["spurious50"] < .5 * r["A_size"] for r in rows],
                        "joint_index": [r["recall50"] >= .8 and r["spurious50"] < .5 * r["A_size"] for r in rows]}
    ab, bc = bits(ah), bits(bh)
    paired = {k: discordance(ab[k], bc[k]) for k in ab}
    for key, source in (("C4_recall", "C1"), ("C4_spurious", "C2")):
        old = [i for i, r in enumerate(ah) if r["oldest"]]
        paired[key] = discordance([ab[source][i] for i in old], [bc[source][i] for i in old])
    decision = classify(original["index"], null["index"])
    valid = all(v is not False for row in (original, null) for v in row["protocol"].values())
    if not valid:
        decision["label"] = "PROTOCOL FAILURE"
    elif original["M"] != 1000:
        decision["label"] = "LOW-LOAD DESCRIPTIVE"
    safe = decision["delta"]["C1"] >= -.03 - EPS and decision["delta"]["C4_recall"] >= -.03 - EPS
    decision["low_load_material_gain"] = bool(original["M"] == 500 and safe and
        (decision["delta"]["C2"] >= .05 - EPS or decision["delta"]["joint_index"] >= .05 - EPS))
    content = {}
    for store in ("inherited", "assigned_A"):
        def successes(compact):
            tab = compact["content"][store]
            data = [dict(zip(tab["columns"], r)) for r in tab["rows"]]
            return [data[r["cue_id"]]["missing"] >= 40 and data[r["cue_id"]]["total"] - data[r["cue_id"]]["item"] < 10 for r in ah]
        delta = null["content"][store]["joint"] - original["content"][store]["joint"]
        content[store] = dict(delta_S2=delta, label="MATERIAL GAIN" if delta >= .10 - EPS else
            "MATERIAL LOSS" if delta <= -.10 + EPS else "INTERMEDIATE/SMALL CHANGE",
            paired=discordance(successes(a), successes(b)))
    ed = np.asarray(null["learning"]["eligibility_block_counts"]) - np.asarray(original["learning"]["eligibility_block_counts"])
    coins_a = np.asarray(original["learning"]["coin_draws_per_episode"])
    coins_b = np.asarray(null["learning"]["coin_draws_per_episode"])
    return dict(M=original["M"], decision=decision, paired=paired, content=content,
                eligibility_block_count_differences=ed.tolist(),
                eligibility_block_max_abs=np.max(np.abs(ed), axis=1).tolist(),
                coin_draw_counts_equal=bool(np.array_equal(coins_a, coins_b)),
                cumulative_coin_draw_differences=np.cumsum(coins_b - coins_a).tolist(),
                exact_A_and_test_schedule=True, scope="two-seed descriptive contrast, no causal partition or capability gate")


def git_read(*args):
    proc = subprocess.run(["git", "-C", str(record.REPO), *args], capture_output=True)
    if proc.returncode:
        raise IntegrityError("required committed source unavailable: " + " ".join(args))
    return proc.stdout


def source_manifest():
    hashes = {}
    for path in SOURCES:
        raw = (record.REPO / path).read_bytes()
        require(raw == git_read("show", "HEAD:" + path), "uncommitted source: " + path)
        if path in INHERITED:
            require(raw == git_read("show", BASELINE + ":" + path), "inherited source changed: " + path)
        hashes[path] = hashlib.sha256(raw).hexdigest()
    require((record.REPO / CONTRACT_PATH).read_bytes() == git_read("show", CONTRACT_COMMIT + ":" + CONTRACT_PATH),
            "frozen contract changed")
    return dict(commit=git_read("rev-parse", "HEAD").decode().strip(), files=hashes,
                code_sha256=hashlib.sha256(r1.json_bytes(hashes)).hexdigest(), contract_commit=CONTRACT_COMMIT)


def reserve(seed, source, process_start):
    """Filesystem lock works across isolated process namespaces; only two fixed seed claims exist."""
    import fcntl
    root = record.cache_dir("p2r2")
    with (root / "resource-lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        window = root / "resource-window.json"
        if not window.exists():
            write_json(window, dict(start_unix=process_start, start=record.now(), source=source,
                                   max_workers=2, global_max_simulations=4))
        info = json.loads(window.read_text())
        require(info["source"]["code_sha256"] == source["code_sha256"], "resource window belongs to another source version")
        budget = Budget(info["start_unix"])
        budget.check(new_stage=True)
        claim = root / f"seed{seed}.started.json"
        if claim.exists():
            raise IntegrityError("seed already started; replacement/rerun is not authorized")
        write_json(claim, dict(seed=seed, source=source, start_unix=time.time(), pid=os.getpid()))
    return budget


def shared_parity(source, budget):
    """One frozen small validation, shared by the two workers without extra full trajectories."""
    import fcntl
    root = record.cache_dir("p2r2")
    with (root / "parity-lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        budget.check(new_stage=True)
        path = root / "original-sham-parity.json"
        if path.exists():
            result = json.loads(path.read_text())
            require(result["code_sha256"] == source["code_sha256"] and result["parity"]["passed"],
                    "shared parity belongs to another source or failed")
            return result["parity"]
        result = parity_check()
        write_json(path, dict(code_sha256=source["code_sha256"], parity=result))
        return result


def required_stages():
    return ["validation", "structure/F10", "structure/F40"] + [
        f"{arm}/{M}/{stage}" for arm in ARMS for M in LOADS
        for stage in ("learning", "index", "inherited", "assigned_A")] + [f"paired/{M}" for M in LOADS]


def run(seed, log=print):
    process_start = time.time()
    if seed not in SEEDS:
        raise ValueError("P2-R2 uses only seeds 103 and 104")
    source = source_manifest()  # Refuses before code commit or with modified inherited sources.
    budget = reserve(seed, source, process_start)
    cache = record.cache_dir("p2r2", f"seed{seed}")
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    meta = dict(experiment="P2-R2", schema=1, seed=seed, source=source, runtime=record.runtime(),
                contract_path=CONTRACT_PATH, full_size=True, start_unix=budget.start,
                source_mechanism="unchanged inherited E3; input adapter only")
    stage_receipts = {}
    def emit(kind, **values):
        record.append(dict(meta, kind=kind, timestamp=record.now(), **values), RESULTS)
        if kind == "original_sham_parity":
            stage_receipts["validation"] = values["parity"]
        elif kind == "structure":
            stage_receipts[f"structure/F{values['F']}"] = values["result"]["portable"]
        elif kind in ("learned_checkpoint", "index_load", "content_load"):
            stage = {"learned_checkpoint": "learning", "index_load": "index"}.get(kind, values.get("store"))
            stage_receipts[f"{values['arm']}/{values['M']}/{stage}"] = values.get("portable", values.get("raw"))
        elif kind == "paired_load":
            stage_receipts[f"paired/{values['result']['M']}"] = values["portable"]
    emit("seed_started", cache=str(cache))
    completed, structural, pairs = {}, {}, {}
    main, current, status = None, "validation", "COMPLETE"
    progress = dict(stage=current)
    try:
        with hard_deadline(budget):
            budget.check(new_stage=True)
            parity = shared_parity(source, budget)
            emit("original_sham_parity", parity=parity)
            current = "F10 preprocessing"
            original, null, structure = preprocess(seed, 10, cache, EVIDENCE, budget, meta, log, progress)
            structural["F10"] = structure
            emit("structure", F=10, result=structure)
            if not all(v["decision"]["ok"] for v in structure["loads"].values()):
                status = "STRUCTURAL CONTRAST UNCERTAIN"
            else:
                current = "F40 structural-only preprocessing"
                _, _, transfer = preprocess(seed, 40, cache, EVIDENCE, budget, meta, log, progress)
                structural["F40"] = transfer
                emit("structure", F=40, result=transfer)
                for arm, rows in (("ORIGINAL", original), ("DEGREE_NULL", null)):
                    budget.check(new_stage=True)
                    main = e3.E3(dict(CFG), seed)
                    main._pat = MatrixItems(rows, main.c["m"])
                    for M in LOADS:
                        budget.check(new_stage=True)
                        current = f"{arm}/{M}/learning"
                        progress["stage"] = current
                        progress.pop("evaluation", None)
                        emit("load_started", arm=arm, M=M)
                        t = time.time()
                        with bounded_steps(main, budget):
                            main.learn(M)
                        learning_s = time.time() - t
                        require(np.array_equal(np.asarray(main.items), rows[:M]), "learner did not consume prescribed matrix prefix")
                        require(main._pat.k == M, "adapter episode counter")
                        stem = f"seed{seed}-{arm}-M{M}"
                        learned = learned_save(cache / (stem + "-learned.npz"), main, dict(meta, arm=arm, M=M))
                        emit("learned_checkpoint", arm=arm, M=M, raw=learned, learning_s=learning_s)
                        current = f"{arm}/{M}/evaluation and replay"
                        result = evaluate_load(main, M, cache, EVIDENCE, dict(meta, arm=arm), budget, learned, emit, progress)
                        result["timing"]["learning_s"] = learning_s
                        completed[f"{arm}/{M}"] = result
                        emit("load_complete", result=result)
                        log(f"seed {seed} {arm} M={M}: C1={result['index']['C1']:.3f} C2={result['index']['C2']:.3f}")
                        if arm == "DEGREE_NULL":
                            pair = paired_evidence(completed[f"ORIGINAL/{M}"], result)
                            pairs[str(M)] = pair
                            portable = write_json(EVIDENCE / f"seed{seed}-M{M}-paired.json", dict(meta, **pair))
                            emit("paired_load", result=pair, portable=portable)
    except (Exception, KeyboardInterrupt) as exc:
        status = "PARTIAL" if isinstance(exc, (ResourceStop, KeyboardInterrupt)) else "INVALID"
        partial, checkpoint_error = None, None
        try:
            if time.time() >= budget.start + 1200:
                raise ResourceStop("hard deadline reached; emergency metadata only")
            with hard_deadline(budget, checkpoint=True):
                partial = checkpoint_interrupted(main, progress, exc, cache / "interrupted-state.npz", meta)
        except (Exception, KeyboardInterrupt) as save_exc:
            checkpoint_error = repr(save_exc)
        emit("interrupted", status=status, stage=progress["stage"], error=repr(exc),
             started_items=len(main.items) if main is not None else None,
             eligibility_sets=len(main.E) if main is not None else None,
             partial_checkpoint=partial, checkpoint_error=checkpoint_error,
             completed_stages=stage_receipts, completed_loads=list(completed),
             note="forensic partial state only; no replacement, resumption or shortened run")
        log(f"seed {seed} {status}: {exc!r}")
    missing = [f"{a}/{M}" for a in ARMS for M in LOADS if f"{a}/{M}" not in completed]
    final = dict(status=status, loads=completed, structural=structural, pairs=pairs, missing_loads=missing,
                 missing_paired_loads=[M for M in LOADS if str(M) not in pairs], wall_s=time.time() - budget.start,
                 completed_stages=stage_receipts, missing_stages=[s for s in required_stages() if s not in stage_receipts],
                 label=pairs.get("1000", {}).get("decision", {}).get("label"),
                 scope="reported explanation test; no Stage 1 gate or learned-mechanism claim")
    emit("seed_complete", result=final)
    return final


def summarize(records):
    finals = [r for r in records if r.get("kind") == "seed_complete" and r.get("experiment") == "P2-R2"]
    complete = {r["seed"]: r["result"] for r in finals}
    duplicate = len(finals) != len(complete)
    if duplicate or any(x["status"] == "INVALID" for x in complete.values()):
        status = "INVALID"
    elif any(x["status"] == "STRUCTURAL CONTRAST UNCERTAIN" for x in complete.values()):
        status = "STRUCTURAL CONTRAST UNCERTAIN"
    elif set(complete) != set(SEEDS) or any(x["status"] != "COMPLETE" or x["missing_loads"] or x["missing_paired_loads"]
            or x.get("missing_stages", ["stage inventory absent"]) for x in complete.values()):
        status = "PARTIAL"
    else:
        status = "COMPLETE"
    labels = {str(s): x.get("label") for s, x in complete.items()}
    fractions = [x.get("pairs", {}).get("1000", {}).get("decision", {}).get("C2_bar_deficit_removed") for x in complete.values()]
    return dict(status=status, seed_labels=labels, replicated_label=next(iter(labels.values()))
                if status == "COMPLETE" and len(set(labels.values())) == 1 else None,
                half_bar_deficit_removed_on_both=bool(status == "COMPLETE" and len(fractions) == 2
                    and all(x is not None and x >= .5 for x in fractions)),
                missing_seeds=sorted(set(SEEDS) - set(complete)), scope="descriptive n=2; not a capability gate")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    runner = commands.add_parser("run")
    runner.add_argument("--seed", type=int, required=True, choices=SEEDS)
    commands.add_parser("summary")
    args = parser.parse_args(argv)
    if args.command == "run":
        result = run(args.seed, log=lambda x: print(f"[{record.now()}] {x}", flush=True))
        return 0 if result["status"] == "COMPLETE" else 1
    rows = [json.loads(x) for x in RESULTS.read_text().splitlines() if x.strip()] if RESULTS.exists() else []
    result = summarize(rows)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
