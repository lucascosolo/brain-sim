# P2-E5 results review: northstar skeptic lens

Independent reviewer given only the files (HEAD f25d3ed, after the verdict). Run 2026-10-11. Recorded verbatim, before synthesis.

## Verdict

The FAIL is real and correctly computed from the records: all 5 gated seeds are valid, S1 fails at both loads, and S2 and S4 fail at both loads. Several readings go further than the data. (1) CONTAMINATION-DOMINANT at M=1000 depends on the grid-best convention. At the frozen readout the same rule reads INDEX-DOMINANT on 5 of 5 seeds. (2) Part C shows that the experimenter's key can be read back from activity, not a mechanism. (3) The online C2 gain is an unpaired excitability shift, not a more specific index. (4) The plateau-set failure at M=1000 is partly caused by F=10's line load. The firm conclusion is narrower and stronger: S1 fails whatever the feedback write is, so no content-write fix can pass this clause under the settled protocol. P2-E5 removes no experimenter supply. The next contract should target the forward index.

## Findings

### NS1 [major] M=1000 CONTAMINATION-DOMINANT holds only under the grid-best convention; capping is not the cause

- where: kill_test_verdict readings.1000.part_B; reported_arm gated_diagnostics grid; contract Part B
- evidence: Frozen readout: L_c_frozen 28-35, L_i = 180 minus plateau frozen cues (28-35) = 145-152, L_o 65-79, so the rule gives INDEX-DOMINANT on 5/5 seeds. Grid best lifts the plateau-set store to 126-141 cues at J_fb 5-6, g 0.7-0.8, with D4 0.56-0.67, D1 about 0.865, 0 passing points; J=6.0 is the grid edge on seeds 22 and 24. Main's best sits at the g=1.0 edge on 4/5 seeds. The cap only binds at M=500, where it lowers L_c (frozen L_c there is 144-161, so M=500 is robust). L_o uses P2-E4's frozen readout, so the losses are compared under mixed conventions.
- recommendation: State that M=1000 reads CONTAMINATION-DOMINANT under the predeclared grid convention and INDEX-DOMINANT at the frozen point, and send this to the owner as a convention disagreement. Do not use it to choose a feedback-write contract.

### NS2 [major] S1 fails at both loads whatever the feedback write is; L_i cannot see this at M=500

- where: kill_test_verdict per_seed; Part B L_i
- evidence: M=500: C2 fails on seed 23 only (174/200, bar 180); C4-spurious fails on seeds 23 (86/100) and 25 (88/100); L_i is 0 on every seed. M=1000: C2 87-103/200, C4-spurious 35-49/100. The memory raster does not depend on the feedback store, so burst-gated eligibility, the error-correcting feedback write or any other content-write fix inherits this failure. At M=500 the index failure is marginal; at M=1000 it is large.
- recommendation: The Result should say plainly that no feedback-write contract can clear the structured clause on this index. Any such contract must predeclare that it inherits S1, and must not be presented as a route to Stage 1.

### NS3 [major] Part C 'AVAILABLE FROM ACTIVITY' reads back the experimenter's key; it is not a mechanism

- where: gated_diagnostics activity and R_k; online twin_A.R3; contract Part C and Decision
- evidence: Positives are defined by A(x), the cells the plateau just wrote. They fire 3.9-5.5 continuation spikes against 1.05-1.1 for other responders, a consequence of that write. At M=1000, 90% of positives and 0.04% of negatives reach 3 or more spikes, so R_3 is approximately A. J(R_3) matches the plateau-set store within 0-7 cues, including where both fail (M=1000 frozen: 32-40 against 28-35 cues). First-spike AUC is only 0.78-0.81. The Decision rules out plateau-trace eligibility because it equals A x E; R_3 is empirically the same store. R_4 and R_6 beat the plateau-set store at M=1000 (51-63 and 68-84 cues), but R_6 has D1 0.395.
- recommendation: Relabel Part C as 'the plateau key is recoverable from activity'. Apply to burst-gated eligibility the same admissibility argument used for plateau eligibility, and state which supply it removes. It removes none of the key, the value or the write timing.

### NS4 [major] Online C2 near 0.98 is an unpaired comparison consistent with a global excitability shift

- where: reported_arm online, loads.1000 (block, twin_A.memory, twin_B); contract appended predictions
- evidence: Seed 22: online block C2 0.99 against settled twin A C2 0.48. The two use different cue sets, so they are unpaired. Paired twin B shows memory 0.92 settled against 0.565 online (McNemar 11 vs 82). Offset is 8.2 mV online against 3.6 settled, and rises within the block from 7.3 to 9.2 mV. During learning the continuation offset climbs with load (1.1 to 8.2 mV) while |R| climbs from 37 to 268. Both fit a shift along one sensitivity-specificity curve. No 75 ms memory rate is recorded for the online arm, so 'specific but slow' is not measured in P2-E5.
- recommendation: Replace 'the index is specific but slow' with 'online the memory layer fires less: fewer spurious cells and fewer own cells'. To show better discrimination, use a paired per-cue C1 x C2 analysis on the same cues.

