# P2-R2 independent persistence-integrity postmortem

Reviewed 2026-10-12, after production, by the independent code reviewer. Scope: source/control-flow inspection, read-only journal/artifact hashes and metadata, and corroboration of the separately authorized recovery artifact. No simulation, test rerun, source modification, Git operation, deletion or cleanup was performed. This report is a new file; original evidence is unchanged.

**Disposition: seed104 remains INVALID; the formal two-seed result remains INVALID. The cause of the persistence discrepancy is not established.** No inspected source path explains both the empty combined artifact and the absent progress events under ordinary coherent file semantics. This is not a finding that the filesystem, execution service, Git, a particular worker or an external actor caused the discrepancy.

## Observations

The inspected journal snapshot has 2,820,002 bytes, 61 complete parseable JSON lines, a terminal newline, no NUL bytes, and SHA256 `305e3edd01659cabf242da86a21c014a1f8f605436a540df112c7b8ca91fe492`. Its last line is the parent's explicit INVALID disposition. Seed103 finishes COMPLETE at 194.492307 seconds; seed104 finishes INVALID at 198.318102 seconds.

The original `bench/results/p2r2/seed104-ORIGINAL-M1000.json` currently has zero bytes. Seed104's final in-memory load record instead retains a descriptor of 1,883,558 bytes and SHA256 `a16f1b9c209cccd202f3251ce7f931fe948f6284542ddc71d852ab7e47725a7d`. The other seven combined load artifacts match their final recorded sizes and hashes. Every source file currently matches both workers' recorded source manifests: commit `c7a5350b6a9c2359d39e4391b5e371901bf9e0ac`, aggregate source SHA256 `23d86d5af283aa3c5433ed4c4dc07b9207b27396b01c0b4f6361c7802279f3fc`.

Exactly two expected seed104 progress events are absent: ORIGINAL/M1000 `load_complete` and DEGREE_NULL/M500 `load_started`. Later DEGREE_NULL/M500 learning/index/content/completion/pair events and every DEGREE_NULL/M1000 load event survive. All four loads survive in seed104's final record. The missing M1000 paired event follows the observed failure and is not a third unexplained lost event.

The interrupted record reports `JSONDecodeError('Expecting value: line 1 column 1 (char 0)')`. Its stage string, DEGREE_NULL/1000/replay/assigned_A, is the last progress marker, not proof that replay failed. Both assigned-A content and load-completion records survive. The next operation is `paired_evidence`, whose first operation parses the ORIGINAL/M1000 combined file; an empty file produces this error. The evidence supports failure during that reread, after replay completed.

The empty file's inspected mtime is 04:39:05.445611 UTC and ctime is 04:39:07.841660 UTC, with one link and inode 790397. These are present metadata, not a write history or attribution. An empty file does not by itself prove a truncate syscall occurred.

## Source assessment

`analysis/p2r2_degree_null.py:write_json` exclusively creates each artifact with `open("xb")`, serializes/writes, closes the handle, then calls `p2r1_replay.file_info`. That helper opens the path again, reads its bytes to calculate SHA256, and obtains its size. The full historical descriptor therefore is not merely a hash of an intended in-memory payload: normal execution reads the completed file before returning it. A serialization/write interruption can leave a newly created empty or incomplete artifact, but cannot normally also return the recorded full descriptor and continue into the null arm. Filenames include seed, arm and load; the two workers do not select the same combined-artifact path. No subsequent truncate, overwrite, rename or deletion of this path exists in the inspected execution path.

`plant2.record.append` serializes one complete line, opens with `O_WRONLY|O_APPEND|O_CREAT`, performs one `os.write`, raises on a short write, and closes. The R2 runner calls both missing emissions unconditionally in sequence between the completed original evaluation and null learning. An ordinary serialization/open/write exception there exits the run's main body into the exception handler; it does not continue to the surviving null learning events. There is no source branch that intentionally suppresses those events. Under ordinary append semantics the other worker does not seek back or replace their lines.

The source's timers are per-process SIGALRM timers, far below their 19/20-minute limits at the observed failure. They do not signal the other worker or write/truncate artifacts. Parent-reported publication of four immutable structural files and Git add/fetch/update-ref, without checkout, does not identify a source-level operation targeting the damaged file or journal. No independent syscall/service trace was available to establish what actually changed persistent state.

## Limits and future integrity controls

The existing implementation has no artifact/journal `fsync`, journal lock, persistent per-worker sequence chain, or post-append readback. `file_info` hashes and stats the path in separate operations. `paired_evidence` parses without first checking the stored size/hash; a valid-JSON mutation could evade this particular empty-file failure. Stage receipts attest successful append calls in memory, not later durability. These are integrity/durability limitations, not a demonstrated causal explanation of this incident. Exclusive creation and O_APPEND constrain program intent; they do not independently prove end-to-end persistence on the actual execution/storage substrate.

Any future persistence hardening should be a separately reviewed source change: exclusive immutable per-event receipts or sequenced per-worker journals, explicit durability where supported, and descriptor verification before evidence consumption/final acceptance. This review does not authorize reruns, alteration of the frozen result, or replacement of original evidence.

## Recovery corroboration

The results reviewer reconstructed the exact historical combined JSON from surviving index/content components and the final recorded replay timings, then saved it to a new recovery path after separate parent authorization. This reviewer independently read that new artifact and verified its 1,883,558 bytes and exact historical SHA256. The original remains empty. This establishes recoverable evidence content, not successful completion of the original paired stage, durability of the missing journal events, or a valid formal replication. Post hoc paired analysis remains explicitly separate. The initial code-review closure is therefore supplemented by this open production-integrity finding; the original INVALID disposition is preserved.
