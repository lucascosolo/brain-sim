import copy
import json

import numpy as np
import pytest

from plant2.experiments import p2_e1_btsp as e1
from plant2.experiments import p2_e4_online as e4

# seeds 90+ belong to no experiment; the real-config schedule is built from indices only (no gated material)
TINY = dict(e4.CONTRACT, m=1500, n=1500, a=100, f_q=0.0133, acc_tau=2000, settle=8000, converge_window=2000,
            n_old=20, n_rand=20, n_novel=20, gate_M=(120, 200), stress_M=(260,), block=48, sub_blocks=2,
            age0_blank_subblocks=(0,), c500_uniform_spread=(2, 1),
            stress_mix=(("recent", 20), ("uniform", 12), ("novel", 8), ("blank", 4), ("full", 4)), stress_recent_max_age=30,
            pool=40, cohort=20, hab_items=4, hab_reps=12, hab_late=4, hab_pause=2, hab_recovery=3, hab_controls=7,
            late_need=3, max_drop=1, recovery_need=2, min_eligible=1, wps_steps=10, ood_each=3, duty_post=300,
            mean_A_lo=10, mean_A_hi=30, final_M=260)


def test_contract_constants_are_the_frozen_ones():
    c = e4.CONTRACT
    assert (c["J_fb"], c["g"], c["J"], c["acc_tau"]) == (2.80, 0.3, 1.525, 10_000)
    assert (c["pre"], c["slot"], c["post"], c["duty_post"]) == (50, 100, 100, 1850)
    assert c["gate_M"] == (500, 1000) and c["block"] == 240 and c["sub_blocks"] == 10
    assert dict(c["sub_mix"]) == dict(recent=5, uniform=5, cohort=10, novel=2, blank=2) and sum(dict(c["sub_mix"]).values()) == 24
    assert (c["pool"], c["cohort"], c["recent_max_age"], c["uniform_min_age"]) == (200, 100, 20, 21)
    assert sum(c["c500_uniform_spread"]) == 15 and len(c["age0_blank_subblocks"]) == 5
    assert (c["hab_items"], c["hab_reps"], c["hab_late"], c["hab_pause"], c["hab_recovery"], c["hab_controls"]) == (50, 100, 10, 20, 5, 89)
    assert (c["late_need"], c["max_drop"], c["recovery_need"], c["min_eligible"]) == (8, 2, 3, 25)
    assert (c["win_mem"], c["win_rec"], c["joint_missing"], c["joint_intrusions"], c["frac"]) == (50, 75, 40, 10, 0.90)
    assert c["window"] == 50 and c["rec_window"] == 75 and c["t_cue"] + c["t_gap"] == 300
    assert abs(sum(s for _, s in c["rolling"]) - 1.0) < 1e-12
    assert (e4.BG, e4.SLOT_IN, e4.ROLL, e4.BLOCK, e4.HAB, e4.NOVEL_K, e4.ARMS) == (12, 13, 14, 15, 16, 17, 18)
    assert e4.GATED_SEEDS == (16, 17, 18, 19, 20) and e4.EXPLORE_SEEDS == (42, 43)


@pytest.mark.parametrize("seed", [90, 91])
def test_real_schedule_is_feasible_and_follows_every_rule(seed):
    c = e4.CONTRACT
    s = e4.Schedule(seed, c)
    assert e4.audit_schedule(s, c["final_M"]) == []
    assert all(len(b) == c["block"] for b in s.blocks.values())
    assert sum(sl["c500"] for sl in s.blocks[1000].values()) == 15 and sum(sl["c500"] for sl in s.blocks[500].values()) == 0
    for M in c["gate_M"]:
        b = s.blocks[M]
        assert sum(sl["age0"] for sl in b.values()) == 5
        assert all(sl["target"] == k for k, sl in b.items() if sl["age0"])
        steps = sorted(b)
        for j in range(10):  # stratified sub-blocks
            sub = [b[k]["kind"] for k in steps[24 * j:24 * (j + 1)]]
            assert {kd: sub.count(kd) for kd in set(sub)} == dict(recent=5, uniform=5, cohort=10, novel=2, blank=2)
        assert all(sl["pseudo"] is not None and sl["pseudo"][0] not in s.reserved for sl in b.values() if sl["kind"] == "novel")
    assert all(s.slot(k)["kind"] == "novel" for k in range(1, 201))  # every item 1-200 is reserved
    assert all(s.slot(k)["kind"] != "uniform" for k in range(1, 221))
    assert set(s.reserved.tolist()) == set(range(1, 201))


