# Evaluation after P2-E3: does content completion move plant2 toward sequences, abstraction and problem solving?

Written 2026-10-10, at the owner's request ("After completing P2-E3, evaluate whether the new
capability meaningfully advances us toward sequences, abstraction, and eventually independent
problem-solving").

**Sources:**
- the P2-E3 Result and its review addendum (`docs/plant2/P2-E3-content-completion.md`);
- four independent reviews (`review/plant2/P2-E3/`), two of them through a north-star lens,
  one constructive and one skeptical;
- one replication I ran of an exploratory check.

Exploratory numbers are labelled as such. They are not results.

## Short answer

**Not yet as evidence; yes as a piece of plumbing that later stages need.**
- **What P2-E3 adds.** It is the first readout in input coordinates: a half cue regenerates the
  rest of the stored input, one-shot, in 23-28 ms, with few intrusions. Sequences (reading out
  the next item), replay, prediction and any comparison of expectation against input all need
  this.
- **What it does not add is learning power.**
  - The system stores each input verbatim under a random key and looks it up: a spiking
    Willshaw hetero-associative memory.
  - It was tested only on independent random items, on frozen copies after a 50 s rest.
  - Nothing inside the system uses the regenerated content.
- **Two findings threaten the path as it stands:**
  1. **Structured input** (exploratory, 2 seeds). When items share structure, as Stage 2's
     shared items and Stage 3's exemplars do by definition, content completion collapses.
  2. **No forgetting.** The content store saturates instead of forgetting. Past about 0.375
     items per memory cell, cues light most of the reconstruction layer.

Both reviewers with the north-star lens recommended that the owner look at the line now,
before the online-memory contract is committed. I agree.

## What Stage 1 has, and what the experimenter still supplies

| capacity | evidence | conditions |
|---|---|---|
| one-shot index memory (P2-E2) | C1 0.945-0.985 at up to 0.25 items per memory cell, 5/5 fresh seeds | after a 50 s rest; habituates under a held cue |
| content completion (P2-E3) | joint 0.955-1.000 at up to 0.25 items per cell, 5/5 fresh seeds | independent random items; frozen copies; inhibition needed at 0.25 items per cell |

The experimenter still supplies the following. This list should shrink stage by stage, and it
is the honest measure of how far the system runs itself:
1. **When to write.** Plateaus occur only inside protocol-marked encodings, so the system is
   told which inputs are new and which are tests.
2. **The key.** Plateau cells are drawn at random, independent of content. A re-exposed item
   gets a second, unrelated memory.
3. **The value.** Eligible input lines are copied one-to-one onto the reconstruction layer.
4. **The operating point.**
   - J is calibrated on a held-out seed; its window is about ±5 % for the memory layer.
   - The inhibition ratio g is fixed by hand.
   - Accommodation tracks mean input.
   - Recall needs rest before testing.
5. **The input statistics.** Every gated item is an independent random pattern of 100 lines at
   40 Hz, cued with exactly half of its lines.
6. **The test regime.** Tests run on discarded copies with plasticity off, so recall never
   changes the system.

## Toward sequences (Stage 2)

**What helps:**
- **A distinct memory per occurrence.** Random plateaus give every occurrence of an item its own
  assembly. That is the kind of per-context copy ("clone") that disambiguates shared items in
  sequence models.
- **Unlinked assemblies.** The memory layer is nearly silent in background, so successive
  assemblies are not linked by accident.
- **A window wide enough to link them.** BTSP's seconds-long plasticity window is wide enough to
  link item k's assembly to item k+1's.
- **A readout of the result.** P2-E3 can then read the next item out in input coordinates.

**What does not:**
- **Chaining through content cannot reach the bar.** It is first-order Markov. A shared item
  with two successors resolves at most half the time, against Stage 2's 0.80 bar (constructive
  review F2, arithmetic).
- **The transition must live between memory assemblies.** That mechanism is untested.
  Recurrence inside the memory layer ran away in P2-E1's review (2,889-3,969 cells), so it will
  need a stabiliser.
