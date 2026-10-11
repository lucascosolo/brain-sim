# P2-E5 contract verification: ambiguity

Fresh checker given only the files (revised contract at commit 68148bb). Run 2026-10-11. Recorded verbatim, before synthesis.

## Verdict

The contract can be implemented on the existing code. Every hook it needs exists: `_pat` injection works in E1, E3 and P2-E4's Online; e3.readout takes any J/g arrays and scores D3, D4 and `passes` per arm; twin_A(S, M, ref_store) accepts the gated arm's BinarySynapses store; and L_o can be derived from twin_B's McNemar aggregates. Two places should be fixed before freezing because each can move a gated number or a predeclared reading:
- **(1) "Best joint over the grid" has two incompatible definitions.** The contract text says the maximum joint, but the power reference used the joint at the argmax of min(joint, D3, D4). On the exploration grids the two differ by up to 0.045, against a 0.05 dominance margin in Part B.
- **(2) Nothing checks that the gated arm's feedback write is still P2-E3's.** Counts and the learning raster must be captured inside learn_one, and the R_1 check is self-referential.

Several minor pins remain:
- stream and generator details (sorted versus draw-order prototypes give 0 % identical items);
- Part G for F = 40, pooled and s = 100;
- Part B with missing or excluded arms;
- Part C's AUC population and the sidedness of "within 0.05";
- Part D's overlapping labels and floor;
- float comparisons at exact 0.05 boundaries;
- which P2-E4 validity checks apply to the online arm;
- the Part F own-cell share definition;
- the undefined "dose-response".

**The cost line is realistic, with margin.** About 45-55 min per seed is estimated against the contract's 1-1.5 h. Persistence is a few MB per seed.

## Findings

### IMP-1 [major] 'Best joint over the grid' (J_own*, J_ub*, Part C's grid best) is ambiguous; the contract text and the power reference use different definitions

- where: docs/plant2/P2-E5-structured-items.md lines 279, 282-283, 291-292, 318-319; analysis/p2e5_power.py line 91
- evidence: Contract l.279: 'the best joint over the grid'; l.282: 'J_ub* is the plateau-set store's best grid joint'. The natural reading is max(joint) over the 72 points. The power reference instead uses J_own* = 0.56 at M = 500 and 0.025 at M = 1,000. That is the mean of the joint at argmax min(joint, D3, D4), the rule in the red-team's grid.py ('best = max(..., key=lambda a: min(a["joint"], a["D3"], a["D4"]))'). Recomputed from grid_s60_seed44_{cyclic,random}.json (script grid_best.py). For the main store:
- M = 500: max joint is 0.565 / 0.600, against 0.565 / 0.555 under the min rule;
- M = 1,000: max joint is 0.040 / 0.065, against 0.025 / 0.025.
The plateau-set store gives the same value under both rules (1.000 / 0.995 and 0.600 / 0.585). So L_c at M = 500 is 0.415 under the text's definition and 0.4375 under the power's. With L_o around 0.35, the seed-level gap L_c - L_o moves from about 0.09 to about 0.065, against the 0.05 dominance margin. The power table's 'P = 0.57 (else SPLIT)' column and Part C's 'within 0.05 ... at each store's grid best' both depend on which definition is used. The choice can be made after seeing seeds 44-45, where the two already differ.
- fix: Replace l.279 with: 'the best joint: the maximum of the S2 fraction (joint) over the 72 points, with no condition on D3 or D4. The record also gives (J_fb, g) of the first maximum in grid order (J_fb ascending, then g ascending) and D1-D4 there.' Use the same definition for J_own*, J_ub* and Part C's 'grid best'. Before appending the power_reference record, recompute `best` in analysis/p2e5_power.py with it (from the exploration grids: J_own* is about 0.58 at M = 500 and about 0.05 at M = 1,000). Alternatively, adopt P2-E3's calibration rule (the joint at argmax min(joint, D3, D4), ties to the first grid point) explicitly in the text. Either way, the text and the power script must agree.

### IMP-2 [major] The gated arm's feedback write is not validity-checked against P2-E3. Logging counts and the learning raster requires touching learn_one, and the R_1 check is self-referential

