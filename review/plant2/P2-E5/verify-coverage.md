# P2-E5 contract verification: coverage

Fresh checker given only the files (revised contract at commit 68148bb). Run 2026-10-11. Recorded verbatim, before synthesis.

## Verdict

No blocker. All 31 red-team findings have a ledger row, and every one shows up in the revised contract at least in substance: the drift bar is withdrawn, C4 is back in S1, and the verdict vector and labels, Parts A-G, the power section, the Decision section, persistence, the guard and the cost are all present. The gate itself is faithful to ruling 1: s = 60 (about 17 %), M = 500 and 1,000, fresh seeds 21-25 (I checked there are no records for them), s = 80 and s = 40 arms, P2-E3's PASS kept and scoped, generalisation left to Stage 3.

Two major problems should be fixed before the contract is frozen:
- **Part D cannot answer the owner's question at M = 1,000.** The reading is a difference in content joint, and the P2-E3-protocol store's joint is already 0 there. So the reading comes out NOT WORSE with certainty, which contradicts the contract's own prediction. At M = 500 the predicted WORSENS has only about a 0.5 chance.
- **The Decision section sends M = 500 to a write mechanism that cannot meet the re-pass rule.** Part B's index loss is about 0 at M = 500, so the routing points to a write mechanism. That mechanism must re-pass P2-E5's gates, but S1 fails on the index alone with probability about 0.999. The index failure at M = 500 is not sent to the owner, and two Part B readings (NO MATERIAL LOSS, NOT ATTRIBUTABLE) have no branch in the Decision section.

The other findings are smaller:
- **Part B and Part C design.** No rule decides the next contract when the two loads give different readings. The three losses are measured at different readout points. At M = 1,000 the plateau-set store is not actually an upper bound: subsets of A(x) such as R_4 and R_6 do better. Part C's "within 0.05" test is two-sided, so an activity-written store that beats the plateau-set store by more than 0.05 would read NOT SHOWN.
- **Arms and controls left undefined.** The online arm's orchestration and validity checks are not pinned, and P2-E4's state_digest reads the item generator's internal state, which a replacement generator may not have. NOT ATTRIBUTABLE is ambiguous. Part G is not defined for the s = 100, pooled and F = 40 arms. The new-exemplar cue is not labelled "not generalisation". The shuffled-feedback check changes P2-E3's rule, and P2-E3 addendum item 8 is not addressed.
- **Partly done but marked "accepted" in the ledger:** completeness C4's online-arm part, implementation M1, methodology M2 and B1, and a few nits.

Every number in the power section is reproduced exactly by `analysis/p2e5_power.py`.

## Findings

### COV-1 [major] Part D (contamination under continuous learning) is floored: at M = 1,000 it reads NOT WORSE whatever happens, and its own predictions contradict its rule

