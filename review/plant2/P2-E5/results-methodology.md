# P2-E5 results review: methodology lens

Independent reviewer given only the files (HEAD f25d3ed, after the verdict). Run 2026-10-11. Recorded verbatim, before synthesis.

## Verdict

Trustworthy and correctly derived. The recorded verdict holds under the frozen rules: STRUCTURED INDEX FAIL + STRUCTURED CONTENT FAIL, with all 5 gated seeds valid. Every part checks out: Part B CONTAMINATION-DOMINANT at both loads; Part C AVAILABLE FROM ACTIVITY; Part D WORSENS at both loads; s100 REPLICATES; pooled CORRELATION-ATTRIBUTABLE at M=500 and LINE LOAD SUFFICIENT, CORRELATION WORSENS at M=1000. I rebuilt all 80 per-seed criterion counts from the persisted per-cue files (sha256 matched) and they agree exactly. I re-derived each reading by hand and found the same values. Event order is sound: freeze, then driver, then reviews, then exploration, then predictions committed, then gated seeds. No blocker. The open risks are in what the Result says, not in the verdict: the M=500 index failure is narrow; Part B at M=1000 depends on the optimistic grid best; and Part C means less than its label suggests.

## Findings

### M1 [major] The M=500 STRUCTURED INDEX FAIL rests on 2 of 5 seeds, by narrow margins

- where: bench/results/plant2.jsonl kill_test_seed rows (seeds 23, 25); verdict row 152
- evidence: At M=500 seeds 21, 22 and 24 pass every S1 part. Seed 23 fails C2 at 174/200 (bar 180) and C4-spurious at 86/100 (bar 90). Seed 25 fails C4-spurious at 88/100. At M=1000, S1 fails on all 5 seeds (C2 87-103/200, C4-spurious 35-49/100). Content fails on all 5 seeds at both loads: S2 19-36/200 and S4 4-8/100 at M=500; S2 0-1 and S4 0-1 at M=1000. S3 holds (0.965-1.0).
- recommendation: Keep the label; the every-seed rule is frozen. The Result must name the failing parts, seeds and margins at M=500, as P2-E4 did for RECOVERY FAIL. It must also state that 3 of 5 seeds pass S1 at M=500, and must not call the M=500 index failure robust.

### M2 [major] Part B at M=1000 depends on the optimistic grid best; at the frozen readout no item-specific write reaches the bar

- where: gated_diagnostics grid; verdict readings part_B per_seed (L_c_frozen)
- evidence: At M=1000, L_c is 110-126 cues, from grid bests at J_fb 4-6 and g 0.7-0.8. At the frozen point, L_c_frozen is only 28-35 cues, because the plateau-set store itself reads 28-35/200. That makes its frozen shortfall 145-152 cues. Even at the grid best, the plateau-set store reaches 126-141 and R_3 127-143, below the 180 bar on every seed, with 0 passing grid points. The contract does fix grid bests for L_c and L_i, so the reading is correctly derived.
- recommendation: The Result must give L_c_frozen beside L_c and label the grid best optimistic. It must say that on these rasters no store written from the network's activity, nor the plateau-set store, reaches S2 at M=1000 even after optimistic recalibration. So a write-only correction cannot pass P2-E5 at M=1000; this is a same-raster replay, not a gated test.

### M3 [major] L_i = 0 at M=500 must not be read as a sound index

- where: verdict readings 500 part_B; contract Part B L_i row
- evidence: At M=500, L_i is 0 on every seed (plateau-set grid best 198-200). The plateau-set store also passes S2 at the frozen point (186-195). Yet S1 fails at M=500 (M1). S1 does not depend on the feedback store, so no write correction can change C1-C4. 'Material' is L_c at both loads, and L_i and L_o only at M=1000. At M=500, L_o is at least 20 cues on only 3 of 5 seeds (26, 30, 12, 21, 15).
- recommendation: Name C2 and C4-spurious beside L_i, as the contract requires. State that S1 is untouched by any feedback write and that Part B never overrides S1.

### M4 [major] Part C AVAILABLE FROM ACTIVITY is a narrow, labelled measurement

- where: gated_diagnostics activity and grid R3; contract Part C
- evidence: I verified every clause on 5 of 5 seeds at both loads. Count AUC is 0.9988-0.9995 at M=500 and 0.9955-0.9971 at M=1000; first-spike AUC is about 0.78. R_3 is within 10 cues of the plateau-set store at the frozen point (worst gap 1 cue below) and at the grid best (worst 1 below, seed 22 at M=1000). Positives are defined by A(x), the experimenter's key. At M=1000, R_3 matches a store that itself fails. R_4 and R_6 read higher at the frozen point (seed 21: 0.305 and 0.395, against 0.175 for R_3).
- recommendation: Say it is measured, not adopted, and that it is scored against the experimenter-assigned assembly. Do not imply that R_3 fixes contamination at M=1000. Report R_k without choosing k after the fact: k=3 was fixed in advance, and choosing it now would be parameter rescue.

### m1 [minor] Part D: AT FLOOR also applies at M=500 on seed 25; the cause is not isolated

- where: verdict readings 500 part_D joints
- evidence: R is 1.66-1.95 at M=500 and 1.69-1.84 at M=1000, at least 1.25 on 5/5 seeds at both loads, so WORSENS is correct. The P2-E3-protocol store's twin A joint is 19 cues on seed 25 at M=500, so that seed is AT FLOOR. At M=1000 all five are (0-1 cues). Twin B: at M=500 online gains 84-103 content cues while losing 12-30 memory cues. At M=1000 it loses 65-79 memory cues and gains 8-13 content cues.
- recommendation: Mark seed 25 at M=500 AT FLOOR. The appended predictions flagged AT FLOOR only at M=1000. Report the signed counts. Word WORSENS as a comparison of the whole online driver against the settled protocol; schedule, probes and offset are not separated.