- where: Contract lines 125-131 ('Everything is P2-E3 exactly'), 225-226 (Validity 1), 271-272 (R_1 bit-identity), 408-413 (Persistence); plant2/experiments/p2_e3_completion.py:76-85
- evidence: E3.learn_one keeps only a boolean `responded` over the 50 continuation steps (p2_e3_completion.py:77-79) and no learning raster. Part A and C's counts and the persisted learning raster therefore need either a copied learn_one, as the red-team's rk.py E3log did, or a hook.

Validity 1 checks only the forward store against plain P2-E1, so it catches changes to encoding, not to the continuation or the write. 'R_1 ... bit-identity is a validity check of the logging' compares the counts with R produced in the same loop. A slip in a copied continuation would change fb, and hence S2 and S4, while every listed check still passed. Examples: an extra draw from the CONT stream, a different key, a quiet(), or writing before the loop ends.

The R_1 check is also not among Validity 1-6, so whether a failure makes the run INVALID is undefined.
- fix: Add to Items/Pins: 'The P2-E3-protocol arms are e3.E3 with learn_one not overridden. The subclass's learn_one temporarily sets self.net.step to a read-only wrapper that appends each step's mem spikes (no draws, no state change), calls super().learn_one(), then deletes the wrapper before returning, so that deep copies never carry it. The learning raster, the continuation counts and the first-spike ticks are derived from the captured steps; the continuation is the last t_cont calls.'

