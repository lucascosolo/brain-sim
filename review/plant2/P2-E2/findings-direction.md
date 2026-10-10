# P2-E2 review: direction lens

Fresh reviewer given only the files (review packet in the workflow prompt; no implementer history). Model: session default. Run 2026-10-10. Recorded verbatim, before synthesis.

## Verdict

P2-E2's PASS is procedurally sound: contract 9f647b2 before code 6076a22, calibration committed before any gated seed, plant2 unchanged during the runs, stores equal to P2-E1's, and both void arms fail as required. Two readings need an addendum: accommodation is needed only at M=1,000 (a fixed threshold at J* passes 250 and 500), and the reported offsets include the test's own cue duty. Next step: content completion with Wu & Maass's two-step Hebbian feedback. Exploratory runs show its readout also needs activity-proportional inhibition at M=1,000. The owner's gate ruling comes first.

## Findings

### F1 [major] The PASS and every next step wait on the owner's gate ruling

- where: DECISIONS.md 2026-10-10 (second entry); P2-E2 Result 'Decision'; STAGES log
- evidence: The Result and STAGES say 'pending the owner's ruling' on 'rejected intrinsic homeostasis as previously run'. In the records the offset correlates 0.994-0.998 with each cell's strong-synapse count at every load. In effect it is a per-cell threshold proportional to stored load, reached through the mean potential. Any P2-E3 that reuses J*=1.525 and accommodation inherits this dependency.
- recommendation: Get the owner's ruling before committing a P2-E3 contract. If the mechanism is withdrawn, P2-E3 must not reuse J* or accommodation, and STAGES must show Stage 1 storage as open again.

### F2 [major] Content completion with a fixed readout threshold has no window at M=1,000 (exploratory)

- where: Next Stage 1 experiment (content-completion clause); ~/.cache/brain-sim/review/p2e2-direction/completion2.py
- evidence: Exploratory, seeds 42-43: two-step clipped Hebbian feedback from mem to 4,000 recon cells. Joint score = completion >=0.8 and intrusions <25. M=500: 0.93-0.99 at J_fb 1.8-2.4. M=1,000: best 0.87 (J_fb 1.8), and 0.64-0.70 at 2.4. Adding inhibition of 0.3 J_fb per mem spike gives 0.96-0.99 at J_fb 3-4. At M=1,500 the best is <=0.67 either way.
- recommendation: Make activity-proportional feedforward inhibition on the readout a declared, fixed element, with a no-inhibition void arm. Otherwise expect a FAIL at M=1,000. Flag it to the owner as a second element.

### F3 [minor] Accommodation is needed only at M=1,000; P2-E1's slowness at low load came from J

- where: P2-E2 Result 'What this shows'; ~/.cache/brain-sim/plant2/p2_e2/run.log (fixed arm)
- evidence: At J*=1.525 the fixed-threshold arm passes C1-C3 on all 5 gated seeds at M=250 (all 1.0) and at M=500 (C2 0.905-0.955, C3 0.92-0.965). It fails only at M=1,000 (C2 <=0.015). P2-E1's C1 of 0.61 at M=250 came from J=1.12. The claim 'one J across 4x, which no fixed threshold achieved' rests on reviewer sweeps that were never recorded as results.
- recommendation: Add to the addendum: accommodation extends the fixed-J window from <=0.125 to 0.25 items per cell, and the 'no fixed J' claim cites the exploratory sweeps.

### F4 [minor] The reported threshold offsets include the test's own cue duty

- where: plant2/experiments/p2_e2_accommodation.py run_seed (offsets read after the full-cue block); Result offset row
- evidence: Background alone predicts 1.525 x 233 x 0.5 Hz x 20 ms = 3.55 mV at M=1,000. The reported value is 6.0 mV, 1.7x at every load (1.59 vs 0.93 mV at M=250), which matches the extra 0.33 Hz per line from the full-cue duty. Half cues add about 0.165 Hz, so thresholds rise about a third within about 20 s of the half-cue block. Items 1-100 are cued first, so the C4 items see lower thresholds.
- recommendation: Report each cue's mean threshold at onset and state that the operating point depends on the protocol. In a continuous stream (Stage 2), predict habituation to frequent inputs.

### F5 [minor] The capacity clause is under-defined, and the scaling is mostly combinatorial

- where: docs/plant2/STAGES.md Stage 1 gate and P2-E1 review note; ~/.cache/brain-sim/review/p2e2-direction/scaling.py
- evidence: Exploratory surrogate: exact BTSP store plus an LIF fire table with accommodation. At n=4,000 it matches the edge (C2 0.77 at M=1,500 against 0.73-0.78 measured) but is too harsh at 2,000. n=8,000 with m and f_q fixed: the edge stays at about 1,500 items, so items per cell halve. n=8,000 with f_q 0.0025 (|A| 20): edge about 2,500 (1.7x). m=n=8,000 with a=100: C2 0.98 at 3,000 and 0.07 at 4,000 (about 2.2x).
- recommendation: Before any capacity contract, the owner decides what scales (inputs and memory cells, f_q or |A|). Predict the curve with this surrogate. Credit growth to sparser codes over more inputs, not to accommodation.

### F6 [minor] Stage 2 with BTSP's real window on 200 ms items would saturate the store

