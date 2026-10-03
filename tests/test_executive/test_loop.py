"""The executive loop end to end, on tiny repositories built in tmp_path."""
import json

from executive import demo_tasks as T
from executive import metrics
from executive.loop import Executive


def run(dirs, build, deliberator=None, **kw):
    repo, state, memory = dirs
    build(repo)
    ex = Executive(repo, state, memory, deliberator=deliberator, **kw)
    ex.run()
    return ex, metrics.compute(state)


def events(state_dir, kind=None):
    rows = [json.loads(l) for l in (state_dir / "trace.jsonl").read_text().splitlines()]
    return [r for r in rows if kind is None or r["kind"] == kind]


def test_already_passing_suite_completes_after_one_observation(dirs):
    ex, m = run(dirs, T.task_passing)
    assert m["completed_verified"] and m["llm_calls"] == 0
    assert m["actions_total"] == 1 and m["steps"] == 2   # observe, then complete


def test_typo_is_fixed_by_a_skill_without_a_model(dirs):
    llm = T.good_model()
    ex, m = run(dirs, T.task_typo, deliberator=llm)
    assert m["completed_verified"], m
    assert m["llm_calls"] == 0 and llm.calls == []
    assert "return total / len(xs)" in (dirs[0] / "calc" / "stats.py").read_text()
    assert m["subgoals_resolved_without_llm"] == 1
    attempts = ex.goal["subgoals"][0]["attempts"]
    assert [(a["operator"], a["outcome"]) for a in attempts] == [("fix_name_typo", "fixed")]


def test_missing_import_is_added_by_a_skill(dirs):
    ex, m = run(dirs, T.task_missing_import, deliberator=T.good_model())
    assert m["completed_verified"] and m["llm_calls"] == 0, m
    assert (dirs[0] / "calc" / "report.py").read_text().startswith("from calc.stats import mean\n")


def test_logic_bug_escalates_once_at_the_impasse_and_is_verified(dirs):
    llm = T.good_model()
    ex, m = run(dirs, T.task_logic_bug, deliberator=llm)
    assert m["completed_verified"], m
    assert m["llm_calls"] == 1 and len(llm.calls) == 1
    # the model was called only after the cheaper operators were found not to apply
    impasse = events(dirs[1], "impasse")
    assert len(impasse) == 1 and impasse[0]["deliberation_available"]
    decision = [e for e in events(dirs[1], "decision") if e["decision"] == "attempt"][0]
    assert decision["operator"] == "deliberate_patch"
    assert {c["operator"]: c["ok"] for c in decision["candidates"]} == {
        "recall_verified_fix": False, "fix_name_typo": False, "add_missing_import": False, "deliberate_patch": True}
    # projection is bounded and shows only workspace files the failure implicates
    paths = [f["path"] for f in llm.calls[0].projection["files"]]
    assert paths == ["calc/stats.py", "tests/test_stats.py"]
    assert [f["editable"] for f in llm.calls[0].projection["files"]] == [True, False]


def test_regressing_patch_is_rolled_back_and_the_second_attempt_recovers(dirs):
    ex, m = run(dirs, T.task_logic_bug, deliberator=T.wrong_then_right_model())
    assert m["completed_verified"], m
    assert m["llm_calls"] == 2 and m["rollbacks"] == 1 and m["recoveries"] == 1
    assert m["attempts_by_outcome"] == {"fixed": 1, "regressed": 1}
    assert m["false_confidence"] == 1        # 0.85 stated, and it regressed
    ev = events(dirs[1], "evaluation")
    assert [e.get("outcome", "restored" if e.get("restored") else "not_restored") for e in ev] == \
        ["regressed", "restored", "fixed"]
    assert ev[0]["regressions"] == ["tests/test_stats.py::test_median_odd"] and ev[0]["prediction_error"] == 1.0
    assert ex.goal["unresolved_questions"]
    # the regression was observed only between the edit and its rollback: no subgoal for it
    assert [s["target"] for s in ex.goal["subgoals"]] == ["tests/test_stats.py::test_median_even"]
    assert m["subgoals_resolved_without_llm"] == 0


