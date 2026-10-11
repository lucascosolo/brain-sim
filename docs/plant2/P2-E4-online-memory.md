# P2-E4: online memory, recall while learning continues

**Contract (2026-10-10). Frozen by the commit that adds this text together with its
`power_reference` record.** No P2-E4 driver code existed before that commit. Gated seeds 16-20
are untouched.

**How it was reviewed:**
- **Draft:** commit 953851e.
- **Red-team:** three lenses, an independent refuter for each lens, and a completeness critic;
  exploration on seeds 42-43 only. Findings are in `review/plant2/P2-E4/redteam-*.md`.
- **Verification of the revision:** three checkers covering schedule and power, coverage of the
  red-team, and implementation ambiguity. Findings are in `review/plant2/P2-E4/verify-*.md`.
- **Decisions on every finding** are in `review/ledger.jsonl`.

**What it gates.** The owner requires this experiment before Stage 1 counts as complete
(`DECISIONS.md`, rulings of 2026-10-10). It gates the following at loads within the
demonstrated capacity (M = 500 and 1,000):
- continuous recall;
- interference resistance;
- retention of the oldest items;
- repeated-cue habituation and recovery.

**What it reports only.** Learning past capacity, and writes during probes, are reported stress
tests, not gates. P2-E2's and P2-E3's contracts and results are not changed.

## Why this test, and why previous passes do not settle it

- **The settle.** P2-E2 and P2-E3 tested frozen copies after a 50 s settle, with learning
  stopped. In exploration (P2-E2 review, seed 0), C1 at M = 1,000 was:

  | rest before test | C1 |
  |---|---|
  | none | 0.875 |
  | 5 s | 0.915 |
  | 50 s | 0.94 |

  A 10-item exploratory run (seed 6) found that a half cue repeated for 30 s cut the share of
  items with recall >= 0.8 from 0.99 to 0.67.
- **The test block is itself a settle.** P2-E3's 600-cue block lasts 180 s, against an
  accommodation time constant of 10 s. So recall has to be measured by short probes interleaved
  into learning.
- **What the red-team found** (rough re-implementations, seeds 42-43, labelled exploratory):
  - **Online index recall.** At M = 1,000 online C1 was 0.70-0.85. At 50 % encoding duty the
    threshold offset sits near 7-7.7 mV, against about 3.7 mV settled.
  - **The online timeline changes the feedback write:**

    | measure, items 751-1,000 | P2-E3's protocol | online |
    |---|---|---|
    | \|R\| | 28.6 | 45 |
    | Jaccard(R, A) | 0.73 | 0.49 |

  - **The online-written store** fails content even after a settle (joint 0.81 / 0.89).
  - **So P2-E3's content PASS depended on its back-to-back protocol** (P2-E3 addendum 2).

## Hypothesis

The P2-E3 system keeps memory and content recall for recent and old items while it learns one
item every 500 ms with no settle and no `quiet()`. Every parameter is frozen. The recall is
caused by the cue.

When learning pauses and the input duty is held, a cue repeated 100 times over 50 s keeps
recall no worse than a matched control. Recall recovers 10.5-14.5 s after the last repetition.

**Labelled limitations.** The experimenter still supplies:
- **When to write** (the write oracle). Plateaus and feedback writes happen only inside
  encodings.
- **The key.** Plateaus are random and content-blind.
- **The value.** Eligible lines are copied one to one onto `rec`.
- **The operating point.**
  - J, J_fb, g and accommodation tau are frozen.
  - The operating point depends on input duty.
  - The responder write's specificity depends on the operating point at write time.
- **The input statistics.** Items are independent random patterns. Correlated items are P2-E5.

The habituation statistics (O4, O5) are measured on **copies with learning paused**. Sham
encodings hold the input duty, the load and the memory layer's `vbar`. They do not reproduce the
post-write memory burst, so `rec` on the copies sits about 1.5-3 mV nearer rest at slot onset
(verification SHAM-1; no measurable effect on "both" in an n = 60 exploratory check).

P2-E4 removes only two experimenter supplies from the gated numbers: the rest before testing,
and the frozen-copy test regime.

## No new mechanism; new protocol values, fixed by argument before any gated run

Model parameters are frozen from P2-E2 and P2-E3:
- J = 1.525 mV, accommodation tau 10 s;
- J_fb = 2.80 mV, g = 0.3;
- f_q, a, rates, encoding 200 ms, continuation 50 ms.

The new protocol values:

| value | setting |
|---|---|
| interval I | 250 ms: a 50 ms pre-gap, a 100 ms probe slot, a 100 ms post-gap |
| gated blocks | 240 steps ending at M = 500 and 1,000 |
| never-probed pool | items 1-200, two cohorts of 100 |
| block mix | below |
| habituation | 50 items, 100 repetitions, a 20-step pause, 5 recovery and 5 collateral cues |
| twins and arms | below |

**Why I = 250 ms.** It is the shortest interval that holds one probe with:
- a pre-gap of 2.5 membrane time constants after the continuation;
- the 75 ms readout window inside the 100 ms cue;
- a 100 ms post-gap before the next encoding.

The red-team agreed to keep it. Moving it after exploration would be outcome-informed.
I = 2,000 ms is a reported duty arm, predeclared as **unable to satisfy the online clause**.

## Definitions

- **Ages.** Item j has age k - j at step k. Item k is age 0 in its own step's slot.
- **Unreserved.** An item is unreserved when it is in neither cohort. The rule applies at every
  step.
- **Slot ticks.** Every score window starts at slot tick k = 0, the slot's first tick, when its
  rates are set (blank slots included).
- **Memory responders R50:** cells with >= 1 spike at k = 0..49.
- **Regenerated lines:** `rec` lines with >= 1 spike at k = 0..74 (for P2-E3's 50 ms variant,
  k = 0..49).
- **Recall, spurious and ignition** are P2-E1's per-cue measures, applied to one slot:
  - recall = |A ∩ R50| / |A|, and 0 when A is empty;
  - spurious = |R50 \ A|, which must be < 0.5 |A|;
  - ignition = |R50|, which must be < 0.5 mean|A|. Here mean|A| is the mean plateau-set size
    over items 1..M of the gated load: one value per block.
