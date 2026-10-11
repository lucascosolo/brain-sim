# P2-E5 driver fix-check: fixes

Independent checker given only the files (driver at commit 7cfe62c, branch plant2-p2e5-driver). Run 2026-10-11. Recorded verbatim, before synthesis.

## Verdict

All 20 ledger rows of the P2-E5 implementation review are fixed correctly in 7cfe62c. I found no blocker, major or minor problem. I found 7 nits. One fix is only partly right: F6, the specificity flag (N1). The other six nits are small gaps or weak spots in otherwise correct fixes. None of them can change the verdict, a validity flag or a predeclared reading on a run where nothing crashes. The tree can be frozen as it is; N1 to N4 are cheap to fix first if you want them.

How each row stands:
- **bugs-F1, recompute-F1 (spurious-cell lookup speed).** Correct, exact and complete. n_in_sorted gives the same counts as np.isin, and contamination() is about 160 times faster at M = 500.
- **bugs-F2, conformance-C1 (gated_diagnostics crash).** Correct.
  - A crash inside the per-load loop is recorded together with the loads already done.
  - A crash before the loop goes to the new handler in run_seed, which writes a crash record; the s100, s80, s40, pooled, F40 and online arms still run.
  - Weak spot (N2): a crash at M = 500 also loses M = 1,000, although both loads are already computed.
- **bugs-F3, conformance-C6, recompute-F2 (predictions tree filter).** Correct. Records from an older tree, a dirty tree, a gated run or another seed are all excluded.
  - Weak spot (N5): the committed record does not say which arm records it used.
- **bugs-F4, conformance-C3, recompute-F3 (Part D joints and AT FLOOR).** Correct. The joints, the difference and AT FLOOR are computed, with the label switching between 19 and 20 cues as the contract says.
- **bugs-F5, conformance-C5 (online A digest).** Correct. The online arm's A digest equals the gated arm's at both TINY loads.
- **bugs-F6 (specificity flag).** Partly correct (N1).
- **bugs-F7 (gzip).** Correct. The file is an uncompressed npz inside gzip, the format is recorded, and the sha256 matches.
- **bugs-F8, conformance-C7 (guard).** Correct. An inserted line is refused and an appended line is accepted, checked against a real scratch git repo.
- **conformance-C2, recompute-F4 (crash at the second load).** Correct. A crash at the second load keeps the first, and readings() treats only the missing load as void.
  - The new per-load handover leaves learning unchanged: the work done at M = 500 reads only the test copy.
  - Weak spot (N4): the eligible-fraction and mean |A| check (validity 3) changed for reported arms at M = 500.
- **conformance-C4 (per-cue outcomes persisted).** Correct. All 600 cue rows plus the half-cue and novel-cue measures are in the file.
- **conformance-C8 (dose-response skips void loads).** Correct.
  - Weak spot (N6): the counts are no longer tied to seeds.

All 63 fast plant2 tests and both slow P2-E5 tests pass. The worktree's git status is clean.

## Findings

### N1 [nit] Specificity flag reads None (check not done) even when a seed with diagnostics shows a definite failure

- where: plant2/experiments/p2_e5_structured.py:1099-1102 (verdict)
- evidence: The F6 fix returns None unless every gated seed has diagnostics at every load. But the check is an any-rule, so one seed-load with perm_spec > 0.5 x main_spec decides it whatever the missing seeds hold. Script scripts/spec2.py, synthetic PASS records:
- seed 25 has perm_spec 0.9 against main_spec 0.98 at M = 500;
- seed 23's diagnostics crashed after M = 500;
- verdict() returns PASS with pass_specificity_check_failed = None.
So the PASS is not flagged, although the contract sends exactly this case to the owner. Without the missing load the same records give True (synth.py: 'PASS one seed perm_spec high: True').
- fix: Compute the flag over the diagnostics that are present:
```
hit = [d['loads'][M]['contamination']['label_permuted'] for d in diag.values() for M in loads if M in d.get('loads', {})]
spec_flag = True if any(x['perm_spec'] > c['specificity_ratio'] * x['main_spec'] for x in hit) else (None if not complete else False)
```
where `complete` is the current all-seeds-all-loads test.

### N2 [nit] A gated_diagnostics crash at M = 500 also voids M = 1,000, although both loads are already computed

- where: plant2/experiments/p2_e5_structured.py:741-773 (one try around the whole `for M, T in loads.items()` loop)
- evidence: The diagnostics loop works on loads that are already finished; each T holds its own test copy and raster. An exception at M = 500 still leaves the loop, so M = 1,000 is never tried. The contract says a crash voids 'that arm at that load'. In readings(), that seed is then missing from Part B and Part C at both loads, and Part E has no plateau_gain at either load.