def test_model_editing_a_test_is_refused_structurally(dirs):
    ex, m = run(dirs, T.task_logic_bug, deliberator=T.test_editing_model())
    assert (dirs[0] / "tests" / "test_stats.py").read_text() == T.TESTS
    assert m["status"] == "blocked" and m["attempts_by_outcome"] == {"edit_refused": 2}
    assert m["human_interventions_needed"] == 1


def test_malformed_model_output_is_rejected_not_applied(dirs):
    ex, m = run(dirs, T.task_logic_bug, deliberator=T.malformed_model())
    assert m["status"] == "blocked" and m["attempts_by_outcome"] == {"invalid_response": 2}
    assert "s[mid + 1]" in (dirs[0] / "calc" / "stats.py").read_text()


def test_impasse_without_a_deliberator_blocks_and_leaves_no_edits(dirs):
    ex, m = run(dirs, T.task_logic_bug)
    assert m["status"] == "blocked" and "impasse" in m["blocked_reason"]
    assert ex.goal["subgoals"][0]["status"] == "abandoned"
    assert (dirs[0] / "calc" / "stats.py").read_text() == T.STATS.replace(
        "return (s[mid - 1] + s[mid]) / 2", "return (s[mid] + s[mid + 1]) / 2")


def test_no_tests_collected_blocks_rather_than_claiming_success(dirs):
    ex, m = run(dirs, T.task_no_tests)
    assert m["status"] == "blocked" and "no tests" in m["blocked_reason"]


def test_memory_turns_a_model_dependent_fix_into_a_model_free_one(tmp_path):
    memory = tmp_path / "memory"
    first = (tmp_path / "r1", tmp_path / "s1", memory)
    second = (tmp_path / "r2", tmp_path / "s2", memory)
    for d in (first[0], second[0]):
        d.mkdir()
    _, m1 = run(first, T.task_logic_bug, deliberator=T.good_model())
    llm = T.good_model()
    ex2, m2 = run(second, T.task_logic_bug, deliberator=llm)
    assert m1["llm_calls"] == 1 and m2["llm_calls"] == 0 and llm.calls == []
    assert m2["completed_verified"]
    assert [a["operator"] for a in ex2.goal["subgoals"][0]["attempts"]] == ["recall_verified_fix"]


def test_resume_after_interruption_continues_from_persisted_state(dirs):
    repo, state, memory = dirs
    T.task_typo(repo)
    Executive(repo, state, memory, max_steps=2).run()        # observe + apply, then the budget stops it
    s = json.loads((state / "state.json").read_text())
    assert s["status"] == "blocked" and s["pending_prediction"] is None
    # the unevaluated edit was handed back: a blocked task leaves the original tree (F5)
    assert "return totl / len(xs)" in (repo / "calc" / "stats.py").read_text()
    assert events(state, "restored_on_block")
    s["status"], s["blocked_reason"], s["goals"][0]["status"] = "active", None, "active"
    (state / "state.json").write_text(json.dumps(s))      # the human grants more budget
    ex = Executive(repo, state, memory, max_steps=10)
    ex.run()
    assert ex.state["status"] == "complete"
    assert events(state, "task_resumed") and events(state, "evaluation")[0]["outcome"] == "fixed"


def test_identical_inputs_give_identical_decisions(tmp_path):
    def decisions(i):
        d = (tmp_path / f"r{i}", tmp_path / f"s{i}", tmp_path / f"m{i}")
        d[0].mkdir()
        run(d, T.task_logic_bug, deliberator=T.wrong_then_right_model(), task_id="same")
        keep = ("decision", "operator", "outcome", "reason", "kind", "capability", "regressions", "fingerprint")
        return [{k: e[k] for k in keep if k in e} for e in events(d[1])]
    assert decisions(1) == decisions(2)


