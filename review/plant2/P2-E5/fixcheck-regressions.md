# P2-E5 contract fix-check: regressions

Fresh checker given only the files (second revision at commit 3c78f03). Run 2026-10-11. Recorded verbatim, before synthesis.

## Verdict

The contract can be frozen once two majors are fixed. Neither needs a gated re-design; both are wording or reading-rule fixes plus prediction rows. There is no blocker. Every number in the Power section reproduces exactly from analysis/p2e5_power.py, run read-only. Every grid, R_k, spurious-cell and intrusion figure I checked matches the exploratory outputs. The Part B, C and D rules are exclusive and exhaustive as written.

The read-only step wrapper works on both e3.E3.learn_one and P2-E4's Online.learn_one. I tested both on seed 44: stores, R lists, vbar and P2-E4 state digests came out bit-identical to the unmodified code. Each episode has exactly 250 net.step calls, and R(x) equals the cells with at least one capture in the last 50. Deep copies carry no step override.

The twin-A cue set, the Part D ratio's population, the R_k grid, the reported block per arm and the spurious-cell rule are pinned well enough.

The majors:
- **Operating-point framing.** The contract says the settled-protocol failures do not depend on the operating point (Scope), and that the M = 500 index failure is a "third problem outside the owner's two". P2-E4's frozen driver on the contract's own items contradicts this.
- **Pooled-control reading.** At M = 1,000 the reading is fixed in advance to LINE-LOAD-LIMITED, although the correlated arm is far worse than the pooled one.

The minors cover:
- the M = 500 Part B prediction, which sits on the CD/SPLIT boundary at the measured L_o;
- the Decision's plateau-eligibility candidate and its operating-point branch, against the owner's guidance;
- void and validity handling in the reported arms.

The nits are wording and record-keeping.

## Findings

### R1 [major] Scope and Why say the settled-protocol failures do not depend on the operating point; P2-E4's frozen driver on the contract's own items shows the M = 500 C2 failure and most of the S2 shortfall move with it

