# P2-E5 implementation review: conformance

Independent reviewer given only the files (driver at commit f873dc5, side branch plant2-p2e5-driver). Run 2026-10-11. Recorded verbatim, before synthesis.

## Verdict

I went through the frozen contract (bc28cd9) one clause at a time against p2_e5_structured.py and test_p2_e5.py at f873dc5. I found nothing that could move a gated number, a label, a validity flag or a predeclared reading. All the remaining findings are minor or nits. Here is how the driver meets each clause.

**Items, streams and draws.**
- Every stream key is as the table gives it:
  - (seed, 20, F): sorted prototypes.
  - (seed, 21, F, k): k starts at 1, and k = 0 raises an error.
  - (seed, 23, k): the pooled draw from the sorted unique U.
  - (seed, 22, M): for each j, the exemplar then its mask; then the prototype masks; then the same generator is passed to present(), new exemplars first, then prototypes.
  - (seed, 24, M): the within-family derangement is redrawn until it has no fixed point.
- Item k belongs to family k mod F. Kept sets are nested across s. Each line set is sorted after drawing.

**Pins.**
- The read-only net.step wrapper is installed and removed in a finally clause around the inherited learn_one. The continuation is the last 50 captured steps, t = 0..49.
- The plain E1 gets the injected generator.
- Gated scores use the first 600 onsets, on the raster cut at n_ticks. The cut is made before the block's separate present() call. The persisted test raster is the full raster, with n_ticks_gated recorded.
- The integer-cue pin is applied: round(200 f), bar_count 180 or 90, and 20 and 10 cues for the material threshold and the margin.

**Kill test S1-S4.** These come from P2-E1/E2's criteria and P2-E3's score. C4 and S4 use the oldest 100 items.

**Validity 1-7.** All seven are implemented exactly, including 2(a) with the block, 2(b) with vbar, convergence per load, the shuffled check at 1,000 from stream (seed, 10, M), the 15-19 overlap check over all within-family pairs, and validity 7 with capture, fb_union and R_1.

**Verdict.** INVALID takes precedence, failure labels are joined, and the first record of each seed is used.

**Part A.**
- The grid is 72 points, ordered J ascending then g ascending.
- The grid best is np.argmax on integer joints, so a tie goes to the first maximum, with no condition on D3 or D4.
- Each store records the frozen point, the best point with D1-D4, and the number of passing points.

**Part B.**
- L_c = max(0, min(ub, 180) - min(own, 180)), L_i = max(0, 180 - ub), and L_o is taken from twin_B["all"] McNemar counts, net and clipped at 0.
- Exclusion follows the s = 100 validity and gate per load, and the online arm's per-load validity.
- A loss dominates when it is at least 20 cues and at least 10 more than each of the others. The reading order is NOT ATTRIBUTABLE, then X-DOMINANT, then NO MATERIAL LOSS, then SPLIT.

**Part C.**
- Items in (M-200, M] are pooled into one AUC.
- The reading is one-sided with a 10-cue allowance, at both the frozen point and each store's grid best, on every seed and load.
- The online arm's R_3 is read through a second twin_A call.

**Part D.**
- The ratio is (median intrusions + 1)/(median intrusions + 1), with WORSENS at 1.25 or more, NOT WORSE below 1.10, and at least 4 valid seeds needed.
- The reused P2-E4 pieces and the blob check pass: all seven blobs equal tree 9152f1e4.

**Part E.**
- The s = 100 rule is ordered over (seed, load) as the contract says.
- The pooled reading uses the plateau-set joint at the frozen readout for both arms and the C2 count, at 20 and 10 cues.
- Dose-response uses per-cue McNemar counts.

**Part G.** The gated, s = 80, s = 40 and F = 40 arms each get their own block. Pooled and s = 100 get the gated arm's block and report only responders and lines.

**Guard and run-once.** These follow the contract list (one nit below).

**Can the readings be recomputed from the records alone?** Yes:
- per-cue joint and index bit strings;
- grid best and frozen-point cue counts;
- L_o with the signed counts;
- the medians behind the Part D ratio;
- the s = 100 validity and gate;
- the pooled inputs.

