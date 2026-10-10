# P2-E4 fix verification: fixes

Fresh checker given only the files (driver at commit 1ae5030). Run 2026-10-10. Recorded verbatim.

## Verdict

Of the 31 ledger rows for "P2-E4 implementation review" (23 distinct fixes once the "same fix as" rows are merged), the fixes for every gated, verdict and validity item are correct and complete, and none of them introduced a new gated-path problem. I found no blocker.
- **The three verdict blockers (V-1/F1/R1) are fixed.** verdict() on the real bench/results/plant2.jsonl plus five gated records built from real TINY records gives the right label and keeps the first record per seed. It refuses a missing seed, a foreign digest, another experiment, gated=False and an extra seed. An earlier invalid record wins over a later valid one.
- **Labels (L-1) use the ledgered global reading consistently** in all 11 edge cases I tried.
- **Run-once markers (N-2/F13)** block a re-run after a crash. `--owner-ruled-rerun` lifts only the marker, never a recorded seed, and duplicate seeds are dropped.
- **The guard (G-1/F3)** accepts an appended predictions section and refuses both an uncommitted edit and a committed change to a frozen line, tested against real git in a scratch clone.
- **TINY seeds 90 and 91** (every arm, 113 s each) gave:
  - every gated and reported validity flag true;
  - no NaN tokens;
  - log hashes that match the decompressed content;
  - replay-vs-live joint difference 0;
  - offset_settled read after the settle: 1.27 mV against 3.99 mV online, where the old code gave about 2.2;
  - the new habituation fields present.
- **The matched-episode window (W-1/F6)** now holds 91-101 half cues on the full schedules of seeds 90-99; it held 0 before.

The remaining problems are on the predict path and in provenance hardening:
- **Major:** the P-2 fix made `p_criterion_5seeds` hold a one-seed probability under a five-seed name.
- **Minor:** predictions() would refuse forever after any re-exploration on a new tree, and explore does not refuse a dirty tree.
- **Minor:** the guard's frozen-text check fails open when the frozen commit cannot be resolved.
- **Two nits.**

Fix the major one before exploration, because predictions() is frozen with the tree.

## Findings

### PRED-1 [major] `p_criterion_5seeds` records the one-seed pass probability, not the five-seed probability its name and the reference convention claim

- where: plant2/experiments/p2_e4_online.py:1213-1215 (crit_counts incremented per simulated seed and load) and :1254 (p_criterion_5seeds = count / (5*sims)); introduced by the P-2/F4 fix (ledger rows 212, 225)
- evidence: In the joint label simulation, crit_counts[f'{M}:{k}'] gains int(val) once per (sim, seed, load), and the record divides by 5*sims. The value is therefore the mean one-seed pass rate.
- Before the fix the same key held p_criterion**5, the five-seed value.
- The frozen power_reference record states per-criterion values over five seeds (power.p2e4_o1_o3 uses p_rule(seeds=5); O4 is 0.981 over five seeds).
- Run of predictions() on synthetic full-shape exploration records (pred_check.py predicted), comparing the recorded value with the one-seed and five-seed probabilities at the same rates:

| key | recorded | one seed | five seeds |
|---|---|---|---|
| 500:O1_C1 | 0.526 | 0.514 | 0.036 |
| 500:O3_memory | 0.446 | 0.414 | 0.012 |
| 1000:O2_joint | 0.958 | 0.982 | 0.913 |

The contract requires committed 'per-criterion and per-label probabilities'. This one would be read against the gated outcome while overstating the gate probability up to about 15-fold, and predictions() is frozen with the plant2 tree, so it cannot be corrected later.
- fix: In the sims loop, also keep a per-sim AND across the five seeds:
- set `allp = {}` before the seed loop;
- inside it, `allp[key] = allp.get(key, True) and bool(val)`;
- after the seed loop, `crit5[key] = crit5.get(key, 0) + int(allp[key])` for each key.

Record `p_criterion_5seeds = {k: v / sims for k, v in crit5.items()}`, and keep the current value under `p_criterion_1seed`. Add a test assertion that p_criterion_5seeds is at most p_criterion_1seed for every key, and lower when the latter is below 1.

### PRED-2 [minor] predictions() keeps the first exploration record per seed before checking its tree, so any earlier record from another or dirty tree blocks predict permanently; explore does not refuse a dirty tree

- where: plant2/experiments/p2_e4_online.py:1157-1167 (predictions record selection), 1323-1327 (explore path); G-1/F2 fix (ledger rows 216, 223)
- evidence: `first[r['seed']]` is filled with the first P2-E4 exploration_seed record under DIGEST, whatever its tree. Only afterwards is it checked against the current tree and plant2_dirty.