- **Content joint:** >= 40 of the 50 missing lines regenerated, and < 10 intrusions (lines
  outside the item's 100).
- **"Both":** recall >= 0.8 and the content joint.
- **A novel cue** is the 50-line half cue of a fresh 100-line item, drawn with its mask. The
  item is never stored and never reused.

**Streams.** Every generator is `stream(seed, sid, *ints)`, and ids 12-18 are P2-E4's. The
encoding uses P2-E1's streams and the continuation uses P2-E3's stream 9.

| key | use |
|---|---|
| (seed, 12, k) | background in step k's pre-gap and post-gap |
| (seed, 13, k) | step k's slot input |
| (seed, 14, k) | step k's rolling kind, target and mask |
| (seed, 15, 0) | the cohorts |
| (seed, 15, M, attempt) | the block builder: order, targets, masks, blank designations, pseudo-targets |
| (seed, 16, M, 0) | habituation item selection, collateral tie-breaks, the 89 control items, masks |
| (seed, 16, M, x + 1, s) | every input draw of copy step s for item x, shared by both copies; the sham pattern is its first draw |
| (seed, 17, k) | step k's novel item on the main line |
| (seed, 18, arm, ...) | the twins and arms: novel-duty twin 1; twin B 2; writes during probes 3; out-of-distribution 4; duty arm 5 |

The forward store stays bit-identical to P2-E1's. BTSP reads only the encoding's input spikes,
which come from `_learn_in` (a fixed draw of m uniforms per tick), and nothing else consumes
that stream.

## Protocol: the main timeline, one per seed

**Learning step k:**
1. **Encoding** (200 ms), exactly as in P2-E1.
2. **Continuation** (50 ms) and the feedback write, exactly as in P2-E3.
3. **Interval:** 50 ms background, the 100 ms slot, 100 ms background.

There is no `quiet()` and no settle.

**`rec`** is a live engine population. It starts at rest at tick 0, is never reset, runs through
encodings, and has no outputs. The live feedback projection is reloaded right after each write.
**Gated numbers come from this continuous simulation.**

**Cohorts.** Items 1-200 are split into cohort 500 and cohort 1,000, 100 each (stream (seed, 15,
0)). On the main line:
- **Cohort 1,000:** cued only in block 1,000's cohort slots, and in oldest-probed rolling slots
  after step 1,000.
- **Cohort 500:** cued in block 500's cohort slots, in oldest-probed rolling slots after step
  500, and as 15 of block 1,000's uniform cues (the probed-history comparison).
- **Both cohorts:** never a blank target, never a full cue, never a habituation item, collateral
  item or control item.
- **Scope.** These rules bind the main line. Copies cannot feed history back (validity 6), so
  settled twins may run P2-E3's own test sets.

**Rolling slots** (every step outside a gated block). The kind is drawn i.i.d. per step from
stream (seed, 14, k):

| kind | share | target |
|---|---|---|
| recent | 20 % | an unreserved item of age 0-20 |
| uniform | 20 % | an unreserved item of age >= 21 |
| oldest-probed | 10 % | a cohort item whose block has passed |
| novel | 25 % | |
| full | 10 % | an unreserved item of any age |
| blank | 15 % | an unreserved item of age 0-20 |

- Targets are drawn uniformly from the kind's eligible set. Repeats across rolling steps are
  allowed.
- A kind whose eligible set is empty becomes a novel cue. So steps 1-200 hold only novel cues,
  and uniform slots become novel until step 221.

**Gated blocks** (M in {500, 1,000}; steps M-239 .. M, loads 261-500 and 761-1,000). Each block
holds exactly:

| kind | count | detail |
|---|---|---|
| recent | 50 | |
| uniform | 50 | block 1,000: 15 cohort-500 items plus 35 unreserved |
| cohort | 100 | this load's cohort |
| novel | 20 | |
| blank | 20 | 5 at age 0, in odd sub-blocks; 15 at ages 1-20 |

- **Order.** The block is 10 sub-blocks of 24 steps. Each holds 5 recent, 5 uniform, 10 cohort,
  2 novel and 2 blank, in random order. Block 1,000's 15 cohort-500 uniform cues are spread
  2, 2, 2, 2, 2, 1, 1, 1, 1, 1 over the sub-blocks.
- **The sampler.** The builder fills slots in step order. Each targeted slot draws uniformly
  from its kind's eligible set, minus every item already targeted in the block, cued or blank.

  | kind | eligible set |
  |---|---|
  | recent and blank | unreserved items of age 0-20 |
  | uniform | unreserved items of age >= 21 |
  | cohort | this load's cohort |

- **Realised ages.** Recent ages are therefore skewed toward 0. The realised age distribution is
  reported.
- **Masks.** Half-cue masks, and the designated missing halves of blank targets, are drawn with
  each slot (stream 15).
- **Pseudo-targets.** Each novel slot also gets a pseudo-target by the blank-target rule. It is
  never cued; it only serves the leak baseline.
- **Infeasible schedules.** An attempt fails only if an eligible set is empty, and is then
  redrawn as (seed, 15, M, attempt + 1). The unit test builds the schedule for seeds 90+ only.
- **Half cues.** O1 and O2 pool all 200 half cues (50 recent, 50 uniform, 100 cohort).

## Habituation arm (M = 500 and 1,000; on copies)

**Selection** (stream (seed, 16, M, 0)):
- **The candidate set C:** unreserved stored items of age >= 21.
- **The 50 items** are drawn from C.
- **Collateral.** Each item x gets a collateral item y in C, outside the 50, that maximises
  |A(x) ∩ A(y)| in cells. Ties are broken uniformly by the same stream. The median maximum
  overlap is about 2 of 20 cells, so the collateral tests little spread to overlapping
  assemblies. Overlap and age are reported.
- **Control items.** Each item x gets 89 other items, drawn from C outside the 50 and excluding
  x's collateral.
- **Masks.** One mask per item, and one per collateral, from the same stream. Every cue of x and
  of y uses its own mask on both copies.

**The copies.** Each item x gets a **repeated** and a **control** deep copy of the main line,
taken right after step M, with `rec` live. A copy step s has the main line's structure:
1. a **sham encoding** of 200 ms: a fresh random 100-line pattern at encoding rates (the first
   draw of (seed, 16, M, x + 1, s));
2. 50 ms of the same pattern;
3. a 50 ms pre-gap;
4. the 100 ms slot;
5. a 100 ms post-gap.

There are no plateaus, no BTSP update and no feedback write. All input of step s comes from
(seed, 16, M, x + 1, s) on both copies.

| copy steps | repeated copy's slot | control copy's slot |
|---|---|---|
| 1-100 | x's half cue | x at step 1 and steps 91-100; the 89 control items at steps 2-90 |
| 101-120 | blank | blank |
| 121-130 | x, y, x, y, ... (x at the odd steps) | the same |

**Per-item statistics:**

| statistic | definition |
|---|---|
| scored | copy step 1 passes "both" |
| L_rep | "both" passes in the repeated copy's steps 91-100 |
| L_ctl | "both" passes in the control copy's steps 91-100 |
| eligible | scored, and L_ctl >= 8 |
| habituated | eligible, and L_rep <= L_ctl - 3 |
| recovery | on each copy, >= 3 of x's 5 recovery cues pass "both" |
| collateral | on each copy, >= 3 of y's 5 cues pass "both" |

O5 is taken over all 50 items.

## Twins and references (reported)

1. **Settled twin A**, from the snapshot at step M, with the carried live `rec`:
   - P2-E3's `run_phase(e, M)`: `settle_drift(M, 1)`, then P2-E2's `evaluate` on P2-E3's test
     set;
   - the carried `rec`'s spikes are logged;
   - P2-E3's replay of the raster with the online store gives the P2-E3-comparable numbers, and
     is compared spike for spike with the carried `rec`;
   - a mismatch is reported as a count of differing spikes plus its effect on the joint. It leaves
     twin A valid.
2. **Settled twin B.** A deep copy of twin A right after its settle (the same `settle_drift(M,
   1)`):
   - a 200 ms lead-in, then the block's 200 half cues in block order, with the same masks;
   - 100 ms on, 200 ms off, input from (seed, 18, 2, M);
   - memory scored as in P2-E1, and content from the carried live `rec` at k = 0..74;
   - this gives the paired per-cue comparison of online against settled (McNemar).
3. **Novel-duty twin.** A second timeline from step 1, identical except:
   - every cue slot holds a novel cue of the same form: half cues are 50-line novel half cues,
     and full cues novel 100-line patterns, from (seed, 18, 1, k);
   - blank slots stay blank.

   It has the same input duty with no retrieval of stored items. At M = 500 and 1,000 it records
   its stores and twin A's readout.
4. **P2-E3-protocol reference line.** `E3.learn` on the same seed, to 1,000, with P2-E3's
   `run_phase` and `readout` at 500 and 1,000. Its feedback store serves the store swaps.

## Kill test (gated seeds 16-20, all fresh; each seed runs once)

Each criterion must hold on every gated seed at M = 500 and at M = 1,000.

| criterion | owner's term | what must hold |
|---|---|---|
| **O1 memory, online** | continuous recall; interference resistance | Of the 200 half cues: recall >= 0.8 for >= 90 % (C1) and spurious < 0.5\|A\| for >= 90 % (C2). Of the 20 novel cues: ignition < 0.5 mean\|A\| for >= 90 % (C3) |
| **O2 content, online** | continuous recall; interference resistance | The content joint for >= 90 % of the 200 half cues; < 10 regenerated lines for >= 90 % of the 20 novel cues (D3) |
| **O3 retention** (never-probed cohort) | oldest-item retention; Stage 1's "after 60 s of ongoing activity" | Of the 100 cohort cues: recall >= 0.8 for >= 90 %, and the content joint for >= 90 % |
| **O4 habituation** (owner's ruling 2, read as "no more habituation than without repetition"; the owner may overrule this reading) | repeated-cue habituation | >= 25 of the 50 items eligible, and <= 10 % of eligible items habituated |
| **O5 recovery** | recovery | Recovery: >= 90 % of items pass on the repeated copy, among the >= 25 items that pass on the control copy. Collateral: >= 90 % pass on the repeated copy, among the >= 25 that pass on the control copy |

- **When a minimum count is not met,** the criterion fails as not estimable. It is never skipped.
- **Interference.** It is carried by the uniform and cohort cues of old items while learning
  continues. The forward store is bit-identical to P2-E1 whatever the regime, so online
  interference can act only through `vbar` and the responder write. Per-kind rates are reported
  in the verdict text, not gated separately.
- **An O3 memory failure** means Stage 1's clause "holds ... after 60 s of ongoing activity" is
  not met online, for the P2-E3 system.
- **The P2-E3 addendum's item 8** (a gated control that could pass if the claim were false). It
  is met for O4 and O5 by the paired control copies, whose outcome is not fixed by construction.
  For the recall claim itself, no artefact control can fail in this architecture: validity check
  9 demonstrates this (ledger M4, FID-7).

## Validity (checked first; a gated failure makes the seed INVALID)

1. The forward store's sha256 equals P2-E1 learning at M = 500 and 1,000.
2. The eligible fraction is >= 0.95, and mean |A| is 18.5-21.5.
3. The feedback store equals the union of R(x) x E(x) over the items learned so far.
4. **No store changes in any probe slot.** An O(1) identity check runs on the stores' key arrays
   at every slot, with full digests at block ends.
5. **The live projection is current.** At every gated slot, the projection's load version equals
   the feedback store's write version, and the inhibition weight equals g x J_fb.
6. **The main line is untouched by every copy.** Digests of the stores, `vbar`, mem v, t_last,
   the delay rings, `rec` state, net.t and every generator state are taken before and after
   each copy and each habituation arm.
7. **The realised probe log passes an audit:**
   - the cohort rules hold;
   - counts are exact;
   - no item is targeted twice within a block.
8. **Repetition 1 is identical.** The memory and `rec` spike rasters of copy step 1 are equal on
   both copies of every item.
9. **The blank-slot leak check** (no artefact control can fail here; this check shows it).
   - **Leak statistics.** L_A is the mean, over the 20 blank slots, of |A_t ∩ R50| / |A_t|. L_C
     is the mean of |miss_t ∩ rec75| / 50, where miss_t is the target's designated missing half.
   - **Baselines** B_A and B_C are the same means over the 20 novel slots' pseudo-targets.
   - **Pass if all three hold:**
     1. <= 1 of 20 blank targets has recall >= 0.8;
     2. L_A <= B_A + 0.05;
     3. L_C <= B_C + 0.05.
   - **The positive control (memory) must also hold.** Over the 20 blank-slot steps, the mean
     fraction of that step's age-0 item's assembly with >= 1 spike in its own 50 ms continuation
     is >= 0.5.
   - **The content part has no positive control.** An item's feedback is written after its
     continuation. Its sensitivity is shown by the recent cued slots, reported beside it.

A validity failure in a reported arm invalidates only that arm.

## Verdict (a vector plus labels)

- **The vector.** Pass, fail, or fail (not estimable), for each part at each load:
  - O1: C1, C2, C3;
  - O2: joint, D3;
  - O3: memory, content;
  - O4;
  - O5: recovery, collateral.

  Per-seed values are recorded.
- **Labels:**

  | label | when |
  |---|---|
  | INVALID | a gated validity check fails on any seed |
  | PASS | every criterion holds |
  | ONLINE INDEX FAIL | an O1 or O3 memory part fails |
  | ONLINE CONTENT FAIL | an O2 or O3 content part fails |
  | HABITUATION FAIL | O4 fails with >= 25 items eligible |
  | HABITUATION NOT ESTIMABLE | O4 fails only because fewer than 25 items are eligible |
  | RECOVERY FAIL | O5 fails on a seed and load where `power.p_paired_majority` (cues = 5, need = 3) gives a zero-effect pass probability >= 0.8 at the control copies' observed per-cue "both" rate |
  | RECOVERY NOT ESTIMABLE | O5 fails only on seeds and loads where that probability is below 0.8 |

  Unless the verdict is INVALID or PASS, every applicable failure label is joined; none hides
  another. Not-estimable labels still fail the gate.
- **Run once.** Gated seeds run once. A re-run needs the owner's ruling and keeps the first
  records.

## Power (computed before freezing; `plant2/power.py`; record kind `power_reference`)

**O1-O3.** Exact binomials, with a logit-normal seed effect (SD 0.18, the recorded excess
spread), over all five seeds and both loads. The reference rates are the recorded settled rates
of the gated seeds.

- **Memory measures** (C1, C2, C3, oldest-item recall) are pooled over P2-E2 seeds 6-10 and
  P2-E3 seeds 11-15: the same memory network, tested settled.
- **Content measures** (joint, D3, D4) come from P2-E3 seeds 11-15 alone.
- **Recorded values of 1.000** enter as 0.999.

| measure | M = 500 | M = 1,000 |
|---|---|---|
| C1 | 0.969 | 0.9435 |
| C2 | 0.999 | 0.986 |
| C3 | 0.999 | 0.9955 |
| joint | 0.994 | 0.975 |
| D3 | 0.999 | 0.998 |
| oldest recall | 0.969 | 0.953 |
| D4 | 0.998 | 0.972 |

| rates | P(O1-O3 pass, all seeds and loads) |
|---|---|
| pooled memory rates | **0.855** |
| P2-E3-only memory rates (C1 0.972 / 0.938) | 0.788 |
| the earlier draft's counts | 0.62 |

Within a block, each cue is a distinct item scored once, so binomial variance is an upper bound.

**O4 and O5.**
- **The item model.** Beta per-item reliability with intraclass correlation 0.09 (red-team
  estimate), 50 items, five seeds.
- **The "both" rate.** C1 x joint, which is conservative: 0.963 at M = 500 and 0.920 at M = 1,000.
- **Zero-habituation pass probabilities:**

  | O4 | O5 recovery (majority of 5) | O5 collateral (majority of 5) |
  |---|---|---|
  | 0.981 | 0.996 | 0.997 |

- **With modest habituation** (late per-cue rate x 0.85), O4 fails with certainty, because about
  22 % of eligible items habituate.
- **The earlier draft's unpaired rule** passed with only 0.41 at one load and 0.17 at both
  (rate 0.93, no habituation).

**The full rule, zero online cost:**

| rates | P(PASS) |
|---|---|
| pooled memory rates | 0.833-0.853 |
| P2-E3-only memory rates | 0.768-0.786 |

The range runs between "both" rates of 0.963/0.920 and 0.968/0.944. The P2-E3-only figure is
just below the 0.8 target. That is stated, not hidden: blocks cannot grow past 240 steps without
widening the load spread (red-team M7).

**After implementation, before any gated seed:**
- **Exploration.** The real driver runs on seeds 42-43.
- **The Monte Carlo is re-run.** It uses exact binomials with propagated rate uncertainty for
  O1-O3, and a bootstrap of whole items from the exploration copies for O4-O5.
- **What is committed:**
  - P(PASS) as an interval;
  - per-criterion and per-label probabilities;
  - the per-cue rate that gives P(PASS) >= 0.8, as one common logit shift of all rates;
  - the plant2 tree hash and the contract digest.
- **The guard.** A `--gated` run refuses to start unless:
  - that commit is an ancestor of HEAD;
  - the tree is clean;
  - the tree hash and contract digest match.

## Reported, not gated (each with a prediction)

| arm | reported | prediction |
|---|---|---|
| online against settled (twin B) | per kind and load: online minus settled pass rates for memory and content; McNemar | memory: online lower by 0.15-0.25 at M = 1,000 and 0.03-0.08 at M = 500. Content: about equal, or online higher |
| write against readout cost (store swaps on twin A's raster) | the joint through the online store, the reference store and the plateau-set store | 0.80-0.90; 0.97-1.0; 0.97-1.0 (M = 1,000) |
| responder write | \|R\|, R - A, Jaccard(R, A) and the continuation offset by age bin: main line, novel-duty twin, reference line, duty arm | at M = 1,000: main \|R\| about 45 against about 28.6 for the reference; Jaccard about 0.5 against 0.73 |
| probe history | novel-duty twin against main: stores, \|R\|, settled readout | small differences, sign uncertain |
| probed against never-probed | block 1,000: the 15 cohort-500 uniform cues against the 100 cohort-1,000 cues (same block, similar ages) | about zero difference under the write oracle |
| operating point | `vbar` offset at probe time per block; `rec` v at slot onset; block offset minus twin A's settled offset | about 7-7.7 mV online against about 3.7 settled at M = 1,000; about 2.5-3.5 against about 1.9 at M = 500; `rec` 2-4 mV below rest |
| retention against age | rolling probes; the realised recent-age distribution | recall falls with age |
| causality | cued minus blank by age, age 0 separately; L_A, L_C and baselines | blank about 0; age-0 cued recall about 0.88-1.0 |
| habituation detail | per-repetition recall and "both"; the L_rep - L_ctl distribution and McNemar on "L >= 8"; the habituated fraction; recovery among habituated items; global and assembly `vbar` and `rec` onset v on every copy against the main line; collateral overlap and age | habituation present at M = 500; at M = 1,000 eligibility likely under 25 |
| M = 250 | rolling probes in steps 221-250 | C1 about 0.92-1.0, joint about 1.0 |
| duty arm (I = 2,000 ms; a 1,850 ms post-gap; blocks built by the same rules and streams) | online and twin A, M <= 1,000; predeclared unable to satisfy the online clause | online memory passes (C1 about 0.96-0.98); store collapses (settled joint about 0.17) |
| beyond capacity (stress test) | the main line continues to M = 3,000. Stress blocks end at 1,500, 2,000 and 3,000, each with 100 recent cues at ages 0-100, 60 uniform, 40 novel, 20 blank and 20 full | blackout: joint < 0.3 by M = 1,500 and about 0 at 2,000 |
| writes during probe slots (store/recall oracle partly removed; stress test) | a copy from the step-1,000 snapshot runs steps 1,001-1,200 on the main line's rolling schedule (items keep `_pat`, `_plat` and `_coin`). In addition, every non-blank slot draws plateaus at f_q per cell from (seed, 18, 3, k), applies BTSP with coins from the same stream to lines with >= 3 spikes in the 100 ms slot, and writes feedback from memory cells responding in the slot's last 50 ms. Still scheduled: slot boundaries, the eligibility window and the write time; background never writes. After step 1,200 each written probe is re-presented once, in write order, in the online rhythm with sham encodings; it counts as "stored" if recall of its new assembly reaches >= 0.8. Compared with the main line at matched items (M = 1,200) and matched plateau episodes (about 1,370). BTSP depressions of existing items are reported | about 170 probes written, nearly all "stored" (by arithmetic); older-item recall falls as at matched load |
| out-of-distribution probes (a copy at 1,000 with the sham rhythm; stream 18, 4) | 40 lures (novel items sharing 50 lines with a stored unreserved item), 40 cues of 30 % of an item's lines, 40 half cues with 10 of 50 lines swapped for noise | lures recalled as the stored item; 30 % cues: C1 about 0.2-0.5; noisy cues below half cues |
| efficiency | bits per synapse; inherited window widths (J ±5 %, J_fb ±29 %) | about 0.2 bits per synapse |

**Cut on review** (ledger FID-9):
- the a = 50 and 200 transfer timelines go to the capacity contract;
- re-exposure goes to the familiarity and representation contract.

## Order of runs on one seed

1. Main line steps 1-500. Keep snapshot S500 (a deep copy) and run the M = 500 habituation arm
   from it.
2. Main line steps 501-1,000. Keep S1000, run the M = 1,000 habituation arm from it, and run the
   P2-E1 forward-store checks (plain E1 to 500 and 1,000).
3. Append `kill_test_seed`, the gated record. Validity check 6 is gated over steps 1-2.
4. Run the reported arms, then append `reported_arms`:
   - twins A and B from S500 and S1000;
   - writes during probes and out-of-distribution probes from S1000;
   - main line steps 1,001-3,000;
   - the reference line, the novel-duty twin and the duty arm, each from step 1.

**Cost:** about 35 min gated and 35-50 min reported per seed. Snapshots take about 0.1-0.2 GB.

## Predictions before implementation

These are the red-team's exploratory numbers. Predictions from the real driver will be
**appended** below them, never replacing them.

| criterion | prediction |
|---|---|
| O1 | **FAIL at M = 1,000** (C1 about 0.70-0.85); borderline at 500 (0.89-0.96); C2 and C3 hold |
| O2 | holds at 500; borderline at 1,000 (online joint 0.935-1.0) |
| O3 | memory **FAIL at M = 1,000** (cohort ages 561-999; proxy for ages >= 281: 0.70-0.80); borderline at 500; content about 0.93 |
| O4 | at M = 1,000 likely not estimable (eligible < 25 at a per-cue "both" rate of about 0.77); at 500 uncertain |
| O5 | at M = 1,000 fails from sampling (zero-effect pass probability about 0.003 at 0.77), so RECOVERY NOT ESTIMABLE; likely holds at 500 |
| validity | holds |

**Expected labels:** ONLINE INDEX FAIL, with HABITUATION NOT ESTIMABLE and RECOVERY NOT ESTIMABLE
at M = 1,000, and possibly ONLINE CONTENT FAIL. P(PASS) < 0.05.

## Decision (predeclared)

- **On PASS.** Stage 1's online clause is met, for the P2-E3 system on independent random items,
  within the demonstrated capacity.
  - Stage 1 still needs P2-E5 (structured input) and capacity growth.
  - No claim of lifelong memory is made before bounded capacity and graceful forgetting are
    shown.
  - Any later change to the write or the operating point must re-pass P2-E4's gates on fresh
    seeds. The driver is built to make that cheap.
- **On any FAIL.**
  - It is recorded.
  - The claim that accommodation provides a usable online operating point is withdrawn for the
    failing loads.
  - Work proceeds to P2-E5, as the owner ordered.
  - Where a separately contracted operating-point mechanism sits relative to the contamination
    fix is the owner's decision. Nothing is retuned.
- **On INVALID.** It is recorded and reported to the owner. A re-run needs the owner's ruling.
- **The duty arm** never satisfies the online clause.

## Files

| file | contents |
|---|---|
| `plant2/experiments/p2_e4_online.py` | the driver (a subclass of E3; E3 is not edited) |
| `plant2/power.py` | power functions |
| `plant2/tests/test_p2_e4.py` | tests |
| `bench/results/plant2.jsonl` | records (append-only): `power_reference`, `exploration_seed`, `power_predictions`, `kill_test_seed`, `kill_test_verdict`, `reported_arms` |

**Seeds:** exploration 42-43; gated 16-20.

## Predictions from the real driver (exploration seeds 42-43)

Appended 2026-10-11, after implementation and before any gated seed. The sections above are
unchanged.

**Source.** `power_predictions` record, timestamp 2026-10-11T00:37:57Z, made by
`p2_e4_online predict`:

| field | value |
|---|---|
| contract digest | f8f8838bce35d38c |
| plant2 tree | 9152f1e4 |
| commit | 37b1c84 |
| posterior draws | 300 |
| simulations | 1,500 |
| exploration records | from commit 737e8b1 |
| skipped records | none |

**Observed exploration counts, pooled over seeds 42 and 43** (passing cues of cues scored):

| part | M = 500 | M = 1,000 |
|---|---|---|
| C1 (index recall of half cues) | 362 / 400 (0.905) | 296 / 400 (0.740) |
| C2 (spurious) | 400 / 400 | 400 / 400 |
| C3 (novel ignition) | 40 / 40 | 40 / 40 |
| content joint | 397 / 400 (0.993) | 386 / 400 (0.965) |
| D3 (novel regeneration) | 40 / 40 | 40 / 40 |
| O3 memory (never-probed cohort) | 177 / 200 (0.885) | 148 / 200 (0.740) |
| O3 content | 200 / 200 | 191 / 200 (0.955) |
| control-copy "both" rate (habituation arm) | 0.799 | 0.586 |

**Probability that each criterion holds on all five gated seeds.** These are full-rule simulations.
Each cue's rate is drawn from its posterior, the seed effect has an SD of 0.18 on the logit scale,
and O4-O5 come from a bootstrap of whole habituation items.

| criterion | M = 500 | M = 1,000 |
|---|---|---|
| O1 C1 | 0.155 | 0.000 |
| O1 C2 | 1.000 | 1.000 |
| O1 C3 | 0.868 | 0.882 |
| O2 joint | 1.000 | 0.985 |
| O2 D3 | 0.878 | 0.873 |
| O3 memory | 0.044 | 0.000 |
| O3 content | 1.000 | 0.831 |
| O4 | 0.000 | 0.000 |
| O5 recovery | 0.207 | 0.344 |
| O5 collateral | 1.000 | 0.991 |

**P(PASS)** is 0. The median over posterior draws is 0, with a 5-95 % interval of [0, 0], and none
of the 1,500 joint simulations passed. The probability that O1 index recall passes alone is
4 × 10^-4 at M = 500 and below 10^-38 at M = 1,000.

**Expected labels** (fraction of joint simulations carrying each):

| label | probability |
|---|---|
| ONLINE INDEX FAIL | 1.00 |
| HABITUATION FAIL | 1.00 |
| RECOVERY NOT ESTIMABLE | 0.57 |
| ONLINE CONTENT FAIL | 0.37 |
| RECOVERY FAIL | 0.36 |

RECOVERY NOT ESTIMABLE and RECOVERY FAIL are exclusive in the labelling. Together, recovery fails in
about 0.93 of simulations. That mostly comes from requiring >= 90 % on all ten seed-loads at a
per-seed pass probability of 0.74-0.80. It is not evidence of a recovery deficit: recovery passed
on both exploration seeds.

**Distance from the bar.** P(PASS) reaches 0.8 only if every per-cue rate is moved together by
+1.90 on the logit scale. That would put C1 at 0.98 at M = 500 and 0.95 at M = 1,000, and the
control "both" rate at 0.96 and 0.90. This is not a near-miss.

**How this differs from the predictions before implementation.**
- **Habituation.** Those predicted HABITUATION NOT ESTIMABLE at M = 1,000. The driver now predicts
  HABITUATION FAIL, carried by M = 500: 22 of 31 eligible items habituated on seed 42, and 10 of
  22 on seed 43, against a bar of 10 %.
- **O3 memory now also fails at M = 500.** Its probability is 0.044, against "borderline" before.
- **The rest stands:** ONLINE INDEX FAIL, possible ONLINE CONTENT FAIL, recovery not estimable at
  M = 1,000.

**Consequence under the Decision above.** A FAIL is expected. The gated seeds still run, exactly as
frozen, because the contract requires the independent gated evaluation. Nothing is retuned.

## Result (appended 2026-10-11, after the verdict and the post-verdict diagnosis; nothing above is edited)

**Verdict: ONLINE INDEX FAIL + HABITUATION FAIL + RECOVERY FAIL.** The kill_test_verdict record is
in commit e756252.

**Validity and provenance.**
- All five gated seeds (16-20) are valid. Each ran once, on plant2 tree 9152f1e4 under contract
  digest f8f8838b.
- The real-driver predictions were committed (124ecb2, 00:38:40) before the first run-once marker
  (00:38:56).
- The guard checks that plant2/ is clean, not the whole working tree. Seed 19's record shows
  dirty=true outside plant2/ (a results-file append).
- Two independent reviewers re-derived the verdict vector and labels from the per-slot logs, with
  every sha256 matching, and got exactly the recorded result (`review/plant2/P2-E4/results-*.md`).
- **Validity 5 holds by construction, not by test.** Its `proj_current` and `inh_ok` checks cannot
  fail as written. The evidence that the live projection was current is twin A's replay: zero
  differing spikes at both loads on all five seeds, over 463k-665k spikes.

**Per seed and load** (online rates; O4 counts eligible and habituated items; O5 counts
control-copy passers and recovered items, with p0 the zero-effect pass probability):

| seed | M | C1 | C2 | C3 | joint | D3 | O3 memory | O3 content | O4 eligible / habituated (McNemar b/c) | O5 recovery passers / recovered (p0) | O5 collateral |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 16 | 500 | 0.89 | 1.0 | 1.0 | 0.985 | 1.0 | 0.88 | 0.97 | 21 / 12 (16/0) | 48 / 47 (0.75) | pass |
| 17 | 500 | 0.87 | 1.0 | 1.0 | 0.975 | 1.0 | 0.83 | 0.98 | 28 / 14 (23/0) | 45 / 42 (0.62) | pass |
| 18 | 500 | 0.93 | 1.0 | 1.0 | 0.995 | 1.0 | 0.93 | 1.0 | 33 / 21 (25/0) | **47 / 42 (0.83)** | pass |
| 19 | 500 | 0.91 | 1.0 | 1.0 | 0.98 | 1.0 | 0.91 | 0.99 | 27 / 14 (18/0) | 45 / 44 (0.69) | pass |
| 20 | 500 | 0.92 | 1.0 | 1.0 | 0.975 | 1.0 | 0.94 | 0.98 | 20 / 10 (12/0) | 47 / 41 (0.64) | pass |
| 16 | 1,000 | 0.685 | 1.0 | 1.0 | 0.95 | 1.0 | 0.67 | 0.92 | 13 / 10 | 34 / 26 (0.016) | pass |
| 17 | 1,000 | 0.71 | 1.0 | 1.0 | 0.96 | 1.0 | 0.75 | 0.97 | 6 / 5 | 33 / 25 (0.010) | pass |
| 18 | 1,000 | 0.68 | 1.0 | 1.0 | 0.965 | 1.0 | 0.63 | 0.96 | 12 / 8 | 35 / 27 (0.014) | pass |
| 19 | 1,000 | 0.74 | 1.0 | 1.0 | 0.96 | 1.0 | 0.73 | 0.94 | 9 / 5 | 36 / 29 (0.025) | pass |
| 20 | 1,000 | 0.68 | 1.0 | 1.0 | 0.93 | 1.0 | 0.61 | 0.90 | 6 / 4 | 37 / 27 (0.024) | pass |

**The vector in the contract's three states:**
- O1 C1 and O3 memory fail at both loads.
- O2 and O3 content pass on every seed and load.
- O4 fails, not estimable where fewer than 25 items were eligible: every seed at M = 1,000, and
  seeds 16 and 20 at M = 500.
- O5 recovery fails at M = 1,000 on every seed, though not estimable by the power rule there (p0
  0.010-0.025).
- O5 collateral passes everywhere.
- The NOT ESTIMABLE conditions held at M = 1,000 for both habituation and recovery, but are
  absorbed into the FAIL labels by the labelling rule.

**Per-kind index recall (C1) at M = 1,000:**

| kind | C1 |
|---|---|
| recent (age 0-20) | 0.72-0.82 |
| uniform | 0.62-0.72 |
| never-probed cohort | 0.61-0.75 |

The online index failure reaches the newest items. It is not forgetting of old items, nor
interference alone.

**Disclosures on the labels:**
- **RECOVERY FAIL rests on one seed and load.** On seed 18 at M = 500, 42 of 47 control passers
  recovered and 43 were needed; one item short.
  - Its zero-effect pass probability is 0.83, against the 0.8 bar (exact value 0.831). At 203 of
    250 control passes instead of 205, it would have been 0.794, which reads RECOVERY NOT ESTIMABLE.
  - The driver reads the power rule per seed and load. Read over all seeds and loads, the label
    would have been RECOVERY NOT ESTIMABLE.
  - The label follows the frozen rule and stands. A post-hoc paired check by a reviewer suggests
    recovery really is incomplete (next bullet), so it is not sampling noise.
- **Recovery of the repeated item's own cues is incomplete** (post hoc, a reviewer's computation;
  not a gate):
  - Pooled over the gated seeds, items where the control copy passes and the repeated copy fails
    outnumber the reverse 57 to 2. At M = 1,000 the per-seed counts are 7-10 against 0-1.
  - Collateral cues are spared: 4 against 1.
  - Recovery among habituated items is 0.75-1.0.
  - So the recovery hypothesis is not supported.
- **HABITUATION FAIL.** On the three seeds where it was estimable at M = 500 (17, 18 and 19), 50-64 %
  of eligible items habituated: 14 of 28, 21 of 33, 14 of 27. The predeclared McNemar on
  "L >= 8" gives 23/0, 25/0 and 18/0.
  - O4 had little power at the realised control rates (0.81-0.85, not the 0.963 assumed). A
    reviewer's null model gives a no-effect pass chance of 0.45-0.79 per seed and load.
  - That does not weaken a failure of this size.
  - Habituation is measured on copies with sham encodings (verification SHAM-1).
- **Content passes on all five seeds, but at M = 1,000 the pass depends on the online state.**
  - The online-written store is contaminated: twin A, on the same raster, reads 0.82-0.905, against
    0.96-1.0 for the P2-E3-protocol store and 0.985-1.0 for the plateau-set store.
  - The same cues read worse after the settle (twin B content: 0.835-0.915 settled, against
    0.93-0.965 online).
  - On seed 20 at M = 1,000, O3 content sits exactly at the bar (90/100). One more failure would
    have added ONLINE CONTENT FAIL.

**Reported arms** (gated seeds 16-20, all valid):

| arm | M = 500 | M = 1,000 |
|---|---|---|
| twin A, online-written store | 0.99-1.0 | 0.82-0.905 |
| twin A, P2-E3-protocol store (same raster) | 0.99-1.0 | 0.96-1.0 |
| twin A, plateau-set store (same raster) | 0.99-1.0 | 0.985-1.0 |
| twin B, index online / settled | 0.87-0.93 / 0.965-0.98 | 0.68-0.74 / 0.92-0.975 |
| twin B, content online / settled | 0.975-0.995 / 0.99-1.0 | 0.93-0.965 / 0.835-0.915 |
| duty arm (I = 2,000 ms), online C1 / joint | 0.95-0.99 / 0.99-1.0 | 0.945-0.985 / 0.485-0.565 |
| duty arm, twin A (settled store) | 0.99-0.995 | 0.175-0.245 |
| novel-duty twin, twin A | - | 0.815-0.91 (the main line's 0.82-0.905) |
| P2-E3-protocol reference line, settled joint | - | 0.96-1.0 |

| stress continuation (recent items) | C1 | joint |
|---|---|---|
| M = 1,500 | 0.46-0.57 | 0.72-0.79 |
| M = 2,000 | 0.32-0.41 | 0.18-0.30 |
| M = 3,000 | 0.17-0.27 | 0.00 |

| other reported arms | value |
|---|---|
| writes during probes: fraction of about 170 written probes later recallable | 0.165-0.20 |
| out-of-distribution: 30 % cues, C1 | 0.00 (all seeds) |
| out-of-distribution: half cues with 10 of 50 lines replaced by noise, C1 | 0.075-0.175 |
| out-of-distribution: lures sharing 50 lines, recalled as the stored item | 0.90-0.95 |

**What the arms say:**
- **The novel-duty twin** never retrieves a stored item, yet writes the same store quality as the
  main line. Input duty, not recall, drives the contamination.
- **The settled state passes both index and content at M = 500.** At M = 1,000 no single state
  passes both on the same synapses: online gives index 0.68-0.74 with content 0.93-0.965; settled
  gives index 0.92-0.975 with content 0.835-0.915.

**Predictions scored** (the predictions before implementation, and the real driver's):

| held | failed |
|---|---|
| ONLINE INDEX FAIL (P 1.0) | O5 at M = 500 "likely holds": failed on seeds 18 and 20 |
| HABITUATION FAIL (P 1.0, real driver) | C1 at M = 1,000 predicted 0.70-0.85: 0.68-0.685 on 3 seeds |
| no ONLINE CONTENT FAIL (P 0.37 of the label) | O3 memory predicted 0.70-0.80: 0.61-0.67 on 3 seeds |
| responder \|R\| about 45 against 28.6 for the reference: 41-44.5 against 28-29 | stress joint at M = 1,500 predicted < 0.3: 0.72-0.79; at M = 2,000 predicted about 0: 0.18-0.30 |
| Jaccard(R, A) about 0.5 against 0.73: 0.48-0.53 against 0.71-0.75 | writes during probes "nearly all stored": 0.165-0.20 |
| online offset 6.8-7.0 mV | 30 % cues predicted C1 0.2-0.5: 0.00 |
| duty arm: online memory passes, store collapses | |

The writes-during-probes figure is confounded by online index failure: it is a stress test.

**Index latency, post hoc.** The online index failures are mostly slowed retrievals (diagnosis
D2, all five gated seeds):
- the assembly's first spikes come 6-8.5 ms later at M = 1,000;
- 0.89-0.93 of those cues reach the recall bar within 75 ms.

Combining D1 with that rescue gives C1 at 75 ms of about 0.955-0.97 at M = 1,000. This covers
recall only: spurious cells and ignition at 75 ms were not measured. It is labelled post hoc and
changes nothing. C1's 50 ms window is frozen and the O1 failure stands. Content within 50 ms
(joint_50ms) is only 0.73-0.855, so both readouts slow by about the same amount.

**Observation, post hoc and hypothesis-generating only.** Content failures on the main line are
almost always total `rec` silence: 79 of 2,762 cues regenerated 0 lines, and 3 regenerated 1-39.
Silence concentrates in items with small plateau sets: 64 % of cues for assemblies of 0-10 cells,
under 0.5 % for 19 or more.

**What the experimenter supplies** (wording per reviews). P2-E4 removes the rest before testing
and the frozen-copy test regime. It removes nothing at learning time. "Online" here means
**recall while scheduled learning continues**, not online learning.
- The write oracle, the key and the value remain.
- **A newly named supply: separate encoding and retrieval states, set by the schedule.** P2-E3's
  PASS relied on writing at a high continuation offset (8.35-8.56 mV at items 751-1,000) and
  reading after a 50 s settle (3.65-3.74 mV). With one state, at M = 1,000 the system gives fast
  access or clean content, not both.
- **That trade-off is shown for the responder write,** which recruits every cell above one shared
  threshold. It is not shown for the architecture.

**How the offset should be read.** The owner's narrowed reading applies throughout: the online
state differs by a higher offset among other differences, and which variable is responsible is
not isolated. Gated D2 does not replicate the exploration's offset correlate. At M = 1,000, the
assembly offset of content-only cues minus cues passing both is +0.57, +0.27, -0.15, +0.08 and
+0.40 mV.

**Decision, as predeclared:**
- The claim that accommodation provides a usable online operating point is withdrawn at M = 500
  and M = 1,000.
- Stage 1's clause "holds ... after 60 s of ongoing activity" is not met online by the P2-E3 system.
- Nothing is retuned.
- Work proceeds to P2-E5, as the owner ordered.
- Where a separately contracted operating-point mechanism sits, relative to the contamination fix,
  is the owner's decision.

**The prediction wording** follows the owner: no pass in 1,500 joint simulations (95 % upper bound
about 0.002, Monte Carlo error only). The analytic index-only pass probabilities were 4 × 10^-4 at
M = 500 and below 10^-38 at M = 1,000.

**A process disclosure.** The owner's reading of 2026-10-11 (DECISIONS.md, 09962a4) cited the first
gated readings from the lane logs, before the records for seeds 16 and 17 existed. Nothing changed
afterwards.