### m2 [minor] The timing of the container restart is misdescribed in the packet note

- where: /proc/stat btime; reflog; ~/.cache/brain-sim/plant2/p2_e5 markers
- evidence: The predictions were written at 05:06:53 and left uncommitted. The container booted at 14:02:22. 694038c was committed at 14:03:14. Markers for seeds 21 and 24 are at 14:03:24 and 14:03:26; the lane logs and persistence files start after that. No cache file is dated between 05:07 and 14:03. So the restart came before the predictions commit, not between the commit and the launch. The guard holds: digest 8ab1cb47ff6ac06e and tree dc16f182 on every gated record, and the frozen contract is a byte-prefix of HEAD. HEAD moved to 5067031 (HANDOFF.md only) during this review.
- recommendation: State the exact sequence in the Result, including the 9-hour uncommitted interval and the evidence that no gated run preceded the commit.

### m3 [minor] Score the predictions as held or failed; several qualitative ranges failed narrowly

- where: contract Predictions table and appended section
- evidence: Held: both labels; S1 fail; S2/S4 fail and S3 hold; C1, C3 and C4-recall hold; validity; Part B at both loads; Part C; Part D at both loads; s100; both pooled readings; no load disagreement. Appended P(all seeds): C2 at M=500 was 0.38 and it failed; C1 at M=1000 was 0.49 and it held. Failed narrowly: S3 at M=1000 '>=0.98' (0.965, 0.975); S4 at M=500 '<=0.05' (0.08, 0.06); S2 at M=500 '0.08-0.17' (0.18); main-store grid best at M=1000 0.04-0.055 (0.065-0.10); C2 at M=1000 0.45-0.55 (0.435); AUC at M=500 '>=0.999' (0.9988); online C1 at M=500 0.77-0.82 (0.81-0.89); L_o 29-37 cues (12-30).
- recommendation: List every row as held or failed. Do not summarise them as 'within range'.

### m4 [minor] The 'no pass observed in simulation' wording does not match the method

- where: contract appended section; power_predictions row 111
- evidence: P(PASS) is an analytic binomial product evaluated on 400 posterior draws. It underflows to 0.0 (5-95% interval [0, 0]). No passes were simulated.
- recommendation: In the Result, say P(PASS) was numerically zero under the model, which is not proof that a pass is impossible. Keep the owner's 'not impossible' sense without claiming that simulations were run.

### m5 [minor] Report findings beside the readings that change their interpretation

- where: gated_diagnostics contamination; s80 and F40 reported_arm
- evidence: Label-permuted store at M=1000: perm_spec 0.545-0.583 against 0.984-0.992 for the main store, so regeneration is largely not item-specific (the flag stays null because there is no PASS). Spurious cells per cue: 2.7-3.3 at M=500 and 16.5-18.9 at M=1000. s80 fails at M=1000 (joint 0.62-0.74). F40 at M=1000: joint 0.055-0.065, plateau-set 0.83-0.91. Pooled at M=1000 gains 70-92 cues on the plateau-set store and 62-77 on C2.
- recommendation: Include these as reported values with no reading for F40. Say that at M=500 the content failure is attributable to sibling correlation, and that at M=1000 line load alone already fails S2.

### n1 [nit] The Result must carry the disclosures already promised

- where: DECISIONS.md 2026-10-11 close-out; HANDOFF
- evidence: DECISIONS commits the verdict text to saying that validity 5's proj_current and inh_ok hold by construction (online slot_checks_ok). Signed drift at M=1000 is -0.077 to -0.112 mV; 3 of 5 seeds go beyond the withdrawn |0.1| rule, which was withdrawn before the freeze. The convergence rule holds, with a maximum of 0.118.
- recommendation: State both. Also report that I re-derived the counts from the persisted files and they matched exactly.

## Next steps

- Append the Result to docs/plant2/P2-E5-structured-items.md as appended lines only. It should hold the verdict, the vector with the failing seeds and margins (M1), the readings with L_c_frozen beside L_c, AT FLOOR for seed 25 at M=500, the predictions scored held or failed, the exact timeline, and the by-construction disclosure.
- Add a P2-E5 row to STAGES.md: FAIL on 5/5 valid seeds. Stage 1's structured-input clause is not met. P2-E3's PASS stands, scoped to independent items. P2-E5 removes no experimenter supply and adds one (the item distribution).
- Route to the owner before any mechanism contract: the STRUCTURED INDEX FAIL at both loads, with Part B's readings beside it. Add the projection that no write-only store reaches S2 at M=1000, plus the pending questions in EVAL-after-P2-E4.md (Q1 burst-gated write, Q3 placement of index cross-talk).
- No re-run, no retune, no Stage 2 work; familiarity-gated allocation stays deferred; add ledger rows for this review.

## For the owner

P2-E5 failed exactly as frozen, on five valid fresh seeds. The labels are STRUCTURED INDEX FAIL + STRUCTURED CONTENT FAIL, and the records support them exactly.

- Content fails everywhere: on every seed at both loads.
- The index failure is narrow at M=500 (2 of 5 seeds, 2-6 cues short) and broad at M=1000.
- Part B ranks learning-time contamination as the largest loss at both loads. At M=1000 that ranking needs readout recalibration. Even the best-case plateau-set and activity-selected stores stay below the content bar at M=1000, and no feedback write can change the index.
- Part C shows that cells with 3 or more spikes match the assigned-assembly store. That is measured, not adopted.

Nothing is retuned. The next step needs your rulings: where index cross-talk goes, and whether a write mechanism comes first.
