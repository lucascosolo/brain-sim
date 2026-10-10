# P2-E1 review: code lens

Fresh reviewer given only the files (review packet in the workflow prompt; no implementer history). Model: sonnet. Run 2026-10-10. Recorded verbatim, before synthesis.

## Verdict

Trustworthy. No bug found that moves a reported number. An independent dense LIF replay of the real seed-1 store matched the engine on 1,800 ticks (0 mismatches); a brute-force dense model matched the sparse BTSP store over 3,600 updates; every criterion recomputes from the npz/JSONL; learning and C1 0.840 reproduce bit-exact; the contract preceded code and code is unchanged since 749caee; a J sweep shows no J passes C1 and C2/C3 together at M=1000. Two interpretation corrections: the J rule double-counts cue synapses, and C5 and the twin are vacuous.

## Findings

### F1 [major] J rule double-counts cross-talk synapses; the 1.4x target was really 1.24x

- where: P2-E1-btsp.md, 'J by a rule' (24.66 + 3.10 = 27.76 cue synapses); Result 'Why C1 fails'
- evidence: BTSP toggling resets a written cell's own active-input synapses to P(strong)=0.5, so other plateaus add nothing there. Measured on the real seed-1 store: written cells have 24.69 cue synapses (sd 3.55), flat in k (24.5-24.8 for k 1-11), not 27.76. Mean drive is about 24.9 mV, not 28. 19% of written cells have <22 cue synapses (contract implied ~3%).
- recommendation: Add an addendum below the Result (not above) stating the rule's error. Correct rule gives J about 1.26. The verdict stands, because J=1.12 was fixed explicitly. State that 'no operating point' is shown by the sweep (F5), not by the J rule.

### F2 [nit] Checks run: engine, store, metrics and provenance are correct

- where: plant2/engine.py, btsp.py, p2_e1_btsp.py; bench/results/plant2.jsonl
- evidence: Ran: dense float64 LIF replay with identical input spikes, 6 cues x 300 ticks, 0 spike mismatches (delay 1, refractory, reset). 300 random stores x 12 BTSP updates vs dense toggles, 0 mismatches. C1-C5 and mean|A| recomputed from npz: exact. Capacity M=1000 equals seed 1 (criteria and learning dicts equal). Digest 1f2dcf7f19bf7073 matches. Inequalities match the contract. SeedSequence streams have no collisions.
- recommendation: None. Keep the independent-replay check as a unit test for future engines.

### F3 [minor] C5 is vacuous: the 60 s of activity cannot affect anything measured

- where: p2_e1_btsp.py run_seed -> background(60000) then evaluate(...) -> present() -> net.quiet()
- evidence: present() calls quiet(), zeroing every state, before each test. With no plateau the weights cannot move, so the 60,000-tick loop (about half the wall time) changes nothing. C5 FAIL is C1 re-measured with a new input-noise draw: 0.825-0.880 vs 0.810-0.860, so draw-to-draw noise is about 0.02.
- recommendation: Do not count C5 as separate evidence. Test persistence only when the mechanism has state that can drift, such as adaptation or inhibitory plasticity.

### F4 [minor] Never-trained twin is uninformative; real nulls were never run

- where: p2_e1_btsp.py run_seed (twin) and contract C3 note
- evidence: The twin has all-zero weights, so no input reaches any cell and 0 responders is guaranteed. I ran two nulls on the seed-1 store: 200 background-only windows gave 0 responders in total, and cueing with another item's half cue gave recall of A(x) of 0.006. Recall is therefore cue-specific and not inflated by spontaneous spikes.
- recommendation: Contracts should specify a wrong-cue (shuffled-assembly) null and a matched-density random-store twin, which have teeth. Report the 0.006 as a measured number.

### F5 [minor] 'No operating point' rests on one seed and one J; unregistered sweep supports it at the gate load

- where: P2-E1-btsp.md Result, capacity curve and 'What this run shows'
- evidence: Capacity points are nested prefixes of seed 1 at fixed J=1.12 (n=1 each). My engine sweep, seed 1, exploratory, not recorded: M=1000 J=1.16 C1 .915 C2 .840 C3 .895; J=1.20 C1 .945 C2 .690; J=1.12 C1 .840. M=500 passes everything at J 1.26-1.34, M=250 at J=1.34, M=1500 fails C2/C3 at every J. No J passes C1-C4 at M=1000.
- recommendation: Label the curve n=1. Cite the sweep as the evidence that the failure is not a J rescue away. Do not use it to retune P2-E1.

