# P2-E5 results review: northstar constructive lens

Independent reviewer given only the files (HEAD f25d3ed, after the verdict). Run 2026-10-11. Recorded verbatim, before synthesis.

## Verdict

P2-E5's verdict holds as recorded: STRUCTURED INDEX FAIL + STRUCTURED CONTENT FAIL, 5/5 seeds valid, CONTAMINATION-DOMINANT at both loads. The most promising order is: (1) burst-gated feedback eligibility, gated only where the index does not cap it; (2) an access mechanism that must beat the online/settled C1-C2 trade-off, not slide along it (a burst-gated recurrent basin, pending owner Q2); (3) a forward-index mechanism for line load and correlation at M=1000, after the owner rules on context identity. Each removes little supply on its own. Speculative: (1) and (3) give the match and mismatch halves of a later mismatch-triggered plateau, the step that would remove the write oracle and the key.

## Findings

### NS1 [major] Burst-gated feedback eligibility is next, but gate it only where the index does not cap it

- where: bench/results/plant2.jsonl P2-E5 reported_arm gated_diagnostics/online, seeds 21-25; EVAL-after-P2-E4.md Decision 1
- evidence: Gated seeds 21-25, M=500: R_3 store at the frozen point scores 186-194 of 200 cues, against 19-36 for the main store, equal to the plateau-set store (186-195). Online arm, twin A, M=500: R_3 0.93-0.97 against 0.05-0.10 for the online-written store. Count AUC 0.9988-0.9995 at M=500, 0.9955-0.9971 at M=1,000, about 0.999 online. At M=1,000, R_3 scores 34-40 frozen and 127-143 at grid best, the same as the plateau-set store (28-35 / 126-141): capped by the index (L_i 39-54).
- recommendation: Local signal: memory cell i's own spike count in the 50 ms continuation >= 3 (k frozen from Part C). Gate: P2-E3 content gates on fresh seeds; P2-E4 twin-A store, main line and duty arm, at M=500 and 1,000; P2-E5 S2 and S4 at M=500. Report M=1,000 structured content with its index cap predicted (frozen about 0.17-0.20), not gated.

### NS2 [major] Predeclare that every index criterion is inherited bit-identically; S4 at M=500 is marginal

- where: P2-E5 kill_test_verdict per_seed; gated_diagnostics grid.R3.frozen.D4
- evidence: The memory raster does not depend on the feedback store. So P2-E5 S1 still fails at M=500 (C2 174 on seed 23; C4-spurious 86 and 88 on seeds 23 and 25), and P2-E4 ONLINE INDEX and HABITUATION FAIL carry over. R_3's D4 at M=500 is 0.90-0.97, with seed 24 exactly at the 0.90 bar. So P(S4 on 5/5) is well below 1.
- recommendation: State in advance that S1 and the P2-E4 index labels are inherited, and check a memory-raster digest. Compute power from the persisted P2-E5 rasters, not from optimism. Argue for the frozen readout (2.8, 0.3): R_3's density is about the plateau-set's, which is what P2-E3 calibrated on. Report the grid, and do not recalibrate after seeing data.

### NS3 [major] The burst is a forward-match signal inside the write window, not a plateau readout

- where: p2_e1_btsp.py learn_one (BTSP runs before the continuation); EVAL-after-P2-E4.md lure/repeat note
- evidence: The continuation runs after the forward BTSP write. So >= 3 spikes means the cell's fresh synapses match the current input. Exploration (seed 90, P2-E4): an exact repeat bursts 99 % of the old assembly; a lure bursts about 5 of the stored item's cells. Under this rule, old cells would write the new content. That conflicts with distinct episode identities for repeated items, the familiarity question the owner deferred.
- recommendation: Label the signal as post-write forward match, which still depends on supplies 1-2. Report repeat, lure and s=40 arms with a damage measure: the old item's own joint before and after the lure or repeat. Use the no-plateau sham (about 0 eligible cells expected). Put the context-identity collision to the owner before Stage 2.

### NS4 [major] The access problem is a one-variable frontier; the second mechanism must leave it

- where: P2-E5 online arm, block.rates and twin_A.memory at M=1000, seeds 21-25
- evidence: Online (offset 8.1-8.3 mV): C1 0.54-0.585, C2 0.975-0.99. Settled, same synapses (about 3.6 mV): C1 0.915-0.945, C2 0.435-0.515. L_o 65-79 cues at M=1,000 is material and exceeds L_i on every seed. A threshold or tau change would only move along this curve, as the owner warned.
- recommendation: Next, a burst-gated recurrent completion basin: binary memory-to-memory synapses where pre and post both fire >= 3 continuation spikes, plus fixed activity-proportional memory inhibition if the owner rules yes on Q2. It must show online C1 >= 0.9 within 50 ms and C2 >= 0.9 together at M=1,000. Controls: the no-recurrence system swept along its own threshold curve (reported only), a no-recurrence twin with the same inhibition, inhibition alone, and a degree-matched shuffled recurrent store. Count whole sibling assemblies ignited.

### NS5 [major] The forward-index failure at M=1000 is partly per-line load, not only correlation

