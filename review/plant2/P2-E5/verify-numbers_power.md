# P2-E5 contract verification: numbers and power

Fresh checker given only the files (revised contract at commit 68148bb). Run 2026-10-11. Recorded verbatim, before synthesis.

## Verdict

No blocker; two majors to fix before freezing. My own code (not plant2.power, not analysis/p2e5_power.py) reproduces every number in the Power section exactly: idealised 0.856 and 0.789, the limiting parts, the oracle parts (C2 0.07, C4-spurious 0.02, S2 0.66, S4 0.22), P(S1 at M = 500) 0.0013, P(INVALID) 0.0067, and the whole Part B table (to within Monte Carlo error). analysis/p2e5_power.py implements the stated rules: S1 = C1-C4 with C4 as two n = 100 parts, S2/S3 on n = 200, S4 on n = 100, Part B dominance, NO MATERIAL LOSS, SPLIT and the material rule, and the normal P(INVALID) model. It has small deviations: L_c is clipped at 0, there are no NOT ATTRIBUTABLE exclusions, and comparisons are in floating point. Most quoted numbers match the red-team outputs, but several have weaker support than the text implies:
(a) Part D's joint reading is at floor. At M = 1,000 it must read NOT WORSE, yet the table predicts WORSENS. At M = 500 only 1 of 2 exploratory seeds meets the bar.
(b) Every grid number is from seed 44 alone (two learning orders) but is presented as seeds 44-45. Part B's J_own* is not the contract's own 'best joint'.
(c) 'P(S1 at M = 500) = 0.001' rests on one lens's two runs, and its independence assumption is not conservative here.
(d) The s = 100 figure of 0.86 uses pooled P2-E2 + P2-E3 rates; P2-E3's own rates give 0.79.
Part C holds up: my R_3 grid replay (seed 44, M = 1,000) gives 0.165 against 0.160 at the frozen point and 0.610 against 0.600 at the grid best, both within 0.05. Part B's readings are exclusive and exhaustive as written, and NO MATERIAL LOSS cannot co-occur with an X-DOMINANT reading. The losses are not on one scale, though (finding F5).

## Findings

### F1 [major] Part D's reading is at floor: M = 1,000 can only read NOT WORSE (the table predicts WORSENS), and at M = 500 exploration meets WORSENS on 1 of 2 seeds

- where: docs/plant2/P2-E5-structured-items.md lines 341-345 (reading), 470 (Predictions row 'Part D'); 103-104 (scope)
- evidence: Paired same-item exploratory values (fidelity/where_e3_* against where_online_*, M = 500): joint 0.145 to 0.055 on seed 44 (delta -0.090) and 0.105 to 0.065 on seed 45 (delta -0.040). Seed 45 misses the bar (delta <= -0.05). Treating the two deltas as normal (mean -0.065, SD 0.035) gives P(WORSENS) 0.50, MIXED 0.43, NOT WORSE 0.06 (partb_indep.py). At M = 1,000 the P2-E3-protocol store's joint is 0.000 on every run (out_s60, s60_F10, where_e3), so delta = 0 >= -0.05 and NOT WORSE is guaranteed by the floor. The table's 'WORSENS (both near 0) or MIXED' contradicts the contract's own rule. The two conditions also overlap at exactly delta = -0.05 ('<=' and '>='): with joints in steps of 1/200, three seeds at -10/200 make both readings true. Finally, the exploratory online line was the P2-E4 red-team's where.py (no live rec), described there as 'not P2-E4's frozen driver'. The contract calls it 'P2-E4's 250 ms online rhythm'.
- fix: Base Part D on a measure without a floor. Use the paired intrusion statistics already defined in Part F (median intrusions, or the normalised sibling and prototype intrusion rates, online-written store over P2-E3-protocol store on the twin A raster), with a predeclared ratio bar. Alternatively, add NOT ASSESSABLE when the P2-E3-protocol store's joint is below 0.10. Make NOT WORSE strict (delta > -10/200, in cue counts). Correct the predictions to: M = 500 'WORSENS or MIXED (about 0.5 each)'; M = 1,000 'NOT ASSESSABLE' (or 'NOT WORSE by floor, uninformative'). Label the exploratory online numbers as the P2-E4 red-team's line.