### NS5 [major] Plateau-set failure at M=1000 does not show that no write can pass; it is confounded by F=10 line load

- where: gated_lane logs (pooled and F40 at M=1000); readings.1000.pooled; contract 'F = 10, fixed by argument'
- evidence: Pooled control (no sibling correlation, same line loads): plateau-set 0.49-0.63 at the frozen point, C2 0.82-0.835. F=40 (same 17% overlap, roughly uniform load): plateau-set 0.83-0.91, C2 0.785-0.83. s=100: 0.985-0.995. So line load on hot prototype lines alone sinks the item-specific store, and the owner's clause does not fix F. The grid covers only the feedback readout (J_fb, g), and it binds at its edges. Forward-store changes, which alter the index, are untested.
- recommendation: Scope the claim to 'the A x E store under F=10 fails at every point of the 72-point grid; S1 blocks any feedback-only fix'. Put the choice of F to the owner, since it largely decides the content ceiling at M=1000.

### NS6 [minor] D1 near 1 at M=1000 is mostly non-specific; Part D ratios compare stores near saturation

- where: gated_diagnostics label_permuted; online twin_A intrusions
- evidence: The label-permuted store regenerates item-specific missing lines at 0.535-0.583, against 0.987 for main (M=1000). The specificity-check threshold of half is exceeded. Part D WORSENS at M=1000 compares median intrusions of 1,745 and 3,043 out of 4,000 lines.
- recommendation: Report D1 at M=1000 as uninformative, and label Part D's M=1000 ratio as measured at saturation.

### NS7 [minor] Gated records written from a dirty tree

- where: bench/results/plant2.jsonl git.dirty
- evidence: These records have dirty=true with plant2_dirty=false and the same plant2 tree dc16f182: kill_test_seed 21; gated_diagnostics for seeds 21, 24 and 25; seed 23 s80, s40 and pooled, all at commit 38bb6a4. The likely cause is the other lane's uncommitted appends.
- recommendation: Add a note to the Result naming the cause, so that provenance stays exact.

### NS8 [major] The line is accumulating diagnostics; the pending next contract's outcome can largely be predicted from P2-E5

- where: EVAL-after-P2-E4.md Decision 1; P2-E5 Parts A and C
- evidence: Two consecutive gated experiments had no mechanism by design. P2-E5's own text says it removes no supply. The proposed burst-gated feedback write equals the A x E store on the persisted settled rasters at both loads, and on online twin A (M=500: R_3 0.97, the same as the plateau-set store; M=1000: 0.165 against 0.17). It cannot touch S1, which blocks the clause.
- recommendation: Evaluate burst gating as an exact replay on persisted rasters, reported only. Spend the next gated contract on the forward index (see next_steps).

## Next steps

- Hardest open question: can the system decide what its own key stores, so that shared prototype lines stop recruiting sibling assemblies? This forward cross-talk blocks S1 at M=1000 under every convention.
- Single next experiment: one mechanism from the owner-approved error-correcting family. During encoding, an input line is BTSP-eligible only if the reconstruction layer did not regenerate it. Gate it on S1 (C2, C4-spurious) at s=60, F=10, M=1000 on fresh seeds. The feedback write stays P2-E3's. Include a fails-if-false control that drops the same number of lines per item at random. Report F=40, the pooled control and the plateau-set store alongside.
- Add P2-E5's frozen-convention Part B (INDEX-DOMINANT at M=1000) to the Result beside the predeclared reading, and send the disagreement to the owner.
- Run burst-gated (R_3) eligibility only as a reported exact replay on the persisted P2-E4 and P2-E5 rasters, not as its own gated contract.
- Ask the owner to fix F, or the line-load regime, for Stage 1's structured clause before any further structured gate.

## For the owner

P2-E5 failed as predicted, and the record is sound. What it settles: under the settled protocol, the memory index itself fails on correlated items at both loads (narrowly at M=500, heavily at M=1000), whatever content write is used. Fixing contamination therefore cannot by itself meet the structured-input clause. Three cautions. 'Contamination-dominant' at M=1000 holds only under the grid-best convention; at the frozen readout the index dominates. 'Available from activity' recovers your random plateau key, not a cell's own judgement. The online index looks specific only because everything fires less. Two decisions are yours: how many families the clause assumes (F=10 against F=40 changes the content ceiling a great deal), and whether the next mechanism should act on the key (forward write) rather than the content write.
