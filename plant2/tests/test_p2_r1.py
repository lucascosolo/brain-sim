"""Small P2-R1 checks; all written fixtures persist in the inherited cache run_dir."""
import hashlib
import json

import numpy as np
import pytest

from analysis import p2r1_replay as r1
from plant2.experiments import p2_e4_online as e4
from plant2.experiments import p2_e5_structured as e5


def tiny():
    return dict(e5.CONTRACT, m=160, n=100, f_q=0.05, n_old=2, n_rand=2, n_novel=2,
                settle=30, converge_window=10, acc_tau=200)


def test_controls_are_exact_observed_subsets_and_anti_uses_lowest_counts():
    cells = np.array([4, 11, 18, 22, 47, 50, 71])
    counts = np.array([1, 2, 7, 3, 1, 1, 4])
    got = r1.controls(cells, counts, seed=90, item=1)
    assert got["R3"].tolist() == [18, 22, 71]
    assert got["anti"].tolist() == [4, 47, 50]
    assert got["random"].size == 3 and np.isin(got["random"], cells).all()
    # Boundary cases include no responders and all responders above threshold.
    for cc, nn in (([], []), ([9, 20], [1, 2]), ([9, 20], [3, 4])):
        selected = r1.controls(cc, nn, 90, 3)
        assert len({v.size for v in selected.values()}) == 1
        assert all(np.isin(v, cc).all() for v in selected.values())
    with pytest.raises(ValueError, match="positive counts"):
        r1.controls([1, 2], [0, 3], 90, 1)


def test_control_ties_are_reproducible_separate_from_global_rng_and_change_by_item():
    cells = np.arange(100)
    counts = np.array([1] * 70 + [3] * 30)
    first = r1.controls(cells, counts, 91, 1)
    np.random.default_rng(2).random(1000)
    repeat = r1.controls(cells, counts, 91, 1)
    other = r1.controls(cells, counts, 91, 2)
    assert all(np.array_equal(first[k], repeat[k]) for k in first)
    assert not np.array_equal(first["anti"], other["anti"])
    assert not np.array_equal(first["random"], other["random"])
    assert np.max(first["anti"]) < 70
    # Across independent item keys, the uniform control samples both count groups.
    overlaps = [np.isin(r1.controls(cells, counts, 91, i)["random"], cells[70:]).sum() for i in range(1, 101)]
    assert 7 < np.mean(overlaps) < 11


def test_duty_capture_keeps_inherited_timeline_draws_and_independent_generator():
    cfg = dict(e4.CONTRACT, m=160, n=100, f_q=0.05, n_novel=2, duty_post=5)
    captured = r1.DutyCapture(cfg, 94)
    plain = e4.Online(cfg, 94, post=cfg["duty_post"], bg_key=(e4.ARMS, e4.ARM_DUTY))
    captured.run_to(3)
    plain.run_to(3)
    assert e4.state_digest(captured) == e4.state_digest(plain)
    assert captured.log == plain.log
    assert not isinstance(captured._pat, e5.FamilyGen)
    assert e5.capture_ok(captured, 3)
    assert len(captured.slot_mem) == len(captured.slot_rec) == 3
    writers, stores = r1.five_stores(captured, 3)
    assert np.array_equal(stores["R1"].keys, plain.fb.keys)
    assert np.array_equal(stores["A"].keys, plain.fb_plateau.keys)
    for i in range(3):
        assert writers["R3"][i].size == writers["random"][i].size == writers["anti"][i].size
    captured.cont_cells[0] = np.array([-1])
    with pytest.raises(ValueError, match="captured R1"):
        r1.five_stores(captured, 3)