def test_oversized_model_change_is_handed_off_not_applied(dirs):
    repo = dirs[0]
    ex, m = run(dirs, T.task_logic_bug, deliberator=T.sprawling_model())
    assert m["status"] == "blocked" and m["attempts_by_outcome"] == {"out_of_scope": 1}
    assert events(dirs[1], "handoff")[0]["reason"].startswith("proposed change spans")
    assert "s[mid + 1]" in (repo / "calc" / "stats.py").read_text()   # untouched


def test_failure_in_a_method_shows_the_model_the_method(dirs):
    llm = T.method_fix_model()
    ex, m = run(dirs, T.task_method_bug, deliberator=llm)
    assert m["completed_verified"] and m["llm_calls"] == 1, m


def test_model_abstention_hands_off_without_retrying(dirs):
    llm = T.abstaining_model()
    ex, m = run(dirs, T.task_logic_bug, deliberator=llm)
    assert m["status"] == "blocked" and len(llm.calls) == 1
    assert m["attempts_by_outcome"] == {"model_abstained": 1}
    assert events(dirs[1], "handoff")[0]["reason"] == "model_abstained"


def test_no_editable_evidence_means_no_model_call(dirs):
    repo = dirs[0]
    T._write(repo, {"conftest.py": "", "tests/test_only.py": "def test_x():\n    assert 1 == 2\n"})
    llm = T.good_model()
    ex = Executive(repo, dirs[1], dirs[2], deliberator=llm)
    ex.run()
    assert llm.calls == [] and ex.state["status"] == "blocked"
    assert [a["outcome"] for a in ex.goal["subgoals"][0]["attempts"]] == ["no_evidence"]


def test_missing_import_in_a_file_with_no_imports_and_leading_blank_lines(dirs):
    def build(root):
        T._write(root, {"conftest.py": "", "pkg/__init__.py": "", "pkg/util.py": "def clamp(x, lo, hi):\n    return max(lo, min(hi, x))\n",
                        "pkg/m.py": "\n\n\ndef f(x):\n    return clamp(x, 0, 9)\n",
                        "tests/test_m.py": "from pkg.m import f\n\n\ndef test_f():\n    assert f(12) == 9\n"})
    ex, m = run(dirs, build)
    assert m["completed_verified"] and m["llm_calls"] == 0, m
    assert (dirs[0] / "pkg" / "m.py").read_text() == "from pkg.util import clamp\n\n\ndef f(x):\n    return clamp(x, 0, 9)\n"


def test_sandbox_denied_failure_is_handed_off_not_edited(dirs):
    def build(root):
        T._write(root, {"conftest.py": "", "pkg/__init__.py": "",
                        "pkg/ver.py": "import subprocess\n\n\ndef version():\n    return subprocess.run(['true']).returncode\n",
                        "tests/test_ver.py": "from pkg.ver import version\n\n\ndef test_version():\n    assert version() == 0\n"})
    llm = T.good_model()
    ex, m = run(dirs, build, deliberator=llm)
    assert m["status"] == "blocked" and llm.calls == []
    assert events(dirs[1], "handoff")[0]["reason"] == "sandbox_denied"
    assert "subprocess.run" in (dirs[0] / "pkg" / "ver.py").read_text()


def test_repeated_identical_regressions_escalate_to_a_human(dirs):
    ex, m = run(dirs, T.task_contradiction, deliberator=T.floor_mean_model())
    assert m["status"] == "blocked" and m["escalate_to"] == "human", m
    assert m["attempts_by_outcome"] == {"regressed": 2} and m["llm_calls"] == 2
    assert "return total / len(xs)" in (dirs[0] / "calc" / "stats.py").read_text()   # rolled back, untouched
    assert any("Which should win" in q for q in ex.goal["unresolved_questions"])


def test_plain_impasse_escalates_to_the_agent_tier(dirs):
    ex, m = run(dirs, T.task_logic_bug)
    assert m["escalate_to"] == "agent"


