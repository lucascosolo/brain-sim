import json

import numpy as np
import pytest

from plant2.experiments import p2_e1_btsp as e1

SMALL = dict(e1.CONTRACT, m=800, n=800, a=40, M=60, n_old=20, n_rand=20, n_novel=20, f_q=0.03,
             t_persist=300, t_gap=100)


def test_contract_constants_are_the_predeclared_ones():
    c = e1.CONTRACT
    assert (c["m"], c["n"], c["a"], c["M"], c["f_q"], c["J"]) == (4000, 4000, 100, 1000, 0.005, 1.12)
    assert (c["r_on"], c["r_off"], c["t_item"], c["elig_min"], c["p_flip"]) == (40.0, 0.5, 200, 3, 0.5)
    assert (c["t_cue"], c["t_gap"], c["window"], c["t_persist"]) == (100, 200, 50, 60_000)
    assert e1.BARS["recall"] == 0.80 and e1.BARS["item_frac"] == 0.90 and e1.SEEDS == (1, 2, 3, 4, 5)


def test_small_seed_run_writes_a_complete_record(run_dir):
    out = run_dir / "results.jsonl"
    rec = e1.run_seed(SMALL, 1, out, log=lambda m: None)
    row = json.loads(out.read_text().splitlines()[-1])
    assert row["experiment"] == "P2-E1" and row["kind"] == "kill_test_seed" and row["seed"] == 1
    for k in ("C1", "C2", "C3", "C4", "C1_frac", "mean_A", "median_recall50"):
        assert k in row["criteria"]["phase1"]
    assert row["validity"]["weights_unchanged"] is True
    assert rec["report"]["never_trained_twin_responders"] == [0] * 20


def test_the_write_does_not_read_memory_spikes():
    loud = e1.E1(dict(SMALL, J=8.0), 2)  # strong enough that memory cells fire while items are shown
    silent = e1.E1(dict(SMALL, J=0.0), 2)
    loud.learn(30)
    silent.learn(30)
    assert sum(loud.learn_log["mem_spikes"]) > 0 and sum(silent.learn_log["mem_spikes"]) == 0
    assert np.array_equal(loud.store.keys, silent.store.keys)


def test_capacity_point_reproduces_the_kill_test_numbers(run_dir):
    rec = e1.run_seed(SMALL, 3, run_dir / "a.jsonl", log=lambda m: None)
    cap = e1.run_capacity(SMALL, seed=3, points=(30, SMALL["M"]), results_path=run_dir / "b.jsonl",
                          log=lambda m: None)
    assert cap[-1]["criteria"] == rec["criteria"]["phase1"]


@pytest.mark.slow
def test_p2_e1_kill_test(run_dir):
    verdict, _ = e1.run_kill_test(results_path=run_dir / "results.jsonl", log=print)
    assert verdict["valid"] and verdict["passed"], verdict["per_seed"]
