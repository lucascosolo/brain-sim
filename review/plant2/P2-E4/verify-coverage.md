# P2-E4 contract verification: coverage

Fresh checker given only the files (revised contract at commit b1ec05a). Run 2026-10-10. Recorded verbatim, before synthesis.

## Verdict

The contract cannot be frozen yet. The ledger has 42 rows for this red-team, and the revision does most of what they say: the M = 250 block is no longer gated and its cohort is gone, sham encodings and a paired control are in, stratified 240-step blocks, twin B, the novel-duty twin, the reference line with store swaps, the validity checks, the verdict vector with joined labels, the Decision section, power computed before freezing, and the cut arms. I re-ran plant2/power.py and every power number in the contract checks out (0.83, 0.91/0.91, 0.65 and the O4/O5 table), except one quoted figure, which is wrong.

One blocker: the positive control of the gated blank-slot leak check (validity 9) is specified so that its content half reads about 0 by construction. Validity is checked before the criteria, so the gated verdict would come out INVALID.

One major problem: at the contract's own expected M = 1,000 per-cue rate of 0.77, O4 and O5 fail even with zero habituation and full recovery. The verdict would then read HABITUATION FAIL and RECOVERY FAIL. That is the confusion red-team finding M3 (and ledger row 91 of the P2-E3 review) asked to remove.

Partly done against the ledger:
- M3: the McNemar test is missing.
- M4, m2, FID-7: age-0 blank targets average about 1 per block.
- M14: the probed against never-probed contrast cannot be measured at M = 1,000 as defined.
- C3: the "owner may overrule" note is missing.
- C7: the contract does not say what an O3 FAIL means for the 60 s clause.

The owner's rulings are met line by line, with two gaps. Power for the full five-seed rule is not stated: only O1-O3 is given. And the P2-E3 addendum's commitment that P2-E4 has a gated control that could pass if the claim were false is not reconciled.

The revision also introduced new problems:
- uniform rolling slots have no legal target in steps 162-181;
- a habituation item's collateral can also be one of the control copy's 89 cues;
- the cohort rule's scope conflicts with settled twin A's test;
- the sham copies' `rec` state differs from the main line's;
- the O5 prediction contradicts the Power section;
- some draft text and numbers were left over.

## Findings

### F1 [blocker] Validity 9's positive control fails by construction (content half about 0), which makes the gated verdict INVALID; the novel-slot baseline is undefined

- where: docs/plant2/P2-E4-online-memory.md lines 279-288 (validity 9), 133 (projection reloaded 'right after each write'), 261 (validity first); plant2/experiments/p2_e3_completion.py lines 78-82 (continuation loop, then self.fb.add); review/plant2/P2-E4/redteam-implementation_mechanism.md m3
- evidence: Line 281: the leak statistic is 'the mean fraction of the target's assembly active within 50 ms, and of its designated missing lines regenerated within 75 ms'. Line 283: the positive control is 'the same measure over the last 50 ms of the age-0 item's own continuation'. Line 288 requires 'the positive-control mean is >= 0.5'.

During that continuation the item's own R(x) x E(x) feedback synapses do not exist yet. E3.learn_one adds them (line 82) only after the 50-tick continuation loop (line 78), and the contract reloads the live projection after the write. Red-team m3 (refuter confirmed) also measured `rec` at -109.8 / -102.1 / -89.8 mV at the end of the continuation (M = 250 / 500 / 1,000), so `rec` is silent there.

So the missing-line half reads about 0. The assembly half reads about 1: Jaccard(R, A) of 0.49 with |R| about 45 and |A| about 20 puts nearly all of A inside R.
- Averaged into one number, the control sits at about 0.5 against a bar of >= 0.5, a coin flip.
- Read as two statistics, the content half fails with certainty.

A 75 ms content window also cannot fit inside a 50 ms continuation. Validity takes precedence (line 261), so the gated verdict becomes INVALID.

Separately, 'the same-block novel-slot baseline' (line 287) is undefined: a novel slot has no target assembly and no designated missing lines.
- fix: Split the statistic into a memory part (assembly fraction, 50 ms) and a content part (missing-line fraction, 75 ms).
- Give each part a defined baseline: for each novel slot, an unreserved stored item of age 0-20 drawn at seed start (stream 15) and not cued in that slot, scored the same way.
- Take the memory positive control from the age-0 continuation (assembly fraction >= 0.5).
- Take the content positive control from the same block's cued recent slots (missing-line fraction >= 0.5), or state that the content leak check has no positive control in this architecture.