- where: docs/plant2/P2-E5-structured-items.md L341-345 (reading), L470 (prediction); DECISIONS.md addendum (owner: 'In P2-E5, test whether contamination worsens under continuous learning')
- evidence: The reading is Δ = J(online store) - J(P2-E3-protocol store) on twin A's raster. At M = 1,000 the P2-E3-protocol store's joint is 0.000 on both exploration seeds (L45). So Δ = J_online - 0 >= -0.05 on every seed, and the reading is NOT WORSE. Simulated P(NOT WORSE) = 1.000 (~/.cache/brain-sim/review/p2e5-verify/coverage/partD_reading.log). That contradicts L470 ('WORSENS (both near 0) or MIXED'): if both joints are near 0, Δ is about 0. On independent items the same Δ at M = 1,000 was -0.10 / -0.165 (P2-E4 reported_arms, seeds 43 / 42: own store 0.89 / 0.815 against the reference swap 0.99 / 0.98). So at this load the floor, not the system, would pick the label. At M = 500 the exploratory paired Δ is -0.09 on seed 44 and -0.04 on seed 45 (fidelity/where.py: online 0.055 / 0.065 against the P2-E3 protocol's 0.145 / 0.105; both settled rasters gave the same C1 and C2). So the simulated P(WORSENS) is 0.49 and P(MIXED) 0.45, not the confident WORSENS predicted. The intrusions show clear worsening that the joint cannot register: lines only later siblings have average 106.75 / 98.27 online, against 47.9 / 40.0 under P2-E3's protocol. Also, Δ = -0.05 exactly meets both WORSENS (<= -0.05) and NOT WORSE (>= -0.05).
- fix: Base the Part D reading on a statistic that is not floored at these loads. For example: the paired per-cue intrusion count, or Part F's normalised per-class intrusion rates, of the online store against the P2-E3-protocol store on the same twin A raster. Add a floor rule: where the P2-E3-protocol store's joint is below 0.10 on a seed, Δ on the joint is NOT ESTIMABLE. Make the boundary exclusive (WORSENS if Δ < -0.05). Correct L470: at M = 500, WORSENS or MIXED with roughly even odds; at M = 1,000 under the current rule, NOT WORSE by floor.

### COV-2 [major] Decision routing sends the predicted M = 500 outcome to a write mechanism that cannot meet the contract's own re-pass rule; the M = 500 index failure, NO MATERIAL LOSS and NOT ATTRIBUTABLE are routed nowhere

- where: L107-108 and L491 ('Any correction must re-pass the gates of P2-E3, P2-E4 and P2-E5'); L292 (L_i); L300-308; L435-438; L496-503; ruling 4 ('one new mechanism per contract'); 2026-10-11 guidance (two problems, fixed separately)
- evidence: The power section says 'No item-specific write can pass on this index': P(S1 on all five seeds at M = 500) = 0.001 (re-run: 0.0013; oracle store at M = 500 alone: 0.0002). But L_i = max(0, 0.90 - J_ub*) is about 0 at M = 500, because J_ub* is 0.995-1.000. Part B therefore reads CONTAMINATION-DOMINANT with no index loss (re-run: P >= 0.997 for L_o <= 0.25; index-material P = 0), and L497 points to a write mechanism. That mechanism must re-pass P2-E5, which it fails through C2 and C4-spurious with P about 0.999 whatever the write. The same holds for P2-E4's gates, which are predicted to fail on the operating point (P2-E4 power_predictions: P(PASS) 0). So under 'one mechanism per contract' and 'two problems fixed separately', no single correction can satisfy L107-108 or L491. The M = 500 STRUCTURED INDEX FAIL only gets 'reported beside them' (L308). The route to the owner exists only through a material L_i at M = 1,000, and that route disappears if the owner gates M = 500 alone (L220-221 invites this). Part B can also produce NO MATERIAL LOSS or NOT ATTRIBUTABLE, and neither has a branch in the FAIL Decision.
- fix: Send any STRUCTURED INDEX FAIL (C2 or C4-spurious) to the owner before a mechanism contract, or put S1's index shortfall into L_i (for example, L_i = max of 0.90 - J_ub*, 0.90 - C2 rate and 0.90 - C4-spurious rate). Predeclare what a single-mechanism correction must show: the gates its targeted problem controls, with the other failures reported against this record. Otherwise state that the full three-contract re-pass applies to the combined system, and that the owner decides the interim gate. Add Decision branches for NO MATERIAL LOSS and NOT ATTRIBUTABLE.

### COV-3 [minor] Part B gives one reading per load but no rule for the single 'put first' decision when the loads disagree (completeness C1 only partly done)

- where: L297-305, L496-503; 2026-10-11 guidance ('put first whichever failure remains most consequential'); completeness C1 ('Without one, the order of the next contracts would be decided after the fact')
- evidence: Each Decision bullet applies to a per-load reading, and the loads can disagree. The contract's own power table (L447-450, reproduced) gives, at L_o = 0.45: M = 500 SPLIT (0.97) and M = 1,000 CONTAMINATION-DOMINANT (0.79). At L_o = 0.35: M = 500 CONTAMINATION-DOMINANT only 0.57, else SPLIT, while M = 1,000 is CONTAMINATION-DOMINANT at 0.985. Nothing says which reading decides the next contract.
- fix: Predeclare that when the two loads' readings differ, or either is SPLIT, the ranking goes to the owner. Alternatively, name which load governs and why.

### COV-4 [minor] Part B mixes readout conventions: contamination at the grid-best readout, operating point at the frozen readout

- where: L291-293; L444-450
- evidence: L_c = J_ub* - J_own* uses the main store's grid best (0.555-0.565 at M = 500, at g 0.7 or 1.0), so L_c is about 0.44. At the frozen readout, where L_o is measured, L_c would be 0.785-0.84 (plateau-set 0.925-0.94 minus main 0.10-0.145). The convention decides the reading exactly when L_o is large: at L_o 0.45 the contract predicts SPLIT with P 0.97 at M = 500, while L_c at the frozen point would exceed L_o by more than 0.3.
- fix: State why J_own* is taken at its grid best while L_o is not. Report L_c at the frozen point beside it, and either require both conventions to agree on the dominant failure (otherwise SPLIT) or pick one convention for all three losses.

### COV-5 [minor] At M = 1,000 the plateau-set store is not an upper bound for item-specific writes; Part C's two-sided 'within 0.05' can read NOT SHOWN when activity does better

- where: L292 (L_i 'the shortfall that remains even with an item-specific write'), L317-319, L323-324 ('Its ceiling at M = 1,000 is the index-limited upper bound'), L501 ('no feedback-write change can repair it')
- evidence: completeness/rk_44.log, M = 1,000, frozen readout: plateau-set joint 0.160; R_4 0.240 (60 % of A); R_6 0.350 (9 % of A, D2 0.98). Sparser item-specific stores beat the 'upper bound', so the glosses at L292, L323-324 and L501 overstate. Part C's criterion ('within 0.05 of the plateau-set store's') is two-sided: an R_3 store that beat the plateau-set store at its grid best by more than 0.05 would read NOT SHOWN, although activity identified the cells better than the 'bound'.
- fix: Make Part C one-sided: R_3 >= plateau-set - 0.05, at the frozen point and at grid best. Reword L292, L323-324 and L501 to 'the plateau-set store's shortfall'. Report the best R_k at the frozen point beside J_ub*, and optionally put R_4 and R_6 on the grid (a cheap replay).

