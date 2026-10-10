# P2-E1 review: methodology lens

Fresh reviewer given only the files (review packet in the workflow prompt; no implementer history). Model: session default. Run 2026-10-10. Recorded verbatim, before synthesis.

## Verdict

The FAIL is trustworthy; parts of its interpretation are not. The contract (cb6883b) was committed before the code (749caee), and the code before any run (cache and pytest dirs postdate it). The code follows the contract: its parameters, windows, eligibility, plateau independence, flip rule, test sets, criteria arithmetic and validity checks. I re-derived every table number from the JSONL and npz files, and my rerun of seed 1 gave C1 0.84, C2 0.925, C3 0.955 again. The problems: the J rule double-counted cue synapses, so the real margin was 1.24x, not 1.4x. At the correctly computed J the run still fails, but on C2/C3. Several shown-capability claims are overstated, C5 included.

## Findings

### F1 [major] J rule double-counts 3.1 cue synapses; the real margin was 1.24x, not 1.4x

- where: docs/plant2/P2-E1-btsp.md, 'J by a rule' and Predictions; Result predictions table
- evidence: After x's write, each input x shares with a later item still has P(w=1)=0.5, whatever later flips happen, so the expected strong cue synapses stay at 24.66 for every k. Seed 1 measured 24.8 (k=1), 24.7 (k=6), 24.5 (k=8); the contract said 27.76. Mean drive is 24.9 mV (1.24 x 20 mV), not 27.9. The correct J is about 1.26 mV. My sweep at J=1.25 gave C1 0.99, C2 0.445, C3 0.57. The table leaves out the 27.9 mV prediction.
- recommendation: Add a correction to the Result: the verdict stays FAIL, but the failing criterion and 'C1 the criterion most at risk: right' come from the arithmetic error. The next contract should log measured vs predicted cue synapses per written cell, and a small pre-run test should check the drive formula.

### F2 [major] C5 cannot fail, yet the Result lists it as something the run shows

- where: plant2/experiments/p2_e1_btsp.py present() (net.quiet()) and run_seed; Result 'What this run does show'
- evidence: Weights cannot change without a plateau. present() also calls net.quiet() first, which resets v, the delay ring and refractory state. So the 60 s background leaves no trace, and phase 2 is phase 1 with new input noise (C1 0.825-0.88 against 0.81-0.86). The contract honestly calls C5 'by construction'. The Result still lists 'nothing erased by 60 s of ongoing activity' as a finding.
- recommendation: Restate the bullet as a design property, not evidence. Before any adaptive state exists, change the phase-2 test so it starts from the post-60 s state. quiet() must never reset adaptive variables; otherwise C5 stays blind in P2-E2.

### F3 [major] plant2 tests use pytest tmp_path: derived data in /tmp, old run dirs auto-deleted

- where: plant2/tests/test_p2_e1.py:20,41,50
- evidence: /tmp/pytest-of-root/pytest-0..2 contain seed npz and jsonl files. pytest keeps only the last 3 basetemp dirs and deletes older ones. This conflicts with AGENTS.md invariant 1 (no code that deletes, TemporaryDirectory cleanup included) and invariant 5 (never /tmp). tests/test_safety_lint.py passes, so the lint misses it.
- recommendation: Replace tmp_path with a conftest fixture that makes a fresh dir under ~/.cache/brain-sim/plant2/test-runs/<timestamp> and never cleans it up. Add a tmp_path or tmpdir pattern to the safety lint.

### F4 [minor] 'Fire but too late' diagnosis is incomplete; the operating-point claim had no J evidence

- where: Result: 'Why C1 fails' and 'Every cell's excitability is set by how much the network has stored, not by the cue'
- evidence: At J=1.12, widening the window trades C1 for specificity (75 ms: C1 0.99, C2 0.72; 100 ms: C1 1.0, C2 0.50). In written cells, the coin-set cue-synapse count explains R2 0.16 of misses; plateau count k explains 0.017. My J sweep (1.0-1.6) supports the claim: no J passes C1 and C2 together at M=1000 (1.16 gives 0.915/0.84). J=1.6 passes at M=250.
- recommendation: Reword: the half-cue drive spread (coefficient of variation 14%, from the p=0.5 flip and the 50% mask) and load-dependent background together leave no separable window at M=1000. Keep the operating-point direction, and cite the J sweep as reviewer evidence, not as a run.

### F5 [minor] Numbers in 'Why C1 fails' are wrong or mislabelled

- where: Result, 'Why C1 fails'
- evidence: Cell-level miss is 10.2-11.9% (about 1 in 9), not 1 in 13; 1 in 13 is the median item recall. Failing items have 3-14 late cells (mode 5-6), not 'one or two'. 34-45% of failures have recall 0.19-0.69. k counts the cell's total plateaus, this item included, not plateaus 'for other items'. Observed C1 is 5-6 points below what independent cells predict (0.874-0.92), so failures are correlated within items.
- recommendation: Correct these figures in an addendum. Model item-level correlation, such as shared cue spike counts, in the next contract's predictions.

### F6 [minor] Overstated capability bullets