def test_online_learning_keeps_p2e1s_store_and_a_current_live_projection():
    e = e4.Online(TINY, 96)
    e.run_to(30)
    plain = e1.E1(dict(TINY, J=e1.CONTRACT["J"]), 96)
    plain.learn(30)
    assert np.array_equal(e.store.keys, plain.store.keys)
    assert e4.fb_union_ok(e) and e.proj_version == e.fb_version == 30
    indptr, post = e.fb.csr()
    assert np.array_equal(e.fb_proj.indptr, indptr) and np.array_equal(e.fb_proj.post, post)
    assert all(d["writes_ok"] and d["proj_current"] and d["inh_ok"] for d in e.log)
    assert len(e.cont_frac) == 30 and np.mean(e.cont_frac) > 0.5  # the positive control sees each item's own assembly


def test_slot_scores_match_brute_force_from_the_live_spikes():
    e = e4.Online(TINY, 97)
    e.run_to(80)  # reaches the first block (steps 73-120), so half-cue, novel and blank slots all occur
    for k in range(81, 101):
        twin = copy.deepcopy(e)
        e.step_k(k)
        twin.learn_one()
        s = twin.resolve(k, twin.sched.slot(k))
        c = twin.c
        bg, sl = e4.stream(97, e4.BG, k), e4.stream(97, e4.SLOT_IN, k)
        twin._rates(None)
        for _ in range(c["pre"]):
            twin.net.step(bg)
        twin._rates(s["cue"])
        mem, rec = [], []
        for t in range(c["slot"]):
            sp = twin.net.step(sl)
            mem += [(t, int(i)) for i in sp["mem"]]
            rec += [(t, int(j)) for j in sp["rec"]]
        R50 = {i for t, i in mem if t < 50}
        rec75 = {j for t, j in rec if t < 75}
        d = e.log[-1]
        assert d["n_R50"] == len(R50) and d["n_rec"] == len(rec75)
        if d["kind"] in e4.HALF:
            A, item = set(e.A[d["target"] - 1].tolist()), set(e.items[d["target"] - 1].tolist())
            missing = item - set(np.asarray(s["cue"]).tolist())
            assert d["recall"] == (len(A & R50) / len(A) if A else 0.0)
            assert d["missing"] == len(missing & rec75) and d["intrusions"] == len(rec75 - item)
            assert d["joint"] == (d["missing"] >= 40 and d["intrusions"] < 10)


def test_habituation_copies_leave_the_main_line_untouched_and_share_repetition_one():
    c = dict(TINY, hab_items=2, hab_reps=6, hab_late=2, hab_pause=1, hab_recovery=1, hab_controls=3)
    e = e4.Online(c, 98)
    e.run_to(120)
    before = e4.state_digest(e)
    items, v = e4.habituation(e, 120, log=lambda m: None)
    assert v["main_untouched"] and v["rep1_identical"] and e4.state_digest(e) == before
    assert len(items) == 2 and all(i["y"] != i["x"] for i in items)
    plans = e4.hab_selection(e, 120)
    for p in plans:
        assert p["y"] not in p["controls"] and p["x"] not in p["controls"] and len(p["controls"]) == 3
        assert not set([p["x"], p["y"], *p["controls"]]) & set(e.sched.reserved.tolist())


