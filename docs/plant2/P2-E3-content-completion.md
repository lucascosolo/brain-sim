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

**Run 2026-10-10 on seed 0**, code 68beb4c, contract digest e829ac7011a8c2cd.
- **Records:** `kind` `calibration_point` x3 and `calibration_verdict`.
- **Log:** `~/.cache/brain-sim/plant2/p2_e3/calibrate.log`.
- **Convergence:** mean |dvbar| was 0.031 / 0.048 / 0.102 mV at M = 250 / 500 / 1,000, against a
  0.2 mV bar. The signed drift was -0.013 / -0.023 / -0.089 mV.

**A bug found and fixed before any gated run.**
- **The bug.** The first calibration (code 8c240bc, digest 2583f5e1f7e30627) set
  `window = 75` in the P2-E3 config, for the reconstruction readout. But P2-E1/E2's memory
  criteria read the same key, which should be 50 ms. So the memory-layer numbers it reported
  (D5) were computed at 75 ms. On seed 0 at M = 1,000 that gave C2 0.880.
- **How it was found.** A diagnostic showed the cause was neither the continuation nor the
  test code.
- **The fix.** The readout window now has its own key (`rec_window`), and a test pins both
  windows.
- **The re-run.** The calibration was re-run with the fixed code. All 202 readout arms are
  bit-identical between the two runs, because neither the memory raster nor the replay depends
  on that key. J* is the same, and only the reported memory C2 at M = 1,000 changed, to 0.970.
  Both runs' records stay in the append-only file.

**Passing windows** (pass fractions D1/2 joint, D3 and D4 >= 0.90 at every load):

| arm | passing J values at M = 250 / 500 / 1,000 | passing at all three loads |
|---|---|---|
| g = 0.3 | 84 / 83 / 33 | one contiguous run, **2.00-3.60 mV**, not censored |
| g = 0 | 35 / 19 / 0 | **none**. The fallback is the J with the largest minimum: **1.45 mV** (joint 0.885 at M = 1,000) |

**J_fb* = 2.80 mV.** The matched g = 0 arm runs at 1.45 mV, and it has no calibration window.

**Seed-0 re-read at the frozen values** (the item-level predictions for the gated seeds):

| M | arm | joint D1/2 | D1 | D2 | D3 | D4 | latency | HD ratio p10 / 50 / 90 |
|---|---|---|---|---|---|---|---|---|
| 250 | main (2.80, g 0.3) | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 22 ms | 0.00 / 0.02 / 0.08 |
| 500 | main | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 23 ms | 0.00 / 0.04 / 0.08 |
| 1,000 | main | 0.990 | 0.990 | 1.000 | 1.000 | 0.980 | 25 ms | 0.00 / 0.04 / 0.08 |
| 250 | matched g 0 (1.45) | 0.950 | 0.950 | 1.000 | 1.000 | 0.920 | 31 ms | |
| 500 | matched g 0 | 0.930 | 0.930 | 1.000 | 1.000 | 0.920 | 33 ms | |
| 1,000 | matched g 0 | **0.885** | 0.910 | 0.975 | 1.000 | **0.880** | 34 ms | 0.02 / 0.04 / 0.66 |
| 1,000 | g 0 at 2.80 | **0.130** | 1.000 | **0.130** | 0.995 | 0.120 | 23 ms | 0.14 / 2.26 / 12.6 |

Memory layer (D5), seed 0: C1 0.985 / 0.955 / 0.945, C2 1.0 / 1.0 / 0.970, C3 1.0 / 1.0 / 1.0.

**Predictions for gated seeds 11-15, revised from these numbers before any gated seed:**
- **Main arm:** joint >= 0.97 at M <= 500 and 0.95-0.99 at M = 1,000; D3 >= 0.99; D4 within
  0.03 of joint.
- **Latency:** 22-26 ms. That is barely later than the memory layer's own 22 ms, because rec
  cells fire on the first wave of memory spikes.
- **Matched g = 0 arm:** fails at M = 1,000 on most seeds (joint about 0.88).
- **Chance of PASS: about 70 %.** The remaining risk is D5 (memory C1 at M = 1,000; seed 0 has
  0.945) and seed-to-seed spread in the joint score at M = 1,000.

