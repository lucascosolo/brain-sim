# P2-E2: a load-independent operating point by slow threshold accommodation (predeclared 2026-10-10)

Stage 1 of `docs/plant2/STAGES.md`, second experiment of the plant2 line. Everything down to
"Calibration result" is committed before any P2-E2 code exists. The calibration result is
appended and committed before any gated seed runs. The result is appended after the run, and
nothing above it is edited afterwards.

## Why the prior approaches failed

- **The recovered plant** (SPEC 8.2-8.49; `docs/plant2/AUDIT-2026-10-10.md`). Pair STDP's fixed
  point sat below the homeostatic rest weight. The seconds-scale homeostat erased writes. The
  code was dense. The wiring capped recall.
- **P2-E1** (FAIL, reviewed, `docs/plant2/P2-E1-btsp.md` and its addendum). BTSP wrote the
  right cells and nothing else. A half cue re-evoked a median of 0.92-0.94 of them within
  50 ms, and unlearned cues ignited a median of 2 cells. But no fixed J gives a working memory
  across loads:
  - each cell's distance to threshold was set by how much the network had stored, not by the
    cue;
  - at low load the cue alone was too slow (C1 0.61 at M = 250);
  - at high load every cue ignited hundreds of cells (C2 = C3 = 0.00 at M = 2,000);
  - in the reviewers' sweeps no single J passes M = 250 and M = 1,000 together.
- **Where the load effect comes from.** Two terms contribute about equally:
  - the steady background spikes arriving on other memories' strong synapses;
  - other memories' strong synapses on the cue's own input lines.

  This experiment removes only the first. The second is predicted to set the capacity edge.

## Hypothesis

Each memory cell's spike threshold slowly tracks its own mean membrane potential. That removes
the steady, load-dependent background offset cell by cell. With one J, calibrated in advance
on a held-out seed, half-cue completion and specificity then hold at 250, 500 and 1,000 stored
items, where no fixed threshold at that J does.

## One mechanism: slow threshold accommodation (labelled proxy)

For each memory cell i, every tick:

    vbar_i <- vbar_i + (v_i - vbar_i) / tau_acc
    theta_i = v_th + (vbar_i - v_rest)
    spike if v_i >= theta_i (and not refractory)

- **Order and constants.** `vbar` is updated after the membrane update and before the spike
  test. `v_th` is -50 mV and `v_rest` -70 mV, as in P2-E1. `tau_acc` = 10 s (10,000 ticks).
- **What the threshold does.** It sits 20 mV above the cell's own recent mean potential instead
  of 20 mV above rest. A steady input therefore raises the threshold as much as it raises the
  potential. A transient cue of 100 ms moves `vbar` by under 1 % of its effect.
- **Why 10 s.** A reviewer's exploratory runs (`review/plant2/P2-E1/findings-direction.md`, F7)
  found accommodation at 1-3 s habituating to a cue repeated ten times (recall -0.03 to -0.10).
  At 10 s it stayed flat. 10 s is still far faster than load changes between test phases.
- **Labelled proxy.** It stands for slow threshold accommodation: slow Na+ inactivation and
  slow K+ currents raise the spike threshold with sustained depolarisation (Azouz & Gray 2000;
  Platkiewicz & Brette 2011). No claim of biology is made beyond that label.
- **No reset.** `net.quiet()` resets membrane, delay ring and refractory state. It never resets
  `vbar`. No test phase calls `quiet()`: each presentation continues from the state the
  previous one left.

Everything else is P2-E1 unchanged: BTSP with random plateau gating (f_q 0.005), binary inputs
-> memory synapses, the inputs, the items, the half-cue protocol, the 50 ms window, every bar,
and every random stream. BTSP never reads memory-cell activity, so a seed's store is
bit-identical to the store P2-E1's code learns for that seed.

**The owner's closed gate.** `docs/recovery/project-facts-2026-10-03.md` lists "I_GAIN /
rejected intrinsic homeostasis as previously run". What was rejected is K0.14 (SPEC around line
2593). This mechanism differs from it:

| | K0.14 (closed) | P2-E2 |
|---|---|---|
| driving signal | each cell's firing-rate error against a rate setpoint, applied once per 1 s sweep | the cell's own mean membrane potential; no setpoint, no spike count |
| role | replaced synaptic scaling, in a plant where STDP owns the weights | sits beside a synaptic rule (BTSP) that reads neither rates nor thresholds |
| offset | gain-like; aimed to move the rest weight | additive; equal to the mean depolarisation |
| network | the plant | plant2 |

It is flagged to the owner (`DECISIONS.md` 2026-10-10, second entry). If the owner counts it
under the gate, this result is withdrawn from the plant2 line and kept in the record.

