# P2-E4 results review: northstar skeptic lens

Independent reviewer given only the files (HEAD bbeb25b, after the verdict and the post-verdict diagnosis). Run 2026-10-11. Recorded verbatim, before synthesis.

## Verdict

P2-E4 is a valid, well-built measurement. It adds no capability and removes no supply at learning time; its value is exposing a supply nobody had named. All five gated seeds are valid. O1 C1 and O3 memory fail at both loads, and O4 fails estimably at M = 500. Online content (O2, O3 content, 75 ms window) passes on every seed and load. The index failure is mostly latency: the slowed cues' assembly fires 6-11 ms later, and my post-hoc recombination gives C1 of 0.955-0.97 at M = 1,000 within 75 ms (recall only). The real finding is that P2-E3's PASS relied on writing at a high offset (about 8.4 mV) and reading after a settle (about 3.7 mV). That is an experimenter-supplied split between encoding and retrieval states. At M = 1,000, no single state passes both index and content on the same synapses. The trade-off is shown for the responder write, not for the architecture.

## Findings

### NS-1 [major] ONLINE INDEX FAIL is mostly a 50 ms latency failure, not lost access

- where: bench/results/plant2.jsonl: diagnosis records for gated seeds 16-20 (D1, D2) and kill_test_verdict; docs/plant2/STAGES.md, Stage 1 gate
- evidence: At M = 1,000, 22.5-29.5 % of half cues regenerate content (75 ms window) but fail index recall (50 ms). For these cues the median A(x) first spike is 6-8.5 ms later (6.5-11 ms at M = 500), and 0.89-0.93 of them reach recall >= 0.8 within 75 ms. Combining D1 with that 75 ms rescue gives C1 of about 0.955-0.97 at M = 1,000 and 0.97-0.995 at M = 500, on all five seeds. This covers recall only. Spurious and ignition at 75 ms were not measured, though spurious is <= 3 cells at 50 ms. About a third of index failures are one cell short. Content within 50 ms (joint_50ms) is only 0.73-0.855, so both readouts slow equally. The difference is in the windows, not the memories.
- recommendation: Keep the frozen FAIL. In the Result, report C1 at 75 ms beside it, labelled post hoc, and word the owner's point as 'slower access', not 'lost access'. Ask the owner to set one latency bar for both index and content in future contracts, before any data, justified by a downstream need (for example, a Stage 2 chaining period).

### NS-2 [major] The trade-off exposes an unnamed experimenter supply: separate write and read states

- where: reported_arms for seeds 16-20 (reference_responders, responders_main, responders_duty, offset_settled, twin_B); plant2/experiments/p2_e3_completion.py (learn_one, run_phase)
- evidence: At items 751-1,000, P2-E3's protocol writes at a continuation offset of 8.35-8.56 mV and reads after a 50 s settle at 3.65-3.74 mV. The main line writes and reads at about 6.9 mV, the duty arm at about 4.1 mV. Twin B tests the same synapses in both states at M = 1,000. Online, content passes (0.93-0.965) and index fails (0.68-0.74). Settled, index passes (0.92-0.975) and content fails on 4 of 5 seeds (0.835-0.915). At M = 500 the settled state passes both, and the duty arm passes everything online (C1 0.95-0.99, joint 0.99-1.0). The contract's limitations name the operating point, but not this split.
- recommendation: Add 'separate encoding and retrieval states, set by the schedule' to the experimenter-supplied list in the Result and in the STAGES row. Also state that on the gated schedule the usable online load lies between 0.125 and 0.25 items per cell, below P2-E3's 0.25.

### NS-3 [major] Trade-off shown for a write gated by one shared threshold, not for the architecture; retrieval does not harm writing

