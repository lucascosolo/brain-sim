# P2-R3 independent results review

Reviewed 2026-10-22 after the replay by an independent read-only reviewer (Opus, in the
architecture-reviewer role), at commit b312940, from `bench/results/p2r3.jsonl`, the 48
per-cue replay tables and the step-0 tables (including the relocated one at its cache path),
the P2-E7 load records and portable evidence that supplied the rasters and stores, the
module `analysis/p2r3_branch_rec.py`, the frozen readout and scoring, and `plant2/evidence.py`.
No simulation was run beyond re-running the frozen point readout on two substrates for the
parity check; no file was modified; recomputation scripts stayed in the reviewer's scratchpad.

**Verdict: CORRECTIONS NEEDED (wording only). Every quoted number reproduces from the
per-cue tables, P1-P12 are scored correctly and no kill fired.**

## Reproduced

- All 48 replay cells (joint, D1, intrusions median, novel-lines median) recomputed from the
  per-cue tables with the 200 half and 200 novel cues of each raw NPZ: 192 values, zero
  mismatches against the record summaries and the RESULTS table. Scramble joint and D1 .000
  in all 8 cells; novel-lines median 0 in all 48.
- Mixed subsets from the per-cue rows, the state labels and `cue_index`: independent 34 → 95
  of 95; F10 2 → 71 of 105 (assigned-A 103, K = 8 39, unbounded 79 of 105).
- Parity: the K = 1 table equals the persisted `content_rows.inherited` (600 rows, every
  column, latency included) on all 8 substrate/loads; `sha_array(feedback_keys)` equals the
  portable `feedback_sha256` in all 8; the frozen `plant2.readout.replay` rerun independently
  on gate_off 500 and label_oracle 1,000 equals both the K = 1 table and the persisted rows.
- Step 0: class counts and every per-line summation flag re-derived from the stored
  per-episode active-writer counts and `required`: gate_off 500 171 / 1 / 170 / 0, 0.9766;
  gate_off 1,000 (relocated table) 199 / 0 / 198 / 1, 1.000; label_oracle 500 2 / 2 / 0 / 0;
  label_oracle 1,000 138 / 3 / 135 / 0, 0.9783 (assigned-A 15 / 1 / 14 / 0 .933; 178 / 2 /
  169 / 7 .989; 2 / 2 / 0 / 0; 100 / 3 / 97 / 0 .970); mean active cells match; the kill was
  evaluated as the contract states and did not fire.
- Predictions: held P1, P4, P7, P9, P10, P11, P12; failed above the range P2 (.985 > .95),
  P3 (.985 > .98, one cue), P5 (.345 > .30), P6 (.710 > .50), P8 (95 > 80); no kill fired;
  the summary record agrees.
- Integrity: 18 journals verify (P2-R3's 70 records, the P2-E7 coordinator and 16 arm and
  rider journals); all 52 `artifact_written` descriptors in the P2-R3 journal verify, the
  relocated table at its cache path (sha256 4b70939e…, 158,841,936 bytes); all 76 unique
  descriptors in the records verify; the three `evidence_verification` records passed
  (verifying 0, 4 and 48 artifacts); the contract unchanged between 2c59cfa and b312940 apart
  from the appended Result.

## Findings and dispositions

| # | severity | finding | disposition |
|---|---|---|---|
| 1 | FIX | record counts: 4 COMPLETE `step0` rows plus 4 ABSENT rows of the refused first attempt (not "8 plus 5"; not "two" ABSENT rows); the journal has 4 `step0_absent` entries | accepted; erratum 1 |
| 2 | FIX | wrong load: the mixed store (.830, independent subset 95 of 95) is M = 1,000, not "the deployable M = 500" | accepted; erratum 2 |
| 3 | FIX | label upgraded: "H-085 supported in the replay" against the ledger's `mixed` | accepted; erratum 3 |
| 4 | FIX | H-085 Status counts the candidate substrate as "exact"; it is a stacking diagnostic, reported only | accepted; erratum 4, HYPOTHESES corrected |
| 5 | FIX | H-085 Notes: the assigned-A branch store is at least the inherited one in all 8 cells, so "not an upper bound" is wrong; equal on the oracle only | accepted; erratum 5, HYPOTHESES corrected |
| 6 | FIX | H-046 sentence reversed: the point store is summation-limited; with branches, content is limited by what remains | accepted; erratum 6, HYPOTHESES corrected |
| 7 | NOTE | "the index limits content" at gate_off 1,000 conflicts with the assigned-A arm (.925 with C2 .500): the residual lives in the responder-written writer sets (write-time contamination, H-036), not in cue-time recall; "content tracks the index" is a three-point observation on one seed, two of the points diagnostics | accepted; erratum 7 (a change of reading, carried to ROADMAP §8 and H-085) |
| 8 | NOTE | "about forty write events" is in no record: eligible write events per line are gate_off 500 median 9, p99 48, max 71 (179 lines over 32); label_oracle 1,000 median 17, p99 94, max 136 (891 lines over 32); the tail exceeds K = 32 well beyond the M·a/m = 25 premise | accepted; erratum 8 |
| 9 | NOTE | "exact" applied to the whole replay, including the candidate substrate, in the RESULTS title and header, the EXPERIMENTS label and ROADMAP §8 | accepted; erratum 9 |
| 10 | NOTE | the M = 500 bullet frames a non-gate as a gate ("nearly clears the bar") and the R_3 comparison is self-contradictory (.895 < .925) | accepted; erratum 10 |
| 11 | NOTE | H-085 confidence "high" from one seed's rasters | accepted; reworded to "high on seed 121's rasters; untested elsewhere" |
| 12 | NOTE | the per-cue summation rule (a cue counts only if more than half of its intrusion lines are cross-episode with no single episode reaching the requirement; the kill reads the inherited store) is not written in the contract; the majority rule equals an any-line rule in every inherited cell here | accepted; erratum 11 (operationalisation recorded) |
| 13 | NOTE | one `evidence_verification` is vacuous (0 artifacts, the refused attempt); the relocated table's journal descriptor names its original path, so re-verification needs the `artifact_relocated` record applied by hand | accepted; erratum 12 |
