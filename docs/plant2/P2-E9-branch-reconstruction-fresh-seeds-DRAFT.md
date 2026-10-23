# P2-E9: the bounded episode-clustered reconstruction store on fresh seeds — DRAFT v1

Draft contract, 2026-10-22, written after P2-R3 (`docs/plant2/RESULTS-P2-R3.md`, with its
twelve errata) so that the content mechanism it replayed can be contracted the moment the
owner rules. Not frozen; not reviewed; **blocked on owner questions (g) and (a)** of the
2026-10-22 checkpoint-2 entry in `DECISIONS.md`: whether a fresh-seed content contract may
precede an index pass (ruling 3 puts the index first), and whether the dendritic-subunit
question (a) extends to reconstruction lines (ruling 6, frozen deployed readout primary).
Seeds are proposed here and are assigned only by the `DECISIONS.md` entry that selects this
contract: development **125**, held-out **126**, gated **161-165** (all unspent; the registry
holds 121-124, 131-135, 141-145, 151-155, 107-109).

## Question and hypotheses

On fresh seeds, does a reconstruction store that clusters each episode's writers on one of
K = 32 line-local branches, read through the frozen readout arithmetic with the line
spiking when any branch spikes, regenerate stored content from half cues at the Stage 1
content bars where the point store does not, without changing the writers, the index or any
learning rule, and without regressing on uncorrelated items?

Hypotheses: **H-085** (`mixed`, replay-only; this is the fresh-seed test that could move it);
H-046 (content below the bar at F10/1,000 through the point store; the branch store's value
there is reported); H-036 (writer contamination: the assigned-A diagnostic store bounds it);
H-052, H-057.

## What is inherited unchanged

Learning is the literal E3 learner (P2-E7's `Baseline` with the condition's generator, its
test-time wrapper, snapshot and `evaluate_load`), so every forward and feedback write, the
plateau draw, eligibility, coins, continuation and R(x) are P2-E3's; conditions F10,
independent and mixed (`MixedGen`, stream 36) and F40 (reported); loads 500 and 1,000; the
settled test protocol and the 50 ms index criteria (identical on every arm by construction,
reported once); the frozen 75 ms readout constants and the content criteria (joint ≥ 40 of
50 missing lines regenerated and < 10 intrusions; D1-D4 as `e3.score`); the branch store and
readout exactly as P2-R3 implemented and the review reproduced (`analysis/p2r3_branch_rec.py`
pinned at 62369c5: round-robin line-local branches, K = 32 by the power-of-two rule from
M·a/m = 25, K = 1 the frozen readout as a parity gate, the per-synapse scramble on stream 37
keyed by line, the OR over branches with independent resets); the evidence discipline,
resource window and seed-guard pattern of P2-E7.

## The mechanism (replayed at test time on each fresh raster; one mechanism)

Unchanged from P2-R3: the feedback store is kept as K = 32 writer sets per line filled
round-robin by eligible episode (the counter n_j and the add-only union within a branch);
at test the reconstruction units are the (line, branch) compartments under the frozen
constants, and the line spikes when any branch does. Nothing feeds back into memory
dynamics on any arm, so the branch readout is a function of the persisted raster and the
store, exactly as in the replay. No constant, window, bar or learning rule changes.

## Arms (readouts on the same learned trajectory per condition)

| arm | store / readout | role |
|---|---|---|
| `point` | the frozen point store and readout (K = 1) | reference; must equal the frozen `evaluate_load` content rows (parity gate, INVALID otherwise) |
| `branch` | K = 32 episode branches, inherited (responder-written) store | the mechanism |
| `scramble` | K = 32, per-synapse branch assignment on stream (seed, 37, j) | fails if splitting rather than clustering explains the gain |
| `assigned_A` | K = 32 on the A × E diagnostic store | bounds writer contamination (H-036); diagnostic, never credited |
| `K8`, `unbounded` | dose arms | reported only |