## Result

**PASS (2026-10-10). Valid and not void. Secondary reading: inhibition required.**
- **Settings:** J_fb* = 2.80 mV, g = 0.3, matched g = 0 arm at 1.45 mV (fallback).
- **Code:** commit c97f237, plant2 tree a949ecb0, unchanged during the runs. Contract digest
  e829ac7011a8c2cd.
- **Outcome:** all five gated seeds (11-15) meet every criterion at M = 250, 500 and 1,000.
- **Records:** `kind` `kill_test_seed` x5 and `kill_test_verdict`.
- **Log:** `~/.cache/brain-sim/plant2/p2_e3/run.log`.
- **Wall time:** about 7 min per seed, two processes in parallel.

**Gated criteria, main arm** (joint D1/2, D3, D4; then memory C1 / C2 / C3; bar 0.90 each):

| seed | M = 250 | M = 500 | M = 1,000 |
|---|---|---|---|
| 11 | 1.000 / 1 / 1; 0.960 / 1 / 1 | 0.995 / 1 / 1; 0.970 / 1 / 1 | 0.985 / 1.000 / 0.980; 0.925 / 0.995 / 0.995 |
| 12 | 1.000 / 1 / 1; 0.960 / 1 / 1 | 0.990 / 1 / 0.990; 0.980 / 1 / 1 | 0.970 / 1.000 / 0.970; 0.940 / 1.000 / 0.995 |
| 13 | 0.990 / 1 / 0.980; 0.975 / 1 / 1 | 0.995 / 1 / 1; 0.980 / 1 / 1 | 0.980 / 1.000 / 0.980; 0.930 / 0.990 / 1.000 |
| 14 | 1.000 / 1 / 1; 0.985 / 1 / 1 | 0.990 / 1 / 1; 0.960 / 1 / 1 | 0.955 / 0.990 / 0.940; 0.955 / 0.985 / 0.990 |
| 15 | 0.995 / 1 / 1; 0.975 / 1 / 1 | 1.000 / 1 / 1; 0.970 / 1 / 1 | 0.985 / 1.000 / 0.990; 0.940 / 0.975 / 0.990 |

**Validity on every gated seed.**
- The forward store is bit-identical to unmodified P2-E1 learning at M = 250, 500 and 1,000.
- Both stores are unchanged by every test phase.
- Eligible fraction 0.987; mean |A| 19.83-20.20.
- Convergence 0.029-0.117 mV, against the 0.2 mV bar.

**Void and comparison arms at M = 1,000** (every gated seed):

| arm | joint D1/2 | D1 | D2 | reading |
|---|---|---|---|---|
| main (2.80, g 0.3) | 0.955-0.985 | 0.980-0.995 | 0.970-1.000 | passes |
| shuffled feedback (void check) | 0.000 | 0.000 | | fails, as required. By construction; a leak check |
| label-permuted feedback | 0.000 for x | 0.000 | | pi(x)'s missing lines regenerated at 0.968-0.982: a cue regenerates whatever was written for its own memory cells |
| plateau-set feedback (A(x) instead of R(x)) | 0.980-0.990 | 0.980-0.990 | 1.000 | about equal to main: the activity rule loses nothing to the bookkeeping version |
| matched g = 0 (1.45; no calibration window) | **0.770-0.860** | 0.840-0.920 | 0.920-0.970 | fails on every seed |
| g = 0 at 2.80 | **0.065-0.155** | | | floods with intrusions |

**Secondary claim, predeclared reading.** The matched no-inhibition arm has no calibration
window and fails at M = 1,000 on all five seeds. **Inhibition is required.** At M <= 500 the
no-inhibition arm alone reaches 0.92-0.965, so the inhibition matters only at the higher load.

**What the regeneration looks like** (main arm, gated seeds):