Fix this before freezing.

### F2 [major] HABITUATION FAIL and RECOVERY FAIL will be produced by per-cue unreliability, not habituation, at the contract's own expected M = 1,000 rate

- where: lines 214-217 (eligible, habituated), 246-249 (O4, O5; 'fails (not estimable)'), 299-301 (pass/fail vector), 308-309 (labels), 350-355 (Power text), 409, 413-414 (predictions); ledger M3; ledger row 91 (P2-E3 F11 'O5 can hardly pass, from sampling alone')
- evidence: Line 353-354 claims 'So O4 fails for habituation and not for item noise.' That holds only at per-cue rates of about 0.9 or more. The contract itself predicts a per-cue rate of 0.77 at M = 1,000 (line 409).

With power.py's own beta model (ICC 0.09, 50 items, 5 seeds) and zero habituation at 0.77:
- mean eligible items 24.8, and P(>= 25 eligible) on one seed-load 0.54;
- the noise-only habituated fraction is 0.094, against the 10 % bar;
- P(O4 passes over both loads, with 0.95 at M = 500 and 0.77 at M = 1,000) = 0.003;
- zero-effect O5 recovery passes with P = 0.0025.

Line 249 makes not-estimable criteria fail, and lines 308-309 then label them HABITUATION FAIL and RECOVERY FAIL. The vector records only pass or fail. So a system with no habituation and full recovery, but per-cue reliability of 0.77, is labelled as habituating and not recovering. That is exactly what M3 objected to ('HABITUATION FAIL can be reached with zero habituation'), and what F11 (row 91) objected to. The predicted labels (lines 413-414) already expect this case.
- fix: Keep the gate failing, but make the record honest.
- Record O4, O5 recovery and O5 collateral as pass, fail, or fail (not estimable).
- Label HABITUATION FAIL only when at least 25 items are eligible and more than 10 % habituated; otherwise label HABITUATION NOT ESTIMABLE.
- Label RECOVERY FAIL only when power.p_paired_majority gives a zero-effect pass probability of at least 0.8 at the control copy's observed per-cue rate; otherwise label RECOVERY NOT ESTIMABLE. Alternatively, make O5 a paired McNemar or sign test on discordant items with a predeclared tolerance.
- Delete or qualify 'So O4 fails for habituation and not for item noise'.

### F3 [minor] The O5 prediction and the expected labels contradict the Power section

- where: lines 350-351 against 410 and 413-414
- evidence: Power section (lines 350-351): 'at the online rates expected at M = 1,000 it cannot pass, whatever recovery does.' Predictions (line 410): 'O5 | likely holds at M = 500; uncertain at M = 1,000'. The expected labels (lines 413-414) name only ONLINE INDEX FAIL and HABITUATION FAIL.

Computed: zero-effect O5 recovery at a per-cue rate of 0.77 on M = 1,000 alone passes with P of about 0.003.
- fix: Predict that O5 fails at M = 1,000 from sampling, not from recovery. Add RECOVERY FAIL (or NOT ESTIMABLE, per F2) to the expected labels, and keep P(PASS) < 0.05.

### F4 [minor] Rolling slots in steps 162-181 have no legal target for the uniform and oldest-probed kinds; the redraw rule does not cover the stream-14 rolling draw

- where: lines 146-147, 152-161 (rolling from step 162; uniform 'unreserved, ages >= 21'; oldest-probed 'otherwise uniform'), 180-182 (redraw with stream (seed, 15, attempt)), 3 ('schedule-and-power check')
- evidence: Unreserved items start at item 161, so no unreserved item reaches age 21 before step 182.
- In steps 162-181, 30 % of rolling slots (about 6) have no legal target.
- A draw with no such slot has P = 0.7^20 = 8e-4.
- The redraw rule names stream 15, but rolling slots use stream 14, so it is unclear whether redraws apply here.
- If they do apply, about 1,250 attempts per seed produce a schedule silently conditioned on having no uniform slots in this window.

This repeats, on a smaller scale, the infeasibility that M1/B1 found in the old M = 250 block.
- fix: State that a uniform or oldest-probed rolling slot with no legal target is drawn as novel (or that targeted rolling kinds start at step 182). Give the stream-14 draw its own deterministic redraw rule. Cover steps 162-181 in the schedule builder's unit test before freezing.

