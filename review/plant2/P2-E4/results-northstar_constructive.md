# P2-E4 results review: northstar constructive lens

Independent reviewer given only the files (HEAD bbeb25b, after the verdict and the post-verdict diagnosis). Run 2026-10-11. Recorded verbatim, before synthesis.

## Verdict

P2-E4 points at coordination, not storage. At M = 1,000 online index recall is 0.68-0.74, yet 86-100 % of failures pass after a settle with the same synapses. Meanwhile the online-written store reads 0.82-0.905 against 0.985-1.0 for the plateau-set store. The most promising next mechanism is the owner's hypothesis in its activity form: burst-gated feedback eligibility (a cell writes content only if it fires >= 3 spikes in the 50 ms continuation). In my exploratory seed-90 probe it held the store at 0.995 in the main line and in the low-offset duty arm (online-written: 0.83 and 0.205), so it removes the write side of the encoding-retrieval trade-off. Second comes an access mechanism: eligibility-gated recurrent completion with a fixed stabiliser. Neither fixes forward-index cross-talk on correlated items, and Stage 1 is several contracts away.

## Findings

### NS1 [major] First mechanism: burst-gated feedback eligibility, which decouples write quality from the operating point

- where: plant2/experiments/p2_e3_completion.py:76-82 (every cell with >= 1 continuation spike writes R x E); DECISIONS.md 2026-10-11 hypothesis; P2-E5 Part C
- evidence: Gated seeds 16-20, items 751-1,000:
- |R|: main 41-45, duty arm 121-136, P2-E3 protocol 28-29.
- Twin A joint at M = 1,000: online-written 0.82-0.905; duty 0.175-0.245; plateau-set 0.985-1.0.

Exploratory (my probe, seed 90, frozen driver with a read-only step wrapper):
- Continuation-count AUC, A against other responders: 0.9999 on main and on duty. Other responders reach >= 3 spikes in 0 % and 0.09 % of cases.
- |R_3| is 20.4-20.7, and Jaccard(R_3, A) is 0.99.
- Twin A at M = 1,000 (main / duty): online-written 0.83 / 0.205; R_3 0.995 / 0.995; plateau-set 0.995 / 0.995.
- The duty arm's online C1 is 0.955, at a 4.1 mV offset.

One seed; settled readout only.
- recommendation: Contract it first. Its local signal is the cell's own continuation spike count >= 3. k is fixed by P2-E5 Part C, so it is not tuned.

Gate only its target:
- the twin A online-written joint >= 0.95 at M = 500 and 1,000, on the main line and on the duty arm;
- P2-E3's content gates on fresh seeds, with unchanged bars. Argue the frozen readout: R_3's density matches the plateau-set store's.

Label what it removes: the write's dependence on protocol (P2-E3 addendum 2). It does not remove the write oracle, the key or the value.

### NS2 [major] Predicted effect of the eligibility write on each P2-E4 and P2-E5 criterion: no index criterion can move

- where: p2_e4_online.py Online (rec has no outgoing projection); P2-E4 kill test; P2-E5 kill test and Parts B-D
- evidence: The memory raster does not depend on the feedback store, so the following are bit-identical by construction: O1 C1-C3, O3 memory, O4 and O5 (C1 0.68-0.74 at M = 1,000), and P2-E5 S1.

Predictions for P2-E4:
- O2 joint: 0.93-0.965 -> about 0.97-1.0;
- O3 content: 0.90-0.97 -> >= 0.95;
- D3: unchanged;
- twin B content discordances (online pass, settled fail): 15-28 -> about 0-5.

Predictions for P2-E5:
- S1: fails, unchanged;
- S2 at M = 500: 0.10-0.145 -> about 0.93 (P(all five seeds) about 0.72, by the oracle-store row);
- S4 at M = 500: about 0.88-0.95 (about 0.27);
- at M = 1,000: about 0.16;
- S3: holds;
- Part D: NOT WORSE.
- recommendation: Make a memory-raster digest a validity check. State in advance that ONLINE INDEX FAIL, HABITUATION FAIL and STRUCTURED INDEX FAIL are inherited.