- where: Result, 'What this run does show'
- evidence: 'No response to unlearned cues': max ignition is 15-21 cells per seed, about one assembly, and C3 is 0.945-0.98. 'Full cues recalled at 1.00 within 10 ms': 10 ms is the median first-spike latency, and recall 1.00 is measured at 50 ms. 'About 2 spurious per cue' is a median, while C2 sat at 0.905 and 0.900 on seed 5.
- recommendation: State them as measured: median ignition 2, max 15-21; full-cue median latency 10 ms with recall 1.00 at 50 ms; C2 margin as thin as 0.000-0.005.

### F7 [minor] The 50% mask is beyond what the source paper shows working; deviations from the paper not disclosed

- where: P2-E1 contract, Hypothesis and Predictions
- evidence: Wu & Maass say f_q 0.005 'supports recall up to a fraction of one-third masked 1's'. They define the trace by the full-cue response, use f_w 0.6, and grid-search thresholds or scale them with input activity. P2-E1 uses a 50% mask, full connectivity, the plateau set as target, and one fixed threshold. The bar is stricter, not lowered, but the paper itself signals the risk.
- recommendation: Note in the contract lineage that the half cue is an inherited K1.1 bar outside the paper's demonstrated regime, and list the deviations.

### F8 [nit] Plateau gate is not a teacher, but the protocol supplies episode boundaries

- where: p2_e1_btsp.py learn_one (net.quiet(), counts over exactly t_item)
- evidence: Plateaus come from their own stream, independent of content and activity, and inject no current. The test confirms that writes ignore memory spikes. Eligibility, however, is counted over exactly one item, with state reset between items, so segmentation comes from the protocol. The contract labels this ('quiet time not simulated').
- recommendation: Acceptable at Stage 1. Stage 2 must use a continuous stream with the 10 s window spanning neighbouring items.

### F9 [nit] Never-trained twin is trivially silent; reporting gaps

- where: run_seed twin; npz/JSONL contents
- evidence: The twin has an empty store, so 0 responses carry no information. The contract says so. Item age is reported only as old vs rest. The npz files do not save the cued indices. The predictions of 27.9 mV and 'k>=12 cells can cross' are not compared. The AUDIT says 'done before any plant2 code' but was committed with the results, and its legacy-suite log ended at 06:57.
- recommendation: For P2-E2, add a shuffled-store control (same strong count per cell, presynaptic identities permuted), save cued indices and per-cell features, and fix the AUDIT wording.

## Proposed next experiment

- mechanism: P2-E2: a slow per-cell adaptive threshold (labelled proxy for intrinsic excitability). theta_i = slow average (tau about 20 s) of the cell's own membrane during ongoing activity + delta. Only the threshold adapts; synapses are untouched. delta is fixed by the 1.4 rule applied to the correctly computed cue-specific drive: 24.66 x 40 Hz x 20 ms x 1.12 = 22.1 mV, so delta = 15.8 mV. J stays 1.12, f_q 0.005, BTSP unchanged, all bars unchanged. quiet() must not reset theta.
- why: Removes the load-dependent background offset the Result names, without touching written synapses (the old plant's failure cause 2). My stand-in, a threshold computed from the store (oracle, not learned), at J 1.12 and delta 15.8 on seed 1: M=250 C1/C2/C3 0.95/1.0/1.0; M=1000 0.96/0.97/0.98, against P2-E1's 0.84/0.925/0.955. At M=1000 no global J in 1.0-1.6 passes, so the gain comes from making the threshold per cell, not from margin.
- kill_test_sketch: Seeds 1-5 at M=250 and M=1000. PASS only if P2-E1's C1-C4 hold at both loads on every seed, and C5 holds when phase 2 starts from the post-60 s state with theta carried. Control A, a global threshold with the same 15.8 mV margin (equal to J of about 1.42), must fail C2 or C3 at M=1000; at J=1.4 it gave C2 0.025. Control B, a shuffled store, must fail C1. Report the store-derived stand-in as an upper bound. Validity: theta has converged (drift under 0.5 mV in the last 10 s) and the weights are bit-identical.
- predicted_outcome: From the stand-in: C1 0.93-0.97, C2 and C3 at least 0.95 at M=250 and 1000, so a narrow PASS on seed 1. Other seeds and real tracking noise could cut C1 by 2-4 points. Reported capacity: at M=2000 C1 holds at about 0.94 but C2/C3 fail (stand-in 0.145/0.15), and everything fails at 4000. Capacity would move from no working J at 0.25 items per cell to a working point between 0.25 and 0.5.
- risks: Test cues are on a third of the time, which raises hub thresholds and some written cells' too. Learning simulates only 200 s of episodes, so theta needs a settling period. The 15.8 mV margin can look like a rescue unless control A fails. Background noise grows with sqrt(k) and is not removed. Correlated item failures cost about 5 points of C1. A theta that reads cue activity could drift during the 60 s and fail C5, which is now a real test.
- alternatives_rejected: Re-running P2-E1 with a corrected J: forbidden as a rescue, and my sweep fails C2/C3 at J 1.16-1.25. Global or feedback inhibition (k-WTA): forces winners on novel cues (C3), adds latency, and leaves the per-cell offset. Synaptic normalization: acts on written synapses and scales the cue drive with load. A shorter mask or longer window: lowers the bar. Recurrent completion: a second plastic path too early. More cells: does not change the per-cell operating point.
