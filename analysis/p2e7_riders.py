"""P2-E7 riders: P2-R1's R_3, R_1, size-matched-random and anti-selected feedback stores on the baseline trajectory.

Reported only. Built after the run, from persisted evidence alone: gate_off's per-episode continuation
spike counts and eligible lines (its forward store equals the baseline's, so its memory dynamics are the
baseline's), read through the frozen readout on gate_off's persisted test rasters and cues. Void when the
gate_off == baseline forward-store check of the run did not pass. Store construction is P2-R1's
(`analysis.p2r1_replay.controls` with stream 30, items 1-based, and `p2_e5_structured.store_from`).

    python -m plant2.experiments.p2_e7_error_gated riders --seed 121
"""
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from analysis import p2r1_replay as r1
from plant2 import evidence, record
from plant2.experiments import p2_e3_completion as e3
from plant2.experiments import p2_e5_structured as e5
from plant2.experiments import p2_e7_error_gated as e7
from plant2.readout import replay

STORES = ("R3", "R1", "random", "anti")
META_KEYS = ("experiment", "schema", "attempt", "seed", "source", "git_commit", "runtime", "full_size",
             "contract_commit", "predictions", "authorization")


def rider_stores(z, seed, M):
    """P2-R1's writer selection per item (1-based keys on stream 30) and the stores they write onto E(x)."""
    cfg = json.loads(str(z["metadata_json"]))["cfg"]
    counts = np.asarray(z["cont_counts"][:M], np.int64)
    cells = [np.flatnonzero(c).astype(np.int64) for c in counts]
    R = e7._ragged(z, "R")[:M]
    e7.require(all(np.array_equal(a, b) for a, b in zip(cells, R)), "continuation counts disagree with the persisted R")
    ns = SimpleNamespace(c=cfg, E=e7._ragged(z, "E")[:M], cont_cells=cells, cont_counts=[c[x] for c, x in zip(counts, cells)])
    writers = {name: [] for name in STORES}
    for i in range(M):
        selected = r1.controls(ns.cont_cells[i], ns.cont_counts[i], seed, i + 1)
        selected["R1"] = ns.cont_cells[i]
        for name in STORES:
            writers[name].append(selected[name])
    stores = {name: e5.store_from(ns, M, cells=writers[name]) for name in STORES}
    e7.require(np.array_equal(stores["R1"].keys, z["feedback_keys"]), "R1 rider store differs from gate_off's feedback store")
    return cfg, writers, stores


def read_store(cfg, raster, n_ticks, cues, store):
    indptr, post = store.csr()
    res, latency, oow = replay(raster, n_ticks, indptr, post, cfg["m"], np.array([r1.J_FB]), np.array([r1.G]), cues,
                              window=75, short=50, span=cfg["t_cue"] + cfg["t_gap"])
    summary = {k: v for k, v in e3.score(res, latency, cues, cfg["n_old"], 1)[0].items() if k != "passes"}
    summary.update(counts=r1.content_counts(res, cues, cfg["n_old"]), out_of_window_spikes=int(oow[0]),
                   store_size=store.size, store_sha256=r1.sha_array(store.keys))
    return summary


def run(seed, results_path=e7.RESULTS, evidence_dir=e7.EVIDENCE, attempt=None, log=print):
    records = e7.read_records(results_path)
    screens = [r for r in records if r.get("kind") == "seed_screen" and r.get("seed") == seed
               and (attempt is None or r.get("attempt") == attempt)]
    if not screens:
        raise ValueError(f"no seed_screen for seed {seed}{'' if attempt is None else ' attempt ' + attempt}")
    row = screens[-1]
    meta = {k: row[k] for k in META_KEYS if k in row}
    loads = {r["load"]["M"]: r["load"] for r in records if r.get("kind") == "load" and r.get("attempt") == row["attempt"]
             and (r["load"]["condition"], r["load"]["arm"]) == ("F10", "gate_off")}
    sink = e7.Sink(evidence_dir, seed, "riders")
    sink.journal.append(dict(kind="riders_started", attempt=row["attempt"]))
    out = []
    for M in sorted(loads) or [None]:
        check = row.get("cross_arm", {}).get(f"F10/{M}", {}).get("gate_off_equals_baseline")
        value = dict(meta, kind="rider", timestamp=record.now(), M=M, void=not (M and check))
        if value["void"]:
            value["reason"] = "gate_off load missing" if M is None else "gate_off forward store differs from the baseline's"
        else:
            load = loads[M]
            z = evidence.load_npz_artifact(load["state"])
            raster, n_ticks, cues, tmeta = e7.read_test_raw(evidence.load_npz_artifact(load["raw"]))
            e7.require(r1.raster_digest(raster, n_ticks, tmeta["cfg"]["n"]) == load["raster_sha256"], "persisted test raster digest")
            cfg, writers, stores = rider_stores(z, seed, M)
            summaries = {name: read_store(cfg, raster, n_ticks, cues, stores[name]) for name in STORES}
            value.update(index={k: load["index"][k] for k in ("C1", "C2", "C3", "C4_recall", "C4_spurious", "joint_index")},
                         stores=summaries, mean_writers={n: float(np.mean([w.size for w in writers[n]])) for n in STORES},
                         source_state=load["state"], source_raw=load["raw"], control_stream=e7.STREAMS["rider_control"])
            value["portable"] = sink.json(Path(evidence_dir) / f"{row['attempt']}-riders-M{M}.json",
                                          dict(value, writers={n: [w.tolist() for w in writers[n]] for n in STORES}))
            log(f"riders M={M}: " + ", ".join(f"{n} joint={s['joint']:.3f}" for n, s in summaries.items()))
        record.append(value, results_path)
        out.append(value)
    sink.journal.append(dict(kind="riders_finished", records=len(out)))
    check = e7.verification_record("riders", sink.manifest.entries, sink.journal.path)
    record.append(dict(meta, kind="evidence_verification", timestamp=record.now(), **check), results_path)
    return out
