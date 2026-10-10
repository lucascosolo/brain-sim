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

(appended after the run)