### F5 [minor] The quoted pass probability of the draft's unpaired O4 rule is wrong

- where: lines 354-355
- evidence: The contract says 'The draft's unpaired rule passed with only 0.62 at 0.93 with no habituation (M3).'
- M3, confirmed by its verifier, gives 0.40 at 0.93 for one load over 5 seeds.
- Recomputed with power.py's beta model: 0.41 at one load and 0.17 at both loads.
- M3's 0.60 is the share of scored items reaching 8 of 10 at mu = 0.75, not a pass probability.
- fix: Replace it with 'passed with about 0.4 at one load (0.17 at both loads) at 0.93'.

### F6 [minor] The McNemar test for O4, recorded in ledger M3, is missing

- where: ledger M3 action ('McNemar reported'); contract lines 207-217, 386
- evidence: The contract's only McNemar test is in the twin B row (line 379). The habituation detail row (line 386) lists per-repetition recall, vbar, the habituated fraction and recovery among habituated items. It has no paired test of the repeated copy's late window against the control's.
- fix: Add to the habituation detail row: per load, McNemar on 'late window >= 8 of 10' for the repeated copy against the control copy, and the distribution of the paired difference L_rep - L_ctl.

### F7 [minor] Power for the full five-seed acceptance rule is not stated; only O1-O3 is

- where: lines 337-348; DECISIONS.md ruling 2 ('power checks that account for dependent measurements and the full five-seed acceptance rule'); FID-6
- evidence: The contract states P = 0.83 for O1-O3 only and gives O4 and O5 at hypothetical per-cue rates. PASS also needs O4 and O5 at both loads.

Take settled per-cue 'both' rates (memory and content) of about 0.965 at M = 500 and 0.92-0.944 at M = 1,000. Then O4 x O5 is 0.88-0.985, and the zero-online-cost P(PASS) is 0.73-0.82. At the low end that is below the 0.8 that the counts were sized for.
- fix: Name the zero-cost 'both' reference rate and its source, state the combined O1-O5 zero-online-cost P(PASS), and say whether it reaches 0.8.

### F8 [minor] Age-0 blank targets, the only place a leak is physically possible, average one per block and are absent from 38 % of blocks

- where: lines 172 and 277-278 (blank 'target ages 0-20'); ledger M4 ('age-0 targets'), m2, FID-7; methodology M4 ('a predeclared share of blank slots target the age-0 item')
- evidence: Blank targets are drawn uniformly over ages 0-20.
- Expected age-0 targets per block: 20/21 = 0.95.
- P(a block has no age-0 target) = (20/21)^20 = 0.38.
- fix: Predeclare a fixed share, for example 5 of each block's 20 blank slots aimed at the age-0 item (one in every other sub-block), and report age 0 separately.

### F9 [minor] The probed against never-probed retention contrast 'at M = 1,000' cannot be measured as defined (ledger M14)

- where: lines 158, 166-173, 384; ledger M14
- evidence: Oldest-probed slots exist only in rolling steps (501-760, and after 1,000). Gated blocks have no such kind.
- Cohort 500 is therefore read at loads 501-760 (or above 1,000).
- Cohort 1,000 is read at loads 761-1,000.
- Online recall depends strongly on load: 0.89-0.96 at M = 500 against 0.70-0.85 at M = 1,000 (line 406).
- So the 'near zero' prediction would be tested against a load difference, not probe history.
- Chance uniform draws of cohort-500 items in the M = 1,000 block come to about 4.
- fix: Predeclare a matched measurement, for example 15 of the M = 1,000 block's 50 uniform cues drawn from cohort-500 items (spread across sub-blocks), compared with the cohort-1,000 cues in the same block.

### F10 [minor] A habituation item's collateral item can also be one of its control copy's 89 cued items, which unpairs the collateral comparison

- where: lines 198 and 202-205
- evidence: The control copy cues '89 other unreserved stored items (distinct, stream 16, outside the 50)'. The collateral is 'the unreserved stored item (outside the 50) whose assembly A overlaps ... most'. Nothing excludes the collateral from the 89.
- The chance is about 89/290, or 0.3, per item at M = 500, and about 0.1 at M = 1,000.
- When it happens, the collateral item has had one prior cue on the control copy and none on the repeated copy.

