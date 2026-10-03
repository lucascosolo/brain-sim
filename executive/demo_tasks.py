"""Small repository tasks for exercising the loop, with scripted stand-ins for the model.

Each task builds a tiny Python package plus pytest tests in a directory the caller gives.
The scripted deliberators answer like a model would, from the projection only (they read
`request.projection`, never the disk), so the executive's projection is what is under test.
They measure the loop's mechanics, not a model's skill: a real model may answer worse.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

from .deliberation import DeliberationRequest, ScriptedDeliberator

STATS = '''\
def mean(xs):
    total = sum(xs)
    return total / len(xs)


def median(xs):
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    if n % 2:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2
'''

TESTS = '''\
from calc.stats import mean, median


def test_mean():
    assert mean([1, 2, 3]) == 2


def test_median_odd():
    assert median([3, 1, 2]) == 2


def test_median_even():
    assert median([4, 1, 3, 2]) == 2.5
'''

REPORT = '''\
def summary(xs):
    return f"mean={mean(xs):.1f}"
'''

REPORT_TESTS = '''\
from calc.report import summary


def test_summary():
    assert summary([1, 2, 3]) == "mean=2.0"
'''


def _write(root: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(text))
    return root


def base_files() -> dict[str, str]:
    return {"conftest.py": "", "calc/__init__.py": "", "calc/stats.py": STATS, "tests/test_stats.py": TESTS}


def task_passing(root: Path) -> Path:
    return _write(root, base_files())


def task_typo(root: Path) -> Path:
    files = base_files()
    files["calc/stats.py"] = STATS.replace("return total / len(xs)", "return totl / len(xs)")
    return _write(root, files)


def task_missing_import(root: Path) -> Path:
    files = base_files()
    files.update({"calc/report.py": REPORT, "tests/test_report.py": REPORT_TESTS})
    return _write(root, files)


def task_logic_bug(root: Path) -> Path:
    files = base_files()
    files["calc/stats.py"] = STATS.replace("return (s[mid - 1] + s[mid]) / 2", "return (s[mid] + s[mid + 1]) / 2")
    return _write(root, files)


def task_no_tests(root: Path) -> Path:
    return _write(root, {"calc/__init__.py": "", "calc/stats.py": STATS})


GOOD_FIX = {"path": "calc/stats.py", "old": "return (s[mid] + s[mid + 1]) / 2",
            "new": "return (s[mid - 1] + s[mid]) / 2"}
# Fixes the even case but breaks the odd case (and is wrong): a plausible bad model answer.
BAD_FIX = {"path": "calc/stats.py", "old": "    if n % 2:\n        return s[mid]\n    return (s[mid] + s[mid + 1]) / 2",
           "new": "    return (s[mid - 1] + s[mid]) / 2"}


def _source(request: DeliberationRequest, path: str) -> str:
    return next(f["text"] for f in request.projection["files"] if f["path"] == path)


def good_model() -> ScriptedDeliberator:
    """Answers the median bug correctly, but only if the projection actually shows the bug."""
    def answer(req: DeliberationRequest) -> dict:
        assert "s[mid + 1]" in _source(req, "calc/stats.py"), "projection did not include the buggy line"
        return {"diagnosis": "even-length median averages the wrong pair", "confidence": 0.9, "edits": [GOOD_FIX]}
    return ScriptedDeliberator(answer, "scripted-good")


def wrong_then_right_model() -> ScriptedDeliberator:
    """First answer breaks a passing test; the second, which sees the rejected attempt, is right."""
    def answer(req: DeliberationRequest) -> dict:
        if not req.projection["previous_attempts"]:
            return {"diagnosis": "drop the odd branch", "confidence": 0.85, "edits": [BAD_FIX]}
        assert req.projection["previous_attempts"][-1]["regressions"], "rejected attempt lost its regressions"
        return {"diagnosis": "keep the odd branch; average the two middle values", "confidence": 0.8,
                "edits": [GOOD_FIX]}
    return ScriptedDeliberator(answer, "scripted-wrong-then-right")


def test_editing_model() -> ScriptedDeliberator:
    """Tries to make the test pass by editing the test: the workspace must refuse it."""
    def answer(req: DeliberationRequest) -> dict:
        return {"diagnosis": "the test expectation is wrong", "confidence": 0.95,
                "edits": [{"path": "tests/test_stats.py", "old": "== 2.5", "new": "== 3.0"}]}
    return ScriptedDeliberator(answer, "scripted-test-editor")


def malformed_model() -> ScriptedDeliberator:
    return ScriptedDeliberator(lambda req: {"answer": "just change it"}, "scripted-malformed")


def sprawling_model() -> ScriptedDeliberator:
    """Proposes a rewrite far larger than the bug: the scope guard must refuse it unapplied."""
    def answer(req: DeliberationRequest) -> dict:
        src = _source(req, "calc/stats.py")
        return {"diagnosis": "rewrite the module", "confidence": 0.9,
                "edits": [{"path": "calc/stats.py", "old": src, "new": src.replace("s[mid + 1]", "s[mid - 1]") + "\n" * 40}]}
    return ScriptedDeliberator(answer, "scripted-sprawling")
