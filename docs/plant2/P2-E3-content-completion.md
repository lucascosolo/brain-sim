# P2-E3: content completion, regenerating the missing half of an input from a half cue (predeclared 2026-10-10)

Stage 1 of `docs/plant2/STAGES.md`. This file down to "Calibration result" is committed before
any P2-E3 code. The calibration result is appended and committed before any gated seed runs.
The result is appended afterwards. Nothing above it is edited later.

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

A memory-to-reconstruction feedback path, written one-shot from the memory cells' own spikes
while the experience is still present, lets a half cue regenerate the missing half of the
item's input features in a reconstruction layer. Fixed inhibition proportional to total memory
activity makes it specific. This holds at 250, 500 and 1,000 stored items, with the P2-E2
memory layer unchanged.

## What is new: one learned path and one fixed element

Everything in P2-E2 is unchanged:
- the inputs, memory cells and BTSP store;
- J* = 1.525 mV and threshold accommodation (tau 10 s);
- learning, cue sets, the 50 s settle and the memory criteria.

**Reconstruction layer `rec`.**
- m = 4,000 LIF cells, one per input line, with the same constants as the memory cells (tau_m
  20 ms, rest -70 mV, fixed threshold -50 mV, reset -65 mV, refractory 2 ms).
- No accommodation and no sensory spikes. During the test, its only inputs are the two below.

**Learned path: feedback `mem -> rec`** (binary, strength J_fb, delay 1 ms).
Labelled proxy: a one-shot clipped Hebbian write (Willshaw et al. 1969) with a postsynaptic
instructive signal.
1. Each learning episode is P2-E1's 200 ms encoding (eligibility, random plateaus, the BTSP
   write at 200 ms).
2. A **50 ms continuation** follows. The item stays on, and its input spikes come from a stream
   of their own, so the forward store stays bit-identical to P2-E1's. The memory cells now
   respond through the synapses just written.
3. At the end of the continuation, for every memory cell i that spiked at least once during it,
   and every line j that was eligible in the encoding (>= 3 spikes in the 200 ms), set
   `w_fb(i -> j) = 1`.
4. There is no depression and no other write. The rule never reads a plateau. The presynaptic
   term is real memory spikes. The postsynaptic term is the line's sensory activity during the
   episode. That activity reaches reconstruction cell j as an instructive signal that does not
   make it fire, a labelled proxy like entorhinal input to distal dendrites.

**Fixed element: activity-proportional feedforward inhibition** (declared extra element,
approved by the owner). Every memory spike delivers -g x J_fb to every rec cell, 2 ms later,
1 ms after the excitation.
- g = 0.3, fixed. This is the value at which a P2-E2 reviewer's exploratory runs (seeds 42-43,
  not used here) found a working readout.
- A rec cell then fires only if the fraction of active memory cells that project to it exceeds
  g by enough to cross threshold: a Willshaw threshold that scales with recall activity.
- Labelled proxy: a pool of interneurons driven by memory output, feedforward inhibition in
  the sense of Pouille & Scanziani 2001.

## Test

The protocol is P2-E2's: same cue sets per load, 50 s settle, half cues for 200 learned items,
novel half cues for 200 items, full cues. The reconstruction layer runs alongside.

- **Window.** A rec cell regenerates its line if it spikes at least once in [onset, onset +
  75 ms). That allows the 50 ms memory window plus one synaptic stage and integration.
- **Line sets.** For a cued learned item x:
  - the **missing half** is its 50 lines not in the half cue;
  - the **visible half** is the 50 cue lines;
  - **intrusions** are regenerated lines outside the item's 100.

## Kill test

**Gated seeds: 11, 12, 13, 14 and 15**, all fresh. Calibration uses seed 0. Seeds 1-10 and 42-43
are not used.

**PASS only if every criterion holds at each of M = 250, 500 and 1,000 on every gated seed:**
- **D1 regeneration:** >= 80 % of the missing half is regenerated, for >= 90 % of cued items.
- **D2 intrusions:** fewer than 10 intrusions, for >= 90 % of cued items.
- **D3 novel cues:** a novel half cue regenerates fewer than 10 lines in total, for >= 90 % of
  novel cues.
- **D4 old items:** D1 and D2 also hold within the oldest 100 items.
- **D5 memory layer intact:** P2-E2's C1-C3 hold, with bars unchanged.