Report the P2-E4 and P2-E5 criteria against their records; they are not this mechanism's gates. A PASS would mean only that the write is item-specific in every regime tested.

### NS3 [major] Burst eligibility is not A(x) in disguise: it diverges on lures and repeats, where the familiarity question lives

- where: the owner's hypothesis (DECISIONS.md 2026-10-11); P2-E4 OOD arm (lures recalled as the stored item 0.90-0.95 on gated seeds)
- evidence: Exploratory, seed 90, on a copy at M = 1,000 with no plateau, BTSP or write. Cells reaching >= 3 spikes in the continuation window:
- fresh items: 0 cells (45 fire at least once);
- lures sharing 50 lines: 26 % of the stored item's A cells (about 5 cells), and no others;
- exact repeats: 99 % of A.

So a lure's encoding would write its 50 new lines onto about 5 cells of the old memory, and a repeat re-writes onto the old assembly. The plateau-set store does neither. P2-E5's s = 40 arm comes close to lure overlap.
- recommendation: Predeclare reported arms where the two stores differ, with predictions:
- lures learned as items, with later intrusions scored on the original;
- repeats learned as items;
- P2-E5 s = 40.

Make the sham control a validity check (fresh items give about 0 eligible cells), which shows eligibility follows the plateau-driven write. These arms are what make a pass informative.

### NS4 [major] Access fails because every cue sits near the bar with no completion basin; widen the basin rather than move a threshold

- where: P2-E4 diagnosis (gated D2 and D3); reported_arms ood; plant2/experiments/p2_e1_btsp.py (a one-layer feedforward index)
- evidence: Gated diagnosis:
- Failing cues are slowed: the A first spike comes 6-11 ms later.
- 71-100 % of them reach the bar by 75 ms, and 86-100 % pass after the settle.
- The assembly offset of failing minus passing cues is -0.22 to +0.70 mV: no consistent cause.

Seed 90 (mine): cue-synapse margin predicts failure only weakly (AUC 0.59-0.67), and onset offset hardly at all (0.49-0.60).

