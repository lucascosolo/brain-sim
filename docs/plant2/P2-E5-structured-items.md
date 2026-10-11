# P2-E5: item-specific recall on correlated inputs (structured-input diagnostic)

**Revised after the red-team. Not yet frozen.** No P2-E5 code exists. Gated seeds 21-25 have not
been touched.

- **The red-team.** The draft (commit e736e81) was reviewed by three critics, each with a
  refuter, plus a completeness critic. Their findings are recorded verbatim in
  `review/plant2/P2-E5/`, and the disposition of each is in `review/ledger.jsonl`.
- **Exploration.** All exploratory numbers below come from the red-team's scripts on seeds 44-45
  and are labelled as such.
- **Before freezing:** a verification pass, and the power reference record.
- **After implementation:** predictions from the real driver on seeds 44-45 are appended, and
  committed before any gated seed.
- **Timing.** Implementation waits until P2-E4's gated seeds 16-20 have finished, because the
  plant2 tree is frozen while they run.

**Ordered by the owner** (`DECISIONS.md`: rulings of 2026-10-10, items 1 and 4; guidance of
2026-10-11):
1. Run the existing system first, with **no new mechanism**, as a new Stage 1 gate:
   - about 16 % sibling overlap;
   - M = 500 and ultimately 1,000;
   - fresh seeds;
   - diagnostic arms at lower and higher overlap.
2. If it fails, investigate the responder write. The plateau-set store is an **upper-bound
   diagnostic, not an acceptable solution**. The goal is a network that finds which of its own
   active cells represent the experience, without being handed A(x).
3. Any correction is a separately contracted single mechanism.
4. Learning-time contamination and operating-point instability are separate problems, fixed one
   at a time. Put first whichever matters most under the structured-input tests.
5. Test whether contamination worsens under continuous learning, without adding a second
   mechanism.

The capacity-scaling experiment takes the next free number when its contract is written.

## Why this test

- **Every gated item so far was an independent random pattern,** with about 2.5 % pairwise
  overlap. Stage 2's shared items and Stage 3's exemplars are correlated by definition.
- **What exploration shows** (seeds 44-45; review/plant2/P2-E5/; exploratory, not results). The
  frozen P2-E3 system on exemplars of 10 never-shown prototypes, siblings sharing about 17 of
  100 lines (s = 60):

  | measure | M = 500 | M = 1,000 |
  |---|---|---|
  | content joint, main store | 0.10-0.145 | 0.000 |
  | same raster, plateau-set store | 0.925-0.94 | 0.12-0.18 |
  | memory C2 (spurious) | 0.895-0.92 | 0.465-0.495 |
  | memory C4, spurious part (oldest 100) | 0.86-0.92 | 0.35-0.47 |

- **How the content store is contaminated.** The cause sentence in the draft and in
  `EVAL-after-P2-E3.md` had the direction backwards; corrected here.
  - The write sets `w_fb(i -> j) = 1` for every responder i in R(x) and eligible line j in E(x).
  - At s = 60, x's encoding drives cells of earlier siblings' assemblies through their shared
    prototype lines. So R(x) holds those cells as well as A(x): |R| is about 52 against |A| of
    about 20 at M = 500. Almost all of the extra responders (99.7 %) belong to earlier siblings,
    and their number grows with the family's age: about 74 for items 400-500, and 150-160 for
    items 900-1,000.
  - **Those cells receive x's lines.** Later, when a sibling y's half cue drives them, they
    regenerate x's lines into y's readout.
  - So an item is damaged after it is stored, by later siblings writing onto its cells. In y's
    intrusions:
    - lines only later siblings have average 40-48;
    - lines only earlier siblings have average 2.3-2.4;
    - prototype lines y lacks average 36.
  - The oldest items are hit hardest: D4 is 0.01-0.04, against a joint of 0.10-0.13.
  - Regeneration of the item's own missing lines still holds (D1 0.98-1.0). **The failure is
    entirely intrusions (D2).**