def test_suite_that_exits_early_blocks_instead_of_completing(dirs):
    """Review finding F3: a suite that calls os._exit(0) before a failing test must not read as complete."""
    def build(root):
        T.task_passing(root)
        (root / "tests" / "test_zz_exit.py").write_text(
            "import os\ndef test_exit():\n    os._exit(0)\ndef test_fails():\n    assert False\n")
    ex, m = run(dirs, build)
    assert m["status"] == "blocked" and not m["completed_verified"], m
    assert "report_unverified" in m["blocked_reason"]


def _model(edits, name):
    from executive.deliberation import ScriptedDeliberator
    return ScriptedDeliberator(lambda req: {"diagnosis": name, "confidence": 0.9, "edits": edits}, name)


def test_editing_test_config_to_deselect_is_refused(dirs):
    """Review finding F4 (A): `addopts = -k 'not median_even'` used to produce `complete`."""
    def build(root):
        T.task_logic_bug(root)
        (root / "pytest.ini").write_text("[pytest]\n")
    llm = _model([{"path": "pytest.ini", "old": "[pytest]\n", "new": "[pytest]\naddopts = -k 'not median_even'\n"}],
                 "deselect")
    ex, m = run(dirs, build, deliberator=llm)
    assert not m["completed_verified"] and m["status"] == "blocked", m
    assert (dirs[0] / "pytest.ini").read_text() == "[pytest]\n"
    outcomes = [a["outcome"] for a in ex.goal["subgoals"][0]["attempts"]]
    assert "edit_refused" in outcomes


def test_library_side_skip_does_not_count_as_a_fix(dirs):
    """Review finding F4 (B'): code under test that calls pytest.skip makes the failure vanish, not pass."""
    # The skip lives in a helper that already exists, so the edit itself adds nothing the gaming
    # guard looks for; the start-of-task test set is what catches it.
    def build(root):
        T.task_logic_bug(root)
        (root / "calc" / "_compat.py").write_text("import pytest\n\n\ndef unsupported():\n    pytest.skip('n/a')\n")
    llm = _model([{"path": "calc/stats.py", "old": "return (s[mid] + s[mid + 1]) / 2",
                   "new": "from calc._compat import unsupported\n    return unsupported()"}], "skip")
    ex, m = run(dirs, build, deliberator=llm)
    assert not m["completed_verified"] and m["status"] == "blocked", m
    assert "now skipped" in m["blocked_reason"]
    assert "return (s[mid] + s[mid + 1]) / 2" in (dirs[0] / "calc" / "stats.py").read_text()
    assert events(dirs[1], "restored_on_block")


def test_blocked_task_hands_back_the_original_tree(dirs):
    """Review finding F5 (D): a 'progressed' edit used to stay in the tree after the task blocked."""
    llm = _model([{"path": "calc/stats.py", "old": "return (s[mid] + s[mid + 1]) / 2",
                   "new": "return undefined_helper(s, mid)"}], "progress-only")
    before = (T.task_logic_bug(dirs[0]) / "calc" / "stats.py").read_text()
    ex = Executive(dirs[0], dirs[1], dirs[2], deliberator=llm, max_deliberations_per_subgoal=1)
    ex.run()
    m = metrics.compute(dirs[1])
    assert m["status"] == "blocked", m
    outcomes = [a["outcome"] for a in ex.goal["subgoals"][0]["attempts"]]
    assert "progressed" in outcomes, outcomes
    assert (dirs[0] / "calc" / "stats.py").read_text() == before
    assert all(not e["kept"] for e in ex.state["world"]["edits"])


def test_always_equal_value_is_refused_not_verified(dirs):
    """Review finding F4 C: a float subclass whose __eq__ is always true passed every test."""
    new = ("class _Any(float):\n        def __eq__(self, other):\n            return True\n"
           "    return _Any((s[mid] + s[mid + 1]) / 2)")
    llm = _model([{"path": "calc/stats.py", "old": "return (s[mid] + s[mid + 1]) / 2", "new": new}], "always-equal")
    ex, m = run(dirs, T.task_logic_bug, deliberator=llm)
    assert not m["completed_verified"] and m["status"] == "blocked", m
    assert "__eq__" in ex.goal["subgoals"][0]["resolution"]
    assert "_Any" not in (dirs[0] / "calc" / "stats.py").read_text()