OOD arm, gated seeds: 10 of 50 cue lines swapped gives C1 0.075-0.175, and 30 % cues give 0.00.
- recommendation: The second contract: eligibility-gated recurrent auto-association.
- One-shot binary memory-to-memory synapses where pre and post both reach >= 3 continuation spikes (NS1's signal).
- J_rec fixed by argument.
- Fixed activity-proportional memory-layer inhibition as a stabiliser: J_rec >= 1.5 ran away (P2-E1 review F6). This needs the owner's ruling, because ruling 3 covers Stage 2.

It comes after NS1. Completion during the continuation would otherwise enlarge R, as the duty arm did.

### NS5 [major] What the basin mechanism must show, and the controls that separate it from a lowered threshold

- where: P2-E4 O1-O5 bars; P2-E5 S1; P2-E1 review F6
- evidence: P2-E1 review F6: J_rec 1.0 completed assemblies (12 -> 16 cells) without runaway at M = 250. J_rec 1.5 left 3,969 cells active at M = 1,000.

Speculative risk: on correlated items, siblings' cells receive about 9 prototype lines from the cue, so recurrence could complete sibling assemblies.
- recommendation: Predictions to commit:
- online C1 and O3 memory >= 0.90 at M = 1,000 in the frozen 50 ms window;
- C2, C3 and D3 unchanged;
- the continuous habituation drop (NS6) < 0.05;
- no self-sustained ignition over 60 s;
- P2-E5's C2 and C4-spurious do not fall;
- noisy-cue C1 >= 0.5 (reported).

Controls:
- a no-recurrence twin with the same inhibition;
- an inhibition-only twin;
- a degree-matched shuffled recurrent store.

A gain the shuffled store also produces is a lowered threshold.

### NS6 [major] Habituation is universal and graded; O4's binary label mostly measures margin

- where: ~/.cache/brain-sim/plant2/p2_e4/seed{16..20}_habituation_*.jsonl.gz; diagnosis D4
- evidence: Read-only analysis (mine, ~/.cache/brain-sim/review/p2e4-results/north-star/hab_margin2.py). On every gated seed and load, all 50 items recall less in the repeated copy's late steps than in the control copy's.
- Mean drop: 0.107-0.119 at M = 500 and 0.124-0.134 at M = 1,000. SD is about 0.03, and the minimum is 0.018-0.070.
- Most of the fall comes within 40 repetitions (20 s), consistent with a 10 s accommodation.
- Being labelled habituated tracks the control copy's late recall: AUC 0.62-1.0 on 9 of 10 seed-loads (0.40 on seed 19 at M = 1,000, with 9 eligible items).
- recommendation: Record this as a post-hoc reported reading: every repeatedly driven assembly accommodates, and O4 counts the items near the bar.

Later contracts should report the continuous drop beside O4, so that a margin-widening mechanism cannot pass O4 while the drop persists.

Keep the owner's advice: changing the accommodation tau is not the fix.

### NS7 [minor] Writes during probes: only 16-20 % of the extra writes were retrievable, against 'nearly all' predicted

- where: reported_arms wps (contract's reported-arms table: 'nearly all stored')
- evidence: Gated seeds: 163-173 probe writes, with stored_frac 0.16-0.20. My reading: the re-presented 50-line cue drives a new assembly that was written from about half an encoding's lines in a 100 ms slot, at an offset of about 7 mV. This is NS4's thin margin again.
- recommendation: State the failed prediction in the Result.

It argues for the basin before any mechanism that writes without the oracle. A system that decides when to write must be able to retrieve what it wrote from weaker experiences.

### NS8 [major] Forward-index cross-talk on correlated items lies outside both mechanisms

- where: P2-E5 'Why this test' and Decision; STAGES Stage 3
- evidence: P2-E5 exploration at M = 1,000:
- C2 is 0.45-0.55, with about 19 spurious cells per cue, 98 % of them siblings' plateau cells.
- The plateau-set store's grid best is 0.60-0.665.

NS1 cannot touch this. NS4 could worsen it, or its inhibition could let the cell's own assembly (about 25 driving lines) suppress the siblings' (about 9). Speculation.
- recommendation: Leave it with the owner, as P2-E5 does. A speculative candidate from the approved error-correcting family is error-gated forward eligibility: an input line is BTSP-eligible only if rec did not regenerate it during the encoding, so new assemblies key on what memory did not predict.
- It needs NS1 first, for a clean comparator.
- It trades C1 on prototype-heavy cues for C2.
- If P2-E5 reads INDEX-DOMINANT at both loads, it could come before NS4.

### NS9 [minor] Third mechanism: genuine, mismatch-triggered plateaus, after the owner rules on context identity

- where: DECISIONS.md (2026-10-10 ruling 4; 2026-10-11 hypothesis); P2-E5 Decision
- evidence: Plateau-event eligibility equals A(x) until a separately contracted mechanism supplies a key the experimenter does not. Familiarity gating is deferred until a repeated item keeps distinct identities across contexts. NS3 shows that burst eligibility already acts like familiarity on repeats.
- recommendation: Speculative: a plateau fires when input drive coincides with a local mismatch (the line is active but not regenerated). That would remove the write oracle and the content-blind key, the largest supplies left.

It needs NS1, NS4 and the owner's ruling on context. It must show:
- novel items and lures get new plateaus;
- same-context repeats do not;
- autonomous writes are stored at >= 0.8.

### NS10 [minor] Bearing on sequences, abstraction and problem solving

- where: STAGES.md Stages 2, 3 and 5; EVAL-after-P2-E3.md
- evidence: At M = 1,000, continuation responders number 41-45 on the main line and 121-136 in the duty arm, against about 20 assembly cells. The writes-during-probes arm (NS7) shows that activity-driven writes are mostly unretrievable.
- recommendation: Sequences: NS1's eligibility, held as a decaying trace within BTSP's window, is the natural pre-side signal for memory-to-memory transitions. Without it each transition would link 41-136 cells. NS4's stabilised recurrence is the substrate for chained replay.

Abstraction: none of these mechanisms is abstraction. NS1 secures exemplar specificity for Stage 3's joint clause.

Problem solving: a planner replays while it perceives. Activity-based eligibility would let replayed assemblies write the current input, so eligibility tied to a perception-triggered plateau (NS9) is the guard. NS1 is a step toward the owner's hypothesis, not its end.

### NS11 [minor] Make a pass mean something: a fails-if-false control, out-of-distribution arms and an experimenter-supply ledger

- where: EVAL-after-P2-E3 risk 4 (benchmark collecting); P2-E3 addendum item 8
- evidence: Seed 90 (mine): a random subset of R(x) of R_3's size reads 0.885 on the main line and 0.71 in the duty arm, against 0.995 for R_3. So identity, not sparsity, carries the gain.

Spike counts depend on drive, and k = 3 is an absolute count.
- recommendation: Gate a size-matched random-subset control, which must lose by >= 20 cues in the duty arm, and add an anti-selected (lowest-count) subset.

Predeclare these arms with predictions: a = 50 and 200, other input rates, s = 80 and 40, noisy and 30 % cues, lures, repeats.

Add a row saying which of EVAL's six supplies the mechanism removes.

Replay NS1 on P2-E4's gated seeds and on P2-E5's persisted rasters, beside fresh gated seeds.

## Next steps

- Append to the P2-E4 Result, labelled post hoc and reported: habituation is universal and graded (NS6), and the writes-during-probes prediction failed (NS7). Use the owner's wording of 'zero passes in 1,500 simulations'.
- Run P2-E5 exactly as frozen. Read Part C (count AUC, R_3) and Part D before any mechanism contract; Part B decides whether index cross-talk (NS8) jumps the queue.
- Ask the owner three things: (1) whether the activity form of the eligibility hypothesis (>= 3 continuation spikes) may be contracted next; (2) whether a fixed stabilising inhibition may join a Stage 1 recurrent mechanism; (3) where forward-index cross-talk goes.
- Draft the eligibility contract (NS1-NS3, NS11). Red-team it, replay it on existing rasters as reported arms, then gate it on fresh seeds. Gate its target only.
- Then contract the basin (NS4-NS5), then mismatch-triggered plateaus (NS9) after the owner's context ruling, and only then the Stage 2 transitions that reuse the same eligibility trace.
- Reviewer artefacts (exploratory, seed 90): ~/.cache/brain-sim/review/p2e4-results/north-star/probe90.py, probe90_sham.py, hab_margin2.py and their .json and .log outputs.

## For the owner

P2-E4 failed on access, not storage. At 1,000 items about a third of cues are recalled too slowly while learning goes on, but nearly all come back after a rest, and the content holds.

Your hypothesis fits. A cell that may write an experience's content only if it fires a short burst (3 or more spikes in 50 ms) picks out the right cells almost perfectly. In my one-seed exploratory check it kept the store as clean as the assigned-assembly ideal, even in the low-threshold duty arm (0.995 against 0.205). That removes the write side of your trade-off.

It cannot fix slow access or habituation. Every item habituates a little. That needs a second mechanism, in which part of a memory recruits the rest.

Your rulings needed:
- the burst rule as the next contract;
- stabilising inhibition in Stage 1;
- where index cross-talk on related items belongs.
