import json

import pytest

from analysis import p2e4_diagnosis as diag
from plant2.experiments import p2_e4_online as e4
from plant2.tests.test_p2_e4 import TINY


@pytest.mark.slow
def test_diagnosis_reproduces_every_logged_slot_and_twin_B(run_dir):
    out = run_dir / "r.jsonl"
    e4.run_seed(TINY, 92, gated=False, results_path=out, log=lambda m: None)
    d = diag.run(92, False, results_path=out, log=lambda m: None, c=TINY)
    assert d["valid"] and d["reproduction_mismatches"] == 0
    for M in ("120", "200"):
        L = d["loads"][M]
        assert L["twin_B_matches_record"] is True
        assert sum(L["D1"].values()) == L["n_half"] == 40
    assert e4.score_slot is diag._orig_score_slot  # the driver is left as it was
    assert [json.loads(l)["kind"] for l in out.read_text().splitlines()][-1] == "diagnosis"
