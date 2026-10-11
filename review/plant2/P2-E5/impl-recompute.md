# P2-E5 implementation review: recompute

Independent reviewer given only the files (driver at commit f873dc5, side branch plant2-p2e5-driver). Run 2026-10-11. Recorded verbatim, before synthesis.

## Verdict

I found no disagreements. My independent recomputation of TINY seed 96 matches the driver's records exactly on all seven items, checked at both loads: items, capture, C1-C4, S2-S4 and the per-cue bits, grids, AUC, intrusion classes, own-cell share, Part B losses, the online ratio and L_o. I found no correctness bug. Separately from the recomputation there are four problems, all inside this tree. (a) A major cost problem: in Part F the spurious-cell synapse count calls np.isin once per spurious cell against the whole forward store. On a full M = 500 line (seed 97) this took 354 s, and I project about 100 min per seed at M = 1,000. The fix is a one-line change that gives the same counts. (b) A minor provenance problem: predict() takes the first diagnostics and arm records for each seed without checking their plant2 tree, so its reading inputs can come from an older tree. (c) Minor: Part D's joint difference and its AT FLOOR label are not computed anywhere. (d) Minor: crash handling and the append-only guard are weaker than the contract states.

## Findings

### F1 [major] Part F spurious-cell synapse counts call np.isin against the whole forward store once per spurious cell; about 100 min per seed at M = 1,000

- where: plant2/experiments/p2_e5_structured.py:615-617 (contamination: keys = e.store.keys; np.isin(cue_p * n + x, keys) and np.isin(cue_s * n + x, keys) for each spurious cell x)
- evidence: Allowed full-config check (seed 97, one M = 500 line, one test copy; script ~/.cache/brain-sim/review/p2e5-impl/recompute/full500_timing.py, log full500_timing.log): the forward store held 467,068 keys, with 2.87 spurious cells per half cue, giving 1,148 np.isin calls. contamination() took 354.0 s wall, nearly all of it in these calls. The same 1,148 counts from a sorted-key lookup took 1.87 s and were identical (equal = True). On this venv (numpy 2.5.3), np.isin(9 elements, sorted keys) costs 340 ms at 470k keys and 792 ms at 930k keys, because its internal np.unique(ar2) costs 371 and 815 ms; with assume_unique=True it costs 4 and 14 ms. At M = 1,000 the contract's exploration has about 19 spurious cells per cue, which means 200 x 19 x 2 = 7,600 calls x about 0.79 s, or about 6,000 s (about 100 min) per seed. The contract's whole per-seed budget is 45-55 min unloaded. Over 2 exploration and 5 gated seeds that is about 12 h extra. No number changes.
- fix: Before the freeze, replace both lookups with a sorted-key lookup, e.g. def strong(q): p = np.searchsorted(keys, q); p[p == keys.size] = 0; return int((keys[p] == q).sum()). Alternatively pass assume_unique=True (cue lines and keys are unique), or build a dense boolean forward matrix fwd[m, n] once per load and sum fwd[np.ix_(cue_p, sp)] over axis 0. I checked on 1,148 real lookups that the result is unchanged.

### F2 [minor] predictions() filters exploration_seed records by plant2 tree, but takes the diagnostics and arm records for its reading inputs from any tree (first record wins)

- where: plant2/experiments/p2_e5_structured.py:1097-1100 (diag/arms via first_records) and 886-892 (first_records has no git filter)
- evidence: In memory (script pred_mix.py), I put a copy of seed 96's records labelled plant2_tree 'OLDTREE', with the main grid best set to 0, ahead of identical current-tree records for seeds 44 and 45. predictions() skipped the old exploration_seed records ('other tree...'). It still built exploration_reading_inputs from the old diagnostics: L_c at M = 120 came out as 36 instead of the current tree's 0. This matters if exploration on 44-45 is ever re-run after a code change. The committed power_predictions record would then pair current-tree S-counts with old-tree Part B-E inputs and give no warning.
- fix: In predictions(), keep only diag and arm records whose git.plant2_tree equals g['plant2_tree'] and which are not plant2_dirty. Require one of each per exploration seed, or record which were missing, before calling readings(). For example, pass a filtered recs list to first_records.

### F3 [minor] Part D's joint difference and its AT FLOOR label (contract lines 476-478) are not computed in the record or the verdict

- where: plant2/experiments/p2_e5_structured.py:829-834 (online record) and 960-971 (readings Part D)
- evidence: The contract says: 'the joints of the online-written, P2-E3-protocol and plateau-set stores on the same raster, and their difference. The joint difference is labelled AT FLOOR on a seed where the P2-E3-protocol store's joint is below 20 cues.' It also says every reading is computed by the verdict code from the records. The online record holds twin_A online/reference/plateau/R3 joints, but no difference and no floor flag. readings() Part D returns only {ratios, reading}, and nothing in the file contains 'FLOOR'.
- fix: In readings() Part D, add per valid seed: diff_cues = round(200 * online_joint) - round(200 * reference_joint), and at_floor = round(200 * reference_joint) < 20 (cues computed from n of the twin-A half cues). Report them beside the ratio.

### F4 [minor] Crash handling is coarser than the contract's 'a crash voids that arm at that load', and the guard's 'only appended lines' check accepts insertions anywhere in the text

