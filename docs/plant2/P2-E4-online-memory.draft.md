# P2-E4: online memory, recall while learning continues

**Revised draft, not a contract.** It has not been red-teamed and it is not frozen. No code
exists, and no gated seed has been touched. This revision applies every accepted finding from
the P2-E3 review (`review/plant2/P2-E3/`, ledger rows of 2026-10-10T17:51). Points that wait on
the owner's rulings (`docs/plant2/EVAL-after-P2-E3.md`, decisions 1-2) are marked **[owner]**.

The owner requires this experiment before Stage 1 counts as complete (`DECISIONS.md`, rulings
of 2026-10-10). It tests recall while the system keeps learning new items, with no artificial
50 s settle, and covers:
- interference;
- retention of older memories;
- repeated-cue habituation.

P2-E2's and P2-E3's contracts and results are left unchanged.

## Why this test, and why previous passes do not settle it

- **The settle.** P2-E2 and P2-E3 tested a frozen copy after a 50 s settle, with learning
  stopped.
  - On seed 0, C1 at M = 1,000 was 0.875 with no rest, 0.915 after 5 s and 0.94 after 50 s
    (P2-E2 review).
  - A half cue repeated for 30 s cut the share of items with recall >= 0.8 from 0.99 to 0.67.
- **The test block is itself a settle.** P2-E3's 600-cue test block lasts 180 s, against an
  accommodation time constant of 10 s. A long test block therefore settles the network on its
  own (methodology review F9). Recall must be measured in short probes interleaved into
  learning.
- **Tests never fed back.** No test so far has let tests affect later learning, or learning
  affect later tests. Here both happen: probes shift `vbar`, which changes later continuation
  responders, which changes later feedback writes.

## Hypothesis

The P2-E3 system, with every parameter frozen, keeps memory and content recall for recent and
old items while it learns one item every 500 ms with no settle and no `quiet()`. It also keeps
recall through 30 s of a repeated cue, and recovers within 10 s.

**Labelled limitations, stated up front:**
- **The write schedule is an experimenter oracle.** Plateaus occur only inside encodings, so
  the system is told which inputs to store and which are probes. A probe can never be stored,
  and a novel probe never becomes a memory.
- **Items are independent random patterns.** The structured-input question is separate
  ([owner], decision 1).
- **Accommodation is frozen at tau 10 s.** If O4 fails, that is a result about this operating
  point mechanism. It is not a parameter to retune (north-star reviews NS7 and F10).

## No new mechanism

Every parameter is frozen from P2-E2 and P2-E3:
- J = 1.525 mV, accommodation tau 10 s;
- J_fb = 2.80 mV, g = 0.3;
- f_q, a, rates, episode timing (200 ms encoding, 50 ms continuation).

**The one new protocol value is the inter-item interval.** It is fixed below by argument,
before any run.

## Protocol: one continuous timeline per seed

**Learning step k.** Encoding of item k (200 ms), then the continuation (50 ms), then an
interval of I ms.
- **No `quiet()` and no settle anywhere.** Each episode starts from the ongoing state.
- **The forward store must still be bit-identical to P2-E1's.** BTSP reads only the encoding's
  input spikes. Those come from the encoding stream (`_learn_in`, a fixed draw per tick), which
  probes, intervals and background never consume: they get their own streams. This is checked.

**The interval I.** The gated value is **I = 250 ms**. It is the shortest interval that holds
one probe:
- a 100 ms cue, whose 75 ms readout window ends before the cue does;
- then 150 ms of background before the next encoding.

With it:
- item duty (encoding plus continuation) is 50 %;
- probe duty is 20 %;
- background is 30 %.

**A reported duty arm uses I = 2,000 ms.** The interval is a new value, so it is gated at the
hardest defensible setting and the easier one is reported (methodology review F10).

**One probe in every interval, from the start of learning.** The timeline is therefore
homogeneous: there is no separate test regime that could act as a rest.

