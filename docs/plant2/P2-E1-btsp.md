# P2-E1: one-shot episodic storage by behavioural-timescale plasticity (predeclared 2026-10-10)

Stage 1 of `docs/plant2/STAGES.md`, first experiment of the plant2 line. Everything in this
file down to "Result" is written and committed before any P2-E1 code exists and before any
P2-E1 run. The result is appended below it; nothing above it is edited afterwards.

## Why the prior approaches failed (from the record)

K1.1 asks for the half cue to re-evoke >= 80 % of a 1-20 cell assembly within 50 ticks after
one showing. It failed on the master plant (1/16, SPEC 8.2) and under every labelled proxy
stacked on it (8.3-8.12, best 5/16). The 8.46 line reached 13/16 on four seeds of six, then
lost about half its gain in 10 s (8.48), mostly to synaptic scaling (8.49). The record names
the causes:

1. **The rule needs timing the stimulus does not supply.** Pair STDP's uncorrelated fixed
   point is 0.45 `w_max`; homeostasis rests weights at 0.6-0.75. Potentiation then needs a
   causal:anticausal excess of about 3.6:1. Natural onsets give 1.8, imposed volleys 3.0, so
   co-activity depresses the used pathway (K0.13: 0.750 -> 0.655 `w_max`, evoked response
   halved; 8.19, 8.20).
2. **The homeostat erases the write.** Scaling and rate-driven elimination act on the written
   synapses within one to three 1-s sweeps and back each other up (8.3, 8.13, 8.14, 8.18).
3. **The code is dense.** A 40-cell patch drives a cortex whose background is 19 % of cells
   per 50 ticks; local Hebbian rules separate inputs only by their rate ratio, about 2 (8.20,
   8.22, 8.23).
4. **The wiring caps recall.** A memory cell had about 2 recurrent inputs from its own
   assembly; with oracle weights at the bound no arm completes in 50 ticks (8.23, 8.24).

## Hypothesis

A plasticity rule that writes in one exposure without depending on postsynaptic spike timing,
with bounded binary weights and no homeostat acting on them, stores many items shown once each
in a spiking network. Partial cues then re-evoke the written cells quickly and specifically.

The rule is behavioural-timescale synaptic plasticity (BTSP) as simplified by Wu & Maass
(2025, Nat Commun 16:342, Eq. 1): a dendritic plateau in a CA1 cell opens a window of seconds
in which each active input synapse flips its binary weight with probability 0.5. It was
measured in awake CA1 (Bittner et al. 2017; Milstein et al. 2021). Wu & Maass showed it in
non-spiking threshold units, with thresholds found by grid search. This experiment asks whether
it holds with Poisson spiking inputs, ongoing background activity, LIF integration, a 50 ms
recall window and a synaptic strength fixed by a rule written before any run.

It addresses causes 1-4 as follows. 1: no spike-timing dependence. 2: no homeostat touches
the written synapses. 3: inputs are sparse (2.5 % active) and plateau cells are 0.5 %. 4: one
synapse from input to memory cell, with about 25 written synapses active under a half cue.

## One mechanism

BTSP on the input -> memory synapses. Nothing else in the network is plastic. There is no
inhibition, no recurrence, no homeostasis, no adaptation, no noise current, and nothing is
injected into memory cells.

## Network (all values fixed here)

- `inp`: m = 4,000 Poisson spike sources. **Labelled proxy** for the CA3/entorhinal input
  that carries an experience. An item makes a = 100 of them (f_p = 2.5 %) fire at 40 Hz. All
  others fire at 0.5 Hz (background). Items are drawn uniformly without replacement for each
  item and independently across items.
- `mem`: n = 4,000 LIF cells. tau_m 20 ms, rest -70 mV, fixed threshold -50 mV, reset -65 mV,
  refractory 2 ms, dt 1 ms, forward Euler as in the plant. Delta synapses with a 1 ms delay.
- `inp -> mem`: every pair is a potential synapse with a binary weight w in {0, 1}. A spike on
  a w = 1 synapse adds J = **1.12 mV** to the membrane; w = 0 transmits nothing. All weights
  start at 0. The store is sparse and holds only the w = 1 synapses.

