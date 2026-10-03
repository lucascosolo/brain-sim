"""Deliberators: language models as tools the executive calls at an impasse, and nowhere else.

A Deliberator receives a bounded, structured projection of the state and must return JSON
matching a declared schema. It has no tools and no access to the workspace: everything it
proposes comes back to the executive as data, which validates it and applies it through
reflex-layer capabilities, or refuses it. Model output never chooses a command.

Implementations:
  ScriptedDeliberator   a function stands in for the model (tests, demos)
  ReplayDeliberator     answers from a cassette of recorded responses, keyed by request fingerprint
  RecordingDeliberator  wraps another deliberator and appends every exchange to a cassette
  ClaudeCLIDeliberator  `claude -p` with tools disabled and a JSON schema (not yet run live)
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol

PATCH_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["diagnosis", "confidence", "edits"],
    "properties": {
        "diagnosis": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "edits": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["path", "old", "new"],
            "properties": {"path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}}}},
    },
}


@dataclass
class DeliberationRequest:
    purpose: str
    projection: dict
    response_schema: dict

    def fingerprint(self) -> str:
        blob = json.dumps({"purpose": self.purpose, "projection": self.projection}, sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()[:24]


@dataclass
class DeliberationResponse:
    ok: bool
    content: dict | None
    deliberator: str
    model: str | None = None
    error: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: float = 0.0
    duration_ms: float = 0.0
    extra: dict = field(default_factory=dict)

    def usage(self) -> dict:
        return {"input_tokens": self.input_tokens, "output_tokens": self.output_tokens,
                "cache_read_tokens": self.cache_read_tokens, "cache_write_tokens": self.cache_write_tokens,
                "cost_usd": self.cost_usd, "duration_ms": round(self.duration_ms, 1)}


class Deliberator(Protocol):
    name: str

    def deliberate(self, request: DeliberationRequest) -> DeliberationResponse: ...


def validate_patch(content: object) -> str | None:
    """Return an error string if `content` is not a PATCH_SCHEMA object, else None."""
    if not isinstance(content, dict):
        return "response is not an object"
    if set(content) != {"diagnosis", "confidence", "edits"}:
        return f"response keys {sorted(content)} are not exactly diagnosis, confidence, edits"
    if not isinstance(content["diagnosis"], str):
        return "diagnosis is not a string"
    c = content["confidence"]
    if not isinstance(c, (int, float)) or isinstance(c, bool) or not 0 <= c <= 1:
        return "confidence is not a number in [0, 1]"
    if not isinstance(content["edits"], list) or not content["edits"]:
        return "edits is not a non-empty list"
    for e in content["edits"]:
        if not isinstance(e, dict) or set(e) != {"path", "old", "new"} or not all(isinstance(e[k], str) for k in e):
            return f"malformed edit {e!r}"
    return None


class ScriptedDeliberator:
    def __init__(self, fn: Callable[[DeliberationRequest], dict], name: str = "scripted"):
        self.fn, self.name = fn, name
        self.calls: list[DeliberationRequest] = []

    def deliberate(self, request: DeliberationRequest) -> DeliberationResponse:
        self.calls.append(request)
        return DeliberationResponse(True, self.fn(request), self.name, model="scripted")


class ReplayDeliberator:
    def __init__(self, cassette: Path | str):
        self.name = "replay"
        self.records = {}
        for line in Path(cassette).read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                self.records[rec["fingerprint"]] = rec

    def deliberate(self, request: DeliberationRequest) -> DeliberationResponse:
        rec = self.records.get(request.fingerprint())
        if rec is None:
            return DeliberationResponse(False, None, self.name, error=f"no recorded response for {request.fingerprint()}")
        return DeliberationResponse(True, rec["content"], self.name, model=rec.get("model"),
                                    extra={"replayed_usage": rec.get("usage")})


class RecordingDeliberator:
    def __init__(self, inner: Deliberator, cassette: Path | str):
        self.inner, self.cassette, self.name = inner, Path(cassette), f"recording({inner.name})"

    def deliberate(self, request: DeliberationRequest) -> DeliberationResponse:
        resp = self.inner.deliberate(request)
        if resp.ok:
            self.cassette.parent.mkdir(parents=True, exist_ok=True)
            with self.cassette.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"fingerprint": request.fingerprint(), "purpose": request.purpose,
                                    "projection": request.projection, "content": resp.content,
                                    "model": resp.model, "usage": resp.usage()}, sort_keys=True) + "\n")
        return resp


SYSTEM_PROMPT = (
    "You are a reasoning component inside a larger program. You have no tools and cannot act. "
    "You receive a JSON description of a failing test and the relevant source. Reply only with "
    "JSON matching the schema: a short diagnosis, your confidence that the edits make the failing "
    "test pass without breaking others, and search/replace edits. Each `old` must occur exactly once "
    "in its file. Never edit test files. Prefer the smallest correct change.")


class ClaudeCLIDeliberator:
    """`claude -p` as a tool-less, schema-bound reasoning call.

    Status: run live from 2026-10-03 (owner approved the pilot spend); `structured_output` carries
    the schema result. Effort defaults to low: in E2, default-effort Haiku spent 4k-12k output
    tokens (mostly thinking) per call. The flags it relies
    on: --print, --output-format json, --tools "" (no tools), --json-schema, --model,
    --max-budget-usd, --no-session-persistence, --system-prompt. It runs in `workdir`, an
    empty directory the caller owns (never the workspace), so no project instructions are
    loaded; the directory is created if missing and never cleaned up by this code.
    """

    def __init__(self, workdir: Path | str, model: str = "haiku", max_budget_usd: float = 0.25,
                 timeout_seconds: float = 180.0, executable: str = "claude", effort: str | None = "low"):
        self.workdir = Path(workdir)
        self.effort = effort
        self.model, self.max_budget_usd, self.timeout = model, max_budget_usd, timeout_seconds
        self.executable = shutil.which(executable) or executable
        self.name = f"claude-cli:{model}"

    def deliberate(self, request: DeliberationRequest) -> DeliberationResponse:
        prompt = json.dumps({"purpose": request.purpose, **request.projection}, indent=1)
        argv = [self.executable, "-p", prompt, "--output-format", "json", "--model", self.model,
                "--tools", "", "--json-schema", json.dumps(request.response_schema),
                "--max-budget-usd", str(self.max_budget_usd), "--no-session-persistence",
                "--system-prompt", SYSTEM_PROMPT] + (["--effort", self.effort] if self.effort else [])
        t0 = time.monotonic()
        self.workdir.mkdir(parents=True, exist_ok=True)
        try:
            proc = subprocess.run(argv, cwd=self.workdir, capture_output=True, text=True, timeout=self.timeout, shell=False)
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return DeliberationResponse(False, None, self.name, model=self.model, error=f"{type(e).__name__}: {e}",
                                        duration_ms=(time.monotonic() - t0) * 1000)
        ms = (time.monotonic() - t0) * 1000
        try:
            out = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return DeliberationResponse(False, None, self.name, model=self.model, duration_ms=ms,
                                        error=f"exit {proc.returncode}; stdout is not JSON: {proc.stdout[-300:]} {proc.stderr[-300:]}")
        usage = out.get("usage") or {}
        content = out.get("structured_output")
        if content is None and isinstance(out.get("result"), str):
            try:
                content = json.loads(out["result"])
            except json.JSONDecodeError:
                content = None
        resp = DeliberationResponse(content is not None and not out.get("is_error"), content, self.name,
                                    model=self.model, duration_ms=ms,
                                    input_tokens=int(usage.get("input_tokens") or 0),
                                    output_tokens=int(usage.get("output_tokens") or 0),
                                    cache_read_tokens=int(usage.get("cache_read_input_tokens") or 0),
                                    cache_write_tokens=int(usage.get("cache_creation_input_tokens") or 0),
                                    cost_usd=float(out.get("total_cost_usd") or 0.0))
        if not resp.ok:
            resp.error = f"no structured output (is_error={out.get('is_error')}, subtype={out.get('subtype')})"
        return resp
