# P2-E4 fix verification: regressions

Fresh checker given only the files (driver at commit 1ae5030). Run 2026-10-10. Recorded verbatim.

## Verdict

The gated path at 1ae5030 is sound. On TINY seeds 90 and 91 (gated=False, results in my cache) every validity flag is True, no defect would change a gated number, label or validity, and no gated or verdict path crashes. One regression from the fix commit sits in the predict path: the committed power_predictions field `p_criterion_5seeds` now holds per-seed pass rates, not five-seed probabilities, so the per-criterion predictions would be overstated by up to an order of magnitude (major). A second, minor problem: one exploration record from a dirty tree, from another tree or from a stray seed blocks `predict` for good, and re-running exploration cannot clear it. There is also one nit about reported habituation fields. All of these are in the plant2 tree, so they need fixing before exploration on seeds 42-43. Everything else checked holds. Disclosure: my first script imported plant2.tests.test_p2_e4, which created the git-ignored bytecode file plant2/tests/__pycache__/test_p2_e4.cpython-313.pyc inside the repo. It does not affect `git status`, plant2_dirty (False) or plant2_tree (016c444a). Under the no-delete rule I left it; it can be removed by hand. All later runs used `python -B`.

## Findings

### PRED-5SEEDS [major] power_predictions.p_criterion_5seeds now holds per-seed pass rates, not five-seed probabilities (regression from 1ae5030)

- where: plant2/experiments/p2_e4_online.py:1198-1215 (crit_counts in the joint label simulation) and 1254 (p_criterion_5seeds = v / (5 * sims))
- evidence: crit_counts[f"{M}:{k}"] is incremented once per simulated seed and load, then divided by 5*sims. The result is the probability that one seed passes, stored under the name the pre-fix code used for p_criterion**5 (the probability that all five seeds pass). I ran predictions() on synthetic exploration records at contract-like rates (pred_check.py; results only in my cache). For 500:O1_C1 the record holds 0.522, while the per-seed p_criterion at the posterior mean is 0.514 and five seeds give 0.036. For 500:O3_memory: 0.362 recorded, 0.003 for five seeds. For 1000:O2_joint: 0.968 recorded, 0.913 for five seeds. The contract ("What is committed: ... per-criterion and per-label probabilities") means probabilities for the gate, which needs all five seeds. The committed values would overstate them by up to about 100x, and the record is frozen with the tree. In the joint simulation, seeds within one simulation share a posterior draw, so the correct value cannot be recovered later as (per-seed)**5. test_predictions_run_on_exploration_records_and_refuse_foreign_trees checks only that the key exists.
- fix: In the sims loop, keep a per-simulation flag all_ok[f"{M}:{k}"] that is ANDed across the five seeds, and record p_criterion_5seeds = count(all_ok)/sims. Keep the current per-seed value under a new key, p_criterion_per_seed. Add a test with a fixed rate and a large sims count asserting that p_criterion_5seeds is close to the independent five-seed value.

### PRED-STALE-FIRST [minor] One exploration record from a dirty tree, another tree or a stray seed blocks predict permanently; explore does not refuse a dirty tree

- where: plant2/experiments/p2_e4_online.py:1158-1167 (predictions: first record per seed taken before the tree check, and exact seed-set check) and 1323-1327 (main explore: no plant2_dirty check)
- evidence: predictions() keeps the first exploration_seed record per seed with DIGEST, then requires the seed set to equal (42, 43) and every kept record to match the current clean tree. The results file is append-only, so a re-run cannot replace a bad first record. Reproduced (pred_trap.py): records [42 dirty, 43, 42 clean re-run] give SystemExit 'exploration seed 42 ran on a different or dirty plant2 tree'. Records [42, 43, 44] give SystemExit 'have [42, 43, 44]'. run_seed/explore never check plant2_dirty and accept any non-gated seed, so one exploration started before a commit (or `explore --seeds 44`) makes the predict path unreachable without editing plant2. Recovering then costs a code change plus a full exploration re-run.
- fix: In main's explore branch, refuse when record.git_state()['plant2_dirty'] is True, and refuse seeds outside EXPLORE_SEEDS (or require a flag). In predictions(), keep records only if seed in EXPLORE_SEEDS, git.plant2_tree equals the current tree and plant2_dirty is False, and take the first such record per seed. Then require exactly (42, 43), and list any skipped records (seed, tree, dirty) in the power_predictions record.

### HAB-REC-ONSET [nit] Ledger R-1's 'rec v at copy slot onset beside the main line's last-20-step mean' is only partly in the record

- where: plant2/experiments/p2_e4_online.py:604-606 (hab_copy info), block_criteria rec_onset_v at line 495
- evidence: The ledger row for R-1 says the fix adds 'rec v at each copy step's slot onset, beside the main line's last-20-step mean'. In the code, hab_copy stores only rec_v_onset_mean over all 130 copy steps and rec_v_onset_last20 = mean(rec_onset[-20:]). At the full config those last 20 are copy steps 111-130, which are the blank pause and the recovery cues, not repetitions 81-100. No main-line last-20-step value is recorded: block_criteria's rec_onset_v averages the whole 240-step block. Per-step copy onset values are not saved anywhere, though the main line's per-slot rec_v is in the dumped main log. TINY shows rec_v_onset_last20 == rec_v_onset_mean (only 20 copy steps there). Reported only.
- fix: Record the main line's mean rec_v over steps M-19..M in loads[M] (from main.log). Define the copy window explicitly, for example repetitions reps-19..reps, or store the per-step onset list in the habituation step dump.

