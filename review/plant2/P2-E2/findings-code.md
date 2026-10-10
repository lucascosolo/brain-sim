# P2-E2 review: code lens

Fresh reviewer given only the files (review packet in the workflow prompt; no implementer history). Model: sonnet. Run 2026-10-10. Recorded verbatim, before synthesis.

## Verdict

Trustworthy: no bug found that moves a reported number. Seed 6 at M=250/500/1000 reproduces the record exactly, and an independent dense LIF (float32 and float64, own settle, presentation, first-spike and C1-C3 code) matches every per-item recall, spurious and ignition value. Contract preceded code, calibration was committed before gated runs, plant2 code was unchanged during them. PASS stands. Open issues are documentation, provenance, weak controls and one unreported limit (habituation under sustained cues).

## Findings

### F1 [major] Accommodation habituates under a sustained cue; 'mild habituation' rests on 3 s

- where: P2-E2-accommodation.md Result (repeated-cue arm, 'What it does not show'); p2_e2 repeated_cue
- evidence: Repeated-cue arm covers 10 reps = 3 s = 0.3 tau_acc. My run (seed 6, M=1000, 10 items, exploratory, unrecorded): same half cue 100x (30 s). Items with recall >=0.8: reps 2-10 0.99, 31-60 0.79, 61-100 0.67; cued assembly's vbar +5.2 mV (baseline offset ~6 mV). Same class as the plant's K0.13 repetition habituation. No effect on gated numbers.
- recommendation: Add a 100-repeat arm on gated seeds as a reported measure in the next contract and list sustained or repeated stimulation under 'does not show'. It bears on Stage 6 (hold over 10 s) and any recurrent mechanism.

### F2 [minor] Result cites the wrong contract digest; verdict record lacks one

- where: P2-E2-accommodation.md Result para 1; kill_test_verdict row
- evidence: Doc names digest 1f2dcf7f19bf7073, which is P2-E1's (digest(e1.CONTRACT)). P2-E2 records carry 4f625b7cf4dcfbf1 (gated, J=None) and ca482d31aa3f585d (calibration, J=1.12). The kill_test_verdict row has no contract_digest or runtime.
- recommendation: Add an addendum below the Result naming the right digests (nothing above is edited). Add contract_digest and runtime to verdict rows.

### F3 [minor] Provenance: dirty flag conflates results appends with code edits; commit stamped at run end