- **At M = 1,000 the forward index fails too, upstream of any feedback write.**
  - Spurious memory cells rise from about 2.9 per half cue at M = 500 to about 19 at M = 1,000.
    98 % are plateau cells of one or more siblings, carrying about 9 prototype lines from the
    cue.
  - No change to the feedback write can affect C1-C4. Even the plateau-set store fails at every
    point of a 72-point readout grid (best joint 0.585-0.600).
  - This is a third problem, forward-index cross-talk on correlated items. **It is outside the
    owner's two named problems.**
- **Own-cell identity is in the network's activity** (completeness critic, C4). During the
  continuation:
  - A(x)'s cells fire about 5 spikes in 50 ms at M = 500, and about 3.9 at M = 1,000;
  - sibling responders fire about 1.05, and 94 % of them fire exactly once;
  - the count separates the two with AUC 0.996-0.9996.

  A store written only from cells with at least 3 continuation spikes reproduces the plateau-set
  store's content numbers at both loads. This bears directly on the owner's research target. It
  is measured here and adopted nowhere.
- **The owner's objective.** Remember previously experienced correlated items without
  contamination. Generalising to a never-seen family member belongs to Stage 3. Here it is
  reported, never gated.

## Hypothesis (the one the existing system is expected to fail)

The frozen P2-E3 system, under P2-E3's settled protocol, stores exemplars of related families
item-specifically:
- about 16 % sibling overlap;
- F = 10 families;
- M = 500 and 1,000.

From a half cue it regenerates the item's own missing lines, item-specific ones included, with
few intrusions from the prototype or from siblings. Its memory index stays specific. Precisely,
criteria S1-S4 hold on every gated seed at both loads.

**Scope.** P2-E3's protocol (`quiet()` between items, 50 s settle, frozen copies) is the more
favourable of the two learning rhythms examined for the responder write (P2-E3 addendum 2). In
exploration, P2-E4's 250 ms online rhythm left more continuation responders (|R| 105-111 against
72-75 at M = 500) and a lower settled joint (0.055-0.065 against 0.10-0.145).
- **A PASS** is therefore scoped to the settled protocol.
- **A FAIL** is not an artefact of a hostile operating point.
- **The joint condition** (structured and online) is reported here, not gated. Any correction
  must re-pass the gates of P2-E3, P2-E4 and P2-E5 on fresh seeds.

**Labelled limitations.** The experimenter still supplies:
- **When to write** (the write oracle). Plateaus and feedback writes happen only inside
  protocol-marked encodings.
- **The key.** Plateaus are random and content-blind.
- **The value.** Eligible lines are copied one to one onto `rec`.
- **The operating point.** J, J_fb, g and accommodation tau are frozen. The settled protocol is
  imposed.
- **The input statistics.** These are new here: hidden prototypes, the overlap s, the number of
  families F, and the cyclic family order.

P2-E5 removes none of these and adds one, the item distribution. It is a diagnostic of the
existing system, not a step that reduces experimenter-supplied cognition.

## No new mechanism; one changed variable

- **Everything is P2-E3 exactly:**
  - the network and stores;
  - J* = 1.525 mV, accommodation tau 10 s, J_fb* = 2.80 mV, g = 0.3;
  - the episode (200 ms encoding plus 50 ms continuation, `quiet()` between items);
  - the 50 s settle and the frozen-copy test;
  - the readout, the scoring code and **P2-E3's validity rules, convergence included** (mean
    |dvbar| <= 0.2 mV).
- **Only the item distribution changes.** P2-E4 isolates online operation, and this experiment
  isolates input structure.
- **Reported arms** examine the joint condition (the online arm) and the confounds of the item
  design.

## Items

- **Prototypes.** F random sets of 100 of the 4,000 lines each, never shown.
- **An exemplar** of family f keeps `100 - s` of the prototype's lines, chosen at random, and
  adds `s` random lines from outside the prototype.
- **Learning order.** Item k belongs to family k mod F, so every family is represented at every
  age. Exploration found learning order (cyclic or random) changes nothing: frozen-point joint
  0.130 against 0.140.
- **Sibling overlap.** Two siblings share about (100 - s)^2 / 100 prototype lines plus chance
  overlap. At s = 60 that is 16.8-17.0 lines, measured.
