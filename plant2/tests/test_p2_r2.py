"""R2 scientific-integrity checks; small networks and persistent cache only."""
import copy
import json
from pathlib import Path

import numpy as np
import pytest

from analysis import p2r1_replay as r1
from analysis import p2r2_degree_null as r2
from plant2.experiments import p2_e1_btsp as e1
from plant2.experiments import p2_e3_completion as e3


def test_fixed_curveball_preserves_binary_degrees_and_attempt_count_deterministically():
    rows = np.array([[0, 1, 2, 3], [0, 4, 5, 6], [1, 4, 7, 8],
                     [2, 5, 7, 9], [3, 6, 8, 9], [0, 2, 4, 8]])
    steps = (0, 10, 30, 60)
    a, ca = r2.curveball_block(rows, np.random.default_rng(7), steps)
    b, cb = r2.curveball_block(rows, np.random.default_rng(7), steps)
    assert ca == cb and tuple(a) == steps
    for step in steps:
        assert np.array_equal(a[step], b[step])
        assert r2.check_margins(rows, a[step], 10, block=6)
        assert ca[step] <= step
    assert ca[60] > 0 and not np.array_equal(a[60], rows)
    altered = a[60].copy()
    altered[0, 1] = altered[0, 0]
    with pytest.raises(r2.IntegrityError, match="binary"):
        r2.check_margins(rows, altered, 10, block=6)
    # A saturated pair still consumes every attempted trade, even when nothing can change.
    _, changed = r2.curveball_block(np.array([[0, 1], [0, 1]]), np.random.default_rng(1), (0, 20))
    assert changed[20] == 0


def test_overlap_statistics_match_explicit_pair_counts_and_keep_squared_counts_above_int8():
    rows = np.array([np.arange(100), np.arange(10, 110), np.arange(20, 120), np.arange(30, 130)])
    metric = r2.structural_metrics(rows, rows, 140, F=2, attempted=0, changed=0, block=2)
    overlap = [len(set(x) & set(y)) for i, x in enumerate(rows) for y in rows[i + 1:]]
    assert metric["Q"] == np.mean(np.square(np.asarray(overlap, np.int64)))
    assert metric["Q"] > 255 and metric["mean_overlap"] == np.mean(overlap)
    assert metric["R"] == 1 and metric["within_block_cumulative_max"] == 0
    assert metric["changed_entry_fraction"] == 0


def synthetic_chains():
    return {str(c): {"0": dict(D=12., Q=80., R=1.),
                    "5000": dict(D=.2, Q=40., R=.05),
                    "10000": dict(D=.2, Q=40., R=.05)} for c in (0, 1)}


def test_structural_checks_cover_both_chains_late_drift_and_between_chain_endpoints():
    chains = synthetic_chains()
    assert r2.structural_decision(chains)["ok"]
    chains["1"]["10000"]["D"] = 1.5
    result = r2.structural_decision(chains)
    assert not result["ok"] and not result["checks"]["1/D_reduced"]
    chains = synthetic_chains()
    chains["1"]["5000"]["Q"] = 50.
    assert not r2.structural_decision(chains)["checks"]["1/late/Q"]
    chains = synthetic_chains()
    for step in ("5000", "10000"):
        chains["1"][step]["R"] = .09
    assert not r2.structural_decision(chains)["checks"]["between/R"]


def test_exact_frozen_twenty_episode_original_sham_parity():
    result = r2.parity_check()
    assert result["passed"] and result["episodes"] == 20
    assert result["config"] == dict(m=256, n=256, a=64, f_q=.05)


def metrics(**changes):
    base = dict(C1=.95, C2=.50, C3=.99, C4_recall=.96, C4_spurious=.5, joint_index=.48)
    return dict(base, **changes)


def test_effect_labels_boundaries_recall_priority_and_failed_original_requirement():
    original = metrics()
    assert r2.classify(original, metrics(C2=.65, joint_index=.58))["label"] == "MATERIAL STRUCTURE SENSITIVITY"
    trade = r2.classify(original, metrics(C2=.9, joint_index=.85, C4_recall=.92))
    assert trade["label"] == "RECALL TRADE-OFF"
    same = r2.classify(original, metrics(C2=.55, joint_index=.53))
    assert same["label"] == "FAILURE PERSISTS WITH SMALL MEASURED BENEFIT"
    near = r2.classify(metrics(C2=.91), metrics(C2=.89))
    assert near["label"] == "MIXED/INTERMEDIATE" and near["C2_bar_deficit_removed"] is None
    large = r2.classify(original, metrics(C2=.95, joint_index=.90))
    assert large["C2_bar_deficit_removed"] > 1  # Deliberately not clipped.


def test_budget_has_no_grace_and_stops_new_stages_at_eighteen_minutes(monkeypatch):
    budget = r2.Budget(1000)
    monkeypatch.setattr(r2.time, "time", lambda: 2080)
    with pytest.raises(r2.ResourceStop, match="18-minute"):
        budget.check(new_stage=True)
    budget.check()
    monkeypatch.setattr(r2.time, "time", lambda: 2200)
    with pytest.raises(r2.ResourceStop, match="20-minute"):
        budget.check()
    monkeypatch.setattr(r2.time, "time", lambda: 2140)
    with pytest.raises(r2.ResourceStop, match="19-minute"):
        budget.check()