**Where it deviates:**
- Part D's AT FLOOR label and the joint differences are not computed.
- Persistence leaves out the per-cue outcomes.
- The online arm records no A digest.
- A crash in gated_diagnostics is not isolated. A crash at M = 1,000 voids M = 500 too.
- The predict path reads reported arms without filtering by tree.
- The guard accepts inserted lines as well as appended ones.
- Void arms are included in the dose-response counts.

The online arm's validity also has two extra checks (capture_ok and reference_present). Both are deterministic invariants and harmless.

## Findings

### C1 [minor] A crash in gated_diagnostics is not isolated. It aborts the seed's remaining arms permanently, and Part C then reads NOT SHOWN

- where: plant2/experiments/p2_e5_structured.py:852 (run_seed), 1175-1178 (run-once check), 947-951 (Part C on a missing diag record)
- evidence: run_seed appends kill_test_seed (line 500) before it calls gated_diagnostics (line 852) outside any try/except. Only the arms loop (lines 855-865) catches exceptions.

If the diagnostics raise on a gated seed, for example a MemoryError while the two test copies and the 72-arm replays are held:
- the s100, s80, s40, pooled, F40 and online arms never run for that seed;
- the CLI then refuses that seed for good, because `s in done` (line 1177) is checked before the marker, so even --owner-ruled-rerun cannot run the reported arms.

In readings, that seed's okC is False (lines 949-951), so Part C reads NOT SHOWN whatever the data say. Parts B, D and E each lose the seed, which leaves exactly 4 against their 4-seed minimum.

The contract voids only the crashed arm ('A failure, or a crash, voids that arm at that load').
- fix: Wrap gated_diagnostics(...) at line 852 in the same try/except as the arms, appending a reported_arm record with arm='gated_diagnostics' and crashed=repr(ex), then continue with the other arms. Set gated_fb from loads before the call. Optionally, let --owner-ruled-rerun run only the missing reported arms of a seed that already has its kill_test_seed record.

### C2 [minor] A crash at M = 1,000 in a reported arm voids its M = 500 load as well

- where: plant2/experiments/p2_e5_structured.py:745-777 (run_p2e3_arm), 794-841 (run_online_arm), 855-865 (run_seed)
- evidence: Both functions build one record across both loads and append it only after the loop (lines 776 and 840). An exception at M = 1,000 is caught at line 861, which writes a crash record with no 'loads', so the completed M = 500 results are thrown away.

readings() then treats the arm as void at 500 too:
- s100 at line 919, so the seed is NOT ATTRIBUTABLE in Part B at 500;
- online at line 916, so no L_o or Part D ratio at 500;
- pooled at line 977.

The contract voids the arm 'at that load' only. M = 1,000 is the load with the highest memory use, so a crash there is the likeliest kind.
- fix: Build out['loads'][str(M)] inside a per-load try. On an exception, append the record with the loads already completed plus crashed={'M': M, 'error': repr(ex)}, and make readings() treat only the missing load as void. Alternatively, append a partial record after each load.

### C3 [minor] Part D's 'AT FLOOR' label and the joint differences are never computed by the verdict code

- where: plant2/experiments/p2_e5_structured.py:829-834 (online record), 960-971 (readings, Part D)
- evidence: The contract (Part D, 'Also reported') says the joints of the online-written, P2-E3-protocol and plateau-set stores and 'their difference' are reported. 'The joint difference is labelled AT FLOOR on a seed where the P2-E3-protocol store's joint is below 20 cues.' It also says: 'Every reading below is computed by the verdict code from the records.'

The online record holds the three joints, as twin_A online, reference and plateau, but neither run_online_arm nor readings() computes a difference or an AT FLOOR flag. Part D's output is only dict(ratios, reading).

