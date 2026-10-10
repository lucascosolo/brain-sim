# P2-E3: content completion, regenerating the missing half of an input from a half cue (predeclared 2026-10-10)

Stage 1 of `docs/plant2/STAGES.md`. This file down to "Calibration result" is committed before
any P2-E3 code. A draft was red-teamed first: two fresh critics, findings in
`review/plant2/P2-E3/contract-redteam.md`. The calibration result is appended and committed
before any gated seed runs. The result is appended afterwards. Nothing above it is edited later.

## Why prior approaches failed, and what is still missing

- **The plant** never reached Stage 1 (SPEC 8.2-8.49; `docs/plant2/AUDIT-2026-10-10.md`), and it
  never scored regenerated input. K1.1 counted assembly cells only.
- **P2-E1 and P2-E2** showed that BTSP writes a one-shot index that a half cue re-evokes.
  - P2-E1 failed for lack of a load-independent operating point.
  - P2-E2 passed with threshold accommodation, which the owner accepted as a distinct
    mechanism.
  - Both scored only whether the experimenter-assigned assembly A(x) answers. Nothing showed
    that the content of an experience comes back. That content is what recall, replay,
    prediction and every later stage need.
- **The P2-E2 reviewers' exploratory runs** (`review/plant2/P2-E2/findings-direction.md`, F2)
  found that a feedback readout with a fixed threshold has no working window at M = 1,000. The
  owner approved fixed, activity-proportional inhibition on the readout as a declared extra
  element.

## Hypothesis

**Primary.** A memory-to-reconstruction feedback path, written one-shot from the memory cells'
own spikes while the experience is still present, lets a half cue regenerate the missing half
of the item's input features in a reconstruction layer. This holds at 250, 500 and 1,000 stored
items, with P2-E2's forward store unchanged.

**Secondary** (read from the matched comparison, not gated). The fixed activity-proportional
inhibition is what makes the regeneration specific.

## What is new: one learned path and one fixed element

**Unchanged from P2-E2:**
- the inputs, memory cells, BTSP forward store and its random streams;
- J* = 1.525 mV and threshold accommodation (tau 10 s);
- the cue sets, the 50 s settle and the memory criteria;
- `plant2/experiments/p2_e1_btsp.py` and `p2_e2_accommodation.py`, which are not edited.

**Changed:** learning episodes last 250 ms instead of 200 ms (see the continuation below). The
forward store is bit-identical to P2-E1's. Memory-layer activity differs slightly from P2-E2's,
because the continuation moves `vbar` during learning; D5 measures it.

**Reconstruction layer `rec`.**
- m = 4,000 LIF cells, one per input line, with the memory cells' constants: tau_m 20 ms, rest
  -70 mV, fixed threshold -50 mV, reset -65 mV, refractory 2 ms, the plant's exact-decay update.
- No accommodation and no floor on v.
- It receives no sensory spikes; during the test its only inputs are the two below.
- It is not simulated during learning. It starts at rest at the start of each test phase, after
  the settle, and is never reset within a phase.

**Learned path: feedback `mem -> rec`** (binary, strength J_fb, delay 1 ms).
Labelled proxy: a one-shot clipped Hebbian write (Willshaw et al. 1969) with a BTSP-like
postsynaptic instructive eligibility trace and fixed 1:1 line-to-rec wiring.
1. **Encoding**, 200 ms: exactly P2-E1's. That covers eligibility counts, the random plateau
   draw, the BTSP write at the end, and the reload of the forward synapses.
2. **Continuation**, the next 50 ms, with no `quiet()` in between. The item stays on at the same
   rates. Its input spikes come from `stream(seed, 9, k)` for item k, so the encoding streams and
   the forward store are untouched. The first continuation tick integrates input already in
   flight through the old synapses. After that, the memory cells respond through the synapses
   just written.
3. **The write.** The responders R(x) are the memory cells with >= 1 spike in the
   continuation. The eligible lines E(x) are the lines with >= 3 spikes in the encoding, taken
   from the encoding spike counts, never from item indices. For every i in R(x) and every j in
   E(x), set `w_fb(i -> j) = 1`.
4. **What the write does not do.** It never depresses and never reads a plateau. Its
   presynaptic term is real memory spikes. Its postsynaptic term is the line's sensory activity
   during the encoding, which reaches rec cell j as an instructive signal that does not make it
   fire. In effect the rule stores the input verbatim against the responders. That is
   input-supervised hetero-association, labelled as such. It is not a teacher current: no
   current enters rec.
5. **Background lines.** About 0.6 background lines per item reach eligibility (0.5 Hz, >= 3
   spikes in 200 ms). They are written and will score as intrusions.

**Fixed element: activity-proportional feedforward inhibition** (declared extra element,
approved by the owner).
- Every memory spike at tick t delivers -g x J_fb to every rec cell at tick t + 2, one tick after
  the excitation (t + 1).
- g = 0.3, fixed. This is the value at which a P2-E2 reviewer's exploration found a working
  readout. A P2-E3 contract critic's exploration, with exactly these dynamics (seed 42, not used
  here), found a g = 0.3 window at 2.00-3.25 mV. g was first found with same-tick inhibition.
  Because of the 1 ms lag, a cell can cross on excitation before its inhibition lands, so the
  Willshaw-threshold description is approximate.
