# Evidence durability: verified artifacts and sequenced journals for every future run

Contract, 2026-10-22. Engineering change, not an experiment: it adds one module,
`plant2/evidence.py`, and its tests. It changes no frozen driver, no contract, no result and
no scoring rule. New drivers (the P2-R2 replication and everything after it) write their
evidence through this module; the frozen drivers keep their own writers so their recorded
provenance stays reproducible.

## Why

P2-R2 seed 104 is INVALID because `bench/results/p2r2/seed104-ORIGINAL-M1000.json` was
found empty at the final paired read, although the worker's descriptor recorded 1,883,558
bytes and a SHA-256 that an independent reconstruction later reproduced exactly, and two
journal progress events were absent (`docs/plant2/RESULTS-P2-R2.md`,
`review/plant2/P2-R2/findings-integrity.md`). The cause is unresolved. The integrity review
names the missing controls: no artifact or journal `fsync`, no journal lock or per-worker
sequence chain, no post-append readback, descriptors computed in separate operations from
the write, and evidence parsed without first checking the stored size and hash. Every
independent reviewer and the handoff made this the first next step. The owner's standing
rule applies: nothing here deletes, truncates, overwrites or renames an existing file.

## What the module guarantees

**Artifacts.** `write_artifact(path, data: bytes) -> descriptor` creates `path` exclusively
(`O_CREAT | O_EXCL`; an existing path raises `FileExistsError` and nothing is touched), writes
every byte (looping on short writes), calls `os.fsync` on the file, closes it, calls `fsync`
on the parent directory, then reopens the path and reads it back in full; the bytes read must
equal the bytes given, or `EvidenceError` is raised and the descriptor is not returned. The
descriptor is `{"path": <repo-relative when under the repository, else absolute>, "bytes":
<int>, "sha256": <hex of the bytes read back>, "written_at": <ISO-8601 UTC>}`. Helpers:
`write_json_artifact(path, obj)` (canonical JSON: `sort_keys=True`, UTF-8) and
`write_npz_artifact(path, **arrays)` (`numpy.savez_compressed` into memory first, then
`write_artifact`). Serialization happens before the file exists, so a serialization error
leaves no file behind.

**Verification before consumption.** `verify_artifact(descriptor) -> bytes` reopens the path,
checks the size against `bytes` and the SHA-256 of the full content against `sha256`, and
returns the content only if both hold; an empty file, a short file, a longer file and a
same-length different file all raise `EvidenceError` naming the path and which check failed.
`load_json_artifact(descriptor)` and `load_npz_artifact(descriptor)` parse only what
`verify_artifact` returned. Nothing in a driver reads an evidence file any other way.

**Journals.** `Journal(path, worker)` is one append-only JSONL file per worker (two workers
never share a journal). `append(record: dict) -> dict` adds `seq` (0, 1, 2, ... with no
gaps), `worker`, `timestamp` (ISO-8601 UTC) and `prev_sha256` (the SHA-256 of the previous
line's bytes, or the string `"genesis"` for `seq` 0), serializes one line (canonical JSON plus
`\n`), writes it with a single `os.write` on a descriptor opened `O_WRONLY | O_APPEND |
O_CREAT`, raises on a short write, calls `os.fsync`, closes, then reopens the file, seeks to
the offset the line was expected to start at, reads exactly that many bytes and compares them
to the line; any difference raises `EvidenceError`. It returns the record as written. The
journal remembers its byte offset and last line hash in memory; opening an existing journal
replays it with `verify_journal` first and continues the chain from its last line.
`verify_journal(path) -> list[dict]` parses every line, checks that every line is complete
JSON, that `seq` runs 0..n-1 without gaps or repeats, that each `prev_sha256` equals the hash
of the previous line's bytes, and that `worker` is the same on every line; it raises
`EvidenceError` with the first failing line number otherwise. Two records can never
interleave because each line is one write and each worker has its own file.

**Completeness.** `Manifest()` collects descriptors by name (`manifest.add(name,
descriptor)`); `manifest.verify_all() -> dict[name, bytes]` verifies every descriptor and
raises on the first failure, naming it; `manifest.require(names)` raises `EvidenceError`
listing every required name that is absent. A driver declares a stage complete only after
`require` and `verify_all` both pass, and it records the manifest itself as a JSON artifact.

**What it never does.** The module contains no `unlink`, `remove`, `rmtree`, `rename`,
`replace`, truncation (`O_TRUNC`, mode `"w"`/`"wb"` on an existing path) or temporary-file
machinery. Overwriting is impossible by construction because every create is exclusive.

## Tests required (written before the implementation, by a different agent)

In `plant2/tests/test_evidence.py`, using the `run_dir` fixture (never `tmp_path`;
`plant2/tests/test_hygiene.py` bans it):

1. `write_artifact` round-trips bytes, returns a descriptor whose `bytes` and `sha256` match
   `hashlib.sha256(data)`, and `verify_artifact` returns the same bytes.
2. A second `write_artifact` to the same path raises `FileExistsError` and leaves the first
   content intact (verified by `verify_artifact` afterwards).
3. `verify_artifact` raises `EvidenceError` when the file on disk is empty, shorter, longer,
   or the same length with different content (the test writes a *separate* scratch file with
   the altered content and points a copied descriptor at it; it never modifies the original
   artifact).
4. `write_json_artifact` is canonical (two dicts with the same keys in different insertion
   order give byte-identical files), and `load_json_artifact` returns the object.
5. `write_npz_artifact` / `load_npz_artifact` round-trip integer and float arrays exactly.
6. `Journal.append` returns records with `seq` 0, 1, 2 and the chain hashes; the file has
   exactly one line per append; `verify_journal` returns the same records.
7. `verify_journal` raises on: a missing line in the middle (the test builds the bad journal
   itself from valid lines, as a separate file), a repeated `seq`, a wrong `prev_sha256`, a
   truncated last line, and a `worker` change.
8. Reopening an existing journal continues the sequence and chain from its last line.
9. `Manifest.require` names every missing entry; `verify_all` fails on a descriptor whose
   file does not match and succeeds when all do.
10. The source of `plant2/evidence.py` contains none of the banned names in the "What it never
    does" paragraph (a text check, mirroring `test_hygiene.py`).

`plant2/tests/test_hygiene.py` and reflex-layer's safety lint must still pass.

## Clarifications (appended 2026-10-22 after the tests were written, before implementation)

- `prev_sha256` is the SHA-256 of the previous line's complete bytes **including** its
  trailing newline, exactly as they sit in the file.
- `Manifest.add(name, descriptor)` with a name already present replaces the in-memory entry
  for that name (the manifest is memory, not a file; nothing on disk changes).
- `EvidenceError` messages always contain the offending file's name (its last path
  component) and, for journals, the 1-based line number of the first failing line.
- Descriptor `path` is repo-relative only when the file is under `plant2.record.REPO`;
  otherwise it is the absolute path as given. `verify_artifact` resolves a relative path
  against `REPO`.
- `Journal` and the verify helpers accept `str` or `pathlib.Path`.

## Out of scope

Changing any frozen driver; retrofitting old results; a cross-process lock (one journal per
worker makes it unnecessary); durability guarantees the host filesystem does not offer
(`fsync` is requested, its effect is the substrate's). The P2-R2 incident is not explained by
this module and is not reclassified by it.
