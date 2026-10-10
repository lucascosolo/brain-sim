# P2-E3 review: methodology lens

Fresh reviewer given only the files (review packet in the workflow prompt; no implementer history). Model: session default. Run 2026-10-10. Recorded verbatim, before synthesis.

## Verdict

The PASS can be trusted. The steps ran in the declared order (contract, red-team, code, bug fix, re-calibration, committed predictions, then gated runs 7 s after commit c97f237). The plant2 code tree did not change during the runs. Seeds 11-15 were fresh. J_fb* = 2.80 and the g=0 fallback of 1.45 follow the rule. The joint criterion and D3-D5 are computed as written, and every gated number re-derives from the JSONL. The bug fix left all 202 readout arms bit-identical. The Result's wording needs an addendum: the plateau-set control is read backwards, 'nothing' is overstated, the bug-fix note is incomplete, and 'content' means a verbatim lookup keyed by an assigned code. The P2-E4 draft is not ready.

## Findings

### F1 [major] Plateau-set control read backwards; the activity-based part of the write is not shown to matter

- where: P2-E3-content-completion.md Result: comparison table plateau-set row, 'Responders' bullet, predictions table; STAGES row
- evidence: At M=1,000 the arm written from A(x) is equal or better than main on every seed. Joint 0.980-0.990 vs 0.955-0.985 (seed 14: 0.985 vs 0.955). D2 is 1.000 on 5/5 seeds vs 0.970-0.995. HD p90 0.08 vs 0.10. Novel-cue max 0-2 lines vs 0-22. Jaccard(R,A) is 0.87-0.88, and 0.99 at M=250. Yet the Result says 'the activity rule loses nothing' and 'extra responders cost no measurable specificity', and marks 'slightly fewer intrusions' as wrong. E(x) is the input copied verbatim, so the path is an outer-product write keyed by the plateau code.
- recommendation: Addendum: the activity-based write adds nothing measurable over writing from the assigned plateau set. Its extra responders add a few intrusions (D2 is lower on 5/5 seeds). The regenerated content is the verbatim input, keyed by a random assigned index. Correct the prediction row and carry this into the north-star evaluation.

### F2 [minor] Bug-fix note incomplete: more than C2 changed, and D5 flipped

- where: P2-E3 'Calibration result', bug paragraph; JSONL rows 58 vs 62
- evidence: Seed 0, M=1,000: C2 went 0.880 to 0.970, but C3 also went 0.970 to 1.000 and C4 spurious 0.90 to 0.98, so gate_ok flipped from False to True. The doc says only C2 changed. All arms, learning summaries and convergence are bit-identical (checked), and the fix restores the contracted 50 ms window, so content and J* could not move. But under the bug D5 failed on seed 0, so the fix moved the expected label from CONTENT PASS / P2-E2 REPLICATION FAIL toward PASS. 'Neither the continuation nor the test code' is muddled.
- recommendation: Addendum: list all three changed numbers and the gate_ok flip. Say plainly that the fix restored the contract's 50 ms memory window and was looked for because D5 looked bad. Cite the seed-0-only diagnostics in ~/.cache/brain-sim/plant2/diag/e3_memory_c2*.py.

### F3 [minor] 'Unlearned cues regenerate nothing' is overstated

- where: P2-E3 Result, 'What this shows'
- evidence: novel_lines_max at M=1,000 is 1, 1, 0, 22, 2 (seeds 11-15), and D3 is 0.990 on seed 14. The Result's own table says 'max 22 on one seed'.
- recommendation: Reword: unlearned cues regenerate almost nothing. The median is 0 lines; at most 1 % of novel cues reach 10 lines (max 22).

### F4 [minor] 'Inhibition required' was settled at calibration and needs a scope