## Computed (exploratory; not results)

All scripts and outputs are under ~/.cache/brain-sim/review/p2e4-fixcheck/regression/. BRAINSIM_CACHE pointed at subdirectories there. Simulations used TINY seeds 90-92 only; the real config was used only for schedules (seeds 90-99, no simulation) and synthetic predictions.

1. **run_seed on TINY seeds 90 and 91** (gated=False, every arm; run_tiny.py, outputs r90.jsonl and r91.jsonl, log90.txt and log91.txt; about 116 s each), checked with check.py:
   - **Records:** each file holds exploration_seed then reported_arms, both parse with json.loads, and there are 0 NaN or Infinity tokens.
   - **Gated validity, both seeds:** valid is True. fwd_equals_p2e1, elig_ok (0.989 and 0.988), mean_A_ok (20.39 and 19.85), fb_union_ok (at both loads), slot_checks_ok, main_untouched, rep1_identical, audit_ok (audit list empty), leak_ok (L_A, L_C, B_A, B_C all 0.0; posctl 1.0) are all True, with schedule attempts 0.
   - **Reported validity:** snapshots_untouched, main_untouched_by_twins, snapshot_untouched_by_wps, novel_duty_fb_union_ok and duty_fb_union_ok are all True.
   - **Per-slot logs:** the main (200 lines), habituation (8 lines) and main_continuation (60 lines) logs exist, and the sha256 of the decompressed data equals the recorded value.
   - **Twin A replay against live:** replay_only = live_only = 0 and joint_live_minus_replay = 0.0 at both loads, for the main twin, the novel-duty twin and the duty twin. For example, seed 90 M=200 has 360,486 spikes and the duty twin 594,428.
   - **offset_settled below the online block offset:** seed 90, 1.27 vs 3.99 mV and 2.07 vs 7.03 mV; seed 91, 1.29 vs 3.90 mV and 1.99 vs 6.83 mV.
   - **Matched-episode window:** n = 40 and 39. **M=250 rolling:** n = 0 in TINY, because steps 221-250 lie inside TINY's stress block.
   - **Habituation fields:** per_rep_recall is present (12 values per item and in the aggregate). stream_pos, rec_v_onset_mean and rec_v_onset_last20 are present. vector_state has three states, and mcnemar_scored is counted over scored items.
   - **Other arms:** cued_vs_blank_by_age is present (age-0 cued recall is None on seed 91, where no recent cue had age 0). The stress, WPS, OOD, novel-duty and duty arms all ran, and the duty arm carries leak and slot_checks.
2. **Writes during probes** (wps_check.py, seed 92). After the writes the copy's forward and feedback stores differ from the main line, and joint_50ms differs at step 207. Memory n_R50 and recall are identical over steps 201-210 because only about 1.3 cue lines overlap each write, so the equal rolling C1 and joint seen on seeds 90-91 are expected, not a bug.
3. **Real-config schedules** (sched_check.py, seeds 90-99, indices only). Every block (500, 1000, 1500, 2000, 3000) was built on attempt 0, with 0 audit violations and 0 pseudo-targets already targeted in their block. Probe writes were 164-177, plateau episodes 1364-1377, and the matched-episode window held 91-101 half cues. Rolling half cues in steps 221-250 numbered 7-16.
4. **predictions() on synthetic exploration records** (pred_check.py, git_state monkeypatched, output to the cache). Each run took about 26 s with no NaN.
   - **Bad rates:** P(PASS) is 0. The label probabilities are INDEX 1.0, CONTENT 0.475, HABITUATION NOT ESTIMABLE 0.947, HABITUATION FAIL 0.053, RECOVERY FAIL 0.39 and RECOVERY NOT ESTIMABLE 0.61. The shift bisects to delta 1.91 with p_pass_model 0.801.
   - **Good rates:** the shift is 0.05.
   - **p_criterion_5seeds** holds per-seed values (finding PRED-5SEEDS).
   - **pred_trap.py** reproduces finding PRED-STALE-FIRST.
5. **verdict()** on the real results file plus five fake gated records built from the TINY seed-90 record (relabelled 500/1000) gives 'ONLINE INDEX FAIL + ONLINE CONTENT FAIL + HABITUATION NOT ESTIMABLE + RECOVERY NOT ESTIMABLE', with per_seed carrying rates, per_kind and habituation_state. load_records skips a torn trailing line.
6. **Guard preconditions at HEAD:** `git diff --numstat cd17cde HEAD` on the contract is empty, the working-tree contract equals HEAD, plant2_dirty is False, and there is no power_predictions record yet, so the guard correctly refuses gated runs now.
7. **Fast tests:** `pytest -p no:cacheprovider -m 'not slow' plant2/tests/test_p2_e4.py` with -B: 11 passed.
8. **Line-by-line read** of run_seed, run_reported, twin_A/B, wps_arm, ood_arm, habituation, hab_criteria, _hab_fast, _p0_table, predictions/p_full, labels, verdict, guard and main:
   - The `gated` flag changes only the record kind and the gated field.
   - The explore and run paths call the same run_seed. Apart from the seed, the only differences are the start marker and the log file names.
   - Populations and signs match the contract.
   - The bisection searches in the right direction, cannot produce beta(·, 0) at the shift extremes, and returns 'unreachable' only if delta = +6 fails.