- where: plant2/experiments/p2_e5_structured.py:772-776 and 835-840 (one record per arm, written after both loads), 852-865 (crash record without loads; gated_diagnostics not wrapped), 1130-1135 (guard checks numstat deletions == 0)
- evidence: run_p2e3_arm and run_online_arm append their record only after the M = 1,000 load. On an exception, run_seed appends {crashed: ...} with no 'loads'. A crash at M = 1,000 therefore discards a completed M = 500 load as well. For the online arm that removes the seed's L_o at M = 500 and makes it NOT ATTRIBUTABLE there (contract lines 341-342 void only 'that arm at that load'). gated_diagnostics (line 852) is not wrapped, so an exception there skips every reported arm for the seed and aborts the remaining seeds of the `run` call. The guard accepts any diff with zero deleted lines, so a sentence inserted mid-contract passes even though lines 5 and 747 allow only appended lines. Today the contract is byte-identical to bc28cd9 (cmp).
- fix: Write each load's result as soon as it completes: either a per-load record, or carry the finished loads into the crash record so readings() can still use them. Wrap gated_diagnostics in the same try/except with a crash record. In guard(), require `git show bc28cd9:docs/plant2/P2-E5-structured-items.md` to be a byte prefix of HEAD's contract.

## Computed (scripts and numbers)

Scripts and outputs are in /root/.cache/brain-sim/review/p2e5-impl/recompute/, with BRAINSIM_CACHE set to the bscache/ folder there. Nothing in either repository was touched.

I ran the driver once: run_seed(TINY, 96, gated=False, c4=E4_TINY), 223 s, 8 records in results_seed96.jsonl, every validity flag True. My independent code (indep.py, indep2.py, indep_online.py, indep_online2.py, compared by compare.py) runs e3.E3 with my own stream-table generator. It captures spikes through a hook on the memory LIF's step (not Net.step). It rebuilds the test copy with run_phase, builds my own cues, and scores rec lines myself from replay's trace.

(1) Items 1..200 and the families match the driver's FamilyGen exactly. Sibling overlap is 18.513684211 in both (TINY bounds 12-22). The persisted E, A, R, continuation cells/counts/first ticks and learning raster all equal my capture. At full config, all 1,000 items of the main, s80, s40, F40 and pooled generators match my code on seeds 90-99. The main-arm overlap is 16.898-16.933, inside 15-19. The (seed, 22, M) block cues match for 2 seeds x 2 loads x 4 arm specs.

(2) C1/C2/C3/C4r/C4s/S2/S3/S4, mine = driver:
- M = 120: 35/38/20/17/18/30/20/12.
- M = 200: 33/31/20/18/15/5/19/1.
- The per-cue joint and index bit strings are identical, as are D1 (40/40) and D2 (30/5).
- Drift is 0.07305 and 0.10118 mV. R matches the cells with at least 1 captured spike. My R1 and A x E stores are bit-equal to fb and fb_plateau.

(3) Grid best cues (J, g) and passing points, mine = driver:
- plateau store: M = 120 40 (2.8, 0.3), 2 passing; M = 200 27 (2.0, 0.3), 0 passing.
- main store: 36 (2.0, 0.3), 1 passing; 14 (2.0, 0.3), 0 passing.
- R3 store: 39, 2 passing; 27, 0 passing.
- Frozen-point cues (plateau/main/R3): 40/30/39 at M = 120 and 18/5/20 at M = 200.

(4) Count AUC by brute-force pairs:
- M = 120: 0.9982465029 (n_pos 864, n_neg 466).
- M = 200: 0.9926763482 (827, 1006).
- The first-spike AUCs (0.76746, 0.79054) and both histograms are identical.
- The online arm, from my own capture: AUC 0.9996004 and 0.9983243. Its R3 twin-A joint is 1.0 and 0.45 (intrusion medians 0 and 13). The twin_A call is deterministic.

(5) All 40 half cues, 5 intrusion classes x {main, plateau} x {mean, median}, both loads, match. For example, M = 200 main: proto 32.125/35, later-only 91.65/49, earlier-only 25.25/2, both 11.175/3, other 43.85/29.5.
- Own-cell share (timed rule): M = 120 median 0.857143, mean 0.846096, n = 25; M = 200 0.635872, 0.615913, n = 39.
- Spurious cells per cue are 2.075 and 5.675, with sibling-plateau share 0.7653 and 0.8831.
- The label-permuted fractions and Part G block statistics also match.

(6) Part B from the records (bar 36, material 4, margin 2 at n = 40):
- M = 120: L_c 0 (frozen 6), L_i 0, L_o 16, which reads OPERATING_POINT and is attributable.
- M = 200: L_c 13, L_i 9, L_o 20. It is NOT ATTRIBUTABLE because s100 fails the P2-E3 gate (joint 0.85).
- The driver's readings() gives the same values. I also ran verdict() and predict() on relabelled copies of these records in memory, and neither crashed.

(7) The online arm, rerun with P2-E4's frozen Online, my generator and my gated fb store as the reference store, matches exactly:
- M = 120: ratio (13+1)/(1.5+1) = 5.6. McNemar memory [1, 17] and content [19, 1] give L_o max(0, 16, -18) = 16.
- M = 200: ratio (595+1)/(162.5+1) = 3.6452599. McNemar [1, 21] and [18, 1] give L_o 20.
- Block rates are identical, and the online items and A equal the gated arm's.

Timing for F1 (full500_timing.log): full config, seed 97, M = 500. The forward store held 467,068 keys and the fb store 1,886,089. contamination() took 354.0 s for 1,148 lookups; the searchsorted variant took 1.87 s and gave identical counts. That run's joint was 0.14 and C2 0.915.