- where: reported_arms: responders_*, twin_A swap_plateau, novel_duty_twin; DECISIONS.md, the owner's reading of 2026-10-11
- evidence: On seeds 16-20, |R| at items 751-1,000 falls on one monotone curve of continuation offset: 27.6-29.2 at about 8.4 mV, 41.2-44.5 at about 6.9 mV, 120.8-135.8 at about 4.1 mV. On twin A's raster the plateau-set store reads 0.985-1.0, against 0.82-0.905 for the online store. P2-E5's exploration found that a store written from cells with >= 3 continuation spikes matches the plateau-set store. rec has no outputs, so the feedback store cannot move the memory operating point. The novel-duty twin never retrieves a stored item, yet it writes the same |R| (within 0.21) and reaches the same twin A joint (within 0.01). Input duty drives contamination; recall does not.
- recommendation: Word the owner's finding as conditional on a write that recruits every cell above one absolute threshold. The owner is right that a threshold or tau change only slides along this curve. The decisive test is a write whose eligibility does not share the read threshold (next steps 3-5).

### NS-4 [major] Falsified reported predictions about capability are not written up

- where: reported_arms wps and ood, seeds 16-20 and 42-43; docs/plant2/HANDOFF.md, exploration table
- evidence: Writes during probe slots: only 0.165-0.21 of about 170 written probes are recallable. The prediction was 'nearly all stored (by arithmetic)', but that arithmetic counted writes. A 100 ms slot makes a line eligible with P about 0.76, against 0.986 in a 200 ms encoding, so storage depends on the exposure length the experimenter sets. Out-of-distribution cues, at the online state:
- 30 % cues: C1 0.0 on all seven seeds (predicted 0.2-0.5);
- half cues with 10 of 50 lines swapped for noise: 0.075-0.175;
- lures sharing 50 lines: recalled as the stored item, 0.7-0.95.
The handoff lists only the write counts. No document analyses these.
- recommendation: Report them in the Result with each prediction marked failed. They are the closest P2-E4 comes to capability: learning outside the write oracle mostly fails, and at the online state only a narrow range of cues still completes.

### NS-5 [major] 'Online' means continuous state under a scheduled write oracle, not online learning

- where: docs/plant2/P2-E4-online-memory.md: Hypothesis, 'Labelled limitations' and Protocol
- evidence: The experimenter still supplies:
- when and how long to write (200 ms encodings, a 50 ms continuation);
- the key (random plateaus, which define A(x));
- the value (a 1:1 copy of the lines into rec);
- the input duty (50 %);
- the gaps that separate encoding from probes (50 ms and 100 ms);
- clean half cues, the readout windows and the item boundaries.
O4 and O5 run on copies with learning paused and sham encodings. P2-E4 removes only the settle and the frozen-copy test regime; the learning rule is untouched. It cuts test-time scaffolding, not the cognition supplied at learning time.
- recommendation: Word the Result as 'recall while scheduled learning continues'. Have every contract name the supply it removes, and record that P2-E4 removes none at learning time.

### NS-6 [minor] Habituation is accommodation working as designed; RECOVERY FAIL is marginal

- where: kill_test_seed habituation summaries and diagnosis D4, gated seeds 16-20
- evidence: At M = 500, 50-64 % of eligible items habituated on the three estimable seeds (14/28, 21/33, 14/27). With repetition, the assembly offset rises 3.0-3.4 mV on every seed, in habituated and non-habituated items alike. Recovery among habituated items is 0.75-1.0. RECOVERY FAIL rests on one seed and load (18 at M = 500), whose zero-effect pass probability of 0.83 is just above the 0.8 bar. At M = 1,000 the control copies' pooled 'both' rate is 0.61-0.65, so nothing there is estimable. One exploration correlate of slow retrieval, an assembly offset higher by 0.3-0.4 mV, does not replicate on the gated seeds (-0.22 to +0.70 mV).
- recommendation: Report habituation as built into per-cell accommodation, and RECOVERY FAIL as a one-seed, low-margin label. Item-level slowing and habituation both point to an unmeasured per-item drive margin. Any operating-point mechanism must predeclare its effect on O4.

### NS-7 [major] The line risks collecting diagnostics instead of capability