The opposite order is handled correctly: in the crash97 run, a crash at the second load kept M = 120. For the P2-E3-protocol arms and the online arm, a learning crash at 500 rightly stops 1,000; this point is only about diagnostics.
- fix: Put the try inside the loop. On an exception, append `dict(M=M, error=repr(ex))` to a list in `out['crashed']` and `continue`. readings() already treats a missing load as void.

### N3 [nit] Part C's per-seed list shows False both for a seed that failed and for a seed whose diagnostics are void

- where: plant2/experiments/p2_e5_structured.py:1003-1007 (readings, Part C)
- evidence: A missing diagnostics load appends False, the same value a seed gets when it fails the AUC or the R_3 tolerance. In the crash97 run (diagnostics crashed at M = 200), Part C at 200 reads {'per_seed': [False], 'ok': False}, and overall Part C is NOT SHOWN.

Now that the F2 fix keeps partial diagnostics records, this case is more likely. The record cannot tell 'not available from activity on this seed' from 'not measured'. Parts B and D already use None for a missing input.
- fix: Append None for a missing D. Keep `ok = bool(okC and all(x is True for x in okC))`, so the reading is unchanged (NOT SHOWN) but the cause shows in the record.

### N4 [nit] Reported arms now check eligible fraction and mean |A| (validity 3) at M = 500 over items 1..500 only, unlike the contract wording and the gated arm

- where: plant2/experiments/p2_e5_structured.py:425-434 (load_validity), compared with 410-422 (arm_validity, gated arm)
- evidence: The contract's validity 3 reads: mean eligible fraction >= 0.95 and mean |A| 18.5-21.5 'at M = 1,000'.
- At f873dc5, reported arms evaluated it over items 1..g1, that is 1..1,000, for both loads. The gated arm still does.
- load_validity now uses items 1..M. In crash97, s100 at M = 120 has mean_A 19.63 over 120 items.
The change is a defensible way to keep M = 500 when M = 1,000 crashes, but it is not mentioned in the ledger action. It can make an M = 500 load valid while M = 1,000 is void, where the old code voided both. At full scale (mean |A| about 20 against bars 18.5-21.5) the effect is practically nil.
- fix: Record the choice, for example `v['validity3_items'] = [1, M]`, and add a one-line ledger note. Or, after a clean M = 1,000 load, also mark the M = 500 load invalid if the M = 1,000 check fails, which keeps the crash semantics.

### N5 [nit] power_predictions does not record which reported-arm records it used or dropped

- where: plant2/experiments/p2_e5_structured.py:1157-1168 (predictions)
- evidence: The tree filter works. pred_tree.py checked older-tree, dirty-tree, gated-flag and non-exploration-seed records placed ahead of the current ones; the reading inputs equal readings() run on the current-tree records alone.

When the current tree has no arm records, the inputs silently read 'Part B NOT ATTRIBUTABLE, Part D NOT ESTIMABLE', with no note that the arms were absent or filtered out. skipped_records lists only exploration_seed records. The recompute review (F2) asked to 'record which were missing'.

This record is committed and gates the run, so a crashed arm cannot be told apart from an exploration run on another tree or one run with --no-reported.
- fix: Add `reported_arms_used={a: sorted(arms[a]) for a in arms} | {'gated_diagnostics': sorted(diag)}` to the record, plus the count of reported_arm records dropped by the tree filter.

### N6 [nit] Dose-response McNemar lists are not tied to seeds, so after a void load is skipped the remaining counts cannot be matched to seeds

- where: plant2/experiments/p2_e5_structured.py:1060-1070 (readings, dose)
- evidence: `dose[...]` is a plain list in seed order. synth.py: with s80 void at M = 500 on seed 21 and s40 missing its M = 1,000 load on seed 22, s80_vs_main has 4 entries at 500 and main_vs_s40 has 4 at 1,000, with no seed labels. Before the C8 fix every seed with both records appeared, so the skip is what makes the list ambiguous.
- fix: Key the counts by seed: `mc[str(s)] = [b, c]`, with `mc = {}`.

### N7 [nit] The new slow crash test asserts on load '1000', which never exists at TINY

- where: plant2/tests/test_p2_e5.py:298
- evidence: TINY's gate_M is (120, 200), so `"1000" not in rec["loads"]` always holds. The test never checks that the record written to the file lacks the crashed second load; the line above only checks the returned `out`.
- fix: Use `"200" not in rec["loads"] and rec["crashed"]["after_loads"] == ["120"]`.

## Computed (scripts and numbers)

Everything is under ~/.cache/brain-sim/review/p2e5-fixcheck2/fixcheck/ (scripts/, out/, bscache/), run with PYTHONDONTWRITEBYTECODE=1 and BRAINSIM_CACHE pointed there. Nothing was written in either repository, and `git status` on the worktree is clean.

