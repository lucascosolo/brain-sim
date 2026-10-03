"""Deterministic descriptions of a failure, used for memory lookup and operator priors.

signature_key  exact identity of a failure: exception type, message with numbers masked,
               innermost workspace frame (path, function). Two failures with the same key
               are "the same problem" for memory purposes.
signature_class  coarse class for priors: the exception type alone.
context_hash   sha256 over the contents of every workspace file in the traceback, so a
               remembered fix is reused only on byte-identical code.
"""
from __future__ import annotations

import hashlib
import json
import re

NUM_RE = re.compile(r"\b\d+(\.\d+)?\b")


def signature(failure: dict) -> dict:
    frames = failure.get("frames") or []
    inner = frames[-1] if frames else {}
    msg = NUM_RE.sub("<n>", failure.get("exc_message") or "")
    key = json.dumps([failure.get("exc_type"), msg, inner.get("path"), inner.get("func")])
    return {"exc_type": failure.get("exc_type"), "message": msg, "inner_path": inner.get("path"),
            "inner_func": inner.get("func"), "key": hashlib.sha256(key.encode()).hexdigest()[:16],
            "class": failure.get("exc_type") or "unknown"}


def context_hash(ws, failure: dict) -> str:
    h = hashlib.sha256()
    for path in sorted({f["path"] for f in failure.get("frames") or [] if f.get("path")}):
        try:
            text = ws.read_text(path)
        except Exception:  # unreadable file: hash its absence, which still differs from any content
            text = "\0missing"
        h.update(path.encode() + b"\0" + text.encode("utf-8") + b"\0")
    return h.hexdigest()
