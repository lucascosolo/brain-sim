"""Operators: the things the executive can try for a subgoal, cheapest tier first.

Each operator says whether it applies to a failing test (from observations only) and, if so,
returns a plan: the exact edits it would make, with the evidence that justified them. The
executive, not the operator, applies edits, predicts their effect and judges the outcome.

Tiers (lower is cheaper; selection is by tier, then by remembered success):
  0 memory        reuse a verified fix for this exact failure on byte-identical code
  2 skill         a known multi-step procedure over reflex capabilities, no model
  5 deliberation  a language model proposes edits; used only when nothing cheaper applies
Tier 1 (reflex) is sensing and evidence: test runs and index queries the others call.
Tiers 3 (cheap evidence gathering as its own step) and 4 (small local model) have no
operators yet; the ladder keeps their slots so adding one changes no ordering logic.
"""
from __future__ import annotations

import io
import re
import tokenize
from dataclasses import dataclass, field

from reflex import READ_ONLY

TIER_MEMORY, TIER_REFLEX, TIER_SKILL, TIER_EVIDENCE, TIER_SMALL_MODEL, TIER_DELIBERATION = 0, 1, 2, 3, 4, 5
TIER_NAMES = {0: "memory", 1: "reflex", 2: "skill", 3: "evidence", 4: "small_model", 5: "deliberation"}
NAME_ERROR_RE = re.compile(r"^name '(?P<name>[A-Za-z_]\w*)' is not defined")


@dataclass
class Plan:
    edits: list[dict]
    rationale: str
    evidence: dict = field(default_factory=dict)
    llm: dict | None = None          # usage and confidence when a model produced the plan


@dataclass
class Applicability:
    ok: bool
    reason: str
    plan: Plan | None = None


def _repo_frame(ex, failure: dict) -> dict | None:
    """Innermost traceback frame in a file the executive may edit."""
    for f in reversed(failure.get("frames") or []):
        if f.get("path") and not ex.ws.is_protected(f["path"]):
            return f
    return None


