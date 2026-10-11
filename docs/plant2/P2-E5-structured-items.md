# P2-E5: item-specific recall on correlated inputs (structured-input diagnostic)

**Revised after the red-team and after verification. Not yet frozen.** No P2-E5 code exists.
Gated seeds 21-25 have not been touched.

- **The red-team.** The draft (commit e736e81) was reviewed by three critics, each with a
  refuter, plus a completeness critic. Their findings are verbatim in
  `review/plant2/P2-E5/redteam-*.md`.
- **Verification.** The first revision (4846de0) was checked by three verifiers (numbers and
  power, coverage, implementation ambiguity), recorded verbatim in
  `review/plant2/P2-E5/verify-*.md`.
- **Dispositions.** Every finding's disposition is a row in `review/ledger.jsonl`.
- **Exploratory numbers** below come from the red-team's and verifiers' scripts on seeds 44-45,
  and are labelled as such. Where a number rests on one seed or one lens, the text says so.
- **Before freezing:** the power reference record (`analysis/p2e5_power.py --append`).
- **After implementation:** predictions from the real driver on seeds 44-45 are appended, and
  committed before any gated seed.
- **Timing.** Implementation waits until P2-E4's gated seeds 16-20 have finished, because the
  plant2 tree is frozen while they run.

**Ordered by the owner** (`DECISIONS.md`):
1. **Run the existing system first, with no new mechanism,** as a new Stage 1 gate (rulings of
   2026-10-10, items 1 and 4):
   - about 16 % sibling overlap;
   - M = 500 and ultimately 1,000;
   - fresh seeds;
   - diagnostic arms at lower and higher overlap.
2. **If it fails, investigate the responder write** (ruling 4). The plateau-set store is an
   **upper-bound diagnostic, not an acceptable solution** (guidance of 2026-10-11). The goal is a
   network that finds which of its own active cells represent the experience, without being
   handed A(x).
3. **Any correction is a separately contracted single mechanism** (ruling 4). Familiarity-gated
   allocation stays deferred.
4. **Two separate problems,** fixed one at a time: learning-time contamination and
   operating-point instability. Put first whichever matters most under the structured-input
   tests (guidance of 2026-10-11).
5. **Test whether contamination worsens under continuous learning,** without adding a second
   mechanism (the owner's comments on P2-E4's exploration, addendum in `DECISIONS.md`).
6. **The owner's later hypothesis** (2026-10-11): an active memory cell should not automatically
   qualify to write an experience's content. One candidate is a local eligibility tied to a
   genuine plateau event. That hypothesis is **for after P2-E4 and P2-E5**. P2-E5 adopts no
   mechanism. Its Part C only measures whether the network's own activity carries the needed
   information.

The capacity-scaling experiment takes the next free number when its contract is written.

## Why this test

- **Every gated item so far was an independent random pattern,** with about 2.5 % pairwise
  overlap. Stage 2's shared items and Stage 3's exemplars are correlated by definition.
- **What exploration shows** (exploratory, not results). The frozen P2-E3 system on exemplars of
  10 never-shown prototypes, siblings sharing about 17 of 100 lines (s = 60), with ranges over
  seeds 44-45 and two independent implementations:

  | measure | M = 500 | M = 1,000 |
  |---|---|---|
  | content joint, main store | 0.10-0.145 | 0.000 |
  | same raster, plateau-set store, frozen readout | 0.925-0.94 | 0.12-0.18 |
  | memory C2 (spurious) | 0.895-0.92 | 0.465-0.495 |
  | memory C4, spurious part (oldest 100) | 0.86-0.92 | 0.35-0.47 |

- **How the content store is contaminated.** This corrects the draft and
  `EVAL-after-P2-E3.md` (see its erratum).
  - The write sets `w_fb(i -> j) = 1` for every responder i in R(x) and eligible line j in E(x).
  - At s = 60, x's encoding drives cells of earlier siblings' assemblies through their shared
    prototype lines. So R(x) holds those cells as well as A(x). |R| is about 72-76 for items
    400-500, against |A| of about 20, and 151-164 for items 900-1,000. The extra responders
    number about 52-57 and 131-143, and 99.7 % of them belong to earlier siblings.
  - **Those cells receive x's lines.** Later, when a sibling y's half cue drives them, they
    regenerate x's lines into y's readout. So an item is damaged after it is stored, by later
    siblings writing onto its cells. At M = 500, y's intrusions average:
    - 40-48 lines that only later siblings have;
    - 2.3-2.4 lines that only earlier siblings have;
    - about 36 prototype lines that y lacks.
  - The oldest items are hit hardest: D4 is 0.01-0.05, against a joint of 0.10-0.145.
  - Regeneration of the item's own missing lines still holds (D1 0.98-1.0). **At M = 500 the
    content failure is entirely intrusions (D2).**