- where: docs/plant2/P2-E5-structured-items.md L84-86 (Why: index cross-talk 'a third problem outside the owner's two named problems'), L118-122 (Scope: 'The settled protocol was the more favourable of the two ... A FAIL is not an artefact of a hostile operating point'), L352-361 (Part B: L_o net and clipped at 0), L435-436 (Part D reports), L576-601 (Predictions: no online-block or twin-B row)
- evidence: I ran P2-E4's frozen Online and twin_A/twin_B with the contract's generator: stream (seed, 20, 10) for prototypes and (seed, 21, 10, k) for exemplars, s = 60, M = 500. Seeds 44 and 45, read-only (partd_probe.py).

Twin B is paired: same online-written store, same 200 block half cues. Content online against settled:
- seed 44: 0.525 against 0.055 (McNemar 97 against 3);
- seed 45: 0.58 against 0.035 (109 against 0).

The online block's C2 is 1.0 on both seeds. Settled C2 is 0.90 / 0.945 in twin A, and 0.895 / 0.91 in the gated arm's exploration. The threshold offset is 3.70 / 3.80 mV online against 1.86 / 1.92 mV settled.

The online operating point fails differently: C1 is 0.82 / 0.77 and the joint is 0.525 / 0.58. So 'a FAIL' holds at both points, but the stated reason ('the settled protocol was the more favourable') is false for retrieval. At M = 500 the C2 deficit vanishes online, so it is not cleanly 'outside the owner's two named problems'. It is the owner's encoding-retrieval trade-off (DECISIONS 2026-10-11).

Part B's L_o counts only losses (memory 29 / 37 cues), so the 94-109 cue content gain online cannot show up in the ranking. No prediction row anticipates any of these numbers.
- fix: **Scope.** Replace L121-122 with: 'The settled protocol gives the cleaner write (fewer continuation responders), not the cleaner retrieval. On P2-E4's frozen driver (exploratory, seeds 44-45, M = 500) the online operating point read the same online-written store at content 0.525-0.58 and C2 1.0, against 0.035-0.055 and about 0.90-0.95 after the settle, while C1 fell to 0.77-0.82. A FAIL holds at both operating points explored, but which criteria fail depends on the operating point.'

**Why.** At L85-86 qualify 'third problem' as 'at M = 500 entangled with the operating point (online C2 1.0); at M = 1,000 unexplored'.

**Part B Conventions.** Add: 'L_o counts losses only; twin B's signed content and memory discordance is reported beside it.'

**Predictions.** Add rows for the online block (C1, C2, joint, cohort) and twin B at M = 500, labelled exploratory frozen-driver values.

### R2 [major] The pooled-control reading has no outcome for 'line load fails S2 and correlation makes it worse'; at M = 1,000 it is fixed in advance to LINE-LOAD-LIMITED against the paired evidence

- where: L445-451 (Part E pooled reading), L594 (prediction 'LINE-LOAD-LIMITED'), L166-171 (Confounds: the pooled arm is to 'separate' correlation from line load)
- evidence: The rule depends only on whether the pooled arm passes S2. At M = 1,000 the main arm fails S2 at floor, so the only possible labels are LINE-LOAD-LIMITED or MIXED.

Exploration at M = 1,000, seed 45 (methodology s60_pooled.jsonl against s60_F10.jsonl):

| measure | pooled | main |
|---|---|---|
| joint | 0.10 | 0.00 |
| plateau-set joint | 0.49 | 0.155 |
| C2 | 0.775 | 0.465 |

Correlation more than doubles the index deficit and cuts the plateau-set joint threefold. Yet the label will read 'line-load-limited', and 'the overlap dose-response is read only beside this control'. That contradicts the contract's own diagnosis that the M = 1,000 failure is sibling cross-talk: 98 % of spurious cells are sibling plateau cells, and 99.7 % of extra responders are earlier siblings.
- fix: Make the reading compare the two arms on a measure that is not at floor, per seed and load, in cues:
- **CORRELATION-ATTRIBUTABLE:** the pooled arm passes S2 on at least 4 seeds while main fails.
- **LINE LOAD SUFFICIENT, CORRELATION WORSENS:** the pooled arm fails S2, and on at least 4 seeds it beats main by at least 20 cues on the plateau-set joint or on the C2 count.
- **LINE-LOAD-LIMITED:** the pooled arm fails S2 and is within 10 cues of main on both measures, on at least 4 seeds.
- **MIXED:** otherwise.

Correct the M = 1,000 prediction accordingly.

### R3 [minor] Part B's M = 500 prediction is conditional on L_o, which is measurable; measured, it falls on the CONTAMINATION-DOMINANT/SPLIT boundary

- where: L562-569 (Power: 'L_o on structured items is unmeasured, so it is given as scenarios'), L589 (prediction: 'CONTAMINATION-DOMINANT if the structured L_o stays at or below about 0.15')
- evidence: P2-E4's frozen driver gives L_o at M = 500 of 29 cues (seed 44) and 37 cues (seed 45), from twin_B['all'] memory discordance: 33-4 and 44-7. Content is clipped (-94, -109). It ran in about 2.5 min per seed.

Paired with each seed's grid L_c (180 - 113 = 67 and 180 - 135 = 45):
- seed 44 reads CONTAMINATION-DOMINANT;
- seed 45 reads no dominance (45 - 37 = 8 < 10).

The power script's ranking() at L_o 0.145 / 0.165 / 0.185 gives P(CONTAMINATION-DOMINANT) of 0.96 / 0.87 / 0.71. The rest is SPLIT.
- fix: Before running --append:
- add the measured exploratory L_o (0.145, 0.185) to analysis/p2e5_power.py as a scenario row;
- state in the Power section that one of the two exploration seeds already reads no dominance;
- change the M = 500 Part B prediction to 'CONTAMINATION-DOMINANT (about 0.7-0.95) or SPLIT; the measured L_o is 0.145-0.185'.

### R4 [minor] The Decision lists the owner's plateau-eligibility hypothesis as a write candidate, which in this model is the A(x) store it forbids; its operating-point branch drops the owner's caution

- where: L626-634 (candidates; 'Where Part B reads OPERATING-POINT-DOMINANT ... the operating-point problem is the candidate'), L637-641 ('no correction may read A(x)'; plateau-set 'not a target or a solution'); DECISIONS.md 2026-10-11 entries
- evidence: Plateaus here are experimenter-assigned and content-blind (L127-128: 'The key. Plateaus are random and content-blind'). DECISIONS' own note says a plateau-trace-gated write 'in the current model ... reproduces the assigned-assembly store exactly'.

The owner: 'The eventual mechanism must derive eligibility locally, not receive the assembly from the experimenter.' The owner also 'advises against trying [a threshold adjustment alone] as the fix'.

The operating-point branch carries no such caveat. Finding R1 shows the operating point trades C1 against C2 and content on these items, which is exactly the owner's trade-off.
- fix: After the plateau-eligibility bullet, add: 'in the current model a plateau-event eligibility equals A(x) x E(x), so it is admissible only together with a non-experimenter plateau key, which is a separate mechanism under ruling 4'.

To the operating-point branch, add: 'not a threshold or accommodation adjustment alone (owner, 2026-10-11)'.

### R5 [minor] Reported arms: validity checks unnamed for s = 80, s = 40, pooled and F = 40; no void-seed rule for the s = 100 and pooled readings; 'while main fails' undefined; dose-response inputs not recorded

- where: L313-315 ('fails its own validity checks voids only that arm, and the readings that need it'), L440-456 (Part E), L519-524 (Persistence: gated arm only)
- evidence: Only s = 100 (validity 1-4) and the online arm have named checks. So whether, say, an s = 40 convergence failure voids it is undefined; its exploratory |dvbar| was 0.130, the largest.

Other gaps:
- REPLICATES needs 'every gated seed' and the pooled reading needs '4 of 5 seeds'. With a voided seed, neither says whether the denominator shrinks, nor whether the reading is still REPLICATES/REPLICATION FAIL or void, so they are not exhaustive under voids.
- 'while main fails' does not say on which seeds.
- The dose-response McNemar counts need per-cue joints of the s = 80 and s = 40 arms. Only the gated arm's per-cue outcomes are listed as recorded, yet readings are 'computed by the verdict code from the records'.
- fix: State the following:
- every P2-E3-protocol reported arm applies validity 1-4 and 7, and a failure voids that arm at that load;
- REPLICATES needs all non-void seeds, and at least 4;
- the pooled reading uses 'at least 4 of the non-void seeds, with main failing S2 on those seeds';
- every P2-E3-protocol arm's reported_arm record holds its 200 per-cue joint booleans per load.

### R6 [nit] Pins wording contradicts itself ('learn_one not overridden' and 'the subclass's learn_one'); wrapper removal is not exception-safe

- where: L204-209
- evidence: L204: 'e3.E3 with learn_one not overridden'. L205: 'The subclass's learn_one temporarily replaces self.net.step'. A test asserting the method is not overridden would contradict the pin.

If super().learn_one() raises, the instance attribute stays. copy.deepcopy shares function objects, so any copy would then step the original net through the closure.

Feasibility itself is confirmed (wrapcheck.py, seed 44, 40 items, E3 and Online). Store, fb, R, vbar and net.t are identical, as are Online's state_digest and log. There are 250 steps per episode, R equals the cells with at least one capture in the last 50, and copies carry no 'step' in net.__dict__.
- fix: Write 'E3's learn_one body is neither copied nor changed: the subclass's learn_one installs the wrapper, calls super().learn_one() and deletes the wrapper in a finally clause'.

### R7 [nit] Part C: the stated reason for no R_3 swap in twin A is inaccurate; the M = 500 prediction cites a grid comparison never run

- where: L398-399; L588
- evidence: twin_A deep-copies S, then settles and tests on seed-keyed streams (TEST_IN, M, 101 and TEST_IN, M, 1). A second twin_A(S, M, ref_store=R3_store) call therefore reproduces the identical raster; the swap is feasible at about 1-2 min per load.

The M = 500 cell claims 'AVAILABLE FROM ACTIVITY (seed 44 both loads, seed 45 M = 500)'. But R_3's grid best exists only for seed 44 at M = 1,000 (verify/numbers/r3grid.log); at M = 500 only frozen-point values exist (rk_44/45.log: 0.925 / 0.935, equal to the plateau-set).
- fix: Reword the reason as a choice ('not run; a second twin_A call would give it'). Label the M = 500 Part C prediction 'frozen point only; grid best not explored'.

### R8 [nit] Power-section summaries omit what the script outputs

- where: L550-552, L568-572
- evidence: - **M = 1,000 'material losses' cell.** It omits the operating point. The script gives it as material with P 0.97-0.98 for L_o >= 0.15, which the M = 500 row does state.
- **'The rest reads SPLIT'.** NOT ATTRIBUTABLE is about 0.02 at every J_ub* value.
- **'By run it ranges from 0.0002 to 0.12'.** That is the dependent model's range; the independent model's by-run range is 6e-6 to 0.058.
- fix: Add 'operating point when L_o >= 0.15' to the M = 1,000 row. Write 'the rest reads SPLIT, except about 0.02 NOT ATTRIBUTABLE'. Write 'by run 6e-6 to 0.06 (independent) and 0.0002 to 0.12 (dependent)'.

### R9 [nit] The online arm is bound to 'tree 9152f1e4' only in the text

- where: L406
- evidence: 9152f1e4 is the current HEAD:plant2 tree. Once p2_e5_structured.py lands, the plant2 tree changes, and no check ties the online arm to the frozen p2_e4_online.py, e3, e2, e1, engine, readout and btsp blobs. P2-E4's verdict code lives in p2_e4_online.py.
- fix: Record git blob ids of those files in the online arm's record. Add to the arm's validity that they equal the blobs in tree 9152f1e4.

## Computed (scripts and numbers)

All scripts and outputs are under ~/.cache/brain-sim/review/p2e5-fixcheck/regression/. git status in the repository stayed clean, and PYTHONDONTWRITEBYTECODE=1 was set throughout.

**1. Power reference.** Ran analysis/p2e5_power.py read-only (power_out.json). Every number in the contract's Power section reproduces:
- idealised 0.856 and 0.789;
- oracle at M = 500 alone 0.0018 (by run 1.6e-8 to 0.035; C2 0.159, C4-spurious 0.06, S2 0.722, S4 0.267);
- P(S1 at M = 500) 0.0095 (independent) and 0.039 (dependent);
- replication per seed and load 0.9997 and 0.954;
- P(INVALID) 0.0067 (SD 0.03) and 0.060 (SD 0.04);
- the Part B table: M = 500 CD 1.0 / 0.945, SPLIT 0.921, SPLIT 0.598 / OPD 0.402, OPD 0.99; M = 1,000 CD 0.97-0.975 and 0.851; NOT ATTRIBUTABLE about 0.02;
- sensitivity 0.919 / 0.687 / 0.481 / 0.177.

**2. Grids** (grid_s60_seed44/45_cyclic.json, max joint with first-in-grid-order ties, integer-cue passing points):

| store | M = 500 | M = 1,000 |
|---|---|---|
| plateau-set | 1.0 / 0.985; 24 / 26 passing points | 0.60 / 0.665 at (5.0, 0.8) |
| main | 0.565 at (2.8, 0.7) / 0.675 at (3.6, 0.8) | 0.04 / 0.055 |

Frozen-point values match.

**3. Other exploratory outputs.** rk_44/45, spurious, where_*, out_s*, the methodology jsonl files and r3grid were checked against the Why and Predictions numbers. All match, for example: AUC 0.9995 / 0.9996 / 0.996; spurious 583/200 and 3845/200 at 98.8 % / 97.7 % sibling; intrusion classes 36.6 / 47.9 / 2.4.

**4. wrapcheck.py** (seed 44, 40 items). The step wrapper on E3 and on P2-E4 Online leaves stores, R, vbar, net.t, state_digest and the log identical. There are 250 steps per episode, R equals the cells with a nonzero continuation count, and deep copies carry no instance step.

**5. online_validity.py** (frozen P2-E4 driver with the contract's generator, seed 44, M = 500, 53 s):
- leak ok (all zero), slot checks ok, audit empty, fb_union ok, elig 0.988, mean |A| 19.84;
- block C1 0.82, C2 1.0, joint 0.525, cohort content 0.34.

**6. partd_probe.py** (seeds 44 and 45, M = 500, about 2.5 min each; reference E3 learning, Online.run_to, twin_A with ref_store, twin_B):

| measure | seed 44 | seed 45 |
|---|---|---|
| intrusions_median, online-written | 123 | 112 |
| intrusions_median, P2-E3-protocol | 65.5 | 61 |
| Part D R | 1.86 (WORSENS) | 1.82 (WORSENS) |
| twin A joints: online / P2-E3 / plateau-set | 0.035 / 0.09 / 0.965 | 0.10 / 0.165 / 0.95 |
| twin B memory, online against settled | 0.82 against 0.965 | 0.77 against 0.955 |
| twin B content, online against settled | 0.525 against 0.055 | 0.58 against 0.035 |
| L_o memory / content (cues) | +29 / -94 | +37 / -109 |
| offset online / settled (mV) | 3.70 / 1.86 | 3.80 / 1.92 |

**7. ranking() at the measured L_o.** At L_o 0.145 / 0.165 / 0.185, M = 500 reads CD 0.961 / 0.874 / 0.705. Paired per seed: seed 44 L_c 67 against L_o 29 reads CD; seed 45 L_c 45 against L_o 37 has no dominant loss.

**8. Pooled control against main**, seed 45 at M = 1,000: joint 0.10 against 0.0, plateau-set 0.49 against 0.155, C2 0.775 against 0.465.

**9. Code read** (p2_e3_completion.py, p2_e4_online.py, p2_e1_btsp.py, p2_e2_accommodation.py, engine.py):
- E3 and Online call self.net.step directly, and learn_one has no other step path;
- Net is a plain class, so the instance-attribute override works, with precedent in e2.evaluate's present override;
- twin_A is deterministic, so a second call with another ref_store reproduces the raster;
- intrusions_median is over the 200 P2-E3 half cues.