### F2 [major] Every grid number (J_ub*, J_own*, best joints, passing points) is from seed 44 alone, shown as seeds 44-45 ranges; J_own* also does not match the contract's 'best joint'; Part B's probabilities depend on both

- where: lines 9-10 ('All exploratory numbers ... seeds 44-45'), 72-73 ('best joint 0.585-0.600'), 426, 444-450 (Part B table: J_ub* 0.9975/0.59, J_own* 0.56/0.025), 465-466 (grid-best rows), 468; analysis/p2e5_power.py ranking() 'best' dict
- evidence: completeness/grid_44_cyclic.log and grid_44_random.log are both seed 44; no seed 45 grid exists. The 'ranges' 0.585-0.600, 0.555-0.565, 0.995-1.000 and '18-24 passing points' span cyclic against random learning order, and random order is not the contract's design. grid.py's 'best' maximises min(joint, D3, D4). By the contract's definition ('the best joint over the grid', line 279), the main store's best joint is 0.565 (cyclic) and 0.600 (random) at M = 500, and 0.04 and 0.065 at M = 1,000, not 0.555-0.565 and 0.025. The plateau-set values coincide. Sensitivity (partb_indep.py, 40,000 simulations):
- With J_own* at the contract's definition: P(CONTAMINATION-DOMINANT) falls from 0.57 to 0.35 at M = 500 with L_o 0.35, and from 0.79 to 0.58 at M = 1,000 with L_o 0.45.
- At M = 1,000 the 0.986 depends on J_ub* = 0.59 from one seed. With J_ub* 0.53 it is 0.68 (SD 0.18) or 0.52 (SD 0.30); with 0.50 it is 0.32. At the frozen point the four M = 1,000 runs already range 0.12-0.18.
- fix: Label every grid-derived number 'seed 44 only (two learning orders)', or run seed 45's 72-point grid (main, plateau-set, R_3) at both loads before freezing (about 15 min). Pin 'grid best' exactly: max joint, or max of min(joint, D3, D4) as explored, or max joint subject to D3 >= 0.90. Recompute J_own* and the Part B table with the matching values. Add a sensitivity row for J_ub* at M = 1,000 (for example 0.50-0.59).

### F3 [minor] 'P(S1 at M = 500) = 0.001, whatever the write' (and oracle '0.000 at M = 500 alone') uses one lens's two runs; independence understates it here, so it is not conservative

- where: lines 425-426 ('Independence ... is conservative'; 'Rates ... from seeds 44-45'), 430-437, 459 ('P(all seeds) 0.001'); analysis/p2e5_power.py S60 (comment 'methodology lens agrees')
- evidence: S60 in the script holds only the implementation lens's runs (C4-spurious 0.86/0.92, C2 0.895/0.91). The methodology lens on the same seeds (s60_F10.jsonl) has C4-spurious 0.91/0.91 and C2 0.92/0.915, so it does not agree on C4. My code gives P(S1 at M = 500):
- 0.0013 with the implementation rates;
- 0.047 with the methodology rates;
- 0.0095 with all four runs averaged;
- per run: 6e-6, 0.050, 0.058, 0.027.
The oracle at M = 500 alone is 0.012 with the methodology rates. C4 is scored on the oldest 100 of the same 200 half cues as C2, and a seed effect is shared within a seed. Modelling both raises P(S1 at M = 500) from 0.0013 to 0.011 (implementation rates) and from 0.0095 to 0.039 (all four). Independence is conservative for P(PASS) of a passing system, but anti-conservative for these near-zero claims. The conclusion (S1 very likely fails at M = 500) stands.
- fix: Report 'P(S1 holds on all seeds at M = 500) about 0.001-0.05 (lens and dependence), below 0.05', and give the oracle at M = 500 as 0.0002-0.012. Use all four exploratory runs in S60, or state which lens and why. Reword the independence sentence: 'conservative for pass probabilities near 1, not for near-zero ones'. Correct the script comment, and the same 0.001 in the DECISIONS entry.

