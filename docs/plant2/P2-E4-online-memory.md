# P2-E4: online memory, recall while learning continues

**Contract, revised after red-team (2026-10-10). Not frozen until committed with its
schedule-and-power check.** No P2-E4 driver code exists. Gated seeds 16-20 are untouched.

**History:**
- the draft at commit 953851e;
- the two-critic-plus red-team (`review/plant2/P2-E4/redteam-*.md`; three lenses, a refuter per
  lens, a completeness critic; exploration on seeds 42-43 only);
- the decisions on each finding (`review/ledger.jsonl`, review "P2-E4 contract red-team").

The owner requires this experiment before Stage 1 counts as complete (`DECISIONS.md`, rulings of
2026-10-10). It gates the following at loads within the demonstrated capacity (M = 500 and
1,000):
- continuous recall;
- interference resistance;
- retention of the oldest items;
- repeated-cue habituation and recovery.

Learning past capacity and learning with writes during probes are **reported stress tests, not
gates**. P2-E2's and P2-E3's contracts and results are not changed.

## Why this test, and why previous passes do not settle it

- **The settle.** P2-E2 and P2-E3 tested frozen copies after a 50 s settle, with learning
  stopped. The P2-E2 review (exploratory, seed 0) found:
  - C1 at M = 1,000 was 0.875 with no rest, 0.915 after 5 s and 0.94 after 50 s;
  - on a 10-item exploratory run (seed 6), a half cue repeated for 30 s cut the share of items
    with recall >= 0.8 from 0.99 to 0.67.
- **The test block is itself a settle.** P2-E3's 600-cue test block lasts 180 s, against an
  accommodation time constant of 10 s. Recall has to be measured by short probes interleaved
  into learning.
- **Tests never fed back.** No test so far let tests affect later learning, or learning affect
  later tests. Here both can happen.
- **What the red-team's exploration found** (rough re-implementations, seeds 42-43, labelled;
  not results):
  - **Online index recall falls at M = 1,000.** Online C1 was 0.70-0.85, because at 50 %
    encoding duty the threshold offset sits near 7-7.7 mV, against about 3.7 mV settled.
  - **The online timeline changes the feedback write itself.**

    | measure, items 751-1,000 | P2-E3 protocol | online |
    |---|---|---|
    | continuation responders \|R\| | 28.6 | 45 |
    | Jaccard(R, A) | 0.73 | 0.49 |

    The online-written store fails content even after a settle (joint 0.81 / 0.89). The same
    raster read through the P2-E3-protocol store gives 0.98 / 0.99.
  - **So P2-E3's content PASS depended on its back-to-back protocol** (P2-E3 addendum 2).

  This experiment measures these effects under predeclared conditions.

## Hypothesis

The P2-E3 system, with every parameter frozen, keeps memory and content recall for recent and
old items while it learns one item every 500 ms with no settle and no `quiet()`. The recall is
caused by the cue. Recall survives 50 s of a repeated cue no worse than without the repetition,
and recovers within 10 s.

**Labelled limitations, stated up front.** The experimenter still supplies:
- **When to write** (the write oracle). Plateaus and feedback writes occur only inside
  encodings, so the system is told what to store and what is a probe.
- **The key.** Plateau cells are random and content-blind.
- **The value.** Eligible lines are copied one-to-one onto `rec`.
- **The operating point.** J, J_fb, g and accommodation tau are frozen. The red-team showed that
  the operating point depends on input duty, and that the responder write's specificity depends
  on the operating point at write time.
- **The input statistics.** Items are independent random patterns. Correlated items are P2-E5's
  question.

P2-E4 removes only two experimenter supplies from the gated numbers: the rest before testing,
and the frozen-copy test regime.

## No new mechanism; new protocol values, all fixed by argument before any gated run