- **The forward index fails too, upstream of any feedback write.**
  - Spurious memory cells number about 2.9 per half cue at M = 500 and about 19 at M = 1,000
    (seed 44). 98 % are plateau cells of at least one sibling, carrying about 9 prototype lines
    from the cue.
  - At M = 500, C2 and C4-spurious already sit at about 0.90.
  - At M = 1,000 the plateau-set store fails at every point of a 72-point readout grid. Its best
    joint is 0.60 on seed 44 and TBD45 on seed 45.
  - No change to the feedback write can affect C1-C4. This is forward-index cross-talk on
    correlated items, a third problem **outside the owner's two named problems**.
- **Own-cell identity is in the network's activity** (completeness critic, C4; seed 44 at both
  loads, seed 45 at M = 500).
  - During the continuation, A(x)'s cells fire about 5 spikes in 50 ms at M = 500 and about 3.9
    at M = 1,000. Sibling responders fire about 1.05, and 94 % of them fire exactly once.
  - The count separates the two with AUC 0.996-0.9996.
  - A store written only from cells with at least 3 continuation spikes reproduces the
    plateau-set store's content numbers at both loads. Sparser ones (at least 4 or 6 spikes) do
    better than the plateau-set store at M = 1,000.
  - This bears on the owner's hypothesis. It is measured here and adopted nowhere.
- **The owner's objective.** Remember previously experienced correlated items without
  contamination. **Generalisation to never-seen family members is not measured here.** It
  belongs to Stage 3. The new-exemplar and prototype cues below measure index cross-talk and
  retrieval-time superposition, not generalisation.

## Hypothesis (the one the existing system is expected to fail)

The frozen P2-E3 system, under P2-E3's settled protocol, stores exemplars of related families
item-specifically:
- about 16 % sibling overlap;
- F = 10 families;
- M = 500 and 1,000.

From a half cue it regenerates the item's own missing lines, item-specific ones included, with
few intrusions from the prototype or from siblings. Its memory index stays specific. Precisely,
criteria S1-S4 hold on every gated seed at both loads.

**Scope.**
- **Two learning rhythms have been examined for the responder write on structured items:**
  - P2-E3's back-to-back protocol (`quiet()` between items);
  - the P2-E4 red-team's exploratory online line (250 ms interval with probes; not P2-E4's
    frozen driver).
- **The settled protocol was the more favourable of the two.** The online line left more
  continuation responders (|R| 105-111 against 72-75 at M = 500) and a lower settled joint
  (0.055-0.065 against 0.105-0.145 on the same items).
- **A PASS** is therefore scoped to the settled protocol.
- **A FAIL** is not an artefact of a hostile operating point.
- **The joint condition** (structured and online) is reported here (Part D), not gated.

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
  - the readout and scoring code;
  - P2-E3's validity rules, including convergence (mean |dvbar| <= 0.2 mV) and its shuffled
    leak check.
- **Only the item distribution changes.** P2-E4 isolates online operation, and this experiment
  isolates input structure.
- **Reported arms** examine the joint condition (Part D) and the confounds of the item design
  (Part E).

## Items

- **Prototypes.** F random sets of 100 of the 4,000 lines, never shown.
- **An exemplar** of family f keeps `100 - s` of the prototype's lines and adds `s` lines from
  outside it. The draws are pinned below.
- **Learning order.** Item k (k = 1, 2, ...) belongs to family k mod F, so every family is
  represented at every age. Exploration found learning order (cyclic or random) changes
  nothing: frozen-point joint 0.130 against 0.140 (seed 44).
- **Sibling overlap.** Two siblings share about (100 - s)^2 / 100 prototype lines plus chance
  overlap. At s = 60 that is 16.9 lines over all within-family pairs (verifier, seeds 90-92).
