# P2-R2b independent results review

Reviewed 2026-10-22 after execution by an independent read-only reviewer (Opus, in the
architecture-reviewer role), from `bench/results/p2r2b.jsonl`, the portable evidence under
`bench/results/p2r2b/`, both worker journals, the frozen rules in `analysis/p2r2_degree_null.py`
and the wrapper `analysis/p2r2b_replication.py`. No simulation was rerun and no file was
modified; recomputation scripts stayed in the reviewer's scratchpad.

**Verdict: CORRECTIONS NEEDED (wording only). Every number reproduces from the per-cue rows
and the frozen rules, and P1-P6 are scored correctly.**

## Reproduced

- Index metrics: C1 (own50 >= 0.8 A_size), C2, joint index, oldest recall and oldest
  specificity recomputed from `index_cues` (200 half, 100 oldest, 200 novel cues) for all
  eight seed/arm/load cells match `load_complete.result.index` and every cell of the RESULTS
  table at three decimals. C1 by own50 equals C1 by recall50 everywhere. C3 is .990-1.000.
- Content: inherited and assigned-A joint fractions from the `-inherited.json` /
  `-assigned_A.json` tables and from the combined artifacts' content tables are identical to
  each other and to `load_complete.result.content.*.joint`.
- M = 1,000 decisions: Delta C2 +0.260 / +0.265; Delta joint index +0.240 / +0.280; Delta C1
  -0.010 / +0.035; Delta oldest recall -0.020 / +0.030; `classify` gives MATERIAL STRUCTURE
  SENSITIVITY on both seeds; bar-deficit fraction 0.6265060 / 0.5955056.
- M = 500: `low_load_material_gain` False on 105, True on 106; inherited content delta
  +0.845 / +0.825 (MATERIAL GAIN).
- P6: seed 105 own -0.025, spurious -10.46 (pass); seed 106 own +0.265, spurious -6.97 (fail).
- Evidence integrity: seed 105, 33 descriptors re-read with matching size and SHA-256, 36
  journal lines with contiguous seq and an intact chain; seed 106, 31 descriptors matching,
  34 lines, chain intact; `artifacts_verified` equals the descriptor count on both.
- Protocol: eligibility and settled true in all eight cells; mean |A| at 1,000 is 20.017 /
  20.04; F10 and F40 `decision.ok` true at both loads on both seeds; parity passed;
  `seed_complete` COMPLETE with empty missing lists; wall_s 154.48 / 152.03.

## Findings and dispositions

| # | severity | finding | disposition |
|---|---|---|---|
| 1 | FIX | "line load alone does not explain the residual failure" is unsupported and "co-occurrence structure is a material part of it" reads as the causal partition the contract rules out | accepted; erratum 1 in RESULTS-P2-R2b.md |
| 2 | FIX | "every artifact ... re-verified before `paired_evidence`" overstates: only the two combined descriptors are verified there; all artifacts after `run()` | accepted; erratum 2 |
| 3 | FIX | the seed-106 P6 explanation ("fewer spurious responders to remove") does not fit the data (15.47 → 8.50, 45 %, versus 17.57 → 7.11, 59 %); the qualitative reading re-reads a failed prediction | accepted; erratum 3 |
| 4 | NOTE | assigned-A content changes at 1,000 are MATERIAL GAIN (+0.140, +0.185); at 500 INTERMEDIATE/SMALL CHANGE | accepted; erratum 4 |
| 5 | NOTE | "condition ... now met" goes beyond "informs which mechanism to contract next" and does not cite the review | accepted; erratum 5 |
| 6 | NOTE | "no git command ran" is not backed by a record | accepted; erratum 6 (operator's account) |
| 7 | NOTE | P6 output not persisted | accepted; `p6_prediction` records appended to p2r2b.jsonl |
