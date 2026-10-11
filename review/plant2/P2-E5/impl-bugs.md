# P2-E5 implementation review: bugs

Independent reviewer given only the files (driver at commit f873dc5, side branch plant2-p2e5-driver). Run 2026-10-11. Recorded verbatim, before synthesis.

## Verdict

I found no blocker. I traced every gated number, validity flag, label and predeclared reading in the driver against the contract, and each one matches the frozen rules. The checks run were the fast tests (9 passed), a full TINY end-to-end run (seed 96), one full-scale M = 500 line (seed 90), synthetic-record verdicts and crash injections. They found no crash in any gated, predict or verdict path.

There is one major problem: the cost of Part F's spurious-cell synapse count. As written, I estimate it adds about 1.5 h per seed at M = 1,000 under the current two-lane load, extrapolated from the measured M = 500 time and a synthetic benchmark at M = 1,000 store size. That roughly doubles the contract's per-seed cost. A one-line exact fix exists.

The other findings are minor or nits:
- a crash in `gated_diagnostics` is not contained, so it loses that seed's reported arms;
- `predictions()` does not filter the reported-arm records by tree;
- Part D's AT FLOOR label and joint difference are not computed;
- the online arm records no A digest;
- the specificity flag reads False when no diagnostics record exists;
- the persistence file is zip, not gzip;
- the guard's "only additions" check is weaker than "only appended lines".

All of these should be fixed before the tree is frozen, since the fixes change the tree.

Items checked and found correct:
- **Family generator.** Draw order, sorting, k >= 1, and the pooled, block and mask draws all follow the stream table, with F = 40 handled.
- **CaptureMixin.** It counts exactly t_item + t_cont steps, with the continuation as the last 50. It is identical to unmodified E3 and Online, the wrapper is removed in `finally` and never reaches deep copies, and `capture_ok`, `fb_union_ok` and the R_1 check all hold at full scale.
- **`test_copy`.** The gated raster and onsets are snapshotted before the block, and the block keeps the full raster with its own onsets. On seed 90 at full scale: `unchanged` is True, 180,600 gated ticks against 225,800 total, 600 + 150 onsets.
- **`readout_full`.** It is bit-identical to `e3.readout` at TINY and at full scale.
- **`FirstLines`.** Window [onset, onset + 75), arm 0 only, ticks relative to onset; line counts equal the replay's totals.
- **`grid_summary`.** Grid order is J then g, ties go to the first maximum, cues are integers, and the frozen point is found.
- **`store_from` and `permuted_store`.** pi is a within-family derangement (checked at full scale).
- **`contamination()`.** The classes are exclusive and exhaustive over lines outside x, siblings are ordered by storage index at load M, and the own-cell timing rule is fm <= t_j - 1. The spurious-cell rule and the label-permuted fractions match the contract.
- **`block_stats`, `arm_validity` and `load_valid`.** Validity 1, 2a, 2b, 3, 4, 5, 6 and 7 are each computed on the right object.
- **Online arm.** `ref_store` is the gated store at the same load. L_o = mcnemar[1] - mcnemar[0], clipped at 0, so it counts settled-pass/online-fail minus the reverse. The ratio is (median + 1)/(median + 1), the validity list is complete, and the blobs match tree 9152f1e4.
- **`readings()`.** Parts B-E and s = 100 follow the contract's ordered, exclusive rules with the right denominators, and the verdict and labels are correct.

## Findings

### F1 [major] Part F's spurious-cell forward-synapse count calls np.isin against the whole forward store once per spurious cell, adding about 1.5 h per seed at M = 1,000

- where: plant2/experiments/p2_e5_structured.py:615-617 (contamination)
- evidence: Each spurious cell x makes two calls, `np.isin(cue_p * n + x, keys)` and `np.isin(cue_s * n + x, keys)`, against `keys = e.store.keys`. With a store of about 0.5-0.9 M keys and a 16 M key range, numpy 2.5.3 falls back to its sort method, which re-sorts the whole store on every call.
- **Measured at M = 500** (full scale, seed 90, `scripts/full500.py`): the contamination step took 460 s. That is 3.625 spurious cells per cue x 2 calls x 200 cues = 1,450 calls at about 0.31 s each. The other parts of `gated_diagnostics` took seconds to a minute.
- **Synthetic benchmark at M = 1,000 size** (P2-E1's records give 930,107 forward keys at M = 1,000): 19 spurious cells (the contract's figure for seed 44) took 14.35 s per cue for the prototype half alone. With both calls, 200 cues come to about 1.6 h under the current two-lane load (load average 2.5 on 4 CPUs).
- This alone roughly doubles the contract's 45-55 min per seed (1.5-2 h contended). It applies to every exploration and gated seed, after the freeze.
- fix: Build a dense boolean forward matrix once per load and index it. The result is exact; I checked it gives identical counts on a synthetic 930 k-key store, in 1.8 ms instead of 14.35 s.
```
W = np.zeros(c["m"] * n, bool); W[e.store.keys] = True; W = W.reshape(c["m"], n)   # once, before the cue loop
...
spur_proto.append(float(W[cue_p][:, sp].sum(0).mean()))
spur_spec.append(float(W[cue_s][:, sp].sum(0).mean()))
```
`np.searchsorted` on the already-sorted keys is an alternative.