- **F = 10, fixed by argument.**
  - The owner's ruling fixes sibling overlap, not family size.
  - With F fixed, family size grows with load: 50 exemplars per family at M = 500, 100 at
    M = 1,000. This is the regime of a learner accumulating exemplars of a fixed set of kinds,
    and where the exploratory collapse was found.
  - **Confounds.** Correlation, family size and per-line load move together. Prototype lines
    carry about 29 items at M = 500 and 58 at M = 1,000; for independent items the figure is
    12.5 and 25. Two reported arms separate them: a line-frequency-matched pooled control, and
    F = 40.

| arm | s | F | sibling overlap | role |
|---|---|---|---|---|
| **main** | 60 | 10 | about 17 % | **gated** |
| low overlap | 80 | 10 | about 4-6 % | reported (owner's diagnostic arm) |
| high overlap | 40 | 10 | about 36 % | reported (owner's diagnostic arm) |
| independent items | P2-E3's own generator | - | about 2.5 % | reported; P2-E3 replication on fresh seeds (positive control) |
| pooled control | 60 (prototype share drawn from the union of the 10 prototypes) | 10 | about 3.7 % | reported; same per-line loads as main, no sibling correlation |
| F = 40 | 60 | 40 | about 17 % | reported; families of 12-25, roughly uniform line load |
| online | 60 | 10 | about 17 % | reported; learning on P2-E4's frozen online driver |

**Pairing.** Plateaus come from P2-E1's plateau stream (n uniforms per item, whatever the
content), so A(k) is identical across arms for every item k. Only the content differs. Every arm
records a digest of its A lists.

### Streams and draws (P2-E5 owns ids 20-24; every other stream is P2-E1's, P2-E3's or P2-E4's, unchanged)

**General rules.**
- `stream(seed, id, *extra)` is P2-E1's helper (`default_rng([seed, id, ...])`).
- The exemplar index k starts at 1. k = 0 is forbidden, because SeedSequence pads with zeros
  and (seed, 21, F, 0) would alias (seed, 21, F).
- Every line set is sorted after drawing.

| key | draws, in order |
|---|---|
| (seed, 20, F) | for f = 0..F-1: `P_f = sort(r.choice(4000, 100, replace=False))` |
| (seed, 21, F, k) | f = k mod F; `pp = r.permutation(P_f)`; `po = r.permutation(setdiff(arange(4000), P_f))`; the exemplar is `sort(concat(pp[:100-s], po[:s]))`. Arms with the same F share these draws, so their kept sets are nested. |
| (seed, 23, k) | pooled control. U = the union of P_0..P_9 (F = 10). `d = r.choice(U, 100-s, replace=False)`; `pool = setdiff(arange(4000), union(P_(k mod 10), d))`; the exemplar is `sort(concat(d, r.choice(pool, s, replace=False)))`. |
| (seed, 22, M) | the reported cue block at load M, one generator used in order. (i) For j = 0..99, a new exemplar of family j mod F, drawn as for (seed, 21) but from this generator, with a mask `sort(r.choice(100, 50, replace=False))` indexing the sorted exemplar. (ii) For j = 0..49, a prototype cue of family j mod F, with a mask drawn the same way. (iii) The same generator is then passed to `present()`, with the 100 new-exemplar cues in draw order followed by the 50 prototype cues. |
| (seed, 24, M) | pi for the label-permuted store: for f = 0..F-1, `p = r.permutation(idx_f)` over the stored items of family f, redrawn until it has no fixed point |

**Pins.**
- **The P2-E3-protocol arms are `e3.E3` with `learn_one` not overridden.**
  - The subclass's `learn_one` temporarily replaces `self.net.step` with a read-only wrapper.
    The wrapper calls the original and appends the returned memory spikes; it makes no draws
    and changes no state.
  - It then calls `super().learn_one()`, and deletes the wrapper before returning, so deep
    copies never carry it.
  - The learning raster, the continuation spike counts and the first-spike ticks come from the
    captured steps. The continuation is the last 50 `step` calls of the episode, loop index
    t = 0..49.
- **Plain P2-E1 learning on the same items.** The generator is injected into a plain E1
  (`plain._pat`), so the forward-store check tests the encoding path, not the generator.
- **Gated scores** come from P2-E3's `readout` and `score`, on the first 600 onsets (200 half,
  200 novel and 200 full cues) and the raster truncated at the end of the gated `present()`
  calls.
