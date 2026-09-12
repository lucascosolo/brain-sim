"""PRD section 5/6: ui/stage0_results.json is a real, checkable record, not free text."""
import ast
import json
import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_PATH = os.path.join(REPO_ROOT, "ui", "stage0_results.json")

REQUIRED_ENTRY_FIELDS = {"test", "label", "outcome", "tested_commit", "date", "evidence"}
_NODE_SPLIT = re.compile(r"::|\(")
_PLAIN_FUNC = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _load():
    with open(RESULTS_PATH) as fh:
        return json.load(fh)


def _file_functions(path):
    with open(path) as fh:
        tree = ast.parse(fh.read(), filename=path)
    return {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


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


def test_every_entry_test_node_names_existing_file_and_function():
    data = _load()
    for entry in data["entries"]:
        node = entry["test"].split(",")[0].strip()
        m = _NODE_SPLIT.search(node)
        file_part = node[:m.start()] if m else node
        file_part = file_part.strip()
        path = os.path.join(REPO_ROOT, file_part)
        assert os.path.isfile(path), f"{entry['test']!r}: no such file {file_part}"
        if "::" in node:
            func_part = node.split("::", 1)[1]
            func_part = func_part.split("(")[0].strip()
            if _PLAIN_FUNC.match(func_part):
                funcs = _file_functions(path)
                assert func_part in funcs, f"{entry['test']!r}: no function {func_part} in {file_part}"


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


def test_at_least_one_entry_fails_k0_3():
    data = _load()
    fails = [e for e in data["entries"] if e["outcome"] == "fail"]
    assert fails, "stage0 results must not go green by omission (K0.3 stays red)"
