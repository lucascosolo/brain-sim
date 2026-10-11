# P2-E5 contract fix-check: fixes

Fresh checker given only the files (second revision at commit 3c78f03). Run 2026-10-11. Recorded verbatim, before synthesis.

## Verdict

Can be frozen. I found no blocker or major problem. I checked all 36 ledger rows of the verification review against the revised contract (3c78f03), analysis/p2e5_power.py, the appended ledger correction rows and the DECISIONS entry. 35 are done as their ledger action says. COV-11 is done except for one inaccurate correction row: the methodology-B1 row claims probabilities for Parts C and D, and the contract has none (minor). COV-10 is "accepted in part" and done to that extent. Smaller wording gaps on F3, COV-12 and the Part B table are listed below as nits. Seed 45's grid was run and the grid best is pinned as the maximum joint with first-in-grid-order ties; the GRID values match both cyclic JSONs exactly (ub 1.0/0.985 and 0.60/0.665, own 0.565/0.675 and 0.04/0.055, frozen 0.925/0.935 and 0.13/0.10, 0.16/0.12 and 0/0, 24 and 26 passing points). The integer-cue pin, one-sided Part C, Part D on the median-intrusion ratio, validity 7 with the read-only step wrapper, Part B in cues, the Decision routing, and the pins on the online arm, streams and Part G are all present. I re-ran the power script read-only. Every number in the Power section and every probability in the Predictions table matches its output. The script implements Part B exactly: integer cues, L_c capped at 180, L_i = 180 - J_ub*, losses clipped at 0, 20-cue materiality, 10-cue margin over both other losses, exclusion per load, and the reading order NOT ATTRIBUTABLE, then X-DOMINANT, then NO MATERIAL LOSS, then SPLIT. An independent re-implementation reproduces every cell within Monte Carlo error. The leftover issues are a wrong ledger correction row and some incomplete wording.

## Findings

### LED-1 [minor] COV-11 done differently from the ledger: the methodology-B1 correction row claims per-reading probabilities for Parts C and D that the contract does not give, and DECISIONS calls B1 completed

- where: review/ledger.jsonl, appended row finding P2-E5-methodology-B1 (reviewer 'lead (correction after verification)'); DECISIONS.md 2026-10-11 'P2-E5 verification acted on' entry ('methodology M2, B1 and n1 as completed only by this revision'); contract lines 588 (Part C row) and 590 (Part D row)
- evidence: The correction row says: "probabilities now given per reading where computed (Parts B, C, D); the rest stated as qualitative predictions." The Predictions table gives probabilities only for S1 (0.01-0.04), validity (0.01-0.06), Part B (0.85-0.97; 0.98), s = 100 (0.79-0.86) and P(PASS) (< 10^-6). The Part C row reads 'count AUC >= 0.999; R_3 within 10 cues ...: AVAILABLE FROM ACTIVITY' and the Part D row reads 'WORSENS. Mean intrusions ... about 180 online against about 100'. Neither carries a probability, and the Part D prediction rests on means from the red-team's line, while the reading uses medians on twin A. Methodology B1's recommendation 2 was 'Give each criterion and arm a stated probability'. So B1 is accepted in part, not completed, and the appended row misstates what the contract holds.
- fix: Append one more ledger correction row for P2-E5-methodology-B1. Make it 'accepted in part': probabilities are given for S1, validity, Part B, s = 100 and P(PASS); Parts C, D, E and F-G are qualitative predictions. Append a matching one-line note to DECISIONS. Alternatively, add the probabilities to the Part C and Part D rows, for example Part D at M = 500 from the exploratory medians, with the basis named.

### LED-2 [nit] F3: the per-run range of P(S1 at M = 500) is given for the dependent model only, but reads as covering both models