def _edit_distance(a: str, b: str) -> int:
    """Damerau-Levenshtein (optimal string alignment)."""
    d = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        d[i][0] = i
    for j in range(len(b) + 1):
        d[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            cost = a[i - 1] != b[j - 1]
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[len(a)][len(b)]


def _replace_name_on_line(line_text: str, old: str, new: str) -> str | None:
    """Replace NAME tokens equal to `old` on one source line; None if the line does not tokenize."""
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(line_text + "\n").readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return None
    out, last = [], 0
    for t in toks:
        if t.type == tokenize.NAME and t.string == old:
            col0, col1 = t.start[1], t.end[1]
            out.append(line_text[last:col0] + new)
            last = col1
    if not out:
        return None
    return "".join(out) + line_text[last:]


class Operator:
    name = "operator"
    tier = TIER_SKILL
    uses_llm = False

    def applicable(self, ex, subgoal: dict, failure: dict) -> Applicability:
        raise NotImplementedError


class RecallVerifiedFix(Operator):
    """Memory first: the same failure on the same bytes was fixed before and verified."""
    name, tier = "recall_verified_fix", TIER_MEMORY

    def applicable(self, ex, subgoal, failure):
        ep = ex.memory.find_verified_fix(subgoal["signature"]["key"], subgoal["context_hash"])
        if ep is None:
            return Applicability(False, "no verified episode for this signature and code")
        return Applicability(True, f"episode from task {ep['task_id']} fixed this exact failure",
                             Plan(ep["edits"], f"replay verified fix from {ep['task_id']} ({ep['operator']})",
                                  {"episode_recorded_at": ep["recorded_at"], "episode_operator": ep["operator"]}))


class FixNameTypo(Operator):
    """NameError for a name one or two edits away from exactly one name in scope."""
    name, tier = "fix_name_typo", TIER_SKILL

    def applicable(self, ex, subgoal, failure):
        if failure.get("exc_type") != "NameError":
            return Applicability(False, "not a NameError")
        m = NAME_ERROR_RE.match(failure.get("exc_message") or "")
        frame = _repo_frame(ex, failure)
        if not m or frame is None:
            return Applicability(False, "no undefined name in an editable frame")
        bad = m["name"]
        scope = ex.reflex("py.names_in_scope", READ_ONLY, path=frame["path"], line=frame["line"])
        if not scope.ok or not scope.data["ok"]:
            return Applicability(False, "scope unavailable")
        limit = 1 if len(bad) <= 4 else 2
        names = set(scope.data["names"]) | set(scope.data["builtins"])
        dist = sorted((_edit_distance(bad, n), n) for n in names if n != bad)
        best = [n for d, n in dist if d == dist[0][0]] if dist else []
        if not dist or dist[0][0] > limit:
            return Applicability(False, f"no name within {limit} edits of {bad!r}")
        if len(best) != 1:
            return Applicability(False, f"ambiguous: {best[:5]} are equally close to {bad!r}")
        good = best[0]
        span = ex.reflex("fs.read_span", READ_ONLY, path=frame["path"], start_line=frame["line"], end_line=frame["line"])
        new_line = _replace_name_on_line(span.data["text"], bad, good) if span.ok else None
        if new_line is None:
            return Applicability(False, f"{bad!r} not found as a name token on {frame['path']}:{frame['line']}")
        return Applicability(True, f"{bad!r} → {good!r} (edit distance {dist[0][0]}, unique)",
                             Plan([{"path": frame["path"], "old": span.data["text"], "new": new_line}],
                                  f"rename {bad} to {good} on {frame['path']}:{frame['line']}",
                                  {"undefined": bad, "replacement": good, "distance": dist[0][0],
                                   "frame": f"{frame['path']}:{frame['line']}"}))


class AddMissingImport(Operator):
    """NameError for a name defined at top level in exactly one other workspace module."""
    name, tier = "add_missing_import", TIER_SKILL

    def applicable(self, ex, subgoal, failure):
        if failure.get("exc_type") != "NameError":
            return Applicability(False, "not a NameError")
        m = NAME_ERROR_RE.match(failure.get("exc_message") or "")
        frame = _repo_frame(ex, failure)
        if not m or frame is None:
            return Applicability(False, "no undefined name in an editable frame")
        bad = m["name"]
        defs = ex.reflex("py.module_level_definitions", READ_ONLY, name=bad)
        if not defs.ok:
            return Applicability(False, "index unavailable")
        cands = [d for d in defs.data["definitions"]
                 if d["path"] != frame["path"] and d["module"] and not ex.ws.is_protected(d["path"])]
        if len(cands) != 1:
            return Applicability(False, f"{len(cands)} candidate modules define {bad!r} (need exactly one)")
        module = cands[0]["module"]
        text = ex.ws.read_text(frame["path"])
        lines = text.splitlines(keepends=True)
        anchor = _import_anchor(lines)
        stmt = f"from {module} import {bad}\n"
        if anchor is None:
            # No import block: insert before the first non-blank line that occurs exactly once,
            # so the edit has a unique anchor (E5: files starting with blank lines were refused).
            idx = next((i for i, l in enumerate(lines) if l.strip() and text.count(l) == 1), None)
            if idx is None:
                return Applicability(False, "no unique line to anchor the import on")
            old = "".join(lines[:idx + 1])          # leading blank lines + the anchor: unique prefix
            gap = "\n\n" if lines[idx].startswith(("def ", "class ", "async def ", "@")) else ""
            new = stmt + gap + lines[idx]
        else:
            old, new = lines[anchor], lines[anchor] + stmt
        if text.count(old) != 1:
            return Applicability(False, "anchor line is not unique; refusing an ambiguous edit")
        return Applicability(True, f"{bad!r} is defined only in {module}",
                             Plan([{"path": frame["path"], "old": old, "new": new}],
                                  f"add `from {module} import {bad}` to {frame['path']}",
                                  {"undefined": bad, "module": module, "definition": f"{cands[0]['path']}:{cands[0]['line']}"}))


def _import_anchor(lines: list[str]) -> int | None:
    """Index of the last top-level import line in the leading import block, if any."""
    last = None
    for i, line in enumerate(lines):
        if line.startswith(("import ", "from ")) and not line.rstrip().endswith(("(", "\\")):
            last = i
        elif line.strip() and not line.startswith(("#", '"""', "'''")) and last is not None:
            break
    return last


class DeliberatePatch(Operator):
    """Impasse resolution: a Deliberator proposes edits from a bounded projection of the state."""
    name, tier, uses_llm = "deliberate_patch", TIER_DELIBERATION, True

    def applicable(self, ex, subgoal, failure):
        if ex.deliberator is None:
            return Applicability(False, "no deliberator configured")
        b = ex.state["budgets"]
        used_here = sum(1 for a in subgoal["attempts"] if a["operator"] == self.name)
        if used_here >= b["max_deliberations_per_subgoal"]:
            return Applicability(False, f"deliberation budget for this subgoal spent ({used_here})")
        if ex.state["counters"]["deliberations"] >= b["max_deliberations_total"]:
            return Applicability(False, "total deliberation budget spent")
        return Applicability(True, "impasse: no cheaper operator applies")
