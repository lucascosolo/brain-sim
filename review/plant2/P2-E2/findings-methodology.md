# P2-E2 review: methodology lens

Fresh reviewer given only the files (review packet in the workflow prompt; no implementer history). Model: session default. Run 2026-10-10. Recorded verbatim, before synthesis.

## Verdict

PASS is procedurally trustworthy. Contract 9f647b2 (07:59) precedes the code (driver file born 08:01, commit 6076a22); calibration took the one passing run 1.45-1.60 to J* = 1.525 exactly and was committed (52e5475) before gated seeds 6-10, which no earlier run touched; plant2/ is unchanged 19776f9..545d507; bars are P2-E1's; every gated number re-derives from plant2.jsonl. J* is not a disguised rescue. Weak spots: void controls that could barely fail, C5 a re-sample, a gate table that misstates K0.14, overstated sentences.

## Findings

### F1 [major] Gate table misstates K0.14 and understates the similarity

- where: docs/plant2/P2-E2-accommodation.md, 'The owner's closed gate' table; DECISIONS.md 2026-10-10 P2-E2 entry
- evidence: SPEC 2600-2603 and 2641: K0.14's theta_h is a slow per-neuron offset 'added to theta in the spike test' (v >= theta + theta_h), i.e. additive, not 'gain-like'. P2-E2 holds theta - vbar at 20 mV, a setpoint on mean distance to threshold, so 'no setpoint' is a stretch. Both are slow, per-cell, additive threshold homeostats. Real differences: controlled variable (mean V vs rate), continuous and unbounded, beside BTSP rather than replacing scaling, plant2.
- recommendation: Correct the table and DECISIONS before the owner rules: 'same family (slow additive intrinsic threshold homeostasis), different controlled variable and role'. My judgement: materially different from K0.14 as run, not a renamed re-run, but squarely in the family the gate names, so the ruling is genuinely the owner's.

### F2 [minor] Void controls could barely fail; 'no fixed threshold' rests on exploratory sweeps

- where: P2-E2 contract V-A/V-B; Result, 'What this shows'
- evidence: V-A at J* was near-certain to fail: fixed J 1.12 already gave C2 0.905-0.95 at M=1000, and reviewer seed 1 gave C2 0.005 at J 1.5. It was predicted <= 0.10 and gave 0.000-0.015. The fixed arm at J* passes M=250 and 500 on all 10 seeds. V-B can reach C1 only if the network over-ignites, which C2/C3 already exclude. My seed-0 check (exploratory): M=250 needs fixed J >= 1.25; at M=1000 no J in 1.10-1.35 passes (1.13: C1 0.885; 1.16: C2 0.895).
- recommendation: Label 'which no fixed threshold achieved' as exploratory (seeds 0-2). In later contracts make the void comparator an arm calibrated by the same rule on the held-out seed, not one fixed at the mechanism's own J.

### F3 [minor] C5 is non-vacuous in form only

- where: P2-E2 contract C5; Result C5 column
- evidence: Weights are frozen. The only carried state, vbar (tau 10 s), re-equilibrates within the 60 s (6 tau). My seed-0 run: after 40 s of background the signed drift is about -0.04 mV per 10 s. Phase 2 is therefore a fresh sample of the same equilibrium on another input stream. C5 minus C1 is -0.035 to +0.03, about +/-2 sampling SE (0.016 at 200 items). Nothing in the network can decay in 60 s, so C5 cannot detect a persistence failure.
- recommendation: Say this in an addendum. For Stage 1's 'after 60 s of ongoing activity', put ongoing learning of new items (or a load step) into the interval, so the criterion can fail for a reason other than noise.

### F4 [minor] Load independence holds only after the 50 s rest; reported offset is post-cue

- where: Result: 'load-independent operating point', 'Threshold offset at M = 1,000'
- evidence: My seed-0 runs at M=1000, J* (exploratory): testing straight after learning gives C1 0.875 (fail); vbar offset is 9.1 mV because learning simulates only the 200 ms item episodes. 5 s of background gives 0.915, 50 s gives 0.94. The equilibrium offset is 3.6 mV. The reported 6.0 mV is read after the test phase (half+novel cues 4.75, plus full cues 5.93). Test order has a small effect: novel cues first, mean ignition 1.1 -> 1.4.
- recommendation: State that the operating point is load-independent after >= 5-50 s of background following learning. Report offsets before the cues as well as after. Test an online protocol, with inter-episode background simulated, before Stage 4 relies on it.

### F5 [minor] Overstated sentences in 'What this shows'

- where: docs/plant2/P2-E2-accommodation.md, Result, 'What this shows'
- evidence: 'Unlearned cues ignite nothing': at M=1000 on gated seeds a novel cue ignites a median of 0.5-1 cell and at most 8-14. '>= 92 % of items': the gated minimum is 0.945 in phase 1 and 0.915 after 60 s; 0.92 comes from paired seed 4 (0.925). 'Load window running from 0.06': 0.0625 is the lowest load tested, not a measured edge. 'One J ... which no fixed threshold achieved' cites only exploratory sweeps (F2).
- recommendation: In an addendum, restate as measured: novel half cues ignite a median of 0-1 cells (max 14 of 4,000); >= 94.5 % of items on gated seeds (>= 91.5 % after 60 s); tested from 0.0625 to 0.25 items per cell.

### F6 [nit] Provenance and number slips in the Result