- **The reported block** is a separate `present()` call after the gated cues, so it cannot
  change a gated score. A unit test checks this identity. The persisted test raster is the full
  raster, with the gated tick count recorded.
- **Every threshold on a fraction of 200 cues** is applied to integer cue counts (a fraction f
  is `round(200 f)`): 0.05 is 10 cues and 0.10 is 20 cues. A ratio threshold is applied as
  stated.

## Test (P2-E3's protocol, at each load)

- **Learning and test.** Learning runs to M. A deep copy gets the 50 s settle, then P2-E3's test
  set:
  - 200 half cues of stored items: the 100 oldest plus 100 random, with fixed masks (P2-E3's
    code);
  - 200 novel half cues of random independent items (P2-E3's code);
  - 200 full cues.
- **The reported block** follows (Part G).

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

**M = 1,000 is gated now,** as the draft and the owner's "ultimately 1,000" read it. The owner
may rule to gate M = 500 alone before this contract is frozen.

**P2-E3 addendum item 8** asks that, from P2-E4 on, a gated control could pass if the claim were
false. **It is not met here, and that is stated rather than hidden.**
- The claim is item-specific storage of correlated items, and it is predicted to fail.
- The shuffled leak check cannot pass on this distribution.
- The control that can come out either way is the s = 100 replication (Part E), which is
  reported.
- On a PASS, the label-permuted store's item-specific fraction (Part F) is the specificity
  check. A PASS whose permuted store regenerated x's item-specific missing lines at more than
  half the main store's rate would go to the owner before any Stage 1 claim.

## Validity (checked first; a failure on any gated seed makes the verdict INVALID)

1. At both loads, the forward store's sha256 equals plain P2-E1 learning on the same items (pin
   above).
2. **Test copies:**
   - (a) on each test copy, the forward and feedback stores are bit-identical before the settle
     and after the last `present()` call, the reported block included (P2-E3's
     `stores_unchanged_by_tests`);
   - (b) the main line's forward store, feedback store and `vbar` are bit-identical before the
     copy is made and after its test.
3. The mean eligible fraction is >= 0.95, and mean |A| is 18.5-21.5 at M = 1,000.
4. **Convergence, P2-E3's rule unchanged:** mean over cells of |vbar change| over the last 10 s
   of each settle <= 0.2 mV. Signed drift is reported beside it.
   - **The draft's signed rule is withdrawn.** Its |signed drift| <= 0.1 mV would have made
     P2-E3's own seed 14 INVALID (-0.110 mV), and this run INVALID with probability about 0.8.
5. **Shuffled feedback, P2-E3's rule unchanged:** the shuffled store's joint is < 0.90 at
   M = 1,000.
   - Each memory cell keeps its number of feedback synapses, with targets redrawn without
     replacement from all 4,000 lines (`stream(seed, 10, M)`), at J_fb* and g.
   - It is labelled a leak check that cannot fail on this distribution. P2-E3's rationale for it
     ("each responder reaches about 13 % of lines, below g") no longer holds at a feedback
     density of about 0.31, but the shuffled store still fails through intrusions.
6. **Generator check:** the realised mean |x ∩ y| over all within-family pairs among items
   1-1,000 of the gated arm is 15-19 lines.
