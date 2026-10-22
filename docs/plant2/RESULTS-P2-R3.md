# P2-R3 results: the episode-clustered reconstruction store, replayed exactly on the P2-E7 seed-121 rasters

Measured 2026-10-22, 23:24-23:46 UTC, on this PC (CPython 3.11.17, NumPy 2.4.6,
`OPENBLAS_NUM_THREADS=1`), from commit 62369c5 (contract frozen at 2c59cfa,
`docs/plant2/P2-R3-branch-reconstruction-replay.md`; module `analysis/p2r3_branch_rec.py`
at 0195131 and 62369c5, 17 tests). Records: `bench/results/p2r3.jsonl` (8 `step0`,
8 `parity`, 48 `replay`, 3 `evidence_verification`, 1 `summary`, 1 `artifact_relocated`,
plus 5 `ABSENT` rows of a first step-0 attempt refused on input discovery before any
artifact); per-cue tables under `bench/results/p2r3/` (one 159 MB step-0 table relocated to
the cache, descriptor unchanged). **A reported replay on one development seed's persisted
rasters: not a capability, not a gate, no fresh seed; it credits nothing.** Every number is
**reported-only (exact replay), development seed 121**.

**Formal status: COMPLETE.** Step 0 did not kill; every parity check held (K = 1 reproduced
every persisted `content.inherited` row and the point store's SHA-256 on all eight
substrate/loads, and the assigned-A store rebuilt); no replay kill fired; three
`evidence_verification` records passed. Predictions P1, P4, P7, P9, P10, P11 and P12 held;
P2, P3, P5, P6 and P8 failed, every one of them by exceeding the predicted upper bound.

## Step 0: what fails at content, and why

Point store, half cues (200 per substrate and load), inherited store unless stated:

| substrate | failing cues | by D1 (missing < 40) | by intrusions (≥ 10) | both | fraction failing by cross-episode summation | memory cells active 0-49 / 50-74 ms |
|---|---|---|---|---|---|---|
| gate_off 500 | 171 | 1 | 170 | 0 | 0.977 | 22.0 / 23.5 |
| gate_off 1,000 | 199 | 0 | 198 | 1 | 1.000 | 39.7 / 42.3 |
| label_oracle 500 | 2 | 2 | 0 | 0 | 0.000 (nothing to decompose) | 19.0 / 18.1 |
| label_oracle 1,000 | 138 | 3 | 135 | 0 | 0.978 | 20.5 / 18.8 |

"Cross-episode summation" counts a failing cue whose intrusion lines have active writers
spanning at least two contributing episodes with no single episode reaching the frozen
coincidence requirement ceil(0.3·N_active + 7.14). The contract's kill (fewer than half on
the oracle at 1,000) was far from firing: 97.8 %. The assigned-A store gives the same
picture (oracle 1,000: 100 failing, 97 by intrusions, 0.970).

## The replay

Content joint (≥ 40 of 50 missing lines regenerated and < 10 intrusions) through the
inherited responder-written store; the point readout (K = 1) is the frozen one.

| substrate / load | K = 1 (point) | K = 32 (the rule) | scramble (K = 32, episodes destroyed) | assigned-A store, K = 32 | K = 8 | unbounded | D1 point → K = 32 | intrusions median point → K = 32 |
|---|---|---|---|---|---|---|---|---|
| gate_off 500 (deployable) | .145 | **.895** | .000 | .995 | .710 | .895 | .995 → .995 | 71 → 1 |
| gate_off 1,000 (deployable) | .005 | **.345** | .000 | .925 | .055 | .495 | .995 → .950 | 1,771 → 32 |
| label_oracle 500 (diagnostic) | .990 | .990 | .000 | .990 | .990 | .990 | .990 → .990 | 1 → 0 |
| label_oracle 1,000 (diagnostic) | .310 | **.985** | .000 | .985 | .985 | .985 | .985 → .985 | 18.5 → 0 |
| candidate 1,000 (stacking diagnostic, reported) | .005 | .710 | .000 | .950 | .325 | .795 | .980 → .965 | 554 → 1 |
| independent 500 | .995 | .995 | .000 | .995 | .995 | .995 | .995 → .995 | 0 → 0 |
| independent 1,000 | .960 | .975 | .000 | .975 | .975 | .975 | .975 → .975 | 1 → 0 |
| mixed baseline 1,000 | .180 | .830 | .000 | .990 | .670 | .870 | 1.000 → .995 | 118.5 → 1 |