One learned trajectory per condition (F10, independent, mixed, F40): four trajectories and
six readouts each. Family labels are read by `assigned_A` and the scoring only.

## Structural checks and kills (before any test phase)

- The parity gate: the K = 1 readout equals the frozen content rows on every condition and
  load, else INVALID.
- Eligible write events per line at 1,000 (the P2-R3 review's recomputed tail: median 9-17,
  99th percentile 48-94, hundreds of lines over 32): the fraction of lines whose branch
  counter exceeds K is reported per condition; it decides nothing (bounded forgetting is a
  later contract).

## Screen rules (development seed)

KILL (FEASIBILITY FAIL; no retuning) if any of:

- F10/500 `branch` `content.inherited.joint` < point + 0.20, or < scramble + 0.20;
- independent `branch` content joint below the point's by more than 0.05 at either load, or
  `D1` below the point's by more than 0.05 anywhere (the cross-episode support cost);
- mixed independent-subset `branch` content joint count below the point's by 5 or more cues;
- novel half cues regenerate more lines (median) under `branch` than under `point` on any
  condition.

FEASIBILITY PASS only if, in addition: F10/500 `branch` joint ≥ 0.90, D3 ≥ 0.90 and D4 ≥ 0.90
(the content bars); independent `branch` joint ≥ 0.90 at both loads. F10/1,000 `branch` is
reported, not a bar (P2-R3: .345 on the deployable substrate, writer-contamination-limited;
the `assigned_A` arm's value is reported beside it). Index values are reported once and
decide nothing (the index is not this contract's target).

## Predictions (set from P2-R3's recorded values on seed 121; all extrapolations to a fresh seed)

- P1 parity: K = 1 equals the frozen rows and feedback SHA-256 everywhere.
- P2 F10/500 `branch` joint in [0.80, 0.97] (P2-R3 gate_off 500: .895), point in [0.08, 0.25]
  (.145), scramble ≤ 0.05 (.000), `assigned_A` ≥ 0.95 (.995).
- P3 F10/1,000 `branch` joint in [0.15, 0.55] (.345); `assigned_A` in [0.80, 0.98] (.925);
  unbounded ≥ branch (.495 ≥ .345).
- P4 independent `branch` joint ≥ 0.97 at 500 and ≥ 0.94 at 1,000 (.995 / .975), no D1 drop
  beyond 0.02.
- P5 mixed at 1,000: independent-subset joint count ≥ point + 40 cues (34 → 95); F10 subset
  ≥ point + 40 cues (2 → 71).
- P6 D1 under `branch` within 0.05 of the point's everywhere (largest P2-R3 drop 0.045).
- P7 novel cues: 0 regenerated lines median under every arm.
- P8 dose: joint non-decreasing in K on F10 at both loads.
- Most likely failure: F10/500 `branch` joint lands just below 0.90 (as on seed 121), an
  informative FEASIBILITY FAIL; or the fresh seed's F10 index at 500 is weaker and content
  follows it.

## What this cannot show

A pass would be a content result on one development seed under a frozen screen, on a
substrate whose index is the frozen P2-E3 index; not a capability until the gated seeds
pass under their own contract, and it says nothing about F10/1,000 content, which is
writer-contamination-limited through the responder-written store (P2-R3 erratum 7). It
removes no experimenter supply (the random key, episode boundaries, the write oracle and
its timing, the verbatim feedback value and the test regime stay; the episode boundary now
also drives the branch counter). Deploying a branch readout changes the reconstruction
layer's integration while keeping every frozen constant: it needs the owner's ruling (a)
extended to reconstruction lines, and running a content contract before an index pass
needs ruling (g). K past M = 1,000 (bounded forgetting) is a later contract.

## Compliance notes

One mechanism (the branch store); the point readout is always reported beside it (ruling
6); no stacking (no index mechanism in this contract; the learner is literal E3); R_3 is not
used (ruling 1); the 50 ms and 75 ms windows, F = 10 canonical, no LLM, no teacher current,
frozen drivers untouched, no deletion, no retuning after a failed screen.
