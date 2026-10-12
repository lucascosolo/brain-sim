"""P2-R1 reported five-writer diagnostic; no gates are reopened.

Run from the repository root with ``python3 -m analysis.p2r1_replay
--regime correlated --seed 44`` (or ``--regime duty --seed 90``).
All content arms start with a fresh reconstruction layer and share one settled
P2-E3 memory raster. The duty timeline itself retains its inherited live rec.
"""
import argparse
import copy
import hashlib
import json
import re
import time
import uuid
from pathlib import Path

import numpy as np

from plant2 import record
from plant2.experiments import p2_e1_btsp as e1
from plant2.experiments import p2_e3_completion as e3
from plant2.experiments import p2_e4_online as e4
from plant2.experiments import p2_e5_structured as e5
from plant2.readout import replay

CONTRACT_PATH = "docs/plant2/P2-R1-takeover-replay.md"
CONTRACT_COMMIT = "8002427"
RESULTS = record.REPO / "bench/results/p2r1.jsonl"
EVIDENCE = record.REPO / "bench/results/p2r1"
WRITERS = ("R1", "A", "R3", "random", "anti")
CONTROL_STREAM, RANDOM_KIND, ANTI_KIND = 30, 0, 1
J_FB, G, LOADS = 2.80, 0.3, (500, 1000)


class DutyCapture(e5.CaptureMixin, e4.Online):
    """Independent E4 duty timeline, with read-only inherited learning capture."""

    def __init__(self, cfg, seed):
        super().__init__(cfg, seed, post=cfg["duty_post"], bg_key=(e4.ARMS, e4.ARM_DUTY))
        self._init_capture()
        self.slot_mem, self.slot_rec = [], []

    def run_slot(self, s, bg, sl, post):
        result = super().run_slot(s, bg, sl, post)
        fm, fr = result[:2]
        # Sparse first-spike inputs permit independent rescoring of online slots.
        self.slot_mem.append(np.flatnonzero(fm >= 0) * self.c["slot"] + fm[fm >= 0])
        self.slot_rec.append(np.flatnonzero(fr >= 0) * self.c["slot"] + fr[fr >= 0])
        return result


def controls(cells, counts, seed, item):
    """Select R3 and count-matched controls without access to assigned cells A.

    Item is 1-based. Uniform selection uses kind 0; lowest-count selection uses
    kind 1's permutation followed by a stable count sort, independently per item.
    """
    cells, counts = np.asarray(cells, np.int64), np.asarray(counts, np.int64)
    if cells.ndim != 1 or counts.shape != cells.shape:
        raise ValueError("cells/counts must be matching vectors")
    if np.any(counts < 1) or np.unique(cells).size != cells.size:
        raise ValueError("controls require unique observed responders and positive counts")
    r3 = cells[counts >= 3]
    k = r3.size
    random = e1.stream(seed, CONTROL_STREAM, item, RANDOM_KIND).choice(cells, k, replace=False)
    tie_order = e1.stream(seed, CONTROL_STREAM, item, ANTI_KIND).permutation(cells.size)
    anti_order = tie_order[np.argsort(counts[tie_order], kind="stable")]
    return dict(R3=np.sort(r3), random=np.sort(random), anti=np.sort(cells[anti_order[:k]]))


def five_stores(main, M):
    if not e5.capture_ok(main, M):
        raise ValueError("captured R1 differs from inherited responders")
    writers = {name: [] for name in WRITERS}
    for i in range(M):
        selected = controls(main.cont_cells[i], main.cont_counts[i], main.seed, i + 1)
        selected.update(R1=main.cont_cells[i], A=main.A[i])
        for name in WRITERS:
            writers[name].append(selected[name])
        if any(selected[n].size != selected["R3"].size or not np.isin(selected[n], selected["R1"]).all()
               for n in ("random", "anti")):
            raise ValueError("writer control cardinality/subset check failed")
    stores = {name: e5.store_from(main, M, cells=writers[name]) for name in WRITERS}
    if not np.array_equal(stores["R1"].keys, main.fb.keys) or not e4.fb_union_ok(main):
        raise ValueError("inherited feedback union differs from captured R1 union")
    if not np.array_equal(stores["A"].keys, main.fb_plateau.keys):
        raise ValueError("assigned-cell union differs from inherited plateau store")
    return writers, stores