- Labelled proxy: a pool of interneurons driven by memory output, feedforward inhibition in the
  sense of Pouille & Scanziani 2001.

**Implementation pinned.**
- All readout arms are replayed from the memory spike raster of the test phase.
- Each tick, a shared feedback matrix turns that tick's memory spikes into integer counts per
  line, and each arm adds J x count. Inhibition is one scalar per tick per arm.
- Calibration and gated runs use this same code. A unit test checks it spike-for-spike against
  `plant2.engine` LIF plus Projection on a small network.

## Test, at each load

**State.** Learning always continues from the untested state. Every test phase runs on a deep
copy, and the copy is discarded afterwards.

**Each test phase:**
1. 50 s settle, as in P2-E2.
2. P2-E2's half cues for 200 learned items (items 1-100 plus 100 drawn from the rest, fixed
   masks).
3. 200 novel half cues.
4. 200 full cues.

Each cue lasts 100 ms with a 200 ms gap after it, and each block starts with a 200 ms lead-in.
The rec arms run through every tick of the phase's cue blocks.

**Not run:** P2-E2's 60 s phase and its V-A, V-B and repeated-cue arms. Persistence and
habituation under ongoing learning belong to the separate online-memory experiment the owner
required.

**Window.**
- Onset is the first tick with cue rates.
- A rec cell regenerates its line if it spikes in ticks k = 0..74 after onset.
- The earliest causal spike is at k = 2 (input to memory 1 ms, memory to rec 1 ms).

**Item sets.** For a cued learned item x:
- the **missing half** is its 50 lines not in the half cue, including any that were not
  eligible, which count as misses;
- the **visible half** is the 50 cue lines;
- **intrusions** are regenerated lines outside x's 100.

**Joint criterion for one item.** At least 80 % of the missing half regenerated (>= 40 of 50)
**and** fewer than 10 intrusions.

## Kill test

**Gated seeds: 11, 12, 13, 14 and 15**, all fresh. Calibration uses seed 0. Seeds 1-10 and 42-43
are not used.

**PASS** only if, at each of M = 250, 500 and 1,000 on every gated seed, the main arm (g = 0.3,
J_fb*) meets:
- **D1/2 joint:** the joint criterion holds for >= 90 % of the 200 cued items.
- **D3 novel cues:** a novel half cue regenerates fewer than 10 lines in total, for >= 90 % of
  the 200 novel cues.
- **D4 old items:** the joint criterion holds for >= 90 % of the oldest 100 items.
- **D5 memory layer:** P2-E2's C1-C4 hold, with bars unchanged.

**Verdicts.**
- If every content criterion (D1/2, D3, D4) holds and only D5 fails on some seed, the verdict
  is **CONTENT PASS / P2-E2 REPLICATION FAIL**. That is recorded as a P2-E2 replication failure,
  not as evidence against content completion.
- If any content criterion fails, the verdict is **FAIL**.

**Void (VOID, not pass).** The shuffled-feedback arm must fail D1/2 at M = 1,000 on every gated
seed. In that arm each memory cell keeps its number of feedback synapses, with targets drawn
without replacement from all 4,000 lines (`stream(seed, 10, M)`), at the same J_fb* and g. This
arm fails by construction: each responder reaches about 13 % of lines, below g. It is a leak
check, labelled as such.

**Validity** (a failure makes the run invalid):
- At every gated load, the forward store's sha256 equals what unmodified P2-E1 learning code
  produces for the seed.
- The forward and feedback stores are bit-identical before and after every test phase. The
  feedback-store digest is recorded at every load.
- Mean eligible fraction >= 0.95.
- Mean |A| in 18.5-21.5 at M = 1,000.
- **Convergence**, P2-E2's rule unchanged: mean over cells of |vbar change| over the last 10 s of
  each gated-load settle <= 0.2 mV. Signed drift is reported beside it. M = 1,500 and 2,000 are
  flagged, never made invalid.

**Decision.**
- PASS: Stage 1's content-completion clause is met. Next come a north-star evaluation and the
  online-memory experiment.
- FAIL: record the criterion and why, and stop this line. No parameter is retuned.
- VOID: record it.

## Matched no-inhibition comparison and structural nulls (required by the owner; reported, not gated)

- **Matched g = 0 arm.** It is calibrated on seed 0 by the same grid and rule as the main arm.
  - If it has no passing J, it uses the grid J with the largest minimum over the pass fractions
    across loads; on a tie, the lower J.
  - It runs at every load on every gated seed.
  - **Secondary claim**, predeclared reading. "Inhibition required" holds if the matched arm
    has no calibration window, or fails the gate on at least one gated seed. "Inhibition
    unnecessary" holds if it passes on every gated seed. In that case later stages drop the
    element.