def test_source_guard_refuses_uncommitted_code_without_starting_any_simulation(monkeypatch):
    monkeypatch.setattr(r2, "git_read", lambda *args: b"not the committed source")
    with pytest.raises(r2.IntegrityError, match="uncommitted source"):
        r2.source_manifest()


def test_small_evaluation_retains_raster_and_recomputable_counts_without_changing_learning(run_dir):
    cfg = dict(r2.CFG, m=160, n=80, f_q=.05, n_old=2, n_rand=2, n_novel=2,
               settle=30, converge_window=10, acc_tau=200)
    gen = e1.stream(103, e1.PATTERNS)
    rows = np.asarray([np.sort(gen.choice(cfg["m"], cfg["a"], replace=False)) for _ in range(6)])
    e = e3.E3(cfg, 103)
    e._pat = r2.MatrixItems(rows, cfg["m"])
    e.learn(6)
    digest = r2.state_digest(e)
    meta = dict(experiment="P2-R2", seed=103, arm="ORIGINAL", full_size=False)
    raw = r2.learned_save(run_dir / "learned.npz", e, meta)
    logged = []
    value = r2.evaluate_load(e, 6, run_dir, run_dir, meta, r2.Budget(), raw,
                              lambda kind, **kw: logged.append(dict(kind=kind, **kw)))
    assert r2.state_digest(e) == digest and value["integrity"]
    assert [x["kind"] for x in logged] == ["index_load", "content_load", "content_load"]
    compact = json.loads(Path(value["portable"]["path"]).read_text())
    half = [r for r in compact["index_cues"] if r["kind"] == "half"]
    joint = [r["recall50"] >= .8 and r["spurious50"] < .5 * r["A_size"] for r in half]
    assert sum(joint) == value["index"]["joint_index_count"]
    for row in compact["index_cues"]:
        assert row["total50"] == sum(t < 50 for _, t in row["first_spikes100"])
        assert "threshold_offset" in row
    with np.load(value["raw"]["raster"]["path"], allow_pickle=False) as archive:
        offsets = archive["raster_cells_offsets"]
        raster = {int(t): archive["raster_cells"][offsets[i]:offsets[i + 1]]
                  for i, t in enumerate(archive["raster_ticks"])}
        raw_meta = json.loads(str(archive["metadata_json"]))
        assert r1.raster_digest(raster, raw_meta["n_ticks"], cfg["n"]) == compact["raster_sha256"]
    for name, content in compact["content"].items():
        data = [dict(zip(content["columns"], x)) for x in content["rows"]]
        hits = [data[r["cue_id"]]["missing"] >= 40 and data[r["cue_id"]]["total"] - data[r["cue_id"]]["item"] < 10 for r in half]
        assert sum(hits) == value["content"][name]["counts"]["joint"]
    same = copy.deepcopy(value)
    same["arm"] = "DEGREE_NULL"
    paired = r2.paired_evidence(value, same)
    assert paired["coin_draw_counts_equal"] and paired["exact_A_and_test_schedule"]
    assert all(v["null_only"] == v["original_only"] == 0 for v in paired["paired"].values())


def test_summary_never_calls_missing_or_duplicate_seed_evidence_complete():
    def complete(seed):
        return dict(experiment="P2-R2", kind="seed_complete", seed=seed, result=dict(status="COMPLETE",
            missing_loads=[], missing_paired_loads=[], missing_stages=[], label="MATERIAL STRUCTURE SENSITIVITY",
            pairs={"1000": dict(decision=dict(C2_bar_deficit_removed=.6))}))
    assert r2.summarize([complete(103)])["status"] == "PARTIAL"
    assert r2.summarize([complete(103), complete(103)])["status"] == "INVALID"
    result = r2.summarize([complete(103), complete(104)])
    assert result["status"] == "COMPLETE" and result["half_bar_deficit_removed_on_both"]
    assert result["replicated_label"] == "MATERIAL STRUCTURE SENSITIVITY"
    interrupted = complete(104)
    interrupted["result"]["missing_stages"] = ["DEGREE_NULL/1000/assigned_A"]
    assert r2.summarize([complete(103), interrupted])["status"] == "PARTIAL"


def test_interruption_checkpoint_preserves_paused_replay_and_marks_unfinished_episode(run_dir):
    class InterruptedRaster(dict):
        def get(self, tick):
            if tick == 20:
                raise r2.ResourceStop("synthetic readout interruption")
            return super().get(tick)
    cfg = dict(r2.CFG, m=160, n=80)
    e = e3.E3(cfg, 103)
    # Mirrors the inherited pre-write interval: item exists before its A/E entries.
    e.items.append(np.arange(100, dtype=np.int64))
    try:
        r2.replay(InterruptedRaster(), 50, np.zeros(81, np.int64), np.empty(0, np.int64),
                  160, np.array([2.8]), np.array([.3]), [])
    except r2.ResourceStop as exc:
        saved = r2.checkpoint_interrupted(e, dict(stage="ORIGINAL/500/replay/inherited"), exc,
            run_dir / "interrupted-state.npz", dict(seed=103, full_size=False))
    with np.load(saved["path"], allow_pickle=False) as archive:
        meta = json.loads(str(archive["metadata_json"]))
        assert not meta["resumable"] and meta["main"]["started_items"] == 1
        assert meta["main"]["assigned_sets"] == meta["main"]["eligibility_sets"] == 0
        assert int(archive["paused_replay_t"]) == 20
        assert archive["paused_replay_v"].shape == (1, 160)
        assert archive["paused_replay_ring"].shape == (3, 1, 160)