- where: contract lines 550-552 ('0.0095 by the independent model and 0.039 by the dependent one ... By run it ranges from 0.0002 to 0.12'); the same sentence in the DECISIONS 2026-10-11 verification entry
- evidence: Script output (main_arm.p_S1_M500), run read-only. Independent model by run: impl44 5.7e-6, impl45 0.050, meth44 0.058, meth45 0.027. Dependent model by run: 0.000185, 0.113, 0.124, 0.082. So 0.0002-0.12 is the dependent model's range. Under independence the range is 6e-6 to 0.058. The F3 action ('per-run, all-four and dependent-model values reported') is therefore only partly reflected in the text. The conclusion is unaffected.
- fix: Write: 'By run it ranges from 6e-6 to 0.058 (independent) and from 0.0002 to 0.12 (dependent).'

### LED-3 [nit] Part B power table: the M = 1,000 material column omits the operating-point loss, and 'the rest reads SPLIT' ignores NOT ATTRIBUTABLE

- where: contract line 569 (M = 1,000 'material losses' cell) and lines 571-572 (sensitivity sentence)
- evidence: Script ranking['1000:L_o=x'].material.operating_point: 0.0001 at L_o 0.07, then 0.970, 0.981, 0.981 and 0.979 for L_o 0.15-0.45. The M = 500 row lists 'operating point when L_o >= 0.15'; the M = 1,000 row gives only 'contamination 0.98; index 0.98'. The Predictions table copies this ('with the index loss also material (0.98)'). In the sensitivity rows, NOT_ATTRIBUTABLE is 0.019-0.020, and INDEX_DOMINANT is 0.0046 at J_ub* 0.50. So 'the rest' is not all SPLIT.
- fix: Add 'operating point when L_o >= 0.15 (0.97-0.98)' to the M = 1,000 material cell, and the same to the Predictions Part B M = 1,000 cell. Change 'The rest reads SPLIT' to 'the rest reads SPLIT, apart from about 0.02 NOT ATTRIBUTABLE'.

### LED-4 [nit] COV-12: validity 5 is called 'P2-E3's rule unchanged' but moves P2-E3's VOID outcome to INVALID without saying so

- where: contract lines 279-285 (validity 5) under 'Validity (... a failure on any gated seed makes the verdict INVALID)'; docs/plant2/P2-E3-content-completion.md line 148
- evidence: P2-E3 line 148 reads: '**Void (VOID, not pass).** The shuffled-feedback arm must fail D1/2 at M = 1,000 on every gated seed', and this sits outside its Validity list ('a failure makes the run invalid'). P2-E5 quotes the threshold unchanged (joint < 0.90 at M = 1,000) but files it under Validity, so a failure would read INVALID. COV-12's fix asked to 'label the change and the VOID-to-INVALID move as new'. This has no practical effect, because the contract notes the check cannot fail on this distribution.
- fix: Add a clause to validity 5: 'P2-E3 treated a failure as VOID; here it is a validity check, so a failure makes the verdict INVALID.'

### LED-5 [nit] The ranking() docstring misstates the dominance rule that its code implements correctly

- where: analysis/p2e5_power.py lines 133-140 (ranking docstring)
- evidence: The docstring reads: 'A load reads X-DOMINANT if X dominates on >= 4 seeds and on every attributable seed beyond the fifth's allowance (>= 4 of the attributable seeds, with >= 4 attributable)'. That is garbled. The code (lines 160-176) applies the contract's rule exactly: X dominates on >= 4 attributable seeds, with >= 4 seeds attributable. My independent re-implementation matches the code's output within Monte Carlo error.
- fix: Change the docstring to: 'A load reads X-DOMINANT if X dominates on at least 4 of the attributable seeds (and at least 4 are attributable).'

## Computed (scripts and numbers)

Nothing was written under /home/user/brain-sim. git status is clean at 3c78f03. Outputs are in /root/.cache/brain-sim/review/p2e5-fixcheck/ledger/.

