"""Contract tests for plant2/evidence.py (docs/plant2/EVIDENCE-DURABILITY.md).

Every file lives under the run_dir fixture; no test modifies an existing file. Corruption cases are
built as NEW scratch files that a copied descriptor (or the verify call) is pointed at.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from plant2 import evidence

SOURCE = Path(__file__).resolve().parent.parent / "evidence.py"


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _scratch(run_dir, name, data):
    """Create a brand-new file (exclusive create) holding data."""
    p = run_dir / name
    with open(p, "xb") as f:
        f.write(data)
    return p


def _journal_lines(run_dir, name="good.jsonl", worker="w0", n=4):
    j = evidence.Journal(run_dir / name, worker)
    for i in range(n):
        j.append({"event": "progress", "i": i})
    return (run_dir / name).read_bytes().splitlines(keepends=True)


def _bad_journal(run_dir, name, lines):
    return _scratch(run_dir, name, b"".join(lines))


def _edit(line, **changes):
    rec = json.loads(line)
    rec.update(changes)
    return (json.dumps(rec, sort_keys=True) + "\n").encode()


# 1
def test_write_artifact_roundtrip_and_descriptor(run_dir):
    data = b"\x00evidence\xff" * 100
    p = run_dir / "a.bin"
    desc = evidence.write_artifact(p, data)
    assert p.read_bytes() == data
    assert desc["bytes"] == len(data)
    assert desc["sha256"] == hashlib.sha256(data).hexdigest()
    assert Path(desc["path"]).name == "a.bin"
    assert desc["written_at"]
    assert evidence.verify_artifact(desc) == data


# 2
def test_second_write_to_same_path_raises_and_keeps_first(run_dir):
    p = run_dir / "once.bin"
    desc = evidence.write_artifact(p, b"first")
    with pytest.raises(FileExistsError):
        evidence.write_artifact(p, b"second, longer")
    assert evidence.verify_artifact(desc) == b"first"


# 3
@pytest.mark.parametrize("label,altered", [
    ("empty", b""),
    ("shorter", b"0123456"),
    ("longer", b"0123456789-and-more"),
    ("samelen", b"9876543210"),
])
def test_verify_artifact_rejects_altered_content(run_dir, label, altered):
    original = b"0123456789"
    desc = evidence.write_artifact(run_dir / "orig.bin", original)
    scratch = _scratch(run_dir, f"altered-{label}.bin", altered)
    bad = dict(desc, path=str(scratch))
    with pytest.raises(evidence.EvidenceError) as exc:
        evidence.verify_artifact(bad)
    assert scratch.name in str(exc.value)
    assert evidence.verify_artifact(desc) == original


# 4
def test_json_artifact_is_canonical_and_loads(run_dir):
    a = {"b": 1, "a": [1, 2, {"z": 0, "y": "é"}]}
    b = {"a": [1, 2, {"y": "é", "z": 0}], "b": 1}
    da = evidence.write_json_artifact(run_dir / "a.json", a)
    db = evidence.write_json_artifact(run_dir / "b.json", b)
    assert (run_dir / "a.json").read_bytes() == (run_dir / "b.json").read_bytes()
    assert da["sha256"] == db["sha256"]
    assert evidence.load_json_artifact(da) == a


# 5
def test_npz_artifact_roundtrips_int_and_float_exactly(run_dir):
    ints = np.arange(-5, 20, dtype=np.int64).reshape(5, 5)
    floats = np.array([0.1, 1 / 3, np.pi, -2.5e-300, 1e300], dtype=np.float64)
    desc = evidence.write_npz_artifact(run_dir / "arrs.npz", ints=ints, floats=floats)
    out = evidence.load_npz_artifact(desc)
    assert out["ints"].dtype == ints.dtype and np.array_equal(out["ints"], ints)
    assert out["floats"].dtype == floats.dtype and out["floats"].tobytes() == floats.tobytes()


# 6
def test_journal_append_chain_and_verify(run_dir):
    p = run_dir / "j.jsonl"
    j = evidence.Journal(p, "w0")
    recs = [j.append({"event": "e", "i": i}) for i in range(3)]
    assert [r["seq"] for r in recs] == [0, 1, 2]
    assert all(r["worker"] == "w0" and r["timestamp"] and r["event"] == "e" for r in recs)
    assert recs[0]["prev_sha256"] == "genesis"
    lines = p.read_bytes().splitlines(keepends=True)
    assert len(lines) == 3 and all(l.endswith(b"\n") for l in lines)
    for prev_line, rec in zip(lines, recs[1:]):
        assert rec["prev_sha256"] in (_sha(prev_line), _sha(prev_line[:-1]))
    assert evidence.verify_journal(p) == recs


# 7
def test_verify_journal_rejects_missing_middle_line(run_dir):
    lines = _journal_lines(run_dir)
    bad = _bad_journal(run_dir, "missing.jsonl", [lines[0], lines[2], lines[3]])
    with pytest.raises(evidence.EvidenceError) as exc:
        evidence.verify_journal(bad)
    assert bad.name in str(exc.value)


def test_verify_journal_rejects_repeated_seq(run_dir):
    lines = _journal_lines(run_dir)
    bad = _bad_journal(run_dir, "repeat.jsonl", lines[:3] + [_edit(lines[3], seq=2)])
    with pytest.raises(evidence.EvidenceError) as exc:
        evidence.verify_journal(bad)
    assert bad.name in str(exc.value)


def test_verify_journal_rejects_wrong_prev_sha256(run_dir):
    lines = _journal_lines(run_dir)
    bad = _bad_journal(run_dir, "badhash.jsonl", lines[:2] + [_edit(lines[2], prev_sha256="0" * 64)] + lines[3:])
    with pytest.raises(evidence.EvidenceError) as exc:
        evidence.verify_journal(bad)
    assert bad.name in str(exc.value)


def test_verify_journal_rejects_truncated_last_line(run_dir):
    lines = _journal_lines(run_dir)
    bad = _bad_journal(run_dir, "trunc.jsonl", lines[:3] + [lines[3][: len(lines[3]) // 2]])
    with pytest.raises(evidence.EvidenceError) as exc:
        evidence.verify_journal(bad)
    assert bad.name in str(exc.value)


def test_verify_journal_rejects_worker_change(run_dir):
    lines = _journal_lines(run_dir)
    bad = _bad_journal(run_dir, "worker.jsonl", lines[:3] + [_edit(lines[3], worker="w1")])
    with pytest.raises(evidence.EvidenceError) as exc:
        evidence.verify_journal(bad)
    assert bad.name in str(exc.value)


# 8
def test_reopened_journal_continues_sequence_and_chain(run_dir):
    p = run_dir / "reopen.jsonl"
    first = evidence.Journal(p, "w0")
    first.append({"i": 0})
    first.append({"i": 1})
    second = evidence.Journal(p, "w0")
    rec = second.append({"i": 2})
    assert rec["seq"] == 2
    assert rec["prev_sha256"] != "genesis"
    records = evidence.verify_journal(p)
    assert [r["seq"] for r in records] == [0, 1, 2]
    assert records[2] == rec


# 9
def test_manifest_require_names_every_missing_and_verify_all(run_dir):
    d1 = evidence.write_artifact(run_dir / "m1.bin", b"one")
    d2 = evidence.write_artifact(run_dir / "m2.bin", b"two")
    m = evidence.Manifest()
    m.add("alpha", d1)
    m.add("beta", d2)
    m.require(["alpha", "beta"])
    with pytest.raises(evidence.EvidenceError) as exc:
        m.require(["alpha", "gamma", "delta"])
    msg = str(exc.value)
    assert "gamma" in msg and "delta" in msg
    assert m.verify_all() == {"alpha": b"one", "beta": b"two"}

    scratch = _scratch(run_dir, "m2-other.bin", b"TWO")
    m.add("beta", dict(d2, path=str(scratch)))
    with pytest.raises(evidence.EvidenceError) as exc:
        m.verify_all()
    assert scratch.name in str(exc.value) or "beta" in str(exc.value)


# 10
def test_evidence_source_has_no_destructive_or_temporary_machinery():
    banned = ["un" + "link", "re" + "move(", "r" + "mtree", "re" + "name", "re" + "place(", "O_" + "TRUNC",
              "temp" + "file", "Temporary" + "Directory", "mk" + "dtemp", "NamedTemporary" + "File"]
    text = SOURCE.read_text()
    assert [b for b in banned if b in text] == []