### F2 [minor] A crash in gated_diagnostics is not contained: that seed's reported arms are all lost and a multi-seed run aborts

- where: plant2/experiments/p2_e5_structured.py:852 (run_seed), 1172-1180 (main run loop)
- evidence: Every reported arm runs inside `try/except Exception`, which appends a `crashed` record, but `gated_diagnostics` runs outside it.
- **Demonstrated on TINY seed 97** (`scripts/crash_arm.py`): a synthetic ValueError in `gated_diagnostics` propagated out of `run_seed`. Only the `exploration_seed` record was written; s100 and the online arm never ran. A synthetic MemoryError in the s80 arm, by contrast, was recorded as crashed and s100 still ran.
- **On a gated seed** the run-once marker is already written, so that seed's Parts A-G are lost without an owner's ruling. That seed counts as NOT ATTRIBUTABLE in Part B, NOT ESTIMABLE in D and E, and NOT SHOWN in C.
- **In `run --seeds 21 22 23 24 25`**, the exception also stops the loop, so the remaining seeds are not started.
- No actual crash path was found at TINY or at full M = 500.
- fix: Wrap `gated_diagnostics(...)` in run_seed the same way as the arms. On an exception, append `dict(experiment="P2-E5", kind="reported_arm", arm="gated_diagnostics", seed=seed, gated=gated, contract_digest=..., crashed=repr(ex), ...)` and continue with the other arms. `readings()` already treats a diagnostics record without "loads" as missing.

### F3 [minor] predictions() takes exploration reported-arm and diagnostics records without filtering by tree, so the committed reading inputs can come from an older, crashed run

- where: plant2/experiments/p2_e5_structured.py:1097-1100 (predictions)
- evidence: The `exploration_seed` records are filtered: current plant2 tree, not dirty, seeds 44-45. But `diag = first_records(recs, "reported_arm", gated=False, arm="gated_diagnostics")` and the arm records take the first record per seed under DIGEST, from any tree. DIGEST does not change with the code.
- **Demonstrated** (`scripts/predict_tree.py`): I put crashed online records for 44/45 from an older tree ahead of a complete current-tree exploration. `exploration_reading_inputs` then read Part B NOT ATTRIBUTABLE and Part D NOT ESTIMABLE at both loads. The same current-tree records alone give OPERATING-POINT-DOMINANT and WORSENS at M = 120.
- Any re-exploration after a fix would trigger this. The `power_predictions` record is committed and gates the run.
- fix: Pre-filter before calling first_records: `cur = [r for r in recs if r.get("git", {}).get("plant2_tree") == g["plant2_tree"] and not r["git"]["plant2_dirty"] and r.get("seed") in EXPLORE_SEEDS]`. Take `diag` and `arms` from `cur`.

### F4 [minor] Part D's joint difference and its AT FLOOR label are computed nowhere

- where: plant2/experiments/p2_e5_structured.py:961-971 (readings Part D), 829-834 (run_online_arm)
- evidence: The contract (lines 476-478) asks for the joints of the online-written, P2-E3-protocol and plateau-set stores, and their difference. The difference is labelled AT FLOOR where the P2-E3-protocol joint is below 20 cues. Line 341 says every reading is computed by the verdict code.
- The online record has the three joints (`twin_A.online`, `reference`, `plateau`).
- Neither `run_online_arm` nor `readings()` computes the difference or the AT FLOOR label. `grep FLOOR` finds nothing in the driver.
- The prediction expects the reference joint near 0 at M = 1,000, so the label matters there.
- fix: In readings Part D, for each valid seed record `diff_cues = cues_count(online joint, 200) - cues_count(reference joint, 200)` and `at_floor = cues_count(reference joint, 200) < cues_count(c["material_frac"], 200)`. Report them beside `ratios`.

### F5 [nit] The online arm records no digest of its A lists

- where: plant2/experiments/p2_e5_structured.py:803-834 (run_online_arm)
- evidence: Contract line 209: "Every arm records a digest of its A lists." The P2-E3-protocol arms record `A_digest` per load (lines 389, 478, 761), but the online arm's loads do not. A should be identical to the gated arm (same plateau stream), and the online arm is where that pairing is least obvious.
- fix: Add `A_digest=hashlib.sha256(b"".join(a.astype(np.int64).tobytes() for a in o.A[:M])).hexdigest()[:16]` to the online arm's per-load record.

### F6 [nit] On a PASS, the specificity flag reads False when no diagnostics record exists

