# P2-E7 independent results review (development seed 121)

Reviewed 2026-10-22 after execution by an independent read-only reviewer (Opus, in the
architecture-reviewer role), at commit d1a0f4e, from `bench/results/p2e7.jsonl`, the portable
evidence under `bench/results/p2e7/`, the cache checkpoints the descriptors point to, the
frozen rules in `docs/plant2/P2-E7-frozen.json` and the contract, and the driver and rider
code. No simulation was rerun and no file was modified; recomputation scripts stayed in the
reviewer's scratchpad.

**Verdict: CORRECTIONS NEEDED (wording only). Every index, content, structural, screen and
rider number in the tables reproduces, and P1-P12 are scored from their named fields in the
right direction.** The errors are in the prose: three counts misquoted, one "every arm"
generalisation false, and several causal readings beyond what one development seed shows.

## Reproduced

- Index metrics for all 28 (condition, arm, M) cells recomputed from `index_cues` (200 half
  cues, 100 oldest, recall50 ≥ 0.8, spurious50 < 0.5·A_size): zero mismatches against
  `load.index` and the portable copies; every table and prose value in
  `RESULTS-P2-E7.md` matches at three decimals (candidate F10/1,000 .895 / .745 / 1.000 /
  .940 / .720 / .645; baseline = gate_off .920 / .500 / 1.000 / .940 / .470 / .425).
- Diagnostics own50, spurious50, total50 recomputed from the rows equal `load.diagnostics`;
  the table rounds half-up; candidate − baseline own50 is 0.045.
- Content: inherited and assigned-A joint (missing ≥ 40, intrusions < 10) equal
  `load.content.*.joint` for all 28 loads.
- Mixed subsets recomputed from the persisted labels: every count equals `index_by_subset`
  and `content_by_subset` at both loads (independent subset at 1,000: baseline 95 / 90 / 94 /
  89 / 48 / 49 / 34; candidate 95 / 91 / 95 / 91 / 48 / 50 / 48; F10 subset C2 64/105 and
  81/105).
- Structural (F10 candidate) from the digest-verified `applied_V_size`: mean |V| 12.958 and
  40.366; per-block 1.03, 4.31, 16.82, 17.84, 24.79, 31.19, 34.60, 37.67, 47.51, 50.86;
  maximum 84; vetoed-episode fractions .684 and .878; first nonzero episode 44. The oracle's
  applied count averages 39.5 from episode 0. Precision, the predicted fractions and
  p_capped are not persisted per episode and were checked against the record only. No kill
  rule fires against the frozen thresholds.
- Screen recomputed by hand: only F10/1,000 C1, C2, C4_spurious and joint fail; C2 margins
  +.245 / +.265 / +.110 against .20 / .10 / .05; joint +.220 / +.235 against .10; C4_recall
  non-regression .94 against .91; C1 non-regression .895 against .89 and .950 against .935;
  independent identical to baseline; mixed cue differences −1, −1, −14 against limits 4 and
  5; `informative` holds; verdict FEASIBILITY FAIL.
- P1-P12 scored from the correct fields in the correct direction (P11: 618 > 511; P10b
  fails on content only, +14 against ±2).
- Integrity: 99 distinct artifact descriptors re-read with matching size and SHA-256; all 16
  portable journals verify; 16 `evidence_verification` records passed and their counts sum
  to 99; gate_off = baseline at 500 and 1,000; independent candidate = baseline on forward,
  feedback and raster digests; gated `matching` identical within every condition and load,
  baseline matching on items, A, E, H; `uniform_integrity` true; pins pass (55e16eb files,
  contract append-only with 2,172 bytes appended, frozen_json e38a6b0; driver and rider blobs
  identical at 9bc6cf3, 6a9e204 and d1a0f4e); `OPENBLAS_NUM_THREADS=1` on every record;
  wall 610.6 s.
- Riders built from gate_off's persisted `cont_counts`, E and R with the R_1 store asserted
  equal to gate_off's feedback keys; content joint R_3 .925 / .140, R_1 .145 / .005, random
  .310 / .015, anti .100 / .000.

## Findings and dispositions

| # | severity | finding | disposition |
|---|---|---|---|
| 1 | FIX | "index counts moved by at most one cue" (RESULTS, P10b evidence, H-060): the independent-subset joint count went 89 → 91 (+2); the quoted candidate joint "89" is wrong; P10b's outcome unchanged | accepted; erratum 1 |
| 2 | FIX | "inherited content .005 on every arm but the oracle" and H-046's "every non-oracle arm": random, history and assigned_A are .000, no_conservation .055 | accepted; erratum 2 |
| 3 | FIX | "first four to fourteen members written in full": with the family map (k + 1) mod 10 the members before first engagement number 4-13 | accepted; erratum 3 |
| 4 | FIX | "the gap is onset and coverage, not the idea": the oracle differs in onset, coverage and precision at once; the design cannot apportion the gap; "not the idea" untested | accepted; erratum 4 |
| 5 | FIX | "Coverage, not precision, limits the gain" and "engages later": assigned_A_teacher's first engagement equals the candidate's in 9 of 10 families; the arm changes the teacher store, not precision alone | accepted; erratum 5 |
| 6 | FIX | causal and generalising readings stated as findings ("not a hot-line filter in disguise"; "because the fully written early members keep feeding spurious responders"; "the veto reduced its own teacher's contamination", a cross-trajectory comparison) | accepted; erratum 6 |
| 7 | FIX | row count: 118 rows (115 run, 2 `rider`, 1 riders `evidence_verification`), not 117 | accepted; erratum 7 |
| 8 | NOTE | H-060 confidence raised to Medium on one exploratory development seed; possibly an upgraded label | accepted; confidence reworded to Low with the comparative evidence labelled exploratory |
| 9 | NOTE | "E6's .785 and the degree null's .960" quoted without a source | accepted; sources added |
| 10 | NOTE | the drop controls' persisted V_sequence is the candidate's applied counts; their own-gate figures and every arm's precision and predicted fractions exist only in the records | accepted; stated in erratum 10 |
| 11 | NOTE | table label "history_drop (E6 counts, stream 34)" misleading: the count is the candidate's, only the line choice is history-weighted | accepted; relabelled |
| 12 | NOTE | rider records copy `source` and `git_commit` from the seed_screen row rather than their own provenance; harmless here (identical blobs) | accepted; noted; fix in the next driver |