**Tests**
- `pytest plant2/tests/test_p2_e5.py -m "not slow"`: 10 passed.
- The slow P2-E5 tests (TINY end-to-end and the crash at the second load): 2 passed in 200 s.
- All fast plant2 tests: 63 passed.

**n_in_sorted (nin.py)**
- 3,000 random trials against np.isin gave 0 mismatches. The queries included the first and last stored keys, values just outside both ends, 0, unsorted queries and empty queries.
- Single-key and empty stores also matched.
- On a 395k-key BinarySynapses store (sorted, unique, int64) the results matched for int64 and int32 queries, for the end keys, and for duplicated queries.

**Crash injection (crash_run.py and crash_read.py, TINY seed 97, 157 s)**
- Three injected crashes, each at the second load:
  - s100: MemoryError in test_copy;
  - gated_diagnostics: ValueError in contamination;
  - online: RuntimeError in twin_B.
- Each record kept load 120 with `crashed = {after_loads: ['120'], ...}`. s80, s40, pooled and F40 completed. Every record has git and runtime.
- readings() with min_seeds = 1, at M = 120:
  - Part B OPERATING-POINT-DOMINANT (L_c 3, L_i 0, L_o 16);
  - Part C ok;
  - Part D WORSENS, joints online 23 / reference 32 / plateau 39 (difference -9, not AT FLOOR, A digest matches);
  - pooled CORRELATION-ATTRIBUTABLE.
- At M = 200: Part B NOT ATTRIBUTABLE (row None), Part C [False], Part D NOT ESTIMABLE, pooled plateau_gain None.
- s100 reads NOT ESTIMABLE and overall Part C NOT SHOWN.
- Pre-loop diagnostics crash (outer.py): run_seed wrote one crash record and then ran s100, s80, s40, pooled, F40 and online. gated_info was passed with fb and A_digest.

**Persistence**
- TINY seed 97: the file is gzip (magic 1f8b) wrapping a stored zip/npz; the sha256 matches the record.
- It holds:
  - cue_{kind, missing, item, total, visible, *_short}_M with 100 entries;
  - half_recall50, half_spurious and half_A_size with 40 entries;
  - novel_ignition with 20 entries;
  - the rasters and E, A, R and continuation arrays.
- Full config, M = 500 (seed 91): persist took 2.2 s. The file is 1.04 MB gzipped (3.7 MB uncompressed).

**Synthetic readings (synth.py)**
- Part D: reference joint 0.095 gives 19 cues and AT FLOOR True; 0.10 gives 20 and False; 0.0 gives True with difference +6.
- An invalid online seed, or one with no reference store, gets no joints entry.
- Dose-response: an s80 load marked invalid and an s40 load missing are both skipped (4 of 5 entries).
- Specificity flag:
  - all diagnostics present: False;
  - one seed missing, partial or empty: None;
  - a pre-loop crash record listed first: None;
  - a seed with high perm_spec: True;
  - not a PASS: None.
- spec2.py: a high perm_spec on one seed plus missing diagnostics on another gives None (N1).

**Predictions (pred_tree.py, git_state monkeypatched)**
- Records were relabelled to seeds 44 and 45. Older-tree, dirty-tree and gated-flag arm records were placed first, and seed-46 records added.
- The reading inputs equal readings() run on the current clean tree alone (True).
- With arm records from the older tree only: Part B NOT ATTRIBUTABLE and Part D NOT ESTIMABLE, with no note of the missing arms in the record.

**Guard (guard_git.py, a real scratch git repo seeded with the frozen bc28cd9 contract, _git monkeypatched)**
- Unchanged and appended contracts pass.
- A line inserted mid-text, a line inserted at the top, and a blank line inserted mid-text are all refused by the new prefix check.
- A modified line and an extended last line are refused by numstat.
- On the real worktree (read-only), the frozen and HEAD contracts are 48,901 chars each and HEAD's starts with the frozen text. guard() refuses with 'no committed P2-E5 power_predictions record'.

**A digests (slow end-to-end test, TINY seed 95)** The gated, s100, s80 and online arms give identical A_digest at both 120 and 200, and A_digest_matches_gated is True.

**Timing (full500.py, the one allowed full-config M = 500 line, seed 91, with one P2-E4 lane running)**
- The gated arm took 78 s; the main, plateau and permuted replays took 15.3 s.
- contamination() took 2.4 s in total.
- The spurious-cell lookups on the real 471,107-key forward store (657 spurious cells, 1,314 lookups):

| method | lookups | time |
|---|---|---|
| n_in_sorted | 1,314 | 0.013 s |
| old np.isin | 432 (a subset) | 127.6 s, 295 ms each |

- The two methods gave identical counts on those 432 lookups.
- The old method would have needed about 388 s for this load, so the speed-up is confirmed.