- where: plant2/record.py git_state; run_seed rec['git']
- evidence: dirty=True on 3 of 10 seed rows, the verdict and 33 of 34 calibration rows, only because bench/results/plant2.jsonl was uncommitted. I verified code identity by other means: plant2/*.py mtimes <= 08:12:11, first gated start ~08:12:45, git diff 19776f9 545d507 -- plant2 empty, calibration code 6076a22 differs from gated code only by record.py O_APPEND.
- recommendation: Stamp at run START: git rev-parse HEAD:plant2 (tree hash) and git status --porcelain -- plant2, so results-only commits cannot blur it.

### F4 [minor] Convergence statistic is mostly a noise floor at high load

- where: p2_e2 settle(); validity 'converged' bar 0.2 mV
- evidence: mean|dvbar| over 10 s includes stationary fluctuation that grows with sqrt(strong count). Seed 6, M=1000, settled run: 0.065 mV per window with signed drift ~0 (my prediction 0.064); the recorded 0.083 = 0.065 noise plus -0.063 signed drift. Seed 5's 0.207 at M=2000 (reported load) is likely noise-dominated. Gated loads 0.03-0.10, so no effect on the verdict.
- recommendation: Judge convergence by |mean signed change| against a noise estimate from a second window.

### F5 [minor] Void controls are weaker than worded; paired comparison changes more than the readout

- where: P2-E2 'Void conditions', 'Paired comparison'; randomise_store; run_seed fixed arm
- evidence: V-B random store gives recall 0.0 by construction: it removes all cue-line to assembly synapses (its presynaptic out-degree sd is 14.7 vs 46 real). V-A uses J*=1.525, so it shows J* is too high for a fixed threshold, not that no fixed J works; that claim rests on unrecorded reviewer sweeps. Paired seeds 1-5 differ from P2-E1 in J (1.12 vs 1.525) and in no-quiet state as well as readout.
- recommendation: Record a fixed-threshold J sweep (seed 0, M=250/500/1000) and a control that keeps cue-line synapses but shuffles cross-talk. Reword 'only the readout differs'.

### F6 [nit] Result text slips and reported items not produced

- where: P2-E2 Result tables and 'Reported, not gated'
- evidence: C2 at M=1500 is given as 0.73-0.78 'mean over gated seeds'; records give mean 0.748, range 0.715-0.775. Median 25 ms recall '0.57-0.61 (gated and paired)' misses paired seed 1 (0.55). Contract lists a random-store arm at every load and a separate 100-pair wrong-cue null; code runs the random arm only at M=1000 and one 200-pair shuffled null.
- recommendation: Correct in the addendum; state which reported items were dropped.

### F7 [nit] Tests do not pin the properties the claim rests on

- where: plant2/tests/test_p2_e2.py
- evidence: No test that test phases never call quiet(), that main/fixed/random arms see identical input spikes, or that repeated_cue and the convergence value are computed as described; the small-run test only checks record keys. store_equals_p2e1 is in-process and inherits E1.learn, so it guards regressions only. Scratch checks passed: input-spike hashes identical across arms, zero quiet() calls, seed 1 re-learned with E1 code gives size 930107 (equals P2-E1's record) and the digest in P2-E2's record.
- recommendation: Add two tests: hash of Poisson draws equal across arms; LIF.quiet patched to raise during settle and evaluate.

### F8 [nit] Checks run with no defect found

- where: plant2/engine.py, p2_e2_accommodation.py, p2_e1_btsp.py, plant2.jsonl
- evidence: Spike-test order, float64 vbar, quiet() keeping vbar, set_accommodation: correct, and the non-accommodating path is unchanged since 749caee. Criteria, calibration verdict (J* 1.525) and all gated/void/validity flags recompute from rows. randomise_store keeps counts, unique sorted keys, deterministic. repeated_cue indexing correct. 16 plant2 tests pass.
- recommendation: None. Keep the dense-replay script as a regression check.

## Proposed next experiment

- mechanism: P2-E3 content completion: a reverse binary store from memory cells to a readout population of m lines, written by the same BTSP Eq. 1 (plateau cell x eligible input, p 0.5, transposed). Readout cells have a plain fixed threshold; their only drive is recalled memory spikes. Forward path, J*=1.525, accommodation and bars stay. J_rev is calibrated on seed 0 before any gated run.
- why: Stage 1 stores a random tag, but nothing shows the missing half of the input can be read back. The plant never scored regenerated input (K1.1 counted assembly cells; 8.23 oracle weights capped recall). At M=250 a fixed threshold already works at J*, so that load does not depend on the pending intrinsic-homeostasis ruling.
- kill_test_sketch: Predeclare: at M=250 and 1000, for >=90% of 200 cued items, >=80% of the 50 MISSING item lines fire within 75 ms of cue onset and non-item readout spikes < 10; visible half scored separately. Seeds 11-15, all must pass. Must fail: permuted reverse store (<=10% recovered) and forward-only net (0). Report the 100-repeat cue arm. FAIL on any bar: stop this line.
- predicted_outcome: Missing-line recall median 0.90-0.95 at M=250 and 0.85-0.92 at M=1000; non-item readout spikes 0-3. Basis, an unrun estimate: each missing line gets ~9-10 strong inputs from ~19 recalled cells against ~1.2 cross-talk. About 55% chance of PASS; the likeliest failure is item-level completion at M=1000.
- risks: The reverse store is a hand-built symmetry of the forward rule (labelled proxy) and doubles stored synapses. Readout may need its own operating point near M=1500. M=1000 depends on the pending homeostasis ruling. A pass shows no self-chosen codes and no thinking power.
- alternatives_rejected: Capacity vs cell count: needs a signal-to-noise mechanism first, and size alone is not a gate. Fixing habituation (clipped vbar): mechanism work; record the limit on 5 seeds first. Load-balanced plateaus: instructive selector. Recurrent completion: runaway without a stabiliser. Fixed-J sweep: a control, fold into E3's contract.

## For the owner

PASS reproduces exactly and I found no bug that moves a number. Rule on the intrinsic-homeostasis gate: the offset tracks each cell's stored synapse count at r=0.998, a per-cell load normaliser by another route. Know the limit: a half cue repeated for 30 s drops items with recall >=0.8 from 0.99 to 0.67 (my exploratory run, 1 seed). Correct the Result's contract digest by addendum and soften the control wording. Approve or redirect P2-E3.
