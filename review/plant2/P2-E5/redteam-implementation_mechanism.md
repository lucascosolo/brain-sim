# P2-E5 draft red-team: implementation and mechanism lens

Fresh reviewer given only the files (draft at commit e736e81); each finding then checked by a separate refuter. Run 2026-10-10 to 2026-10-11. Recorded verbatim, before synthesis.

## Verdict

The draft cannot be frozen as written. The protocol can be implemented exactly on the existing code. I wrote a fresh E3 subclass in which only `_pat` (the item generator) changes. On it:
- the P2-E1 forward-store check, run as "P2-E1 learning on the same items", returns True at M = 500 and 1,000 on both exploration seeds;
- the main-line digests are unchanged by the test copies;
- P2-E3's own `run_phase`, `readout` and `score` give gated numbers identical to my independent rescoring over the raster with the extra cues appended;
- the cost estimate holds: about 19 min per seed.

Exploration on seeds 44 and 45 (labelled exploratory) reproduces the collapse at s = 60 and M = 500: joint 0.130 and 0.100, against 0.925 and 0.935 for the plateau-set store.

The blocking problem is one validity rule. The new signed-drift rule (|signed drift| <= 0.1 mV) sits on the deterministic exponential tail of the 50 s settle, not on noise. It would fail at s = 60, M = 1,000 on one of the two exploration seeds, so the expected FAIL would probably be recorded as INVALID.

The mechanism exploration changes what the experiment will show and what ruling 4's next step can achieve:
- **M = 1,000, s = 60:** content joint is 0.000 on both seeds, with about 1,800 intruding lines per cue.
- **Memory C2:** 0.47-0.50, so S1 fails. The draft predicts it holds. The spurious memory cells come from the forward BTSP store: prototype lines build up on cells that belong to several siblings' plateau sets.
- **Plateau-set baseline:** collapses at M = 1,000 (0.12-0.16).
- **Overlap arms at M = 1,000:**
  - s = 80 fails (0.665-0.68), against the predicted 0.99;
  - s = 40 collapses in the memory layer itself (C2 0.15 at M = 500);
  - s = 100 replicates P2-E3 (0.98).

So "the responder write against the plateau-set baseline" covers only M = 500. Further problems:
- S3 cannot fail on this item distribution.
- The scoring of new-exemplar and prototype cues is undefined.
- The within-family permutation arm is given the wrong rationale.
- The stream ids are unpinned.

## Findings

### B1 [blocker] The signed-drift validity bar (|signed drift| <= 0.1 mV) sits on the deterministic tail of the 50 s settle; the expected FAIL will most likely be recorded as INVALID

- where: Draft, Validity bullet 4 ('convergence is gated on signed drift ... <= 0.1 mV'), against 'Everything is P2-E3 exactly' and the Verdicts list (INVALID takes precedence in P2-E3's and P2-E4's verdict code)
- evidence: Exploratory, `fam5.py`, settle drift (abs; signed) at M = 1,000:

| arm | seed 44 | seed 45 |
|---|---|---|
| s = 60 (gated) | 0.096; -0.085 | 0.120; **-0.114** |
| s = 80 | 0.076; -0.052 | 0.110; **-0.101** |
| s = 100 | 0.073; -0.045 | 0.100; -0.088 |
| s = 40 | 0.115; **-0.110** | 0.130; **-0.127** |
| F = 20 control | -0.055 | -0.100 |

- At M = 500 every value is between -0.018 and -0.054.
- **This is not noise.** vbar relaxes with tau 10 s from its learning-time level, so the drift over seconds 40-50 is about (e^-4 - e^-5) x (learning offset - settled offset), roughly 0.0116 x the excess.
- The learning-time offsets (`cont_offset`, last 100 items) are:
  - 9.05-9.24 mV at s = 100;
  - 9.7-9.8 mV at s = 80;
  - 11.6-11.7 mV at s = 60;
  - 13.2-13.3 mV at s = 40.
  The drift tracks them.
- **P2-E3's own gated seeds** (`bench/results/plant2.jsonl`) gave signed drift at M = 1,000 of -0.024, -0.072, -0.070, -0.110 (seed 14) and -0.072, with seed 0 at -0.089. Under this rule P2-E3 itself would have been INVALID on seed 14.
- **The probability.** At s = 60 the two exploration seeds straddle the bar. P(at least one of 5 gated seeds INVALID) is likely above 0.8 (exploratory estimate).
- **The draft does not say whether INVALID or FAIL wins** when both apply. P2-E3's `verdict()` and P2-E4's labels put INVALID first.
- **P2-E3's actual rule** (mean |dvbar| <= 0.2 mV) passes every run above: 0.048-0.130.
- recommendation: Keep P2-E3's convergence rule verbatim, as the draft's 'everything is P2-E3 exactly' requires: mean |dvbar| <= 0.2 mV over the last 10 s, with signed drift reported beside it.

