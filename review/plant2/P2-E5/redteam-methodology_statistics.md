# P2-E5 draft red-team: methodology and statistics lens

Fresh reviewer given only the files (draft at commit e736e81); each finding then checked by a separate refuter. Run 2026-10-10 to 2026-10-11. Recorded verbatim, before synthesis.

## Verdict

The draft cannot be frozen as written. Two blockers, three majors, and a few minor points and nits.

The exploration that supports the draft stops at M = 500. I extended it to M = 1,000 using the frozen P2-E3 code, P2-E3's own test set, and seeds 44 and 45 only. These numbers are exploratory, not results. At the gated load M = 1,000, the memory index itself fails: C2 is 0.465-0.48, and 79-83 % of the spurious cells belong to sibling assemblies. The plateau-set store, which the draft treats as the clean baseline, also fails (joint 0.155-0.18). So at M = 1,000 no change to the feedback write, including the error-correcting write the owner approved as a research direction, can pass S1, and even an oracle write cannot pass S2. The draft's account of the cause, its predictions ("C2 probably holds"), its reading of the comparison arms and its next step all rest on M = 500 alone.

The second blocker is the new validity bar (signed drift <= 0.1 mV). It is exceeded at M = 1,000 by P2-E3 gated seed 14 (-0.110 mV) and by 3 of 6 exploratory M = 1,000 runs. The likeliest recorded outcome as written is therefore INVALID, not the predicted FAIL.

The draft has no power section. Even an idealised system that behaves on correlated items as P2-E3 does on independent items passes S1-S4 with probability 0.84-0.92 under the five-seed, two-load rule. A system with a perfectly item-specific feedback write (the plateau-set oracle) on the frozen index passes with probability 0.08-0.15 at M = 500 alone, and 0 at M = 1,000. The gate therefore cannot recognise a successful correction to the write.

Family construction: F = 10 with s = 60 does give the stated sibling overlap (about 16.9 % expected). But family size, per-line load and total load move with it, and each has a large effect:
- The main-arm joint at M = 500 is 0.405 with 25 exemplars per family, against 0.105-0.145 with 50.
- With the same per-line loads but no sibling correlation (the pooled control), the system passes at M = 500 (0.985) and fails at M = 1,000 (C2 0.775, joint 0.10). So at M = 1,000 the uneven line frequencies alone break the index.
- The low-overlap arm (s = 80) also fails at M = 1,000 (joint 0.705), against the predicted 0.99.

Running a gate that is predicted to fail is worth it: it is cheap (about 2-3 CPU-hours over five seeds), the owner ordered it, and it turns the reviewer-script evidence into a predeclared record on fresh seeds. But its pass/fail verdict is settled in advance: exploration predicts S2 fails at both loads, and S1 and S4 at M = 1,000 (S4 at both loads). Its whole value is in attribution and in serving as a baseline. The draft is not built for either: there is no verdict vector or labels, no rule for reading the same-raster store swap, no positive control, no attribution arms, and nothing is persisted that would let a later feedback rule be replayed on the identical memory activity. The memory layer does not depend on the feedback store, so such a replay would be exact.

Scripts and outputs: /root/.cache/brain-sim/review/p2e5-redteam/methodology/ (fam_e5.py, fam_e5_mode.py, fam_e5_v2.py, power_e5.py, *.jsonl, *.log).

## Findings

### B1 [blocker] At M = 1,000 the memory index fails and the plateau-set 'baseline' fails too; the draft's cause, predictions, arm readings and next step rest on M = 500 only