### F6 [minor] Per-item recall is overdispersed; per-cell arithmetic understates the margin needed

- where: Contract Predictions ('if per-cell recall falls to 0.85 ... 83%'); criteria C1
- evidence: Item recall sd is 0.105-0.127 vs 0.07 expected if cells were independent. C1 would be 0.87-0.92 under independence vs 0.81-0.86 observed. Cause: all cells of an assembly share the cue's spike train and mask. An item-level surrogate (shared cue spikes, independent synapses) reproduces engine C1 within 0.05 at J=1.12-1.34 for M=250 and 1000, and spurious 2/4/6/12.
- recommendation: Predict C1 from an item-level simulation, not per-cell probability. Use the surrogate in the next contract and say so.

### F7 [nit] Provenance and test hygiene gaps

- where: plant2/record.py; plant2/tests/test_p2_e1.py; run_seed validity
- evidence: Records omit numpy and python versions (reproduced here under numpy 2.5.3, store 930,107, so no harm). dirty ignores untracked files and the results file was untracked during the run. weights_unchanged is tautological because test phases never call a write. Tests use pytest tmp_path, whose old-dir purge may conflict with invariant 1. test_engine covers delay 3 with d_max 4 only.
- recommendation: Record library versions. Add a slot-reuse test with delay == d_max and two populations. Check tmp_path against test_safety_lint.

### F8 [nit] Assembly A(x) is an imposed random code; the metric is hash-code recoverability

- where: Contract 'Plateaus' (labelled proxy)
- evidence: Written cells are drawn independent of content and activity, so recall measures whether an assigned random code can be read back from a half cue. That is a legitimate storage test and is labelled, but it says nothing about the system choosing its own representation, which is the abstraction stage's question.
- recommendation: Keep the label when reporting. Do not read Stage 1 passes as evidence of thinking power; Stage 3 is where self-chosen codes matter.

## Proposed next experiment

- mechanism: P2-E2: keep the P2-E1 BTSP write, LIF readout, bars, validity and 5 fresh seeds. Change only how plateau cells are chosen: for each of Poisson(20) plateau slots per episode, draw 2 candidate cells and give the plateau to the one with fewer stored strong synapses (readable from the store; ties random). J is predeclared from the corrected rule: 1.26 mV. One mechanism, one new parameter (d=2), labelled as a load-limited plateau-propensity proxy.
- why: The sweep shows the J that fixes completion (>=1.16) lights hub cells at M=1000. Hubs come from the Poisson tail of plateaus per cell (k sd 2.2; 20 cells with k>=12). In the surrogate, best-of-2 gating cuts k sd to 0.95 and removes hubs, opening a J window of 1.2-1.4 at M=1000 and 1.3-1.4 at M=250. It targets the measured cause and needs no new dynamics in the engine.
- kill_test_sketch: Commit the contract first. J=1.26 fixed, same C1-C5 and validity bars, seeds 6-10 (seeds 1-5 reported). Added bars: hubs (cells answering >5% of cues) <= 2 per seed; plateaus-per-cell sd <= 1.2. Ablation: random gating at the same J on the same seeds must fail C2 or C3 (engine seed 1: C2 0.42), or the gain is not the mechanism. Report capacity M=250/500/1000/2000. FAIL on any bar: stop the line.
- predicted_outcome: At M=1000: C1 about 0.95-0.99, C2 and C3 >=0.98, median spurious about 1, hubs 0. M=250 at J=1.26 may miss C1 (about 0.85-0.90; reported only). M=2000 still fails C2/C3 (mean k 10, surrogate spurious >30), which motivates a background-balance mechanism next. Real C1 likely 0.02-0.03 below the surrogate.
- risks: Gating by the cell's own load is an instructive-signal selector and must be labelled a proxy, not emergent. The surrogate ignores toggle erasure and uses a fitted 0.92 density factor, so numbers carry about +-0.05. C3 may fail on residual k>=8 cells. Passing M=1000 alone does not show load-independence.
- alternatives_rejected: (1) Re-run P2-E1 with J 1.16-1.26: barred by the contract, and no joint window exists at M=1000. (2) Per-cell background balance: the surrogate also opens a window (J 1.4-1.5), but needs per-cell inhibitory state; the natural second step. (3) Recurrent completion of late cells: needs memory activity during episodes, i.e. a teacher burst. (4) Scaling m and n: size alone is not a gate.