Every model parameter is frozen from P2-E2 and P2-E3:
- J = 1.525 mV, accommodation tau 10 s;
- J_fb = 2.80 mV, g = 0.3;
- f_q, a, rates, encoding 200 ms, continuation 50 ms.

The new protocol values are:

| value | setting |
|---|---|
| interval I | 250 ms: a 50 ms pre-gap, a 100 ms probe slot, a 100 ms post-gap |
| gated loads and blocks | 240-step blocks ending at M = 500 and 1,000 |
| block mix | below |
| cohort pool | items 1-160 |
| habituation | 50 items per load, 100 repeated presentations, 20-step recovery, 3 recovery and 3 collateral cues |
| twins | below |

**Why I = 250 ms.** It is the shortest interval that holds one probe with:
- a pre-gap of 2.5 membrane time constants after the continuation;
- the 75 ms readout window inside the 100 ms cue;
- a 100 ms post-gap before the next encoding.

The red-team agreed to keep I = 250 ms. Moving it after exploration would be outcome-informed.
I = 2,000 ms is a reported duty arm, and it **cannot satisfy the online clause** (predeclared).

## Protocol: one continuous timeline per seed

**Ages.** An item learned at step j has age k - j at step k. Item k is age 0 in its own step's
probe slot.

**Learning step k:**
1. **Encoding** of item k (200 ms), with plateaus, eligibility and the BTSP write exactly as in
   P2-E1.
2. **Continuation** (50 ms), with the clipped feedback write from responders exactly as in
   P2-E3.
3. **Interval:** 50 ms background, 100 ms probe slot, 100 ms background.

There is no `quiet()` and no settle anywhere on the main line.

**Streams.** The encoding uses P2-E1's streams; the continuation uses P2-E3's stream 9. P2-E4's
own stream ids:

| id | use |
|---|---|
| 12 | interval background |
| 13 | probe-slot input |
| 14 | rolling schedule |
| 15 | block schedules and cohorts |
| 16 | habituation |
| 17 | novel items (never stored, never reused) |
| 18 | twins and reported arms |

The forward store must stay bit-identical to P2-E1's. BTSP reads only the encoding's input
spikes, from `_learn_in` (a fixed draw of m uniforms per tick), which nothing else consumes.