On TINY seed 96 at M = 200, the reference joint was 0.125 of 40 cues. At full scale the exploration put the M = 1,000 reference joint at about 0.
- fix: In readings() Part D, add per seed and load: on_c = round(n * online.joint), ref_c = round(n * reference.joint), pl_c = round(n * plateau.joint), diff = on_c - ref_c, and at_floor = ref_c < 20, with n = 200 under the integer-cue pin. Report them beside the ratio.

### C4 [minor] The persisted file leaves out the per-cue outcomes that the Persistence clause lists first

- where: plant2/experiments/p2_e5_structured.py:435-462 (persist); 479 (per_cue in the record)
- evidence: The contract's Persistence list for the gated arm at both loads is: per-cue outcomes; E, A, R, continuation counts and first-spike ticks; the learning raster; the test raster.

The npz holds A, E, R, cont_cells, cont_counts, cont_first, learn_raster, test_raster_M, test_n_ticks_gated_M and test_onsets_M. I listed its contents from the TINY seed 96 file, and its sha256 matches the record. It has no per-cue outcomes.

The kill_test_seed record keeps only two bit strings per load, the half-cue joint and index. These are not stored anywhere:
- per-cue missing and intrusion counts;
- D3 per novel cue;
- C3 ignition;
- recall and spurious counts.

The file is also np.savez_compressed (zip/deflate), not the gzip the contract names (a nit).
- fix: In persist(), add the frozen-readout per-cue arrays for all 600 cues: res['missing'][:,0], res['item'][:,0], res['total'][:,0] and the kinds. Add out['recall'][50], out['spurious'] and out['ignition'] from the gated test. Keep the per_cue bits in the record as well.

### C5 [minor] The online arm records no digest of its A lists

- where: plant2/experiments/p2_e5_structured.py:829-834
- evidence: The contract's Pairing clause says 'Every arm records a digest of its A lists'. The gated record has A_digest (line 389, recorded at 478), and every P2-E3-protocol arm has A_digest at line 761. The online arm's load record (validity, valid, block, twin_A, twin_B, L_o, ratio, activity, responders) has none.

Part D's ratio and Part B's L_o rest on the online arm sharing A(k) with the gated arm, but the records cannot show that it did.
- fix: Add A_digest=hashlib.sha256(b''.join(a.astype(np.int64).tobytes() for a in o.A[:M])).hexdigest()[:16] to L. Optionally, check in readings() that it equals the gated record's A_digest at that load.

### C6 [minor] predictions() takes reported_arm records without the tree filter it applies to exploration_seed records

- where: plant2/experiments/p2_e5_structured.py:1063-1071 vs 1097-1100
- evidence: exploration_seed records are accepted only if they come from this plant2 tree, with plant2 clean (lines 1066-1067). The diagnostics and arms passed to readings() come from first_records(recs, 'reported_arm', gated=False, arm=a) (lines 1097-1098), which filters only on experiment, kind, gated, digest and arm, and keeps the FIRST record per seed.

Suppose exploration on 44-45 is re-run after any driver change that leaves CONTRACT, and so DIGEST, unchanged, as happened with P2-E4's fix verification. Then exploration_reading_inputs in the committed power_predictions record would combine the new tree's exploration_seed records with the old tree's diagnostics and arms.

There are no P2-E5 exploration records yet. I checked bench/results/plant2.jsonl and it holds only power_reference.
- fix: Filter reported_arm records for predictions the same way: r['git']['plant2_tree'] == g['plant2_tree'] and not r['git']['plant2_dirty']. For example, add a tree argument to first_records.

### C7 [nit] The guard accepts lines inserted anywhere in the contract, not only appended lines

- where: plant2/experiments/p2_e5_structured.py:1130-1135
- evidence: The contract allows only appended lines ('After freezing, only appended lines are allowed'; the guard is to refuse unless 'the contract is unchanged since its frozen commit except for appended lines'). The guard checks only that numstat deletions == 0 between bc28cd9 and HEAD. An insertion in the middle of a section, for example inside the Part B rules, passes.