- where: Draft: 'Why this test' (the cause), 'Comparison arms' (plateau-set store 'isolates the responder write'), 'Predictions' (S1: 'C2 probably holds'; no plateau-set prediction at M = 1,000), 'If it fails'. DECISIONS ruling 4 ('against the plateau-set baseline').
- evidence: Exploratory runs on seeds 44 and 45: fam_e5.py (frozen E3, J_fb 2.8, g 0.3, P2-E3's run_phase and test set), s = 60, F = 10.
- M = 500: C1 0.97 / 0.945; C2 0.92 / 0.915; joint 0.145 / 0.105; plateau-set store 0.93 / 0.94. This agrees with the draft.
- M = 1,000: C1 0.935 / 0.915; C2 0.48 / 0.465; C4 spurious 0.47 / 0.40. Main-store joint 0.000 / 0.000, with median intrusions of 1,540 / 1,741 lines and a novel-cue maximum of 1,041 lines on seed 44. Plateau-set store joint 0.18 / 0.155, D4 0.16 / 0.09.
- In the v2 runs (s = 80 at M = 1,000, and F = 40), 79-83 % of the spurious memory cells under a half cue belong to sibling assemblies, so the contamination is already in the index.
- The responder write also inflates further: |R| is 86-88 against |A| of about 20, and the continuation offset is about 12 mV.
- C2 sits upstream of the feedback path. No feedback-write mechanism, including the owner-approved error-correcting write, can repair S1 at M = 1,000, and even the oracle plateau-set write fails S2 there.
- recommendation: Before freezing:
1. Report this to the owner. It bears on ruling 4's order (write first, judged against the plateau-set baseline) and on whether 'ultimately M = 1,000' should be gated now, at F = 10, at the edge of the independent-item capacity.
2. Rewrite the cause and the predictions per load. Give each criterion and arm a stated probability.
3. Predeclare an attribution reading from the same-raster store swap at each load: 'write-attributable' where the plateau-set store passes S2 and S4 but main fails; 'index-limited' where the plateau-set store also fails or S1's C2 fails.
4. Add the M = 1,000 plateau-set prediction (about 0.15-0.2) and an s = 80 prediction at M = 1,000 (see M2).
- independent verifier: **confirmed** (severity should be blocker): The claim survives and is stronger than stated. (1) The logs are real. Re-running the reviewer's fam_e5.py on seed 44 at M = 500 reproduced every number bit for bit. My own script (verify-methodology/sibshare.py, EXPLORATORY), learning straight to M = 1,000 in the gated condition, also matched exactly: C2 0.48, C4 spurious 0.47, main joint 0.000 (median 1,540 intrusions), plateau-set joint 0.18, D4 0.16, drift -0.0757. (2) The reviewer's 79-83 % sibling share came from other arms (s = 80; F = 40) with no chance baseline. I measured the gated condition itself: 98.7 % of spurious memory cells (3,356 over 200 half cues) belong to sibling assemblies, against a chance share of 39 %. So the index contamination holds for the gated condition. (3) Architecture backs the upstream argument. E3's network is Net([inp],[mem],[proj]), and the feedback store is written from R x E without rec ever being simulated. No feedback-write correction can therefore change C1-C3. (4) The draft's S1 prediction is weak even at M = 500: C2 0.915-0.92 gives S1 a five-seed pass probability of only 0.31-0.44. Caveat: the draft itself says its predictions come only from M = 500 and will be extended. The blocking part is what the extension shows. It contradicts 'C2 probably holds', the claim that the plateau-set arm 'isolates the responder write', and ruling 4's write-against-plateau-set path at M = 1,000. That needs the owner before seeds 21-25 are spent. Basis: two consistent exploratory seeds.

### B2 [blocker] The new convergence validity bar (|signed drift| <= 0.1 mV) is exceeded at M = 1,000 by recorded and exploratory runs; INVALID becomes the likeliest outcome

- where: Draft, Validity: 'convergence is gated on signed drift ... <= 0.1 mV over the last 10 s of the settle'
- evidence: Signed drift at M = 1,000 in bench/results/plant2.jsonl:
- P2-E3 gated seeds 11-15: -0.024, -0.072, -0.070, -0.110 (seed 14), -0.072.
- P2-E3 calibration seed 0: -0.089.
This exploration at M = 1,000:
- s = 60, F = 10: -0.076 (seed 44) and -0.117 (seed 45);
- pooled control: -0.107;
- F = 40: -0.103;
- F = 20: -0.062;
- s = 80: -0.054.
So 4 of the 12 values with independent and correlated items are above 0.1 mV: about 0.3 per seed, and P(at least one of five gated seeds INVALID at M = 1,000) is about 0.8.

The drift is systematic (always negative, growing with load), not noise around zero. Under P2-E3's existing rule (mean |dvbar| <= 0.2 mV), every one of these values passes (largest 0.122). The draft also says 'everything is P2-E3 exactly', yet this rule is changed without any power check.
- recommendation: Use P2-E3's convergence rule unchanged, and report signed drift beside it. If a signed rule is wanted, set its bar from a computed false-alarm rate (for example <= 5 % over 5 seeds x 2 loads, using the 12 values above) or lengthen the settle. Put P(INVALID) in the power section. A predicted-FAIL diagnostic that ends up INVALID burns five fresh seeds and needs an owner ruling to re-run.
- independent verifier: **confirmed** (severity should be blocker): Verified in bench/results/plant2.jsonl. Signed drift at M = 1,000 is -0.024, -0.072, -0.070, -0.110 (seed 14) and -0.072 on P2-E3's gated seeds, and -0.089 on calibration seed 0. The exploratory jsonl files give -0.076, -0.117, -0.107, -0.103, -0.062 and -0.054. Every value is negative and larger at M = 1,000 than at M = 500. The largest |dvbar| is 0.122, under P2-E3's 0.2 bar. Decisive precedent: P2-E3's contract red-team (review/plant2/P2-E3/contract-redteam.md, lines 9-10 and 36-37) flagged this exact bar, '|signed mean dvbar| <= 0.1 mV', as a must-fix. P2-E3 then kept P2-E2's rule (P2-E3 doc, lines 161-162). The draft reintroduces the rejected bar while saying 'Everything is P2-E3 exactly'. Under the draft's rule, P2-E3's own gated seed 14 would have been INVALID. The reviewer's 4/12 pooling mixes conditions and is crude. Even so, P2-E3's independent-item rate alone (1 of 6) gives P(at least one INVALID seed out of 5) of about 0.6, and the gated structured condition is worse (1 of 2 values over the bar). The recommendation is right.

### M1 [major] No power section; the rule has limited power for a truly item-specific system and none for the approved correction path

- where: Draft: Kill test, and the absence of a Power section (compare P2-E4's 'Power (computed before freezing)')
- evidence: Computed with plant2.power.p_rule (power_e5.py): exact binomials, n = 200 (C1-C3, joint, D3) and n = 100 (D4), five seeds, both loads, logit seed SD 0.18.
- **Idealised system** that is as item-specific on correlated items as P2-E3 is on independent items (P2E4_RATES): P(PASS S1-S4) = 0.92 (pooled memory rates) or 0.84 (P2-E3-only rates). It is 0.86 / 0.79 if P2-E2's C4 is added. With SD 0, it is 0.98 / 0.94. S1's C1 at M = 1,000 drives it (0.84-0.92).
- **Structured items:** exploratory C1 at M = 1,000 is 0.915-0.935. At 0.925, P(C1 holds on all five seeds) = 0.52 by itself.
- **Oracle item-specific write** (plateau-set store on the frozen index, exploratory rates C1 0.9575, C2 0.9175, joint 0.935, D4 0.92 at M = 500): P(PASS) = 0.08-0.15 at M = 500 alone (S1 0.31-0.44, S4 0.32-0.38, S2 0.78-0.90), and 0.000 at M = 1,000.
- recommendation: Add a power section before freezing, in P2-E4's form. Give per-criterion and full-rule pass probabilities for three cases:
- independent-item-like rates;
- oracle plateau-set rates at both loads;
- the main arm.

Also give P(INVALID) (see B2).

For the baseline role, predeclare graded paired statistics: per-seed joint, D1, D2 and intrusion distributions for the main and plateau-set stores on the same raster. A later correction can then be judged on improvement over the baseline, not only on an absolute bar that even an ideal write cannot reach.
- independent verifier: **confirmed** (severity should be major): The draft has no power section, although P2-E4's frozen contract makes one the expected discipline. I reproduced the numbers with plant2.power (verify-methodology/power_check.py):
- idealised rates: P(PASS) 0.919 / 0.839 at seed SD 0.18, and 0.975 / 0.935 at SD 0;
- with C4 added: 0.856 / 0.789;
- C1 at 0.925 holding on all five seeds: 0.52 (0.68 at SD 0);
- oracle plateau-set rates at M = 500: 0.077-0.15 (S1 0.31-0.44, S2 0.78-0.90, S4 0.32-0.38), and 0 at M = 1,000.

One overstatement: 'limited power for a truly item-specific system' is not a defect in itself. 0.79-0.92 is at or above the 0.77-0.85 that P2-E4 accepted and stated. The real gaps are:
- the missing section;
- the missing P(INVALID) (see B2);
- the fact that even an oracle write cannot meet the absolute bar, which overlaps B1.

The graded paired baseline statistics it recommends are sound.

### M2 [major] Overlap is confounded with family size, per-line load and total load; F = 10 is one unexplained point on a steep surface, and the overlap arms inherit the confound

- where: Draft: Items (F = 10, item k in family k mod F, 'Family size' bullet); Overlap arms (s = 80, 40, 100); Predictions (s = 80 'about 0.99')
- evidence: All exploratory, seeds 44 and 45 (plus the earlier seeds 97 and 99 for M = 250). Values are main-store joint / plateau-set joint / C2, by exemplars per family.

| exemplars per family | runs |
|---|---|
| 25 | M = 250, F = 10: main 0.62-0.63 · M = 500, F = 20: 0.405 / 0.995 / 0.955 · M = 1,000, F = 40: 0.045 / 0.85 / 0.74 |
| 50 | M = 500, F = 10: 0.105-0.145 / 0.93-0.94 / 0.915-0.92 · M = 1,000, F = 20: 0.03 / 0.52 / 0.66 |
| 100 | M = 1,000, F = 10: 0.000 / 0.155-0.18 / 0.465-0.48 |

- **Per-line load** (synthetic count): at F = 10, s = 60, the roughly 1,000 prototype lines (25 % of lines) carry 29 / 58 items at M = 500 / 1,000, against 12.5 / 25 for independent items.
- **Line-frequency control** (pooled; seed 45): the prototype-share lines are drawn from the union of all prototypes, so per-line loads match but pairwise overlap is about 3.7 %. At M = 500: joint 0.985, C2 0.99, so the M = 500 collapse is caused by sibling correlation. At M = 1,000: joint 0.10, plateau-set 0.49, C2 0.775, so the line skew alone breaks the index and the content.
- **Overlap arms at F = 10** also change the skew: prototype-line load at M = 1,000 is 41 at s = 80, 58 at s = 60 and 76 at s = 40.
- **The s = 80 arm** (about 5.6 % sibling overlap) at M = 1,000: joint 0.705, D4 0.64, plateau-set 0.92, C2 0.96. The draft predicts about 0.99 from M = 500 only.
- recommendation: Declare F with a reason, as part of the operationalisation of 'about 16 % sibling overlap'. State that in this design the step from M = 500 to 1,000 also doubles family size (50 to 100) and prototype-line load.

Add predeclared attribution arms on the same seeds and loads:
- (a) a line-frequency-matched control (prototype-share lines drawn from the pooled prototype set);
- (b) a constant-family-size arm (F = M/50), or a tiled-prototype arm (F = 40, roughly uniform line load).

Give predictions for every arm at M = 1,000. Interpret the overlap dose-response only alongside (a).
- independent verifier: **confirmed** (severity should be major): My synthetic check (verify-methodology/lineload.py; numpy only) reproduces the loads:
- prototype-line load is 29.2 / 58.2 at M = 500 / 1,000, against 12.5 / 25 for independent items;
- the non-prototype load is 7.7 / 15.4;
- the overlap arms at M = 1,000 give s = 80: 40.4, s = 40: 77.2, and F = 20: 40.1;
- the pooled control matches the per-line load (29.5 / 59.5) at 3.7 % pairwise overlap, and its generator is logically right.

One small slip: the prototype lines number about 900 (22 %), not about 1,000 (25 %). The substance holds. The draft gives no reason for F = 10, and F is a consequential parameter: at the same 16 % overlap and M = 500, main joint is 0.105-0.145 at F = 10, 0.405 at F = 20 and 0.765 at F = 40, and C2 at M = 1,000 is 0.47 / 0.66 / 0.74. S2 fails at every F in exploration. What depends on F is S1 at M = 1,000 and the attribution, which is the experiment's stated purpose. The s = 80 arm at M = 1,000 gave 0.705, against the draft's 'about 0.99'. The pooled and s = 80 results rest on one seed each.

### M3 [major] The record is not built to be the baseline a correction must beat: no verdict vector or labels, no positive control, no persistence for an exact same-raster replay

- where: Draft: Verdicts (PASS / FAIL / INVALID); Comparison arms (s = 100 'diagnostic'); 'If it fails'; no persistence clause
- evidence: - **Verdicts.** They are only PASS, FAIL or INVALID, 'with the failing criteria named'. P2-E4's red-team (FID-3, M9) led to a verdict vector with non-hiding labels that separate index from content failure. Exploration here predicts exactly that split: S1 fails at M = 1,000 through C2, and S2 fails at both loads.
- **Positive control.** The s = 100 arm on the same seeds is an exact P2-E3 replication, and the forward store matches P2-E3 learning for that seed. It is the natural positive control that can come out either way: P2-E3's C1 at M = 1,000 was 0.925-0.955, and the idealised P(PASS) is 0.84-0.92. Yet the draft gives it no reading.
- **Exact replay.** The feedback store never influences the memory layer: rec has no outputs, and P2-E3 replays rec from the memory raster bit-exactly. Any later feedback rule, including an error-correcting write that needs rec during learning, could therefore be replayed exactly on P2-E5's own learning and test memory activity, if the encoding and continuation memory spikes, E(x), A(x) and the test rasters were kept.
- **Per-cue outcomes.** These are not required to be persisted (P2-E4 implementation finding F7).
- recommendation: 1. Use a verdict vector: criterion part x load x seed.
2. Use labels: STRUCTURED INDEX FAIL (S1, with C2/C4 spurious named); STRUCTURED CONTENT FAIL, qualified 'write-attributable' or 'index-limited' by the predeclared plateau-set swap (B1); NOT ATTRIBUTABLE on any seed and load where the s = 100 arm fails S1-S4.
3. Persist per-cue outcomes and the learning and test memory rasters, so the correction contract can run a paired same-raster replay on these seeds as a reported arm, beside its own fresh gated seeds.
4. State the exact quantities the correction must improve: the per-seed joint, and the prototype and sibling intrusion rates for the main and plateau-set stores.
- independent verifier: **confirmed** (severity should be major): The cited precedents exist: P2-E4 owner-intent FID-3 and methodology M9 (verdict labels separating index from content), and P2-E4 impl-bugs F7 (per-cue outcomes not persisted). The draft's verdicts are only PASS / FAIL / INVALID, yet exploration predicts exactly the index/content split (S1 failing at M = 1,000 through C2, and S2 failing at both loads). The s = 100 arm uses P2-E3's generator and protocol, so it is a fresh-seed replication of P2-E3. Its recorded C1 at M = 1,000 was 0.925-0.955, so the arm could come out either way, yet the draft gives it no reading. The exact-replay claim is correct by the code: rec is absent from the learning network, so memory activity during learning and test does not depend on any feedback store. A feedback-only correction could therefore be replayed exactly, if rasters, E(x) and A(x) were kept. The point is strengthened by P2-E3 addendum item 8: from P2-E4 on, at least one gated control must be able to pass if the claim were false. The draft has none; its shuffled arm is a leak check and every other arm is reported only. Its stated purpose, to fix the target a correction must beat, is not served without persistence and named target quantities.

### m1 [minor] S3 (random novel cues) cannot detect correlated-item contamination; the informative unlearned cue (a never-stored family member) has no predeclared reading

- where: Draft: S3; Reported cues (100 new-exemplar half cues)
- evidence: In the reviewer's earlier families.py outputs (s = 20 and 40, M = 500), random novel cues lit 0 lines while stored cues lit 2,500-3,200. Here at M = 1,000 with F = 10, D3 is 0.985-0.99 while stored cues flood rec. S3 is effectively a leak check.

For correlated items, the specificity question is false recall: does a new exemplar regenerate sibling-specific lines? That differs from generalisation (prototype lines), which the owner assigned to Stage 3. At M = 500 the new-exemplar cue lit 0 lines on seeds 97 and 99, so it can come out either way at other loads.
- recommendation: Keep S3, per the owner's 'existing criteria', but label it a leak check. Predeclare a reported reading for the new-exemplar cues, split into prototype lines (generalisation; Stage 3; not gated) and non-prototype lines of siblings (false recall; contamination).
- independent verifier: **partly** (severity should be minor): The evidence checks out:
- families.py at s = 20 / 40, M = 500: random cues lit 0 lines, while stored cues lit a median of 2,837-2,942;
- at s = 60, M = 500, new exemplars lit 0 lines on seeds 97 and 99;
- at M = 1,000, D3 is 0.985-0.99 alongside 1,540-1,741 intrusions.

But S3 is P2-E3's D3, a leak check by design. Contamination of stored cues is caught by S2's D2, so 'S3 cannot detect contamination' is not a defect of S3. The draft also already reports the new-exemplar cues ('what is regenerated, and how many memory cells respond'). What holds is narrower: there is no predeclared split of those cues into prototype lines (generalisation, Stage 3) and sibling-specific lines (false recall), and no reading for either. Worth adding.

### m2 [minor] The intrusion classes as defined are not specific, and '< 10 intrusions' lets systematic low-level contamination pass

- where: Draft: Per-load diagnostics ('intrusions split into prototype, sibling-specific and other lines'); S2 (D2 < 10)
- evidence: The union of siblings' non-prototype lines covers 1 - exp(-60 x 49 / 3,900), about 53 % of non-prototype lines at M = 500, and about 78 % at M = 1,000 (99 siblings). So 'sibling-specific' absorbs most chance intrusions (for example 1,331 'sibling' against 152 'other' at M = 1,000).

D2 still separates the arms strongly here: main-store prototype intrusions average 36, sibling 49-59, against about 1 for the plateau-set store at M = 500. But 7-8 of 200 plateau-set cues, and 21 of 200 main-store cues at F = 20, M = 500, passed D2 with 3 or more prototype intrusions.
- recommendation: Keep D2 gated as the owner ruled. Report per-line intrusion rates per class, each normalised by the class size:
- the prototype complement;
- lines of siblings whose assemblies responded in the test window;
- unrelated lines.

Also report a contamination ratio against the unrelated-line rate, with a predeclared reading.
- independent verifier: **confirmed** (severity should be minor): The union coverage computes as stated: 1 - exp(-60 x 49 / 3,900) = 0.529, and 0.782 with 99 siblings. The logs show:
- 1,331 'sibling' against 152 'other' intrusions (seed 44, M = 1,000);
- 8 and 7 plateau-set cues passing D2 with 3 or more prototype intrusions;
- 21 such main-store cues at F = 20, M = 500.

The draft never defines 'sibling-specific', so the reviewer's union definition is one plausible reading. That is the point: the classes need definitions and normalisation by class size before freezing. Keeping D2 gated as ruled, and adding normalised per-class rates, is the right fix.

### m3 [minor] S1 drops P2-E2's C4 (memory recall and spurious for the oldest items), which P2-E2's gate and P2-E3's D5 included

- where: Draft: S1 ('P2-E2's C1, C2 and C3')
- evidence: e2.summary's gate_ok requires C1, C2, C3 and C4. P2-E3's D5 gated 'P2-E2's C1-C4'. In exploration at M = 1,000 (F = 10), C4 spurious was 0.40-0.47, so including it changes the record. The owner asked for the existing criteria.
- recommendation: Include C4 in S1, or justify its omission explicitly. Include it in the power computation, where adding C4 lowers the idealised P(PASS) to 0.79-0.86.
- independent verifier: **confirmed** (severity should be minor): P2-E3's D5 gated 'P2-E2's C1-C4' (P2-E3 doc, kill test), and e2.summary's gate_ok requires C4. The draft's S1 lists only C1-C3, and S4 is content-only. Memory recall and spurious responses of the oldest items are therefore not gated at all. P2-E4's O1 also used C1-C3, but its O3 gated oldest-item recall. With C4, my recomputed idealised P(PASS) is 0.856 / 0.789. In practice C4 adds a failing criterion only at M = 1,000 (spurious 0.40-0.47), where C2 already fails. Include it, or justify leaving it out.

### m4 [minor] The within-family label permutation is described as a control that 'could pass', but its joint cannot reach the bar

- where: Draft: Comparison arms, 'Within-family label permutation'
- evidence: x's missing lines overlap pi(x)'s lines by about 16 %, so D1 >= 40/50 is unreachable unless rec floods, and flooding fails D2. Exploration: joint 0.000 at both loads; D1 0.005-0.02 at M = 500 and 0.38-0.45 at M = 1,000, when rec floods.
- recommendation: Reword it. Predeclare its actual statistic: the fraction of x's prototype missing lines against x's item-specific missing lines that are regenerated, under the permuted store compared with the main store. Equal prototype-line rates would mean that part is family-generic.
- independent verifier: **confirmed** (severity should be minor): Siblings share about 16.9 lines (synthetic check), so about 8 of x's 50 missing lines are in pi(x). D1 (40 or more) is therefore unreachable unless rec floods, and flooding with sibling lines fails D2. A purely family-generic regenerator could not pass the joint either. The logs confirm: within-family permuted joint 0.000 everywhere, D1 0.005-0.02 at M = 500 and 0.38-0.45 at M = 1,000. The draft's 'could pass if regeneration were only family-generic' is wrong for the joint. Predeclare the prototype-line against item-specific-line regeneration statistic instead.

### n1 [nit] Paired structure across arms is unstated; guard and run-once rule missing

- where: Draft: Overlap arms; Seeds and cost
- evidence: Plateaus come from P2-E1's plateau stream (n uniforms per item, independent of content), so A(k) is identical across the s arms for every k; only content and coins differ. P2-E4's frozen contract has a --gated guard (frozen commit an ancestor of HEAD, clean tree, tree hash and digest) and 'gated seeds run once'. The draft has neither.
- recommendation: State the pairing and digest the A lists across arms, then use paired per-item comparisons in the overlap dose-response. Add P2-E4's guard and the run-once rule.
- independent verifier: **confirmed** (severity should be nit): Plateaus come from _plat.random(n) < f_q (p2_e3_completion.py, line 57), which uses n uniforms per item whatever the content. Poisson input uses m uniforms per step. So A(k) is identical across the s arms, and the pairing is real but unstated. P2-E4's contract has the --gated guard (ancestor commit, clean tree, tree hash and digest) and 'Gated seeds run once'. The draft has neither. Both are normally added at freezing, hence a nit.

## Exploratory runs (labelled; not results)

- `/root/.cache/brain-sim/review/p2e5-redteam/methodology/fam_e5.py` (seed 44, 45; Frozen E3 (J_fb 2.8, g 0.3); family generator as in the draft (stream (seed, 20)); F = 10, s = 60; M = 500 and 1,000 on deep copies with P2-E3's run_phase and test set; main, plateau-set and within-family-permuted stores; P2-E2's C1-C4): EXPLORATORY.

**M = 500** (seed 44 / 45):
- memory: C1 0.97 / 0.945; C2 0.92 / 0.915; C3 1.0;
- main store: joint 0.145 / 0.105, D4 0.02 / 0.05; median intrusions 73 / 69, with mean prototype 36.6 / 35.8, sibling 58.6 / 49.2, other 4.4 / 4.1;
- plateau-set store: 0.93 / 0.94, D4 0.92 / 0.92;
- permuted store: joint 0;
- learning: |R| 51 against |A| 20; 99.7 % of extra responders are sibling cells.

**M = 1,000:**
- memory: C1 0.935 / 0.915; C2 0.48 / 0.465; C4 spurious 0.47 / 0.40;
- main store: joint 0.000 / 0.000; median intrusions 1,540 / 1,741;
- plateau-set store: 0.18 / 0.155;
- learning: |R| 86-88; continuation offset about 12 mV.

Signed drift: -0.052 / -0.042 at M = 500; -0.076 / -0.117 at M = 1,000.
- `/root/.cache/brain-sim/review/p2e5-redteam/methodology/fam_e5_mode.py` (seed 44; F = 20 (family size 25 / 50), s = 60, M = 500 and 1,000): EXPLORATORY.
- M = 500: C2 0.955; main joint 0.405, D4 0.22; plateau-set 0.995.
- M = 1,000: C2 0.66; main joint 0.03; plateau-set 0.52.
- Signed drift -0.029 / -0.062.
- `/root/.cache/brain-sim/review/p2e5-redteam/methodology/fam_e5_mode.py (mode pooled)` (seed 45; Line-frequency control: the 40 'prototype' lines are drawn from the union of all 10 prototypes. Per-line loads match F = 10, s = 60; pairwise overlap is about 3.7 %. M = 500 and 1,000.): EXPLORATORY.
- M = 500: C2 0.99; main joint 0.985; plateau-set 0.99.
- M = 1,000: C1 0.91; C2 0.775; main joint 0.10; plateau-set 0.49.
- Signed drift -0.042 / -0.107.
- `/root/.cache/brain-sim/review/p2e5-redteam/methodology/fam_e5_v2.py` (seed 44; s = 80 (low-overlap arm), F = 10, M = 500 and 1,000; also measures the sibling share of spurious memory cells): EXPLORATORY.
- M = 500: all criteria 0.985-1.0; main joint 0.99.
- M = 1,000: C2 0.96; main joint 0.705, D4 0.64; plateau-set 0.92; 83 % of spurious cells are sibling cells.
- Signed drift -0.036 / -0.054.
- `/root/.cache/brain-sim/review/p2e5-redteam/methodology/fam_e5_v2.py` (seed 45; s = 60, F = 40 (prototypes tile the line space, so line load is roughly uniform; family size 12 / 25), M = 500 and 1,000): EXPLORATORY.
- M = 500: C2 0.995; main joint 0.765; plateau-set 0.99.
- M = 1,000: C2 0.74 (79 % of spurious cells are sibling cells); main joint 0.045; plateau-set 0.85.
- Signed drift -0.023 / -0.103.
- `/root/.cache/brain-sim/review/p2e5-redteam/methodology/power_e5.py (plant2.power.p_rule)` (seed n/a (analytic); S1-S4 with n = 200 / 100, five seeds, both loads, seed SD 0 and 0.18): - Idealised system at P2-E3 independent-item rates: P(PASS) 0.92 with pooled memory rates or 0.84 with P2-E3-only rates (0.98 / 0.94 with SD 0); 0.86 / 0.79 with C4 added. Limited by C1 at M = 1,000.
- Oracle plateau-set write on the structured index: 0.08-0.15 at M = 500 alone, and 0 at M = 1,000.
- P(C1 holds on all five seeds) at p = 0.925: 0.52.
- `inline synthetic generator (numpy rng 12345; no plant2 simulation)` (seed synthetic; Per-line load and sibling-overlap statistics for F = 10 / 20 / 50, s = 40 / 60 / 80 / 100, M = 500 and 1,000): - F = 10, s = 60: prototype-line load 29 / 58 at M = 500 / 1,000, against 12.5 / 25 for independent items; non-prototype lines 7.7 / 15.4; sibling overlap mean 16.5-16.8 (SD 2.6).
- Prototype-line load at M = 1,000: s = 80: 41; s = 40: 76; F = 20, s = 60: 39.

## Reviewer's predictions

These predictions are for the contract if it is frozen and run as written on seeds 21-25. They come from the exploratory numbers above.
- **S2:** fails at M = 500 on 5/5 seeds (joint about 0.08-0.20) and at M = 1,000 on 5/5 (about 0.00).
- **S4:** fails at both loads.
- **S1:** fails at M = 1,000 on 5/5 seeds through C2 (about 0.4-0.55), with C1 at about 0.90-0.94. At M = 500, C2 is about 0.90-0.93, so S1 fails on at least one seed with probability about 0.6.
- **S3:** passes (D3 >= 0.98).
- **Plateau-set arm:** about 0.92-0.95 at M = 500 and about 0.1-0.25 at M = 1,000.
- **Overlap arms:** s = 80 is about 0.99 at M = 500 and 0.6-0.8 at M = 1,000; s = 40 collapses at both loads; s = 100 passes S1-S4 on all five seeds with probability about 0.85.
- **Validity:** the signed-drift check fails on at least one seed at M = 1,000 with probability about 0.7-0.8. So the most likely recorded label as written is INVALID, not FAIL.
- **After the fixes** (P2-E3's convergence rule kept, plus labels): the label would be STRUCTURED INDEX FAIL plus STRUCTURED CONTENT FAIL, write-attributable at M = 500 and index-limited at M = 1,000.