## J: calibrated on a held-out seed before any gated run

**Grid.** J in {1.40, 1.45, ..., 1.90} mV on seed 0, which is never gated. Accommodation is on.
Each J is tested at M = 250, 500 and 1,000 with the test protocol below (full cues omitted). J
passes if C1-C4 are all >= 0.90 at all three loads.

**Choice.**
- J* is the midpoint of the longest contiguous run of passing grid values; on a tie between
  runs, the lower run is taken.
- If no J passes, P2-E2 FAILS and no gated seed is run.

The calibration's numbers at J* are appended under "Calibration result" as the item-level
prediction for the gated seeds. That answers the P2-E1 review: predict C1 from an item-level
simulation, not from per-cell probabilities.

## Protocol

Learning is P2-E1's: one 200 ms episode per item, BTSP at the episode's end. Episodes are
separated by unsimulated quiet. Learning runs once per seed up to M = 2,000, with test phases
at the checkpoints M = 250, 500, 1,000, 1,500 and 2,000; test phases never change a weight.

Each test phase:
1. **Settle.** 50 s (5 `tau_acc`) of background, continuing from the current state.
2. **Half cues.** The P2-E1 cue set for that load: items 1-100, plus 100 drawn uniformly from
   the rest, with fixed half masks.
3. **Novel half cues.** 200 fresh items, as in P2-E1.
4. **Full cues.** All 100 inputs; latency reference only.

Each cue lasts 100 ms and is followed by 200 ms of background. At M = 1,000 the phase is
followed by 60 s more background, with `vbar` carried and nothing reset, and then the half
cues and novel half cues again (C5).

## Kill test

**Gated seeds: 6, 7, 8, 9 and 10**, all fresh. Seeds 1-5, whose stores equal P2-E1's, are
reported beside them as a paired comparison, not gated. Bars and definitions are P2-E1's.
**PASS** only if, with the single J*, every criterion holds on every gated seed:

- **C1-C4 at each of M = 250, 500 and 1,000:**
  - C1: recall >= 0.80 for >= 90 % of cued items;
  - C2: spurious < 0.5 |A| for >= 90 %;
  - C3: novel ignition < 0.5 mean |A| for >= 90 %;
  - C4: C1 and C2 within the oldest 100 items.
- **C5 at M = 1,000:** C1-C3 hold again after the 60 s, measured from the carried state.

**Void conditions** (any one makes the run VOID: not a pass, recorded):
- **V-A. The mechanism must matter.** A fixed-threshold arm uses the same stores, the same J*,
  the same input-spike streams and no accommodation. It must fail C2 or C3 at M = 1,000 on
  every gated seed.
- **V-B. The memory must matter.** A matched-density random store keeps each memory cell's
  number of strong synapses but draws their presynaptic inputs uniformly, from its own stream.
  With accommodation and J*, it must fail C1 at M = 1,000 on every gated seed.

**Validity** (any failure makes the run invalid):
- mean eligible fraction >= 0.95;
- mean |A| in 18.5-21.5 at M = 1,000;
- the strong-synapse set is bit-identical before and after every test phase;
- each seed's store at M = 1,000 is bit-identical (sha256 of the sorted keys) to what P2-E1's
  learning code produces for that seed;
- accommodation has converged before each test phase: the mean over cells of |vbar change|
  over the last 10 s of settling is <= 0.2 mV.

**Decision.** PASS: accommodation is plant2's operating-point mechanism, and the next Stage 1
experiment attacks capacity growth with cell count, a signal-to-noise problem. FAIL: record
which criterion and why, and stop this line. VOID: record which control and why.

## Predictions (written before any code, from the reviewers' exploratory runs and my single-cell estimates)

- **J*.** The calibration window is about 1.50-1.70 mV, so J* is about 1.6.
- **C1-C3.**
  - C1 0.93-0.99 at each gated load.
  - C2 and C3 >= 0.97 at M = 250 and 500.
  - At M = 1,000, C2 and C3 0.91-0.99, with the thinnest margin in C2.
  - C4 within 0.03 of C1.
- **C5.** Within 0.03 of phase 1.
- **V-A.** The fixed-threshold arm at J* gives C2 <= 0.10 at M = 1,000 and C1 >= 0.95 at every
  load (it is over-excitable).
- **V-B.** The random store gives median recall <= 0.10.
- **Recall at 25 ms.** About 0.5 (P2-E1: 0.42-0.48).
- **Capacity edge** (reported). It is set by cue-line overlap, which accommodation leaves alone:
  C2 and C3 about 0.5-0.85 at M = 1,500 and <= 0.4 at M = 2,000.
- **Overall.** Chance of PASS about 70 %. The likeliest failure is C2 at M = 1,000 on one seed.