1. **Power script, run read-only** (PYTHONDONTWRITEBYTECODE=1, no --append; output power_out.json).
   - idealised pooled 0.8556 (C1 at 1,000 0.921, C4-recall 0.934); P2-E3-only 0.7891 (C1 0.840).
   - oracle: p_pass 0.0; M = 500 alone 0.00183; by run 1.58e-8, 0.0352, 0.0119, 0.0075; M = 500 parts C2 0.159, C4-spurious 0.060, S2 0.722, S4 0.267.
   - main arm: p_pass 0.0.
   - P(S1 at M = 500), all four runs: 0.00949 independent, 0.0392 dependent. By run, independent 5.7e-6 / 0.050 / 0.058 / 0.027; dependent 0.000185 / 0.113 / 0.124 / 0.082.
   - P(INVALID): 0.0067 at SD 0.03, 0.0596 at SD 0.04.
   - s = 100: 0.856 pooled, 0.789 P2-E3-only; per seed and load 0.99966 at M = 500, 0.9541 at M = 1,000.
   - Part B, M = 500: CONTAMINATION-DOMINANT 1.0 / 0.945 / 0.079 at L_o 0.07 / 0.15 / 0.25 (SPLIT 0.921 at 0.25). L_o 0.35 gives SPLIT 0.598 and OPERATING-POINT-DOMINANT 0.402; L_o 0.45 gives OPERATING-POINT-DOMINANT 0.990. Material: contamination 1.0, index 0, operating point 0.998 or more from L_o 0.15.
   - Part B, M = 1,000: CONTAMINATION-DOMINANT 0.974 / 0.975 / 0.973 / 0.972 / 0.851 for L_o 0.07-0.45 (SPLIT 0.128 at 0.45); NOT ATTRIBUTABLE 0.019-0.021. Material: contamination 0.98, index 0.98, operating point 0.97-0.98 from L_o 0.15.
   - Sensitivity at L_o 0.25: CONTAMINATION-DOMINANT 0.177 / 0.481 / 0.687 / 0.919 at J_ub* 0.50 / 0.53 / 0.55 / 0.59.
   - All of these match the contract's Power section and its Predictions probabilities, except as noted in LED-2 and LED-3.

2. **Independent Part B re-implementation** (partb_check.py, my own per-seed loop; output partb_check.out.json). It reproduces every cell within Monte Carlo error, for example:
   - M = 500, L_o 0.15: CONTAMINATION-DOMINANT 0.946;
   - M = 500, L_o 0.35: OPERATING-POINT-DOMINANT 0.409;
   - M = 1,000, L_o 0.45: CONTAMINATION-DOMINANT 0.851;
   - sensitivity: 0.169 / 0.488 / 0.700 / 0.922.

3. **Grid bests by the contract's definition** (maximum joint, first in grid order), read from completeness/grid_s60_seed4{4,5}_cyclic.json.
   - Main store: M = 500 0.565 at (2.8, 0.7) and 0.675 at (3.6, 0.8); M = 1,000 0.04 at (3.2, 1.0) and 0.055 at (2.4, 0.6).
   - Plateau-set store: M = 500 1.0 and 0.985; M = 1,000 0.60 and 0.665.
   - Passing points (S2, S3 and S4 all hold): 24 and 26 for the plateau-set store at M = 500, 0 elsewhere.
   - Frozen points match GRID.

4. **Code checks.**
   - E3.learn_one calls self.net.step exactly t_item + t_cont times, and quiet() does not step, so the wrapper pin and validity 7 are feasible.
   - Novel cues come from E1's own novel stream, not _pat, so they stay independent with an injected generator.
   - twin_A returns main, swap_reference and swap_plateau with intrusions_median, as Part D needs; twin_B returns 'all' (n = 200) with the McNemar memory and content counts that L_o needs.
   - state_digest JSON-dumps _pat.bit_generator.state.
   - P2-E5 stream ids 20-24 do not collide with P2-E1 (0-6), P2-E2 (8), P2-E3 (9-11) or P2-E4 (12-18).

5. **Ledger and DECISIONS.**
   - All 36 rows were read against the verify-*.md reports.
   - The five appended correction rows match DECISIONS, except the B1 row's 'Parts B, C, D' (LED-1).
   - Other spot-checked numbers agree with the exploratory outputs: |R| 72-76 and 151-164, extra responders 52-57 and 131-143, the 99.7 % earlier-sibling share, continuation counts (sibling responders fire once in 94-95 % of cases), and where.py intrusion means (online 184 / 175 against P2-E3 protocol 100 at M = 500).
