"""Provenance and the append-only results file (bench/results/plant2.jsonl)."""
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "bench" / "results" / "plant2.jsonl"


def cache_dir(*parts):
    """Derived data lives under ~/.cache/brain-sim (AGENTS.md invariant 5), never /tmp."""
    root = Path(os.environ.get("BRAINSIM_CACHE", Path.home() / ".cache" / "brain-sim"))
    d = root.joinpath("plant2", *parts)
    d.mkdir(parents=True, exist_ok=True)
    return d


def git_state():
    def run(*args):
        return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True).stdout.strip()
    return {"commit": run("rev-parse", "HEAD"), "dirty": bool(run("status", "--porcelain", "--untracked-files=no"))}


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def append(record, path=RESULTS):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