- **The readout handles about three co-active assemblies** (exploratory). Chained replay must
  therefore switch off earlier steps.

**Verdict for Stage 2.** P2-E3 is necessary plumbing. The sequence mechanism itself (memory to
memory transitions plus a stabiliser) is still entirely ahead.

## Toward abstraction (Stage 3)

**The decisive exploratory fact** (labelled, frozen P2-E3 parameters, reviewer's script on seed
99, re-run by me on seed 97). Items were drawn as exemplars of 10 never-shown prototypes, with
siblings sharing about 16 of 100 lines.

| condition | seed 99 | seed 97 |
|---|---|---|
| exemplar half cues, joint at M = 500 (iid items give 0.99) | 0.147 | 0.167 |
| same raster, plateau-set store | 0.94 | 0.94 |
| about 4 % sibling overlap, joint | 0.99 | 0.99 |

- **What the plateau-set comparison shows.** The collapse comes from the one experience-driven
  part of the write: sibling assemblies fire during the continuation and write their own lines
  into the item's feedback. |R(x)| is 50-52 against |A(x)| of about 20.
- **A new exemplar of a known family regenerates nothing.** The system does not generalise
  within a family.
- **The never-seen prototype's half cue** regenerates the whole prototype, but with 745-862
  intrusions. With the plateau-set store it does so with 12-18 intrusions, because 80-89 memory
  cells from many sibling assemblies respond and the count threshold keeps their common lines.

The last point matters for the Stage 3 gate. A Willshaw-type memory produces a "prototype
effect" by superposition at retrieval, with no learned abstraction (constructive review F7,
surrogate; the plateau-set run above agrees). Stage 3's prototype clause as written can be met
this way. Its label-efficiency clause cannot be met cheaply only where raw input is already
poor: at distortion about 0.8, according to the surrogate (constructive review F8).

**Verdict for Stage 3.** P2-E3 does not advance abstraction. Its learned write fails on
structured input. The variant that survives (writing from the assigned code) is a pure lookup
whose only "abstraction" is blending at retrieval.

## Toward behaviour and problem solving (Stages 4-5)

- **What P2-E3 could support.** One-shot storage plus regeneration of (state, action, outcome)
  content would support episodic control, a known baseline for fast reinforcement learning.
  Learned transitions plus replay could later support planning.
- **What is missing.** There is no action, no reward, no closed loop, and no use of
  regenerated content by the system.

**Verdict for Stages 4-5.** The distance is unchanged by P2-E3. Fair estimates are several
experiments for Stage 2, and Stage 4 only after it.

## Risks to the line, in order of severity

1. **Structured input** (skeptic review NS1). If content-blind keys plus responder writes cannot
   store correlated items, Stages 2 and 3 cannot rest on this substrate. This is the first thing
   to settle.
2. **Saturation without forgetting** (NS4).
   - Feedback density reaches 0.36 at M = 2,000.
   - Novel cues light up to every line.
   - At one item per 2.25 s, a learner reaches the wall in about an hour.
   - A lifelong learner needs graceful forgetting: a palimpsest.
3. **An operating point that habituates** (P2-E2 review; NS7). A repeated cue cut recall from
   0.99 to 0.67 over 30 s. Stage 4 (repeated stimuli) and Stage 6 (10 s holds) conflict with
   that.
4. **Benchmark collecting** (NS5).
   - Each pass so far added one calibrated element against in-distribution tests.
   - Counting arithmetic predicted each pass to within a few per cent.
   - From P2-E4 on, every contract should predeclare untuned out-of-distribution arms, reported
     but not gated, so the record shows where each mechanism stops working:
     - correlated items;
     - other item sizes;
     - cue fractions other than one half;
     - noisy cues.

## What would count as real progress next