### COV-6 [minor] Online arm: orchestration, validity and missing-L_o handling unpinned; P2-E4's state_digest needs the injected generator's state (implementation m3 now applies)

- where: L328-339 ('with only the item generator replaced'; 'No habituation copies'); L293, L347; plant2/experiments/p2_e4_online.py:503-510, 936-995, 1000-1029
- evidence: P2-E4's run_seed runs the habituation copies. Its gated validity includes rep1_identical and main_untouched, both taken from those copies, which P2-E5 drops. So the arm needs new orchestration, and the contract does not say which P2-E4 validity checks apply: forward store equal to P2-E1, feedback-store union, slot checks, audit, leak, main untouched by the twins. Nor does it say what a validity failure in the arm does. state_digest hashes `_pat.bit_generator.state` (lines 509-510; used for the twins at 1000-1029), so a stand-in exemplar generator breaks it. Implementation m3 raised this, and its refuter dismissed it only because P2-E4's helper was not reused; the revision now reuses it. Part B also has no rule for when L_o is missing because the online arm crashed or was invalid ('a crash voids only that arm', L522-524).
- fix: Pin the reused pieces: Online.run_to, block_criteria, twin_A with ref_store set to the gated arm's store at the same load, and twin_B. List which P2-E4 validity checks apply. State that a failure invalidates only the online arm and the Part B and Part D readings, and that Part B then reads NOT ATTRIBUTABLE. Require the injected generator to expose a hashable state, or digest the exemplar index instead.

### COV-7 [minor] NOT ATTRIBUTABLE is ambiguous and missing from the power simulation

- where: L297 ('exclusive and exhaustive'), L306-307; analysis/p2e5_power.py ranking()
- evidence: Three things are unspecified. When a seed is excluded, does 'at least 4 of 5 seeds' become 4 of the remaining 4? Is exclusion per load or per seed? And NOT ATTRIBUTABLE is a sixth label outside the list called exclusive and exhaustive. Re-run: P(s = 100 replicates on all five seeds) = 0.856, so P(at least one excluded seed) is about 0.14. ranking() never models exclusion.
- fix: State the denominators after exclusion, say whether exclusion is per load, add NOT ATTRIBUTABLE to the list of labels, and include exclusion in the Part B power numbers.

### COV-8 [minor] Part G and stream 22 are undefined for some of 'all arms on the P2-E3 protocol'

- where: L386; L181 (stream (seed, 22, M): '50 prototype cues (5 per family)'); arm table L163-165
- evidence: The s = 100 arm uses P2-E3's generator and has no families or prototypes (F is '-'). The pooled arm has no sibling structure, so its 'new exemplar' is undefined. F = 40 cannot have 5 prototype cues per family within 50 cues. Stream 22 is not keyed by arm.
- fix: Name the arms that carry Part G (for example main, s = 80, s = 40 and F = 40), give per-arm counts (for F = 40, which 50 prototype cues), and define the pooled arm's new-exemplar draw or exclude that arm.

### COV-9 [minor] New-exemplar cue lacks the 'not generalisation' label and the false-recall split (FID5-7, implementation m1 and methodology m1 only partly done)

