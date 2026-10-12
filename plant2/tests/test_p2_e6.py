"""Small E6 integrity and decision checks; outputs persist in cache, never temporary directories."""
import copy
import json
from pathlib import Path

import numpy as np
import pytest

from analysis import p2r1_replay as r1
from plant2.experiments import p2_e3_completion as e3
from plant2.experiments import p2_e6 as e6


def tiny():
    return dict(e6.CONTRACT, m=160, n=80, f_q=.05, n_old=2, n_rand=2, n_novel=2,
                settle=30, converge_window=10, acc_tau=200)


def test_causal_normalized_rule_and_exact_per_cell_random_control():
    assert np.array_equal(e6.probabilities(np.zeros(100, np.int64)), np.full(100, .5))
    p = e6.probabilities(np.array([0, 0, 9, 99]))
    assert abs(p.sum() - 2) <= 1e-9 and np.max(p) <= 1 and p[0] == p[1] > p[2] > p[3]
    assert e6.probabilities(np.empty(0)).size == 0
    cells, eligible = np.array([7, 19, 31]), np.arange(4)
    coins = np.array([[.1, .7, .6], [.3, .9, .2], [.8, .01, .1], [.02, .03, .9]])
    selected, counts = e6.flip_mask(coins, p, eligible, cells, 101, 8, "candidate")
    random, random_counts = e6.flip_mask(coins, p, eligible, cells, 101, 8, "random")
    assert np.array_equal(selected.sum(0), random.sum(0))
    assert np.array_equal(counts, random_counts)
    cfg = tiny()
    arms = [e6.E6(cfg, 101, arm, "F10") for arm in e6.ARMS]
    for a in arms:
        a.learn(8)
    assert len({json.dumps(e6.matched_digests(a), sort_keys=True) for a in arms}) == 1
    assert e6.ragged_digest(arms[1].actual_counts) == e6.ragged_digest(arms[2].actual_counts)
    # Independently reconstruct each history prefix from actual eligibility.
    H = np.zeros(cfg["m"], np.int64)
    for E, actual_p in zip(arms[1].E, arms[1].p_history):
        assert np.array_equal(actual_p, e6.probabilities(H[E]))
        H[E] += 1
    assert np.array_equal(H, arms[1].H)


def test_uniform_wrapper_reproduces_frozen_stores_neural_state_and_stream_positions():
    cfg = tiny()
    wrapped = e6.E6(cfg, 101, "baseline", "independent")
    frozen = e3.E3(cfg, 101)
    wrapped.learn(8)
    frozen.learn(8)
    assert r1.live_digest(wrapped) == r1.live_digest(frozen)
    assert wrapped.learn_log == frozen.learn_log
    assert all(np.array_equal(a, b) for a, b in zip(wrapped.R, frozen.R))
    assert wrapped.episodes == 8


def test_small_load_roundtrip_keeps_histories_states_and_portable_metrics(run_dir):
    main = e6.E6(tiny(), 101, "candidate", "F10")
    main.learn(6)
    before = e6.state_digest(main)
    value = e6.evaluate_load(main, 6, run_dir / "raw.npz", run_dir / "portable.json",
                             dict(seed=101, attempt="tiny", full_size=False), e6.Budget())
    assert e6.state_digest(main) == before
    compact = json.loads((run_dir / "portable.json").read_text())
    half = [r for r in compact["index_cues"] if r["kind"] == "half"]
    joint = [r["own50"] >= .8 * r["A_size"] and r["spurious50"] < .5 * r["A_size"] for r in half]
    assert sum(joint) == value["index"]["joint_index_count"]
    assert all("threshold_offset" in r for r in compact["index_cues"])
    with np.load(run_dir / "raw.npz", allow_pickle=False) as raw:
        assert np.array_equal(raw["H"], main.H) and np.array_equal(raw["forward_keys"], main.store.keys)
        assert raw["probabilities"].dtype == np.float64
        raster = dict(zip(raw["raster_ticks"].tolist(), e6.unpack(raw, "raster_cells")))
        meta = json.loads(str(raw["metadata_json"]))
        assert r1.raster_digest(raster, meta["n_ticks"], main.c["n"]) == value["raster_sha256"]
    for name, content in compact["content"].items():
        rows = [dict(zip(content["columns"], r)) for r in content["rows"]]
        half_ids = [r["cue_id"] for r in half]
        successes = sum(rows[i]["missing"] >= 40 and rows[i]["total"] - rows[i]["item"] < 10 for i in half_ids)
        assert successes == value["content"][name]["counts"]["joint"]
    logged = []
    sanity = e6.sanity_loads(value, run_dir, run_dir, dict(seed=101, attempt="tiny"), e6.Budget(),
                            lambda kind, **fields: logged.append(dict(kind=kind, **fields)))
    assert sanity["wrong_label"]["count_preserved"]
    assert sanity["empty_store"]["responders"] == sanity["empty_store"]["total_raster_spikes"] == 0
    assert len(logged) == 2