Add Validity 7, on every gated seed at both loads:
- R(x) equals the cells with at least 1 captured continuation spike, for every x;
- the feedback store equals the union of R(x) x E(x) (P2-E4's fb_union_ok);
- the R_1 store's sha256 equals the main store's.

If learn_one is instead copied statement for statement, Validity 7 is: the fb, fb_plateau, R and E digests equal those of unmodified e3.E3 on the same injected items, at both loads. That costs one extra learning line, about 85 s per seed (measured).

### IMP-3 [minor] Part B's inputs are not fully defined: the L_o population, handling of a missing or invalid online or s = 100 arm, the exclusion load, and the sign of L_c

- where: Contract lines 287-293, 306-307, 520-524; p2_e4_online.py twin_B (lines ~771-808); analysis/p2e5_power.py line 101
- evidence: - **L_o population.** l.287 says the three losses are 'fractions of the 200 gated half cues', but l.293 takes L_o from the online arm's own block half cues: twin_B(...)['all'], with 50 recent, 50 uniform and 100 cohort cues, n = 200. twin_B returns only aggregates, but L_o follows from them: L_o = (mcnemar[1] - mcnemar[0]) / n = settled - online. On P2-E4's exploration records this gives 0.065 / 0.07 for memory at M = 500 and 0.16 / 0.26 at M = 1,000; for content it gives 0.005 / 0.0 at M = 500 and -0.115 / -0.07 at M = 1,000. These reproduce the contract's 'net online index loss'.
- **Missing online arm.** l.523 lets a crash void only that arm. Nothing says what L_o, and so the seed's dominance, is when the online arm is void or fails its validity checks.
- **Exclusion load.** l.306 excludes seeds where s = 100 'fails P2-E3's gate' without saying whether a failure at one load excludes the seed at that load only or at both. The s = 100 arm's own validity (convergence, the forward-store check) is unstated.
- **Sign of L_c.** L_c is unclipped in the contract but clipped with np.maximum(0, ub - own) in the power script.
- fix: Replace the L_o row with: 'L_o = max(memory_settled - memory_online, content_settled - content_online) from twin_B(...)["all"] of the online arm at that load (n = 200 block half cues: recent, uniform and cohort).'

Change the section header to: 'three losses per seed and load (L_c and L_i on the gated arm's 200 half cues; L_o on the online arm's 200 block half cues)'.

Add:
- 'L_c = max(0, J_ub* - J_own*).'
- 'A seed whose online arm is void or invalid has L_o missing and is NOT ATTRIBUTABLE at that load.'
- 'A seed is NOT ATTRIBUTABLE at a load if the s = 100 arm fails P2-E3's gate (D1/2, D3, D4, C1-C4) at that load or fails its validity checks 1-4 there.'

### IMP-4 [minor] Boundary comparisons at exactly 0.05 or 0.10 come out arbitrarily in floating point

- where: Contract lines 295, 300, 303, 318, 343-344 (dominance margin, 'below 0.05', 'at least 0.10', 'within 0.05', Δ <= / >= -0.05)
- evidence: Every joint is k/200, so differences of exactly 0.05 (10 cues) are attainable. Computed with float_gap.py:
- 99 of 191 single differences equal to exactly 10/200 fail `>= 0.05` in float;
- 1,216 of 2,559 composite gaps L_c - L_o (four k/200 terms) equal to exactly 10 cues fail it.
For example, (1.0 - 0.56) - 0.39 = 0.04999999999999993. The power script makes the same raw float comparison (`srt[...,-1] - srt[...,-2] >= 0.05`).
- fix: Add under 'Reported arms and readings': 'Every threshold on fractions of 200 cues is applied to integer cue counts, where a fraction f is round(200 f). "Exceeds by at least 0.05" means at least 10 cues; "at least 0.10" means at least 20; "Δ <= -0.05" means at least 10 cues fewer.' Apply the same rule in analysis/p2e5_power.py.

### IMP-5 [minor] Part D's labels overlap at Δ = -0.05, the reading has an undeclared floor, and the M = 1,000 prediction contradicts the rule

- where: Contract lines 341-345 and 470
- evidence: WORSENS is 'Δ <= -0.05' and NOT WORSE is 'Δ >= -0.05'. A seed with Δ of exactly -0.050, which is attainable on the k/200 grid, counts for both, so the labels are not exclusive.

l.470 predicts 'WORSENS (both near 0) or MIXED' at M = 1,000. But if both twin-A joints are near 0, Δ is about 0, which is >= -0.05, so the rule yields NOT WORSE. The P2-E3-protocol store's joint at M = 1,000 was 0.000 on both exploration seeds (and on seed 90 in my probe). The reading cannot detect worsening at a floor.
- fix: Use NOT WORSE: Δ > -0.05 on at least 4 of 5 seeds (in integer cues, per IMP-4).

Add a third label: 'AT FLOOR: J(P2-E3-protocol store) < 0.05 on at least 2 seeds at that load. The reading is then not estimable from the joint, and the per-cue median intrusions of the two stores on the same twin-A raster are reported instead.'

Correct the M = 1,000 prediction to AT FLOOR.

### IMP-6 [minor] Part C's AUC population and comparison are unpinned

- where: Contract lines 312-320
- evidence: The contract leaves three things unstated:
- whether the AUC pools all (cell, episode) pairs or averages per-item AUCs;
- which arm it uses;
- whether 'within 0.05 of the plateau-set store's' is one-sided or two-sided.

The red-team's rk.py pooled all pairs over items range(M-200, M), which is 1-based (M-200, M]. Its counts are int16 over the 50 continuation loop steps, with the first spike at the loop index, and the AUC is P(a > b) + 0.5 P(a = b). The completeness critic's recommendation spoke of 'per-item' distributions (redteam-completeness.md l.96).

Activity-gated stores can beat the plateau-set store. On seed 44 at M = 1,000 at the frozen point, R_4 scores 0.240 and R_6 0.350 against the plateau-set's 0.160. So a two-sided rule could return NOT SHOWN because the activity store is better.
- fix: Use this wording: 'Gated arm (s = 60, F = 10). For each item x in (M - 200, M] (1-based), the positives are the cells of R(x) ∩ A(x) and the negatives the cells of R(x) \\ A(x). A cell's count is its number of spikes in the 50 continuation steps (loop index t = 0..49), and its first-spike tick is the first such t. The AUC is computed once over all positive-negative pairs pooled across the 200 items: P(count_pos > count_neg) + 0.5 P(=). The comparison is one-sided: J(R_3) >= J(plateau-set) - 0.05, at the frozen point and at each store's grid best (IMP-1).'

### IMP-7 [minor] Stream and generator construction is not fully pinned, and plausible readings give different gated items

- where: Contract lines 177-181
- evidence: - **Prototype order.** 'a choice of 100 of 4,000 lines' does not say whether the prototype is sorted before exemplar k permutes 'its prototype's 100 lines'. With gen_check.py on seeds 90-92, sorted and draw-order prototypes give 0 % identical exemplars, though the overlap statistics are the same (16.92).
- **Unstated draws.** The contract does not state:
  - the mask draw (index draw into the sorted exemplar?);
  - the family of prototype cue j (j mod 10 or j // 5);
  - the cue order inside the block;
  - the pooled draw method (choice from sorted U, then choice from the sorted complement);
  - the derangement algorithm for pi.
- **The block's input spikes.** '(its own present() stream)' conflicts with 'in this order' under the same key.
- **Keys.** The keys are compatible with e1.stream(seed, sid, *extra), which calls default_rng([seed, sid, ...]). But SeedSequence pads with zeros: default_rng([44,21,10]) == default_rng([44,21,10,0]) is True (verified). So k must stay 1-based, or exemplar 0 would alias the key (seed, 21, F).
- fix: Replace the table cells with code-level pins:
- **(seed, 20, F):** for f = 0..F-1, P_f = np.sort(r.choice(4000, 100, replace=False)).
- **(seed, 21, F, k), k >= 1 (k = 0 is forbidden because it aliases (seed, 21, F)):** f = k mod F; pp = r.permutation(P_f); po = r.permutation(np.setdiff1d(np.arange(4000), P_f)); exemplar = np.sort(concat(pp[:100-s], po[:s])).
- **(seed, 23, k):** U = np.unique(concat(P_0..P_9)); d = r.choice(U, 100-s, replace=False); pool = np.setdiff1d(np.arange(4000), np.union1d(P_(k mod 10), d)); exemplar = np.sort(concat(d, r.choice(pool, s, replace=False))).
- **(seed, 22, M), one generator used in order:**
  - for j = 0..99, exemplar j of family j mod F, drawn as for (seed, 21);
  - for each, a mask np.sort(r.choice(100, 50, replace=False)) indexing the sorted exemplar;
  - for j = 0..49, prototype cue j of family j mod 10 with a mask drawn the same way;
  - then the same generator is passed to present(), with the 100 new-exemplar cues in draw order followed by the 50 prototype cues.
- **(seed, 24, M):** for f = 0..F-1 in order, p = r.permutation(idx_f), redrawn until there is no fixed point (as in the red-team's fam5.py).

### IMP-8 [minor] The reported cue block and Part G are undefined for the F = 40, pooled and s = 100 arms

- where: Contract lines 180 and 386-404
- evidence: Part G applies to 'all arms on the P2-E3 protocol'. But:
- **F = 40.** '50 prototype cues (5 per family)' gives 200 cues, not 50.
- **s = 100.** This arm uses P2-E3's own generator and has no prototypes or families.
- **Pooled.** Its items have no family prototype share, so the generator for 'new exemplars (as above)' is undefined.
- **Truncation.** The contract does not say that the gated readout uses the raster truncated at the end of the gated present() calls. The dictionary returned by run_phase keeps filling during the block. Gated criteria are identical either way, but out_of_window_spikes_per_cue changes.
- fix: Add:
- 'The reported block of the pooled and s = 100 arms is the gated arm's block (F = 10, s = 60 cues from (seed, 22, M)), presented to that arm's network.'
- 'For F = 40: 100 new exemplars of families j mod 40 and 50 prototype cues of families j mod 40.'
- 'Gated readouts use run_phase's n_ticks and onsets, that is, the raster truncated before the block. The persisted test raster is the full raster, with n_ticks_gated recorded.'

### IMP-9 [minor] The contract does not say which P2-E4 validity checks apply to the online arm; P2-E4's helpers fail with the injected generator

- where: Contract lines 328-339; p2_e4_online.py p2e1_digests (~line 935), state_digest (~line 503), run_seed validity keys
- evidence: Online.learn_one draws items through self._pat, and Schedule is indices only. Novel cues come from stream (seed, 17, k) and stay independent. Pseudo-targets are learned exemplars, used only as leak baselines. So injecting the generator works.

Three helpers do not work with it unchanged:
- p2e1_digests builds e1.E1 with its own _pat (independent items), so reusing it gives fwd_equals_p2e1 = False.
- state_digest reads _pat.bit_generator.state, so a duck-typed generator raises AttributeError.
- 'No habituation copies' leaves main_untouched and rep1_identical undefined.

The contract also does not say whether leak_ok, audit_ok, slot_checks_ok and fb_union_ok are recorded, or what a failure does to Part D and L_o.
- fix: Add to Part D: 'The online arm records P2-E4's validity checks, excluding those that need habituation:
- fwd_equals_p2e1, against a plain E1 with the same injected generator;
- elig_ok and mean_A_ok;
- fb_union_ok, slot_checks_ok, audit_ok and leak_ok.
If any fails at a load, that load's Part D Δ and L_o are void on that seed (see IMP-3). The injected generator exposes a bit_generator attribute, or the driver does not call state_digest. The online arm uses e4.CONTRACT unchanged.'

### IMP-10 [minor] Part F's own-cell share is defined differently from the exploration that predicts it, and its aggregation is unstated

- where: Contract lines 376-378 and 476; ~/.cache/brain-sim/review/p2e5-redteam/fidelity/where.py lines 236-249
- evidence: The contract defines the share as 'the fraction of feedback inputs from memory cells that spiked at least 1 tick before the line's first spike and belong to A(x)'. That is a timing-conditioned candidate rule like P2-E4's diagnosis. The predicted 'about 0.93' and 'about 0.6' come from where.py, which:
- counts fb synapses from R50 ∩ A(x) against R50 \\ A(x) onto intrusion lines;
- applies no timing condition;
- takes the median over cues.
Whether the denominator counts synapses or lines, whether 'spiked' means in the 75 ms window, and whether to take the mean or median are all unstated.
- fix: Pin one rule:
- For each half cue and each intrusion line j, the candidate synapses are fb synapses i -> j whose memory cell i's first spike in [onset, onset + 75) comes at least 1 tick before j's first spike (as in analysis/p2e4_diagnosis.py).
- The own-cell share is the number of candidate synapses with i in A(x) divided by all candidate synapses, pooled over the cue's intrusion lines.
- Report the median and the mean over cues with intrusions.
Re-derive the prediction with this rule, or label the 0.93 as coming from where.py's rule.

### IMP-11 [minor] 'The dose-response uses paired per-item comparisons' names an analysis that is defined nowhere

- where: Contract lines 170-171
- evidence: No section defines a dose-response statistic: not which arms (s = 80/60/40), which per-item outcome, or which test. That leaves an unspecified reported analysis open to post-hoc choice.
- fix: Either drop the clause, or define it: 'Dose-response (reported): per-item joint at M = 500 and 1,000 for s = 80, 60 and 40 on the same item indices (A identical), with exact McNemar counts for 80 against 60 and 60 against 40, over the 200 gated half cues.'

### IMP-12 [minor] Validity 2 does not say which object's digests are compared, so the meaningful P2-E3 check can be skipped

- where: Contract lines 227-228; p2_e3_completion.py:349-351
- evidence: 'The forward store, the feedback store and vbar are bit-identical before and after every test copy.' vbar necessarily changes on the copy (the settle), so the sentence can only mean the main line, which is trivially untouched because the test runs on a deep copy. P2-E3's check compares the copy's forward and feedback stores before and after run_phase. That is the check that would catch a write during the test, which would corrupt the raster and the readout.
- fix: Use this wording: '(a) On each test copy, the forward and feedback stores are bit-identical before the settle and after the last present() call, including the reported block (P2-E3's stores_unchanged_by_tests). (b) The main line's forward store, feedback store and vbar are bit-identical before the copy is made and after its test.'

### IMP-13 [nit] Validity 5 is worded differently from P2-E3's rule and cannot fail here; Validity 6's pairs are not named

- where: Contract lines 237-241; P2-E3 contract line 148; p2_e3_completion.py:384
- evidence: **Validity 5.** P2-E3's rule is 'must fail D1/2', meaning shuffled joint < 0.90 (void_ok in the code). P2-E5 says 'fail the joint for at least 90 % of the half cues', meaning joint <= 0.10. That is a different and stricter rule, and the contract still calls it 'P2-E3's leak check'. At s = 60 and M = 1,000 the feedback density is 0.321 (my seed-90 probe), above g = 0.3. P2-E3's rationale ('each responder reaches about 13 % of lines, below g') no longer holds, but the shuffled store still fails through massive intrusions, so the check is vacuous.

**Validity 6.** Realised mean sibling overlap at s = 60 is:
- 16.92 over all 49,500 within-family pairs of items 1-1,000;
- 16.87-17.04 over consecutive siblings (seeds 90-92, gen_check.py).
It cannot leave 15-19 under any pair definition, but the pairs are not named.
- fix: For Validity 5, write 'shuffled joint < 0.90 at M = 1,000 (P2-E3's rule), labelled a leak check that cannot fail on this distribution'. Or keep the stricter bar and drop 'P2-E3's'.

For Validity 6, write 'mean |x ∩ y| over all within-family pairs among items 1-1,000 of the gated arm'.

## Computed (scripts and numbers)

All my scripts and outputs are under ~/.cache/brain-sim/review/p2e5-verify/implementation/. Nothing in the repository was touched.

**grid_best.py** (read-only, on the red-team's grid_s60_seed44_{cyclic,random}.json). It compares the max joint with the joint at argmax min(joint, D3, D4).
- Main store, M = 500: 0.565 / 0.600 against 0.565 / 0.555.
- Main store, M = 1,000: 0.040 / 0.065 against 0.025 / 0.025.
- Plateau-set store: identical under both rules (1.000 / 0.995 and 0.600 / 0.585).
- The power script's J_own* (0.56, 0.025) matches the min rule, not the contract text.

**gen_check.py** (the contract's generator only, seeds 90-92, no network).
- Mean sibling overlap: 16.92 over all within-family pairs, 16.87-17.04 over consecutive siblings.
- Sorted and draw-order prototypes give 0 % identical items.
- Pooled control: |U| is 897-908; overlap with item k-10 is 3.77-3.79, with item k-1 3.66-3.76.
- default_rng([44,21,10]) == default_rng([44,21,10,0]) is True (SeedSequence zero padding).

**float_gap.py.** Of single differences equal to exactly 10/200, 99 of 191 fail '>= 0.05' in float. Of composite four-term gaps of exactly 10 cues, 1,216 of 2,559 fail.

**trace_cost.py** (one simulation; seed 90, s = 60, M = 1,000, unmodified e3.E3 with the contract's generator; two P2-E4 lanes running). Output in trace_cost_seed90_M1000.json:
- learning 0 to 1,000: 85.5 s; run_phase at M = 1,000: 22.4 s; one frozen-point readout: 8.6 s;
- trace replay: 12.5 s, 11,142,558 rec spikes, RSS 272 to 1,399 MB;
- feedback density 0.321, C2 0.49, joint 0.000, median intrusions 2,080.5;
- test raster: 274,790 memory spikes over 180,600 ticks; encoding spikes during learning: 246,821.

**L_o from P2-E4's exploration twin_B aggregates**, as (mcnemar[1] - mcnemar[0]) / n:
- memory: 0.065 / 0.07 at M = 500, 0.16 / 0.26 at M = 1,000;
- content: 0.005 / 0.0 at M = 500, -0.115 / -0.07 at M = 1,000.
twin_B exposes only aggregates, but they are sufficient.

**Persistence.** At M = 1,000 the learning and test memory rasters are about 0.4 M and 0.3 M spikes, roughly 2-3 MB raw each. E, A, R and the counts are trivial. Disk has 30 GB free, and no cache budget is stated anywhere, so this fits.

**Cost per seed at m = n = 4,000** (red-team wall times were measured under 4 or more concurrent processes):

| part | measured inputs | estimate |
|---|---|---|
| gated arm | fam5 s = 60: 266-267 s, including the plain-E1 check, three store replays and the 150-cue block | about 5 min |
| grids (three stores, two loads) | grid.py: 55-90 s per 72-point store at M = 500, 125-136 s at M = 1,000 | about 10-11 min |
| R_k, Part F trace and Part G extras | | about 3-4 min |
| five P2-E3-protocol arms | s = 100: 145 s; s = 80: 172-174 s; s = 40: 523-529 s; pooled and F = 40: about 120-160 s each | about 20 min |
| online arm (not measured on structured items) | P2-E4's driver on independent items: 157-203 s to M = 1,000, plus 54-65 s of twins per load; feedback store about 2.4 times denser here | about 6-12 min |

Total: about 45-55 min per seed. The contract's '1-1.5 h unloaded, about 2 h contended, about 5 h for five seeds in two lanes' is realistic, with margin. Peak RAM is about 1.5-2.5 GB per lane, dominated by the trace lists of twin_A and Part F at M = 1,000 (about 1.1 GB each). That fits in 15 GB with two lanes.