- where: L85-87 ('Generalising to a never-seen family member ... Here it is reported'); L388-395; L403-404; L478
- evidence: FID5-7 asked for this statement: 'the new-exemplar cue measures index cross-talk, not generalisation.' Implementation m1 asked to state beforehand that prototype lines regenerated from a new exemplar count as superposition, not generalisation (ruling 5). The ruling-5 label (L403-404) is attached to prototype cues only, while L86-87 says generalisation to a family member 'is reported' here. The new-exemplar prediction is '110-250 lines, mostly prototype lines' (L478), which is just what could later be cited as generalisation. Methodology m1's refuter also asked to split new-exemplar regeneration into prototype lines and sibling-specific (false-recall) lines; L390-395 have no sibling-specific count.
- fix: Add to the new-exemplar bullet: 'not generalisation; prototype lines regenerated from a new exemplar are retrieval-time superposition (ruling 5)'. Reword L86-87 to say that generalisation is not measured here. Add the number of sibling-specific lines each new-exemplar cue regenerates.

### COV-10 [minor] Completeness C4 accepted in full, but its online-arm part is not implemented

- where: review/ledger.jsonl P2-E5-completeness-C4 ('accepted'); redteam-completeness.md C4 rec 1 ('at both loads, and in the online arm, since the responder write depends on the protocol'); contract L312, L326-339
- evidence: Part C is measured on the gated arm only, and Part D lists no spike-count measures. The online rhythm is where count separation is least tested: |R| is 105-111 and the continuation offset 4.39-4.43 mV, against 72-75 and 5.62-5.69 mV under the settled protocol (fidelity/where.py). Any activity-gated write would also have to re-pass P2-E4's online gates.
- fix: Add the count AUC and an R_3 store swap on the online arm's twin A raster (logging only), or append a ledger row marking C4 'accepted in part' with the reason.

### COV-11 [minor] Ledger 'accepted' overstates several findings; graded statistics and diagnostics they promise are absent

- where: review/ledger.jsonl rows implementation-M1, methodology-M2, methodology-B1, methodology-n1, completeness-C3, methodology-M1; DECISIONS.md L509, L538-542; contract L68-71, L171, L362-363, L365-376, L457-479
- evidence: (a) Implementation M1 is marked 'accepted', but DECISIONS rejects its F = 20 arm ('Rejected: An F = 20 arm'). Its spurious-cell breakdown (sibling plateau membership, strong prototype synapses from the cue) is only cited from exploration (L68-71); it is not measured on the gated seeds, even though the index problem now goes to the owner. (b) The methodology M2 row says 'arms added with readings', but F = 40 has no reading (L362-363), and M2's condition 'interpret the overlap dose-response only alongside the pooled control' is absent. (c) The methodology B1 row says 'predictions per load and arm with probabilities', but the table gives probabilities only for S1 (0.001) and validity (0.007); none for Parts C, D or E. (d) Methodology n1's 'paired per-item comparisons' (L171) have no predeclared statistic. (e) Completeness C3 rec 4 (own-store against upper-bound intrusion ratio at M = 1,000) and methodology M1's paired intrusion distributions for the plateau-set store are not specified: Part F covers the main store only. DECISIONS' 'All 31 were accepted, one in part' is therefore inaccurate.
- fix: Append ledger rows (append-only) marking these 'accepted in part' with reasons, and correct the count in DECISIONS by an appended note. Or add the missing items: a reported spurious-cell breakdown at both loads, an F = 40 reading or an explicit 'no reading', probabilities per reading, the paired dose-response statistic, and intrusion distributions for the plateau-set store.

### COV-12 [minor] Validity 5 changes P2-E3's shuffled rule while citing it; P2-E3 addendum item 8 is not addressed

- where: L237-240; docs/plant2/P2-E3-content-completion.md L148 and L568-569; P2-E4-online-memory.md L314
- evidence: P2-E3: 'The shuffled-feedback arm must fail D1/2 at M = 1,000 on every gated seed', with VOID as the outcome. P2-E5 calls its check 'P2-E3's leak check' but makes it 'fail the joint for at least 90 % of the half cues', with INVALID as the outcome. P2-E3 addendum item 8 requires that from P2-E4 on 'at least one gated control could pass if the claim were false'. P2-E4 addressed this explicitly; P2-E5 neither names such a control nor says why none can exist (the shuffled check fails by construction).
- fix: Quote P2-E3's rule unchanged, or label the change and the VOID-to-INVALID move as new. Add P2-E4's statement that no artefact control can fail in this architecture, or name a gated control that could pass.

### COV-13 [nit] Number and wording slips