- **g = 0 at J_fb*.** An over-excitation check, expected to fail. It runs at every load.
- **Label-permuted feedback**, at M = 1,000. Each item's responders write onto the eligible
  lines of a different item pi(x), with pi a fixed random permutation (`stream(seed, 11, M)`).
  Every per-cell and per-line degree is kept. It shows whether a cue regenerates its own item's
  lines rather than an artefact of store statistics. Reported: D1/2 for x, and the fraction of
  pi(x)'s missing lines regenerated.
- **Plateau-set feedback**, at M = 1,000. The feedback is written from A(x) instead of R(x). It
  shows what the activity-based rule adds.
- **Chance level.** Under x's half cue, the fraction of another cued item's missing half that is
  regenerated.

## Calibration (held-out seed 0, before any gated seed)

- **Grid.** J_fb from 1.00 to 6.00 mV in steps of 0.05: 101 values for g = 0.3 and the same 101
  for g = 0. All 202 arms are replayed from one memory raster per load.
- **Pass.** A J passes if, at each of M = 250, 500 and 1,000, the D1/2 joint fraction, the D3
  fraction and the D4 joint fraction are all >= 0.90. D5 does not depend on J_fb, so it is
  reported, not part of the rule.
- **Choice.** J_fb* is the midpoint of the longest contiguous passing run; on a tie, the lower
  run. A run touching 1.00 or 6.00 is recorded as censored, and its midpoint is still taken.
  If no J passes at g = 0.3, P2-E3 FAILS and no gated seed runs.
- **Re-read.** After the choice, seed 0 is re-read once from the same streams with arms at
  J_fb* (g = 0.3), at the matched g = 0 J, and at g = 0 with J_fb*. Those numbers are appended
  under "Calibration result" as the item-level predictions, and committed before any gated
  seed.

## Predictions (written before any code)

The predictions come from the critics' exploratory runs with exactly these dynamics (seed 42)
and a corrected count. At M = 1,000:
- each responder projects to about 13 % of lines;
- a non-item line gets about 0.11 x 20, so about 2.2 responder inputs;
- a missing item line gets about 19.

| quantity | prediction |
|---|---|
| J_fb* | about 2.6 mV; window about 2.0-3.3 mV |
| matched g = 0 arm | no calibration window; best near 1.4-1.5 mV, joint about 0.87 at M = 1,000 |
| D1/2 joint, main arm | 0.92-0.98 at M = 1,000; >= 0.95 at M <= 500 |
| D3 | >= 0.97 |
| D4 | within 0.03 of D1/2 |
| D5 | as P2-E2: C1 0.94-0.98 |
| matched g = 0 arm on gated seeds | fails the joint criterion at M = 1,000 on most seeds |
| g = 0 at J_fb* | fails D2 badly |
| shuffled arm | D1 <= 0.02 |
| label-permuted arm | D1/2 for x about 0; pi(x)'s missing lines regenerated at about main D1 |
| plateau-set arm | slightly fewer intrusions than main, and slightly lower D1 for items with extra responders |
| regeneration latency | median 30-40 ms |
| visible half | regenerated at about the missing-half rate |
| HD(r, x) / HD(x', x) | median <= 0.1 |
| capacity (reported) | M = 1,500 fails D1/2, the same edge as memory specificity |

**Chance of PASS: about 55 %.** The likeliest failure is the joint criterion at M = 1,000, from
items with partial memory recall or extra intrusions.

## Reported, not gated

Per arm and load:
- D1 and D2 separately;
- the joint, D1 and D2 at a 50 ms window;
- intrusions over the whole 100 ms cue plus its 200 ms gap;
- the per-item distribution of the missing-half fraction, so that no graded-fidelity claim goes
  beyond it;
- **reconstruction error.** HD(r, x) / HD(x', x) per item, with r the rec cells spiking in
  k = 0..74, x the item's 100 lines and x' its 50 cue lines (so the denominator is 50). Lines
  missed through eligibility count as errors. Median, 10th and 90th percentiles are given.
- **regeneration latency:** the median over regenerated missing lines of the first-spike k,
  then the median over items;
- the visible-half regeneration fraction;
- rec spikes outside the scoring windows, per cue.

Per load:
- |R(x)| against |A(x)|, and Jaccard(R(x), A(x));
- the `vbar` offset during the continuation;
- feedback-store size and per-cell counts.

Also:
- loads M = 1,500 and 2,000;
- library and CPU-kernel versions, the plant2 tree hash, and one contract digest (J_fb
  excluded) in every calibration, seed and verdict record.

## Files

- `plant2/btsp.py`: `BinarySynapses.add` for the clipped write.
- `plant2/readout.py`: the vectorised replay of reconstruction arms from a memory raster.
- `plant2/experiments/p2_e3_completion.py`: the driver.
- `plant2/tests/test_p2_e3.py`. The tests cover:
  - the replay against the engine, spike for spike;
  - a silenced item line receiving no feedback;
  - test copies leaving the learning state untouched;
  - the forward-store identity;
  - a slow test reproducing P2-E2's seed 6, M = 250 phase-1 criteria exactly.
- Records go to `bench/results/plant2.jsonl`; derived data to `~/.cache/brain-sim/plant2/p2_e3/`.

## Calibration result

(appended after the calibration, before any gated seed)

## Result

(appended after the run)
