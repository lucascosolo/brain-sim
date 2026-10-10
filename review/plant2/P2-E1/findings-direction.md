# P2-E1 review: direction lens

Fresh reviewer given only the files (review packet in the workflow prompt; no implementer history). Model: session default. Run 2026-10-10. Recorded verbatim, before synthesis.

## Verdict

The FAIL is trustworthy and mostly read correctly. The contract (cb6883b) came before the code (749caee). All records point at that clean commit. A diff shows only the Result section was added. My separate vectorised re-implementation reproduced the capacity curve: C1 0.605/0.675/0.83/0.99 against the measured 0.61/0.635/0.84/0.975. A fixed-threshold J scan on seeds 1-2 (exploratory) found no J that passes at both M=250 and M=1000, so the claim of no load-independent operating point holds. One nuance: only about half of the load drift is background. The other half is other memories' synapses on the cue's own lines.

## Findings

### F1 [minor] Only about half of the diagnosed load drift is background

- where: docs/plant2/P2-E1-btsp.md, Result, 'Why C1 fails'
- evidence: plant2/predict.py at J=1.12 for a written cell with 25 own cue synapses and k=5 plateaus: recall 0.818 with neither, 0.955 with background only, 0.923 with cue overlap only, 0.983 with both. The cue adds 50 x 39.5 = 1975 Hz, about as much as the whole background (2000 Hz). So other items' strong synapses on the cue lines drive about 45 % of the load effect.
- recommendation: State in the P2-E2 contract that a mechanism tracking mean potential removes only the background part. The cue-overlap part stays, and it sets the C2/C3 capacity edge. Predict that edge.

### F2 [major] Candidate (a) borders the owner's closed intrinsic-homeostasis gate

- where: docs/recovery/project-facts-2026-10-03.md:47; plant2/predict.py (accommodation option, commit 5bcf3b9)
- evidence: The closed gates list 'I_GAIN / rejected intrinsic homeostasis as previously run'. The rejected mechanism was K0.14, a threshold offset driven by a rate setpoint (SPEC around line 2593). The predictor already has an accommodation term, added before any P2-E2 contract exists.
- recommendation: The P2-E2 contract should cite the gate and list the differences: no rate setpoint, no spike counting, an additive offset rather than a gain change, and no synapse touched. Record it in DECISIONS.md and flag it to the owner. Write no network code for it before the contract is committed.

### F3 [major] Accommodation needs a new J, which can look like rescuing P2-E1 by changing J

- where: P2-E1 Decision clause; P2-E2 design
- evidence: Exploratory, seed 1. With accommodation at J=1.12, C1 falls to 0.25 at M=250 and 0.165 at M=1000, below the fixed threshold's 0.61 and 0.84. The background was helping the written cells. With a fixed threshold, J=1.5 or 1.7 gives C2 of 0.005 or 0.0 at M=1000.
- recommendation: Fix J before the run by a stated calibration on a held-out seed (not seeds 1-5). Also run a fixed-threshold arm at the same J on the same store and spikes. That arm must fail C2 or C3 at M=1000; if it does not, the mechanism is decorative and the run is void.

### F4 [major] The gate must test load independence directly

- where: P2-E2 kill test design
- evidence: P2-E1 gated a single load, which cannot tell a missing operating point from a thin margin. Fixed threshold, seed 2 (exploratory): J=1.12 gives C1 0.58 at M=250. J=1.2 gives C1 0.815 at M=250 and C2 0.72 at M=1000. Neither passes both loads.
- recommendation: PASS only if one predeclared J and tau pass C1-C5 at M=250, 500 and 1000 on all 5 seeds. Report M=1500 and 2000 with predicted numbers.

### F5 [minor] Feedback inhibition or k-WTA (c) cannot satisfy C3

- where: candidate (c)
- evidence: Exploratory, M=1000. Global feedback inhibition at J=1.5, J_I=0.3 mV: C3 0.04 (median ignition 20), C2 0.775. At J_I=1.5: C1 0.35-0.50. A WTA always picks winners, even for unlearned cues. Wu & Maass name not needing a global WTA as an advantage of BTSP.
- recommendation: Reject (c) for P2-E2. Bring inhibition in later as a stabiliser for recurrence, under a bar that keeps novelty detection.

### F6 [major] Recurrent co-plateau links (d) run away, at a load-dependent edge

- where: candidate (d); SPEC 8.7
- evidence: Exploratory, links with p=0.5 and no inhibition. M=250, J=1.12, J_rec=2 mV: one cue ignited 2,889 of 4,000 cells and the activity never stopped. M=1000 with accommodation, J_rec=1.5: 3,969 cells still active after 2 s. J_rec=1.0 completed the assemblies (12->16 and 18->21 of 16 and 21) without runaway at M=250.
- recommendation: Order (d) after (a), with (c) as its stabiliser, under its own contract with a bar on spontaneous and self-sustained ignition.

### F7 [minor] Accommodation habituates to repeated cues and depends on the test protocol

- where: P2-E2 reported measures; later Stages 4 and 6
- evidence: Exploratory, M=1000, J=1.6. The same half cue shown 10 times at the protocol's one-third duty cycle: mean recall 0.945 -> 0.84-0.90 at tau 1 s, 0.958 -> 0.91-0.93 at tau 3 s, flat at tau 10 s. Fixed threshold and centred FFI stay flat. This will work against persistent activity in Stage 6.
- recommendation: Use tau_acc >= 2 s. Report a repeated-cue arm. Keep vbar as state that net.quiet() does not reset, and settle it for 5 tau before testing.

