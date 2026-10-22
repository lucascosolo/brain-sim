"""P2-R2b wrapper checks (docs/plant2/P2-R2b-replication.md); synthetic data only, every file under run_dir."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from analysis import p2r1_replay as r1
from analysis import p2r2_degree_null as r2

FROZEN_PAIRED = r2.paired_evidence  # captured before the wrapper can rebind it

from analysis import p2r2b_replication as r2b  # noqa: E402
from plant2 import evidence, record  # noqa: E402

REPO = record.REPO
EXPECTED_OVERRIDES = {"SEEDS", "RESULTS", "EVIDENCE", "CONTRACT_PATH", "CONTRACT_COMMIT", "SOURCES",
                      "write_json", "write_npz", "paired_evidence"}
ADDED_SOURCES = ["analysis/p2r2b_replication.py", "plant2/evidence.py", "plant2/tests/test_p2_r2b.py",
                 "docs/plant2/P2-R2b-replication.md"]

DESCRIBE = """
import json, sys
sys.path.insert(0, ".")
from analysis import p2r2_degree_null as m
def desc(v):
    code = getattr(v, "__code__", None)
    if code is not None:
        return "fn:" + code.co_filename + ":" + v.__qualname__
    return repr(v)
def snapshot():
    return {n: desc(getattr(m, n)) for n in dir(m) if not n.startswith("__")}
out = {}
if sys.argv[1] == "pristine":
    out["names"] = snapshot()
else:
    from analysis import p2r2b_replication as w
    first = w.apply_overrides()
    second = w.apply_overrides()
    out["names"] = snapshot()
    out["returned"] = sorted(second)
    out["returned_equal"] = sorted(first) == sorted(second)
    out["overridden_names"] = sorted(w.OVERRIDDEN_NAMES)
