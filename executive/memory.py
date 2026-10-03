"""Cross-task memory: episodes (what happened) and procedural statistics (how well things work).

episodes.jsonl   append-only; one record per subgoal outcome
procedural.json  per operator, per signature class: counts by outcome; overwritten atomically

Nothing here is a model or an embedding. Retrieval is exact matching on signature keys and
context hashes; the point of the first version is to be checkable, not clever.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from .state import now

OUTCOMES = ("fixed", "progressed", "no_effect", "regressed", "edit_refused", "invalid_response", "llm_error", "out_of_scope", "no_evidence", "model_abstained")


class Memory:
    def __init__(self, directory: Path | str):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.episodes_path = self.dir / "episodes.jsonl"
        self.procedural_path = self.dir / "procedural.json"

    # ---- episodic ----------------------------------------------------------------------
    def record_episode(self, episode: dict) -> None:
        with self.episodes_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"recorded_at": now(), **episode}, sort_keys=True) + "\n")

    def episodes(self) -> list[dict]:
        if not self.episodes_path.exists():
            return []
        return [json.loads(l) for l in self.episodes_path.read_text(encoding="utf-8").splitlines() if l.strip()]

    def find_verified_fix(self, signature_key: str, context_hash: str) -> dict | None:
        """Newest episode that fixed this exact failure on byte-identical code, with its edits."""
        for ep in reversed(self.episodes()):
            if (ep.get("signature_key") == signature_key and ep.get("context_hash") == context_hash
                    and ep.get("outcome") == "fixed" and ep.get("verified") and ep.get("edits")):
                return ep
        return None

    # ---- procedural --------------------------------------------------------------------
    def _load_stats(self) -> dict:
        if not self.procedural_path.exists():
            return {}
        return json.loads(self.procedural_path.read_text(encoding="utf-8"))

    def update_operator(self, operator: str, signature_class: str, outcome: str) -> None:
        stats = self._load_stats()
        cell = stats.setdefault(operator, {}).setdefault(signature_class, {o: 0 for o in OUTCOMES})
        cell[outcome] = cell.get(outcome, 0) + 1
        tmp = self.procedural_path.with_name(self.procedural_path.name + ".tmp")
        tmp.write_text(json.dumps(stats, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, self.procedural_path)

    def operator_prior(self, operator: str, signature_class: str) -> dict:
        """Laplace-smoothed probability that the operator fixes this class: (fixed+1)/(n+2)."""
        cell = self._load_stats().get(operator, {}).get(signature_class, {})
        n = sum(cell.values())
        return {"p_fixed": (cell.get("fixed", 0) + 1) / (n + 2), "n": n}