### F4 [minor] Part B's three losses are not on one scale; the decision consequences of the thresholds and of L_i's label

- where: lines 287-303 (losses, dominance, readings), 292 (L_i 'forward-index cross-talk'), 300 vs 303 (0.05 against 0.10)
- evidence: Part B is exclusive and exhaustive as written: one dominant failure per seed, so two X-DOMINANT readings would need 8 seed-slots. 'and no failure dominates' rules out NO MATERIAL LOSS together with an X-DOMINANT reading. But:
(1) L_c = J_ub* - J_own* is not capped at the bar while L_i is, so L_c + L_i != 0.90 - J_own* when J_ub* > 0.90. At M = 500 L_c is 0.4375 against a bar-relevant 0.34. Capping L_c moves P(CONTAMINATION-DOMINANT) from 0.999 to 0.63 at L_o 0.25, and to SPLIT 0.97 at L_o 0.35 (partb_indep.py).
(2) L_o is measured on a different criterion (index recall, or the joint, whichever is larger), store (online-written), cue set (P2-E4 block, recent and uniform ages, not the P2-E3 test set; line 287 says 'the 200 gated half cues') and readout (frozen, not the grid best).
(3) The contract does not clip L_c or L_o, and L_o can be negative: P2-E4's content net at M = 1,000 was (8-22)/200 and (4-27)/200. So INDEX can 'dominate' with every loss below 0.05 (L_i small, the others negative).
(4) An X-DOMINANT reading needs no absolute size (L_o 0.06 against 0 reads OPERATING-POINT-DOMINANT), while 'material' starts at 0.10 and NO MATERIAL LOSS needs every loss below 0.05.
(5) At M = 1,000, with a perfect index (verify-implementation/oracle.py, seed 44) the plateau-set store reaches only 0.745 at the frozen point. So L_i is not purely forward-index cross-talk.
(6) At M = 500 L_i is 0, but S1 is predicted to fail through C2 and C4-spurious with no write able to fix it. A CONTAMINATION-DOMINANT reading then routes to a write mechanism that cannot pass P2-E5's unchanged S1 at M = 500.
- fix: Define L_c = max(0, min(J_ub*, 0.90) - min(J_own*, 0.90)). Clip every loss at 0. State that L_o is on a different cue set and criterion, or measure it on the joint/'both' of twin B against online on the same 200 cues. Require the dominant loss to be material (>= 0.10), or rename NO MATERIAL LOSS to 'NO LOSS >= 0.05'. Relabel L_i 'shortfall with an item-specific write (index cross-talk plus store limit)'. In the Decision section, send any load where S1 fails to the owner alongside the Part B reading. Recompute the table.

### F5 [minor] The s = 100 replication probability is misattributed, and NOT ATTRIBUTABLE exclusions are missing from Part B's probabilities and denominators