| measure | M = 250 / 500 | M = 1,000 |
|---|---|---|
| missing half regenerated, 10th / 25th / 50th / 75th / 90th percentile | 0.96 / 0.98 / 0.98-1.0 / 1.0 / 1.0 | same |
| intrusions per cue: median, 90th percentile | 0, 1-2 | 1, 2-3 |
| intrusions over the whole cue plus gap: median | 0 | 1 |
| reconstruction error HD(r, x) / HD(x', x): p10 / 50 / 90 | 0.0 / 0.04 / 0.06-0.08 | 0.0-0.02 / 0.04 / 0.10 (about 2 of 50 lines wrong) |
| novel half cues: lines regenerated, median and max | 0 and 0 | 0 and 0-2; max 22 on one seed |
| chance: another item's missing half regenerated | 0.022-0.027 | 0.022-0.027 |
| visible half regenerated | 0.98-1.0 | 0.98-1.0 |
| full cues: item lines regenerated | 0.99 | 0.99 |
| regeneration latency, median | 23-25 ms | 25-28 ms |
| joint at a 50 ms window | 0.945-0.995 | 0.92-0.955 |

- **Latency.** Regeneration follows the memory layer's own first spikes (about 22 ms) within
  1-6 ms.
- **Out-of-window rec spikes.** These run at 204-252 per cue. They are the regenerated lines
  firing on through the rest of the 100 ms cue (about 2 more spikes per line), not
  intrusions. Intrusions over the whole cue plus its gap stay at a median of 0-1.
- **Feedback store.** At M = 1,000 it holds 2.11-2.16 x 10^6 synapses, 527-540 per memory cell,
  each memory cell reaching 13.3-13.6 % of lines. The forward store holds about 0.93 x 10^6.
- **Responders.** |R(x)| is 23.3-24.0 against |A(x)| 19.8-20.2, with Jaccard 0.87-0.88. The
  extra responders write extra feedback but cost no measurable specificity.

**Capacity edge** (reported):

| M | joint | D2 | memory C2 |
|---|---|---|---|
| 1,500 | 0.185-0.290 | 0.195-0.315 | 0.68-0.73 |
| 2,000 | <= 0.015 | | |

D1 stays at 0.97-1.0 at both loads. Content specificity collapses more sharply than memory
specificity: every spurious memory responder also writes and reads feedback.

**Predictions against outcome.**

| prediction | outcome |
|---|---|
| J_fb* about 2.6 (window 2.0-3.3) | 2.80 (2.00-3.60) |
| matched g = 0 has no window, best near 1.4-1.5, joint about 0.87 | right: 1.45, 0.885 on seed 0; 0.77-0.86 gated |
| main joint 0.95-0.99 at M = 1,000 and >= 0.97 at M <= 500 | 0.955-0.985 and 0.990-1.000 |
| D3 >= 0.99 | 0.99-1.0 |
| latency 22-26 ms | 23-28 ms (slightly later at M = 1,000) |
| shuffled D1 <= 0.02 | 0.000 |
| plateau-set "slightly fewer intrusions and lower D1" | wrong: about equal |
| capacity: M = 1,500 fails D1/2 | right, by D2 |

**What this shows.** After one exposure per item and up to 1,000 items in 4,000 memory cells, a
spiking network regenerates the actual missing half of an input from half of it:
- it regenerates >= 80 % of the missing features with fewer than 10 wrong ones for 95.5-100 %
  of items, within 75 ms;
- the median reconstruction error is 2 of 50 lines;
- unlearned cues regenerate nothing;
- what is regenerated is the specific content written for that memory, not a statistical
  artefact.

The content path is written one-shot, from real memory spikes, while the experience is
present. It needs the fixed activity-proportional inhibition at the higher load.

**What it does not show.**
- **Assigned codes.** The memory index is still a random code assigned by plateaus.
- **Verbatim storage.** The feedback stores the input verbatim against the responders. That is
  input-supervised hetero-association, so "content" means the stored pattern, not an
  abstraction of it.
- **The test regime.** Everything was tested after a 50 s settle, on frozen copies. Online
  learning, interference while learning continues, and repeated-cue habituation are untested;
  that is the online-memory experiment's job.
- **Capacity.** It ends between 0.25 and 0.375 items per memory cell, and more sharply for
  content than for the index.

**Decision (per the contract).** Stage 1's content-completion clause is met. Next come an
evaluation against the north star, then the online-memory experiment, then capacity.