- where: review/plant2/P2-E4/ (12 files); docs/plant2/P2-E4-diagnosis-plan.md; docs/plant2/P2-E5-structured-items.md (P(PASS) below 1e-6); docs/plant2/STAGES.md, Stage 1 row
- evidence: Since P2-E3, two experiments carry no mechanism by design. P2-E4 was run after zero passes in 1,500 simulations. P2-E5 is frozen with P(PASS) below 1e-6, and most of its Part B readings were computed in advance. Each went through three or four review rounds, and the diagnosis plan through four correction rounds. Meanwhile the falsified capability arms (NS-4) went unanalysed. Stage 1 now needs one system to pass P2-E3, P2-E4 and P2-E5, plus capacity and graceful forgetting. Past capacity the store blacks out: joint 0.0-0.01 at M = 3,000 on every seed. The memory layer is a feed-forward spiking Willshaw store with random keys.
- recommendation: Run P2-E5 as frozen, with no new arms or diagnosis rounds. Make the next contract a mechanism with a predeclared capability gain and a named supply that it removes. Limit post-run diagnosis to what decides the next contract.

## Next steps

- Write P2-E4's Result as frozen: the FAIL stands, worded as 'zero passes in 1,500 simulations'. Beside it, report C1 at 75 ms (post hoc), the online content that passes on every seed and load, the write/read state split as an experimenter supply, and the falsified predictions for writes during probes and for out-of-distribution cues.
- Run P2-E5 exactly as frozen on seeds 21-25. The result most likely to change the picture is its unexplored online arm at M = 1,000. If online C2 on correlated items holds at >= 0.9 while settled C2 is 0.47-0.50, one threshold coupling also governs index specificity, and separating the two states becomes the central problem. If online C2 collapses too, the forward-index cross-talk is representational: it comes from the random key, no write or threshold mechanism can fix it, and allocation must come before Stage 2.
- Before the next contract, run an exploratory, read-only re-simulation of P2-E4's duty arm on seeds 42-43, in the manner of analysis/p2e4_diagnosis.py. Measure the AUC of the continuation spike count and the twin A joint of the store written from cells with >= 3 spikes, at M = 1,000. It costs about an hour per seed and adopts no mechanism. It decides whether the contract below is worth writing.
- The hardest open question is whether the network can write cleanly without the experimenter separating its write and read states. The most efficient test, subject to the owner's ruling, is a contract for one mechanism: a burst-gated feedback write that writes only from cells with >= 3 continuation spikes (k fixed by the eligibility rule's argument). Gate it on the P2-E3, P2-E4 and P2-E5 protocols on fresh seeds, and add a reported I = 2,000 ms arm. Predeclare that O1 at I = 250 ms still fails, because the read offset is unchanged.
- The decisive readings of that test are the duty arm's twin A joint at M = 1,000 (now 0.175-0.245) and its online joint (now 0.485-0.565). If both reach >= 0.95 with C1 >= 0.94, the trade-off belongs to the write rule, and an operating-point mechanism can follow without trading one failure for another. If they stay low, cross-talk cells burst too: the trade-off is architectural, and the next mechanism must be an encode/retrieve state that the network generates itself.
- Ask the owner to set one latency bar for both index and content, prospectively and tied to a downstream need. Also record that, in this model, the plateau-eligibility hypothesis is identical to the A(x) x E(x) store. It removes no supply until something other than the experimenter generates the plateaus.

## For the owner

P2-E4 ran correctly and failed as predicted, but the failure is narrower than its label suggests. Online, stored content still comes back within 75 ms on every seed. What fails is reaching the memory code within 50 ms (about 7 ms too slow), plus recall of repeated cues. The important finding is that P2-E3's pass relied on something the experimenter supplied without naming it: writing in a high-threshold state, then reading after a 50 s rest in a low-threshold state. With one state, at M = 1,000 you get fast access or clean content, never both. That is shown for the current write rule, not for the architecture. The hardest open question is whether the network can write cleanly without the experimenter separating those states. The most efficient test, after P2-E5, is a write gated by each cell's own spike burst, run on both the fast and the slow schedule.