**Void condition (VOID, not pass).** Shuffled feedback: each memory cell keeps its number of
feedback synapses, but the targets are drawn uniformly from its own stream. With the same J_fb
and g, it must fail D1 at M = 1,000 on every gated seed.

**Matched no-inhibition comparison** (required by the owner; reported, not gated).
- An arm with g = 0 is calibrated by the same rule on seed 0. If no J_fb passes, it uses the
  grid value with the largest minimum over D1-D4 across the three loads on seed 0.
- It runs on every gated seed, together with a g = 0 arm at the main arm's J_fb*.
- Predeclared reading: if the matched g = 0 arm also passes the gate on every gated seed, the
  inhibition is recorded as unnecessary and later stages drop it. P2-E3's verdict is unaffected
  either way.

**Validity** (a failure makes the run invalid):
- each seed's forward store is bit-identical to what P2-E1's learning code produces;
- the forward and feedback stores are bit-identical across every test phase;
- mean eligible fraction >= 0.95;
- mean |A| in 18.5-21.5;
- accommodation has converged before each test phase. Per the P2-E2 review this is now judged
  by signed drift: |mean over cells of the change in vbar over the last 10 s| <= 0.1 mV.

**Decision.**
- PASS: Stage 1's content-completion clause is met. The online-memory experiment follows, with
  a north-star evaluation in between.
- FAIL: record the criterion and why, and stop this line. No parameter is retuned.
- VOID: record it.

## Calibration (held-out seed 0, before any gated seed)

- **Grid.** J_fb from 1.00 to 6.00 mV in steps of 0.25: 21 values for g = 0.3 and the same 21 for
  g = 0. All arms are read out from one simulation, so every J sees identical memory activity.
- **Pass.** A J passes if D1-D5 are >= 0.90 at M = 250, 500 and 1,000.
- **Choice.** J_fb* is the midpoint of the longest contiguous passing run; on a tie, the lower
  run. If no J passes for g = 0.3, P2-E3 FAILS and no gated seed runs.
- **Recording.** The seed-0 numbers at J_fb* are appended under "Calibration result" as
  item-level predictions.

## Predictions (before any code; from the reviewer's exploration and a counting estimate)

The counting estimate: at M = 1,000 a missing line of item x receives feedback from about 19
of the about 20 memory cells that respond to x's half cue. A non-item line receives from about
2.8 of them, because each responder projects to about 14 % of all lines.

- **Calibration window.** J_fb* is about 3 mV, with the window at about 2-4.5 mV.
- **D1.** 0.93-0.99 at every gated load.
- **D2.** >= 0.95.
- **D3.** About 1.0, since novel cues recruit about one memory cell.
- **D4.** Within 0.03 of D1/D2.
- **D5.** As in P2-E2: C1 0.94-0.98.
- **Regeneration latency.** Median 30-40 ms.
- **Visible half.** Regenerated at about the same rate as the missing half; it gets no
  privileged path.
- **Matched no-inhibition arm.** No window at M = 1,000 on seed 0. On gated seeds it fails D2 at
  M = 1,000 (best joint score about 0.87 in exploration).
- **Shuffled feedback.** D1 <= 0.05.
- **Capacity** (reported). M = 1,500 fails D2, the same edge as memory specificity.
- **Overall.** Chance of PASS about 55 %. The likeliest failure is D1 at M = 1,000 for items
  whose memory recall is partial.

## Reported, not gated

- Visible-half regeneration.
- Scaled reconstruction error HD(r, x) / HD(x', x), as in Wu & Maass 2025 Fig. 5.
- Regeneration latency.
- The intrusion distribution.
- Spontaneous rec spikes in the last 10 s of each settle.
- Continuation responders per item, against |A| (extra responders write extra feedback).
- Feedback store size and per-cell counts.
- M = 1,500 and 2,000.
- Both g = 0 arms.
- Library and CPU-kernel versions, the plant2 tree hash, and the contract digest in every
  record.

## Files

- `plant2/btsp.py`: `BinarySynapses.add` for the clipped write.
- `plant2/engine.py`: a global activity-proportional inhibition projection.
- `plant2/experiments/p2_e3_completion.py`: the driver.
- `plant2/tests/test_p2_e3.py`: the tests.
- Records go to `bench/results/plant2.jsonl`; derived data to `~/.cache/brain-sim/plant2/p2_e3/`.

## Calibration result

(appended after the calibration, before any gated seed)

## Result

(appended after the run)
