# P2-R2b: fresh prospective replication of the exact-degree input null

Contract, 2026-10-22. The commit that adds this file freezes it; append only thereafter. The
earlier draft (`P2-R2b-replication-DRAFT.md`, commit `334504c`) is preparation provenance; an
independent adversarial read of it (eight findings, all addressed below) preceded this text.

Reported replication, not a capability gate and not a new mechanism. It tests nothing that
`docs/plant2/P2-R2-degree-null.md` (frozen at `2454f06`) did not already declare; it repeats
that contrast on two fresh seeds with durable, verified evidence, because P2-R2's formal
two-seed outcome is INVALID (seed 104's combined artifact was found empty at the paired read)
and every reviewer asked for durable evidence followed by fresh replication before a mechanism
is chosen on this contrast. Hypotheses tested: H-R2 (material structure sensitivity at
M = 1,000) and its riders (a low-load oldest-recall cost; inherited content below the bar at
1,000), as listed in `docs/research/HYPOTHESES.md`.

## What is identical to P2-R2

Everything scientific: the F10/s60 canonical items from `FamilyGen`, the row-Curveball block
trade with exactly 10,000 attempted trades per 100-episode block (chain 0 delivered, chain 1
diagnostic), the structural checks and the STRUCTURAL CONTRAST UNCERTAIN flags, the inherited
E3 learner with J_mem = 1.525, accommodation tau = 10,000 ms, J_fb = 2.80, g = 0.3, the 50 ms
index and 75 ms content windows, the loads 500 and 1,000, the deep-copied checkpoint
evaluation with a 50 s settle, 200 half cues, 200 novel half cues and 200 full cues, the
inherited and assigned-A content stores at the frozen readout, the validity bars, the four
ordered labels at M = 1,000 (decided by the frozen `classify`, whose recall rule is
`delta >= -0.03 - 1e-12`), the raw bar-deficit fraction, the M = 500 reporting rules, the
small original/sham parity check (m = n = 256, a = 64, f_q = 0.05, 20 episodes), the F40
structural-only diagnostic, and the 20-minute two-worker ceiling measured from the first
process. The frozen `analysis/p2r2_degree_null.py` is executed byte-identical to `c7a5350`;
its `run()`, item adapter, learner, evaluation, scoring, labelling and `summarize` are not
re-implemented.

## What differs, and why

1. **Seeds 105 and 106.** Audited 2026-10-22: no recognised seed field in any
   `bench/results/*.jsonl` record uses 105 or 106, and no contract, driver or review names
   them as seeds; the only textual hits are unrelated numbers. No substitution during a run.
   The frozen driver refuses any other seed.

2. **A wrapper driver, `analysis/p2r2b_replication.py`.** It imports the frozen module as
   `r2` and rebinds exactly these module attributes, which the frozen functions read at call
   time (verified against the source during the draft review):
   - `r2.SEEDS = (105, 106)`;
   - `r2.RESULTS = <repo>/bench/results/p2r2b.jsonl`; `r2.EVIDENCE = <repo>/bench/results/p2r2b`;
   - `r2.CONTRACT_PATH = "docs/plant2/P2-R2b-replication.md"` and `r2.CONTRACT_COMMIT` = the
     commit that adds this file;
   - `r2.SOURCES = r2.SOURCES + [the wrapper, "plant2/evidence.py", "plant2/tests/test_p2_r2b.py",
     this contract]`, because `SOURCES` is built at import time from the old contract path;
     `r2.INHERITED` is not touched (the baseline `55e16eb` has no `evidence.py`), so the
     frozen manifest still requires every inherited file byte-identical to the baseline and
     every listed file committed at HEAD;
   - `r2.write_json` and `r2.write_npz`, replaced by writers that serialise exactly as the
     frozen ones do (`p2r1_replay.json_bytes`: `jsonable`, `sort_keys`, compact separators,
     `allow_nan=False`; `numpy.savez_compressed`) and store the bytes through
     `plant2.evidence.write_artifact` (exclusive create, fsync, read back, hash), returning
     the evidence descriptor, whose `path` key has the same repo-relative-or-absolute meaning
     as the frozen `file_info` descriptor; the wrapper records every descriptor in a
     `Manifest` keyed by path and appends a `{kind: "artifact_written", name, descriptor}`
     line to its per-worker journal;
   - `r2.paired_evidence`, replaced by a function that first runs `verify_artifact` on both
     combined load descriptors it receives and then delegates to the frozen function
     unchanged. The frozen function then re-reads the files itself; the verification is
     therefore immediately before that read, not inside it. An `EvidenceError` propagates
     into the frozen `run()`'s handler and is recorded as INVALID with its message.
   Nothing else in the frozen module is rebound. A unit test imports the frozen module
   pristine in a subprocess, imports it through the wrapper in another, and asserts that the
   set of names whose values differ is exactly the list above.

3. **Evidence verification after `run()`.** The frozen `run()` emits `seed_complete` from
   inside a closure that the wrapper cannot reach, so verification happens after it returns:
   the wrapper runs `Manifest.verify_all()` over every artifact it wrote (evidence JSONs,
   structural files, cache NPZ checkpoints), verifies its own journal with `verify_journal`,
   and appends one `{kind: "evidence_verification", seed, artifacts_verified, failures,
   journal_ok, passed}` record to `bench/results/p2r2b.jsonl` and to its journal. The
   wrapper's `summary` command applies this rule on top of the frozen `summarize`: a seed is
   COMPLETE only if its `seed_complete.result.status` is COMPLETE **and** its
   `evidence_verification.passed` is true; otherwise it is INVALID (verification failure) or
   whatever the frozen status says. The wrapper's exit code follows the wrapper's status.

4. **Per-worker journal.** `bench/results/p2r2b/seed<seed>.journal.jsonl`, a
   `plant2.evidence.Journal` (seq, worker, hash chain, post-append readback), holding
   `run_started`, every `artifact_written`, `run_returned` (with the frozen `final.status`)
   and `evidence_verification`. The frozen driver's own `record.append` lines to the shared
   results file remain the primary scientific journal; the wrapper journal is the durability
   record beside it.

5. **Cache root.** The wrapper sets `BRAINSIM_CACHE` to
   `~/.cache/brain-sim/plant2-research-20261022/p2r2b` in its own process before any
   `cache_dir` call and asserts it. Because `plant2.record.cache_dir` inserts `plant2/` and
   the frozen driver hardcodes `cache_dir("p2r2")`, the resource window, seed claims, parity
   file and NPZ checkpoints land under `~/.cache/brain-sim/plant2-research-20261022/p2r2b/plant2/p2r2/`.
   That directory does not exist before the run; a pre-existing window there is an integrity
   stop, not something to clear.

6. **Record labelling.** The frozen `meta` hardcodes `experiment = "P2-R2"`; rows in
   `p2r2b.jsonl` therefore say P2-R2 and are told apart from P2-R2 by their separate file
   and by `contract_path = "docs/plant2/P2-R2b-replication.md"`. The ledger cites them as
   P2-R2b.

7. **Runtime.** This PC: CPython 3.11.17, NumPy 2.4.6 (P2-R2 ran on 3.12.14 / 2.3.5). No
   integrity check compares against stored P2-R2 values, so the version difference cannot
   fail a check; it is, however, confounded with seed for any disagreement with P2-R2, and
   the result says so.

8. **Execution hygiene.** Two workers started together, one seed each; at most four
   simulation processes machine-wide; `OPENBLAS_NUM_THREADS=1`. No `git` command, commit,
   fetch, push or any publication runs on this machine while a worker is running (P2-R2's
   damage occurred while its parent ran git operations; the cause is unresolved and that
   confound is removed here). Commits happen only after both workers have exited and their
   verification records exist.

## Predictions (frozen before implementation, from P2-R2's valid seed 103 and the
descriptive seed-104 reconstruction, the only prior data)