A mechanism by which the system **uses its own regenerated content to decide what to learn**.
Concretely, the mismatch between input and regeneration (lines present but not regenerated;
lines regenerated but absent), labelled as a comparator or prediction-error proxy, could drive
two things:
- **the feedback write.** Potentiate only what was missing and depress intrusions. That is an
  error-correcting write, which also bounds the store and makes it a palimpsest. It would remove
  the experimenter-supplied value (item 3 in the list above) and address risks 1 and 2.
- **plateau allocation** (familiarity gating). Familiar inputs would not get a new memory,
  which removes the write signal (item 1) and the duplicate-memory problem (item 2).

Each is a single mechanism and needs its own contract. Both are proposals, not results. Their
order relative to Stage 2 is the owner's decision (question 4 below).

## Proposed path

1. **P2-E4, online memory.** Required by the owner before Stage 1 is complete. The draft has
   been revised for every review finding (`docs/plant2/P2-E4-online-memory.draft.md`). It still
   needs a two-critic red-team before it is committed as a contract. Gated seeds 16-20 are
   untouched.
2. **P2-E5, capacity scaling.** On the owner's design, gating content as well as the index.
3. **Structured-input test, no new mechanism.** Frozen parameters; sibling overlap 2.5 / 6.5 /
   16 / 36 %; gate exemplar completion at 16 %. Predicted FAIL, from the exploration above.
   Where it sits depends on question 1.
4. **Then one mechanism at a time:**
   - an error-correcting feedback write;
   - familiarity-gated allocation;
   - for Stage 2: memory-to-memory BTSP transitions, then chained replay with a fast
     stabiliser, gated against a first-order (Markov-1) content chain.

## Decisions for the owner

1. **Structured input in Stage 1?** Should Stage 1's gate gain a predeclared clause for
   correlated items, for example exemplar completion at 16 % sibling overlap? **Recommended:
   yes.** Otherwise Stage 1 can pass on a substrate that Stages 2 and 3 cannot use.
2. **P2-E4 scope: past capacity, and without the write oracle?**
   - **The proposal.** P2-E4 tests what you asked for: online recall, interference, retention
     and habituation, gated below capacity. Running past capacity (to M = 3,000), plateaus during
     probes, lure probes and re-exposure are reported arms, predicted to fail.
   - **The alternative.** The skeptic would gate recent-item recall past capacity. That makes
     P2-E4 fail by design on a question it has no mechanism for.
   - **Recommended:** report them, and add graceful forgetting to Stage 1 as its own clause if
     you want it gated.
3. **Inhibition in the memory layer for Stage 2.** Memory-to-memory transitions will probably
   need fixed activity-proportional inhibition in the memory layer, like the readout's. May
   Stage 2 contracts declare it as a fixed element, under the same conditions you set for
   P2-E3?
4. **Order: the content-using mechanisms before Stage 2?** Should the error-correcting write and
   familiarity gating come before Stage 2? **Recommended:** yes for the error-correcting write if
   the structured-input test fails, since Stage 2's shared items would hit the same collapse.
5. **The Stage 3 gate.** Should the gate require the prototype effect jointly with exemplar
   specificity, and set the label-efficiency test at high distortion (about 0.8), where raw
   input fails, so that blending at retrieval cannot pass it?

## Erratum (2026-10-11, from the P2-E5 red-team; the text above is not edited)

The sentence in "Toward abstraction" says that sibling assemblies "write their own lines" into an
item's feedback. That is backwards.

**What the code writes.** `w_fb(i -> j) = 1` for responders i in R(x) and eligible lines j in E(x).
So cells of earlier siblings that fire in x's continuation **receive x's lines**. Later, when a
sibling y's half cue drives those cells, they regenerate x's lines into y's readout.

**So an item is damaged after it is stored,** by later siblings writing onto its cells. In
exploration at s = 60 and M = 500, lines that only later siblings have average 40-48 intrusions
per cue, against about 2.3 for lines that only earlier siblings have. The oldest items are hit
hardest.

**At M = 1,000 the forward index also fails:** C2 is about 0.47-0.50, upstream of any feedback
write.

See `docs/plant2/P2-E5-structured-items.md` and `review/plant2/P2-E5/`.