7. **The write is P2-E3's,** at both loads:
   - R(x) equals the cells with at least 1 captured continuation spike, for every x;
   - the feedback store equals the union of R(x) x E(x) (P2-E4's `fb_union_ok` rule);
   - the R_1 store's sha256 equals the main store's.

## Verdict (a vector plus labels)

- **The vector.** Pass or fail for each part, at each load, on each seed:
  - S1 as C1, C2, C3, C4-recall and C4-spurious;
  - S2, S3 and S4.
- **Labels.** INVALID takes precedence over every other label.

  | label | when |
  |---|---|
  | INVALID | a validity check fails on any gated seed |
  | PASS | every part holds on every seed at both loads |
  | STRUCTURED INDEX FAIL | any S1 part fails (the failing parts and loads are named) |
  | STRUCTURED CONTENT FAIL | S2, S3 or S4 fails (the failing parts and loads are named) |

  Failure labels are joined; neither hides the other.
- **Run once.** Each gated seed runs once. A re-run needs the owner's ruling and keeps the first
  records.

## Reported arms and readings (predeclared; none can change the verdict)

Every reading below is computed by the verdict code from the records, by the rule stated here.
A reported arm that crashes or fails its own validity checks voids only that arm, and the
readings that need it.

### A. Same-raster stores on the gated arm (both loads)

Each store is replayed through the gated arm's own settled test raster. The memory layer does not
depend on the feedback store, so the comparison is exact.
- **main:** the responder-written store, `R(x) x E(x)`.
- **plateau-set:** `A(x) x E(x)`, the **plateau-set reference.** It is an upper-bound diagnostic
  in the owner's sense, not an upper bound in principle: sparser activity-selected stores do
  better at M = 1,000.
- **R_k:** written from the cells with at least k continuation spikes, for k = 2, 3, 4 and 6.
  R_1 is the main store (validity 7).
- **label-permuted:** x's responders write onto pi(x)'s eligible lines.

**The readout grid.**
- J_fb in {1.5, 2.0, 2.4, 2.8, 3.2, 3.6, 4.0, 5.0, 6.0} x g in {0, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8,
  1.0}, giving 72 points, using P2-E3's `readout` with arrays of J and g.
- It is run for the main, plateau-set and R_3 stores. The other R_k stores are read at the frozen
  point.
- **The grid best** of a store is the maximum joint (the S2 fraction) over the 72 points, with no
  condition on D3 or D4. Ties go to the first maximum in grid order (J ascending, then g
  ascending).
- **For each store and load the record holds:**
  - the value at the frozen point (2.8, 0.3);
  - the grid best, with its (J_fb, g) and D1-D4 there. The grid best is labelled
    **optimistic,** because it is selected on the same data;
  - the number of grid points where S2, S3 and S4 all hold.
- **J_ub\*** is the plateau-set store's grid best and **J_own\*** the main store's.

### B. Which failure is most consequential (the owner's 2026-10-11 guidance)

**Three losses, per seed and load, in cues** (clipped at 0):

| loss | definition | population |
|---|---|---|
| L_c, contamination | min(J_ub\*, 180) - min(J_own\*, 180), the grid-best joints in cues of 200, each capped at the 180-cue bar | the gated arm's 200 half cues |
| L_i, shortfall with an item-specific write | 180 - J_ub\*: index cross-talk plus the plateau-set store's own limits (C2 and C4-spurious named beside it) | the gated arm's 200 half cues |
| L_o, operating point | from the online arm's `twin_B(...)["all"]` at that load: the larger of (settled pass - online pass) for memory recall and for the joint, as McNemar discordant counts (pass settled and fail online, minus the reverse) | the online arm's 200 block half cues (50 recent, 50 uniform, 100 cohort), at P2-E4's frozen readout |

**Conventions.**
- L_c uses grid bests, because any write correction changes store density and must recalibrate
  its readout (Decision).
- L_c at the frozen point is reported beside it.
- L_o is measured on the online system's own cues and frozen readout, because that is the
  operating point in question.
- The three losses are therefore comparable only as cue counts lost to each failure. The
  readings are stated in those terms.

**Attributable seeds, per load.** A seed is NOT ATTRIBUTABLE at a load in either case:
- the s = 100 arm fails P2-E3's gate there (D1/2, D3, D4, C1-C4), or fails its validity checks
  1-4 there;
- the online arm is void or invalid there.

**A seed's dominant failure** at a load is X if L_X >= 20 cues (material) and L_X exceeds both
other losses by at least 10 cues. Otherwise none dominates.

**A load's reading,** exclusive and exhaustive, in this order:
- **NOT ATTRIBUTABLE:** fewer than 4 attributable seeds;
- **CONTAMINATION-DOMINANT,** **INDEX-DOMINANT** or **OPERATING-POINT-DOMINANT:** X dominates on
  at least 4 of the attributable seeds;
- **NO MATERIAL LOSS:** every loss is below 20 cues on at least 4 of the attributable seeds;
- **SPLIT:** otherwise.

**Also reported:**
- each loss that is at least 20 cues on at least 4 attributable seeds, named *material*;
- S1's verdict parts, beside the readings, never overridden by them.

### C. Own-cell identity from the network's own activity (the owner's research target)

- **Population.** The gated arm (s = 60, F = 10), at each load. For each item x in (M - 200, M],
  1-based:
  - positives are the cells of R(x) ∩ A(x);
  - negatives are the cells of R(x) \ A(x).
- **The measure.**
  - A cell's count is its number of spikes in the 50 continuation steps, and its first-spike
    tick is the first such t.
  - The AUC is computed once over all positive-negative pairs pooled across the 200 items:
    P(count_pos > count_neg) + 0.5 P(count_pos = count_neg).
  - The record also holds both count distributions and the first-spike AUC.
- **The reading** (one-sided):
  - **AVAILABLE FROM ACTIVITY** if, on every seed and load, the count AUC is >= 0.95 **and**
    J(R_3) >= J(plateau-set) - 10 cues, both at the frozen point and at each store's grid best;
  - **NOT SHOWN** otherwise.
- **The online arm** reports the same count AUC, from the same read-only wrapper. Its R_3 store is
  not swapped into twin A: P2-E4's frozen `twin_A` does not expose its raster.
- **What it does not establish.** k = 3 is fixed in advance, because it mirrors the eligibility
  rule's 3 or more spikes. The reading is no mechanism and no adoption: an activity-gated write
  is a new mechanism with its own contract and the owner's ruling.

### D. Contamination under continuous learning (the owner's request)

**The online arm.** P2-E4's frozen driver (contract cd17cde, tree 9152f1e4), with `e4.CONTRACT`
unchanged and only the item generator replaced. It uses s = 60 and F = 10, with the same items
as the gated arm. Novel cues come from P2-E4's own stream and stay independent items.
- **The generator** exposes a `bit_generator` attribute with a hashable state, so P2-E4's
  `state_digest` works.
- **Reused unchanged:** `Online.run_to` with P2-E4's schedule to M = 1,000; `block_criteria` at
  500 and 1,000; `twin_A(S, M, ref_store)` with `ref_store` set to the gated arm's feedback
  store at the same load; and `twin_B` on twin A's settled copy.
- **Not run:** habituation copies, the stress continuation and P2-E4's other arms.
- **Validity of the arm, per load:**
  - `fwd_equals_p2e1`, against a plain E1 with the same injected generator;
  - the eligible fraction and mean |A|;
  - `fb_union_ok`, `slot_checks_ok`, `audit_ok` and `leak_ok`;
  - the twins leave the main line untouched.

  A failure voids that load's Part D reading and L_o on that seed.

**The reading, per load,** on twin A's raster (the same settled half cues for both stores):
- R = (median intrusions of the online-written store + 1) / (median intrusions of the
  P2-E3-protocol store + 1), from each store's `intrusions_median`.
- **WORSENS:** R >= 1.25 on at least 4 of the valid seeds;
- **NOT WORSE:** R < 1.10 on at least 4 of the valid seeds;
- **NOT ESTIMABLE:** fewer than 4 valid seeds;
- **MIXED:** otherwise.

**Also reported:**
- the joints of the online-written, P2-E3-protocol and plateau-set stores on the same raster,
  and their difference. The joint difference is labelled **AT FLOOR** on a seed where the
  P2-E3-protocol store's joint is below 20 cues. That is why the reading uses intrusions;
- the online block criteria (online C1-C3, joint, D3 and the cohort), the McNemar counts of
  twin B, and |R| and the continuation offset by age.

### E. Replication and the confounds of the item design

- **s = 100 (positive control).** Validity checks 1-4 apply to it.
  - **REPLICATES** if P2-E3's gate holds at both loads on every gated seed: D1/2, D3, D4, and
    D5 = C1-C4.
  - **REPLICATION FAIL** otherwise. It is recorded as a replication failure and put to the owner.
  - It does not change P2-E5's verdict, and it can come out either way.
- **Pooled control, per load:**
  - **CORRELATION-ATTRIBUTABLE** if the pooled arm passes S2 on at least 4 of 5 seeds while main
    fails;
  - **LINE-LOAD-LIMITED** if the pooled arm fails S2 on at least 4 of 5 seeds;
  - **MIXED** otherwise.

  The overlap dose-response is read only beside this control.
- **F = 40:** reported values only, with no reading. It shows whether the family-size and
  line-load picture changes with roughly uniform line load.
- **Dose-response** (s = 80, 60 and 40 at both loads): the joint per item on the same item
  indices (A identical), with exact McNemar counts for 80 against 60 and 60 against 40 over the
  200 gated half cues.
- **Every P2-E3-protocol arm** also reports joint, D1, D2, D4 and C1-C4, with the plateau-set
  store beside each.

### F. Where contamination lands (the gated arm, both loads)

- **Intrusions** under each half cue, for the main **and** the plateau-set store, split into
  exclusive classes:
  - prototype lines not in x;
  - lines only later siblings have;
  - lines only earlier siblings have;
  - lines both earlier and later siblings have;
  - other lines.

  Each class is reported as a mean, a median and a per-line rate normalised by class size, with
  a contamination ratio against the rate on other lines. The intrusion ratio of the main store
  to the plateau-set store is reported at M = 1,000.
- **The own-cell share,** computed per half cue:
  - For each intrusion line j, the candidate synapses are the feedback synapses i -> j whose
    memory cell i first spiked in [onset, onset + 75) at least 1 tick before j's first spike
    (as in `analysis/p2e4_diagnosis.py`).
  - The share is the number of candidate synapses with i in A(x), divided by all candidate
    synapses, pooled over the cue's intrusion lines.
  - Median and mean over cues with intrusions.
- **Spurious memory cells** under each half cue: the cells outside A(x) that spike within 50 ms.
  - For each, the share that are plateau cells of at least one sibling;
  - and the number of strong forward synapses from the cue's lines, split into prototype and
    item-specific lines.
- **The label-permuted store:** the regenerated fraction of x's missing prototype lines and of
  its missing item-specific lines, main against permuted.
  - This arm cannot pass the joint even if regeneration were purely family-generic: x's missing
    half holds about 20 prototype lines and D1 needs 40.
  - The informative contrast is the item-specific fraction.

### G. Reported cue kinds (both loads)

- **Which arms.** The gated arm and the s = 80, s = 40 and F = 40 arms, each with its own block
  from (seed, 22, M). F = 40 uses families j mod 40 for both cue kinds.
- **The pooled and s = 100 arms** are presented the gated arm's block (F = 10, s = 60 cues), and
  report only memory responders and total lines.
- **New exemplars** of known families, never stored. They measure **index cross-talk** (memory
  cells answering a family member that was never stored) and false recall. **This is not
  generalisation.** Prototype lines regenerated from a new exemplar are retrieval-time
  superposition (ruling 5). Per cue:
  - memory responders;
  - total regenerated lines;
  - the fraction of its missing prototype lines regenerated, and of the prototype lines it
    lacks;
  - the number of regenerated lines that belong only to stored siblings (false recall);
  - the fraction of its missing specific lines regenerated, which is a chance floor;
  - P(fewer than 10 lines).

  The joint is unattainable here: about 30 of the 50 missing lines were never stored.
- **Prototype half cues:**
  - the missing-prototype fraction;
  - intrusions split into sibling-specific and other lines;
  - memory responders.

  **Labelled retrieval-time superposition.** Under ruling 5 it counts for nothing as learned
  abstraction.

### Persistence (for exact same-raster replay by a later contract)

- **Saved for the gated arm at both loads** (gzip in `~/.cache/brain-sim/plant2/p2_e5/`, with
  the sha256 in the record; a few MB per seed):
  - per-cue outcomes;
  - E(x), A(x), R(x), and the continuation counts and first-spike ticks;
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
- **Rates** are the mean of four exploratory runs: two lenses on seeds 44 and 45.
- **Grid bests** come from the completeness lens's grid on seed 44 and the lead's run of the same
  script on seed 45, both in cyclic order.
- **Independence across criteria** is assumed. That is conservative for pass probabilities near
  1, not for near-zero ones. For S1 a dependent model is also given: one seed effect, and C4
  scored on the oldest 100 of C2's cues.

TBD-POWER

## Predictions (from exploration on seeds 44-45; the real driver's are appended later)

TBD-PRED

**Expected labels:** STRUCTURED INDEX FAIL and STRUCTURED CONTENT FAIL at both loads.
- **P(PASS):** below 10^-6 at the exploratory rates, as an analytic product of the criteria.
  This is not an impossibility.
- **Why run it anyway,** as the owner ordered:
  - the gated record is the baseline on fresh seeds;
  - Parts B-D decide which contract comes next.

## Decision (predeclared)

- **On PASS.** Stage 1's structured-input clause is met for the P2-E3 system, under the settled
  protocol only, at s = 60 and F = 10.
  - Stage 1 still needs online memory (P2-E4) and capacity growth.
  - The PASS is subject to the specificity check under "Kill test".
- **On FAIL.**
  - It is recorded with its labels.
  - P2-E3's PASS stands, scoped to independent items and its protocol.
  - No parameter is retuned, and no Stage 2 work starts.
  - **What goes to the owner before any mechanism contract:**
    - **Any STRUCTURED INDEX FAIL,** at either load, with Part B's readings beside it. A
      write-only correction cannot pass S1 on this index, so the index failure is the owner's
      to place.
    - **Any reading of INDEX-DOMINANT, SPLIT, NO MATERIAL LOSS or NOT ATTRIBUTABLE,** and any
      disagreement between the two loads' readings.
  - **Where Part B reads CONTAMINATION-DOMINANT** at both loads, a write mechanism is the
    candidate:
    - the owner's approved research direction, the error-correcting write. Its contract must
      test whether the regenerated content carries useful error information, and whether
      corrections preserve unrelated memories (ruling 4);
    - Part C's activity-gated write, if the owner rules it in;
    - the owner's plateau-eligibility hypothesis of 2026-10-11, if the owner rules it in.
  - **Where Part B reads OPERATING-POINT-DOMINANT** at both loads, the operating-point problem is
    the candidate.
  - **Familiarity-gated allocation** stays deferred.
- **For any correction:**
  - the bars stay unchanged;
  - the plateau-set store is an upper-bound diagnostic, not a target or a solution;
  - no correction may read A(x);
  - a correction that changes store density must recalibrate its readout on a held-out seed by
    P2-E3's rule, or argue its frozen readout, before gating.
- **Which gates a single-mechanism contract must pass** is set when that contract is proposed.
  - It gates the problem it targets.
  - It re-runs the P2-E3, P2-E4 and P2-E5 protocols on fresh seeds, reported against these
    records.
  - Stage 1 is complete only when one system passes all three gates.
- **On INVALID.** It is recorded and reported to the owner. A re-run needs the owner's ruling.
- **On a REPLICATION FAIL** (s = 100). It is recorded as a replication failure on fresh seeds and
  put to the owner. It does not reopen P2-E3 by itself.

## Order of runs on one seed

1. **The gated arm.**
   - Learn to 500, run the test copy, continue to 1,000, run the test copy.
   - Run the plain-E1 forward-store checks.
   - Save the persistence files.
   - Append `kill_test_seed`, the gated record, with validity checks 1-7 and the verdict vector.
2. **Same-raster diagnostics on the gated arm** (Parts A, C, F, G): grid, R_k, permuted store,
   intrusion classes, spurious cells, AUC and the reported cue kinds. Append them as one
   `reported_arm` record.
3. **The other arms,** each from step 1 and each its own `reported_arm` record: s = 100, s = 80,
   s = 40, pooled, F = 40, online.

**Cost.** About 45-55 min per seed unloaded (verifier's estimate from recorded wall times), so
the contract's allowance of 1-1.5 h has margin. Under two-lane contention it is about 1.5-2 h
per seed, about 5 h for the five gated seeds. Peak memory is about 1.5-2.5 GB per lane. The gated
seeds are scheduled after P2-E4's gated lanes finish.

## Seeds and guard

- **Seeds.**
  - Gated: 21-25.
  - Exploration: 44-45, already used by the red-team's and verifiers' scripts. The real driver's
    predictions on them are appended before any gated seed.
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
| `plant2/tests/test_p2_e5.py` | tests on seeds 90 and up: generator statistics and stream keys (k >= 1), the reported block leaving gated scores identical, the read-only wrapper leaving the stores identical to unmodified E3, validity 7, labels, Part B-E readings on synthetic records, guard |
| `analysis/p2e5_power.py` | the power reference (outside plant2/ while P2-E4's tree is frozen) |
| `bench/results/plant2.jsonl` | records, append-only: `power_reference`, `exploration_seed`, `power_predictions`, `kill_test_seed`, `reported_arm`, `kill_test_verdict` |