If a signed-drift gate is wanted:
- derive its bar from the expected tail, 0.0116 x the measured excess offset, or roughly 0.2 mV;
- show on 44-45 that it passes;
- never lengthen the settle, which would change P2-E3's protocol.

State the label precedence (INVALID against FAIL) explicitly. Consider making a convergence flag reported-only for this diagnostic, whose purpose is the baseline record.
- independent verifier: **confirmed** (severity should be blocker): Every quoted number checks out against out_*.json and bench/results/plant2.jsonl.

**The facts hold.**
- P2-E3's own rule is mean |dvbar| <= 0.2 mV: CONVERGE_BAR_MV = 0.2 in p2_e2_accommodation.py, applied by `converged` at p2_e3_completion.py:376.
- P2-E3's gated seeds at M = 1,000 had signed drift of -0.024, -0.072, -0.070, -0.110 (seed 14) and -0.072. Seed 0 had -0.089. So seed 14 would have been INVALID under the draft's 0.1 bar.
- On seed 45, s = 60 at M = 1,000 gives -0.114.
- The draft's Verdicts list states no precedence. P2-E3's `verdict()` checks INVALID before FAIL, and P2-E4 does too ('Validity (checked first...)').

**One part is overstated: 'This is not noise. The drift is a deterministic tail.'**
- P2-E3's seeds at M = 1,000 had nearly identical learning offsets (9.31-9.46 mV), yet their drift ranged from -0.024 to -0.110.
- Seed 45 is more negative than seed 44 in every arm (-0.114 against -0.085, -0.101 against -0.052, -0.088 against -0.045, and so on), at almost equal offsets. The settle stream (seed, TEST_IN, M, 101) is shared across arms within a seed.
- So the drift is a systematic tail that scales with the offset (about 0.008 x the offset across all 18 runs), plus a seed-level component with SD of about 0.03.

**This strengthens the risk rather than weakening it.** At s = 60 and M = 1,000 (offset about 11.7 mV) the mean drift is about -0.09 with SD about 0.03, so P(at least one of 5 seeds has |drift| > 0.1) is about 0.8-0.95 (exploratory). An INVALID would spend the fresh seeds 21-25 and need an owner ruling.

**Context.** The draft's change has a documented basis: the P2-E2 addendum, item 9, says 'future contracts gate convergence on signed drift instead'. The defect is the unpowered 0.1 bar, not the idea of a signed-drift gate.

**Fix.** Keep P2-E3's rule, or use a signed-drift bar powered on seeds 44-45 (about 0.2). State that INVALID takes precedence over FAIL.

### M1 [major] At M = 1,000 the memory index fails as well: S1 (C2) fails and the plateau-set baseline collapses, so the stated cause and the 'If it fails' plan cover only M = 500

- where: Draft: 'Why this test' (the cause), Predictions ('S1: C1 holds; C2 probably holds'; 'Expected verdict: FAIL on S2 (and S4)'), 'Comparison arms' (plateau-set store 'isolates the responder write'), and 'If it fails' (correction 'against the plateau-set baseline')
- evidence: Exploratory, s = 60, seed 44 / 45.

**Memory layer:**

| M | C1 | C2 | C3 | C4 spurious | memory responders per half cue (median, p90) |
|---|---|---|---|---|---|
| 500 | 0.955 / 0.975 | **0.895** / 0.91 | | | |
| 1,000 | 0.925 / 0.955 | **0.495 / 0.470** | 0.995 / 1.0 | 0.41 / 0.35 | 29-32, 66-68 |

S1 already fails at M = 500 on seed 44.

**Plateau-set store (A(x) x E(x), same raster):**
- M = 500: joint 0.925 / 0.935, but D4 0.88 on seed 44;
- M = 1,000: joint **0.160 / 0.120**, median intrusions 81-100.

