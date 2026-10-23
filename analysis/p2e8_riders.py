"""P2-E8 riders and screen-E classes, reported only.

Riders: P2-R1's R_3, R_1, size-matched-random and anti-selected feedback stores built from gate_off's
persisted continuation counts by analysis/p2e7_riders.py's builders and readout, void unless the run's
gate_off == baseline forward-store check passed. Unlike P2-E7's wrapper (erratum 12), every record
carries this riders run's own source manifest, git commit and runtime; the screen's provenance is kept
under `screen_*` keys. Screen-E classes: the pinned offline `spurious_classes` on every F10 arm's
persisted test raster, state and first engagement.

    python -m plant2.experiments.p2_e8_graded_error riders --seed 123
"""
import os
from pathlib import Path

import numpy as np

from analysis import offline_screens_20261022 as osx
from analysis import p2e7_riders as r7
from analysis import p2r1_replay as r1
from plant2 import evidence, record
from plant2.experiments import p2_e7_error_gated as e7
from plant2.experiments import p2_e8_graded_error as e8

STORES = r7.STORES


def own_meta(row):
    source = e8.source_manifest()
    return dict(experiment="P2-E8", schema=1, attempt=row["attempt"], seed=row["seed"], full_size=row.get("full_size"),
                contract_commit=e8.FROZEN["contract_commit"], predictions=e8.FROZEN["predictions"],
                source=source, git_commit=source["commit"],
                runtime=dict(record.runtime(), openblas_num_threads=os.environ.get("OPENBLAS_NUM_THREADS")),
                screen_git_commit=row.get("git_commit"), screen_code_sha256=row.get("source", {}).get("code_sha256"),
                screen_authorization=row.get("authorization"))


def _first_engagement(records, attempt, arm):
    for r in records:
        if (r.get("kind"), r.get("attempt"), r.get("condition"), r.get("arm")) == ("structural_check", attempt, "F10", arm):
            return {int(f): v for f, v in r["gate"]["first_engagement_by_family"].items()}, "structural_check"
    return {f: None for f in range(e8.FROZEN["conditions"]["F10"]["F"])}, "absent (no gate log on this arm)"


def screen_e_classes(load, records, attempt):
    raw = evidence.load_npz_artifact(load["raw"])
    state = evidence.load_npz_artifact(load["state"])
    portable = evidence.load_json_artifact(load["portable"])
    resp = osx.responders_from_raster(raw["raster_ticks"], e7._ragged(raw, "raster_cells"), raw["cue_index"].tolist(),
                                      raw["cue_onset"].tolist(), raw["cue_kind"].tolist())
    first, origin = _first_engagement(records, attempt, load["arm"])
    out = osx.spurious_classes(portable["index_cues"], e7._ragged(state, "A"), resp, first,
                               F=e8.FROZEN["conditions"]["F10"]["F"], return_cells=False)
    summary = {k: v for k, v in out.items() if k != "per_cue"}
    summary.update(first_engagement={str(f): v for f, v in sorted(first.items())}, first_engagement_source=origin)
    return summary, out["per_cue"]


def run(seed, results_path=e8.RESULTS, evidence_dir=e8.EVIDENCE, attempt=None, log=print):
    records = e8.read_records(results_path)
    screens = [r for r in records if r.get("kind") == "seed_screen" and r.get("seed") == seed
               and (attempt is None or r.get("attempt") == attempt)]
    if not screens:
        raise ValueError(f"no seed_screen for seed {seed}{'' if attempt is None else ' attempt ' + attempt}")
    row = screens[-1]
    meta = own_meta(row)
    loads = [r["load"] for r in records if r.get("kind") == "load" and r.get("attempt") == row["attempt"]
             and r["load"]["condition"] == "F10"]
    gate_off = {x["M"]: x for x in loads if x["arm"] == "gate_off"}
    sink = e7.Sink(evidence_dir, seed, "riders")
    sink.journal.append(dict(kind="riders_started", attempt=row["attempt"]))
    out = []
    for M in sorted(gate_off) or [None]:
        check = row.get("cross_arm", {}).get(f"F10/{M}", {}).get("gate_off_equals_baseline")
        value = dict(meta, kind="rider", timestamp=record.now(), M=M, void=not (M and check))
        if value["void"]:
            value["reason"] = "gate_off load missing" if M is None else "gate_off forward store differs from the baseline's"
        else:
            load = gate_off[M]
            z = evidence.load_npz_artifact(load["state"])
            raster, n_ticks, cues, tmeta = e7.read_test_raw(evidence.load_npz_artifact(load["raw"]))
            e7.require(r1.raster_digest(raster, n_ticks, tmeta["cfg"]["n"]) == load["raster_sha256"], "persisted test raster digest")
            cfg, writers, stores = r7.rider_stores(z, seed, M)
            summaries = {name: r7.read_store(cfg, raster, n_ticks, cues, stores[name]) for name in STORES}
            value.update(index={k: load["index"][k] for k in ("C1", "C2", "C3", "C4_recall", "C4_spurious", "joint_index")},
                         stores=summaries, mean_writers={n: float(np.mean([w.size for w in writers[n]])) for n in STORES},
                         source_state=load["state"], source_raw=load["raw"], control_stream=e8.STREAMS["rider_control"])
            value["portable"] = sink.json(Path(evidence_dir) / f"{row['attempt']}-riders-M{M}.json",
                                          dict(value, writers={n: [w.tolist() for w in writers[n]] for n in STORES}))
            log(f"riders M={M}: " + ", ".join(f"{n} joint={s['joint']:.3f}" for n, s in summaries.items()))
        record.append(value, results_path)
        out.append(value)
    for load in loads:
        summary, per_cue = screen_e_classes(load, records, row["attempt"])
        value = dict(meta, kind="screen_e_classes", timestamp=record.now(), condition="F10", arm=load["arm"], M=load["M"],
                     label="reported only; decides nothing", summary=summary, source_state=load["state"],
                     source_raw=load["raw"], source_portable=load["portable"])
        value["portable"] = sink.json(Path(evidence_dir) / f"{row['attempt']}-screen-e-{load['arm']}-M{load['M']}.json",
                                      dict(value, per_cue=per_cue))
        log(f"screen-E F10 {load['arm']} M={load['M']}: late {summary['same_family_late_per_cue']}, "
            f"early {summary['same_family_early_per_cue']}, other {summary['other_family_only_per_cue']}")
        record.append(value, results_path)
        out.append(value)
    sink.journal.append(dict(kind="riders_finished", records=len(out)))
    check = e7.verification_record("riders", sink.manifest.entries, sink.journal.path)
    record.append(dict(meta, kind="evidence_verification", timestamp=record.now(), **check), results_path)
    return out