- where: lines 442-443 ('about 0.86 at P2-E3's recorded rates'), 306-307 (NOT ATTRIBUTABLE), 471; analysis/p2e5_power.py replication_s100=p_i
- evidence: 0.856 uses power.P2E4_RATES, whose memory rates pool P2-E2 seeds 6-10 with P2-E3. With P2-E3's own recorded seeds 11-15 (bench/results/plant2.jsonl: C1 0.938, C4 0.954/0.986, joint 0.975, D4 0.972 at M = 1,000), my code gives 0.789: C1 at 1,000 0.84, C4-recall 0.94. So P(at least one seed NOT ATTRIBUTABLE) is 0.14-0.21, and P(a load NOT ATTRIBUTABLE: two or more seeds) is 0.01-0.02. The Part B simulation ignores this. With one seed excluded, 4 of the remaining 4 are needed, which lowers 0.986 to about 0.94-0.96 at M = 1,000. The contract does not say whether '4 of 5' becomes 4 of the remaining seeds, nor whether a failure at one load excludes the seed at both.
- fix: Write 'about 0.79-0.86 (P2-E3-only against pooled memory rates)'. Fold the exclusion probability into the Part B table. State the denominator after exclusion (at least 4 of the remaining seeds, at least 4 needed) and the load scope of an exclusion.

### F6 [minor] Descriptive numbers misattributed (|R| as extra responders; medians labelled means; values from different lenses paired)

- where: lines 56-57, 103-104, 471, 476, 479
- evidence: (1) Lines 56-57: 'their number [the extra responders] grows ... about 74 for items 400-500, and 150-160 for items 900-1,000'. These are |R| (out_s60: 76.4/72.0 and 151.4/163.3; where.py 71.9/74.9 and 153.3/164.0). The extra responders are 51.9-56.6 and 130.6-143.0, and the upper end of |R| is 164, not 160.
(2) Line 104 pairs the online 0.055-0.065 with 0.10-0.145. On the same items (where.py) the P2-E3-protocol joint is 0.105-0.145; 0.10 is the implementation lens's other generator.
(3) Line 476 is headed 'means', but the own-cell input share 0.93/0.6 is a median (0.927/0.931; 0.597/0.580).
(4) Line 479's '80-98 memory responders' mixes medians (79-85.5) and means (97.2-97.8).
(5) Line 471 puts 'C1 0.94-0.97' under M = 500, but s = 100 C1 was 0.945/0.945 at M = 500 and 0.97/0.95 at M = 1,000.
- fix: Change line 57 to '|R| about 72-76 for items 400-500 and 151-164 for items 900-1,000 (extra responders about 52-57 and 131-143)'. Use 0.105-0.145 on line 104. Label medians as medians. Split C1 by load in the s = 100 row.

### F7 [nit] Some prediction ranges exclude values already observed

- where: line 459 (S1 C1 ranges), 472 (s = 80 plateau-set)
- evidence: C1 at M = 500 is predicted 0.95-0.98, but observed 0.945-0.975 (s60_F10 seed 45: 0.945). C1 at M = 1,000 is predicted 0.92-0.96, but observed 0.915-0.955 (s60_F10 seed 45: 0.915). s = 80 plateau-set at M = 1,000 is predicted 0.93-0.95, but observed 0.92-0.94 (s80_F10 seed 44: 0.92).
- fix: Widen to cover the observed values: 0.94-0.98, 0.91-0.96 and 0.92-0.95.

### F8 [nit] P(INVALID) about 0.007 is more precise than its basis

- where: lines 439-441
- evidence: The normal model (mean 0.11, SD 0.03) is assumed. The gated condition's four mean |dvbar| values at M = 1,000 are 0.090, 0.096, 0.120 and 0.122 (mean 0.107, SD 0.017). '0.130, the largest exploratory value' is the s = 40 arm (seed 45), not the gated condition (largest 0.122). The 3-SD tail is model-driven: SD 0.04 gives 0.06, SD 0.05 gives 0.17. The qualitative claim (INVALID unlikely: every exploratory and P2-E3 value is <= 0.13 against a 0.2 bar) holds.
- fix: Write 'below about 0.01 under a normal model (mean 0.11, SD 0.03; under 0.06 at SD 0.04)', and attribute 0.130 to the s = 40 arm.

### F9 [nit] The 0.05 thresholds compared in floating point; pin integer cue counts. Part C's 'within' is two-sided

- where: lines 295, 300, 318, 343-344
- evidence: Joints are k/200. For differences of exactly 10/200, 99 of 191 pairs evaluate below 0.05 in floating point (for example 0.06 - 0.01 = 0.049999999999999996). So 'exceeds by at least 0.05' and 'within 0.05' at the boundary would be decided by rounding. Part C's two-sided 'within 0.05' would read NOT SHOWN if R_3 beat the plateau-set store by more than 0.05; at M = 1,000 R_4 already beats it by 0.08 at the frozen point (rk_44.log). My replay supports Part C's prediction on seed 44 at M = 1,000: R_3 is 0.165 against 0.160 at the frozen point and 0.610 against 0.600 at the grid best, both at (5.0, 0.8) (r3grid.log).
- fix: State every threshold as a cue count (>= 10 of 200 cues). Make Part C one-sided: R_3 >= plateau-set - 10/200 at both points.

## Computed (scripts and numbers)

Scripts and outputs are under /root/.cache/brain-sim/review/p2e5-verify/numbers/. Nothing was written under /home/user/brain-sim; git status is clean.

- **power_indep.py** (own code; output power_indep.out.json). Exact log-space binomials, logit-normal seed SD 0.18 on a 4,001-point grid, no plant2.power.
  - Idealised: pooled 0.8556 (C1 at 1,000 0.921, C4r 0.934); P2-E3-only 0.7891 (C1 0.84, C4r 0.942). P2-E3 recorded rates incl. C4-spurious give 0.789.
  - Oracle (implementation rates): at M = 500 alone 0.00019 (C2 0.066, C4s 0.020, S2 0.658, S4 0.224). With methodology rates 0.0116; all four runs 0.0018.
  - P(S1 at M = 500): implementation 0.0013, methodology 0.047, all four 0.0095; per run 5.7e-6, 0.050, 0.058, 0.027. With shared cues (C4 is the oldest 100 of C2's 200) and a shared seed effect: 0.011 (implementation), 0.039 (all four).
  - P(INVALID): contract model 0.0067; SD 0.04 gives 0.060; SD 0.05 gives 0.167. Gated-condition values 0.090/0.096/0.120/0.122 (mean 0.107, SD 0.017).
- **partb_indep.py** (own simulation, 40,000 draws; output partb_indep.out.json).
  - Base table reproduced. M = 500: 1.0 / 1.0 / 0.9986 for L_o 0.07 / 0.15 / 0.25; 0.59 at 0.35; SPLIT 0.965 at 0.45. M = 1,000: 0.989 for L_o 0.07-0.35; 0.81 at 0.45; index material 1.0.
  - Variants: J_own* by max joint: 0.35 (M = 500, L_o 0.35), 0.58 (M = 1,000, L_o 0.45). L_c capped at the bar: 0.63 (M = 500, L_o 0.25), SPLIT 0.97 (L_o 0.35). A paired seed effect or a net-with-reverse L_o changes nothing material. J_ub* at M = 1,000 of 0.50 / 0.53 / 0.55 / 0.59 gives 0.32 / 0.68 / 0.86 / 0.99 at SD 0.18, and 0.27 / 0.52 / 0.69 / 0.91 at SD 0.30.
  - Part D at M = 500 (deltas -0.090 and -0.040): WORSENS 0.50, MIXED 0.43, NOT WORSE 0.06.
  - Floating-point boundary: 99 of 191 exact 10/200 differences evaluate below 0.05.
- **r3grid.py** (one simulation; seed 44, s = 60, M = 1,000, cyclic; 248 s; output r3grid.log and r3grid_s60_seed44_M1000.json). Reuses the red-team's rk.E3log and grid.FamilyGen. The raster check reproduces the plateau-set store (0.160 at (2.8, 0.3); 0.600 at (5.0, 0.8)). R_3: 0.165 at the frozen point; grid best 0.610 at (5.0, 0.8) with D3 1.0; 0 of 72 points pass.
- **Grid best by definition** (read from grid_s60_seed44_{cyclic,random}.json): main max joint 0.565/0.600 at M = 500 and 0.04/0.065 at M = 1,000, against 0.565/0.555 and 0.025/0.025 at the argmax of min(joint, D3, D4). Plateau-set: both definitions give the same value.
- **Ran analysis/p2e5_power.py read-only** (no --append; output p2e5_power_stdout.json): it matches the contract and my numbers.
- **Cross-checked** the contract's other quoted numbers against out_s*_seed4*.json, s*_F*.jsonl, where_*.json, rk_4*.log, grid_44_*.log, oracle_s60_44.log, bench/results/plant2.jsonl (P2-E3 seeds 11-15, including converge_mv and signed drift) and P2-E4-diagnosis-plan.md D3. The net online index loss is 0.07 / 0.065 at M = 500 and 0.26 / 0.16 at M = 1,000, as the contract states.
