"""Verified artifacts and sequenced journals (docs/plant2/EVIDENCE-DURABILITY.md).

Every create is exclusive or append-only; nothing here opens an existing path for writing.
"""
import hashlib
import io
import json
import os
from pathlib import Path

import numpy as np

from plant2.record import REPO, now


class EvidenceError(Exception):
    pass


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _write_all(fd, data):
    view = memoryview(data)
    while view:
        view = view[os.write(fd, view):]


def _fsync_dir(path):
    try:
        dfd = os.open(Path(path).parent, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(dfd)
    except OSError:
        pass
    finally:
        os.close(dfd)


def _read(path):
    with open(path, "rb") as f:
        return f.read()


def _resolve(path):
    p = Path(path)
    return p if p.is_absolute() else REPO / p


def _describe_path(path):
    p = Path(path).resolve()
    try:
        return str(p.relative_to(REPO))
    except ValueError:
        return str(path)


def write_artifact(path, data):
    """Create path exclusively, fsync, read back and compare; return its descriptor."""
    path = Path(path)
    data = bytes(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        _write_all(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    _fsync_dir(path)
    back = _read(path)
    if back != data:
        raise EvidenceError(f"{path.name}: readback differs from the {len(data)} bytes written ({len(back)} read)")
    return {"path": _describe_path(path), "bytes": len(back), "sha256": _sha(back), "written_at": now()}


def write_json_artifact(path, obj):
    return write_artifact(path, _canonical(obj))


def write_npz_artifact(path, **arrays):
    buf = io.BytesIO()
    np.savez_compressed(buf, **arrays)
    return write_artifact(path, buf.getvalue())


def verify_artifact(descriptor):
    """Return the file content only if its size and SHA-256 match the descriptor."""
    path = _resolve(descriptor["path"])
    try:
        data = _read(path)
    except OSError as e:
        raise EvidenceError(f"{path.name}: cannot read ({e})") from e
    if len(data) != descriptor["bytes"]:
        raise EvidenceError(f"{path.name}: size check failed, {len(data)} bytes on disk, {descriptor['bytes']} recorded")
    if _sha(data) != descriptor["sha256"]:
        raise EvidenceError(f"{path.name}: sha256 check failed, content differs from the descriptor")
    return data


def load_json_artifact(descriptor):
    return json.loads(verify_artifact(descriptor).decode("utf-8"))


def load_npz_artifact(descriptor):
    with np.load(io.BytesIO(verify_artifact(descriptor)), allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def verify_journal(path):
    """Parse a journal and check completeness, seq, hash chain and worker; return its records."""
    path = Path(path)
    name = path.name
    data = _read(path)
    records = []
    prev, worker = "genesis", None
    pos = 0
    while pos < len(data):
        n = len(records) + 1
        end = data.find(b"\n", pos)
        if end < 0:
            raise EvidenceError(f"{name}: line {n} is incomplete (no trailing newline)")
        line = data[pos:end + 1]
        try:
            rec = json.loads(line)
        except ValueError as e:
            raise EvidenceError(f"{name}: line {n} is not valid JSON ({e})") from e
        if not isinstance(rec, dict):
            raise EvidenceError(f"{name}: line {n} is not a JSON object")
        if rec.get("seq") != n - 1:
            raise EvidenceError(f"{name}: line {n} has seq {rec.get('seq')!r}, expected {n - 1}")
        if rec.get("prev_sha256") != prev:
            raise EvidenceError(f"{name}: line {n} prev_sha256 does not match the previous line")
        if worker is not None and rec.get("worker") != worker:
            raise EvidenceError(f"{name}: line {n} worker {rec.get('worker')!r} differs from {worker!r}")
        worker = rec.get("worker")
        records.append(rec)
        prev = _sha(line)
        pos = end + 1
    return records


class Journal:
    """One append-only JSONL file per worker, sequenced and hash-chained."""

    def __init__(self, path, worker):
        self.path = Path(path)
        self.worker = worker
        self.seq, self.prev, self.offset = 0, "genesis", 0
        if self.path.exists() and self.path.stat().st_size > 0:
            records = verify_journal(self.path)
            if records[-1]["worker"] != worker:
                raise EvidenceError(f"{self.path.name}: journal belongs to worker {records[-1]['worker']!r}, not {worker!r}")
            data = _read(self.path)
            self.seq = records[-1]["seq"] + 1
            self.prev = _sha(data[data.rfind(b"\n", 0, len(data) - 1) + 1:])
            self.offset = len(data)

    def append(self, record):
        rec = dict(record, seq=self.seq, worker=self.worker, timestamp=now(), prev_sha256=self.prev)
        line = _canonical(rec) + b"\n"
        fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            written = os.write(fd, line)
            if written != len(line):
                raise EvidenceError(f"{self.path.name}: short append, {written} of {len(line)} bytes")
            os.fsync(fd)
        finally:
            os.close(fd)
        _fsync_dir(self.path)
        with open(self.path, "rb") as f:
            f.seek(self.offset)
            back = f.read(len(line))
        if back != line:
            raise EvidenceError(f"{self.path.name}: readback of seq {self.seq} at offset {self.offset} differs from the line written")
        self.seq += 1
        self.prev = _sha(line)
        self.offset += len(line)
        return rec


class Manifest:
    """Descriptors by name; a stage is complete only after require and verify_all pass."""

    def __init__(self):
        self.entries = {}

    def add(self, name, descriptor):
        self.entries[name] = descriptor

    def verify_all(self):
        out = {}
        for name, desc in self.entries.items():
            try:
                out[name] = verify_artifact(desc)
            except EvidenceError as e:
                raise EvidenceError(f"manifest entry {name!r}: {e}") from e
        return out

    def require(self, names):
        missing = [n for n in names if n not in self.entries]
        if missing:
            raise EvidenceError(f"manifest is missing required entries: {', '.join(missing)}")
