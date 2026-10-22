# P2-R2b: fresh prospective replication of the exact-degree input null

Contract, 2026-10-22. The commit that adds this file freezes it; append only thereafter.
Reported replication, not a capability gate and not a new mechanism. It tests nothing that
`docs/plant2/P2-R2-degree-null.md` (frozen at `2454f06`) did not already declare; it repeats
that contrast on two fresh seeds under the evidence-durability module, because P2-R2's formal
two-seed outcome is INVALID (seed 104's combined artifact was found empty) and every reviewer
asked for durable evidence followed by fresh replication before a mechanism is chosen on this
contrast. Hypotheses tested: H-R2 (material structure sensitivity at M = 1,000) and its two
riders (a low-load oldest-recall cost; inherited content still below the bar at 1,000), as
listed in `docs/research/HYPOTHESES.md`.

## What is identical to P2-R2

Everything scientific: the F10/s60 canonical items from `FamilyGen`, the row-Curveball
block trade with exactly 10,000 attempted trades per 100-episode block (chain 0 delivered,
chain 1 diagnostic), the structural checks and the STRUCTURAL CONTRAST UNCERTAIN flags, the
inherited E3 learner with J_mem = 1.525, accommodation tau = 10,000 ms, J_fb = 2.80, g = 0.3,
the 50 ms index and 75 ms content windows, the two loads 500 and 1,000, the deep-copied
checkpoint evaluation with a 50 s settle, 200 half cues, 200 novel half cues and 200 full
cues, the inherited and assigned-A content stores at the frozen readout, the validity bars,
the four ordered labels at M = 1,000, the raw bar-deficit fraction, the M = 500 reporting
rules, the small original/sham parity check (m = n = 256, a = 64, f_q = 0.05, 20 episodes),
the F40 structural-only diagnostic, and the 20-minute two-worker ceiling. The frozen
`analysis/p2r2_degree_null.py` is executed unchanged; the wrapper below only redirects where
it reads its seeds and writes its evidence.

## What differs, and why

1. **Seeds 105 and 106.** Audited 2026-10-22: no recognised seed field in any
   `bench/results/*.jsonl` record, contract, driver or review uses 105 or 106; the only
   textual hits are unrelated numbers. No substitution during a run.
2. **Evidence durability.** Every combined artifact, structural file and journal line is
   written through `plant2/evidence.py` (`write_json_artifact`, `write_npz_artifact`,
   `Journal`), so each artifact is created exclusively, fsynced, read back and hashed before
   its descriptor exists, and each worker has its own hash-chained journal
   (`bench/results/p2r2b/seed<seed>.journal.jsonl`) in addition to the shared results file.
   Before `paired_evidence` and before any `seed_complete` record, the wrapper verifies every
   descriptor in the stage manifest with `verify_artifact` and `Manifest.require`; a failure
   records INVALID with the failing name, exactly as P2-R2 would have, but now at the moment
   the evidence is consumed, with the size and hash that were recorded at the write.
3. **A wrapper driver, `analysis/p2r2b_replication.py`,** imports the frozen module and
   overrides, explicitly and only, its module-level `SEEDS`, `RESULTS`
   (`bench/results/p2r2b.jsonl`), `EVIDENCE` (`bench/results/p2r2b/`), `CONTRACT_PATH` and
   `CONTRACT_COMMIT` (this file and its freezing commit), its cache root (through
   `BRAINSIM_CACHE`, so the resource window and seed claims live under
   `~/.cache/brain-sim/plant2-research-20261022/p2r2b/`), and its two writer functions
   `write_json` and `write_npz` (to the evidence module's). The source manifest check keeps
   the frozen driver and all inherited sources byte-identical to the takeover baseline
   `55e16eb`; the wrapper adds itself, this contract and `plant2/evidence.py` to the manifest.
   The wrapper contains no scientific code: no item generation, learning, evaluation,
   scoring or labelling. A unit test asserts that the wrapper's module namespace differs from
   the frozen one only in the names listed here.
4. **Runtime.** This PC: CPython 3.11.17, NumPy 2.4.6 (P2-R2 ran on 3.12.14 / 2.3.5). Both
   are recorded by `record.runtime()`. The contract does not claim byte-identical rasters to
   P2-R2; it claims the same protocol on fresh seeds.
5. **Two workers, started together,** one seed each, as in P2-R2. At most four simulation
   processes machine-wide; BLAS threads capped at one.

## Predictions (frozen before implementation; written from P2-R2's valid seed 103 and the
descriptive seed-104 reconstruction, which are the only prior data)

- P1. Both seeds complete every mandatory stage and pass the structural checks at both
  loads; neither load is STRUCTURAL CONTRAST UNCERTAIN.
- P2. At M = 1,000 both seeds carry the label MATERIAL STRUCTURE SENSITIVITY: Delta C2 >= 0.15,
  Delta joint-index >= 0.10, Delta C1 and Delta C4-recall both > -0.03.
- P3. At M = 1,000, null C2 stays below 0.90 on both seeds, and the raw C2 bar-deficit
  fraction removed lies in 0.5-0.8 on both.
- P4. At M = 1,000, inherited content S2 stays below 0.15 on both arms and both seeds;
  assigned-A content stays below 0.40.
- P5. At M = 500, on at least one seed the oldest-recall (C4-recall) delta is <= -0.03, so
  the low-load index gain does not meet the recall-preserving reading, while inherited content
  rises by >= 0.10 (a material content gain).
- P6. Own responders change by less than 1.0 cell per cue at M = 1,000 and spurious
  responders fall by more than 10 cells per cue (the "not global silencing" reading).

A contradiction of P2 on either seed is recorded as disagreement with P2-R2 and sends the
mechanism choice back to the roadmap; it does not trigger a third seed under this contract.

## Resource stop and status

Twenty wall minutes from the first P2-R2b process, two workers, no new stage after minute
18, in-flight stage checkpointed by minute 20, PARTIAL retained with every missing stage
listed. Measured on this PC before the run: the frozen test suite's small-network checks
only; no fresh full-size benchmark (P2-R2 took 194-198 s per seed on an eight-core host).

The formal result is COMPLETE only if both seeds are COMPLETE with every descriptor verified;
one INVALID seed makes the formal result INVALID again, with no replacement seed. The result
is appended to `docs/research/EXPERIMENTS.md` and `HYPOTHESES.md` with its label copied, not
paraphrased.

## What this cannot show

Nothing beyond P2-R2's own scope: it is a finite block-constrained randomisation, not a
causal partition into frequency and correlation contributions; fine timing, actual
eligibility, coin alignment and adaptive state change with the inputs. A replicated label is
an explanation result that informs which mechanism to contract next; it is not a memory
capability, removes no experimenter supply and authorises no Stage 2 work.