def synthetic_loads():
    loads = []
    for condition in ("F10", "independent"):
        for M in e6.LOADS:
            for arm in e6.ARMS:
                index = dict(C1=.98, C2=.96, C3=.99, C4_recall=.95, C4_spurious=.95, joint_index=.95)
                if condition == "F10" and M == 1000 and arm != "candidate":
                    index.update(C2=.65 if arm == "baseline" else .8, joint_index=.75 if arm == "baseline" else .8)
                loads.append(dict(condition=condition, arm=arm, M=M, index=index, integrity=True,
                                  content={"inherited": dict(joint=.92, D4=.91)},
                                  protocol=dict(eligibility=True, mean_A_1000=True if M == 1000 else None, settled=True)))
    return loads


def synthetic_sanity():
    return dict(wrong_label=dict(C1=.02, count_preserved=True), empty_store=dict(responders=0, stores_empty=True))


def pairs():
    return {f"{condition}/{M}/{arm}": {} for condition in ("F10", "independent")
            for M in e6.LOADS for arm in ("baseline", "random")}


def test_screen_checks_absolute_margins_content_protocol_and_partial_separately():
    loads, sanity = synthetic_loads(), synthetic_sanity()
    assert e6.screen(loads, sanity, paired_evidence=pairs())["verdict"] == "FEASIBILITY PASS"
    candidate = next(r for r in loads if (r["condition"], r["arm"], r["M"]) == ("F10", "candidate", 1000))
    candidate["index"]["C4_recall"] = .89
    assert e6.screen(loads, sanity)["verdict"] == "FEASIBILITY FAIL"
    candidate["index"]["C4_recall"] = .95
    candidate["index"]["C2"] = .9  # absolute bar passes, but random-control margin fails
    baseline = next(r for r in loads if (r["condition"], r["arm"], r["M"]) == ("F10", "random", 1000))
    baseline["index"]["C2"] = .81
    assert "index/F10/1000/C2_vs_random" in e6.screen(loads, sanity)["failed_parts"]
    clean = synthetic_loads()
    independent = next(r for r in clean if (r["condition"], r["arm"], r["M"]) == ("independent", "candidate", 500))
    independent["content"]["inherited"]["joint"] = .86
    result = e6.screen(clean, sanity)
    assert result["pure_index_verdict"] == "PASS" and result["verdict"] == "FEASIBILITY FAIL"
    independent["protocol"]["settled"] = False
    assert "protocol/independent/500/candidate/settled" in e6.screen(clean, sanity)["failed_parts"]
    assert e6.screen(clean[:-1], {})["verdict"] == "PARTIAL + FEASIBILITY FAIL"
    assert e6.screen(synthetic_loads(), sanity, paired_evidence={})["verdict"] == "PARTIAL"


def test_seed_and_verdict_guards_do_not_accept_test_or_aggregate_only_evidence(run_dir):
    with pytest.raises(ValueError, match="small integrity"):
        e6.run_seed(111, cfg=tiny(), results_path=run_dir / "x.jsonl", evidence_dir=run_dir)
    with pytest.raises(ValueError, match="small integrity"):
        e6.run_seed(101, cfg=tiny())
    forged = dict(kind="seed_screen", seed=101, full_size=False, source=dict(code_sha256="x"),
                  attempt="test", screen=e6.screen(synthetic_loads(), synthetic_sanity(), paired_evidence=pairs()))
    with pytest.raises(ValueError, match="locked"):
        e6.seed_guard(102, dict(code_sha256="x"), [forged], [])
    forged["full_size"] = True
    assert not e6.verified_screen(forged, [forged], "x")
    with pytest.raises(ValueError, match="locked"):
        e6.seed_guard(111, dict(code_sha256="x"), [forged], [])
    fake_gate = [dict(forged, seed=s, full_size=False) for s in e6.GATED]
    assert e6.verdict(fake_gate)["verdict"] == "PARTIAL"
    duplicated = [dict(kind="seed_started", seed=111, full_size=True, attempt=str(i)) for i in (1, 2)]
    assert e6.verdict(duplicated)["verdict"] == "INVALID"


def test_deadline_stops_new_load_at_hour_and_inflight_at_grace(monkeypatch):
    monkeypatch.setattr(e6.time, "time", lambda: 4600)
    budget = e6.Budget(1000)
    with pytest.raises(e6.ResourceStop, match="60-minute"):
        budget.check(new_load=True)
    budget.check()
    monkeypatch.setattr(e6.time, "time", lambda: 5200)
    with pytest.raises(e6.ResourceStop, match="grace"):
        budget.check()


def test_unexpected_driver_defect_records_invalid_and_preserves_attempt(run_dir, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("synthetic implementation defect")
    monkeypatch.setattr(e6, "evaluate_load", broken)
    path = run_dir / "defect.jsonl"
    result = e6.run_seed(101, results_path=path, evidence_dir=run_dir / "evidence", cfg=tiny(), loads=(4,),
                         attempt="defect", log=lambda message: None)
    assert result["screen"]["verdict"] == "INVALID"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    failure = next(r for r in rows if r["kind"] == "interrupted")
    assert failure["integrity_defect"] and "synthetic implementation defect" in failure["error"]
    assert rows[0]["kind"] == "seed_started" and rows[-1]["kind"] == "seed_screen"