### F8 [minor] The capacity edge only just clears the Stage 1 load

- where: STAGES.md Stage 1 gate (>= 0.25 items/cell; linear growth)
- evidence: Exploratory, with accommodation. C2/C3 0.55-0.80 at M=1500 and 0.17-0.27 at M=2000. The J window at M <= 1000 is about 1.52-1.68 mV (+/-5 %). Analytic check: ignition is about the sum over cells of P(Poisson(S_i/80) >= ~13), and it matches the medians.
- recommendation: Treat linear capacity growth with n as needing a separate signal-to-noise mechanism: sparser codes with more inputs, recurrent completion, or matched inhibition. Do not credit it to (a).

### F9 [minor] Per-cell centred feedforward inhibition is the strongest alternative but needs S-matched gain

- where: candidates (b), (f) and centred FFI
- evidence: Exploratory, inhibition of J*S_i/m per input spike. At J=2.0, M=1000: C1 0.995-1.0, C2 0.97-0.985, C3 0.99-1.0, with no habituation. Global FFI with a fixed gain (b) is not load-independent: J=1.6 gives C1 0.765 at M=250; J=1.9 gives C2 0.125 at M=1000.
- recommendation: Keep centred FFI as the fallback or P2-E3 comparator. Its per-cell gain has to come from bookkeeping on the store or from inhibitory plasticity (the owner's wall). Proxy label if used: Xue, Atallah & Scanziani 2014.

### F10 [nit] Controls: the all-zero twin is trivial; check that the store is reused

- where: plant2/experiments/p2_e1_btsp.py run_seed (twin)
- evidence: The never-trained twin has no weights, so 0 responders is guaranteed. BTSP never reads memory spikes and the random streams are keyed by purpose, so each P2-E2 seed's store can be bit-identical to P2-E1's.
- recommendation: Add a label-shuffled control (same store, A(x) permuted across items) as the chance baseline. Make 'store digest equals P2-E1's' a validity check, so only the readout changes.

## Proposed next experiment

- mechanism: Slow threshold accommodation (a), labelled proxy for slow Na+ inactivation or K+ currents. Each memory cell's threshold is -50 mV + (vbar_i - v_rest). vbar_i is an exponential average of the cell's own membrane potential, tau_acc = 2 s. There is no rate setpoint and no synapse changes. Everything else stays as in P2-E1, with the same store per seed.
- why: It targets the drift that was diagnosed. It is local and per cell, so it can be sharded with no global signal. It is one inspectable scalar per cell. It is an additive offset, so it cannot erase writes or make fewer inputs stronger (the 8.33/8.49 failures). It also cancels the extra background drive that recurrent links will add later (the 8.7 failure). In my exploratory sim the fixed threshold has no J that passes both M=250 and 1000; with accommodation, J of about 1.6 passes both on seeds 1-2.
- kill_test_sketch: Seeds 1-5; P2-E1 stores, protocol and bars unchanged. J fixed in advance: grid 1.40-1.90 in steps of 0.05 on held-out seed 0 at M=250/500/1000, J = midpoint of the passing window; an empty window means FAIL. PASS iff with that one J, on every seed and at each of M=250, 500, 1000, C1-C4 >= 0.90 and C5 holds. A fixed-threshold arm at the same J must fail C2 or C3 at M=1000, else the run is void. vbar is settled for 5 tau first. Reported, not gated: M=1500/2000, recall at 25 ms, a repeated-cue arm, a shuffled control.
- predicted_outcome: Exploratory figures from my re-implementation, seeds 1-2. J window about 1.52-1.68, so J about 1.6. C1 0.95-0.99 at each load (P2-E1: 0.58-0.86). C2/C3 1.00 at M <= 500 and 0.93-0.99 at M=1000. Old-item recall (C4) >= 0.93. Fixed arm at J=1.6: C2 0.00-0.05 at M=1000. Median recall at 25 ms about 0.55 (P2-E1: 0.42-0.48). C2/C3 0.55-0.80 at M=1500 and 0.15-0.30 at M=2000. Chance of PASS about 75-85 %.
- risks: C2 at M=1000 clears 0.90 by only 0.01-0.07 (0.91 at J=1.65 on seed 2). The owner may count it under the closed intrinsic-homeostasis gate. Recall falls 0.03-0.10 over 10 repeated cues at tau 1-3 s, and accommodation will work against Stage 6 persistent activity. J rises about 43 % over P2-E1, so the calibration and the control must carry the case for it. Capacity stays near 0.3 items per cell because cue-overlap noise is untouched. How vbar starts, and what quiet() does to it, can bias C3.
- alternatives_rejected: (b) global FFI with a fixed gain: no load-independent J (C1 0.765 at M=250 for J=1.6; C2 0.125 at M=1000 for J=1.9). (c) feedback k-WTA: always finds winners, C3 0.04. (d) recurrent links: 2,889-3,969 cells stay active at J_rec 1.5-2 mV, the 8.7 failure. (e) count normalisation: erases writes and rescales gain, the 8.33/8.49 failures. (f) iSTDP: blocked by the owner's wall. Centred FFI: best margins but needs S-matched inhibition, so it is kept as the comparator.