Mixed baseline at 1,000 by subset (joint count of cues): independent 34 → 95 of 95; F10 2 → 71
of 105. Novel half cues regenerate 0 lines (median) under every store. Index values are
identical to P2-E7's by construction.

## The twelve frozen predictions

| prediction | outcome | evidence |
|---|---|---|
| P1 parity | held | 8 of 8 `feedback_sha256_equal` and `content_rows_equal`; index identical |
| P2 oracle 1,000 inherited joint in [0.60, 0.95] (kill < 0.46) | **failed, above**: .985 | no kill |
| P3 oracle 1,000 assigned-A branch joint in [0.70, 0.98] | **failed, above**: .985 | — |
| P4 gate_off 500 in [0.50, 0.95] (kill < 0.345) | held: .895 | no kill |
| P5 gate_off 1,000 in [0.00, 0.30] | **failed, above**: .345 | — |
| P6 candidate 1,000 in [0.05, 0.50] | **failed, above**: .710 | reported substrate |
| P7 independent ≥ .975 / ≥ .940 (kill: drop > 0.05) | held: .995 / .975 | no kill |
| P8 mixed independent subset in [32, 80] cues | **failed, above**: 95 of 95 | — |
| P9 scramble ≤ 0.41 on the oracle (kill: within 0.05 of K = 32) | held: .000 (regenerates nothing; D1 .000) | no kill |
| P10 novel cues ≤ the point store's | held: 0 everywhere | — |
| P11 dose non-decreasing in K | held on every substrate (gate_off 1,000: .055 ≤ .345 ≤ .495; candidate: .325 ≤ .710 ≤ .795) | reported |
| P12 D1 within 0.05 of the point store's | held (largest drop 0.045, gate_off 1,000) | — |

No prediction is revised; the five misses are recorded as under-predictions.

## What this establishes, and what it does not

- **The content wall at F10/1,000 is cross-episode writer summation on the reconstruction
  lines**, on this seed's rasters: every content failure but a handful is an intrusion
  failure whose active writers span several episodes, and clustering each episode's writers
  on one of K = 32 line-local branches removes it exactly where the index is clean (oracle
  .310 → .985 with zero median intrusions; assigned-A store .985). H-085 supported in the
  replay; H-046's "index-limited" reading narrowed: content tracks the index once summation
  is removed (gate_off C2 .500 → .345; candidate C2 .745 → .710; oracle C2 .970 → .985).
- **Episode clustering, not splitting, is the ingredient.** The per-synapse scramble (same
  K, same writer multiset per line, episode membership destroyed) regenerates nothing at
  all (joint and D1 .000 on every substrate): split at random across 32 branches, no branch
  reaches threshold. The branch store works because an episode's writers arrive together.
- **At the deployable M = 500 the rule nearly clears the bar** (gate_off .895 against .90; the
  mixed store .830 with its independent subset at 95 of 95 cues) and improves over the R_3
  rider's .925 only in kind (no writer selection, no burst threshold), not in level.
- **At the deployable M = 1,000 the index still limits content** (.345), as predicted in
  direction, more than predicted in size; the unbounded dose (.495) shows the bounded K = 32
  store shares some branches at 1,000 (prototype lines see about 40 write events).
- **D1 costs little** (≤ 0.045): branches remove some cross-episode support for own missing
  lines, as the contract anticipated.
- **Not shown:** anything on a fresh seed; any capability; whether a deployed branch readout
  changes memory dynamics (it cannot on these substrates, where the feedback store never
  feeds back); the behaviour of K = 32 past M = 1,000 (bounded forgetting is not tested);
  deployment, which needs the owner's rulings (g) on ordering against ruling 3 and (a)
  extended to reconstruction lines (ruling 6).

## Failure classification

None. A reported replay whose kill and parity rules all held; five predictions
under-predicted the effect. The two first-attempt step-0 rows marked ABSENT came from an
input-discovery defect in the module (fixed at 62369c5 before any artifact), not from
evidence. The 159 MB step-0 table of gate_off at 1,000 was relocated to the cache after the
remote refused it; its recorded descriptor verifies at the new path (`artifact_relocated`).