def jsonable(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    return value


def json_bytes(value):
    return (json.dumps(jsonable(value), sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def sha_array(values):
    """Portable little-endian int64 digest, including shape."""
    a = np.ascontiguousarray(values, dtype="<i8")
    return hashlib.sha256(json_bytes(list(a.shape)) + a.tobytes()).hexdigest()


def raster_digest(raster, n_ticks, n):
    h = hashlib.sha256(json_bytes(dict(n_ticks=n_ticks, n=n)))
    for tick in sorted(raster):
        a = np.asarray(raster[tick], dtype="<i8")
        h.update(np.asarray([tick, a.size], dtype="<i8").tobytes())
        h.update(a.tobytes())
    return h.hexdigest()


def live_digest(e):
    """Assert copied evaluation/store swaps leave the main line and RNGs intact."""
    h = hashlib.sha256()
    for a in (e.store.keys, e.fb.keys, e.fb_plateau.keys, e.inp.rate_hz):
        h.update(np.ascontiguousarray(a).tobytes())
    for p in e.net.populations:
        for a in (p.v, p.vbar, p.t_last, p.ring):
            h.update(np.ascontiguousarray(a).tobytes())
    for p in e.net.projections:
        for name in ("indptr", "post", "weight", "delay"):
            h.update(np.asarray(getattr(p, name, [])).tobytes())
    h.update(json_bytes(dict(t=e.net.t, items=len(e.items), rngs=[g.bit_generator.state for g in
                        (e._pat, e._learn_in, e._plat, e._coin)])))
    return h.hexdigest()


def writer_evidence(main, writers):
    """A is evaluation ground truth only; retain integer numerators per item."""
    out = {}
    for name, selections in writers.items():
        rows = [[i + 1, int(w.size), int(main.A[i].size), int(np.intersect1d(w, main.A[i]).size)]
                for i, w in enumerate(selections)]
        totals = np.asarray(rows, np.int64)[:, 1:].sum(0)
        out[name] = dict(columns=["item_1based", "writers", "assigned", "intersection"], rows=rows,
                         precision_micro=float(totals[2] / totals[0]) if totals[0] else None,
                         recall_micro=float(totals[2] / totals[1]) if totals[1] else None,
                         mean_writers=float(totals[0] / len(rows)),
                         precision_macro=e4.frac([r[3] / r[1] for r in rows if r[1]]),
                         recall_macro=e4.frac([r[3] / r[2] for r in rows if r[2]]))
    return out


def cue_evidence(e, cues, out):
    """Portable index counts independent of feedback, including all inherited cues."""
    half, novel, full = 0, 0, 0
    rows = []
    for i, q in enumerate(cues):
        d = dict(cue_id=i, kind=q["kind"], index_0based=int(q["index"]), onset=int(q["onset"]),
                 oldest=q["kind"] == "half" and int(q["index"]) < e.c["n_old"])
        if q["kind"] == "half":
            d.update(A_size=out["A_size"][half], recall25=out["recall"][25][half],
                     recall50=out["recall"][50][half], recall100=out["recall"][100][half],
                     spurious50=out["spurious"][half], latency_half_ms=out["latency_half"][half])
            half += 1
        elif q["kind"] == "novel":
            d["ignition50"] = out["ignition"][novel]
            novel += 1
        else:
            d["recall50"] = out["recall_full50"][full]
            d["latency_full_ms"] = out["latency_full"][full]
            full += 1
        rows.append(d)
    return rows


def content_counts(res, cues, n_old):
    half = np.asarray([q["kind"] == "half" for q in cues])
    novel = np.asarray([q["kind"] == "novel" for q in cues])
    joint = (res["missing"][:, 0] >= e3.JOINT_MISSING) & (
        res["total"][:, 0] - res["item"][:, 0] < e3.JOINT_INTRUSIONS)
    return dict(joint=int(joint[half].sum()), n_half=int(half.sum()),
                D3=int((res["total"][novel, 0] < e3.NOVEL_LINES).sum()), n_novel=int(novel.sum()),
                D4=int(joint[half][:n_old].sum()), n_old=min(n_old, int(half.sum())))


def index_counts(out, c):
    recall, spur, A = np.array(out["recall"][50]), np.array(out["spurious"]), np.array(out["A_size"])
    old = np.array(out["cued"]) < c["n_old"]
    c1, c2 = recall >= e1.BARS["recall"], spur < e1.BARS["spurious_of_A"] * A
    c3 = np.array(out["ignition"]) < e1.BARS["ignition_of_meanA"] * out["criteria"]["mean_A"]
    return dict(C1=int(c1.sum()), C2=int(c2.sum()), C3=int(c3.sum()),
                C4_recall=int(c1[old].sum()), C4_spurious=int(c2[old].sum()),
                n_half=int(c1.size), n_novel=int(c3.size), n_old=int(old.sum()))


def pack_ragged(payload, name, arrays):
    lengths = np.asarray([len(a) for a in arrays], np.int64)
    payload[name + "_offsets"] = np.concatenate(([0], np.cumsum(lengths)))
    payload[name] = np.concatenate(arrays).astype(np.int64) if arrays else np.empty(0, np.int64)


def file_info(path, relative=False):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return dict(path=str(path.relative_to(record.REPO) if relative else path), sha256=h.hexdigest(), bytes=path.stat().st_size)


def save_raw(path, main, M, raster, n_ticks, cues, out, writers, stores, meta):
    """Lossless NPZ, no pickle: all inputs needed for replay and writer rebuilding."""
    payload = dict(metadata_json=np.asarray(json_bytes(dict(meta, cfg=main.c, n_ticks=n_ticks, M=M)).decode()),
                   memory_out_json=np.asarray(json_bytes(out).decode()), forward_keys=main.store.keys,
                   raster_ticks=np.asarray(sorted(raster), np.int64),
                   cue_kind=np.asarray([q["kind"] for q in cues]),
                   cue_index=np.asarray([q["index"] for q in cues], np.int64),
                   cue_onset=np.asarray([q["onset"] for q in cues], np.int64))
    pack_ragged(payload, "raster_cells", [raster[t] for t in sorted(raster)])
    for key in ("item", "cue", "missing", "other_missing"):
        pack_ragged(payload, "cue_" + key, [q[key] for q in cues])
    for key in ("items", "A", "E", "R", "cont_cells", "cont_counts", "cont_first", "learn_raster"):
        pack_ragged(payload, "learn_" + key, getattr(main, key)[:M])
    for name in WRITERS:
        pack_ragged(payload, "writer_" + name, writers[name])
        payload["feedback_" + name] = stores[name].keys
    if isinstance(main, DutyCapture):
        payload["online_log_json"] = np.asarray(json_bytes(main.log).decode())
        pack_ragged(payload, "online_slot_mem", main.slot_mem)
        pack_ragged(payload, "online_slot_rec", main.slot_rec)
    with Path(path).open("xb") as f:
        np.savez_compressed(f, **payload)
    return file_info(Path(path))


def evaluate_load(main, M, raw_path, compact_path, meta, log=print):
    before = live_digest(main)
    writers, stores = five_stores(main, M)
    e = copy.deepcopy(main)
    # Exactly the settled P2-E3 portion of E4.twin_A; no extra twin_B or
    # carried-rec mismatch arm. Swaps only enter replay(), never a live net.
    out, raster, n_ticks, onsets, drift = e3.run_phase(e, M)
    cues = e3.build_cues(e, M, onsets)
    rdigest = raster_digest(raster, n_ticks, main.c["n"])
    index_sha = hashlib.sha256(json_bytes(out)).hexdigest()
    raw = save_raw(raw_path, main, M, raster, n_ticks, cues, out, writers, stores, meta)
    compact = dict(meta, M=M, raster_sha256=rdigest, memory_out_sha256=index_sha,
                   rec_initial_state="fresh rest; no pending input; not refractory",
                   readout=dict(J_fb=J_FB, g=G, window_mem=50, window_rec=75),
                   index_cues=cue_evidence(e, cues, out), writers=writer_evidence(main, writers), content={})
    arms = {}
    for name in WRITERS:
        indptr, post = stores[name].csr()
        res, latency, oow = replay(raster, n_ticks, indptr, post, main.c["m"], np.array([J_FB]), np.array([G]), cues,
                                  window=75, short=50, span=main.c["t_cue"] + main.c["t_gap"])
        arm = {k: v for k, v in e3.score(res, latency, cues, main.c["n_old"], 1)[0].items() if k != "passes"}
        if raster_digest(raster, n_ticks, main.c["n"]) != rdigest or hashlib.sha256(json_bytes(out)).hexdigest() != index_sha:
            raise ValueError("feedback replay changed the shared memory raster or index")
        arms[name] = dict(arm, counts=content_counts(res, cues, main.c["n_old"]),
                          store_size=stores[name].size, store_sha256=sha_array(stores[name].keys),
                          raster_sha256=rdigest, out_of_window_spikes=int(oow[0]))
        columns = list(res)
        compact["content"][name] = dict(columns=["cue_id"] + columns + ["latency_ms"],
            rows=[[i] + [int(res[k][i, 0]) for k in columns]
                  + [float(latency[i, 0]) if np.isfinite(latency[i, 0]) else None] for i in range(len(cues))])
        log(f"{meta['regime']} seed {main.seed} M={M} {name}: joint={arm['joint']:.3f}, D3={arm['D3']:.3f}, D4={arm['D4']:.3f}")
    if live_digest(main) != before:
        raise ValueError("settled evaluation or swap changed the live timeline")
    if not np.array_equal(e.store.keys, main.store.keys) or not np.array_equal(e.fb.keys, main.fb.keys):
        raise ValueError("settled evaluation changed a synaptic store")
    memory = {k: v for k, v in e3.memory_summary(out).items() if k != "gate_ok"}
    memory.update(counts=index_counts(out, main.c), mean_A=out["criteria"]["mean_A"])
    online = None
    if isinstance(main, DutyCapture):
        inherited = e4.block_criteria(main, M)
        # Full baseline per-slot evidence is retained; online content is observed
        # only for inherited R1 and is never assigned to the swap arms.
        compact["online_baseline_cues"] = main.log
        online = dict(n=inherited["n"], rates=inherited["rates"], per_kind=inherited["per_kind"],
                      slot_checks=inherited["slot_checks"], schedule_violations=e4.realised_audit(main, M))
    compact.update(memory=memory, summaries=arms, online_baseline=online, raw_replay=raw)
    with Path(compact_path).open("xb") as f:
        f.write(json_bytes(compact))
    evidence = file_info(Path(compact_path), relative=Path(compact_path).is_relative_to(record.REPO))
    return dict(M=M, memory=memory, arms=arms, online_baseline=online, drift_mv=list(drift),
                writer_summary={n: {k: v for k, v in x.items() if k not in ("rows", "columns")}
                                for n, x in compact["writers"].items()},
                forward_sha256=sha_array(main.store.keys), raster_sha256=rdigest,
                raw_replay=raw, per_cue_evidence=evidence,
                checks=dict(capture_R1_equal=True, inherited_union_equal=True, A_union_equal=True,
                            control_exact_subsets=True, same_raster_all_arms=True, index_unchanged=True,
                            live_timeline_unchanged=True, settled_stores_unchanged=True))


def run(regime, seed, loads=LOADS, results_path=RESULTS, evidence_dir=EVIDENCE, run_id=None, log=print, cfg=None):
    """Append progress immediately; preserve all completed checkpoints on failure."""
    if regime not in ("correlated", "duty"):
        raise ValueError("regime must be correlated or duty")
    if seed < 0 or not loads or tuple(sorted(set(loads))) != tuple(loads) or loads[0] < 1:
        raise ValueError("seed must be nonnegative and loads increasing positive integers")
    run_id = run_id or f"{regime}-s{seed}-{time.time_ns()}-{uuid.uuid4().hex[:8]}"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", run_id):
        raise ValueError("run id must be a simple filename component")
    evidence_dir = Path(evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    cache = record.cache_dir("p2r1", run_id)
    cfg = dict(e5.CONTRACT if regime == "correlated" else e4.CONTRACT) if cfg is None else dict(cfg)
    if cfg["window"] != 50 or cfg["rec_window"] != 75 or cfg["J_fb"] != J_FB or cfg["g"] != G:
        raise ValueError("P2-R1 readout/index windows and J/g are frozen")
    t0 = time.monotonic()
    meta = dict(experiment="P2-R1", schema=1, run_id=run_id, regime=regime, seed=seed,
                contract_path=CONTRACT_PATH, contract_commit=CONTRACT_COMMIT,
                contract_sha256=file_info(record.REPO / CONTRACT_PATH)["sha256"],
                driver_sha256=file_info(Path(__file__))["sha256"], git=record.git_state(), runtime=record.runtime(),
                config_digest=record.digest(cfg), requested_loads=list(loads),
                control_stream=dict(id=CONTROL_STREAM, item="1-based", random=RANDOM_KIND, anti=ANTI_KIND),
                scope="reported store-quality diagnostic; fresh rec replay; no Stage-1 or online-gate claim")
    # Exclusive reservation prevents accidental reuse even if an earlier run failed.
    with (cache / "attempt.json").open("xb") as f:
        f.write(json_bytes(meta))
    record.append(dict(meta, kind="replay_started", timestamp=record.now()), results_path)
    completed = {}
    current = None
    try:
        if regime == "correlated":
            gen = e5.FamilyGen(seed, cfg["m"], cfg["a"], 60, 10)
            main = e5.E5(cfg, seed, gen)
        else:
            main = DutyCapture(cfg, seed)
        for M in loads:
            current = M
            raw = cache / f"M{M}.npz"
            compact = evidence_dir / f"{run_id}-M{M}.json"
            record.append(dict(meta, kind="replay_load_started", M=M, timestamp=record.now(),
                               raw_path=str(raw), evidence_path=str(compact)), results_path)
            main.learn(M) if regime == "correlated" else main.run_to(M)
            value = evaluate_load(main, M, raw, compact, meta, log=log)
            completed[str(M)] = value
            record.append(dict(meta, kind="replay_load", timestamp=record.now(), load=value,
                               wall_s=round(time.monotonic() - t0, 2)), results_path)
    except (Exception, KeyboardInterrupt) as exc:
        record.append(dict(meta, kind="replay_incomplete", timestamp=record.now(), completed_loads=list(completed),
                           attempted_load=current, error=repr(exc), cache_path=str(cache),
                           wall_s=round(time.monotonic() - t0, 2)), results_path)
        raise
    final = dict(meta, kind="replay_complete", timestamp=record.now(), completed_loads=list(completed),
                 wall_s=round(time.monotonic() - t0, 2), loads=completed)
    record.append(final, results_path)
    return final


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--regime", choices=("correlated", "duty"), required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--loads", nargs="+", type=int, default=list(LOADS), choices=LOADS)
    parser.add_argument("--results", type=Path, default=RESULTS)
    parser.add_argument("--run-id")
    args = parser.parse_args(argv)
    run(args.regime, args.seed, loads=args.loads, results_path=args.results, run_id=args.run_id,
        log=lambda message: print(f"[{record.now()}] {message}", flush=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