- where: plant2/experiments/p2_e5_structured.py:1039-1042 (verdict)
- evidence: `spec_flag = any(... for d in diag.values() for M in loads)` is False when diag is empty or covers fewer than 5 seeds. With synthetic records (all parts passing, no diagnostics records), `pass_specificity_check_failed` came out False. That reads as "check passed" when the check was not done. It is reachable only on a PASS.
- fix: Set `spec_flag = None` unless every gated seed has a diagnostics record with "loads"; otherwise compute it as now.

### F7 [nit] The persistence file is a zip (np.savez_compressed), not gzip as the contract says

- where: plant2/experiments/p2_e5_structured.py:458-462 (persist); contract line 571
- evidence: The contract says "gzip in ~/.cache/brain-sim/plant2/p2_e5/", but `np.savez_compressed` writes a deflate zip (.npz). The sha256 is recorded, so replay is unaffected.
- fix: Either write `gzip.compress` of an `np.savez` buffer, or have the record say `format: "npz (zip deflate)"`.

### F8 [nit] The guard checks for additions only, not for appended lines

- where: plant2/experiments/p2_e5_structured.py:1130-1135 (guard)
- evidence: The contract (lines 5 and 748) allows only appended lines. `git diff --numstat` checks only that the deletion count is 0, so a line inserted mid-contract, for example in the readings, would pass. P2-E4's guard behaves the same way.
- fix: Also require that the frozen text is a prefix of HEAD's text: `_git("show", f"{CONTRACT_FROZEN_AT}:{CONTRACT_PATH}").stdout` must equal the start of `_git("show", f"HEAD:{CONTRACT_PATH}").stdout`.

## Computed (scripts and numbers)

All scripts and outputs are in ~/.cache/brain-sim/review/p2e5-impl/correctness/ (scripts/, out/, cache/). Nothing was written in either repository.

- **Fast tests:** `pytest -m "not slow" plant2/tests/test_p2_e5.py` gave 9 passed (14 s).
- **TINY end-to-end** (`scripts/tiny_e2e.py`, seed 96, TINY + E4_TINY, 211 s):
  - every validity flag is True at 120 and 200; shuffled_ok and overlap_ok are True (overlap 18.5);
  - the online arm is valid at both loads, with blobs_ok True, capture_ok True and twins_untouched True;
  - L_o is 16 and 20 cues; McNemar memory [1, 17] and [1, 21] gives net = settled-pass/online-fail minus the reverse, the correct sign;
  - count AUC 0.998/0.993; label-permuted perm_spec 0.05 against main 0.99;
  - every record serialises and no arm crashed.
- **Full scale, M = 500, seed 90** (`scripts/full500.py`, real CONTRACT, frozen point only, no grid):
  - learning took 30 s; the test copy and block took 25 s; unchanged = True; n_ticks 180,600 gated and 225,800 with the block; onsets 600 + 150; drift 0.063 mV;
  - capture_ok, fb_union_ok and R_1 = main are all True; sibling overlap is 16.90;
  - `readout_full` is identical to `e3.readout`;
  - vector: C1 198, C2 179, C3 200, C4 99/86, S2 18, S3 200, S4 0;
  - pi is a derangement within families;
  - Part F: own-cell share median 0.89; spurious cells 3.6 per cue, 99 % sibling plateau cells; label-permuted spec fraction 0.065 against 0.988;
  - Part G: new exemplars have median 1 responder and median 0 lines; prototype cues have median 102.5 responders and about 980 lines;
  - count AUC 0.999.
  - The values are consistent with the contract's exploratory predictions. The contamination step took 460 s (finding F1).
- **np.isin timing** on synthetic sorted keys: 0.38, 0.87 and 2.0 s per call at 0.5 M, 1 M and 2 M keys. The dense-matrix replacement gives identical counts in 1.8 ms.
- **Synthetic verdicts** (`scripts/synthetic.py`):
  - the base case reads CONTAMINATION-DOMINANT, WORSENS and CORRELATION-ATTRIBUTABLE, with s = 100 REPLICATES and Part C AVAILABLE FROM ACTIVITY;
  - crashed online records give NOT ATTRIBUTABLE and NOT ESTIMABLE;
  - crashed s = 100 records give NOT ATTRIBUTABLE and s = 100 NOT ESTIMABLE;
  - with no diagnostics records, Part C reads NOT SHOWN;
  - an s = 100 arm void at M = 1,000 on one seed still gives REPLICATES (4 non-void seeds);
  - a crashed pooled arm gives NOT ESTIMABLE;
  - the PASS case works, and a PASS with no diagnostics records gives spec_flag False (F6).
- **Predictions** run on relabelled TINY records with no crash (`scripts/predict_fake.py`), but pick up stale-tree records (`scripts/predict_tree.py`, F3). The real `guard()` refuses with "no committed P2-E5 power_predictions record".
- **Crash injection** (`scripts/crash_arm.py`): a crash in an arm is recorded and the next arm runs. A crash in `gated_diagnostics` propagates and no reported arm runs (F2).
- **Blob check:** all seven reused blobs equal their blobs in tree 9152f1e4.
