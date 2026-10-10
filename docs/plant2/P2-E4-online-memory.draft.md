# P2-E4: online memory, recall while learning continues

**Draft for red-team. Not yet a contract.** No P2-E4 driver code exists, and no gated seed has
been touched. This version applies:
- every accepted finding of the P2-E3 review (`review/plant2/P2-E3/`; ledger rows of
  2026-10-10T17:51);
- the owner's rulings of 2026-10-10 (`DECISIONS.md`, last entry).

It is frozen as a contract only after a two-critic red-team. That red-team explores on seeds
42-43 only.

The owner requires this experiment before Stage 1 counts as complete. It gates, at loads within
the demonstrated capacity:
- continuous recall;
- interference resistance;
- retention of the oldest items;
- repeated-cue habituation and recovery.

Learning past capacity and learning without the write oracle are **reported stress tests, not
gates** (owner's ruling 2). P2-E2's and P2-E3's contracts and results are not changed.

## Why this test, and why previous passes do not settle it

- **The settle.** P2-E2 and P2-E3 tested frozen copies after a 50 s settle, with learning
  stopped.
  - On seed 0, C1 at M = 1,000 was 0.875 with no rest, 0.915 after 5 s and 0.94 after 50 s
    (P2-E2 review).
  - A half cue repeated for 30 s cut the share of items with recall >= 0.8 from 0.99 to 0.67.
- **The test block is itself a settle.** P2-E3's 600-cue test block lasts 180 s, against an
  accommodation time constant of 10 s, so it settles the network anyway. Recall has to be
  measured by short probes interleaved into learning (methodology review F9).
- **Tests never fed back.** No test so far let tests affect later learning, or learning affect
  later tests. Here both happen: probes shift `vbar`, which changes later continuation
  responders, which changes later feedback writes.

## Hypothesis

The P2-E3 system, with every parameter frozen, keeps memory and content recall for recent and
old items while it learns one item every 500 ms with no settle and no `quiet()`. The recall is
caused by the cue, not by activity left over from encoding. The system keeps recall through 30 s
of a repeated cue and recovers within 10 s.

**Labelled limitations, stated up front:**
- **The write schedule is an experimenter oracle.** Plateaus and feedback writes occur only
  inside encodings, so the system is told what to store and what is a probe. A probe can never be
  stored, and a novel probe never becomes a memory.
- **Items are independent random patterns.** Correlated items are the next experiment's
  question (owner's ruling 1).
- **Accommodation is frozen at tau 10 s.** If O4 fails, that is a result about this operating
  point mechanism. It is not a parameter to retune.

## No new mechanism

Every parameter is frozen from P2-E2 and P2-E3:
- J = 1.525 mV, accommodation tau 10 s;
- J_fb = 2.80 mV, g = 0.3;
- f_q, a, rates, encoding 200 ms, continuation 50 ms.

**The one new protocol value is the interval I.** It is fixed below by argument, before any run.

## Protocol: one continuous timeline per seed

**Learning step k:**
1. **Encoding** of item k (200 ms), with plateaus, eligibility and the BTSP write exactly as in
   P2-E1.
2. **Continuation** (50 ms), with the clipped feedback write from responders exactly as in
   P2-E3.
3. **Interval** I = 250 ms:

   | part | length |
   |---|---|
   | pre-gap of background | 50 ms |
   | probe slot | 100 ms |
   | post-gap of background | 100 ms |

There is no `quiet()` and no settle anywhere.

**The forward store must still be bit-identical to P2-E1's.** BTSP reads only the encoding's
input spikes. Those come from the encoding stream (`_learn_in`, a fixed draw of m uniforms per
tick), which intervals and probes never consume: they have their own streams (ids 12-19,
reserved for P2-E4). This is checked.

**Why I = 250 ms** (methodology review F10):
- It is the shortest interval that holds one probe with:
  - a 50 ms pre-gap, 2.5 membrane time constants, so the continuation's input-driven activity
    has decayed before the cue starts;
  - the 75 ms readout window inside the 100 ms cue;
  - a 100 ms post-gap before the next encoding.
- **Duty:** items 50 %, probes 20 %, background 30 %.
- **The easier setting, I = 2,000 ms, is a reported duty arm.**

**The reconstruction layer** (owner's ruling 2: replay against continuous simulation):
- **Gated numbers come from continuous simulation.** The reconstruction layer `rec` is a live
  engine population on the main timeline, and on every copy taken from it.
  - It starts at rest at tick 0 and is never reset.
  - It runs through encodings too, though it has no outputs, so it cannot affect memory.
  - The live feedback projection is reloaded from the feedback store right after each write.
- **The replay is used in one place only:** the settled twin's P2-E3 test, for exact
  comparability with P2-E3. There it is verified spike for spike against a fresh live `rec`
  simulated over the same test phase (see Validity).

**What a probe slot can hold.** Every step's slot holds one probe, from the start of learning, so
there is no separate test regime that could act as a rest. The kinds:

| kind | content of the 100 ms slot | scored against |
|---|---|---|
| recent | half cue of a stored item of age 1-20 steps | that item |
| uniform | half cue of any stored item, excluding reserved cohorts | that item |
| cohort | half cue of an item in the current load's never-probed cohort | that item |
| oldest-probed | half cue of a pool item whose cohort was already measured | that item |
| novel | half cue of a fresh random item, never reused | nothing (ignition and lines) |
| full | full cue of a stored item | that item |
| blank | background only, no cue | a designated target of age 1-20 and its designated "missing" half |

**Rolling slots** (steps outside gated blocks) are drawn by a schedule fixed at seed start
(stream 14):

| kind | share |
|---|---|
| recent | 20 % |
| uniform | 20 % |
| oldest-probed | 10 %, given to uniform while empty |
| novel | 25 % |
| full | 10 % |
| blank | 15 % |

**Gated blocks.** The 240 steps that end at item M count for load M, for M = 250, 500 and 1,000.
Their slots hold exact counts in a random order (stream 15):

| kind | count | rule |
|---|---|---|
| recent | 40 | ages uniform on 1-20 (or on 1..k-1 early on) |
| uniform | 40 | distinct items |
| cohort | 40 | placed in the block's last 100 steps |
| novel | 60 | |
| full | 20 | |
| blank | 40 | target ages uniform on 1-20 |

No stored item is cued twice within a block.

**Never-probed cohorts** (owner's ruling 2):
- **The pool.** Items 1-120. Three disjoint cohorts of 40 are drawn at seed start (stream 15),
  one for each gated load.
- **The rule.** A cohort's items receive no probe of any kind before their own block's cohort
  slots. That includes full cues, blank targets and habituation duty.
- **The ages it gives:** 31-249 at M = 250, 281-499 at M = 500, and 781-999 at M = 1,000.
- **Afterwards,** pool items join the oldest-probed stratum. So at M = 1,000, the reported
  comparison of probed against never-probed retention is the measured cohorts (250 and 500)
  against cohort 1,000.

**Paired twins at each gated load:**
1. **Settled twin.** A deep copy after step M, with the live `rec` detached. It gets P2-E3's
   50 s settle and P2-E3's frozen test, run through P2-E3's own functions (`run_phase`,
   `readout`). This measures the cost of online operation within the same seed.
2. **No-probe twin.** A second timeline from step 1, identical (same item, plateau, input and
   interval streams) except that every rolling slot is blank. Its gated blocks hold the same
   probes. This separates interference caused by earlier probes from interference caused by
   learning.

**Habituation arm,** at M = 500 and 1,000:
- **Items.** 50 stored items are drawn by stream 16, excluding still-reserved cohorts. Each gets
  two deep copies of the main line, taken after step M, with no settle, no learning and `rec`
  live.
- **On the repeated copy:**
  1. the item's half cue, 100 times (100 ms on, 200 ms off; 30 s);
  2. 10 s of background;
  3. a recovery cue of the item (100 ms on, 200 ms off);
  4. a collateral cue: the next list item's half cue (100 ms on, 200 ms off).
- **On the control copy:** the same first cue (identical stream draws, so repetition 1 is
  identical on both copies), then background over the same 39.7 s, then the same recovery and
  collateral cues. This measures retest reliability with no repetition.
- **Scored items:** those that meet both memory recall >= 0.8 and the content joint at
  repetition 1.

## Kill test (gated seeds 16-20, all fresh; no calibration)

Each criterion must hold on every gated seed and at every load listed.

| criterion | loads | what must hold |
|---|---|---|
| **O0 causality** (blank control) | 250, 500, 1,000 | Of the block's 40 blank slots: <= 2 (5 %) show memory recall >= 0.8 of the target's assembly within 50 ms, and <= 2 show >= 40 of the target's designated missing lines within 75 ms |
| **O1 memory, online** | 250, 500, 1,000 | Of the block's 120 half cues (recent, uniform and cohort): recall >= 0.8 for >= 90 % and spurious < 0.5 \|A\| for >= 90 % (C1, C2). Of its 60 novel cues: ignition < 0.5 mean \|A\| for >= 90 % (C3) |
| **O2 content, online** | 250, 500, 1,000 | P2-E3's joint criterion (>= 40 of 50 missing lines, < 10 intrusions, 75 ms) for >= 90 % of the 120 half cues; D3 (< 10 lines) for >= 90 % of the 60 novel cues |
| **O3 retention** (never-probed cohort) | 250, 500, 1,000 | Of the 40 cohort cues: memory recall >= 0.8 for >= 90 %, and the content joint for >= 90 % |
| **O4 habituation** | 500, 1,000 | For >= 90 % of scored items: >= 8 of repetitions 91-100 meet both memory recall >= 0.8 and the content joint |
| **O5 recovery** | 500, 1,000 | The recovery cue meets both for >= 90 % of scored items. The collateral cue meets both for >= 90 % of copies whose collateral item is itself scored |

**Validity:**
- the forward store's sha256 equals P2-E1 learning at each gated load;
- the eligible fraction is >= 0.95, and mean |A| is 18.5-21.5;
- the feedback store equals the union of R(x) x E(x) over the items learned so far;
- no store changes across any probe slot: digests before and after each gated-block slot;
- the main line's forward store, feedback store, `vbar` and `rec` state are digested before and
  after every twin and copy, and must be unchanged;
- the settled twin's replay equals the live `rec` spike for spike, at each load;
- repetition 1 is identical on the repeated and control copies.

There is no convergence bar, because there is no settle to converge. The signed `vbar` drift over
each block is reported.

**Verdict names:**
- **INVALID:** a validity check fails.
- **VOID:** O0 fails on any seed or load. Online recall is then not attributable to the cue, so
  O1-O5 cannot be read.
- **ONLINE FAIL:** O1, O2 or O3 fails.
- **HABITUATION FAIL:** only O4 or O5 fails. Stage 1 is then incomplete. The next step is a
  single-mechanism contract for the operating point, with the owner's ruling, since the
  mechanism belongs to a gated family. It is never a retune of tau.
- **PASS:** O0-O5 all hold.

## Power, including dependence and the five-seed rule (owner's ruling 2)

**The problem.** Single-test binomial power overstates the chance of a full PASS, for two
reasons:
- the acceptance rule needs every criterion, at every load, on all five seeds;
- items differ in reliability, so outcomes of the same item are correlated.

**The method, fixed before exploration.**
1. **Exploration runs.** On seeds 42 and 43 the full protocol runs, plus a reliability arm. On a
   copy at each gated load, each of the block's 120 half-cue items is cued 5 times, interleaved
   with novel and blank slots in the gated rhythm. That estimates per-item pass probabilities.
2. **A Monte Carlo of the complete acceptance rule.** It draws per-item probabilities from that
   empirical distribution, with memory and content outcomes drawn jointly per cue, and simulates:
   - O0-O3 at three loads;
   - O4-O5 at two loads, using the habituation and control copies' per-item outcomes;
   - five seeds, with seed-to-seed spread taken from the two exploration seeds.

   The output is P(PASS) for a system that behaves like the exploration seeds, and the per-item
   rate that would give P(PASS) >= 0.8.
3. **Commit before gating.** Both numbers and the predictions are committed before any gated
   seed. If P(PASS) is low, that is recorded as the prediction. The bars do not change.

**Single-test reference, binomial:**

| sample | P(>= 90 %) at a true rate of 0.95 | at 0.97 |
|---|---|---|
| 120 | 0.993 | 1.000 |
| 60 | 0.92 | 0.99 |
| 40 | 0.952 | 0.993 |
| 50 | 0.962 | 0.996 |

## Reported, not gated

Each arm is predeclared with a prediction, so that the record shows where the mechanism stops
working.

- **Online cost.** Online minus settled twin, per criterion and load.
- **Probe-caused interference.** Main line minus no-probe twin: the gated criteria, feedback-store
  size and |R(x)| over each block.
- **Causality detail.** Cued minus blank recall, by target age, with age 1 shown separately.
- **Retention.**
  - recall and content joint against item age, from rolling probes;
  - probed against never-probed retention, at M = 1,000.
- **The operating point.** `vbar` offset against time.
- **Habituation detail.** Recall and joint per repetition, offset rise per repetition, and the
  control copies' retest reliability.
- **Duty arm.** I = 2,000 ms (the pre-gap and probe unchanged, a 1,850 ms post-gap), the same
  blocks, M <= 1,000.
- **Beyond capacity** (stress test). The main timeline continues to M = 3,000, with blocks
  ending at 1,500, 2,000 and 3,000. Recent probes there cover ages 1-100. Predicted blackout.
- **Re-exposure.** A copy at M = 1,000 re-learns 50 stored items as ordinary episodes. Reported:
  synapses added per re-exposure against a new item's, and recall of the re-exposed and other
  items.
- **No write oracle** (stress test). A copy at M = 1,000 runs 200 more steps with plateaus at the
  base rate f_q during probe slots too, with a BTSP write for each probe's eligible lines.
  Reported: how many probes get stored, and the effect on later recall.
- **Out-of-distribution probes**, on a copy at M = 1,000:
  - lures (novel items sharing 50 lines with a stored item; predicted to be recalled as that
    item);
  - cues of 30 % of an item's lines;
  - half cues with 10 lines swapped for noise.
- **Transfer timelines** to M = 500 at frozen values, with a = 50 and a = 200 items.
- **Efficiency.** Bits stored per synapse and per potential synapse, plus the relative width of
  the parameter windows inherited from P2-E2 and P2-E3.

## Predictions

These are not run. They will be replaced by exploration-seed numbers and the power Monte Carlo
before any gated seed.

| criterion | prediction |
|---|---|
| O0 | holds: membrane activity decays within the 50 ms pre-gap, and nothing in the memory layer persists |
| O1 | C1 0.88-0.95 at M = 1,000, below P2-E2's settled 0.925-0.955. May fail on some seeds |
| O2 | 0.93-0.97 |
| O3 | 0.93-0.97 |
| O4 | **FAIL**: late repetitions near 0.67, from the P2-E2 review |
| O5 | 0.85-0.95 |

Chance of a full PASS: about 10-20 %. The most likely verdict is HABITUATION FAIL.

## Implementation notes

- **The driver.** `plant2/experiments/p2_e4_online.py`, a subclass of E3 that does not edit E3.
  The subclass removes `quiet()`, adds the interval, keeps `rec` live, and reloads the feedback
  projection after each write.
- **Its own schedule builder and scorer.** Every window, span, size and bar comes from one
  config dict. The contract digest covers all of them.
- **A guard on gated runs.** A `--gated` run refuses to start unless the predictions commit is
  an ancestor of HEAD and the plant2 tree is clean.
- **Records.** The gated record per seed is written before any reported arm runs, so a crash in
  a stress test cannot touch it.
- **Seeds.** Exploration on 42-43. Gated seeds 16-20.
- **Cost.** About 6-10 s of simulated time per s of wall time, measured. That is about 25 min
  per seed for the gated parts and as much again for the reported arms.