def test_habituation_rules_match_the_power_model_and_label_not_estimable():
    c = e4.CONTRACT
    rng = np.random.default_rng(0)
    items = [dict(scored=True, L_rep=int(rng.integers(6, 11)), L_ctl=int(rng.integers(8, 11)), rec_rep=int(rng.integers(2, 6)),
                  rec_ctl=int(rng.integers(3, 6)), col_rep=5, col_ctl=5, overlap=2, per_rep_both=[1] * 100) for _ in range(50)]
    full = e4.hab_criteria(c, items)
    fast = e4._hab_fast(c, items)
    assert full["O4"] == fast["O4"] and full["O5_recovery"] == fast["O5_recovery"] and full["O5_collateral"] == fast["O5_collateral"]
    habituated = sum(1 for d in items if d["L_rep"] <= d["L_ctl"] - 3)
    assert full["n_habituated"] == habituated
    few = [dict(d, L_ctl=0) for d in items]
    out = e4.hab_criteria(c, few)
    assert not out["O4"] and not out["O4_estimable"]


def test_labels_join_every_failure_and_separate_not_estimable():
    def rec(**v):
        vec = dict(O1_C1=True, O1_C2=True, O1_C3=True, O2_joint=True, O2_D3=True, O3_memory=True, O3_content=True,
                   O4=True, O5_recovery=True, O5_collateral=True)
        vec.update(v)
        hab = dict(O4=vec["O4"], O4_estimable=v.get("est4", True), O5_recovery=vec["O5_recovery"], O5_recovery_estimable=v.get("est5", True),
                   O5_collateral=vec["O5_collateral"], O5_collateral_estimable=True)
        return dict(loads={"1000": dict(block=dict(vector=vec), habituation=hab)})
    assert e4.labels(e4.CONTRACT, [rec()]) == []
    assert e4.labels(e4.CONTRACT, [rec(O1_C1=False, O4=False, est4=False, O5_recovery=False, est5=False)]) == [
        "ONLINE INDEX FAIL", "HABITUATION NOT ESTIMABLE", "RECOVERY NOT ESTIMABLE"]
    assert e4.labels(e4.CONTRACT, [rec(O3_content=False, O4=False)]) == ["ONLINE CONTENT FAIL", "HABITUATION FAIL"]


def test_guard_refuses_without_matching_committed_predictions(monkeypatch):
    monkeypatch.setattr(e4.record, "git_state", lambda: dict(plant2_dirty=False, plant2_tree="abc"))

    class R:
        def __init__(self, rc, out=""):
            self.returncode, self.stdout = rc, out
    pred = json.dumps(dict(experiment="P2-E4", kind="power_predictions", contract_digest=e4.DIGEST, plant2_tree="abc"))
    monkeypatch.setattr(e4, "_git", lambda *a: R(0, "" if a[0] == "show" else ""))
    with pytest.raises(SystemExit):
        e4.guard([])
    monkeypatch.setattr(e4, "_git", lambda *a: R(0, pred if a[0] == "show" else ""))
    assert e4.guard([dict(experiment="P2-E4", kind="kill_test_seed", seed=16)]) == {16}
    monkeypatch.setattr(e4.record, "git_state", lambda: dict(plant2_dirty=False, plant2_tree="other"))
    with pytest.raises(SystemExit):
        e4.guard([])
    monkeypatch.setattr(e4.record, "git_state", lambda: dict(plant2_dirty=True, plant2_tree="abc"))
    with pytest.raises(SystemExit):
        e4.guard([])


@pytest.mark.slow
def test_small_seed_runs_every_arm_and_every_validity_check_holds(run_dir):
    out = run_dir / "r.jsonl"
    rec = e4.run_seed(TINY, 95, gated=False, results_path=out, log=lambda m: None)
    v = rec["validity"]
    assert rec["valid"] and all(v[k] for k in ("fwd_equals_p2e1", "fb_union_ok", "slot_checks_ok", "main_untouched",
                                                 "rep1_identical", "audit_ok", "leak_ok"))
    rows = [json.loads(l) for l in out.read_text().splitlines()]
    assert [r["kind"] for r in rows] == ["exploration_seed", "reported_arms"]
    rep = rows[1]
    for M in ("120", "200"):
        L = rep["loads"][M]
        assert {"twin_A", "twin_B", "reference", "novel_duty_twin", "duty"} <= set(L)
        assert L["twin_A"]["replay_mismatch"]["replay_only"] == L["twin_A"]["replay_mismatch"]["live_only"] == 0
    assert {"ood", "stress", "wps", "efficiency_final", "M250_rolling"} <= set(rep)