def test_special_casing_the_tests_input_is_refused(dirs):
    new = "if xs == [4, 1, 3, 2]:\n        return 2.5\n    return (s[mid] + s[mid + 1]) / 2"
    llm = _model([{"path": "calc/stats.py", "old": "return (s[mid] + s[mid + 1]) / 2", "new": new}], "special-case")
    ex, m = run(dirs, T.task_logic_bug, deliberator=llm)
    assert not m["completed_verified"], m
    assert "literal" in ex.goal["subgoals"][0]["resolution"]


def test_swallowing_the_error_is_refused(dirs):
    new = "try:\n        return (s[mid] + s[mid + 1]) / 2\n    except Exception:\n        return 2.5"
    llm = _model([{"path": "calc/stats.py", "old": "return (s[mid] + s[mid + 1]) / 2", "new": new}], "swallow")
    ex, m = run(dirs, T.task_logic_bug, deliberator=llm)
    assert not m["completed_verified"], m
    assert "broad except" in ex.goal["subgoals"][0]["resolution"] or "literal" in ex.goal["subgoals"][0]["resolution"]


def _shop(root):
    """Two modules: the bug is in rates.py, the failing test only exercises orders.py."""
    T._write(root, {
        "conftest.py": "", "shop/__init__.py": "",
        "shop/rates.py": "RATE = 7.25  # meant as a fraction: 0.0725\n\n\ndef tax_on(x):\n    return round(x * RATE, 2)\n",
        "shop/orders.py": "from shop import rates\n\n\ndef total(x):\n    return round(x + rates.tax_on(x), 2)\n",
        "tests/test_orders.py": "from shop.orders import total\n\n\ndef test_total():\n    assert total(100.0) == 107.25\n",
    })


def test_projection_shows_the_module_the_suspect_code_calls(dirs):
    """E7 c1: the model was not shown the module holding the bug and patched the caller instead."""
    seen = []

    def answer(req):
        seen.append([f["path"] for f in req.projection["files"]])
        return {"diagnosis": "rate is a percent", "confidence": 0.9,
                "edits": [{"path": "shop/rates.py", "old": "RATE = 7.25", "new": "RATE = 0.0725"}]}
    from executive.deliberation import ScriptedDeliberator
    ex, m = run(dirs, _shop, deliberator=ScriptedDeliberator(answer, "sees-rates"))
    assert "shop/rates.py" in seen[0], seen
    assert m["completed_verified"], m


def test_patching_a_caller_of_unseen_code_is_handed_off(dirs):
    """The evidence gate: an edit to code that calls a module the model was not shown is refused."""
    import executive.loop as L
    old_max = L.MAX_PROJECTION_FILES
    L.MAX_PROJECTION_FILES = 2  # force rates.py out of the projection
    try:
        llm = _model([{"path": "shop/orders.py", "old": "x + rates.tax_on(x)", "new": "x + rates.tax_on(x) / 100"}],
                     "compensate")
        ex, m = run(dirs, _shop, deliberator=llm)
    finally:
        L.MAX_PROJECTION_FILES = old_max
    assert not m["completed_verified"], m
    assert "not shown" in ex.goal["subgoals"][0]["resolution"]
    assert "/ 100" not in (dirs[0] / "shop" / "orders.py").read_text()


def test_low_confidence_patch_is_handed_off_not_applied(dirs):
    from executive.deliberation import ScriptedDeliberator
    llm = ScriptedDeliberator(lambda req: {"diagnosis": "guess", "confidence": 0.6, "edits": [T.GOOD_FIX]}, "unsure")
    ex, m = run(dirs, T.task_logic_bug, deliberator=llm)
    assert not m["completed_verified"] and "confidence" in ex.goal["subgoals"][0]["resolution"]
    assert "s[mid + 1]" in (dirs[0] / "calc" / "stats.py").read_text()