- where: L55-57; L101-104; L287; L444 and L465-466; L435-437
- evidence: (1) L55-57: 'their number grows ... about 74 for items 400-500, and 150-160 for items 900-1,000'. Those are |R| values. The extra responders number 51.9 / 54.8 for items 401-500, and |R| for items 900-1,000 is 151.4 / 163.3, outside '150-160'. (2) L102: 'the two learning rhythms examined (P2-E3 addendum 2)'. Addendum 2 examined three rhythms (back-to-back, 250 ms, 2 s). The cited numbers come from the P2-E4 red-team's online line (where.py: 'not P2-E4's frozen driver'), not from P2-E4's rhythm. (3) L287: losses are 'fractions of the 200 gated half cues', but L_o is over the online arm's block cues. (4) The grid numbers and J_ub* / J_own* come from seed 44 only (two learning orders), though the header says seeds 44-45. (5) L436: '0.001' multiplies the C2 and C4-spurious probabilities as if independent, but the oldest 100 items are among the 200 half cues, so it is a lower bound (at most about 0.02); the conclusion stands.
- fix: Correct the wording as above.

### COV-14 [nit] Ruling-4 items and the latest owner wording not carried into the Decision

- where: L17-31, L481-482, L496-509; DECISIONS ruling 4; DECISIONS entry after 68148bb ('P(PASS) is 0' wording)
- evidence: The Decision section does not restate that familiarity-gated allocation stays deferred when index cross-talk goes to the owner, or that the error-correcting write's contract must test useful error information and the preservation of unrelated memories. The 'Ordered by the owner' header cites rulings 1 and 4 and the 2026-10-11 guidance, but its item 5 comes from the addendum. L481-482 says 'P(PASS) is 0'; the owner's later wording note asks such statements to give the bound.
- fix: Add one line each: familiarity-gated allocation stays deferred (ruling 4); the error-correcting write's contract tests the two things ruling 4 names. Cite the addendum for item 5. Write 'P(PASS) < 10^-6 (analytic product of the criteria)' instead of '0'.

## Computed (scripts and numbers)

- Re-ran analysis/p2e5_power.py read-only, without --append and with PYTHONDONTWRITEBYTECODE=1 (git status stayed clean). Output: ~/.cache/brain-sim/review/p2e5-verify/coverage/power_ref.json. Every power number in the contract reproduces:
  - idealised 0.856 / 0.789 (P2-E3-only rates);
  - oracle at the frozen readout 0.000, and 0.0002 at M = 500 alone (C2 0.066, C4-spurious 0.020, S2 0.658, S4 0.224);
  - main-arm P(S1 at M = 500) 0.0013;
  - P(INVALID) 0.0067;
  - s = 100 replication 0.856;
  - Part B readings: M = 500 CONTAMINATION-DOMINANT 1.0 / 1.0 / 0.997 / 0.568 / 0.004 for L_o 0.07 / 0.15 / 0.25 / 0.35 / 0.45 (SPLIT 0.973 at 0.45); M = 1,000 0.986-0.987 and 0.786 at L_o 0.45; index loss material with P 1.0 at M = 1,000 and 0 at M = 500.
- Wrote ~/.cache/brain-sim/review/p2e5-verify/coverage/partD_reading.py (log: partD_reading.log; no simulation of the network). It models Part D's reading from the exploratory joints:
  - M = 500: P(WORSENS) 0.494, P(MIXED) 0.450, P(NOT WORSE) 0.056;
  - M = 1,000: P(NOT WORSE) 1.000 (floor);
  - exploratory paired Δ at M = 500: -0.09 (seed 44) and -0.04 (seed 45).
- From bench/results/plant2.jsonl (P2-E4 reported_arms, seeds 42-43):
  - twin B net online index loss 0.065-0.07 at M = 500 and 0.16-0.26 at M = 1,000 (matches the contract);
  - twin A, independent items at M = 1,000: own store 0.89 / 0.815 against the reference swap 0.99 / 0.98, a Δ of -0.10 / -0.165.
- Seeds 21-25 have no records.
- Read the existing red-team outputs (no new simulation):
  - completeness/rk_44.log: at M = 1,000 the frozen-point joints are plateau-set 0.160, R_3 0.165, R_4 0.240, R_6 0.350;
  - grid_44_*.log;
  - fidelity/where_online_*.json: lines only later siblings have average 106.75 / 98.27 online, against 47.9 / 40.0 under P2-E3's protocol.
- Checked against code in plant2/experiments/p2_e4_online.py: Online.learn_one draws items with _pat.choice (L247); novel items come from separate streams, so replacing the item generator does not change novel cues; state_digest hashes _pat.bit_generator.state (L503-510); run_seed's validity depends on the habituation copies (L936-995).
- Checked all 31 ledger rows of 'P2-E5 draft red-team' against the four red-team files and the contract.
- The contract is unchanged between 68148bb and HEAD 09962a4; only DECISIONS.md and HANDOFF.md changed.