**Where the spurious cells come from** (`spurious.py`, seed 44):
- At M = 1,000 there are 19 spurious memory cells per half cue, against 2.9 at M = 500.
- 98 % of them are plateau cells of at least one sibling (1.8 on average).
- Each gets about 13 strong forward synapses from the cue, of which about 9 are prototype lines. Assembly cells get 25: 10 prototype and 15 specific.
- The share of memory cells that are plateau cells of >= 2 exemplars of one family rises from 0.23 at M = 500 to 0.59 at M = 1,000.
- So the BTSP forward store builds up prototype lines on multi-sibling cells. No feedback-write change can touch that.

**Family-size control** (F = 20, so 50 exemplars per family at M = 1,000, as at M = 500): joint 0.015, plateau-set 0.535-0.55, C2 0.675-0.68. The index loss at M = 1,000 is not just family size.
- recommendation: Rewrite the predictions:
- S1 FAILS at M = 1,000 (C2 about 0.5);
- S1 is a coin flip at M = 500;
- the plateau-set arm is about 0.93 at M = 500 and about 0.14 at M = 1,000.

Adopt a P2-E4-style verdict vector with labels that separate MEMORY-INDEX FAIL (S1) from CONTENT FAIL (S2, S4). State that the plateau-set arm isolates the responder write only where C2 holds.

Before freezing, put this to the owner, because it changes ruling 4's next step. A write correction measured against the plateau-set baseline can at best reach the M = 500 target. At M = 1,000 the forward index must also change, and one mechanism per contract applies.

Add two reported diagnostics:
- the forward-store spurious-cell breakdown: membership in sibling plateau sets, and strong prototype synapses from the cue;
- the F = 20 arm at M = 1,000, separating load from family size.
- independent verifier: **confirmed** (severity should be major): **Verified from the outputs and spurious_*.json:**
- At s = 60, C2 is 0.895 / 0.910 at M = 500 (seed 44 is below the 0.90 bar) and 0.495 / 0.470 at M = 1,000.
- The plateau-set store gives 0.925 / 0.935 at M = 500 and 0.160 / 0.120 at M = 1,000, with median intrusions 81 / 99.5.
- There are 2.9 spurious cells per cue at M = 500 (583/200) and 19.2 at M = 1,000 (3,845/200). Of these, 98.8 % / 97.7 % are sibling plateau cells. They carry 11.6-12.7 strong synapses from the cue (9.1 of them prototype lines); assembly cells carry 24.7 (9.8 prototype, 14.9 specific).
- At F = 20 and M = 1,000: C2 0.675 / 0.68, plateau-set 0.55 / 0.535. At the same family size (50 exemplars), C2 is 0.90 at M = 500, so the drop is not only family size.
- The draft does predict 'C2 probably holds' and 'FAIL on S2 (and S4)', and it plans its correction against the plateau-set baseline.

**A caveat on the 0.23-0.59 rise.** The share of cells in >= 2 siblings' plateau sets rising from 0.23 to 0.59 is simply the combinatorial expectation of random plateaus with 50 and then 100 exemplars per family. It is not a separate finding.

**My oracle check refines the causal claim** (exploratory; seed 44; s = 60; M = 1,000; oracle.py). During each half cue I kept only the spikes of A(x)'s cells.
- The plateau-set store rises from 0.16 to 0.745 (median intrusions 4.5, p90 19).
- The main store goes from 0.000 to only 0.025.
- So the forward index causes most of the plateau-set collapse. But even with a perfect index, the A x E store fails the 0.90 bar at M = 1,000.
- 'At M = 1,000 the forward index must also change' is therefore necessary but not sufficient, and 'can at best reach the M = 500 target' is roughly right.
- The plateau-set store is a baseline, not a ceiling for a correction write.

The core point stands: the cause and the 'If it fails' plan cover only M = 500, and this should go to the owner before freezing.

### M2 [major] Predictions are missing or wrong at M = 1,000 and for every overlap arm; the 'about 16 %' condition is not where the write breaks

- where: Draft Predictions table (no M = 1,000 number; 's = 80 arm about 0.99'; 's = 40 arm collapses (rec saturates)'; 'plateau-set arm about 0.94 at M = 500')
- evidence: Exploratory, seed 44 / 45. Joint, with the plateau-set store in brackets:

| arm | M = 500 | M = 1,000 |
|---|---|---|
| s = 60 | 0.130 / 0.100 [0.925 / 0.935] | **0.000 / 0.000** [0.160 / 0.120] |
| s = 80 | 1.000 / 0.995 | **0.665 / 0.680** [0.940 / 0.935] |
| s = 40 | 0.000 [0.07 / 0.05] | 0.000 [0.000] |
| s = 100 | 1.000 / 0.985 | 0.980 / 0.980 |

