# P2-E5: item-specific recall on correlated inputs (structured-input diagnostic)

**Draft. Not yet a contract and not yet red-teamed.** No P2-E5 code exists, and its gated seeds
(21-25) have not been touched.

Ordered by the owner on 2026-10-10 (`DECISIONS.md`, rulings 1 and 4), as a new Stage 1 gate,
with this sequence:
1. run the existing system first, with **no new mechanism**;
2. if it fails, investigate the responder-based feedback write against the plateau-set baseline;
3. any correction is a separately contracted single mechanism.

The capacity-scaling experiment, provisionally called P2-E5 in
`docs/plant2/EVAL-after-P2-E3.md`, will take the next free number when its contract is written.

## Why this test

- **Every gated item so far was an independent random pattern,** with about 2.5 % pairwise
  overlap. Stage 2's shared items and Stage 3's exemplars are correlated by definition.
- **Exploratory evidence** (labelled; two seeds; reviewer script re-run unchanged by me; the
  P2-E3 addendum, item 3). Frozen P2-E3 values, 10 never-shown prototypes, siblings sharing
  about 16 of 100 lines:

  | measure | seed 99 | seed 97 |
  |---|---|---|
  | content joint at M = 500 | 0.147 | 0.167 |
  | same raster, plateau-set store | 0.94 | 0.94 |

  - **The cause:** |R(x)| rises to 50-52 against |A(x)| of about 20. Sibling assemblies fire
    during the continuation and write their own lines into x's feedback.
- **The owner's objective.** Remember previously experienced correlated items without
  contamination. Generalising to a never-seen family member belongs to Stage 3, so here it is
  reported, never gated.

## Hypothesis (the one the existing system is expected to fail)

The frozen P2-E3 system stores exemplars of related families, with about 16 % sibling overlap,
item-specifically. From a half cue it regenerates the item's own missing lines, including its
item-specific ones, with few intrusions from the shared prototype or from siblings. It does so
at M = 500 and M = 1,000 by P2-E3's criteria.

## No new mechanism; one changed variable

- **Everything is P2-E3 exactly:**
  - the network and stores;
  - J* = 1.525 mV, accommodation tau 10 s, J_fb* = 2.80 mV, g = 0.3;
  - the episode (200 ms encoding plus 50 ms continuation, `quiet()` between items);
  - the 50 s settle and the frozen-copy test.
- **Only the item distribution changes.** This is deliberate: P2-E4 isolates online operation,
  and this experiment isolates input structure. A system that is to complete Stage 1 must later
  pass both.

## Items

- **Families.** F = 10 prototypes, each a random set of 100 of the 4,000 lines. Prototypes are
  never shown.
- **An exemplar** of family f keeps `100 - s` of the prototype's lines, chosen at random, and
  adds `s` random lines from outside the prototype.
- **Learning order.** Items cycle through the families (item k belongs to family k mod F), so
  every family is represented at every age.
- **Sibling overlap.** Two siblings share about (100 - s)^2 / 100 prototype lines, plus chance
  overlap.

| s | sibling overlap | role |
|---|---|---|
| 60 | about 16 % | **gated** |
| 80 | about 4-6 % | diagnostic arm |
| 40 | about 36 % | diagnostic arm |
| 100 (independent items, P2-E3's generator) | about 2.5 % | diagnostic arm |

- **Family size.** At M = 500 each family has 50 stored exemplars, and at M = 1,000 it has 100.
- **The generator** draws from its own streams (ids 20-23, reserved for P2-E5). Every other
  stream (plateaus, input, coins, test picks) is P2-E1's.

## Test (P2-E3's protocol, at each load)

- **Learning and test.** Learning runs to M. A deep copy gets the 50 s settle, then P2-E2/P2-E3's
  test:
  - 200 half cues of stored items (the 100 oldest plus 100 random);
  - 200 novel cues: random independent items, as before;
  - 200 full cues.
- **Reported cues.** Appended after the gated blocks, so they cannot affect gated scores:
  - 100 half cues of **new exemplars** of known families (never stored);
  - 50 half cues of the prototypes.
- **Scoring.** P2-E3's code, plus a split of the missing lines into prototype lines and
  item-specific lines.

## Kill test

- **Gated seeds:** 21-25, all fresh.
- **Gated condition:** s = 60, at M = 500 and 1,000.
- **No calibration:** every value is frozen from P2-E2 and P2-E3.

| criterion | bar (every gated seed and load) |
|---|---|
| **S1 memory** | P2-E2's C1, C2 and C3, each >= 0.90 |
| **S2 content** | P2-E3's joint criterion (>= 40 of 50 missing lines, < 10 intrusions, 75 ms) for >= 90 % of the 200 half cues |
| **S3 unlearned** | D3 (< 10 lines) for >= 90 % of the 200 random novel cues |
| **S4 oldest** | the joint criterion for >= 90 % of the 100 oldest items |

**Validity:**
- the forward store equals P2-E1 learning on the same items;
- the eligible fraction is >= 0.95, and mean |A| is 18.5-21.5;
- the test copies leave the main line's stores and `vbar` unchanged (digests);
- convergence is gated on **signed** drift (P2-E2 review F7): |signed mean drift| <= 0.1 mV over
  the last 10 s of the settle.

**Verdicts:**
- **PASS:** S1-S4 hold.
- **FAIL:** any of S1-S4 fails, with the failing criteria named.
- **INVALID:** a validity check fails.

## Comparison arms (reported, not gated)

**Arms built on the same raster** (no extra learning):
- **Plateau-set store** (A(x) x E(x)). The exploratory baseline that held at 0.94. It isolates
  the responder write.
- **Within-family label permutation.** x's responders carry the lines of a sibling pi(x). This
  measures how much of the regeneration is family-generic rather than item-specific. It is a
  specificity control that could pass if regeneration were only family-generic.
- **Shuffled feedback.** A leak check.

**Overlap arms** (s = 80, 40 and 100), learned on the same seeds, same loads.

**Per-load diagnostics:**
- |R(x)| against |A(x)|; sibling responders in the continuation;
- regeneration of item-specific against prototype missing lines;
- intrusions split into prototype, sibling-specific and other lines;
- new-exemplar and prototype half cues (what is regenerated, and how many memory cells
  respond);
- feedback density, and bits per synapse.

## Predictions

From two exploration seeds at M = 500 (to be extended to M = 1,000 and to the overlap arms on
red-team seeds 44-45 before the contract is frozen):

| criterion or arm | prediction |
|---|---|
| S2 (s = 60) | **FAIL**: joint about 0.15 at M = 500, lower at M = 1,000 |
| S1 | C1 holds (about 0.95); C2 probably holds; C3 holds |
| S3, S4 | S3 holds; S4 fails with S2 |
| plateau-set arm | about 0.94 at M = 500 |
| s = 80 arm | about 0.99 |
| s = 40 arm | collapses (rec saturates) |

**Expected verdict: FAIL on S2 (and S4).** It is run anyway because the owner asked for the
baseline record, and because it fixes the target that a correction mechanism must beat.

## If it fails (not part of this contract)

The next contract tests one mechanism aimed at the identified cause, against the plateau-set
baseline. The candidate the owner approved as a research direction is an error-correcting
feedback write driven by the mismatch between input and regenerated content. Its contract must
test two things:
- whether the regenerated content carries useful error information;
- whether corrections preserve unrelated memories.

## Seeds and cost

- **Seeds.** Gated 21-25; red-team exploration 44-45.
- **Cost.** About four timelines to M = 1,000 per seed (the gated arm plus three overlap arms),
  about 4 min each, so about 20 min per seed.