The trigger is realistic. The full-config reported arms have never been run to completion. If an arm crashes after the exploration_seed record is appended (run_seed appends it before run_reported), the fix changes the tree. A re-exploration on the new tree is then ignored in favour of the old first record. The same happens if explore is launched with an uncommitted plant2 edit: explore never checks plant2_dirty, and a 35-minute run produces an unusable record.

Demonstrated (retree.py):
- records [42/T1, 43/T1, 42/T2, 43/T2] with current tree T2 give SystemExit 'exploration seed 42 ran on a different or dirty plant2 tree';
- a dirty seed-42 record followed by a clean one on the same tree gives the same SystemExit.

The results file is append-only, so recovery needs another code edit, hence another tree and another exploration cycle.
- fix: Select records first, then de-duplicate:
- keep only records with `r['git']['plant2_tree'] == g['plant2_tree'] and not r['git']['plant2_dirty']`, then take the first per seed;
- record the trees of the ignored records in the power_predictions record.

In main()'s explore branch, refuse to start when `record.git_state()['plant2_dirty']`, as run already does through guard().

### GUARD-1 [minor] guard() skips the frozen-text check silently when the frozen commit cannot be resolved

- where: plant2/experiments/p2_e4_online.py:1284-1286 (guard, numstat check against CONTRACT_FROZEN_AT)
- evidence: The check parses only stdout: `num = _git('diff','--numstat', CONTRACT_FROZEN_AT, 'HEAD', '--', CONTRACT_PATH).stdout.split(); if num and int(num[1]) != 0: refuse`.

If the revision is missing (a shallow or partial clone, a rewritten history, or a mistyped constant), git exits with rc 128 and empty stdout, and the check passes. Shown in a scratch clone (guard_check.py missing): 'rc 128 ... fatal: bad revision', then 'frozen commit not resolvable -> guard returned set()'.

In the same clone the check works when the commit exists:
- appended predictions (numstat 6/0) pass;
- a committed change of a frozen line (7/1) is refused;
- an uncommitted contract edit is refused.
- fix: Refuse unless both git calls succeed:
- `r = _git('diff','--numstat',...)`; if `r.returncode != 0`, raise SystemExit naming the frozen commit;
- also require `_git('merge-base','--is-ancestor', CONTRACT_FROZEN_AT, 'HEAD').returncode == 0`.

Extend test_guard_refuses_without_matching_committed_predictions with an R(128, '') numstat case.

### NIT-1 [nit] Ledger row 218 claims slot checks for the novel-duty arm, but that arm runs with score=False and logs no slots

- where: plant2/experiments/p2_e4_online.py:1039-1047 (novel-duty twin uses `twin.run_to(M, score=False)`); step_k logs writes_ok, proj_current and inh_ok only when score is True
- evidence: reported_arms.validity holds only novel_duty_fb_union_ok for this arm. In the TINY records the duty arm carries slot_checks and leak, while the novel-duty twin has only digests and fb union. A probe-slot store write or a stale projection in that arm would go unseen. It is a reported arm and cannot move a gated number.
- fix: Either run the twin with score=True (score_slot handles the converted novel and blank slots) and record all(writes_ok, proj_current, inh_ok) as validity.novel_duty_slot_checks, or correct the ledger text.

### NIT-2 [nit] dump_logs' recorded sha256 is of the uncompressed content, but the record points at the .gz file

- where: plant2/experiments/p2_e4_online.py:916-922 (dump_logs)
- evidence: The hash is `hashlib.sha256(data)` with data being the bytes before gzip, and path is the .jsonl.gz. On every TINY log the recorded hash matched the decompressed bytes and never the file (rec_check.py: 'file sha256 differs from recorded True'). Anyone checking provenance with `sha256sum <path>` will see a mismatch, and the gzip header (mtime) makes the file hash non-deterministic anyway.
- fix: Rename the key to `sha256_uncompressed`. Alternatively, write with `gzip.GzipFile(path, 'wb', mtime=0)` and also record the file's own sha256.

## Computed (exploratory; not results)

Everything is in ~/.cache/brain-sim/review/p2e4-fixcheck/fixes/. The repo was never written to: Python ran with PYTHONDONTWRITEBYTECODE=1, pytest with -p no:cacheprovider, BRAINSIM_CACHE pointed at my dir, and git status is clean. Only seeds 90-91 were simulated, with the TINY config. Seeds 90-99 were used only for index-only full-config schedules.