**s = 60, M = 1,000:**
- feedback density is 0.31, against P2-E3's 0.133 at M = 1,000 and above its 0.23 at M = 1,500;
- a half cue lights a median of 1,760-1,870 of the 4,000 rec lines;
- a prototype half cue lights about 3,550.

**s = 80, M = 1,000:** C2 is 0.94-0.945, and the intrusions are mostly sibling-specific lines (mean about 10, p90 22-26).

**s = 40:** the memory layer itself collapses:
- C2 0.17 / 0.15 at M = 500 and 0.025 at M = 1,000;
- C1 0.895 on seed 45 at M = 1,000;
- |R| 314-509.

**s = 100:** C1-C3 all >= 0.95, and |R| 23.2-23.8.
- recommendation: Replace the prediction table with per-load and per-arm values (joint, D1, D2, D4, C1-C3, plateau-set arm) from the real driver on seeds 44-45, appended as P2-E4 did.

State in the text that, on this protocol:
- the responder write already fails at about 5 % sibling overlap at M = 1,000;
- the s = 40 failure is in the memory index, not only in rec saturation.
- independent verifier: **partly** (severity should be minor): **The numbers reproduce:**
- s = 80: joint 0.665 / 0.680 at M = 1,000, with plateau-set 0.94 / 0.935 and C2 0.94 / 0.945. Intrusions are mostly sibling-specific (mean 10.0 / 9.7, p90 22-26). This is a clean demonstration that the responder write breaks at about 5.6 % sibling overlap at M = 1,000.
- s = 40: C2 0.17 / 0.15 at M = 500 and 0.025 at M = 1,000; |R| 314-509. The collapse is in the index too.
- s = 60: feedback density 0.310 / 0.314.

**Slips:**
- '1,760-1,870 lines lit' and the 3,889 cited in m1 are median intrusions. The median total lines lit are about 100 higher (1,859-1,973 and 3,989).
- At s = 100, C1 is 0.945 at M = 500, so 'all >= 0.95' holds only at M = 1,000.

**What does not hold as a defect:**
- The draft already states that its predictions come from M = 500 only and are 'to be extended to M = 1,000 and to the overlap arms on red-team seeds 44-45 before the contract is frozen'.
- Where predictions were stated (M = 500), 's = 80 about 0.99' (1.000 / 0.995) and 's = 40 collapses' are correct.
- The missing values are the draft's own pending step, and the M = 1,000 collapse duplicates M1.

**What should be kept:** the per-load and per-arm appended numbers, and the statements that the write fails at about 5 % overlap at M = 1,000 and that s = 40 fails in the index.

### m1 [minor] S3 cannot fail on this item distribution, and the new-exemplar and prototype cues have no defined scoring or reading

- where: Draft: Kill test S3; Test 'Reported cues'; Comparison arms 'new-exemplar and prototype half cues (what is regenerated, and how many memory cells respond)'
- evidence: Exploratory:
- **D3 on random novel cues** stays 0.980-1.000 in every arm and load, including s = 40 at M = 1,000, where a stored half cue lights a median of 3,889 lines. S3 measures nothing about family contamination; this is the P2-E3 addendum's 'controls that cannot fail' (item 8).
- **New exemplars at s = 60:**
  - M = 500: memory responders median 1, regenerated lines median 0;
  - M = 1,000: responders median 6-8 (p90 22-36), regenerated lines median 110-244, including 80-100 % of the missing prototype lines and about 0-4 % of the missing item-specific lines.
- **The joint criterion is unattainable for a new exemplar.** About 30 of its 50 missing lines were never stored.
- **Prototype half cues:** memory responders 80-98 at M = 500 and 240-262 at M = 1,000. They regenerate all of the missing prototype half plus about 720-770 lines at M = 500 and about 3,450 at M = 1,000, mostly sibling-specific lines.
- recommendation: Predeclare the reported statistics per cue kind:
- **New exemplars:** memory responders; total lines; the fraction of missing prototype lines and of prototype lines the item lacks; the fraction of missing specific lines (a chance floor); and a false-memory rate, P(< 10 lines), with predictions.
- **Prototype cues:** missing-prototype fraction; intrusions split into sibling-specific and other.

State beforehand that regenerating prototype lines from a new exemplar counts here as contamination by superposition, not generalisation (ruling 5).

