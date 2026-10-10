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

**PASS (2026-10-10). The run is valid and not void.** J* = 1.525 mV and contract digest
1f2dcf7f19bf7073. All five gated seeds (6-10) pass every gated criterion at M = 250, 500 and
1,000, and C5 holds. On every gated seed, both void controls fail as the contract requires.

- **Code.** Every seed ran on code commit 19776f9. Records written during the run name later
  HEADs (6e1fc99 ... 545d507), because the commits in between appended result records while it
  ran. `git diff 19776f9 545d507 -- plant2` is empty.
- **Records** are in `bench/results/plant2.jsonl` (`experiment` P2-E2, `kind`
  `kill_test_seed` / `kill_test_verdict`).
- **Logs** are in `~/.cache/brain-sim/plant2/p2_e2/run.log`.
- **Wall time** was about 20 min per seed on 4 cores, two seeds in parallel.

**Gated criteria** (C1 / C2 / C3 / C4 recall, spurious; bar 0.90 each):

| seed | M = 250 | M = 500 | M = 1,000 | C5 at M = 1,000 after 60 s (C1 / C2 / C3) |
|---|---|---|---|---|
| 6 | 0.980 / 1 / 1 / 0.98, 1 | 0.975 / 1 / 1 / 0.97, 1 | 0.945 / 0.990 / 1.000 / 0.94, 0.99 | 0.940 / 0.985 / 1.000 |
| 7 | 0.975 / 1 / 1 / 0.99, 1 | 0.955 / 1 / 1 / 0.96, 1 | 0.945 / 0.975 / 0.990 / 0.97, 0.97 | 0.975 / 0.990 / 0.990 |
| 8 | 0.960 / 1 / 1 / 0.97, 1 | 0.970 / 1 / 1 / 0.96, 1 | 0.950 / 0.965 / 1.000 / 0.97, 0.96 | 0.925 / 0.995 / 0.995 |
| 9 | 0.980 / 1 / 1 / 0.98, 1 | 0.970 / 1 / 1 / 0.96, 1 | 0.950 / 0.985 / 1.000 / 0.93, 0.97 | 0.915 / 0.975 / 1.000 |
| 10 | 0.985 / 1 / 1 / 0.98, 1 | 0.960 / 1 / 1 / 0.98, 1 | 0.955 / 1.000 / 0.995 / 0.95, 1.00 | 0.945 / 0.995 / 0.995 |

**Void controls at M = 1,000** (they must fail; they do on every gated seed):
- **V-A, fixed threshold** at the same J, stores and input spikes: C1 1.000, C2 0.000-0.015,
  C3 0.000. Without accommodation every cue ignites the network. Accommodation, not the higher
  J, is what makes the result.
- **V-B, matched-density random store** with accommodation: C1 0.000, median recall 0.0. The
  response comes from what was written, not from excitability.

**Validity on every gated seed.**
- Eligible fraction 0.987.
- Mean |A| 19.7-20.1.
- Weights bit-identical across every test phase and the 60 s.
- Each store's sha256 equals the store that P2-E1's learning code produces for that seed.
- Accommodation converged before every phase: 0.028-0.144 mV over the last 10 s, against a
  0.2 mV bar.

**Paired comparison on P2-E1's own stores** (seeds 1-5, reported; same stores, so only the
readout differs). At M = 1,000, C1 / C2 / C3:

| seed | P2-E1 (fixed threshold, J 1.12) | P2-E2 |
|---|---|---|
| 1 | 0.840 / 0.925 / 0.955 | 0.975 / 0.980 / 0.980 |
| 2 | 0.845 / 0.935 / 0.980 | 0.950 / 0.975 / 0.995 |
| 3 | 0.860 / 0.950 / 0.970 | 0.945 / 0.980 / 0.995 |
| 4 | 0.810 / 0.925 / 0.945 | 0.925 / 0.985 / 0.995 |
| 5 | 0.850 / 0.905 / 0.945 | 0.955 / 0.960 / 0.985 |

Seeds 1-4 pass every gated criterion. **Seed 5's record is marked invalid**: accommodation
converged to 0.207 mV before the M = 2,000 test phase, just over the 0.2 mV bar. That phase is
reported only. At its gated loads seed 5 converged at 0.030-0.085 mV and passed every
criterion. The validity rule covers every test phase, and it is not relaxed.

**Reported measures** (gated seeds; seeds 1-5 alike).