- where: Contract 'Matched no-inhibition comparison'; verdict() in p2_e3_completion.py; Result and STAGES
- evidence: The contract's two readings are not mutually exclusive when the fallback J is used, and verdict() returns 'required' whenever --j0-fallback is set. No gated outcome could have produced 'unnecessary'. The seed-0 margin was 0.88 against 0.90. The gated failure is solid (joint 0.77-0.86, fails on 5/5 seeds at M=1,000). But the matched arm passes on 5/5 seeds at M=250 and 500 (0.92-0.965), and STAGES says only 'so inhibition is required'.
- recommendation: Scope it everywhere: with this fixed-threshold readout, inhibition is needed at M=1,000 (matched arm 0.77-0.86) and not at M<=500. Make the readings exclusive in future contracts.

### F5 [minor] STAGES row and headline drop the labels

- where: docs/plant2/STAGES.md P2-E3 row; Result 'What it does not show'
- evidence: The STAGES row says 'the half cue regenerates the missing half of the input'. It does not say that the target is copied verbatim through a per-line instructive channel, that the index comes from random plateaus, or that testing used frozen copies after a 50 s settle. 'What it does not show' omits that no generalisation was tested: D3 requires novel cues to regenerate nothing.
- recommendation: Add to the STAGES row: verbatim input-supervised store keyed by an assigned code; frozen copies after a 50 s settle; no generalisation tested. Add the generalisation point to 'does not show'.

### F6 [nit] Number slips in the Result

- where: P2-E3 Result tables and bullets
- evidence: Main D2 at M=1,000 is given as 0.970-1.000; the JSONL has 0.970-0.995. 'About 2 more spikes per line': 204-252 out-of-window spikes per cue are averaged over 600 cues, including 200 novel cues with about 0 lines, so it is about 3-4 per regenerated line. 'pi(x)'s missing lines' is really pi(x)'s 100 lines minus any overlap with x's cue. Every other number re-derives exactly from rows 64-69.
- recommendation: Correct these in the same addendum.

### F7 [nit] The only gated control cannot fail

- where: Contract 'Void'; Result void table
- evidence: The shuffled arm (13 % density, below g) gives D1 0.000 by construction. It is honestly labelled a leak check. STAGES' 'against a never-trained or shuffled control' is met in letter only. The label-permuted result also follows from how a Willshaw store works.
- recommendation: Keep the label. From P2-E4 on, gate at least one control that could pass if the claim were false, such as a paired settled vs unsettled twin.

### F8 [nit] Provenance: hand-entered ledger times; gated seed 13 used in a unit test

- where: review/ledger.jsonl; plant2/tests/test_p2_e3.py
- evidence: The ledger stamps the P2-E3 red-team rows 11:40Z, before the 15:40Z draft commit; the P2-E2 rows are stamped 10:45Z against a 10:29Z commit. A test runs run_seed(...,13,...) on an 800-cell config before gating; no information leaks. A test comment says 'never elsewhere' but the test asserts only E being a subset of the targets of R. Calibration and gated code trees differ only by the added verdict subcommand (checked).
- recommendation: Machine-stamp ledger rows. Use non-gated seeds in tests. Fix the test comment or the assertion.

### F9 [major] P2-E4: the gated probe settles the network itself

- where: P2-E4 draft, 'Gated probes'
- evidence: The gated probe is 600 cues x 300 ms = 180 s, in a fixed order (half, novel, full), against an accommodation tau of 10 s. The P2-E2 methodology review (seed 0) found C1 0.875 straight after learning, 0.915 after 5 s of background and 0.94 after 50 s. Only the first few dozen cues are really 'no settle'. O1 and O2 would mostly score a settled state, the condition the experiment is meant to remove.
- recommendation: Interleave gated cues into the learning stream (for example one cue per inter-item interval, kinds in random order), or keep blocks much shorter than tau. Predeclare recall against position in the block.

### F10 [major] P2-E4: the 2 s inter-item interval is a new, unfrozen parameter that acts as a spread-out settle

- where: P2-E4 draft, 'No new mechanism' and 'Learning'
- evidence: The draft says every parameter is frozen, but the 2,000 ms background interval is new: P2-E2 and P2-E3 learned items back to back. It sets the learning duty cycle (11 %) and therefore vbar at test, which is the quantity behind C1 going from 0.875 to 0.915 with 5 s of rest. The draft lists it as an open point.
- recommendation: Fix the interval from an argument made before any run. Gate at the hardest defensible value (0-250 ms), or at two predeclared values, and explore on seeds 42-43 only.