Label S3 as a check that cannot fail on this distribution.
- independent verifier: **confirmed** (severity should be minor): **S3 cannot fail on this distribution.** D3 stays 0.98-1.00 in every arm and load, including s = 40 at M = 1,000, where stored half cues light about 3,990 lines. The novel cues are independent random items, so S3 cannot detect family contamination. The P2-E3 addendum, item 8, names this kind of control.

**New-exemplar numbers** (medians):
- M = 500: memory responders 1, lines 0.
- M = 1,000: responders 6 / 8 (p90 21.6 / 36), lines 110 / 243.5, missing-prototype fraction 0.80 / 1.00, missing-specific fraction 0.00 / 0.04.
- The joint criterion is unattainable for a new exemplar: about 30 of its 50 missing lines were never stored.

**Minor slips:**
- The finding quotes medians. The means show missing-specific regeneration of 0.14-0.24 at M = 1,000, which is chance-level given the 2,000-3,000 lines lit at p90. That supports its 'chance floor' framing.
- 'Prototype cue responders 80-98 at M = 500' mixes medians (79-85.5) with means (about 97).

**The defect is real.** The draft lists the new-exemplar and prototype cues with no defined statistics or predictions, and gates a criterion that cannot fail. Predeclaring the per-cue-kind statistics and labelling S3 accordingly is the right fix.

### m2 [minor] The within-family label permutation cannot pass the joint even under the 'family-generic' alternative; its stated rationale is wrong, and pi is unspecified

- where: Draft, Comparison arms: 'Within-family label permutation ... a specificity control that could pass if regeneration were only family-generic'
- evidence: At s = 60 an exemplar's missing half holds only about 20 prototype lines, so purely family-generic regeneration fails D1 in every arm.

Exploratory, M = 500:
- the permuted arm gives joint 0.000 / 0.000 and D1 0.000;
- the regenerated fraction of x's missing prototype lines is 0.79-0.80, and of its specific lines 0.05;
- pi(x)'s lines are regenerated at 0.98-0.99;
- the main arm regenerates x's item-specific missing lines at 0.97-0.99.

The informative contrast is therefore the item-specific missing fraction (main against permuted), not pass or fail. The draft does not say that pi must be a derangement within each family (a plain permutation leaves about one item per family unchanged), nor which stream draws it.
- recommendation: Restate the arm's reading as the item-specific missing fraction, main against permuted, together with the prototype-line fraction. Specify pi as a within-family derangement and give its stream key. Drop 'could pass'.
- independent verifier: **confirmed** (severity should be minor): **The arm cannot pass.**
- At s = 60 the missing half holds about 20 prototype lines and about 30 specific lines. D1 needs 40, so regeneration that is only family-generic cannot pass the joint in the permuted arm, or in main.
- Verified at M = 500 (fam_perm): joint 0.000 / 0.000 and D1 0.000. The regenerated fraction of x's missing prototype lines is 0.79 / 0.80 and of its specific lines 0.05. The fraction of pi(x)'s lines regenerated is 0.991 / 0.977.
- The main arm's missing-specific fraction is 0.988 / 0.97.
- So the draft's 'a specificity control that could pass if regeneration were only family-generic' is wrong as written. The informative reading is the item-specific missing fraction, main against permuted.

**Code check.** The permutation code is correct: it is a within-family derangement on stream 24, an id outside the draft's reserved 20-23.

**A small overstatement.** The draft's 'a sibling pi(x)' arguably already implies pi(x) != x. The real gap is the missing stream key.

### m3 [minor] Stream ids 20-23 have no keys or draw order, and three implementation pins are missing

- where: Draft, Items ('The generator draws from its own streams (ids 20-23)'), Test ('Reported cues ... appended'), Validity bullet 1
- evidence: My implementation (feasible as written) had to choose:
- (seed, 20) for the prototypes;
- (seed, 21, k) for exemplar k, keyed per item so that learning to M does not depend on what runs after it, as P2-E1 intends;
- (seed, 22, M) for the new exemplars and the extra block's input;
- (seed, 23, M) for the prototype masks;
- a further key for pi.

Other reasonable choices give different gated items.

Three pins the contract does not state:
1. **P2-E3's `build_cues` asserts** that len(cues) == len(onsets). Gated scoring must therefore call `e3.readout` with the first 600 onsets only. I verified that this gives values identical to scoring over the extended raster, for every arm, load and seed.
2. **`e1.evaluate`'s TEST_IN generator is local,** so the extra block needs its own input stream.
3. **The P2-E1 check needs the same generator injected into a plain E1** (`plain._pat`). It then checks the encoding path, not the generator. It was True on 44 and 45 at both loads.