- where: P2-E5 readings[1000].pooled; gated_diagnostics spurious; plant2/btsp.py toggle rule
- evidence: The pooled control reads LINE LOAD SUFFICIENT, CORRELATION WORSENS: the pooled arm gains 62-77 cues of C2 and 70-92 of plateau-set joint, yet still fails S2. There are 16.5-18.9 spurious cells per cue, 98 % of them siblings' plateau cells, with about 9.2 strong synapses from the cue's prototype lines and about 4 from its specific lines. Under BTSP's toggle rule, cells that serve many siblings collect prototype weight.
- recommendation: Third contract: one forward-eligibility mechanism, chosen by a predeclared contrast. Either error-gated (a line is eligible only if memory did not regenerate it; this needs NS1's clean store and on-time retrieval during encoding), predicted to help the main arm more than pooled; or presynaptic-load-gated (the line's own count of potentiated synapses), predicted to help both. Target: C2 at M=1,000 from 0.435-0.515 to >= 0.9, L_i below 20, s=100 unchanged.

### NS6 [minor] R_4 and R_6 look better at M=1000; choosing them would be parameter rescue

- where: gated_diagnostics R_k at M=1000
- evidence: At the frozen point, R_4 scores 51-63 cues and R_6 70-84, against 34-40 for R_3. But D1 falls to about 0.84 and 0.40: missing lines are lost to sparser writers.
- recommendation: Keep k=3 as frozen in Part C. Report R_k only. Any later change of k needs its own contract and fresh seeds.

### NS7 [minor] Honest supply accounting, and the path to removing the write oracle (speculative)

- where: EVAL-after-P2-E4.md supply table, items 1-7
- evidence: NS1 removes only the dependence of write quality on the schedule's state separation (item 7, content side). NS4 would remove the rest before testing (item 4, access). The key, the write oracle and the verbatim value remain.
- recommendation: Each contract should name the supply it removes. Speculation: a burst (strong forward match) and an error signal (feedback did not predict the input) are the two local terms of a mismatch-triggered plateau. That would remove items 1-2 and can be contracted only after NS1 and the forward step, and the owner's ruling on context identity.

### NS8 [minor] Bearing on sequences, abstraction and problem solving (speculative)

- where: STAGES.md Stage 2, 3 and 5 gates
- evidence: R_3 has about 20 cells per item, against |R| of 41-277 online. Prototype cues give about 3,500 lines at M=1,000: superposition, not abstraction.
- recommendation: Sequences: the basin's co-burst rule with a lag is the one-shot transition rule. Sparse tags keep a chain from becoming a blur, but shared items still need distinct context assemblies (NS3). Abstraction: none of these is abstraction. Error-gating might split shared structure from distinctive detail, and must still meet ruling 5 and exemplar specificity. Problem solving: replay during perception would set off bursts that write the current input onto memories, so writes stay gated by the oracle until mismatch plateaus exist.

## Next steps

- Get owner rulings on EVAL-after-P2-E4 Q1 (burst-gated eligibility), Q2 (memory-layer stabilising inhibition) and Q3, using P2-E5's gated numbers: CONTAMINATION-DOMINANT at both loads, L_o > L_i at M=1,000.
- Contract 1, burst-gated feedback eligibility (k=3, frozen readout argued): gate P2-E3 content, the P2-E4 twin-A store (main line and duty arm) and P2-E5 S2/S4 at M=500. Predeclare that every index criterion is inherited, with a raster digest. Controls: size-matched random subset and anti-selected subset, plateau-set store as a reference only, leak check, no-plateau sham, and repeat and lure damage arms. Power comes from the persisted rasters. Also replay on P2-E4 and P2-E5 rasters as reported arms.
- Read the duty arm as decisive. If the store reaches the bar there, the content side of the trade-off belongs to the write rule. If not, the next mechanism is a state the network generates itself.
- Contract 2, a burst-gated recurrent basin, only with the Q2 ruling: pass requires online C1 >= 0.9 within 50 ms and C2 >= 0.9 together at M=1,000, beyond the no-recurrence frontier, with shuffled-recurrence and inhibition-only controls and sibling-ignition counts.
- Contract 3, forward eligibility (error-gated or presynaptic-load), chosen in advance by the pooled-arm contrast and after the owner rules on context identity. Target: C2 at M=1,000 >= 0.9 and L_i below 20.

## For the owner

P2-E5 failed as predicted, cleanly on all 5 seeds. The network's own burst signal finds each item's cells. A store written only by bursting cells matched the upper-bound store (93-97 % of cues at M=500, online too), against 10-18 % for the current write. My recommendation: make that the next contract, gated only on content at M=500 and on the earlier online tests. The memory index fails separately at M=1,000. Online it is specific but slow; settled it is fast but loose (C2 about 0.48). One slow threshold trades the two, so retuning cannot fix it. A second contract needs a mechanism that wins both, perhaps recurrent completion with stabilising inhibition, if you allow it. Then fix how shared lines are keyed. Your ruling on context identity matters first: under burst gating, repeats and lures write onto old memories.