- **F = 10, fixed by argument.**
  - The owner's ruling fixes sibling overlap, not family size.
  - With F fixed, family size grows with load: 50 exemplars per family at M = 500, 100 at
    M = 1,000. This is the regime of a learner accumulating exemplars of a fixed set of kinds.
    It is also where the exploratory collapse was found.
  - **Confounds.** Correlation, family size and per-line load move together:
    - prototype lines carry about 29 items at M = 500 and 58 at M = 1,000;
    - for independent items the figure is 12.5 and 25.

    Two reported arms separate them: a line-frequency-matched pooled control, and F = 40.

| arm | s | F | sibling overlap | role |
|---|---|---|---|---|
| **main** | 60 | 10 | about 16-17 % | **gated** |
| low overlap | 80 | 10 | about 4-6 % | reported (owner's diagnostic arm) |
| high overlap | 40 | 10 | about 36 % | reported (owner's diagnostic arm) |
| independent items | 100 (P2-E3's own generator) | - | about 2.5 % | reported; P2-E3 replication on fresh seeds (positive control) |
| pooled control | 60 (prototype share drawn from the union of the 10 prototypes) | 10 | about 3.7 % | reported; same per-line loads as main, no sibling correlation |
| F = 40 | 60 | 40 | about 16-17 % | reported; families of 12-25, roughly uniform line load |
| online | 60 | 10 | about 16-17 % | reported; learning on P2-E4's frozen online rhythm |

**Pairing.** Plateaus come from P2-E1's plateau stream (n uniforms per item, whatever the
content), so A(k) is identical across the arms for every item k. Only the content differs.
Every arm records a digest of its A lists, and the dose-response uses paired per-item
comparisons.

### Streams (P2-E5 owns ids 20-24; every other stream is P2-E1's, P2-E3's or P2-E4's, unchanged)

| key | use and draw order |
|---|---|
| (seed, 20, F) | prototypes: for f = 0..F-1, a choice of 100 of 4,000 lines without replacement |
| (seed, 21, F, k) | exemplar k (k = 1, 2, ...): a permutation of its prototype's 100 lines, then a permutation of the 3,900 lines outside it. The exemplar is the first 100 - s of the former plus the first s of the latter. Arms with the same F share the draws, so their kept sets are nested. |
| (seed, 23, k) | pooled control exemplar k: 100 - s lines drawn uniformly without replacement from U, the union of the F = 10 prototypes; then s lines from outside P_(k mod 10), excluding those already drawn |
| (seed, 22, M) | the reported cue block at load M, in this order: 100 new exemplars (as above, families cycling 0..F-1); their half masks; a half mask for each of 50 prototype cues (5 per family); the block's input spikes (its own `present()` stream) |
| (seed, 24, M) | pi, a within-family derangement (no fixed points) for the label-permuted store at load M |

**Pins.**
- **Plain P2-E1 learning on the same items.** The generator is injected into a plain E1
  (`plain._pat`). The forward-store check therefore tests the encoding path, not the
  generator.
- **Gated scores** come from P2-E3's `readout` and `score` on the first 600 onsets: 200 half,
  200 novel and 200 full cues.
- **The reported block** is a separate `present()` call after them, so it cannot change a gated
  score. A unit test checks this identity.

## Test (P2-E3's protocol, at each load)

- **Learning and test.** Learning runs to M. A deep copy gets the 50 s settle, then P2-E3's test
  set:
  - 200 half cues of stored items: the 100 oldest plus 100 random, with fixed masks;
  - 200 novel half cues of random independent items, as in P2-E3;
  - 200 full cues.
- **Reported cues.** 100 half cues of new exemplars (never stored) and 50 prototype half cues,
  in their own block after the gated cues.
- **Scoring.** P2-E3's code, unchanged.

## Kill test (gated seeds 21-25, all fresh; each seed runs once)

- **Gated condition:** s = 60, F = 10, at M = 500 and 1,000.
- **No calibration:** every value is frozen from P2-E2 and P2-E3.
- **The rule:** each part must hold on every gated seed at both loads.

| criterion | bar |
|---|---|
| **S1 memory index** | P2-E2's C1-C4, as P2-E3's D5 gated them, bars unchanged. **C1** recall >= 0.8 for >= 90 % of the 200 half cues. **C2** spurious < 0.5\|A\| for >= 90 %. **C3** novel ignition < 0.5 mean\|A\| for >= 90 % of the 200 novel cues. **C4** C1 and C2 within the oldest 100 items. |
| **S2 content** | P2-E3's joint (>= 40 of 50 missing lines regenerated, < 10 intrusions, 75 ms window) for >= 90 % of the 200 half cues |
| **S3 unlearned** | D3 (< 10 lines) for >= 90 % of the 200 random novel cues. This is a leak check: novel cues are independent items, so it cannot detect family contamination. Contamination of stored cues is carried by S2. |
| **S4 oldest** | the joint for >= 90 % of the 100 oldest items |

**C4 was missing from the draft and is restored.** The owner's ruling asks for the existing
criteria, and P2-E3 gated C1-C4.

**M = 1,000 is gated now,** as the draft and the owner's "ultimately 1,000" read it. Exploration
predicts failure there in the memory index itself. The owner may rule to gate M = 500 alone
before this contract is frozen.

## Validity (checked first; a failure on any gated seed makes the verdict INVALID)

1. At both loads, the forward store's sha256 equals plain P2-E1 learning on the same items (pin
   above).
2. The forward store, the feedback store and `vbar` are bit-identical before and after every
   test copy, by digest.
3. The mean eligible fraction is >= 0.95, and mean |A| is 18.5-21.5 at M = 1,000.
4. **Convergence, P2-E3's rule unchanged:** mean over cells of |vbar change| over the last 10 s
   of each settle <= 0.2 mV. Signed drift is reported beside it.
   - **The draft's signed rule is withdrawn.** Its |signed drift| <= 0.1 mV would have made
     P2-E3's own seed 14 INVALID (-0.110 mV). It would also have made the run INVALID with
     probability about 0.8.
   - Signed drift is a systematic tail that grows with the learning-time offset, plus a
     seed-level component.
5. **Shuffled feedback,** P2-E3's leak check, at M = 1,000. Each memory cell keeps its number of
   feedback synapses, with targets redrawn without replacement from all 4,000 lines
   (`stream(seed, 10, M)`), at the same J_fb* and g. It must fail the joint for at least 90 % of
   the half cues.
6. **Generator check:** the realised mean sibling overlap at s = 60 is 15-19 lines.

## Verdict (a vector plus labels)

- **The vector.** Pass or fail for each part, at each load, on each seed:
  - S1 as C1, C2, C3, C4-recall and C4-spurious;
  - S2, S3 and S4.
- **Labels.** INVALID takes precedence over every other label.

  | label | when |
  |---|---|
  | INVALID | a validity check fails on any gated seed |
  | PASS | every part holds on every seed at both loads |
  | STRUCTURED INDEX FAIL | any S1 part fails (the failing parts are named) |
  | STRUCTURED CONTENT FAIL | S2, S3 or S4 fails |

  Failure labels are joined; neither hides the other.
- **Run once.** Each gated seed runs once. A re-run needs the owner's ruling and keeps the first
  records.

## Reported arms and readings (predeclared; none can change the verdict)

Every reading below is computed by the verdict code from the records, by the rule stated here.

### A. Same-raster stores on the gated arm (both loads)

Each of these stores is replayed through the gated arm's own settled test raster. The memory
layer does not depend on the feedback store, so the comparison is exact.
- **main:** the responder-written store, `R(x) x E(x)`.
- **plateau-set:** `A(x) x E(x)`, the upper-bound diagnostic.
- **R_k:** written from the cells with at least k continuation spikes, for k = 2, 3, 4 and 6.
  R_1 is the main store, and its bit-identity is a validity check of the logging.
- **label-permuted:** x's responders write onto pi(x)'s eligible lines.

**The readout grid.** J_fb in {1.5, 2.0, 2.4, 2.8, 3.2, 3.6, 4.0, 5.0, 6.0} x g in {0, 0.3, 0.4, 0.5,
0.6, 0.7, 0.8, 1.0}, giving 72 points, run for the main, plateau-set and R_3 stores. For each
store and load the record holds:
- the value at the frozen point (2.8, 0.3);
- the best joint over the grid, labelled **optimistic** because it is selected on the same data;
- the number of grid points where S2, S3 and S4 all hold.

Other R_k stores are read at the frozen point only. **The upper bound** J_ub* is the plateau-set
store's best grid joint.

### B. Which failure is most consequential (the owner's 2026-10-11 guidance)

**Three losses, per seed and load,** as fractions of the 200 gated half cues:

| loss | definition | what it measures |
|---|---|---|
| L_c, contamination | J_ub* - J_own*, the grid-best joints of the plateau-set and main stores on the same raster | what an item-specific write would recover at the best readout |
| L_i, index | max(0, 0.90 - J_ub*) | the shortfall that remains even with an item-specific write: forward-index cross-talk (C2 and C4-spurious named beside it) |
| L_o, operating point | from the online arm's twin B: (cues passing index recall settled but failing online - the reverse) / n, over its gated-block half cues; also computed for the joint, and the larger is used | what continuous operation costs, on the same stored synapses |

- **A seed's dominant failure** is its largest loss if it exceeds the next by at least 0.05.
  Otherwise the seed is tied.
- **A load's reading**, exclusive and exhaustive:
  - **CONTAMINATION-DOMINANT,** **INDEX-DOMINANT** or **OPERATING-POINT-DOMINANT:** that
    failure dominates on at least 4 of 5 seeds;
  - **NO MATERIAL LOSS:** every loss is below 0.05 on at least 4 of 5 seeds, and no failure
    dominates;
  - **SPLIT:** otherwise. A SPLIT reading goes to the owner.
- **Material losses.** Each loss of at least 0.10 on at least 4 of 5 seeds is also named
  *material*. A material index loss is outside the owner's two named problems and goes to the
  owner before any mechanism contract.
- **NOT ATTRIBUTABLE.** Seeds where the s = 100 arm fails P2-E3's gate are excluded and marked
  NOT ATTRIBUTABLE. With fewer than 4 seeds left, the reading is NOT ATTRIBUTABLE.
- **The readings never override S1.** C2 and C4-spurious are reported beside them.

### C. Own-cell identity from the network's own activity (the owner's research target)

- **Measured per load,** over items in (M - 200, M]:
  - the distribution of continuation spike counts and first-spike ticks, for R(x) ∩ A(x)
    against R(x) \ A(x);
  - the count AUC, with ties counted as half.
- **The reading:**
  - **AVAILABLE FROM ACTIVITY** if, on every seed and load, the count AUC is >= 0.95 **and**
    the R_3 store's joint is within 0.05 of the plateau-set store's, both at the frozen point and
    at each store's grid best;
  - **NOT SHOWN** otherwise.
- **What it does not establish.** k = 3 is fixed in advance, because it mirrors the eligibility
  rule's count of 3 or more spikes. The reading is no mechanism and no adoption: an
  activity-gated write is a new mechanism with its own contract. Its ceiling at M = 1,000 is the
  index-limited upper bound.

### D. Contamination under continuous learning (the owner's request)

**The online arm.** P2-E4's frozen online driver (contract cd17cde, tree 9152f1e4), with only the
item generator replaced (s = 60, F = 10, the same items as the gated arm).
- It runs:
  - its main line to M = 1,000, with P2-E4's schedule;
  - P2-E4's block criteria at 500 and 1,000 (online C1-C3, joint, D3 and the never-probed cohort);
  - twin A at both loads, with store swaps on the same settled raster:
    - its own online-written store;
    - the gated arm's P2-E3-protocol store at the same load;
    - the plateau-set store;
  - twin B at both loads, a paired settled retest.
- **No habituation copies,** no stress continuation and no other P2-E4 arms.
- **Novel cues** are independent random items, as in P2-E4.

**The reading, per load.** Let Δ = J(online store) - J(P2-E3-protocol store) on the same twin A
raster:
- **WORSENS:** Δ <= -0.05 on at least 4 of 5 seeds;
- **NOT WORSE:** Δ >= -0.05 on at least 4 of 5 seeds;
- **MIXED:** otherwise.

L_o in B comes from this arm's twin B.

### E. Replication and the confounds of the item design

- **s = 100 (positive control).**
  - **REPLICATES** if P2-E3's gate holds at both loads on every gated seed: D1/2, D3, D4, and
    D5 = C1-C4.
  - **REPLICATION FAIL** otherwise. That is recorded as a replication failure and put to the
    owner; it does not change P2-E5's verdict.
  - This arm can come out either way.
- **Pooled control, per load:**
  - **CORRELATION-ATTRIBUTABLE** if the pooled arm passes S2 on at least 4 of 5 seeds while main
    fails;
  - **LINE-LOAD-LIMITED** if it fails S2 on at least 4 of 5 seeds;
  - **MIXED** otherwise.
- **F = 40, s = 80 and s = 40:** joint, D1, D2, D4 and C1-C4, at both loads, with the plateau-set
  store beside each.

### F. Where contamination lands (the gated arm, both loads)

- **Intrusions** under each half cue, split into exclusive classes:
  - prototype lines not in x;
  - lines only later siblings have;
  - lines only earlier siblings have;
  - lines both earlier and later siblings have;
  - other lines.

  Each class is also reported per line, normalised by its size, with a contamination ratio
  against the rate on other lines.
- **The own-cell share** of input to intrusion lines. This is the fraction of feedback inputs
  from memory cells that spiked at least 1 tick before the line's first spike and belong to
  A(x), rather than to spurious responders.
- **The label-permuted store:** the regenerated fraction of x's missing prototype lines and of
  its missing item-specific lines, main against permuted.
  - This arm cannot pass the joint even if regeneration were purely family-generic: x's
    missing half holds about 20 prototype lines and D1 needs 40. The draft's "could pass" is
    withdrawn.
  - The informative contrast is the item-specific fraction.

### G. Reported cue kinds (both loads, all arms on the P2-E3 protocol)

- **New exemplars** of known families, never stored. This measures **index cross-talk:** memory
  cells answering a family member that was never stored. For each cue:
  - memory responders;
  - total regenerated lines;
  - the fraction of its missing prototype lines regenerated;
  - the fraction of the prototype lines it lacks regenerated;
  - the fraction of its missing specific lines regenerated, which is a chance floor;
  - P(fewer than 10 lines).

  The joint criterion is unattainable here: about 30 of the 50 missing lines were never stored.
- **Prototype half cues:**
  - the missing-prototype fraction;
  - intrusions split into sibling-specific and other lines;
  - memory responders.

  **Labelled retrieval-time superposition.** Under ruling 5 it counts for nothing as learned
  abstraction, and it is not a Stage 3 result.

### Persistence (for exact same-raster replay by a later contract)

- **Saved for the gated arm at both loads** (gzip in `~/.cache/brain-sim/plant2/p2_e5/`, with
  the sha256 in the record):
  - per-cue outcomes;
  - E(x), A(x), R(x) and the continuation spike counts;
  - the learning-time memory raster;
  - the test memory raster.
- **Why it allows exact replay.** The memory layer does not depend on the feedback store. So a
  later feedback rule can be replayed exactly on these seeds' activity, as a reported arm beside
  that contract's own fresh gated seeds.
- **The quantities a correction must improve:** the per-seed joint, D4, and the normalised
  prototype and sibling intrusion rates. The bars stay unchanged.

## Power (computed before freezing; `analysis/p2e5_power.py`; record kind `power_reference`)

**Method.**
- Exact binomials with a logit-normal seed effect (SD 0.18), five seeds, both loads, using
  `plant2.power`.
- Independence across criteria is assumed, which is conservative.
- Rates are exploratory, from seeds 44-45.

| system | P(PASS S1-S4) | limiting parts |
|---|---|---|
| idealised: as item-specific on correlated items as P2-E3 is on independent items (pooled rates) | 0.856 | C1 at M = 1,000 (0.92), C4-recall at 1,000 (0.93) |
| idealised, P2-E3-only rates | 0.789 | C1 at 1,000 (0.84) |
| oracle write (plateau-set store at the frozen readout) on the structured index | 0.000 (0.000 at M = 500 alone) | M = 500: C2 0.07, C4-spurious 0.02, S2 0.66, S4 0.22 |
| main arm (exploratory rates) | 0.000 | S2 and S4 at both loads; C2 at both loads |

- **No item-specific write can pass on this index.** At M = 500, C2 (about 0.90) and
  C4-spurious (about 0.89) make S1 hold on all five seeds with probability 0.001, whatever the
  write. The gate therefore tests the index as well as the write at both loads. Part B ranks
  them.
- **P(INVALID)** under P2-E3's convergence rule is about 0.007. That uses a normal model of mean
  |dvbar| at M = 1,000 (mean 0.11, SD 0.03), whose largest exploratory value is 0.130. The
  other validity checks are deterministic and held on seeds 44-45.
- **The s = 100 replication** holds on all five seeds with probability about 0.86 at P2-E3's
  recorded rates.
- **Part B readings** (simulated from the grid-best joints, J_ub* 0.9975 and 0.59, J_own* 0.56
  and 0.025, with L_o unmeasured):

  | load | L_o of 0.07-0.25 | L_o of 0.35 | L_o of 0.45 | index loss material |
  |---|---|---|---|---|
  | M = 500 | CONTAMINATION-DOMINANT, P >= 0.997 | P = 0.57 (else SPLIT) | SPLIT, about 0.97 | P = 0 |
  | M = 1,000 | CONTAMINATION-DOMINANT, P = 0.986 | P = 0.985 | P = 0.79 | P = 1.0 |

  For scale, P2-E4's exploration on independent items had a net online index loss of 0.07 at
  M = 500 and 0.16-0.26 at M = 1,000.

## Predictions (from the red-team's exploration on seeds 44-45; the real driver's are appended later)

| criterion or arm | M = 500 | M = 1,000 |
|---|---|---|
| S1 | **fails**: C2 0.88-0.92, C4-spurious 0.86-0.92 (P(all seeds) 0.001); C1 0.95-0.98 | **fails**: C2 0.45-0.55, C4-spurious 0.35-0.47; C1 0.92-0.96 |
| S2 | **fails**: joint 0.08-0.17 (D1 >= 0.97, D2 0.1-0.2) | **fails**: about 0.00, median intrusions 1,500-1,900 |
| S3 | holds (>= 0.98) | holds (>= 0.98) |
| S4 | **fails**: <= 0.05 | **fails**: 0.00 |
| validity | holds | holds (P(INVALID) about 0.007) |
| plateau-set store, frozen point | 0.92-0.94 (D4 0.88-0.95) | 0.12-0.20 |
| plateau-set store, grid best (optimistic) | 0.995-1.000, 18-24 passing points | 0.585-0.600, no passing point |
| main store, grid best (optimistic) | 0.555-0.565, no passing point | 0.025, no passing point |
| R_3 store / count AUC | within 0.01 of plateau-set / >= 0.999 | within 0.01 of plateau-set / about 0.996 |
| Part B reading | CONTAMINATION-DOMINANT | CONTAMINATION-DOMINANT, with the index loss material (about 0.31) |
| Part C reading | AVAILABLE FROM ACTIVITY (both loads) | |
| Part D: online store / P2-E3-protocol store (twin A) | 0.05-0.07 against 0.10-0.15: WORSENS | WORSENS (both near 0) or MIXED |
| s = 100 | REPLICATES: joint 0.98-1.0, C1 0.94-0.97 | joint 0.98 |
| s = 80 | joint about 0.99-1.0 | **joint 0.6-0.75**, plateau-set 0.93-0.95, C2 about 0.94 |
| s = 40 | joint 0; C2 about 0.15 (the index collapses) | joint 0; C2 about 0.03 |
| pooled control | joint about 0.985: CORRELATION-ATTRIBUTABLE | joint about 0.10, C2 about 0.78: LINE-LOAD-LIMITED |
| F = 40 | joint about 0.77; plateau-set about 0.99 | joint about 0.05; C2 about 0.74; plateau-set about 0.85 |
| intrusions (main, M = 500, means) | prototype lines not in x about 36; later-sibling-only 40-48; earlier-sibling-only about 2.3; own-cell input share about 0.93 | own-cell share about 0.6 |
| label-permuted | item-specific missing fraction about 0.05 against 0.97-0.99 (main); prototype missing fraction about 0.8 | - |
| new exemplars | responders median about 1; 0 lines | responders 6-8; 110-250 lines, mostly prototype lines; specific lines at chance |
| prototype cues | 80-98 memory responders; about 800 lines | about 250 responders; about 3,500 lines |

**Expected labels:** STRUCTURED INDEX FAIL and STRUCTURED CONTENT FAIL at both loads. P(PASS) is
0. This is run anyway, as the owner ordered:
- the gated record is the baseline on fresh seeds;
- Parts B-D decide which contract comes next.

## Decision (predeclared)

- **On PASS.** Stage 1's structured-input clause is met for the P2-E3 system, under the settled
  protocol only, at s = 60 and F = 10.
  - Stage 1 still needs online memory (P2-E4) and capacity growth.
  - Any later change to the write re-passes the gates of P2-E3, P2-E4 and P2-E5 on fresh seeds.
- **On FAIL.**
  - It is recorded with its labels.
  - P2-E3's PASS stands, scoped to independent items and its protocol.
  - No parameter is retuned, and no Stage 2 work starts.
  - **The next step follows ruling 4, chosen from Part B's predeclared readings:**
    - **CONTAMINATION-DOMINANT** points to a write mechanism. The owner approved the
      error-correcting write as a research direction, not an assumed solution. Part C's
      activity-gated write is a second candidate, which needs the owner's ruling.
    - **A material index loss, or INDEX-DOMINANT,** goes to the owner before any mechanism
      contract. It is outside both named problems, and no feedback-write change can repair it.
    - **OPERATING-POINT-DOMINANT** points to the operating-point problem.
    - **SPLIT** goes to the owner.
  - **For any correction:**
    - the bars stay unchanged;
    - the plateau-set store is an upper-bound diagnostic, not a target or a solution;
    - no correction may read A(x);
    - a correction that changes store density must recalibrate its readout on a held-out seed
      by P2-E3's rule, or argue its frozen readout, before gating.
- **On INVALID.** It is recorded and reported to the owner. A re-run needs the owner's ruling.
- **On a REPLICATION FAIL** (s = 100). It is recorded as a replication failure on fresh seeds,
  and put to the owner. It does not reopen P2-E3 by itself.

## Order of runs on one seed

1. **The gated arm.**
   - Learn to 500, run the test copy, continue to 1,000, run the test copy.
   - Run the plain-E1 forward-store checks.
   - Save the persistence files.
   - Append `kill_test_seed`, the gated record, with the validity checks and the verdict vector.
2. **Same-raster diagnostics on the gated arm** (Parts A, C, F, G): grid, R_k, permuted store,
   intrusion classes, AUC and the reported cue kinds. Append them as one `reported_arm` record.
3. **The other arms,** each from step 1 and each its own `reported_arm` record, so that a crash
   voids only that arm: s = 100, s = 80, s = 40, pooled, F = 40, online.

**Cost.**
- Per seed, unloaded: about 1-1.5 h. The gated arm takes about 10 min, the grids about 20 min,
  the five P2-E3-protocol arms about 25 min, and the online arm about 15 min.
- Under two-lane contention, about 2 h per seed, so about 5 h for the five gated seeds.
- The gated seeds are scheduled after P2-E4's gated lanes finish.

## Seeds and guard

- **Seeds.**
  - Gated: 21-25.
  - Exploration: 44-45, already used by the red-team's scripts. The real driver's predictions on
    them are appended before any gated seed.
- **`--gated` refuses unless:**
  - plant2/ is committed;
  - the contract is unchanged since its frozen commit except for appended lines;
  - the frozen commit is an ancestor of HEAD;
  - HEAD's results file holds a P2-E5 `power_predictions` record with this contract's digest and
    plant2 tree.
- **Run-once markers** live in `~/.cache/brain-sim/plant2/p2_e5/`.

## Files

| file | contents |
|---|---|
| `plant2/experiments/p2_e5_structured.py` | the driver: a subclass of E3 for the P2-E3-protocol arms, and of P2-E4's `Online` for the online arm. E3 and P2-E4 are not edited. |
| `plant2/tests/test_p2_e5.py` | tests on seeds 90 and up: generator statistics, stream keys, identity of gated scores with and without the reported block, the R_1 store's bit-identity, labels, readings, guard |
| `analysis/p2e5_power.py` | the power reference (outside plant2/ while P2-E4's tree is frozen) |
| `bench/results/plant2.jsonl` | records, append-only: `power_reference`, `exploration_seed`, `power_predictions`, `kill_test_seed`, `reported_arm`, `kill_test_verdict` |
