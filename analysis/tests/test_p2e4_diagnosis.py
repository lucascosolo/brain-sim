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
    assert d["valid"] and d["reproduction_mismatches"] == 0 and d["D3_verified"] and d["steps_compared"] == 200
    for M in ("120", "200"):
        L = d["loads"][M]
        assert L["twin_B_matches_record"] is True
        assert sum(L["D1"].values()) == L["n_half"] == 40
    assert e4.score_slot is diag._orig_score_slot  # the driver is left as it was
    assert [json.loads(l)["kind"] for l in out.read_text().splitlines()][-1] == "diagnosis"


def test_twin_B_check_needs_a_record_and_every_aggregate():
    pairs = [dict(kind="recent", index_online=True, index_settled=False, content_online=True, content_settled=True)]
    rec = {"all": dict(n=1, memory_online=1.0, memory_settled=0.0, content_online=1.0, content_settled=1.0,
                       mcnemar_memory=[1, 0], mcnemar_content=[0, 0])}
    assert diag.twin_B_matches(pairs, rec) is True
    assert diag.twin_B_matches(pairs, None) is None
    assert diag.twin_B_matches(pairs, {"all": dict(rec["all"], mcnemar_memory=[0, 1])}) is False


def test_candidate_classes_are_exhaustive_and_exclusive():
    regen = [1, 2, 3, 4, 5, 6]
    out = diag.classify_lines(regen, lines_A=[1, 2], lines_RnA=[3, 5, 2], lines_other=[4, 5, 1])
    fr = {k: out[k] for k in diag.CANDIDATE_CLASSES}
    assert abs(sum(fr.values()) - 1.0) < 1e-12
    assert fr == dict(with_A_candidate=2 / 6, only_R_not_A_candidates=1 / 6, only_other_candidates=1 / 6,
                      mixed_non_A_candidates=1 / 6, no_earlier_candidate=1 / 6)