Today the numstat from bc28cd9 to HEAD is empty, so the check passes correctly.
- fix: Also require that `git show bc28cd9:docs/plant2/P2-E5-structured-items.md` is a byte prefix of `git show HEAD:...` (or of the working-tree file).

### C8 [nit] Dose-response McNemar counts include void s80 or s40 seed-loads

- where: plant2/experiments/p2_e5_structured.py:998-1008
- evidence: The dose loop pairs per_cue bit strings whenever both records exist. It never checks ja['valid'] or jb['valid'], so an s80 or s40 load that fails validity 1-4 or 7 still enters the counts. The contract's Voids clause says a failure 'voids that arm at that load'. Dose-response is a reported value, not a reading, so no predeclared label moves.
- fix: Skip a seed-load when the reported arm's load has valid == False. The gated side's invalidity already makes the verdict INVALID.

## Computed (scripts and numbers)

All scripts and outputs are in ~/.cache/brain-sim/review/p2e5-impl/conformance/. Nothing in either repository was changed. I set PYTHONDONTWRITEBYTECODE=1 and passed -p no:cacheprovider to pytest, and git status in the worktree is clean.

1. **Blob check.** e5.blob_check(): all seven reused files have the same blob as plant2 tree 9152f1e4. The plant2 tree at f873dc5 is da55da7f, clean, and DIGEST = 8ab1cb47ff6ac06e. `git diff --numstat bc28cd9 HEAD -- contract` is empty.

2. **Fast tests.** `pytest plant2/tests/test_p2_e5.py -m "not slow"` gives 9 passed in 13.8 s.

3. **TINY end-to-end, seed 96** (run_tiny.py). `run_seed(TINY, 96, gated=False, c4=E4_TINY)` took 214 s and wrote all 8 records with no crash.
   - Validity 1-7 all hold. The sibling overlap is 18.5, the shuffled joint 0.0, and count AUC 0.998 at M = 120 and 0.993 at M = 200.
   - The gated readout and the grid's (2.8, 0.3) point agree exactly: joint 0.75/0.125, D4 0.6/0.05, intrusion median 1.5/173.
   - The per-cue joint bit counts equal counts.S2: 30 and 5.
   - The persistence npz sha256 matches the record. Its keys are A, E, R, cont_cells, cont_counts, cont_first, learn_raster, test_raster_M, test_n_ticks_gated_M and test_onsets_M, with no per-cue outcomes.
   - The online arm's validity includes all the contract keys plus capture_ok and reference_present. L_o = max(0, 16, -18) = 16 at M = 120.

4. **Synthetic reading branches** (synthetic.py; none of these is in the repo tests):
   - Part B:
     - INDEX-DOMINANT at L_i 30, L_c 10, L_o 5;
     - CONTAMINATION at exactly L_c 20 against 10 and 10, and none at L_c 19, which reads NO MATERIAL LOSS;
     - with ub 200 and own 185 the cap gives L_c 0, L_i 0;
     - OPERATING-POINT-DOMINANT at L_o 40 against L_c 20;
     - SPLIT at 3 seeds against 2;
     - NOT ATTRIBUTABLE with s = 100 void on 2 seeds, where s = 100 reads NOT ESTIMABLE.
   - Part D: NOT WORSE on 4 seeds below 1.10, WORSENS at exactly 1.25, a ratio of exactly 1.10 not counted as NOT WORSE, and MIXED.
   - Part C: NOT SHOWN when R_3 is 11 cues below the plateau-set store at grid best.
   - Pooled: LINE LOAD SUFFICIENT, CORRELATION WORSENS at a C2 gain of exactly 20, and LINE-LOAD-LIMITED at gains of 10 and 10.
   - All of these match the contract.

5. **Predict and verdict paths** (paths.py). I relabelled the real-structured TINY records as exploration seeds 44-45 and as gated seeds 21-25. predictions() and verdict() both ran without error, giving the label 'STRUCTURED INDEX FAIL + STRUCTURED CONTENT FAIL' and readings for every part.

6. **Results file.** bench/results/plant2.jsonl holds only P2-E5's power_reference record, with no exploration records yet.