def test_small_run_preserves_raw_inputs_and_auditable_per_cue_counts(run_dir):
    results = run_dir / "results.jsonl"
    evidence = run_dir / "portable"
    final = r1.run("correlated", 96, loads=(4,), results_path=results, evidence_dir=evidence,
                   run_id="small", cfg=tiny(), log=lambda message: None)
    rows = [json.loads(line) for line in results.read_text().splitlines()]
    assert [r["kind"] for r in rows] == ["replay_started", "replay_load_started", "replay_load", "replay_complete"]
    load = final["loads"]["4"]
    assert all(load["checks"].values())
    assert len({a["raster_sha256"] for a in load["arms"].values()}) == 1
    compact = json.loads((evidence / "small-M4.json").read_text())
    assert compact["readout"] == dict(J_fb=2.8, g=0.3, window_mem=50, window_rec=75)
    assert "gate_ok" not in compact["memory"] and all("passes" not in a for a in compact["summaries"].values())
    half = [q["cue_id"] for q in compact["index_cues"] if q["kind"] == "half"]
    novel = [q["cue_id"] for q in compact["index_cues"] if q["kind"] == "novel"]
    old = [q["cue_id"] for q in compact["index_cues"] if q["oldest"]]
    for window in (25, 50, 100):
        assert np.median([compact["index_cues"][i][f"recall{window}"] for i in half]) == compact["memory"]["recall_median"][str(window)]
    index_latencies = [compact["index_cues"][i]["latency_half_ms"] for i in half
                       if compact["index_cues"][i]["latency_half_ms"] is not None]
    assert (float(np.median(index_latencies)) if index_latencies else None) == compact["memory"]["latency_half_ms"]
    for name, content in compact["content"].items():
        per = [dict(zip(content["columns"], row)) for row in content["rows"]]
        joint = [row["missing"] >= 40 and row["total"] - row["item"] < 10 for row in per]
        counts = compact["summaries"][name]["counts"]
        assert counts["joint"] == sum(joint[i] for i in half)
        assert counts["D3"] == sum(per[i]["total"] < 10 for i in novel)
        assert counts["D4"] == sum(joint[i] for i in old)
        latencies = [per[i]["latency_ms"] for i in half if per[i]["latency_ms"] is not None]
        assert (float(np.median(latencies)) if latencies else None) == compact["summaries"][name]["latency_ms_median"]
        assert all(row["latency_ms"] is None or 0 <= row["latency_ms"] < 75 for row in per)
        assert any(row["latency_ms"] is None for row in per)  # nonfinite readout values survive as JSON null
    raw = load["raw_replay"]
    from pathlib import Path
    raw_bytes = Path(raw["path"]).read_bytes()
    assert hashlib.sha256(raw_bytes).hexdigest() == raw["sha256"]
    with np.load(raw["path"], allow_pickle=False) as archive:
        assert {"raster_ticks", "raster_cells", "raster_cells_offsets", "cue_missing", "learn_cont_counts",
                "learn_A", "writer_random", "feedback_R3", "memory_out_json"} <= set(archive.files)
        cfg = json.loads(str(archive["metadata_json"]))["cfg"]
        memory_out = json.loads(str(archive["memory_out_json"]))
        for j, i in enumerate(half):
            cue = compact["index_cues"][i]
            assert [cue[f"recall{w}"] for w in (25, 50, 100)] == [memory_out["recall"][str(w)][j] for w in (25, 50, 100)]
            assert cue["latency_half_ms"] == memory_out["latency_half"][j]
        offsets = archive["raster_cells_offsets"]
        raster = {int(t): archive["raster_cells"][offsets[i]:offsets[i + 1]]
                  for i, t in enumerate(archive["raster_ticks"])}
        n_ticks = json.loads(str(archive["metadata_json"]))["n_ticks"]
        assert r1.raster_digest(raster, n_ticks, cfg["n"]) == load["raster_sha256"]
    # Attempt identity is exclusive; neither evidence nor journal is overwritten.
    journal = results.read_bytes()
    with pytest.raises(FileExistsError):
        r1.run("correlated", 96, loads=(4,), results_path=results, evidence_dir=evidence,
               run_id="small", cfg=tiny(), log=lambda message: None)
    assert results.read_bytes() == journal and Path(raw["path"]).read_bytes() == raw_bytes


def test_partial_failure_is_append_only_and_keeps_completed_load(run_dir, monkeypatch):
    results = run_dir / "results.jsonl"
    seen = []

    def fail_second(main, M, raw, compact, meta, log):
        seen.append(M)
        if M == 6:
            raise RuntimeError("injected replay interruption")
        return dict(M=M, measured_marker="first checkpoint remains")

    monkeypatch.setattr(r1, "evaluate_load", fail_second)
    with pytest.raises(RuntimeError, match="injected replay"):
        r1.run("correlated", 97, loads=(4, 6), results_path=results, evidence_dir=run_dir / "portable",
               run_id="incomplete", cfg=tiny(), log=lambda message: None)
    rows = [json.loads(line) for line in results.read_text().splitlines()]
    assert seen == [4, 6]
    assert rows[-1]["kind"] == "replay_incomplete" and rows[-1]["completed_loads"] == ["4"]
    assert rows[-1]["attempted_load"] == 6
    assert [r["load"] for r in rows if r["kind"] == "replay_load"] == [dict(M=4, measured_marker="first checkpoint remains")]
    assert not any(r["kind"] == "replay_complete" for r in rows)


def test_cli_rejects_unplanned_readout_loads_and_unsafe_run_identity(run_dir):
    with pytest.raises(SystemExit):
        r1.main(["--regime", "correlated", "--seed", "44", "--loads", "750"])
    with pytest.raises(ValueError, match="filename"):
        r1.run("duty", 90, run_id="../escape", evidence_dir=run_dir)