| measure | outcome | prediction |
|---|---|---|
| Median recall at M = 1,000, at 25 / 50 / 100 ms | 0.57-0.61 / 0.96-1.00 / 1.00 (P2-E1: 0.42-0.48 at 25 ms) | about 0.5 at 25 ms |
| Median latency, half / full cue | 22-23 ms / 10 ms | |
| Hub cells | 0 at every gated load (P2-E1: 5-13 at M = 1,000) | |
| Threshold offset at M = 1,000 | mean 6.0 mV, 95th percentile 10.2-10.3 mV | |
| Offset vs the cell's strong-synapse count | correlation 0.998 | |
| Cue synapses per written cell | 24.61-24.82 | 24.66, corrected rule |
| Label-shuffled chance (another item's assembly) | median 0.0, mean 0.004-0.008 | |
| Repeated-cue arm, recall over 10 repeats | 0.89-0.95 to 0.90-0.94, minimum 0.87 | |

The threshold tracks each cell's stored load almost exactly. The repeated-cue arm shows mild
habituation at tau 10 s, smaller than at 1-3 s in the reviewer's exploration.

**Capacity edge** (reported; mean over gated seeds):

| M | C1 | C2 | C3 |
|---|---|---|---|
| 1,500 | 0.93 | 0.73-0.78 | 0.74-0.87 |
| 2,000 | 0.90-0.93 | 0.30-0.37 | 0.43-0.46 |

As predicted, completion now holds across load, and the limit has moved to specificity. Other
memories' strong synapses on the cue's own lines are untouched by accommodation, and they end
the operating window between 0.25 and 0.375 items per cell.

**Predictions against outcome** (calibration seed 0 predicted M = 1,000 at 0.935 / 0.97 / 1.00):

| prediction | outcome |
|---|---|
| C1 0.93-0.99 | 0.945-0.955 at M = 1,000; 0.955-0.985 at M <= 500 |
| C2 / C3 >= 0.97 at M <= 500 | 1.00 |
| C2 / C3 0.91-0.99 at M = 1,000 | 0.965-1.00 |
| C5 within 0.03 of phase 1 | within 0.035 (seed 9: 0.950 -> 0.915) |
| V-A: fixed arm C2 <= 0.10 | 0.000-0.015 |
| V-B: random store recall <= 0.10 | 0.0 |
| Capacity edge: C2 / C3 0.5-0.85 at M = 1,500 | 0.69-0.87 |
| Capacity edge: <= 0.4 at M = 2,000 | 0.27-0.46 (C3 at 0.43-0.46 slightly above) |

**What this shows.** In a spiking network, one exposure per item stores up to 1,000 items in
4,000 memory cells: 0.25 items per cell, with the load window running from 0.06. A half cue
re-evokes >= 80 % of an item's written cells within 50 ms for >= 92 % of items. Unlearned cues
ignite nothing, and the oldest items are retained. One J works across a 4x range of load, which
no fixed threshold achieved (P2-E1 and the reviewers' sweeps).

**What it does not show.**
- That the system chose its own code: the plateaus are random.
- That the input content is regenerated: not tested yet.
- That capacity grows with cell count.
- Anything about sequences, abstraction or behaviour.

This is Stage 1's storage-and-recall part. The content-completion and capacity parts of the
Stage 1 gate remain open.

**Decision (per the contract).** Accommodation is plant2's operating-point mechanism. This
holds pending the owner's ruling on its closeness to the closed intrinsic-homeostasis gate
(`DECISIONS.md`). The next Stage 1 experiment, after the independent review, attacks either
content completion or capacity growth with cell count.

## Addendum after independent review (2026-10-10)

Three fresh reviewers checked P2-E2 from the files alone. Findings are verbatim in
`review/plant2/P2-E2/`, with decisions in `review/ledger.jsonl`.

**The verdict stands: PASS, trustworthy.**
- Contract, calibration and gated-run ordering verified from git.
- Every gated number re-derives from the records.
- An independent dense LIF re-implementation (float32 and float64) reproduced seed 6's
  per-item recall, spurious and ignition values at M = 250, 500 and 1,000 exactly.
- Input-spike hashes are identical across the main, fixed and random arms, and no test phase
  calls `quiet()`; this is now pinned by a unit test.
- No bug changes a reported number.

The corrections below replace the statements they name. Nothing above is edited.

1. **The closed-gate table misstated K0.14.** K0.14's `theta_h` was also an *additive* offset
   "added to theta in the spike test" (SPEC around line 2600), not gain-like. And P2-E2's
   accommodation does hold a setpoint: it keeps theta - vbar at 20 mV, a setpoint on mean
   distance to threshold. The accurate statement is this:
   - Both are slow, per-cell, additive intrinsic-threshold homeostats, the family the closed
     gate names.
   - They differ in the controlled variable: mean membrane potential, continuous and
     unbounded, against firing rate per 1 s sweep, bounded.
   - They differ in role: beside BTSP, against replacing synaptic scaling next to STDP.
   - They differ in network: plant2, against the plant.
   - In the records the offset correlates 0.994-0.998 with each cell's stored strong-synapse
     count. In effect it is a per-cell load normaliser, reached through the membrane potential.

   Two reviewers judge it materially different from K0.14 *as run* and not a renamed re-run,
   but squarely in the gated family. **The ruling is the owner's.**
2. **What the controls show, and the "no fixed threshold" claim.**
   - The fixed-threshold arm at J* passes M = 250 and 500 on every gated seed: C1 >= 0.995,
     C2 >= 0.905, C3 >= 0.92. It fails only at M = 1,000 (C2 <= 0.015). Accommodation
     therefore extends the fixed-J window from <= 0.125 to 0.25 items per cell. It is not
     needed at the lower loads, and P2-E1's slowness at M = 250 came from its J of 1.12.
   - That no single fixed J passes 250 and 1,000 together rests on reviewers' exploratory
     sweeps (seeds 0-2), not on recorded runs.
   - V-A, fixed at the mechanism's own J, was near-certain to fail.
   - V-B (random store) fails by construction: it removes the cue-line-to-assembly synapses.
   - Future void comparators are calibrated by the same rule on the held-out seed. A control
     that keeps cue-line synapses and shuffles only the cross-talk is the stronger null.
   - The paired seeds differ from P2-E1 in J and in no-reset state as well as in readout, so
     "only the readout differs" is wrong.
3. **The operating point needs rest after learning.** Learning simulates only the 200 ms
   episodes, so `vbar` is not at equilibrium when learning ends. A reviewer's exploratory run
   (seed 0, M = 1,000, J*) gave:

   | background before testing | C1 |
   |---|---|
   | none | 0.875 (fails) |
   | 5 s | 0.915 |
   | 50 s (the contract) | 0.94 |

   The result holds after the contract's 50 s settle, which is 5 tau. An online protocol, with
   background simulated between episodes, is untested.
4. **The reported threshold offsets include the test's own cue duty.** They are read after the
   cue blocks. Background alone predicts about 3.6 mV at M = 1,000. The reported 6.0 mV includes
   the 1/3 cue duty, and items 1-100, cued first, saw lower thresholds. The operating point
   depends on the protocol.
5. **C5 is non-vacuous only in form.** Weights are frozen, and `vbar` (tau 10 s) re-equilibrates
   within the 60 s, so phase 2 is a fresh sample of the same equilibrium. C5 - C1 lay in -0.035
   to +0.03, about +/-2 sampling standard errors. A persistence criterion that can fail for a real
   reason needs ongoing learning or a load step inside the interval.
6. **A limit not tested by the contract: habituation under a sustained cue.** The repeated-cue
   arm covered only 10 repeats, about 3 s. A reviewer's exploratory run (seed 6, M = 1,000, 10
   items, 1 seed) showed recall degrading over 30 s, the same class as the plant's K0.13
   habituation. It bears on any stage that holds or repeats a stimulus (Stages 4 and 6).

   | presentations of the same half cue | items with recall >= 0.8 |
   |---|---|
   | 2-10 | 0.99 |
   | 31-60 | 0.79 |
   | 61-100 | 0.67 |

   The cued assembly's `vbar` rose by 5.2 mV.
7. **Overstated sentences, restated as measured** (gated seeds):
   - novel half cues ignite a median of 0-1 cells: 0 at M <= 500, 0.5-1 at M = 1,000, with a
     maximum of 14 of 4,000;
   - completion holds for >= 94.5 % of items (>= 91.5 % after 60 s), not ">= 92 %";
   - loads tested run from 0.0625 to 0.25 items per cell, and 0.0625 is the lowest load tested,
     not a measured edge.
8. **Number and provenance slips.**
   - The Result's contract digest 1f2dcf7f19bf7073 is P2-E1's. P2-E2's records carry
     ca482d31aa3f585d (calibration) and 4f625b7cf4dcfbf1 (seeds, J excluded).
   - Mean |A| on gated seeds is 19.94-20.13.
   - C2 at M = 1,500 is 0.715-0.775 (mean 0.748), and C3 is 0.74-0.865. C3's 0.865 is above
     the predicted 0.85.
   - The median recall at 25 ms of 0.57-0.61 excludes paired seed 1 (0.55).
   - The contract promised a random-store arm at every load and a separate 100-pair wrong-cue
     null. The code ran the random arm only at M = 1,000 and one 200-pair label-shuffled null.
   - The `dirty` flag was true on rows written while the results file had uncommitted appends.
     The code identity is shown by `git diff 19776f9 545d507 -- plant2` (empty). Records now
     also carry the plant2 tree hash and a plant2-only dirty flag, and the verdict row carries
     the digest and runtime.
9. **The convergence bar sits near the noise floor at high load.** Mean |dvbar| has a floor of
   about 0.065 mV at M = 1,000 that grows with load. Paired seed 5's 0.207 mV at M = 2,000 is
   plausibly a fluctuation. The rule was applied as written, and future contracts gate
   convergence on signed drift instead.