Each prediction names the record and field that decides it.

- **P1.** Both seeds: `seed_complete.result.status == "COMPLETE"` with empty
  `missing_stages`, and `structure` (F = 10) `result.loads["500"].decision.ok` and
  `["1000"].decision.ok` true. F40 flags are reported only and do not decide P1.
- **P2.** Both seeds: `paired_load` with `result.M == 1000` has
  `result.decision.label == "MATERIAL STRUCTURE SENSITIVITY"` (the frozen label already
  encodes Delta C2 >= 0.15, Delta joint-index >= 0.10 and both recall deltas >= -0.03 - EPS).
- **P3.** Both seeds, at M = 1,000: DEGREE_NULL `load_complete.result.index.C2 < 0.90`, and
  `paired_load.result.decision.C2_bar_deficit_removed` is not None and lies in the closed
  interval [0.50, 0.80].
- **P4.** Both seeds, both arms, at M = 1,000: `load_complete.result.content.inherited.joint
  < 0.15` and `result.content.assigned_A.joint < 0.40`.
- **P5.** On at least one seed, both of these on that same seed at M = 500:
  `paired_load.result.decision.delta.C4_recall <= -0.03` and
  `paired_load.result.content.inherited.delta_S2 >= 0.10`.
- **P6.** Computed after the run by `analysis/p2r2b_replication.py p6`, from each seed's two
  combined load artifacts `seed<seed>-ORIGINAL-M1000.json` and `seed<seed>-DEGREE_NULL-M1000.json`
  (field `index_cues`, rows with `kind == "half"`, paired by position; fields `own50` and
  `spurious50`): the mean over the 200 half cues of (null minus original) satisfies
  |mean Delta own50| < 1.0 and mean Delta spurious50 < -10.0, on both seeds. The script prints
  the two means per seed and the verdict; it reads only verified artifacts.

