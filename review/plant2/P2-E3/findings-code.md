# P2-E3 review: code lens

Fresh reviewer given only the files (review packet in the workflow prompt; no implementer history). Model: sonnet. Run 2026-10-10. Recorded verbatim, before synthesis.

## Verdict

No bug found that changes any reported P2-E3 number. I re-ran the readout against the real engine, rescored 200 cues by brute force from raw rec spikes, and re-ran seed 14 (M 250/500/1000) from scratch: every arm, digest and structural arm matched the records. Remaining issues are latent (a span counter that silently returns zeros if cues are spaced under 300 ms), thin tests around scoring, and a few over-worded claims. The gated PASS is sound as code; its meaning is bounded by the contract's own 'does not show' list.

## Findings

### F1 [minor] replay span counter silently yields zeros when cue spacing is below SPAN or the raster ends early

- where: plant2/readout.py:45,101-108 (single span_cue slot)
- evidence: Tiny config with t_gap=100 (spacing 200 < 300): total_span/item_span were 0 for 37 of 100 cues, where brute force on the live engine gave 75-80. No error raised. The real config is safe only because t_cue+t_gap equals SPAN (300) exactly, so reported intrusions_span_median is right.
- recommendation: Give each cue its own span accumulator or raise when spacing < span or the last span is cut off. Add a test. Needed before P2-E4 reuses replay with other layouts.

### F2 [minor] Scoring path (onsets, windows, latency, build_cues alignment, score, choose, verdict) has no unit test

- where: plant2/tests/test_p2_e3.py:35-58 (replay test passes cues=[])
- evidence: Spike-for-spike replay test never exercises windows. My check: live mem+rec in one engine Net (m=n=2000 and m=2400/n=1600, 200 cues, J 2.8/g 0.3 and J 1.55/g 0). 0 mismatches in 10 per-cue counters; joint, D1-D4, HD, chance, latency match score(). Presented cue arrays equal build_cues; block order half/novel/full right; earliest spike k>=2.
- recommendation: Commit that live-engine vs replay vs brute-force check as a test (about 17 s), plus a build_cues alignment test.

### F3 [nit] Committed slow test exercises E2, not the E3 pipeline

- where: plant2/tests/test_p2_e3.py:125-133
- evidence: It builds e2.E2 and e2.evaluate, so run_phase, settle_drift and E3.present are untested against a recorded point. I ran E3 with t_cont=0 and 50 on seed 6, M=250 through run_phase: criteria and drift equal P2-E2's recorded values (True/True). The implementer's equivalent check is only a diag script.
- recommendation: Replace or extend the slow test with E3 at t_cont=0 via run_phase.

### F4 [minor] Label-permuted store is not degree-preserving as the contract says; 'pi(x) missing lines' is pi(x)'s lines minus x's cue

- where: plant2/experiments/p2_e3_completion.py:146-151, 154-179; contract 'Matched ... nulls'
- evidence: Contract: 'every per-cell and per-line degree is kept'. Measured (m=2400, n=1600, M=120): per-cell degree equal for 36% of cells (corr 0.9996), per-line equal for 3.6% of lines (corr 0.947). The 0.968-0.982 figure is a fraction of about 99 lines, not of a 50-line missing half. pi can have fixed points; none among cued items here. Reported arm only.
- recommendation: Reword in an append-only addendum; optionally exclude fixed points next time.

### F5 [nit] 'Chance' statistic is the overlap floor, not an independent null

- where: build_cues other_missing; score chance_other_missing
- evidence: Another item's missing half overlaps x's own 100 lines by 100/4000 = 2.5% by construction; reported chance 0.022-0.027 is exactly that. It adds no evidence beyond x's own regeneration. The label-permuted arm is the real specificity control.
- recommendation: Describe it as an overlap floor.

### F6 [nit] Config/constant coupling of the kind that caused the 'window' bug remains

- where: p2_e3_completion.py:27,37,204-222,234; readout.py signature
- evidence: cfg['rec_window'] is never read; readout uses module WINDOW. score() hard-codes a=100 (100-item, /50, /100). DIGEST omits SHORT, SPAN, J_GRID, JOINT_*, NOVEL_LINES, FRAC. No live collision found: keys window/J/M/g/t_cont/rec_window are read only where intended; m != n indexing verified.
- recommendation: Read window and a from cfg; fold all scoring constants into the digest (new digest for P2-E4, not retroactive).

### F7 [nit] stores_unchanged_by_tests cannot fail

- where: p2_e3_completion.py:345-347
- evidence: It compares the test copy with itself before and after a phase that touches neither store. Protection of the untested main line rests only on test_testing_a_copy_leaves_learning_untouched (which does pass). Forward store identity vs unmodified E1 is real but cannot depend on memory activity.
- recommendation: Also digest main's stores and vbar before and after each phase.

### F8 [nit] Provenance: calibration and gated runs used different plant2 trees; predictions committed 7 s before gating

- where: bench/results/plant2.jsonl rows 63 vs 64-68; git c97f237 16:52:56
- evidence: Calibration tree 0207e6cc, gated a949ecb0. git diff 68beb4c..c97f237 -- plant2 is only the 17-line verdict subcommand. Gated wall_s puts starts near 16:53:03, after the commit. Records append-only (checked per commit). Verdict read the 5 right gated rows (J 2.8, J0 1.45, digest e829...).
- recommendation: State the tree change in an addendum; add a guard that refuses gated runs unless the predictions commit is an ancestor.

### F9 [minor] P2-E4 draft relies on code that does not exist or is unsafe to reuse

- where: P2-E4-online-memory.draft.md; E3.learn_one, E3.present/_step, replay, score
- evidence: learn_one calls net.quiet() (draft: none). present/_step need _raster/_t0 set only by run_phase. replay assumes rec at rest at tick 0 and 300-tick spacing (F1). score/build_cues are fixed to half/novel/full blocks, old = first n_old. Probes move vbar, so the feedback store becomes timeline-dependent and P2-E3's fb-identity check cannot carry over; only the forward digest can. Seeds 16-20 are unused so far.
- recommendation: Subclass instead of editing E3.learn_one; write a probe builder and scorer; fix F1 first; define fb validity afresh.

## Next steps

- Fix or guard the span accumulator in readout.replay and add the live-engine vs brute-force scoring test before P2-E4 code is written.
- Append an addendum to the P2-E3 contract (nothing above it edited): tree change, degree-preservation and 'chance' wording, test gaps found here.
- For P2-E4, build on a subclass, take window and a from cfg, put every scoring constant in the digest, and red-team the draft's open points (inter-item interval, live vs copied probes, O4 bar).
- Keep gated seeds 16-20 untouched until the P2-E4 contract is committed.

## For the owner

The P2-E3 PASS is sound as code: I rebuilt the readout against the real engine, rescored cues by brute force, and re-ran one seed from scratch; all matched the recorded numbers. What I found is latent: a counter that fails silently if cues are packed closer than 300 ms (it matters for the online-memory experiment), thin tests around scoring, and two over-worded claims. None changes the verdict. The result still means what its own 'does not show' list says: verbatim hetero-association onto assigned codes, not abstraction.