**Probe kinds,** drawn by a predeclared stream (stream ids 12-19 are reserved for P2-E4):

| kind | share | content |
|---|---|---|
| recent | 20 % | half cue of a stored item of age 1-20 steps |
| uniform | 20 % | half cue of any stored item |
| oldest | 20 % | half cue of one of the first 100 items |
| novel | 30 % | half cue of a fresh random item, never reused |
| full | 10 % | full cue of a stored item |

**Gated blocks.** The probes in the 200 steps that end at item M count for load M, for M =
250, 500 and 1,000. They are drawn with exact counts:
- 120 half cues: 40 recent, 40 uniform and 40 oldest;
- 60 novel cues;
- 20 full cues.

**The reconstruction layer** is replayed from the main timeline's whole memory raster:
- it starts at rest at tick 0 and is never reset, and it runs through encodings too;
- the replay code is P2-E3's, with the span fix of 2026-10-10;
- the span is cue plus background (250 ms).

**Paired twins at each gated load** (methodology review F12, constructive review F5):
1. **Settled twin.** A deep copy at M, given P2-E3's 50 s settle and P2-E3's frozen test,
   unchanged. It measures the cost of online operation within the same seed.
2. **No-probe twin.** A second timeline from step 1, identical except that intervals outside
   gated blocks hold background instead of probes. It shares the same item, plateau and input
   streams. It measures interference caused by earlier probes, as opposed to interference
   caused by learning.

**Habituation arm,** at M = 500 and 1,000 (methodology review F14, constructive review F4):
- 50 stored items are drawn by stream. Each gets **its own** deep copy of the main line at M,
  with no settle and no learning on the copy.
- On each copy:
  1. the item's half cue is shown 100 times (100 ms on, 200 ms off; 30 s);
  2. 10 s of background follow;
  3. then one recovery cue;
  4. then one collateral cue: the half cue of the next habituation item in the list.
- **Unrepeated control** (reported). On a second copy per item: the first cue, 40 s of
  background, then the same recovery and collateral cues. This measures retest reliability with
  no habituation.
- **Scored items:** only those that pass at repetition 1 (memory recall >= 0.8 and content
  joint).

## Kill test (gated seeds 16-20, all fresh; no calibration)

| criterion | what must hold, every gated seed and load |
|---|---|
| **O1 memory, online** | Over the block's 120 half cues: recall >= 0.8 (50 ms window) for >= 90 %; spurious < 0.5 \|A\| for >= 90 %. Over its 60 novel cues: ignition < 0.5 mean \|A\| for >= 90 % (P2-E2's C1-C3) |
| **O2 content, online** | P2-E3's joint criterion for >= 90 % of the 120 half cues; D3 for >= 90 % of the 60 novel cues |
| **O3 retention** | the joint criterion for >= 90 % of the 40 oldest-stratum cues |
| **O4 habituation** (M = 500 and 1,000) | for >= 90 % of scored items, >= 8 of repetitions 91-100 meet both memory recall >= 0.8 and the content joint |
| **O5 recovery** (M = 500 and 1,000) | the recovery cue meets both for >= 90 % of scored items, and the collateral cue meets both for >= 90 % |

**Power** (binomial, if the true per-cue rate were 0.95 / 0.97):

| sample | P(pass) at 0.95 | P(pass) at 0.97 |
|---|---|---|
| 120 cues | 0.993 | 1.000 |
| 40 cues | 0.952 | 0.993 |
| 50 items | 0.962 | 0.996 |
| O4 per item, at a per-repetition rate of 0.95 | 0.989 | |

The unrepeated control's retest rate is measured on exploration seeds 42-43 before the
contract is frozen. If it is below 0.95, O5's sample is raised, not its bar.

**Validity:**
- the forward store's sha256 equals P2-E1 learning at each gated load;
- the eligible fraction is >= 0.95;
- mean |A| is 18.5-21.5;
- the main line's forward store, feedback store and `vbar` are digested before and after every
  twin and habituation copy, and must be unchanged (code review F7);
