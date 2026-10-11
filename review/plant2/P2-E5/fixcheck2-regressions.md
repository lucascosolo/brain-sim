# P2-E5 driver fix-check: regressions

Independent checker given only the files (driver at commit 7cfe62c, branch plant2-p2e5-driver). Run 2026-10-11. Recorded verbatim, before synthesis.

## Verdict

The driver can be frozen as it stands. I found no blocker or major problem and no regression from the 7cfe62c restructure. I ran TINY run_seed end to end on seeds 91 and 93 (gated=False, c4=E4_TINY), and each wrote 8 records with no crash. Every validity flag of the gated record and of each reported arm is True at both loads, and every record parses with json.loads with no NaN or Infinity token. The persistence file matches its sha256 and holds what the Persistence clause lists. readings() runs on the records, alone and with both seeds together, at min_seeds=1. The online arm's ratio, L_o, A digest (matches the gated arm: True) and blob check (all 7 blobs the same) are present at both loads. I read the restructured code line by line: run_timeline/on_load, run_p2e3_arm, gated_diagnostics, run_online_arm, run_seed, readings, verdict, predictions and guard. No arm writes a record twice. A crash record cannot be written ahead of a good record in the same run. I found no wrong sign and no path where exploration and gated runs differ other than the seed, the record kind and the persistence file name. One minor conformance gap remains: Part C counts a seed whose diagnostics crashed as a failure, where the contract's rule (count only non-void seeds) applies. That case is reachable now that the diagnostics crash is contained. There are also two nits, both about crash handling and its test.

## Findings

### R1 [minor] Part C counts a seed whose gated_diagnostics crashed as a failure (NOT SHOWN) instead of counting only non-void seeds

- where: plant2/experiments/p2_e5_structured.py:1001-1014 (readings, Part C) and 1081 (overall Part C)
- evidence: The contract (Voids) says a crash voids that arm at that load. Its Denominators rule says a reading that needs a voided arm counts only non-void seeds, needs at least 4, and otherwise reads NOT ESTIMABLE. Commit 7cfe62c now contains a diagnostics crash, writing a reported_arm 'gated_diagnostics' record with 'crashed' and only the completed loads. But readings still does okC.append(False) when D is None, so one void seed forces Part C to NOT SHOWN. Synthetic check (synth_partc.py, test-file helpers): five gated seeds, and seed 21's diagnostics crashed before any load as run_seed's except writes it. Part B reads CONTAMINATION-DOMINANT at both loads on the 4 remaining seeds, and Part D reads WORSENS. Part C reads per_seed [False, True, True, True, True], so overall NOT SHOWN, even though all 4 non-void seeds show AUC >= 0.95 with R_3 within 10 cues. The bugs review (F2) and the conformance review (C1) both named this NOT SHOWN outcome, but the fix changed only the containment. Part C is the owner's research target, so a crash would give a misleading reading rather than NOT ESTIMABLE.
- fix: In readings Part C, skip a seed whose diagnostics load is missing (D is None) instead of appending False. Per load: if fewer than c['min_seeds'] seeds have the load, set C = dict(per_seed=..., ok=None, reading='NOT ESTIMABLE'); otherwise set ok = all(okC) over the non-void seeds. Overall: out['part_C'] = 'NOT ESTIMABLE' if any load is NOT ESTIMABLE, else 'AVAILABLE FROM ACTIVITY' if all loads are ok, else 'NOT SHOWN'. Add the synthetic case above to test_labels_and_readings_on_synthetic_records.

### R2 [nit] A crash while processing the first load voids the later load too, even where that load's data is already in hand

- where: plant2/experiments/p2_e5_structured.py:741-773 (gated_diagnostics: one try around both loads); 793-820 (run_p2e3_arm: on_load raises out of run_timeline)
- evidence: gated_diagnostics already holds both loads' test copies and rasters, and processing one load does not depend on the other. Yet one try/except wraps the whole `for M` loop, so a data-dependent exception at M = 500 also abandons M = 1,000. Likewise, in run_p2e3_arm an exception in on_load at M = 500 propagates out of run_timeline and stops learning to 1,000. The contract voids a crashed arm only 'at that load'. Crash injection on TINY seed 94 confirmed the behaviour in the other direction: a crash at the second load kept '120' and recorded crashed.after_loads ['120'], with one record per arm. Reachable only on a crash.
- fix: In gated_diagnostics, move the try/except inside the `for M` loop, recording the failed loads, e.g. out['crashed'] = dict(failed_loads=[...], error=...). In run_p2e3_arm, wrap the body of on_load in its own try/except that records the failed load and returns, so the timeline goes on to the next load. readings() already treats a missing load as void.

### R3 [nit] The crash test's persisted-record assertion is vacuous under TINY loads

- where: plant2/tests/test_p2_e5.py:298 (test_reported_arm_crash_at_second_load_keeps_the_first)
- evidence: TINY's gate_M is (120, 200), but the test asserts `"1000" not in rec["loads"]` on the record read back from the file. That holds whatever the driver writes, so the appended record's second-load exclusion is never checked. The in-memory check `list(out["loads"]) == ["120"]` covers only the returned dict.
- fix: Replace it with `assert list(rec["loads"]) == ["120"] and rec["crashed"]["after_loads"] == ["120"]`.

