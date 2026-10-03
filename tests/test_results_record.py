"""PRD section 5/6: ui/stage{0,1}_results.json are real, checkable records, not free text."""
import ast
import json
import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_PATH = os.path.join(REPO_ROOT, "ui", "stage0_results.json")
STAGE1_PATH = os.path.join(REPO_ROOT, "ui", "stage1_results.json")

REQUIRED_ENTRY_FIELDS = {"test", "label", "outcome", "tested_commit", "date", "evidence"}
REQUIRED_ENTRY_FIELDS_STAGE1 = REQUIRED_ENTRY_FIELDS | {"stage", "spec"}
_NODE_SPLIT = re.compile(r"::|\(")
_PLAIN_FUNC = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _load(path=RESULTS_PATH):
    with open(path) as fh:
        return json.load(fh)


def _file_functions(path):
    with open(path) as fh:
        tree = ast.parse(fh.read(), filename=path)
    return {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def _assert_node_names_existing_file_and_function(entry, *, allow_unmerged_branch=False):
    """Shared rule: entry['test'] names a real file (and, for a ::function node id,
    a real function in that file). When allow_unmerged_branch is set, a file that
    does not exist on this checkout is tolerated only if the entry's evidence says
    so (the test lived on a branch that was never merged to master)."""
    node = entry["test"].split(",")[0].strip()
    m = _NODE_SPLIT.search(node)
    file_part = node[:m.start()] if m else node
    file_part = file_part.strip()
    path = os.path.join(REPO_ROOT, file_part)

    if not os.path.isfile(path):
        assert allow_unmerged_branch, f"{entry['test']!r}: no such file {file_part}"
        assert "branch" in entry.get("evidence", "").lower(), (
            f"{entry['test']!r}: file {file_part} does not exist on this checkout, "
            "so evidence must explain it (mention 'branch', e.g. never merged to master)"
        )
        return

    if "::" in node:
        func_part = node.split("::", 1)[1]
        func_part = func_part.split("(")[0].strip()
        if _PLAIN_FUNC.match(func_part):
            funcs = _file_functions(path)
            assert func_part in funcs, f"{entry['test']!r}: no function {func_part} in {file_part}"


def test_stage0_results_json_parses():
    data = _load()
    assert isinstance(data, dict)
    assert "entries" in data and isinstance(data["entries"], list)
    assert len(data["entries"]) > 0


def test_every_entry_has_schema_fields():
    data = _load()
    for entry in data["entries"]:
        missing = REQUIRED_ENTRY_FIELDS - set(entry)
        assert not missing, f"{entry.get('test')!r} missing {missing}"
        assert entry["outcome"] in ("pass", "fail")


def test_stage0_entries_never_carry_reject():
    """The stage-1 'reject' outcome must not leak into the stricter stage-0 rule."""
    data = _load()
    for entry in data["entries"]:
        assert entry["outcome"] != "reject", (
            f"{entry.get('test')!r}: stage0 outcomes are pass/fail only, got 'reject'"
        )


def test_every_entry_test_node_names_existing_file_and_function():
    data = _load()
    for entry in data["entries"]:
        _assert_node_names_existing_file_and_function(entry, allow_unmerged_branch=False)


def test_carried_forward_entries_differ_from_current_run_commit():
    data = _load()
    entries = data["entries"]
    current_commits = {e["tested_commit"] for e in entries if not e.get("carried_forward")}
    assert current_commits, "no non-carried-forward entries to establish the current run commit"
    carried = [e for e in entries if e.get("carried_forward")]
    if not carried:
        return  # nothing carried forward: every entry was measured at the current commit
    for e in carried:
        assert e["tested_commit"] not in current_commits, e["test"]


def test_at_least_one_entry_fails():
    data = _load()
    fails = [e for e in data["entries"] if e["outcome"] == "fail"]
    assert fails, "stage0 results must not go green by omission (K0.1 and K0.4 are red)"


# ---------------------------------------------------------------------------
# stage1: ui/stage1_results.json
# ---------------------------------------------------------------------------


def test_stage1_results_json_parses():
    data = _load(STAGE1_PATH)
    assert isinstance(data, dict)
    assert "entries" in data and isinstance(data["entries"], list)
    assert len(data["entries"]) > 0


def test_stage1_schema_string():
    data = _load(STAGE1_PATH)
    assert data.get("schema") == "stage1-results/1", data.get("schema")


def test_every_stage1_entry_has_schema_fields():
    data = _load(STAGE1_PATH)
    for entry in data["entries"]:
        missing = REQUIRED_ENTRY_FIELDS_STAGE1 - set(entry)
        assert not missing, f"{entry.get('test')!r} missing {missing}"
        assert entry["outcome"] in ("pass", "fail", "reject"), (
            f"{entry.get('test')!r}: outcome {entry['outcome']!r} not in pass/fail/reject"
        )
        assert entry["stage"] == 1, f"{entry.get('test')!r}: stage must be int 1, got {entry['stage']!r}"
        assert isinstance(entry["spec"], str) and entry["spec"].startswith("8."), (
            f"{entry.get('test')!r}: spec must start with '8.', got {entry.get('spec')!r}"
        )


def test_every_stage1_entry_test_node_names_existing_file_or_explains_branch():
    data = _load(STAGE1_PATH)
    for entry in data["entries"]:
        _assert_node_names_existing_file_and_function(entry, allow_unmerged_branch=True)


def test_stage1_at_least_one_entry_fails_or_rejects():
    data = _load(STAGE1_PATH)
    not_green = [e for e in data["entries"] if e["outcome"] in ("fail", "reject")]
    assert not_green, "stage1 results must not go green by omission"