A contradiction of P2 on either seed is recorded as disagreement with P2-R2 and sends the
mechanism choice back to the roadmap; it does not trigger a third seed under this contract.
No prediction is revised after the run.

## Resource stop and status

Twenty wall minutes from the first P2-R2b process (the frozen resource window), two workers,
no new stage after minute 18, in-flight stage checkpointed by minute 20, PARTIAL retained
with every missing stage listed. No fresh full-size benchmark before the run (P2-R2 took
194-198 s per seed on an eight-core host; this PC has sixteen threads and 31 GB).

Formal result: COMPLETE only if both seeds are COMPLETE under the wrapper's rule above; one
INVALID seed makes the formal two-seed result INVALID again, with no replacement seed. The
result is appended to `docs/research/EXPERIMENTS.md` and `HYPOTHESES.md` with its labels
copied, not paraphrased. Tests: `plant2/tests/test_p2_r2b.py` (the namespace test, the writer
serialisation equivalence including a numpy scalar and a refused NaN, the verification record
rule on synthetic rows, the P6 computation on a synthetic pair, and the cache-root assertion)
must pass with the rest of the non-slow suite, and the safety lint must show no new finding,
before any worker starts.

## What this cannot show

Nothing beyond P2-R2's own scope: a finite block-constrained randomisation is not a causal
partition into frequency and correlation contributions; fine timing, actual eligibility, coin
alignment and adaptive state change with the inputs. A replicated label is an explanation
result that informs which mechanism to contract next; it is not a memory capability, removes
no experimenter supply and authorises no Stage 2 work.

## Result (appended 2026-10-22, after execution)

COMPLETE on both seeds with verified evidence; replicated label at M = 1,000 MATERIAL
STRUCTURE SENSITIVITY (Delta C2 +0.260 / +0.265, Delta joint index +0.240 / +0.280, recall
deltas within tolerance); P1-P4 held, P5 failed (no oldest-recall cost at 500 on either seed),
P6 failed on seed 106 (spurious responders fell by 6.97, not 10). Full record:
`docs/plant2/RESULTS-P2-R2b.md`; data `bench/results/p2r2b.jsonl` and `bench/results/p2r2b/`.
