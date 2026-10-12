# P2-R1: independent baseline and burst-write replay

Predeclared reported diagnostic, 2026-10-12. This contract is committed before its driver.
It creates no PASS label and does not reopen any P2-E1..E5 gate.

## Questions and scope

1. Do committed P2-E4/E5 counts and verdicts support the reported failures?
2. Does R_3 improve content on unchanged memory rasters beyond merely reducing writer count?
3. Does this hold in the longer-gap duty regime and where correlated inputs damage the index?

Raw historical artifacts live outside Git and are absent in this environment. Audit all available
aggregate records, their provenance, and raw-artifact availability. Do not call an aggregate check
a raw-data replication. Reproduce selected exploratory timelines with the inherited engine; record
runtime versions and any disagreement instead of requiring cross-platform bit identity.

## Frozen design

- Correlated settled line: existing exploratory seed 44, canonical F=10/s=60 generator and
  P2-E3 learning protocol, checkpoints M=500 and 1000, inherited full cue sets and settle.
- Independent online duty line: existing diagnostic seed 90, P2-E4 I=2000 ms duty schedule
  (`post=duty_post`, `bg_key=(ARMS, ARM_DUTY)`), M=500 and 1000. Capture continuation counts
  without changing random draws or neural dynamics. Score online index with inherited functions;
  replay feedback-store swaps on its settled P2-E3 twin. This is a store-quality diagnostic,
  not evidence that all online requirements pass.
- If resources permit, repeat correlated seed 45 and duty seed 91 as reported replications.
  Mandatory runs are attempted first. Partial runs are explicitly incomplete, not failures.
- Five writers: inherited R_1; assigned plateau A (oracle comparator); R_3; uniform random subset
  of R_1 of exactly |R_3|; anti-selected subset of R_1 of exactly |R_3| with lowest spike counts
  (ties use a separate deterministic permutation). Random/tie stream is `(seed, 30, item, kind)`.
  Both controls select from observed responders, never using A. No top-k oracle is deployed.
- All writers store the same eligible sensory lines, with the same clipped union rule.
- Readout frozen at J_fb=2.80 and g=0.3; index 50 ms, content 75 ms. No grid or calibration.
- Index and content are reported separately. Record C1..C4, content joint, D3 and oldest D4,
  per-cue outcomes, writer precision/recall against A, counts, store digests and raster digests.
- Check capture R_1 equality and inherited feedback union equality; swaps cannot alter the
  memory raster. Preserve full replay inputs as a compressed cache artifact plus a hash; commit
  portable compact per-cue outcomes and result records so new aggregate claims are independently
  auditable from Git. Never overwrite a completed run or auto-clean artifacts.

## Predictions (not measured)

- F=10/M=500: R_3 joint at least 0.85, inherited below 0.25; R_3 within 0.05 of A.
- F=10/M=1000: R_3 and A both below 0.90 at the frozen readout, because index interference
  persists. Index C2 below 0.65. A feedback-only swap does not improve index.
- Duty/M=1000: R_3 joint at least 0.90 and exceeds random and anti-selected by at least 0.10;
  inherited joint below 0.35. This tests writer identity beyond sparsity.
- Habituation, capacity scaling and forgetting are not newly tested by these swaps. Existing
  failures remain; successful store swaps cannot close Stage 1.

## Independent review and decision

Audit methodology and implementation with fresh specialist reviewers. Findings and dispositions
go to review/plant2/P2-R1/ and the append-only review ledger. Correct documentary errors by
appending errata. Use the measured result to select one forward-index mechanism; do not tune R_3.