**J by a rule fixed before any run.** Set J so that the predicted mean free-membrane
depolarisation of a written cell under its half cue, at the full load M = 1,000, is 1.4 x the
20 mV distance from rest to threshold. Prediction: an active input is eligible with
probability P(Poisson(8) >= 3) = 0.98625; a background input with P(Poisson(0.1) >= 3) =
0.000155. One plateau writes 49.6 strong synapses. A written cell has 24.66 strong synapses
on the half cue's 50 inputs. Its other (M - 1) f_q = 5.0 plateaus give 247.8 strong synapses,
3.10 of them on the cue. Input rate = 40 x 27.76 + 0.5 x 269.8 = 1,245 Hz. Mean depolarisation
= 1,245 x 0.020 s x J = 28 mV, so J = 1.1245, rounded to 1.12 mV. No other value of J is run.

## Learning (one exposure per item)

M = 1,000 items, each shown once for 200 ms. Each item is an episode; the BTSP window spans
its episode. Episodes are separated by quiet time that is not simulated: nothing can change
the weights without a plateau, and plateaus occur only inside episodes.

- **Plateaus (labelled proxy for entorhinal-layer-III instructive input).** During each
  episode each memory cell independently has a plateau with probability f_q = 0.005 (Wu &
  Maass's value from Grienberger & Magee 2022). They are drawn from their own random stream
  and are independent of the item's content and of any cell's activity. A plateau injects no
  current and makes no cell fire. It only gates plasticity. A(x), the cells that had a plateau
  for item x, is the item's **written assembly**.
- **Eligibility (labelled proxy for the seconds-long eligibility trace).** An input is
  eligible for the episode if it spiked >= 3 times during the 200 ms.
- **BTSP update** at the end of the episode, for each plateau cell i and each eligible input
  j: with probability 0.5, w_ji <- 1 - w_ji. That is, 0 becomes 1 and 1 becomes 0, as in Wu &
  Maass Eq. 1. The coin flips have their own random stream. The update does not read the
  memory cells' spikes.

## Test (learning off: no plateaus, no weight change)

Cue set: the 100 oldest items (1-100), plus 100 drawn uniformly from items 101-1,000 with a
fixed seed. Novel set: 200 fresh random items with the same statistics, never shown.
Each cue is shown for 100 ms, followed by 200 ms of background, so cells return to rest.
- **Half cue:** a fixed random half (50) of the item's 100 inputs fire at 40 Hz. The other 50
  stay at background.
- **Full cue:** all 100 fire. This is a latency reference only.
- A memory cell **responds** if it spikes at least once in [onset, onset + 50 ms).

Per learned item x: recall(x) = |responders to half cue ∩ A(x)| / |A(x)|, and spurious(x) =
|responders to half cue not in A(x)|. Per novel item y: ignition(y) = |responders to its half
cue|.

## Kill test

Seeds 1-5. Each seed is a separate network, item set, input-spike stream, plateau stream and
coin stream. **PASS only if every criterion holds on every seed.**

- **C1 completion:** recall(x) >= 0.80 for >= 90 % of the 200 cued items.
- **C2 specificity:** spurious(x) < 0.5 |A(x)| for >= 90 % of the cued items.
- **C3 no ignition by unlearned cues** (the control that replaces the never-trained twin,
  which has all-zero weights and cannot respond): ignition(y) < 0.5 x mean |A| for >= 90 %
  of the 200 novel items.
- **C4 retention under interference:** C1 and C2 also hold within the 100 oldest items
  alone, which were followed by 900 or more later one-shot writes.
- **C5 persistence in time:** after 60 s of background-only activity (plateaus off), C1-C3
  hold again on the same cues. Weights cannot change without a plateau, so C5 checks that
  nothing else drifts. It is stated now as a property by construction, not as evidence of a
  consolidation mechanism.

**Validity** (a failure makes the run invalid, not a result): mean eligible fraction of active
inputs during learning >= 0.95; the strong-synapse set is bit-identical before and after
every test phase; mean |A| over the 1,000 items is within 20 +/- 1.5.

**Decision.** PASS: BTSP becomes plant2's Stage 1 storage rule. The next experiment is content
completion: the half cue regenerates the missing half of the input. FAIL: record which
criterion failed and why. J, f_q, rates, durations and thresholds are not changed to rescue
it, and this line stops. A further Stage 1 experiment then needs a different mechanism and its
own contract.

## Predictions (written before any code)

- Mean |A| = 20.0 (sd 4.5). Strong synapses per cell about 50 per plateau received, about
  250 on average at M = 1,000. The store holds about 1.0 x 10^6 of the 1.6 x 10^7 possible
  synapses.
- Written cell under its half cue: mean 27.9 mV, sd 3.95 mV, against the 20 mV distance to
  threshold. The deterministic first-spike time is about 25 ms. Cells whose cue-active strong
  synapses fall about 2 sd low (about 3 %), or that have few other plateaus, may miss the
  50 ms window. Predicted median recall 0.90-0.95. **C1 is the criterion most at risk**: if
  per-cell recall falls to 0.85, about 83 % of items reach 0.80 and C1 fails.
- Non-written cell with k plateaus under any half cue: mean 1.10 k mV, sd about 0.8 sqrt(k)
  mV. Cells with k >= 12 (about 22 of 4,000 at M = 1,000) can cross threshold. Predicted
  spurious and novel ignition about 3 cells per cue (bar about 10). C2 and C3 pass.
- An old item's written synapses are flipped by later plateaus on the same cell only through
  overlaps (about 2.5 inputs per later item, half each way), so they do not decay on average.
  C4 passes, with recall for the oldest items within 0.03 of the rest.
- C5 passes by construction.
- Full cue: recall about 1.0, first spikes 10-15 ms after onset.

## Reported, not gated

- Recall at 25, 50 and 100 ms.
- Recall against |A(x)|, item age and the cell's plateau count.
- Strong-synapse distribution, and cells that respond to more than 5 % of cues (hubs).
- Latency for half and full cues.
- Never-trained twin response (predicted 0).
- Wall time.
- **Capacity curve** on seed 1 with J fixed at 1.12 mV: M = 250, 500, 1,000, 2,000 and 4,000
  with the same criteria. Prediction: C2 and C3 fail first as M grows, because hub cells
  accumulate strong synapses (mean drive about 1.1 k mV for k plateaus). That is the limit a
  later mechanism would have to move.

## Files

- `plant2/engine.py`: LIF populations, Poisson sources, sparse projections with delays.
- `plant2/btsp.py`: binary sparse synapse store and the BTSP update.
- `plant2/experiments/p2_e1_btsp.py`: driver and JSONL record.
- `plant2/tests/`: unit tests, and a kill-test wrapper marked `slow`.
- Results are appended to `bench/results/plant2.jsonl`. Derived data and logs go under
  `~/.cache/brain-sim/plant2/`.

## Result

**FAIL (2026-10-10, commit 749caee, contract digest 1f2dcf7f19bf7073, all five seeds valid).**
C1 fails on every seed. C4 fails on its recall half, and C5 fails because C1 fails again after
the 60 s. C2 and C3 pass on every seed. Records: `bench/results/plant2.jsonl` (`kind`
`kill_test_seed`, `kill_test_verdict`, `capacity_point`). Log and per-item arrays:
`~/.cache/brain-sim/plant2/p2_e1/`. Wall time is about 55 s per seed on 4 cores.

| seed | C1 (bar 0.90) | C2 | C3 | C4 recall / spurious | C5: C1 / C2 / C3 after 60 s | median recall at 25 / 50 / 100 ms | half / full latency, ms | median spurious, ignition | hubs |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **0.840** | 0.925 | 0.955 | **0.820** / 0.940 | **0.835** / 0.940 / 0.950 | 0.42 / 0.929 / 1.00 | 27 / 10 | 2 / 2 | 10 |
| 2 | **0.845** | 0.935 | 0.980 | **0.830** / 0.950 | **0.840** / 0.950 / 0.965 | 0.44 / 0.920 / 1.00 | 26 / 10 | 2 / 2 | 5 |
| 3 | **0.860** | 0.950 | 0.970 | **0.890** / 0.950 | **0.880** / 0.955 / 0.990 | 0.46 / 0.941 / 1.00 | 26 / 10 | 2 / 2 | 8 |
| 4 | **0.810** | 0.925 | 0.945 | **0.820** / 0.920 | **0.825** / 0.960 / 0.940 | 0.48 / 0.929 / 1.00 | 25 / 10 | 2 / 2 | 10 |
| 5 | **0.850** | 0.905 | 0.945 | **0.880** / 0.930 | **0.845** / 0.900 / 0.970 | 0.45 / 0.923 / 1.00 | 26 / 10 | 2 / 2.5 | 13 |

**Validity.**
- Eligible fraction 0.987-0.988 (bar 0.95).
- Mean |A| 19.74-19.98 (bar 18.5-21.5).
- The strong-synapse set was bit-identical before and after both test phases and the 60 s.
- The never-trained twin answered 0 cells to every one of its 20 half cues on every seed.

**Predictions against outcome.**

| prediction | outcome |
|---|---|
| Store size about 1.0 x 10^6 | 0.92-0.93 x 10^6 |
| About 250 strong synapses per cell | 230-234 |
| Mean |A| 20.0 | 19.74-19.98 |
| Eligibility 0.986 | 0.987 |
| Median recall 0.90-0.95 | 0.920-0.941 |
| C1 the criterion most at risk | right: it is the criterion that failed |
| Half-cue first spikes about 25 ms after onset | median latency 25-27 ms |
| Full-cue latency 10-15 ms | 10 ms |
| Spurious and ignition about 3 | median 2 |
| Old items within 0.03 of the rest | 0.907-0.946 against 0.915-0.929 |
| C2 and C3 fail first as M grows (capacity curve) | right at M = 2,000 |
| (not predicted) | **C1 is worse at low load** |

**Why C1 fails.** The written cells fire, but too late. Median recall is 0.92-0.94 at 50 ms
and 1.00 at 100 ms; at 25 ms it is 0.42-0.48. About 1 cell in 13 crosses threshold after
the 50 ms window. Pooled over seeds, a written cell's recall rises with the number of
plateaus it has received for other items: k = 1: 0.73, 3: 0.82, 5: 0.88, 7: 0.92, 9: 0.94,
>= 12: 0.98. Other items' strong synapses carry background spikes, which raise the cell's
resting depolarisation and bring the half cue's push nearer to threshold. The failing items
are mostly marginal (recall 0.70-0.79, one or two of about 20 cells late).

**The capacity curve** (seed 1, J fixed; reported, not gated) shows that this is not a margin
problem at one load. It is the absence of an operating point:

| M (items per cell) | C1 | C2 | C3 | median recall | median spurious / ignition | hubs | strong per cell |
|---|---|---|---|---|---|---|---|
| 250 (0.06) | 0.610 | 1.000 | 1.000 | 0.842 | 0 / 0 | 0 | 61 |
| 500 (0.13) | 0.635 | 1.000 | 1.000 | 0.875 | 0 / 0 | 0 | 120 |
| 1,000 (0.25) | 0.840 | 0.925 | 0.955 | 0.929 | 2 / 2 | 10 | 233 |
| 2,000 (0.5) | 0.975 | 0.000 | 0.000 | 1.000 | 111 / 113 | 756 | 441 |
| 4,000 (1.0) | 1.000 | 0.000 | 0.000 | 1.000 | 1,815 / 1,774 | 3,797 | 782 |

The M = 1,000 point reproduces the kill test's seed 1 numbers exactly, as the separate random
streams were designed to.

Every cell's excitability is set by how much the network has stored, not by the cue. A cell
with few writes sits near rest, so the half cue alone is slow. A cell with many writes sits
near threshold, so any cue fires it. The fixed J was placed by its rule at the only load where
the two effects nearly balance, and even there completion misses the bar.

**What this run does show.** BTSP writes one-shot, specific, inspectable traces in a spiking
network:
- the right cells, with about 2 spurious per cue;
- no response to unlearned cues;
- no loss for the oldest of 1,000 items;
- nothing erased by 60 s of ongoing activity;
- full cues recalled at 1.00 within 10 ms.

None of that is the Stage 1 gate.

**Decision (per the contract).** P2-E1 FAILS. J, f_q, rates, windows and bars stay as they
are, and this configuration is not re-run to pass. The diagnosis points to a missing mechanism
that holds each cell's operating point independent of load. The next Stage 1 experiment
carries such a mechanism under its own contract.

**Contract wording, corrected here and not above.** The network section says "forward Euler as
in the plant". The plant's membrane update is exact exponential leak decay plus delta inputs
(`brainsim/engine.py`, `_m_decay`), and the code implements that, as "as in the plant"
intends. At dt 1 ms and tau 20 ms the leak factors are 0.9512 (exact) and 0.9500 (Euler).

## Addendum after independent review (2026-10-10)

Three fresh reviewers (methodology, code, direction) checked P2-E1 from the files alone. Their
findings are verbatim in `review/plant2/P2-E1/`, and each decision is in `review/ledger.jsonl`.
The verdict stands: **FAIL, trustworthy**.
- Two reviewers recomputed every number.
- One reran seed 1 and got C1 0.840 again.
- A dense float64 LIF replay of the seed-1 store matched the engine spike for spike.
- A dense toggle model matched the sparse BTSP store over 3,600 updates.

The corrections below replace the statements they name. Nothing above "Result" is edited.

1. **The J rule double-counted 3.1 cue synapses.** BTSP toggling leaves each of a written
   cell's own item inputs at P(strong) = 0.5 whatever later plateaus do. Later items' strong
   synapses on the cue lines are therefore the same synapses, not extra ones.
   - Measured on seed 1: 24.69 cue synapses per written cell (sd 3.55), flat in k (24.5-24.8),
     not the predicted 27.76.
   - The mean half-cue drive was about 24.9 mV, 1.24x the distance to threshold, not 1.4x.
     The rule computed correctly would have given J of about 1.26 mV.
   - The verdict does not depend on this, because J = 1.12 was fixed explicitly. But "C1 the
     criterion most at risk: right" is an artefact of the error. One reviewer's sweep at
     J = 1.25 (exploratory, seed 1) gave C1 0.99, C2 0.445, C3 0.57: at the intended margin
     the run fails on specificity instead.
2. **"Why C1 fails": corrected figures.**
   - The cell-level miss rate is 10.2-11.9 % (about 1 in 9), not "1 in 13".
   - Failing items have 3-14 late cells (median 5-6), not one or two, and 34-45 % of failing
     items have recall below 0.70.
   - k counts all of the cell's plateaus, this item's included.
   - Item recall is overdispersed: sd 0.105-0.127 against about 0.07 for independent cells,
     because all cells of an assembly share one cue spike train and mask. C1 is therefore
     5-6 points below what independent per-cell recall implies.
3. **"No operating point" rests on reviewer sweeps, not on the run.** The capacity curve is
   one seed (nested prefixes of seed 1, n = 1 per point). The reviewers' exploratory engine
   sweeps (seeds 1-2, not recorded as results) support the claim: no single fixed J passes
   C1-C4 at M = 1,000 (J = 1.16: C1 0.915, C2 0.84; J = 1.20: C1 0.945, C2 0.69), or at both
   M = 250 and 1,000.
   - Two terms contribute about equally to the load effect: background spikes on other items'
     strong synapses, and other items' strong synapses on the cue's own lines (the cue adds
     about 1,975 Hz, comparable to the whole background).
   - Widening the window trades C1 for C2: at 75 ms, C1 0.99 and C2 0.72.
4. **C5 and the never-trained twin are vacuous.** `present()` calls `net.quiet()`, which resets
   all dynamic state, and nothing changes weights without a plateau. So the 60 s cannot affect
   anything measured: C5 is C1 re-measured with a new input-noise draw (draw-to-draw noise
   about 0.02). The twin has no weights. The result bullet "nothing erased by 60 s of ongoing
   activity" is a design property, not evidence. Nulls with teeth, run by a reviewer on the
   seed-1 store:
   - 200 background-only 50 ms windows gave 0 responders;
   - another item's half cue recalled 0.006 of A(x).
5. **Overstated bullets, restated as measured.**
   - Unlearned cues: median ignition 2, maximum 15-21 per seed, about one assembly; C3
     0.945-0.98.
   - Full cues: median first-spike latency 10 ms, recall 1.00 at 50 ms.
   - Spurious: median 2 per cue, with C2 at 0.905 and 0.900 on seed 5.
6. **Lineage and deviations from Wu & Maass 2025.**
   - The half cue (50 % masked) is the inherited K1.1 bar. It lies outside the paper's
     demonstrated regime: one third masked at f_q 0.005.
   - The paper defines a trace by the full-cue response and sets thresholds by grid search or
     scales them with input activity. Here the trace is the plateau set, there is one fixed
     threshold, and connectivity is full.
   - These make the test stricter, not easier.
7. **What A(x) is.** The written assembly is a random code assigned by content-independent
   plateaus. Stage 1 measures whether an assigned code can be read back from a partial cue. It
   says nothing about the system choosing its own representations (Stage 3), and a Stage 1
   pass is not evidence of thinking power.