Also: a duck-typed `_pat` breaks P2-E4's `state_digest` (`_pat.bit_generator.state`) if that helper is reused for the draft's digest check.
- recommendation: Add a stream table as P2-E4 has: key, use and draw order for 20-23 and for pi. Key exemplars per item. Pin that the extra block is a separate `present()` call on its own stream, after the 600 gated cues, and that gated scores come from P2-E3's `readout` on those 600 onsets. Pin the plain-E1 generator injection.

Add unit tests on seeds 90 and up for:
- generator statistics: sibling overlap about 17 at s = 60 (measured 16.8-17.0);
- identity of the gated scores with and without the extra block.
- independent verifier: **confirmed** (severity should be minor): **The draft gives no stream table.** It says only 'ids 20-23'. P2-E4 has a key / use / draw-order table, and pi needs an id outside 20-23. Different reasonable keyings give different gated items, so this is a real gap.

**The three pins are real:**
1. P2-E3's `build_cues` asserts len(cues) == len(onsets), so gated scoring must use the first 600 onsets. Verified: p2e3_main joint, D3 and D4 equal fam5's scores on the extended raster in all 18 runs.
2. `e1.evaluate` creates its TEST_IN generator locally, so the extra block needs its own stream.
3. The forward-store check needs the generator injected into a plain E1. fwd_equals_p2e1 is True at s = 60 on both seeds and both loads.

**Two weaker sub-points:**
- 'Keyed per item so learning to M does not depend on what runs after it' is a weak justification, because a dedicated sequential stream already has that property. Per-item keying is a choice, not a requirement.
- The `state_digest` / duck-typed `_pat` concern applies only if P2-E4's helper is reused. The draft's digest check is P2-E3-style (stores and vbar).

Neither weakens the finding.

### m4 [minor] The stated mechanism misdescribes the write and the intrusions; the hypothesis should say D1 holds and only D2 fails