## Computed (scripts and numbers)

All scripts and outputs are in ~/.cache/brain-sim/review/p2e5-fixcheck2/regress/ (run_tiny.py, check.py, readings_check.py, synth_partc.py, crash_inject.py, predict_relabel.py, full500_timing.py and their logs and results). BRAINSIM_CACHE pointed inside that directory and PYTHONDONTWRITEBYTECODE=1 was set. Nothing was written in either repository; git status in the worktree is clean.

TINY end to end (TINY + E4_TINY, gated=False):
- Seed 91 took 178 s and seed 93 took 185 s. Each wrote 8 records in this order: exploration_seed, gated_diagnostics, s100, s80, s40, pooled, F40, online. There is no 'crashed' field anywhere.
- All lines parse with json.loads using a parse_constant that raises, and grep finds no NaN or Infinity token.
- Gated record validity: True at 120 and at 200 for capture_ok, converged, fb_union_ok, fwd_equals_p2e1, main_untouched, r1_equals_main and stores_unchanged_by_tests. elig_ok, mean_A_ok, shuffled_ok (shuffled joint 0.0) and overlap_ok (18.6 for seed 91, 18.5 for seed 93) are also True.
- Each P2-E3-protocol arm (s100, s80, s40, pooled, F40) carries per-load validity. All 11 fields are True at both loads, as is valid. Each arm's A_digest equals the gated arm's at both loads.
- The online arm is valid at both loads, with all 11 flags True: audit, blobs, capture, elig, fb_union, fwd_equals_p2e1, leak, mean_A, reference_present, slot_checks and twins_untouched. The blobs match tree 9152f1e4. twin_A.R3 is present and A_digest_matches_gated is True at both loads.
  - Seed 91: ratio 8.0 and 2.98; L_o 16 and 17 (net memory 16/17, net content -21/-22).
  - Seed 93: ratio 4.75 and 4.02; L_o 17 and 26.
- Persistence: the npz-inside-gzip file's sha256 matches the record. It holds:
  - E, A and R, with their offsets;
  - cont_cells, cont_counts and cont_first;
  - learn_raster (201 offsets);
  - test_raster per load (the full raster with the block), with test_n_ticks_gated and test_onsets (110 = 100 gated + 10 block);
  - per-cue outcomes for all 100 cues per load: kind, missing, item, total, visible and the short-window counts;
  - half-cue recall50, spurious and |A|, and novel ignition.
- readings(min_seeds=1) runs on each seed alone and on both together. It returns Part B per-seed rows, Part C, Part D ratios with per-seed joints, difference and at_floor, the pooled rows, dose-response McNemar pairs and s100. On TINY, s100 fails P2-E3's gate (C4_recall at 120, joint at 200), so Part B reads NOT ATTRIBUTABLE there. That is expected at TINY size.

Full config, timing only (seed 92, one M = 500 line, run_gated_arm with gate_M=(500,)):
- The gated arm took 77 s and was valid. C1 0.93, C2 0.91, C3 1.0, C4 0.93/0.89, joint 0.085, D4 0.03, convergence 0.066 mV.
- gated_diagnostics took 321 s. Of that, readout_full took 314.5 s over 12 calls (three 72-point grids, R_k, traces and the permuted store); contamination took 2.3 s (it was 354-460 s before the F1 fix), block_stats 5.6 s and store_from 5.0 s.
- Values: plateau-set frozen 188 cues and grid best 198, with 26 passing points; main frozen 17 and best 113; R3 equals the plateau-set store; count AUC 0.9994; 2.8 spurious cells per cue, 99 % of them sibling plateau cells. All are consistent with the contract's exploratory predictions, and the records parse strictly.
- The first attempt called run_timeline directly and raised KeyError('cues'), because gated_diagnostics needs T['cues'] and T['main_res'] from run_gated_arm. That was my harness, not the driver: run_seed always calls them in order.

Crash injection (TINY seed 94, arms s100 and online): a MemoryError in contamination at the second load gave one gated_diagnostics record that kept '120', with crashed.after_loads ['120']. An exception in run_online_arm before its try gave exactly one crash record. s100 ran normally, and there was no duplicate or shadowing record.

Synthetic readings with seed 21's diagnostics crashed: Part B reads CONTAMINATION-DOMINANT, Part D WORSENS and pooled CORRELATION-ATTRIBUTABLE, but Part C reads NOT SHOWN (finding R1).

predictions(), run on TINY records relabelled as seeds 44 and 45 with c=TINY, works: no skipped records, and reading inputs are produced.

guard() on the real worktree passes the dirty, HEAD-diff, ancestor, numstat and prefix checks. It then refuses with 'no committed P2-E5 power_predictions record', which is expected before predictions are committed.

The fast tests gave 10 passed (pytest -p no:cacheprovider).