out["SOURCES"] = list(m.SOURCES)
out["INHERITED"] = list(m.INHERITED)
print(json.dumps(out))
"""


def describe(mode, run_dir):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", BRAINSIM_CACHE=str(run_dir))
    proc = subprocess.run([sys.executable, "-c", DESCRIBE, mode], cwd=REPO, env=env, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr[-2000:]
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_constants():
    sha = subprocess.run(["git", "rev-parse", "4cd865b"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    assert len(sha) == 40
    assert r2b.SEEDS == (105, 106)
    assert r2b.CONTRACT_PATH == "docs/plant2/P2-R2b-replication.md"
    assert r2b.CONTRACT_COMMIT == sha
    assert r2b.RESULTS == record.REPO / "bench/results/p2r2b.jsonl"
    assert r2b.EVIDENCE == record.REPO / "bench/results/p2r2b"
    assert r2b.CACHE_ROOT.is_absolute()
    assert r2b.CACHE_ROOT.parts[-4:] == (".cache", "brain-sim", "plant2-research-20261022", "p2r2b")
    assert set(r2b.OVERRIDDEN_NAMES) == EXPECTED_OVERRIDES


def test_namespace_differs_from_pristine_only_in_the_listed_names(run_dir):
    pristine, wrapped = describe("pristine", run_dir), describe("wrapped", run_dir)
    assert set(pristine["names"]) == set(wrapped["names"])
    changed = {n for n in pristine["names"] if pristine["names"][n] != wrapped["names"][n]}
    assert changed == set(r2b.OVERRIDDEN_NAMES) == EXPECTED_OVERRIDES
    assert wrapped["overridden_names"] == sorted(EXPECTED_OVERRIDES)
    assert wrapped["returned"] == sorted(EXPECTED_OVERRIDES) and wrapped["returned_equal"]


def test_sources_extended_once_and_inherited_untouched(run_dir):
    pristine, wrapped = describe("pristine", run_dir), describe("wrapped", run_dir)
    assert wrapped["SOURCES"] == pristine["SOURCES"] + ADDED_SOURCES  # also proves idempotence (applied twice)
    assert wrapped["INHERITED"] == pristine["INHERITED"]


def sample_value():
    return {"i": np.int64(7), "arr": np.array([0.5, 1.5, 2.25], dtype=np.float64),
            "nest": {1: "one", "k": {"z": 2, 3: [np.float64(1.5)]}}, "text": "héllo ✓"}


def test_write_json_matches_frozen_serialisation_and_registers(run_dir):
    path = run_dir / "x.json"
    desc = r2b.write_json(path, sample_value())
    expected = r1.json_bytes(sample_value())
    assert path.read_bytes() == expected
    assert set(desc) == {"path", "bytes", "sha256", "written_at"}
    assert desc["bytes"] == len(expected) and desc["sha256"] == hashlib.sha256(expected).hexdigest()
    assert r2b.MANIFEST.entries[desc["path"]] == desc
    assert evidence.verify_artifact(desc) == expected


def test_write_json_refuses_nan_and_existing_path(run_dir):
    bad = run_dir / "nan.json"
    with pytest.raises(ValueError):
        r2b.write_json(bad, {"v": float("nan")})
    assert not bad.exists()
    path = run_dir / "once.json"
    r2b.write_json(path, {"a": 1})
    with pytest.raises(FileExistsError):
        r2b.write_json(path, {"a": 2})
    assert path.read_bytes() == r1.json_bytes({"a": 1})


def test_write_npz_returns_descriptor_and_registers(run_dir):
    path = run_dir / "y.npz"
    desc = r2b.write_npz(path, a=np.arange(3), b=np.asarray("text"))
    assert set(desc) == {"path", "bytes", "sha256", "written_at"}
    assert desc["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    with np.load(path) as z:
        assert np.array_equal(z["a"], np.arange(3)) and str(z["b"]) == "text"
    assert r2b.MANIFEST.entries[desc["path"]] == desc


def combined(own, spurious, extra_rows=()):
    rows = [dict(kind="half", index_0based=i, onset=100 * i, cue_id=i, oldest=bool(i == 0), A_size=50,
                 recall50=1.0, own50=own[i], spurious50=spurious[i]) for i in range(len(own))]
    table = dict(columns=["missing", "total", "item"], rows=[[45, 50, 45], [0, 50, 45], [45, 50, 45], [0, 50, 45]][:max(len(own), 2)])
    return dict(index_cues=rows + list(extra_rows), content=dict(inherited=table, assigned_A=table))


def load_row(desc, A=(1, 2)):
    return dict(portable=desc, matching=dict(A=list(A), novel=[3]), M=1000,
                index=dict(C1=1.0, C2=.5, C3=1.0, C4_recall=1.0, C4_spurious=.5, joint_index=.5),
                content=dict(inherited=dict(joint=.1), assigned_A=dict(joint=.3)),
                protocol=dict(ok=True),
                learning=dict(eligibility_block_counts=[[1, 2], [3, 4]], coin_draws_per_episode=[5, 6]))


def test_paired_evidence_verifies_then_delegates_unchanged(run_dir):
    d_o = r2b.write_json(run_dir / "o.json", combined([10, 10], [20, 20]))
    d_n = r2b.write_json(run_dir / "n.json", combined([10, 10], [8, 8]))
    o, n = load_row(d_o), load_row(d_n)
    assert r2b.paired_evidence(o, n) == FROZEN_PAIRED(o, n)
    altered = r2b.write_json(run_dir / "o-altered.json", combined([10, 10], [20, 21]))
    # differing assigned assemblies would make the frozen function raise IntegrityError; verification must come first
    tampered_o = load_row(dict(d_o, path=altered["path"]), A=(9, 9))
    with pytest.raises(evidence.EvidenceError):
        r2b.paired_evidence(tampered_o, n)
    tampered_n = load_row(dict(d_n, path=altered["path"]), A=(9, 9))
    with pytest.raises(evidence.EvidenceError):
        r2b.paired_evidence(o, tampered_n)


def manifest_of(*descs):
    m = evidence.Manifest()
    for d in descs:
        m.add(d["path"], d)
    return m


def good_journal(run_dir, name="j.jsonl"):
    j = evidence.Journal(run_dir / name, "w105")
    j.append({"kind": "run_started"})
    j.append({"kind": "run_returned"})
    return j.path


def test_verification_record_passes_with_good_artifacts_and_journal(run_dir):
    d1, d2 = r2b.write_json(run_dir / "a.json", {"a": 1}), r2b.write_json(run_dir / "b.json", {"b": 2})
    journal = good_journal(run_dir)
    before = sorted(p.name for p in run_dir.iterdir()), journal.read_bytes()
    rec = r2b.verification_record(105, manifest_of(d1, d2), journal)
    assert rec == dict(kind="evidence_verification", seed=105, artifacts_verified=2, failures=[],
                       journal_ok=True, passed=True)
    assert (sorted(p.name for p in run_dir.iterdir()), journal.read_bytes()) == before


def test_verification_record_flags_altered_artifact(run_dir):
    d1 = r2b.write_json(run_dir / "a.json", {"a": 1})
    altered = r2b.write_json(run_dir / "a-altered.json", {"a": 999})
    bad = dict(d1, path=altered["path"])
    good = r2b.write_json(run_dir / "b.json", {"b": 2})
    rec = r2b.verification_record(105, manifest_of(bad, good), good_journal(run_dir))
    assert rec["passed"] is False and rec["journal_ok"] is True
    assert rec["failures"] and altered["path"] in json.dumps(rec["failures"])


def test_verification_record_flags_broken_journal_chain(run_dir):
    d1 = r2b.write_json(run_dir / "a.json", {"a": 1})
    lines = [dict(seq=0, worker="w", prev_sha256="genesis", kind="x"),
             dict(seq=1, worker="w", prev_sha256="0" * 64, kind="y")]
    broken = run_dir / "broken.jsonl"
    evidence.write_artifact(broken, b"".join((json.dumps(x, sort_keys=True) + "\n").encode() for x in lines))
    rec = r2b.verification_record(105, manifest_of(d1), broken)
    assert rec["journal_ok"] is False and rec["passed"] is False


def seed_row(seed, status="COMPLETE"):
    return dict(experiment="P2-R2", kind="seed_complete", seed=seed,
                result=dict(status=status, missing_loads=[], missing_paired_loads=[], missing_stages=[],
                            label="MATERIAL STRUCTURE SENSITIVITY",
                            pairs={"1000": {"decision": {"C2_bar_deficit_removed": 0.6}}}))


def verification(seed, passed):
    return dict(kind="evidence_verification", seed=seed, artifacts_verified=3, failures=[], journal_ok=passed,
                passed=passed)


def test_summarize_requires_frozen_complete_and_passed_verification(monkeypatch):
    monkeypatch.setattr(r2, "SEEDS", (105, 106))  # the frozen summarize reads the rebound name
    ok = [seed_row(105), seed_row(106), verification(105, True), verification(106, True)]
    assert r2b.summarize(ok)["status"] == "COMPLETE"
    failed = r2b.summarize([seed_row(105), seed_row(106), verification(105, True), verification(106, False)])
    assert failed["status"] == "INVALID" and failed["invalid_seeds"] == [106]
    assert r2b.summarize([seed_row(105), seed_row(106), verification(105, True)])["status"] == "INVALID"
    frozen_invalid = [seed_row(105), seed_row(106, "INVALID"), verification(105, True), verification(106, True)]
    assert r2b.summarize(frozen_invalid)["status"] == "INVALID"


def half(own, spurious):
    return [dict(kind="half", own50=o, spurious50=s) for o, s in zip(own, spurious)]


def test_p6_means_and_verdict(run_dir):
    novel = [dict(kind="novel", own50=100, spurious50=100)]
    orig = r2b.write_json(run_dir / "o.json", dict(index_cues=half([10, 10, 10, 10], [20] * 4) + novel))
    null = r2b.write_json(run_dir / "n.json", dict(index_cues=half([12, 10, 10, 10], [8] * 4) +
                                                   [dict(kind="novel", own50=0, spurious50=0)]))
    result = r2b.p6(orig["path"], null["path"])
    assert result["mean_delta_own50"] == pytest.approx(0.5)
    assert result["mean_delta_spurious50"] == pytest.approx(-12.0)
    assert result["passed"] is True
    worse = r2b.write_json(run_dir / "n2.json", dict(index_cues=half([12, 12, 12, 10], [8] * 4) + novel))
    result = r2b.p6(orig["path"], worse["path"])
    assert result["mean_delta_own50"] == pytest.approx(1.5) and result["passed"] is False


def test_ensure_cache_root(monkeypatch, run_dir):
    monkeypatch.delenv("BRAINSIM_CACHE", raising=False)
    r2b.ensure_cache_root()
    assert os.environ["BRAINSIM_CACHE"] == str(r2b.CACHE_ROOT)
    r2b.ensure_cache_root()  # already equal: no error
    monkeypatch.setenv("BRAINSIM_CACHE", str(run_dir))
    with pytest.raises(RuntimeError):
        r2b.ensure_cache_root()
    assert os.environ["BRAINSIM_CACHE"] == str(run_dir)