- where: Result header, Validity, Capacity edge and Predictions tables; plant2/record.py git_state
- evidence: The Result cites contract digest 1f2dcf7f19bf7073, which is P2-E1's; P2-E2 records carry ca482d31aa3f585d (calibration) and 4f625b7cf4dcfbf1 (seeds). 'Mean |A| 19.7-20.1 on every gated seed': gated seeds give 19.94-20.13. The capacity table says 'mean' but lists ranges; C2 at M=1,500 is 0.715-0.775, not 0.73-0.78. The predictions table's 0.69 is paired seed 5, and C3 0.865 is above the predicted 0.85 without a flag. 'dirty' reads true whenever the tracked JSONL has been appended.
- recommendation: Correct these in an addendum, leaving the Result text unedited. Exclude bench/results from the dirty check, or record a hash of the plant2/ sources in each record.

### F7 [nit] Convergence bar sits near the noise floor at high load

- where: p2_e2_accommodation.py settle(); validity 'converged'; seed 5
- evidence: My seed-0 run at M=1000: mean |dvbar| per 10 s window falls to a floor of about 0.065 mV, with signed drift within +/-0.05 after 40 s. The gated statistic rises with load (0.03 at M=250, 0.11-0.17 at M=2,000), so the fixed 0.2 mV bar gets stricter as load grows. Seed 5's 0.207 at M=2,000 is plausibly a fluctuation. The handling was honest: the rule was applied, not relaxed.
- recommendation: Keep the verdict as recorded. In future contracts, gate convergence on signed mean drift, or on drift against a longer reference window, not on mean |dvbar|.

### F8 [nit] Store-identity check compares against today's code, not P2-E1's artifacts

- where: p2_e2_accommodation.py run_seed (plain = e1.E1(c, seed))
- evidence: The check confirms that test phases do not perturb learning, since E2 inherits learn(). It does not compare against what P2-E1 produced. My independent check: the seed-1 store from current code matches P2-E1's seed1.npz per-cell strong counts and plateaus, and its store_size (930,107). Its digest 65feccd3bab338a7 equals the P2-E2 record's. So the claim holds.
- recommendation: Record a per-seed store digest in P2-E1-type records so that later experiments can cross-check against committed artifacts instead of re-running the same code.

## Proposed next experiment

- mechanism: P2-E3, content completion (Stage 1's next clause), labelled proxy: a plateau-gated binary back-projection (Willshaw-style clipped Hebbian write; cf. hippocampal back-projections). An input-mirror LIF layer has one cell per input line, driven 1:1. When an item plateaus, memory->mirror synapses from each plateau cell to that item's eligible lines are set strong, once. Everything else is P2-E2: stores, J* 1.525, accommodation, protocol and bars.
- why: Stage 1 requires the half cue to regenerate the missing half of the input; P2-E2 shows only that the memory cells answer. It is a lasting, specific, experience-driven change with inspectable binary state, and no homeostat touches written synapses (the plant's failure). The readout is the input itself, not a cell set the experimenter assigned. Count estimate: an item line gets about 16-19 strong inputs from responding assembly cells; a non-item line gets about 2.4 at M=1000.
- kill_test_sketch: Contract before code. J_back is calibrated on held-out seed 0 by P2-E2's midpoint rule; seeds 11-15 are fresh. PASS iff, with one J_back, at M=250, 500 and 1000 on every seed: >= 90 % of cued items regenerate >= 80 % of their missing-half lines within 100 ms; >= 90 % of cues fire < 5 non-item mirror cells; >= 90 % of novel half cues regenerate < 5 lines. VOID if a label-shuffled back-store with the same per-cell counts passes. The 60 s interval includes 50 new items. Reported: a static per-cell offset arm.
- predicted_outcome: From counts (to be replaced, before any gated seed, by a seed-0 item-level simulation in the contract): at M <= 1000, >= 80 % regeneration for 0.93-0.99 of items; false lines median 0-2 per cue; novel cues regenerate a median of 0 lines. The edge coincides with P2-E2's specificity edge: false lines climb steeply at M = 1,500-2,000 (non-item lines about 4-5 strong inputs, plus 4-15 spurious memory responders). Chance of PASS about 60 %.
- risks: If the owner rules accommodation under the gate, the base is withdrawn, and the fixed threshold fails C1 at M=1000; get the ruling first. Mirror cells receive load-dependent back-projection background; needing their own operating point would be a second mechanism, so estimate it before the contract. The write rule is Willshaw-style, not BTSP; label it. Memory responders peak near 22 ms, so regeneration lands late. Content capacity inherits the 0.25-0.375 items/cell edge.
- alternatives_rejected: Capacity growth with cell count: STAGES says it needs its own signal-to-noise mechanism, and scaling alone breaks 'scale only when it improves stated metrics'. Recurrent completion inside the memory layer: runs away without a stabiliser (P2-E1 direction F6). Centred FFI: needs store bookkeeping for its gain. An online re-gate of P2-E2, or a static-offset ablation: robustness and diagnosis, no new capability; kept as reported arms.

## For the owner

Rule on the gate first. P2-E2 is a slow, additive, per-cell threshold homeostat on mean membrane potential: the same family as K0.14, whose offset was also additive (the contract's table says otherwise), but it controls voltage rather than rate and has a different role and network, so it is not a renamed re-run. If you allow it, the PASS stands: fresh seeds, a predeclared J rule applied exactly, numbers that reproduce. Ask for an addendum that fixes the overstated sentences and the wrong digest, and that says the result needs a rest of 5-50 s before testing (seed 0: C1 0.875 with none).
