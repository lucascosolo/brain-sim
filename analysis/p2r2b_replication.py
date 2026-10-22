"""P2-R2b fresh two-seed replication (docs/plant2/P2-R2b-replication.md).

This wrapper rebinds the seeds, output paths and write/pairing helpers of the frozen P2-R2
driver (analysis/p2r2_degree_null.py), adds evidence verification and a hash-chained journal,
and then executes the frozen driver's ``run`` unchanged.
"""
import argparse
import json
import os
from pathlib import Path

from analysis import p2r1_replay as r1
from analysis import p2r2_degree_null as r2
from plant2 import evidence, record

SEEDS = (105, 106)
CONTRACT_PATH = "docs/plant2/P2-R2b-replication.md"
CONTRACT_COMMIT = "4cd865b5f41a898c5f48538f2fbec4451a3c8af3"
RESULTS = record.REPO / "bench/results/p2r2b.jsonl"
EVIDENCE = record.REPO / "bench/results/p2r2b"
CACHE_ROOT = Path.home() / ".cache/brain-sim/plant2-research-20261022/p2r2b"
ADDED_SOURCES = ["analysis/p2r2b_replication.py", "plant2/evidence.py", "plant2/tests/test_p2_r2b.py",
                 CONTRACT_PATH]
OVERRIDDEN_NAMES = ("SEEDS", "RESULTS", "EVIDENCE", "CONTRACT_PATH", "CONTRACT_COMMIT", "SOURCES",
                    "write_json", "write_npz", "paired_evidence")
MANIFEST = evidence.Manifest()
JOURNAL = None

_FROZEN_PAIRED = r2.paired_evidence
_FROZEN_SOURCES = list(r2.SOURCES)


def _register(desc):
    MANIFEST.add(desc["path"], desc)
    if JOURNAL is not None:
        JOURNAL.append({"kind": "artifact_written", "name": Path(desc["path"]).name, "descriptor": desc})
    return desc


def write_json(path, value):
    data = r1.json_bytes(value)
    return _register(evidence.write_artifact(path, data))


def write_npz(path, **values):
    return _register(evidence.write_npz_artifact(path, **values))


def paired_evidence(original, null):
    evidence.verify_artifact(original["portable"])
    evidence.verify_artifact(null["portable"])
    return _FROZEN_PAIRED(original, null)


def apply_overrides():
    r2.SEEDS = SEEDS
    r2.RESULTS = RESULTS
    r2.EVIDENCE = EVIDENCE
    r2.CONTRACT_PATH = CONTRACT_PATH
    r2.CONTRACT_COMMIT = CONTRACT_COMMIT
    r2.SOURCES = _FROZEN_SOURCES + ADDED_SOURCES
    r2.write_json = write_json
    r2.write_npz = write_npz
    r2.paired_evidence = paired_evidence
    return {name: getattr(r2, name) for name in OVERRIDDEN_NAMES}


def ensure_cache_root():
    current = os.environ.get("BRAINSIM_CACHE")
    if current is None:
        os.environ["BRAINSIM_CACHE"] = str(CACHE_ROOT)
    elif current != str(CACHE_ROOT):
        raise RuntimeError(f"BRAINSIM_CACHE is {current!r}, required {str(CACHE_ROOT)!r}")


def verification_record(seed, manifest, journal_path):
    failures, verified = [], 0
    for name, desc in manifest.entries.items():
        try:
            evidence.verify_artifact(desc)
            verified += 1
        except evidence.EvidenceError as e:
            failures.append(f"{name}: {e}")
    try:
        evidence.verify_journal(journal_path)
        journal_ok = True
    except (evidence.EvidenceError, OSError) as e:
        journal_ok = False
        failures.append(f"journal: {e}")
    return {"kind": "evidence_verification", "seed": seed, "artifacts_verified": verified,
            "failures": failures, "journal_ok": journal_ok, "passed": not failures and journal_ok}


def summarize(rows):
    saved = r2.SEEDS
    r2.SEEDS = SEEDS
    try:
        frozen = r2.summarize(rows)
    finally:
        r2.SEEDS = saved
    complete = {r["seed"]: r["result"] for r in rows
                if r.get("kind") == "seed_complete" and r.get("experiment") == "P2-R2"}
    invalid = []
    for seed in SEEDS:
        if complete.get(seed, {}).get("status") != "COMPLETE":
            continue
        checks = [r for r in rows if r.get("kind") == "evidence_verification" and r.get("seed") == seed]
        if not checks or not checks[-1].get("passed"):
            invalid.append(seed)
    status = "INVALID" if invalid or frozen["status"] == "INVALID" else frozen["status"]
    return dict(frozen, status=status, invalid_seeds=sorted(invalid))


def _load(path):
    path = Path(path)
    return json.loads((path if path.is_absolute() else record.REPO / path).read_text())


def p6(original_path, null_path):
    halves = [[r for r in _load(p)["index_cues"] if r["kind"] == "half"] for p in (original_path, null_path)]
    pairs = list(zip(*halves))
    mean = lambda key: sum(b[key] - a[key] for a, b in pairs) / len(pairs)
    own, spur = mean("own50"), mean("spurious50")
    return {"mean_delta_own50": own, "mean_delta_spurious50": spur, "passed": abs(own) < 1.0 and spur < -10.0}


def run(seed, log=print):
    global JOURNAL
    ensure_cache_root()
    apply_overrides()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    source = r2.source_manifest()
    JOURNAL = evidence.Journal(EVIDENCE / f"seed{seed}.journal.jsonl", f"seed{seed}")
    JOURNAL.append({"kind": "run_started", "seed": seed, "contract_commit": CONTRACT_COMMIT,
                    "code_sha256": source["code_sha256"], "runtime": record.runtime(),
                    "brainsim_cache": os.environ["BRAINSIM_CACHE"]})
    final = r2.run(seed, log=log)
    JOURNAL.append({"kind": "run_returned", "status": final["status"], "label": final.get("label")})
    rec = verification_record(seed, MANIFEST, JOURNAL.path)
    record.append(dict(rec, experiment="P2-R2", contract_path=CONTRACT_PATH, timestamp=record.now()), RESULTS)
    JOURNAL.append(rec)
    JOURNAL = None
    return dict(final=final, verification=rec)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    runner = commands.add_parser("run")
    runner.add_argument("--seed", type=int, required=True, choices=SEEDS)
    commands.add_parser("summary")
    six = commands.add_parser("p6")
    six.add_argument("--seed", type=int, required=True, choices=SEEDS)
    args = parser.parse_args(argv)
    if args.command == "run":
        result = run(args.seed, log=lambda x: print(f"[{record.now()}] {x}", flush=True))
        return 0 if result["final"]["status"] == "COMPLETE" and result["verification"]["passed"] else 1
    if args.command == "summary":
        rows = [json.loads(x) for x in RESULTS.read_text().splitlines() if x.strip()] if RESULTS.exists() else []
        print(json.dumps(summarize(rows), sort_keys=True))
        return 0
    records = evidence.verify_journal(EVIDENCE / f"seed{args.seed}.journal.jsonl")
    wanted = [f"seed{args.seed}-ORIGINAL-M1000.json", f"seed{args.seed}-DEGREE_NULL-M1000.json"]
    paths = []
    for name in wanted:
        desc = next(r["descriptor"] for r in records if r.get("kind") == "artifact_written" and r["name"] == name)
        evidence.verify_artifact(desc)
        paths.append(desc["path"])
    print(json.dumps(p6(*paths), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