**The reconstruction layer `rec`** (owner's ruling 2):
- **A live engine population** on the main timeline and on every copy. It starts at rest at
  tick 0, is never reset, and runs through encodings. It has no outputs, so it cannot affect
  memory.
- **The live feedback projection** is reloaded from the feedback store right after each write.
- **Gated numbers come from this continuous simulation.**
- **The replay is used only in reported readouts:**
  - settled-twin comparability with P2-E3;
  - store swaps.

  There it is checked spike for spike against the carried live `rec` (see Validity).

**The never-probed cohort pool** (owner's ruling 2):
- **Items 1-160.** Two disjoint cohorts of 80 are drawn at seed start (stream 15): cohort 500 and
  cohort 1,000.
- **The rule.** A cohort item receives no probe of any kind before its own block. That includes
  full cues, blank targets, habituation duty and collateral duty.
- **Before step 162**, no unreserved stored item of age >= 1 exists. Rolling slots in steps 1-161
  therefore hold novel cues (85 %) or untargeted blank slots (15 %).
- **M = 250 is not a gated load.** Its retention cannot be measured without an unreserved
  oldest pool (red-team blocker M1/B1/FID-1). It is reported from rolling probes over steps
  201-250.

**Rolling slots** (steps outside gated blocks, from step 162; stream 14):

| kind | share |
|---|---|
| recent (ages 0-20) | 20 % |
| uniform (unreserved, ages >= 21) | 20 % |
| oldest-probed (cohort 500 items, after step 500; otherwise uniform) | 10 % |
| novel | 25 % |
| full | 10 % |
| blank (target ages 0-20) | 15 % |

**Gated blocks.** For M in {500, 1,000}: steps M-239 .. M (loads 261-500 and 761-1,000). Each
block holds exactly:

| kind | count | rule |
|---|---|---|
| recent | 50 | ages uniform on 0-20 |
| uniform | 50 | unreserved items of age >= 21, distinct |
| cohort | 80 | this load's cohort |
| novel | 30 | |
| blank | 20 | target ages 0-20 |
| full | 10 | |

- **Stratified order.** The block is cut into 10 sub-blocks of 24 steps. Each sub-block holds 5
  recent, 5 uniform, 8 cohort, 3 novel, 2 blank and 1 full, in random order (stream 15) (M7).
- **No stored item is cued twice within a block.**
- **Each half cue's mask** is drawn at seed start (stream 15) and reused by the paired settled
  retest.
- **The schedule builder** asserts every rule (counts, reservations, no repeats, ages) at seed
  start. If a draw is infeasible, it redraws with stream (seed, 15, attempt), deterministically,
  and records the attempt.
- **Its unit test** runs on non-gated seeds (90+) only, so no gated-seed material is exposed.

**Habituation arm,** at M = 500 and 1,000 (red-team M2, M3, FID-2, C2, C3, m4). After step M:
- **Items.** 50 items are drawn (stream 16) from unreserved stored items of age >= 21, excluding
  both cohorts.
- **Copies.** Each item gets a **repeated** and a **control** deep copy, `rec` live. Both run the
  main line's step rhythm with **sham encodings**, which hold the input duty and the operating
  point without adding load:
  - a sham encoding is 200 ms of a fresh random 100-line pattern (stream 16) at encoding rates,
    then 50 ms of the same pattern;
  - there are no plateaus, no BTSP update and no feedback write;
  - both copies get identical sham patterns and slot input draws, so repetition 1 is identical.

  | steps | repeated copy's slots | control copy's slots |
  |---|---|---|
  | 1-100 | the item's half cue (one fixed mask) every step | the item's cue at step 1 and steps 91-100; at steps 2-90, half cues of 89 other unreserved stored items (distinct, stream 16, outside the 50) |
  | 101-120 | blank (10 s) | blank (10 s) |
  | 121-126 | item, collateral, item, collateral, item, collateral | same |

  The control copy's 89 other cues match the repeated copy's cue duty.
- **The collateral item** is the unreserved stored item (outside the 50) whose assembly A
  overlaps the repeated item's assembly most, with ties going to the lowest index. Its half-cue
  mask is fixed.
- **"Both"** means memory recall >= 0.8 (50 ms) and the content joint (75 ms).
- **Statistics per item:**

  | statistic | definition |
  |---|---|
  | scored | repetition 1 passes both |
  | L_rep | passes among repetitions 91-100 on the repeated copy |
  | L_ctl | passes among steps 91-100 on the control copy |
  | eligible for O4 | scored, and L_ctl >= 8 |
  | habituated | eligible, and L_rep <= L_ctl - 3 |
  | recovery | of the three recovery cues, >= 2 pass both; per copy |
  | collateral | of the three collateral cues, >= 2 pass both; per copy |

**Twins and references at each gated load:**
1. **Settled twin A** (comparability; replay check). A deep copy after step M, carried live
   `rec` attached. It runs P2-E3's `run_phase` (the 50 s settle and P2-E3's 600-cue test) and
   logs the carried `rec`'s spikes. Readouts on its test raster:
   - P2-E3's replay with the online store, compared spike for spike with the carried `rec`;
   - the store swaps listed under Reported.
2. **Settled twin B** (paired retest, red-team M4, M7, FID-7). A deep copy after step M, carried
   live `rec`. It gets P2-E3's 50 s settle, then the block's 180 half cues, with the same masks,
   in the same order, at P2-E3's cue rhythm (100 ms on, 200 ms off). This gives the per-cue
   paired comparison of online against settled.
3. **Novel-duty twin** (probe history, M4, M13). A second timeline from step 1, identical except
   that **every** slot, gated blocks included, holds a fresh novel cue (stream 18). It has the
   same input duty and no retrieval of stored items. At M = 500 and 1,000 it records its stores
   and runs settled twin A's readout.
4. **P2-E3-protocol reference line** (implementation M1). `E3.learn` (with `quiet()`, back to
   back) on the same seed, to M = 1,000, with P2-E3's settled test at M = 500 and 1,000. Its
   forward store equals the main line's, and its feedback store is used for store swaps.

## Kill test (gated seeds 16-20, all fresh; each seed runs once)

Each criterion must hold on every gated seed at M = 500 and at M = 1,000.

| criterion | owner's term | what must hold |
|---|---|---|
| **O1 memory, online** | continuous recall, interference resistance | Of the block's 180 half cues (50 recent, 50 uniform, 80 cohort): recall >= 0.8 (50 ms) for >= 90 % (C1); spurious < 0.5 \|A\| for >= 90 % (C2). Of its 30 novel cues: ignition < 0.5 mean \|A\| for >= 90 % (C3) |
| **O2 content, online** | continuous recall, interference resistance | P2-E3's joint criterion (>= 40 of 50 missing lines, < 10 intrusions, 75 ms) for >= 90 % of the 180 half cues; D3 (< 10 lines) for >= 90 % of the 30 novel cues |
| **O3 retention** (never-probed cohort) | oldest-item retention; also Stage 1's "after 60 s of ongoing activity" (C7) | Of the 80 cohort cues: memory recall >= 0.8 for >= 90 %, and the content joint for >= 90 % |
| **O4 habituation** | repeated-cue habituation | At least 25 of the 50 items are eligible, and <= 10 % of eligible items habituated |
| **O5 recovery** | recovery | Recovery: >= 90 % pass on the repeated copy, among items that pass recovery on the control copy, with at least 25 such items. Collateral: >= 90 % pass on the repeated copy, among items whose collateral passes on the control copy, with at least 25 such items |

When a minimum count is not met, the criterion **fails** (not estimable). It is never skipped.

**How the owner's terms map** (FID-4, M8):
- **Continuous recall:** recent probes, inside O1 and O2.
- **Interference resistance:** uniform and cohort probes of old items while learning continues,
  inside O1, O2 and O3.
- **What interference can act through.** The forward store is bit-identical to P2-E1 whatever
  the online regime. So online interference acts only through the operating point (`vbar`) and
  the responder write.
- **Per-kind rates** (recent, uniform, cohort) are reported in the verdict text. They are not
  gated separately, because that would need 90-150 cues per kind (completeness review C1).

**Validity** (precedence: validity first, then the criteria):
1. The forward store's sha256 equals P2-E1 learning at M = 500 and 1,000.
2. The eligible fraction is >= 0.95; mean |A| is 18.5-21.5.
3. The feedback store equals the union of R(x) x E(x) over the items learned so far.
4. **No store changes across any probe slot.** An O(1) identity check of the stores' key arrays
   runs at every slot, and full digests at block ends.
5. **The live projection is current.** At every gated slot its load version equals the feedback
   store's write version, and the inhibition weight equals g x J_fb (C4b).
6. **The main line is untouched by every twin and copy.** Digests of the stores, `vbar`, mem v,
   t_last, delay rings, `rec` state, net.t and every generator state are taken before and after
   each twin and copy (C4a).
7. **The realised probe log passes an audit:**
   - cohort items were never cued or targeted before their block;
   - counts are exact;
   - nothing repeats within a block (C4c).
8. **Repetition 1 is identical on the repeated and control copies of every item.**
9. **The blank-slot leak check (O0, relabelled; M4, m2, FID-7).** The 20 blank slots per block
   target items of ages 0-20.
   - **Two statistics:**
     - **the leak statistic:** the mean fraction of the target's assembly active within 50 ms,
       and of its designated missing lines regenerated within 75 ms;
     - **the positive control:** the same measure over the last 50 ms of the age-0 item's own
       continuation, read from the live log. It shows the measure detects activity when there
       is any.
   - **Pass if all hold:**
     - <= 1 of 20 blank slots has target recall >= 0.8;
     - the mean leak statistic is <= the same-block novel-slot baseline + 0.05;
     - the positive-control mean is >= 0.5.
   - **In this architecture the check cannot fail except through a leak or bug.** The memory
     layer has no recurrence, so nothing persists past the pre-gap (red-team exploration: 0
     activity in 644 blank slots). It is therefore a validity check, not evidence.

A validity failure in a **reported** arm invalidates only that arm. The settled twins' replay
check is one of these: a mismatch is reported as a count of differing spikes and its effect on
the joint, not as INVALID, because carried `rec` state can differ by 1 ulp from rest (m1,
FID-8).

**Verdict** (a vector plus a label; M9, FID-3):
- **The vector.** Pass or fail for each of O1 (C1, C2, C3), O2 (joint, D3), O3 (memory,
  content), O4 and O5 (recovery, collateral), per load. Seeds are pooled by the all-seeds rule,
  and per-seed values are recorded.
- **The labels:**
  - **INVALID:** a gated validity check fails on any seed.
  - **PASS:** every criterion holds.
  - Otherwise, every applicable label, joined:
    - **ONLINE INDEX FAIL:** any memory criterion of O1 or O3 fails.
    - **ONLINE CONTENT FAIL:** any content criterion of O2 or O3 fails.
    - **HABITUATION FAIL:** O4 fails.
    - **RECOVERY FAIL:** O5 fails.

  A label never hides another.
- **Run once.** Gated seeds run once. A re-run needs the owner's ruling and keeps the first
  records.

## Power (before freezing; owner's ruling 2; red-team M5, M6, FID-6, C1)

Computed by `plant2/power.py` and recorded with this contract:
`bench/results/plant2.jsonl`, kind `power_reference`.

**O1-O3.** Exact binomials for each cue set, a logit-normal seed effect with SD 0.18 (the
recorded excess spread, about 0.01, on the probability scale), and all five seeds at both loads.

- **Reference rates** are the recorded settled rates of P2-E2 and P2-E3's gated seeds:

  | measure | M = 500 | M = 1,000 |
  |---|---|---|
  | C1 | 0.970 | 0.944 |
  | C2 | 0.999 | 0.989 |
  | C3 | 0.999 | 0.994 |
  | joint | 0.994 | 0.975 |
  | D3 | 0.999 | 0.998 |
  | oldest recall | 0.972 | 0.954 |
  | D4 | 0.998 | 0.972 |

  Within a block each cue is a distinct item scored once, so item heterogeneity can only shrink
  variance below binomial (M6b).
- **Result.** A system with **no online cost** passes O1-O3 on all seeds and loads with P = 0.83.
  - At M = 1,000: O1 0.91, O3 0.91.
  - The draft's sizes (120/60/40) gave 0.65, which is why the counts changed.

**O4 and O5.** Beta per-item reliability with intraclass correlation 0.09 (red-team estimate,
seeds 42-43), 50 items, both loads, all seeds, zero habituation:

| per-cue rate | O4 | O5 recovery | O5 collateral | O5 both |
|---|---|---|---|---|
| 0.95 | 0.998 | 0.994 | 0.994 | 0.988 |
| 0.93 | 0.987 | 0.952 | 0.950 | 0.905 |
| 0.90 | 0.87 | 0.68 | 0.69 | 0.47 |

O5 is weak below a per-cue rate of about 0.92; at the online rates expected at M = 1,000 it
cannot pass, whatever recovery does.

Under real habituation (late per-cue rate x 0.85), O4 fails with certainty, with about 22 % of
eligible items habituated. So O4 fails for habituation and not for item noise. The draft's
unpaired rule passed with only 0.62 at 0.93 with no habituation (M3).

**After implementation, before any gated seed.**
- **The exploration runs.** The real driver runs on seeds 42 and 43.
- **The Monte Carlo.** The full-rule Monte Carlo is re-run from their per-criterion rates. For
  O0-O3 it uses a binomial on the mean rates, with the seed effect above and the rates'
  uncertainty propagated. For O4 and O5 it uses a bootstrap of whole items from the exploration
  copies.
- **What is committed:**
  - P(PASS) as an interval;
  - the probability of each criterion and of each label;
  - the per-cue rate that would give P(PASS) >= 0.8, as one common logit shift of all rates;
  - the plant2 tree hash and the contract digest.
- **The guard.** A `--gated` run refuses to start unless:
  - that predictions commit is an ancestor of HEAD;
  - the tree is clean;
  - the plant2 tree hash and contract digest equal the recorded ones (M10).

## Reported, not gated

Each arm carries a prediction (C6).

| arm | what is reported | prediction |
|---|---|---|
| online against settled, paired (twin B) | per kind and load: online minus settled pass rates for memory and content; McNemar | memory: online lower by 0.15-0.25 at M = 1,000 and 0.03-0.08 at M = 500. Content: online about equal or **higher** (the settle raises intrusions from the online-written store) |
| write against readout cost (store swaps on twin A's raster) | the joint through (i) the online store, (ii) the reference line's store, (iii) the plateau-set store | (i) 0.80-0.90 at M = 1,000; (ii) and (iii) 0.97-1.0 |
| responder write | \|R(x)\|, R - A, Jaccard(R, A) and the continuation offset by age bin: main line, novel-duty twin, reference line, duty arm | main \|R\| about 45 against about 28.6 for the reference at M = 1,000; Jaccard about 0.5 against 0.73 |
| probe history (novel-duty twin against main) | stores, \|R\|, the settled readout | small differences, of uncertain sign (no item-specific path) |
| operating point | `vbar` offset at probe time per block; `rec` v at slot onset; manipulation check: block offset minus twin A's settled offset | about 7-7.7 mV online against about 3.7 mV settled at M = 1,000; about 2.5-3.5 against about 1.9 at M = 500; `rec` 2-4 mV below rest at slot onset |
| retention | recall and joint against age, from rolling probes; probed (cohort 500, via oldest-probed slots) against never-probed (cohort 1,000) retention at M = 1,000 | falls with age; probed against never-probed near zero under the write oracle (M14) |
| causality | cued minus blank by age, with age 0 shown separately | blank about 0; age-0 cued recall about 0.88-1.0 |
| habituation detail | per-repetition recall and joint; assembly and global `vbar` on each copy; the habituated fraction; recovery among habituated items | habituation present (exploratory: 1 of 8-10 items held 8 of 10 late repetitions on copies that settled); at M = 1,000 eligibility may fall under 25 |
| M = 250 | rolling probes over steps 201-250 | C1 about 0.92-1.0; joint about 1.0 |
| duty arm (I = 2,000 ms, post-gap 1,850 ms) | same blocks, M <= 1,000, online and settled twin A. Predeclared: **cannot satisfy the online clause** | online memory passes (C1 about 0.96-0.98); the store collapses (settled joint about 0.17) |
| beyond capacity (stress test) | the main line continues to M = 3,000; stress blocks ending at 1,500, 2,000 and 3,000 (100 recent ages 0-100, 60 uniform, 40 novel, 20 blank, 20 full) | blackout: the joint falls below 0.3 by M = 1,500 and about 0 at 2,000; rec saturates |
| writes during probe slots (store/recall oracle partly removed; stress test) | a copy at M = 1,000 runs 200 more steps. Each non-blank probe slot also draws plateaus at f_q per cell, applies BTSP to lines with >= 3 spikes in the 100 ms slot, and writes feedback from memory cells responding in the slot's last 50 ms. Still scheduled: slot boundaries, the eligibility window and the write time; background never writes. "Stored": a later presentation of the identical probe recalls its new assembly at >= 0.8. Compared with the main line at matched items (M = 1,200) and matched plateau episodes (about 1,370). BTSP depressions of existing items are reported | about 170 probes written, nearly all "stored", by arithmetic (C5). Older-item recall falls as at matched load |
| out-of-distribution probes | a copy at M = 1,000 with sham rhythm: 40 lures (novel items sharing 50 lines with a stored item), 40 cues of 30 % of an item's lines, 40 half cues with 10 of 50 lines swapped for noise | lures recalled as the stored item (> 0.8); 30 % cues: C1 low (about 0.2-0.5); noisy half cues: C1 below half cues |
| efficiency | bits per synapse (stored and potential); relative widths of the inherited parameter windows (J ±5 %, J_fb ±29 %) | about 0.2 bits per synapse |

**Cut on review, recorded in the ledger:**
- the a = 50 and a = 200 transfer timelines move to the capacity contract;
- the re-exposure arm moves to the familiarity and representation contract (FID-9).

## Predictions before implementation

These are the red-team's exploratory numbers (rough re-implementations, seeds 42-43). They stay
on record. Predictions from the real driver will be **appended** below them, never replacing
them (M10).

| criterion | prediction |
|---|---|
| O1 | **FAIL at M = 1,000** (C1 about 0.70-0.85). At M = 500 borderline (0.89-0.96). C2 and C3 hold |
| O2 | holds at M = 500. At M = 1,000 borderline (online joint 0.935-1.0) |
| O3 | memory **FAIL at M = 1,000** (ages 781+: about 0.70-0.80); borderline at 500. Content about 0.93 |
| O4 | at M = 1,000 likely not estimable (eligible < 25 when per-cue recall is about 0.77); at M = 500 uncertain |
| O5 | likely holds at M = 500; uncertain at M = 1,000 |
| validity | holds |

**Expected labels:** ONLINE INDEX FAIL, probably with HABITUATION FAIL (not estimable at
M = 1,000). P(PASS) < 0.05.

## Decision (predeclared; FID-4)

- **On PASS.** Stage 1's online clause is met, for the P2-E3 system on independent random items,
  at loads within the demonstrated capacity.
  - Stage 1 still needs the structured-input clause (P2-E5) and capacity growth.
  - No claim of lifelong memory is made until bounded capacity and graceful forgetting are shown.
  - Any later change to the feedback write or the operating point must re-pass P2-E4's gates on
    fresh seeds. The driver is built so its gates can be re-run cheaply on a changed system.
- **On any FAIL.**
  - The failure is recorded.
  - The claim that accommodation provides a usable online operating point is withdrawn for the
    failing loads.
  - Work proceeds to P2-E5 (structured input), as the owner ordered.
  - Whether a separately contracted operating-point mechanism comes before or after the
    contamination fix is the owner's decision. No parameter of P2-E2 or P2-E3 is retuned.
- **The duty arm,** however it comes out, does not satisfy the online clause.

## Files

| file | contents |
|---|---|
| `plant2/experiments/p2_e4_online.py` | the driver (subclass of E3; E3 is not edited) |
| `plant2/power.py` | power functions |
| `plant2/tests/test_p2_e4.py` | tests |
| `bench/results/plant2.jsonl` | records (append-only): `power_reference`, `exploration_seed`, `power_predictions`, `kill_test_seed`, `kill_test_verdict`, `reported_arms` |

- **Record order.** The gated record per seed is written before any reported arm runs.
- **Seeds.** Exploration on 42-43; gated seeds 16-20.
- **Cost estimate.** About 35 min per seed for the gated parts (habituation copies dominate,
  without store upkeep) and about 20 min for the reported arms.