## Reported, not gated

- **Per load:**
  - recall at 25, 50 and 100 ms;
  - half-cue and full-cue latencies;
  - hubs (cells answering more than 5 % of cues);
  - threshold offsets theta_i - v_th: mean and 95th percentile, and their correlation with
    each cell's strong-synapse count.
- **Synapse counts.** Measured against predicted cue synapses per written cell (24.66).
- **Repeated-cue arm** (M = 1,000). 20 items, each half cue shown 10 times in a row at the
  one-third duty cycle; recall per repetition.
- **Wrong-cue null.** 100 pairs: item y's half cue, recall of A(x).
- **Label-shuffled chance.** Recall of a random other item's assembly under each half cue.
- **Comparison arms at every load:** the full fixed-threshold arm and the random-store arm.
- **Seeds 1-5** at J*, paired against P2-E1.
- **Library and CPU-kernel versions** in every record.

## Files

- `plant2/engine.py`: LIF gains `acc_tau`, plus `vbar` state that `quiet()` keeps.
- `plant2/experiments/p2_e2_accommodation.py`: driver for calibration, gated and reported runs.
- `plant2/tests/test_p2_e2.py`: unit tests, including a check of the cue-synapse formula.
- Records go to `bench/results/plant2.jsonl`; derived data to `~/.cache/brain-sim/plant2/p2_e2/`.

## Calibration result

**Run 2026-10-10, commit 6076a22, seed 0** (records `kind: calibration_point` and
`calibration_verdict`; log `~/.cache/brain-sim/plant2/p2_e2/calibrate.log`). Accommodation
converged at every point: mean |vbar change| over the last 10 s was 0.03-0.09 mV, against a
0.2 mV bar.

| J (mV) | M = 250: C1 / C2 / C3 / C4 (recall, spurious) | M = 500 | M = 1,000 | passes |
|---|---|---|---|---|
| 1.40 | 0.925 / 1 / 1 / 0.910, 1 | 0.920 / 1 / 1 / 0.940, 1 | **0.875** / 1 / 1 / **0.880**, 1 | no |
| 1.45 | 0.960 / 1 / 1 / 0.950, 1 | 0.945 / 1 / 1 / 0.950, 1 | 0.900 / 1 / 1 / 0.920, 1 | yes |
| 1.50 | 0.980 / 1 / 1 / 0.970, 1 | 0.950 / 1 / 1 / 0.960, 1 | 0.925 / 0.985 / 1 / 0.950, 0.990 | yes |
| 1.55 | 0.985 / 1 / 1 / 0.980, 1 | 0.975 / 1 / 1 / 0.990, 1 | 0.945 / 0.960 / 1 / 0.960, 0.960 | yes |
| 1.60 | 0.990 / 1 / 1 / 0.980, 1 | 0.990 / 1 / 1 / 1, 1 | 0.965 / 0.940 / 0.985 / 0.960, 0.950 | yes |
| 1.65 | 0.995 / 1 / 1 / 0.990, 1 | 0.995 / 1 / 1 / 1, 1 | 0.970 / **0.895** / 0.940 / 0.960, **0.890** | no |
| 1.70 | 0.995 / 1 / 1 / 0.990, 1 | 1 / 1 / 1 / 1, 1 | 0.980 / **0.815** / 0.910 / 0.980, **0.820** | no |
| 1.75-1.90 | >= 0.995 / 1 / 1 / >= 0.99, 1 | 1 / 1 / 1 / 1, 1 | >= 0.99 / **0.71-0.445** / 0.845-0.540 / ..., **0.70-0.40** | no |

**J\* is 1.525 mV**, the midpoint of the one passing run, 1.45-1.60. This J is fixed for every
gated and reported seed.

**Item-level predictions for the gated seeds**, read from seed 0 at J = 1.50-1.55:

| | C1 | C2 | C3 | C4 |
|---|---|---|---|---|
| M = 250 | 0.98 | 1.00 | 1.00 | |
| M = 500 | 0.96 | 1.00 | 1.00 | |
| M = 1,000 | 0.935 | 0.97 | 1.00 | 0.955 recall / 0.975 spurious |

- The window is narrower than the reviewers' exploration suggested (about 1.52-1.68). C1 at
  M = 1,000 clears its bar by only about 0.035, so seed-to-seed spread (about +/-0.03 in P2-E1)
  could fail one gated seed there.
- Revised chance of PASS: **about 55 %**. The likeliest failure is C1 at M = 1,000.
- Above J*, C2 and C3 at M = 1,000 fall fast. Below it, C1 at M = 1,000 does. Even with
  accommodation, the cue-line overlap term closes the window near 0.25 items per cell, as
  predicted.

## Result

(appended after the run)