- where: STAGES.md Stage 2; review/ledger.jsonl P2-E1 methodology F8 (continuous stream, deferred)
- evidence: Wu & Maass Fig. 1: LTP for inputs from -3 to +2 s around plateau onset. With 200 ms items and f_p 2.5 %, a 5 s window makes 1-0.975^25 = 47 % of lines eligible per plateau. That gives about 940 strong synapses per plateau, against about 50 now. The code becomes a temporal context (assemblies about 25x larger). In-order replay also needs a loop and a stabiliser, which the network does not have.
- recommendation: Start Stage 2 only after a content path exists. Use seconds-long items or a window scaled to item length, labelled, and treat the content path as the hetero-associative link.

### F7 [nit] The Result cites P2-E1's contract digest

- where: docs/plant2/P2-E2-accommodation.md Result, first paragraph; bench/results/plant2.jsonl
- evidence: The Result says 'contract digest 1f2dcf7f19bf7073', which is P2-E1's. The P2-E2 kill_test_seed records carry 4f625b7cf4dcfbf1. The calibration records carry ca482d31aa3f585d, a digest of a config that still holds J 1.12. The kill_test_verdict record has no digest.
- recommendation: Correct this in an addendum. Digest the same config (J excluded) in calibration and gated runs, and write the digest into the verdict record.

### F8 [nit] Ordering and code-freeze checks hold

- where: git 9f647b2..95fb77a; bench/results/plant2.jsonl
- evidence: Contract 9f647b2 (07:59) came before code 6076a22 (08:02). All 33 calibration points ran on 6076a22 and were committed in 52e5475 (08:11:59), before the first gated record (08:13:45). git diff 19776f9 545d507 -- plant2 is empty, and 6076a22..19776f9 changes only record.append. The 3-minute gap before a 433-line code commit means drafting overlapped; git proves commit order only.
- recommendation: No action. Describe what is verified as commit order, not authoring order.

## Proposed next experiment

- mechanism: P2-E3, content completion. A one-shot clipped Hebbian feedback path from mem to recon: 4,000 LIF cells, one per input line, fixed threshold. Wu & Maass's two steps: after the BTSP write the item stays on for 50 ms, on its own stream so stores stay bit-identical. Each mem cell that spikes in that time through its new synapses gets w=1 onto every recon cell whose line was eligible. No current goes into mem or recon. Declared fixed readout element: inhibition of g x J_fb on every recon cell per mem spike (Willshaw threshold, labelled FFI proxy).
- why: It is the open Stage 1 clause and the base for later stages. Output in the input's code allows hetero-association (Stage 2 is the same rule with a lag), regenerating prototypes (Stage 3) and replay (Stage 5). No teacher burst is needed: the post-write responders contained A(x) for every item, with 0-1 extra cells at M<=1,000. The binary feedback matrix and each regenerated pattern can be inspected directly against the original.
- kill_test_sketch: Contract first; J* and accommodation unchanged. Calibrate J_fb on held-out seed 0 at M=250/500/1,000 (midpoint of the passing run). g is predeclared at 0.3. Fresh seeds 11-15, not 0-10 or 42-43. PASS only if at every load: D1 completion of the masked half >=0.8 within 50 ms for >=90 % of items; D2 intrusions <25 for >=90 %; D3 a novel cue lights <25 recon cells for >=90 %; D4 D1-D2 hold on the oldest 100; C1-C3 still hold. Void: the g=0 arm must fail D2 at M=1,000; shuffled feedback must fail D1.
- predicted_outcome: Exploratory (seeds 42-43, g 0.3, J_fb 3-4). Joint D1 and D2: 0.96-1.0 at M=500 and 0.96-0.99 at M=1,000. Novel cues light 0 cells. The g=0 arm peaks at 0.87 at M=1,000. Shuffled feedback gives D1 <=0.015 (seed 42, without inhibition). M=1,500 fails D2 (<=0.67), the same edge as memory specificity. Completion is low at 25 ms (mem median latency is 22 ms). Chance of PASS about 60 %.
- risks: Two new elements make a FAIL harder to attribute, and the owner may not count static inhibition as part of 'one mechanism'. My inhibition arrives in the same tick as excitation; a realistic 1-2 ms lag narrows the window. Feedback learned from activity picks up spurious responders, so it gives more intrusions than plateau-set feedback. The 50 ms continuation must be labelled as a protocol addition. Capacity stays near 0.3 items per cell. Exploration used 2 seeds, a surrogate readout and no sensory relay.
- alternatives_rejected: (2) Capacity scaling now: the surrogate predicts it from counting (about 2.2x when m and n double), so a run mostly confirms that and needs the owner to define what scales. Run it next, as a predicted curve. (3) Stage 2 now: the -3 to +2 s window saturates the store on 200 ms items, and replay needs a loop. Plateau-gated feedback is bookkeeping, not experience. A fixed-threshold readout alone has no window at M=1,000. Recurrent completion inside mem runs away (P2-E1 review F6).

## For the owner

Yes, now is a point for the owner to look. (1) Rule on whether P2-E2's accommodation falls under the closed gate 'rejected intrinsic homeostasis as previously run': the PASS and all next steps depend on it, and in effect the offset tracks each cell's stored load (r 0.998). (2) Decide what 'capacity grows with cell count' scales: the exploratory counts flip with that choice. (3) Say whether content completion may add a fixed, activity-proportional inhibition on its readout: without it no exploratory setting passed at M=1,000. The provenance holds; a digest and two readings need an addendum.