**Tests**
- 11 fast tests pass (34 s).
- The slow TINY test passes (104 s).

**tiny_run.py: TINY run_seed, seeds 90 and 91, every arm**
- 113 s each, maxrss 376 MB. Records in tiny90_explore.jsonl and tiny91_explore.jsonl; logs under cache/plant2/p2_e4/.
- Every gated validity flag is true, and so is every new reported validity flag: snapshots_untouched, main_untouched_by_twins, snapshot_untouched_by_wps, novel_duty_fb_union_ok, duty_fb_union_ok.
- fb_union_ok is checked at both loads.
- No NaN or Infinity tokens; empty populations are null.
- contract_digest equals record.digest(TINY); CONTRACT is not mutated.

**rec_check.py: the new fields in those records**
- dump_logs paths are in my cache.
  - The sha256 matches the decompressed bytes: main has 200 lines, habituation 8 entries holding rep/ctl steps, main_continuation 60 lines.
  - The gated record no longer contains 'steps'.
- twin A, the novel-duty twin and the duty arm all show replay_only = live_only = 0 and joint_live_minus_replay = 0.0.
- offset_settled against the online block offset:

| seed | M | offset_settled (mV) | online block (mV) |
|---|---|---|---|
| 90 | 120 | 1.274 | 3.992 |
| 90 | 200 | 2.071 | 7.030 |
| 91 | 120 | 1.291 | 3.904 |
| 91 | 200 | 1.989 | 6.829 |

- vector_state is three-state; mcnemar_scored is present.
- stream_pos runs 1..4; per_rep_recall is present; rec_v_onset_mean and rec_v_onset_last20 are present.
- cued_vs_blank_by_age, the novel-duty twin digests and fwd_equals_main, the duty arm's slot_checks and leak, and the window widths are all present.

**wps_window.py: full-config schedules, seeds 90-99**
- Probe writes are 164-177.
- The matched-episode window lies in stress block 1500 and holds n = 91-101 half cues (55-62 recent, 32-40 uniform). It held 0 before the fix.

**verdict_check.py: verdict() on the real results file plus gated records built from the TINY records**
- Loads were renamed 120/200 to 500/1000 and the records round-tripped through JSON.
- Result: 'ONLINE INDEX FAIL + ONLINE CONTENT FAIL + HABITUATION NOT ESTIMABLE + RECOVERY NOT ESTIMABLE', seeds 16-20, and per_seed carries rates, per_kind and habituation_state.
- A later invalid duplicate is ignored; an earlier invalid record gives INVALID.
- Seed 20 present only under another digest, another experiment, or gated False: refused.
- An extra seed 21: refused.
- An added exploration record: ignored.
- Output is strict JSON.

**labels_check.py**
- 11 edge cases, all consistent with the global reading.
- The contract's predicted outcome gives [ONLINE INDEX FAIL, HABITUATION NOT ESTIMABLE, RECOVERY NOT ESTIMABLE].

**main_check.py: main() with guard, load_records and run_seed faked; markers in my dir**
- run without --gated is refused.
- Duplicate seeds are dropped.
- A second start is refused.
- A crash leaves a marker that blocks the seed; --owner-ruled-rerun lifts it.
- A recorded seed is refused even with the flag.
- A non-gated seed and explore of a gated seed are refused.

**guard_check.py: real git in a scratch clone, with record.REPO patched**
- Appended predictions plus a committed predictions record: passes (numstat 6/0).
- Uncommitted contract edit: refused.
- Committed change of a frozen line: refused (numstat 7/1).
- Frozen commit unresolvable: rc 128 and the guard passes, which is GUARD-1.

**pred_check.py: predictions() on synthetic full-shape records**
- Defaults take about 25 s. A duplicate seed-42 record and a foreign-digest record are ignored.
- Predicted scenario: P(PASS) 0. Labels: INDEX 1.0, CONTENT 0.60, HABITUATION FAIL 1.0, RECOVERY FAIL 0.58, RECOVERY NOT ESTIMABLE 0.42. Logit shift delta 1.857, with shifted rates recorded.
- High-rate scenario: median 0.65, interval [0.06, 0.96], simulated 0.61, delta 0.049.
- p_criterion_5seeds is a one-seed value (PRED-1).

**pred_tiny.py**
- predictions() on the renamed TINY records with the real git state works (clean tree 016c444).

**p45_noise.py**
- With 20 simulations per posterior draw the O4-O5 spread is sd 0.148, against 0.137 with 400. Pool resampling dominates, so this is not reported.

**retree.py**
- Demonstrates PRED-2.