The contract also does not say that the control copy's cues of the item use the repeated copy's fixed mask, or which masks the 89 cues use.
- fix: Exclude each item's collateral from that item's 89 control cues. State that the control uses the same fixed mask for the item, and that the 89 masks come from stream 16.

### F11 [minor] The scope of the cohort reservation and the probe-log audit conflicts with settled twin A's P2-E3 test

- where: lines 143-145 (the rule covers 'habituation duty and collateral duty', which happen only on copies), 220-224 (twin A runs P2-E3's 600-cue test), 272-275 (validity 7); plant2/experiments/p2_e1_btsp.py line 136 (test set = items 0-99 plus 100 random)
- evidence: The reservation rule reaches copy-only duties. Yet at M = 500, twin A runs P2-E3's test, whose cued set includes items 1-100. That is about 50 cohort-1,000 items, before their block at steps 761-1,000. If validity 7's 'realised probe log' covers copies, it flags INVALID. If it does not, the copy clauses of the rule are inconsistent.
- fix: State that the reservation and the audit apply to the main line, since copies cannot carry history back and validity 6 checks that. Or give twin A at M = 500 a test set that excludes cohort-1,000 items, and say so.

### F12 [minor] The P2-E3 addendum's commitment ('From P2-E4 on: at least one gated control could pass if the claim were false') is not reconciled

- where: docs/plant2/P2-E3-content-completion.md lines 568-570; contract lines 289-291 and 379; ledger M4 and FID-7
- evidence: The contract's only gated control for the recall claim is validity 9, which 'cannot fail except through a leak or bug' (line 289), and twin B is reported only. Ledger FID-7 corrects ledger row 87, but neither the contract nor P2-E3 says whether addendum item 8 is waived or met another way.
- fix: Add a sentence naming the gated element that meets item 8 (for example, the O4/O5 control copies, which can come out either way), or state that item 8 is superseded by ledger M4/FID-7 and why.

### F13 [minor] O4/O5 run with learning paused, but the hypothesis and limitations do not say so; ledger C3's interpretation and the owner's right to overrule are not recorded

- where: lines 54-57 (hypothesis), 59-71 (labelled limitations), 188-195 (sham encodings); ledger C3; DECISIONS.md lines 336-339
- evidence: The hypothesis places the habituation clause inside 'while it learns one item every 500 ms with no settle'. The owner described the experiment as testing 'recall while the system keeps learning new items ... covers ... repeated-cue habituation'.

The copies run sham encodings with 'no plateaus, no BTSP update and no feedback write' (line 193). Learning is paused; only the input duty is held. The labelled limitations do not list this.

Ledger C3 records that O4 and O5 are a reading of ruling 2 that 'the owner may overrule'. The contract does not say so.
- fix: Add to the labelled limitations: 'O4 and O5 are measured on copies with learning paused; sham encodings hold the input duty and the load at M.' Record the C3 reading, and the owner's right to overrule it, next to O4 and O5.

### F14 [minor] Sham encodings do not reproduce the main line's `rec` state at slot onset, so 'hold ... the operating point' is overstated

- where: lines 188-190; redteam-implementation_mechanism.md m3
- evidence: m3 measured main-line `rec` at -89.8 to -109.8 mV at the end of the continuation and -72.0 to -73.9 mV at slot onset. That inhibition comes from the stored item's assembly firing during the continuation.

A sham continuation shows an unstored pattern. Novel cues ignite about 0-1 memory cells (P2-E3 D3, P2-E2 C3), so `rec` in the copies starts near -70 mV.

m3 names this hyperpolarisation as a candidate intrusion suppressor. So the copies' content and 'both' rates, and the bootstrap of O4/O5 from exploration copies, may differ from the main line's rates.
- fix: Narrow the claim to 'the memory layer's operating point'. Report `rec` v at slot onset and global vbar on both copies, next to the main line's. Report repetition-1 'both' rates beside the main line's block rates at the same load.

### F15 [nit] Leftover draft text and mislabelled numbers

- where: lines 8, 360, 408
- evidence: - Line 360: 'For O0-O3 it uses a binomial'. O0 is no longer a criterion.
- Line 8: 'the two-critic-plus red-team'.
- Line 408: O3 prediction 'ages 781+: about 0.70-0.80'. Under the revision, the cohort-1,000 items (from items 1-160) are cued over steps 761-1,000 at ages 601-999. The 0.70-0.80 figure is implementation M2's proxy for ages >= 281.
- fix: Change line 360 to 'For O1-O3'. Fix the wording on line 8. Change line 408 to 'cohort ages 601-999; proxy for ages >= 281: 0.70-0.80'.

### F16 [nit] Small unspecified points

- where: lines 160 and 173 (full cues), 245 (C7), 293-296, 416-431 (Decision), 442 (record order)
- evidence: - Full-cue targets (pool and ages) are not specified for rolling slots or blocks.
- Ledger C7 asked what an O3 FAIL means for Stage 1's 60 s clause; the contract does not say.
- Lines 293-296 say a reported-arm validity failure 'invalidates only that arm', then that a replay mismatch is 'not INVALID'. It is unclear whether twin A stays valid.
- The Decision section has no INVALID branch.
- Twins A and B at M = 500 are taken at step 500, but line 442 says the gated record is written before any reported arm runs.
- fix: Specify full-cue targets (unreserved stored items, distinct within a block). Add one line on what an O3 FAIL means for the 60 s clause. Say that a replay mismatch leaves twin A valid. Add an INVALID branch to the Decision section (record it; any re-run needs the owner's ruling). Say that the M = 500 twin snapshots are kept and run after the gated record.

### F17 [nit] Two reference rates do not reproduce from the recorded gated seeds

- where: lines 323-333; plant2/power.py P2E4_RATES (hard-coded)
- evidence: From bench/results/plant2.jsonl, gated seeds 6-15:
- C2 at M = 1,000 is 0.986 (0.983 over all 15 P2-E2/E3 seeds), not 0.989.
- Oldest-item recall at M = 500 is 0.969, not 0.972.

The other entries match. The effect on P is negligible.
- fix: Correct the two values, or name the seed set used. Better, have p2e4_reference() compute the rates from the records.

## Computed (exploratory; not results)

All scripts and outputs are in /root/.cache/brain-sim/review/p2e4-verify/coverage/. Nothing was simulated, no network seeds were used, and Monte Carlo generator seeds were 1, 2, 5 and 42.

- ref.py (ref.out) re-ran plant2.power.p2e4_reference():
  - O1-O3 over all seeds and loads: 0.830;
  - M = 1,000: O1 0.914 and O3 0.912;
  - the draft's sizes give 0.646;
  - the O4/O5 table matches the contract (0.998/0.994/0.994/0.988; 0.987/0.952/0.950/0.905; 0.865/0.683/0.686/0.468).
- hab.py (hab.out), zero habituation:
  - at per-cue 0.77: mean eligible 24.8, P(>= 25 eligible) per seed-load 0.54, noise-only habituated fraction 0.094;
  - at 0.93 with late rate x 0.85: habituated fraction 0.22, which matches the contract;
  - O4 and O5 over 5 seeds and both loads: 0.0 at 0.77; 0.005 and 0.0003 at 0.80;
  - with M = 500 at 0.95 and M = 1,000 at 0.77: O4 0.003, O5 recovery 0.0025.
- fullrule.py (fullrule.out): full-rule zero-cost P(PASS) of 0.82, 0.76 and 0.73 for 'both' rates (M = 500 / M = 1,000) of 0.968/0.944, 0.965/0.925 and 0.964/0.920.
- unpaired.py: the draft's unpaired O4 rule at 0.93 passes with P = 0.41 at one load and 0.17 at both (at 0.95: 0.84 and 0.70). This contradicts the contract's '0.62'.
- rates3.py: recorded settled rates for gated seeds 6-15:
  - M = 500: C1 0.969, C2 1.000, C3 1.000, oldest recall 0.969, joint 0.994, D3 1.000, D4 0.998;
  - M = 1,000: C1 0.9435, C2 0.986, C3 0.9955, oldest recall 0.953, joint 0.975, D3 0.998, D4 0.972.
- misc.out:
  - P(no age-0 blank target in a block) = 0.377;
  - P(no uniform or oldest-probed rolling draw in steps 162-181) = 8.0e-4;
  - P(the collateral item is among the control copy's 89 cues) is about 0.31 at M = 500 and 0.10 at M = 1,000.

Ledger coverage: all 42 rows of 'P2-E4 contract red-team' were checked against the contract.