### F11 [major] P2-E4: O5 can hardly pass, from sampling alone

- where: P2-E4 draft, criterion O5
- evidence: O5 requires all 10 repeated items to meet the joint criterion. At P2-E3's per-item rates (0.955-0.985 at M=1,000, 0.99-1.0 at M=500), P(10 of 10) is 0.63-0.86 and 0.90-1.0 per seed and load. Across 5 seeds x 2 loads, P(all pass) is about 0.2 even with perfect recovery.
- recommendation: Use about 50 items with the 90 % bar, or bar recovery as a paired before/after change with a predeclared tolerance. Run a power calculation for every gated fraction.

### F12 [major] P2-E4: no paired twins, and the probe effect is misdescribed

- where: P2-E4 draft, protocol and 'Reported'
- evidence: There is no settled-copy arm at the gated loads, so the cost of online testing is read across seeds against P2-E2/E3. There is no twin without probes, so interference caused by probes cannot be separated from interference caused by learning. Probes shift vbar, which changes later responders and so later writes. 'Feedback-store growth that the probes cause' is wrong: probes write nothing themselves.
- recommendation: At each gated load add a deep copy given the 50 s settle and P2-E3's test, and a twin timeline without rolling probes. Report store digests. Reword the probe-effect line.

### F13 [minor] P2-E4: the experimenter switches between learning and recall

- where: P2-E4 draft, 'Plateaus occur only during encodings'
- evidence: Writes are gated by the schedule, so a probe can never be stored and novel probes never become memories. 'Online' here means alternating modes labelled by the experimenter, not learning while recalling in one stream.
- recommendation: Label this limitation in the hypothesis and in 'does not show', or add a reported arm with plateaus at their base rate during probes.

### F14 [minor] P2-E4: habituation arm confounded, and FAIL has no defined meaning

- where: P2-E4 draft, habituation arm, O4 and predictions
- evidence: The 10 items run one after another on one copy, so item 10 is tested after 270 s of the other items' repeats. O4 turns the owner's 'covers habituation' into a no-habituation bar. The draft then predicts FAIL and says that would 'identify the next mechanism', which clashes with stopping on FAIL and invites stacking mechanisms.
- recommendation: Give each item its own copy, or randomise the interleaving. State what an O4 FAIL means (Stage 1 incomplete; a new single-mechanism contract) and what level of recovery counts.

### F15 [minor] P2-E4: details not pinned down

- where: P2-E4 draft, protocol and validity
- evidence: Not specified: whether rec is simulated continuously or replayed per probe, and when it is reset; whether novel items are reused across 20 rolling probes; what replaces the convergence bar; whether stores are checked to be unchanged across probes; which seeds the red-team may explore on.
- recommendation: Pin each one. Add a check that neither store changes during any probe. Name the exploration seeds.

## Next steps

- Append a corrections addendum to P2-E3 (F1-F6); leave the text above it unchanged
- Rewrite the STAGES P2-E3 row with its labels and the scope of the inhibition reading
- In the north-star evaluation, state that P2-E3 is a verbatim lookup keyed by an assigned code, with no generalisation tested
- Revise the P2-E4 draft for F9-F15, then send it to a two-critic red-team that explores on seeds 42-43 only

## For the owner

The P2-E3 pass is real. It was predeclared, run on fresh seeds and computed as written, and every number checks out. The bug fix restored the contract and could not change the content results. Read it narrowly: the network stores each input word for word, keyed to a randomly assigned memory code, and replays it. Writing from the network's own spikes added nothing over writing from that assigned code. Inhibition was needed only at 1,000 items. Nothing here is generalisation. The online-memory draft needs rework before review. Its long test block lets the network settle anyway, the 2 s gap between items is a new, unjustified setting, O5 would fail on chance alone, and it lacks paired comparison runs.