- no store changes during any probe, checked per probe on the main line.

**There is no convergence bar.** There is no settle to converge. The signed `vbar` drift over
each gated block is reported.

**Verdict names:**
- **PASS**: O1-O5 all hold.
- **ONLINE FAIL**: O1, O2 or O3 fails.
- **HABITUATION FAIL**: only O4 or O5 fails. Stage 1 is then incomplete. The next step is a
  single-mechanism contract for the operating point, with the owner's ruling, since the
  mechanism belongs to a gated family. It is never a retune of tau.

## Reported, not gated

Each arm below is predeclared with a prediction, so that the record shows where the mechanism
stops working (north-star review NS5).

- **Online cost.** Online minus settled twin, per criterion and load.
- **Probe-caused interference.** Main line minus no-probe twin, for the gated block's criteria,
  feedback-store size and |R(x)| over the block.
- **Retention curve.** Recall and content joint against item age.
- **Offset.** The `vbar` offset against time.
- **Habituation detail.** Recall and joint per repetition, and the offset rise per repetition.
- **Duty arm.** I = 2,000 ms, same gated blocks, M <= 1,000.
- **Beyond capacity** (north-star review NS4) **[owner: gated or reported]**. The main timeline
  continues to M = 3,000, with the content joint for recent probes (ages 1-100) in blocks ending
  at 1,500, 2,000 and 3,000. Predicted blackout.
- **Re-exposure** (constructive review F3). A copy at M = 1,000 re-learns 50 stored items as
  ordinary episodes. Reported: synapses added per re-exposure against a new item's, and recall of
  the re-exposed and the other items.
- **No write oracle** (methodology review F13, north-star review NS3). A copy at M = 1,000 runs
  200 more steps with plateaus at the base rate f_q during probes as well. Reported: how many
  probes get stored, and the effect on later recall.
- **Lures** (north-star review NS3). Novel items sharing 50 lines with a stored item. Reported:
  recalled as the stored item (predicted).
- **Transfer battery** (constructive review F6). Short timelines to M = 500 at frozen values
  with a = 50 and a = 200 items, and with prototype-family items at 16 % sibling overlap.
  Predicted: C1 fails at a = 50; content fails on families.
- **Efficiency.** Bits stored per synapse and per potential synapse (constructive review F11).

## Predictions

These are not run. The basis is the P2-E2 review's exploration and P2-E3's gated numbers. They
will be replaced by exploration-seed numbers (42-43) before the contract is frozen.

| criterion | prediction |
|---|---|
| O1 | C1 0.88-0.95 at M = 1,000, below P2-E2's settled 0.925-0.955. Likely fails on some seeds |
| O2 | 0.93-0.97 |
| O3 | 0.93-0.97 |
| O4 | **FAIL** (late repetitions near 0.67, from the P2-E2 review) |
| O5 | 0.85-0.95 |

Chance of a full PASS is about 10-20 %. The most likely verdict is HABITUATION FAIL.

## Implementation notes (code review F9, F6, F8)

- **A subclass of E3.** E3's `learn_one` is not edited. The subclass removes `quiet()`, records
  the raster during learning, and inserts the interval.
- **Its own probe builder and scorer.** These take window, span, item size and every scoring
  constant from one config dict. The contract digest covers all of them.
- **Feedback-store validity is defined afresh.** The feedback store is now timeline-dependent,
  so P2-E3's identity check cannot carry over. The forward-store identity can.
- **A guard on gated runs.** A `--gated` run refuses to start unless the predictions commit is
  an ancestor of HEAD and the plant2 tree is clean.
- **Seeds.** Exploration and red-team on seeds 42-43 only. Gated seeds 16-20.
- **Cost estimate.** About 25 min of wall time per seed for the gated arms. The reported arms
  add about as much again.