- where: Draft, 'Why this test' ('|R(x)| rises to 50-52 ... Sibling assemblies fire during the continuation and write their own lines into x's feedback'), Hypothesis
- evidence: Exploratory, s = 60, seed 44 / 45.

**Responders:**
- |R| of 50-52 is the mean over all items. For items 400-500 it is 72-76, and for items 900-1,000 it is 151-163.
- Almost every extra responder belongs to an earlier sibling's plateau set: of R - A = 56.6 / 52.0, 56.4 / 51.8 are sibling cells, 0.2 other-assembly cells and 0 unassigned.
- They are scattered cells, not whole assemblies: >= 50 % of one sibling's assembly co-fires in only 0.24-0.39 continuations per item at M = 500.
- The write puts x's lines onto those cells' rows. It does not write sibling lines into x's feedback. Old items are hit hardest: D4 0.01-0.04 against a joint of 0.10-0.13.

**Intrusions at M = 500** (main arm, mean / median): prototype lines x lacks 36-38 / 41-44 (61-64 % of them), sibling-specific lines 55-60 / 30-33 (p90 137-162), other 5 / 1-2.

**What still holds:** D1 0.98-1.0, and x's item-specific missing lines are regenerated at 0.97-0.99. The failure is entirely D2.
- recommendation: Correct the cause sentence along these lines. Cells of earlier siblings' assemblies fire in x's continuation and receive x's lines. The number of such cells grows with family age. Cueing then regenerates prototype lines and whole siblings' specific lines.

Predict D1 holds and D2 fails, and give the intrusion split per load, so the next contract's target (intrusions, not recall) is fixed in advance.
- independent verifier: **confirmed** (severity should be minor): **The code contradicts the draft.** p2_e3_completion.py:83 writes `fb.add(R x eligible(x))`. The responders of x's continuation receive x's lines. Siblings do not write their own lines into x's feedback, as the draft says. The P2-E3 addendum, item 3, said only 'write feedback', so the draft's wording is its own error.

**Contamination works in reverse.** A(x)'s cells are recruited into later siblings' continuations and carry their lines. That fits D4 being lower than the joint: 0.04 / 0.01 against 0.13 / 0.10.

**Verified from R_decomp:**
- |R| for items 400-500 is 76.4 / 72.0, and for items 900-1,000 it is 151.4 / 163.3.
- Of R - A = 56.6 / 52.0, 56.4 / 51.8 are sibling cells, 0.19 / 0.22 other-assembly cells, and 0 unassigned.
- Sibling assemblies with >= 50 % co-firing: 0.39 / 0.24 per item.
- Intrusions at M = 500: prototype 36.4 / 38.3 (median 41 / 44.5; 61-64 % of lacking prototype lines), sibling-specific 60.5 / 55.0 (median 33 / 30, p90 162 / 137), other about 5.
- D1 is 1.0 / 0.98 and the missing-specific fraction 0.99 / 0.97, so the failure is entirely D2.

The recommendation (correct the cause sentence; predict D1 holds and D2 fails, with the intrusion split) is sound.

### n1 [nit] Small gaps in the gate text

- where: Draft, Kill test S1 and Validity
- evidence: - **C4 dropped.** S1 uses C1-C3, while P2-E3's D5 used C1-C4. The draft does not say C4 was dropped; at M = 1,000, C4 spurious is 0.41 / 0.35.
- **Mean |A| load unstated.** The draft does not say at which load the 18.5-21.5 range applies; P2-E3 used items up to 1,000.
- **Bits per synapse undefined.** It is listed as a diagnostic, but is undefined for correlated items, where the information per item is less than log2 C(4000,100).
- recommendation: State that C4 is reported only, or add it to S1. Pin the load for mean |A|. Define bits per synapse from the exemplar's entropy given its prototype, or drop it.
- independent verifier: **confirmed** (severity should be nit): **C4.** P2-E3's D5 used P2-E2's C1-C4 (contract line 140, and `gate_ok` in `e2.summary` includes C4). The draft's S1 uses C1-C3 without saying C4 was dropped. C4 spurious is 0.41 / 0.35 at M = 1,000.

**Mean |A| load.** The draft gives no load for the 18.5-21.5 range, while P2-E3 pinned M = 1,000. This is harmless in practice, because |A| does not depend on the items.

**Bits per synapse.** It appears only in the draft's diagnostics list (line 130) and is not defined anywhere in the plant2 docs.

All three are small text gaps.

## Exploratory runs (labelled; not results)

- `~/.cache/brain-sim/review/p2e5-redteam/implementation/fam5.py (`chain.sh`; log in logs/s60_seed44.log)` (seed 44; s = 60, F = 10, loads 500 and 1,000, --plain (P2-E1 forward-store check); frozen P2-E3 contract; arms: main, plateau-set, within-family permutation; extra cues: 100 new exemplars and 50 prototype half cues): Exploratory.
- M = 500:
  - joint 0.130 (D1 1.000, D2 0.130, D3 1.000, D4 0.040); plateau-set 0.925 (D4 0.88);
  - memory C1 0.955, C2 0.895, C3 1.0;
  - |R| 52.3 (items 400-500: 76.4), |A| 19.8;
  - signed drift -0.050.
- M = 1,000:
  - joint 0.000, median intrusions 1,759; plateau-set 0.160;
  - memory C1 0.925, C2 0.495, C3 0.995;
  - |R| 86 (items 900-1,000: 151);
  - feedback density 0.31;
  - signed drift -0.085.
- The forward store equals P2-E1 at both loads; digests unchanged; my scoring equals P2-E3's `score`.
- Wall time 267 s.
- `~/.cache/brain-sim/review/p2e5-redteam/implementation/fam5.py` (seed 45; as for seed 44: s = 60, loads 500 and 1,000, --plain): Exploratory.
- M = 500: joint 0.100 (D2 0.12, D4 0.01); plateau-set 0.935; C1 0.975, C2 0.910; |R| 50.1 (items 400-500: 72.0); signed drift -0.045.
- M = 1,000: joint 0.000; plateau-set 0.120; C1 0.955, C2 0.470; |R| 87 (items 900-1,000: 163); signed drift -0.114, which exceeds the draft's 0.1 bar.
- New exemplars: nothing at M = 500; at M = 1,000 a median of 244 lines, prototype lines 1.0.
- Forward store equals P2-E1.
- `~/.cache/brain-sim/review/p2e5-redteam/implementation/fam5.py` (seed 44 and 45; s = 80 arm, loads 500 and 1,000): Exploratory.
- M = 500: joint 1.000 / 0.995.
- M = 1,000:
  - joint 0.665 / 0.680 (D2 0.68 / 0.69, D4 0.65 / 0.62);
  - plateau-set 0.940 / 0.935;
  - C2 0.940 / 0.945;
  - |R| 25.5 / 25.9 (items 900-1,000: about 37);
  - intrusions mostly sibling-specific;
  - signed drift -0.052 / -0.101.
- Sibling overlap 5.5-5.7 lines.
- `~/.cache/brain-sim/review/p2e5-redteam/implementation/fam5.py` (seed 44 and 45; s = 40 arm, loads 500 and 1,000): Exploratory.
- M = 500: joint 0.000; plateau-set 0.07 / 0.05; C2 0.17 / 0.15; |R| about 315.
- M = 1,000: joint 0.000; plateau-set 0.000; C1 0.915 / 0.895; C2 0.025; about 3,880 of 4,000 rec lines per cue.
- D3 still 0.98-0.995.
- Signed drift -0.110 / -0.127.
- Wall time about 525 s.
- `~/.cache/brain-sim/review/p2e5-redteam/implementation/fam5.py` (seed 44 and 45; s = 100 (P2-E3's own generator), loads 500 and 1,000): Exploratory. P2-E3 replicates:
- joint 1.000 / 0.985 at M = 500 and 0.980 / 0.980 at M = 1,000;
- plateau-set 0.995 / 0.985;
- C1 0.97 / 0.95, C2 0.995 / 0.975;
- |R| 23.2 / 23.8;
- signed drift -0.045 / -0.088;
- wall time about 145 s.
- `~/.cache/brain-sim/review/p2e5-redteam/implementation/spurious.py` (seed 44; s = 60, M = 500 and 1,000: breakdown of spurious memory responders under the gated half cues (forward store)): Exploratory.
- Spurious cells per cue: 2.9 at M = 500 and 19 at M = 1,000.
- 98-99 % are plateau cells of >= 1 sibling (mean 1.7-1.8).
- Strong synapses from the cue: about 12-13, of which about 9 are prototype lines. Assembly cells get 25 (10 prototype, 15 specific).
- Share of cells in >= 2 siblings of one family: 0.23 at M = 500, 0.59 at M = 1,000.
- `~/.cache/brain-sim/review/p2e5-redteam/implementation/fam5.py (FAM_F=20, --tag _F20)` (seed 44 and 45; s = 60, F = 20 (50 exemplars per family at M = 1,000), load 1,000): Exploratory.
- joint 0.015 / 0.015;
- plateau-set 0.550 / 0.535;
- C2 0.675 / 0.680;
- |R| 61.8 / 61.3;
- signed drift -0.055 / -0.100.

The M = 1,000 index loss is not just family size.
- `~/.cache/brain-sim/review/p2e5-redteam/implementation/fam5.py (--tag _smoke)` (seed 44; s = 60, M = 150, smoke test): Exploratory. The implementation works end to end: forward store equals P2-E1, digests unchanged. Joint 0.787. The D3 field is invalid at M < 200 because of my cue indexing.

## Reviewer's predictions

Predictions for the gated run on seeds 21-25 as drafted, from my exploratory numbers on seeds 44-45:

**s = 60 (gated):**
- M = 500: joint about 0.08-0.17, D1 >= 0.97, D2 about 0.1-0.2, D4 <= 0.05. S1 is borderline (C2 about 0.88-0.92), so S1 may fail on some seeds.
- M = 1,000: joint about 0.00, with a median of about 1,700-1,900 intruding lines. Memory C2 about 0.45-0.55, so S1 fails. C1 0.92-0.96. S3 holds (0.98-1.0).

**Validity:** under the draft's signed-drift rule, at least one gated seed at M = 1,000 most likely exceeds 0.1 mV, about 0.8 or more. If INVALID takes precedence, the record is INVALID rather than FAIL.

**Plateau-set arm:** about 0.92-0.94 at M = 500, with D4 possibly below 0.90; about 0.10-0.20 at M = 1,000.

**Overlap arms:**
- s = 80: about 0.99-1.0 at M = 500, about 0.6-0.75 at M = 1,000, with the plateau-set store about 0.93-0.95 there.
- s = 40: joint 0 at both loads, with C2 about 0.15 at M = 500 and about 0.03 at M = 1,000.
- s = 100: 0.97-1.0, replicating P2-E3.

**Extra cues:**
- New exemplars regenerate nothing at M = 500, and at M = 1,000 a median of about 100-250 lines, mostly prototype lines.
- Prototype half cues light about 800 lines at M = 500 and about 3,500 at M = 1,000.

**Overall:** FAIL on S1 at M = 1,000 (and possibly at M = 500), and on S2 and S4 at both loads.
