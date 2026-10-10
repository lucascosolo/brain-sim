# P2-E4 implementation review: conformance lens

Fresh reviewer given only the files (driver at commit d404332, contract frozen at cd17cde); each finding checked by a separate refuter. Run 2026-10-10. Recorded verbatim.

## Verdict

Not ready to run exploration as committed. The gated per-seed path matches the contract section by section. I checked stream keys and draw order, window ticks k=0..49 and k=0..74, the populations of C1-C3, joint/D3 and O3, the strict and >= bars, the ceil(0.9n) rule, the eligible/habituated/recovery/collateral rules, validity 1-9, the order of runs and the record kinds. None of the gated numbers in a kill_test_seed record would come out wrong. The problems are around that path, and they matter because plant2 is frozen from exploration onward:
(1) BLOCKER: the `verdict` subcommand crashes on the real results file, so no kill_test_verdict can be written without changing code.
(2) The verdict labels treat the two not-estimable families inconsistently, and the contract's own predicted outcome triggers the difference.
(3) The committed power_predictions will lack the required logit-shift rate (it will be None) and the per-label probabilities.
(4) The writes-during-probes 'matched plateau episodes' comparison is always empty at the full config.
The rest are minor or nit. All of these should be fixed before exploration on seeds 42-43, because the plant2 tree may not change afterwards.

## Findings

### V-1 [blocker] verdict() crashes on the real results file: no experiment filter and r['gated'] KeyError

- where: plant2/experiments/p2_e4_online.py:1000-1002 (verdict), called from main() at 1161-1162 with load_records()
- evidence: `gated = [r for r in recs if r["gated"] and r["kind"] == "kill_test_seed"]`. bench/results/plant2.jsonl holds P2-E1 kill_test_seed records with no 'gated' key, plus gated kill_test_seed records of P2-E2 (seeds 6-10) and P2-E3 (seeds 11-15). Reproduced (~/.cache/brain-sim/review/p2e4-impl/conformance/verdict_crash.py):
- on the real file: `KeyError 'gated'`;
- with five fake gated P2-E4 records added: the same KeyError;
- with the KeyError avoided by keeping only rows that have a 'gated' key: `SystemExit verdict needs exactly the gated seeds (16..20); have [6, ..., 20]`.
So the contract's kill_test_verdict record (Files table; 'Verdict' section) cannot be produced without editing plant2 after gating. The verdict is also not filtered by contract_digest. If an owner-ruled re-run exists it also exits, where the contract says 'keeps the first records'.
- fix: Filter with `r.get("experiment") == "P2-E4" and r.get("kind") == "kill_test_seed" and r.get("gated") and r.get("contract_digest") == DIGEST`. Keep the first record per seed (contract: a re-run 'keeps the first records'), then require the seed set to equal GATED_SEEDS. Add a unit test that runs verdict() on a copy of the real results file plus five synthetic P2-E4 gated records, with results_path pointed at a cache file.
- independent verifier: **confirmed** (severity should be blocker): Reproduced in ~/.cache/brain-sim/review/p2e4-impl/verify-conformance/v1.py, with results_path pointed at a cache file. On the real bench/results/plant2.jsonl, verdict() raises KeyError 'gated'. The first record is a P2-E1 capacity_point, and r["gated"] is evaluated before r["kind"] at line 1000. Adding five synthetic gated P2-E4 records gives the same KeyError. If records lacking 'gated' are dropped, it gives SystemExit 'have [6, ..., 20]', because the gated P2-E2 seeds 6-10 and P2-E3 seeds 11-15 are also gated kill_test_seed rows. Fed only the P2-E4 records, it returns PASS, so the experiment/digest filter is the only defect. A duplicate seed from an owner-ruled re-run also exits, whereas the contract says the re-run 'keeps the first records'. The run path is fine: guard() short-circuits on r.get('experiment'). The frozen tree therefore cannot produce the contract's kill_test_verdict, and the gated label would have to come from code edited after gating. The proposed fix is correct: filter on experiment, kind, gated and DIGEST, keep the first record per seed, and add a unit test on a copy of the real file.

### L-1 [major] HABITUATION and RECOVERY not-estimable labels are de-duplicated inconsistently; the contract's predicted outcome hits the difference

- where: plant2/experiments/p2_e4_online.py:986-995 (labels)
- evidence: The contract's label table words the two families in parallel:
- 'HABITUATION NOT ESTIMABLE | O4 fails only because fewer than 25 items are eligible';
- 'RECOVERY NOT ESTIMABLE | O5 fails only on seeds and loads where that probability is below 0.8'.
The driver drops RECOVERY NOT ESTIMABLE when RECOVERY FAIL is present (lines 994-995) but keeps HABITUATION NOT ESTIMABLE beside HABITUATION FAIL. Reproduced (labels_check.py) with O4 and O5 failing as estimable at M=500 and as not estimable at M=1000. This is exactly the contract's prediction ('habituation present at M = 500; at M = 1,000 eligibility likely under 25'). The result is ['HABITUATION FAIL', 'HABITUATION NOT ESTIMABLE', 'RECOVERY FAIL'].
Under a single reading of 'only', one family is wrong:
- global reading: HABITUATION NOT ESTIMABLE must be dropped;
- per seed-and-load reading (as in 'Expected labels ... at M = 1,000'): RECOVERY NOT ESTIMABLE must be kept.
The pass/fail outcome is unchanged, but the gated label string differs.
- fix: Treat both families the same way. The parallel wording supports the global reading: add `if "HABITUATION FAIL" in lab and "HABITUATION NOT ESTIMABLE" in lab: lab.remove("HABITUATION NOT ESTIMABLE")`. Record the reading in review/ledger.jsonl before exploration, and extend test_labels_join_every_failure_and_separate_not_estimable with the two-load case above.
- independent verifier: **partly** (severity should be minor): The output is reproduced: ['HABITUATION FAIL', 'HABITUATION NOT ESTIMABLE', 'RECOVERY FAIL']. The two families are handled differently (lines 986-995), and the contract's predicted scenario (O4 estimable-fail at 500, not estimable at 1,000) hits the difference. The claim that one family is necessarily wrong does not hold, because the two rows are not worded in parallel. RECOVERY NOT ESTIMABLE is explicitly global: 'O5 fails only on seeds and loads where that probability is below 0.8'. The driver's removal at 994-995 is the literal reading. HABITUATION NOT ESTIMABLE ('O4 fails only because fewer than 25 items are eligible') has no seeds-and-loads quantifier. Applying it per seed and load fits 'every applicable failure label is joined; none hides another' and 'Expected labels ... HABITUATION NOT ESTIMABLE ... at M = 1,000'. Each family therefore follows a defensible literal reading. What holds: the frozen text is ambiguous and the reading is not recorded in the ledger (only row 176, which introduced the labels). PASS/FAIL is unchanged. Fix: record the reading (or the owner's choice) in review/ledger.jsonl before exploration, and change code only if the global reading is chosen.

### P-1 [major] power_predictions: the required 'per-cue rate for P(PASS) >= 0.8, one common logit shift of all rates' will be None, and it shifts only O1-O3

- where: plant2/experiments/p2_e4_online.py:1066-1074, 1079
- evidence: The contract ('After implementation') commits 'the per-cue rate that gives P(PASS) >= 0.8, as one common logit shift of all rates'. The code does three things wrong:
- It searches only `if p45 > 0.8`, holding O4-O5 at the bootstrap value. The contract predicts O4 not estimable and O5 failing from sampling at M = 1,000, so p45 is about 0 and the record will carry `logit_shift_for_p08: None`.
- The shift is applied to the O1-O3 rates only, not to 'all rates', which include the per-cue 'both' rate behind O4-O5.
- It searches delta >= 0 only, so when P(PASS) is already >= 0.8 it returns 0, not the threshold. It also records a delta rather than 'the per-cue rate'.
This cannot be fixed after exploration without changing the plant2 tree.
- fix: Apply one logit delta to every per-cue rate. For O1-O3, shift the posterior mean rates. For O4-O5, shift each bootstrapped item's per-cue 'both' probability, or use power.p_paired_late_window and p_paired_majority at the shifted 'both' rate. Bisect delta over [-6, 6] to the smallest value giving P(PASS) >= 0.8, and record both delta and the resulting rates per criterion and load. Record 'unreachable' (not None) only if no delta reaches 0.8.
- independent verifier: **confirmed** (severity should be major): Lines 1066-1074: the shift search runs only `if p45 > 0.8`. It shifts only mean_rates of O1-O3 (line 1070) and steps delta over [0, 6]. The contract commits 'the per-cue rate that gives P(PASS) >= 0.8, as one common logit shift of all rates'. Its own predictions (O4 at M = 1,000 not estimable; O5 failing from sampling at 0.77) make the bootstrap hab['1000']['both'] about 0. So p45 is about 0 and the committed record will hold logit_shift_for_p08: None. The O4/O5 rates are never part of the shift, so 'all rates' is not met even when p45 > 0.8. Lesser parts: when delta = 0 already reaches 0.8 it reports 0, which is arguable; and the rates can be derived from 'observed' plus delta, so the 'records a delta' complaint is weak. The main defect stands. predictions() is in plant2, so a fix after exploration changes the tree the guard pins.

### W-1 [major] Writes-during-probes 'matched plateau episodes' comparison is always empty at the full config

- where: plant2/experiments/p2_e4_online.py:837-842 (wps_arm) with rolling_summary at 776-779
- evidence: `episodes = M + wps_steps + len(writes)` is about 1,000 + 200 + 170 = 1,370 (the contract also says 'about 1,370'). It is compared with `rolling_summary(main_final, episodes - 70, episodes + 70)`, which keeps only `d["block"] is None`. Steps 1,300-1,440 lie inside stress block 1,500 (steps 1,261-1,500), so there are 0 rolling steps in the window: 0 at 170 or 200 writes and 11 at 120 writes (computed on Schedule(90)). The contract's predeclared 'Compared with the main line at ... matched plateau episodes (about 1,370)' therefore reports n = 0 and NaN. TINY does not show this, because its window overlaps rolling steps.
- fix: For the matched-episode reference, take the main line's half cues (recent and uniform, including stress-block 1,500 cues) in steps episodes ± 70 regardless of block. Alternatively, compare by age-matched retention_by_age on main_final. Record n with the rate.
- independent verifier: **confirmed** (severity should be major): Computed on Schedule(90..99) (verify-conformance/w1.py). Probe writes are 164-177, so plateau episodes are 1,364-1,377. The window [episodes-70, episodes+70] lies entirely inside stress block 1,500 (steps 1,261-1,500) on every seed, and rolling_summary keeps only block None. Rolling half cues in the window: 0 on all ten seeds. Arithmetic: n = 0 for any count from 131 to 230 writes. The contract's 'matched plateau episodes (about 1,370)' comparison is therefore n = 0 / NaN on every exploration and gated seed. The matched-items comparison (1,001-1,200, all rolling) still works. Fix as proposed: include the main line's stress-block half cues in that window, or compare by age.

### P-2 [minor] power_predictions omits per-label probabilities (FAIL vs NOT ESTIMABLE) and splits neither O5 part

- where: plant2/experiments/p2_e4_online.py:1051-1064, 1075-1081, 1089-1098 (_hab_fast)
- evidence: The contract commits 'per-criterion and per-label probabilities'. The record carries:
- p_index_pass_median and p_content_pass_median, which cover the ONLINE INDEX and ONLINE CONTENT labels;
- habituation_5seeds {O4, O5, both}, with O5 recovery and collateral merged.
_hab_fast computes no estimability, so P(HABITUATION FAIL), P(HABITUATION NOT ESTIMABLE), P(RECOVERY FAIL) and P(RECOVERY NOT ESTIMABLE) are not produced, and neither is O5 collateral on its own. These are the labels the contract predicts. They cannot be added after exploration without changing the plant2 tree.
- fix: In the O4-O5 bootstrap:
- count, per simulated seed set, whether O4 fails with >= 25 eligible or with < 25;
- for O5, compute the p_paired_majority estimability at the bootstrapped control rate (as hab_criteria does);
- apply the labels() logic, and record the probability of each label and of O5 recovery and collateral separately.
- independent verifier: **confirmed** (severity should be minor): The record (lines 1075-1081) has p_criterion_5seeds for the O1-O3 parts, p_index/p_content medians (complements of the INDEX/CONTENT labels), and habituation_5seeds {O4, O5, both}. O5 recovery and collateral are merged at line 1059. _hab_fast (1089-1098) computes no estimability. So P(HABITUATION FAIL), P(HABITUATION NOT ESTIMABLE), P(RECOVERY FAIL) and P(RECOVERY NOT ESTIMABLE), which the contract's expected labels name, are not produced, and neither are the O5 parts on their own. The contract commits 'per-criterion and per-label probabilities'. This is an incomplete commitment, not a wrong number.

### L-2 [minor] RECOVERY FAIL vs NOT ESTIMABLE uses a separate rate per O5 part, not 'the control copies' observed per-cue "both" rate'

- where: plant2/experiments/p2_e4_online.py:636-644, 651-652, 988-990
- evidence: Contract: 'RECOVERY FAIL | O5 fails on a seed and load where power.p_paired_majority (cues = 5, need = 3) gives a zero-effect pass probability >= 0.8 at the control copies' observed per-cue "both" rate'. That is one rate per seed and load. The driver uses two:
- rate_r = mean(rec_ctl)/5, from x's 5 recovery cues;
- rate_c = mean(col_ctl)/5, from y's 5 cues.
It then labels each part by its own probability. When recovery passes and collateral fails, the label (FAIL vs NOT ESTIMABLE) depends on which rate is read. A pooled rate (all 10 recovery and collateral cues, or every scored control-copy cue) can fall on the other side of 0.8.
- fix: Either pool into one control-copy per-cue 'both' rate per seed and load, used for both parts, or keep the per-part rates and record that reading in review/ledger.jsonl before exploration. In both cases, record the alternative rate and its probability in the habituation dict.
- independent verifier: **partly** (severity should be minor): True that hab_criteria uses two rates per seed and load: rate_r from x's recovery cues and rate_c from y's cues (lines 636-644, 651-652). The contract names one: 'at the control copies' observed per-cue "both" rate'. Per-part rates are a defensible reading, since each is the direct estimate for its rule. I computed p_paired_majority (cues 5, need 3, seeds 1, loads 1, rng 7): 0.73 at 0.80, 0.83 at 0.82, 0.91 at 0.84. The 0.8 bar sits near a rate of 0.81. Each part's rate rests on about 250 cues (SE about 0.025), so a pooled rate and a part rate can straddle the bar only near about 0.81. That is unlikely under the predicted rates (about 0.77 at 1,000, high at 500), but possible. Fix: ledger the per-part reading before exploration, or pool; record both rates.

### V-2 [minor] The verdict vector is boolean; the contract's 'fail (not estimable)' state and per-kind rates are not in kill_test_verdict

- where: plant2/experiments/p2_e4_online.py:459-460, 884, 1011-1014; hab_criteria 632-633 (est_r/est_c discarded)
- evidence: Contract: 'The vector. Pass, fail, or fail (not estimable), for each part at each load'. In the driver:
- vector entries are bools and the verdict ANDs them;
- the min-count estimability of O5 ('among the >= 25 items that pass on the control copy') is computed in paired() but thrown away;
- the only O5 'estimable' flag is the power-based label flag.
Also, 'Per-kind rates are reported in the verdict text', but kill_test_verdict carries no per-kind rates.
- fix: Store each vector entry as 'pass' / 'fail' / 'fail (not estimable)'. Use the min-count rule for O4 (eligible < 25) and O5 (control passers < 25), and keep the power flag separately for labels. In kill_test_verdict, add per seed and load the per_kind rates from each record's block.
- independent verifier: **partly** (severity should be minor): True that the vector entries are bools (459-460, 884) and kill_test_verdict ANDs them (1011), so the three-state 'fail (not estimable)' is never stored. O5_recovery_estimable and O5_collateral_estimable hold the power-based label flag, not the contract's min-count notion, which invites misreading. Overstated: the min-count state is not thrown away. O5_recovery_n=[n_r, k_r] and O5_collateral_n are stored (lines 651-652), and O4_estimable is stored, so the three-state vector can be derived from the per-seed records. 'Per-kind rates are reported in the verdict text' most plausibly means the prose result. per_kind is already in each kill_test_seed record. Fix: store the vector as pass / fail / fail (not estimable), and rename or add the power-based flag.

### S-1 [minor] Pseudo-targets are not drawn 'by the blank-target rule' minus items already targeted in the block

- where: plant2/experiments/p2_e4_online.py:129-137 (_build)
- evidence: Contract: the sampler draws 'from its kind's eligible set, minus every item already targeted in the block, cued or blank', and 'Each novel slot also gets a pseudo-target by the blank-target rule'. The driver draws `r.choice(self.eligible("blank", k))` with no `used` exclusion. Over 400 gated novel slots (seeds 90-99, pseudo.py):
- 52 pseudo-targets (13 %) had already been cued or blank-targeted earlier in the same block;
- 9 repeat another pseudo-target.
This changes the B_A and B_C baselines of validity 9, which is gated, only slightly, because exploration leak values are about 0.
- fix: Draw the pseudo-target from `[i for i in el if i not in used]`, failing the attempt if that is empty. Keep it out of `used` (it is never cued). Do this before exploration, since it changes the schedule draws.
- independent verifier: **confirmed** (severity should be minor): Line 135 draws `r.choice(self.eligible('blank', k))` with no `used` exclusion. The contract says each novel slot 'gets a pseudo-target by the blank-target rule', and the sampler rule for blank targets is 'its kind's eligible set, minus every item already targeted in the block, cued or blank'. Re-running the reviewer's pseudo.py on seeds 90-99: 400 pseudo-targets, 52 already targeted earlier in the block, 8 of them cued within 3 steps, 9 repeated pseudo-targets. Including age 0 matches the eligible table ('recent and blank | age 0-20'), so only the exclusion deviates. The effect on gated validity 9 (B_A, B_C) is tiny with leak about 0, but it slightly loosens the check. The fix changes the stream-15 draws, so it must land before exploration.

### G-1 [minor] Provenance: predictions accept exploration records from any plant2 tree; the guard never checks the frozen contract text

- where: plant2/experiments/p2_e4_online.py:1028 (predictions filter), 1106-1123 (guard)
- evidence: predictions() keeps exploration_seed records by contract_digest only. That is the config-dict digest, unchanged by code edits outside CONTRACT. It does not compare r['git']['plant2_tree'] with the current tree, and it does not refuse when plant2 is dirty at predict time, so the rule that exploration and gating run the same plant2 tree is not enforced. The guard checks the contract file only against HEAD (`git diff --quiet HEAD`). A committed edit to docs/plant2/P2-E4-online-memory.md would pass. The frozen sha256 a7c3f465... is recorded in power_reference.contract_sha256 and is never compared.
- fix: In predictions():
- require each exploration record to have git.plant2_tree equal to the current HEAD:plant2 and plant2_dirty False;
- refuse if plant2 is dirty;
- store sha256 of the contract file.
In guard(): require sha256(contract file) to equal the power_reference record's contract_sha256 and the predictions record's stored value.
- independent verifier: **partly** (severity should be minor): Holds: predictions() (line 1028) filters exploration records by DIGEST only and never compares r['git']['plant2_tree'] with the current tree. It records HEAD:plant2 even when plant2 is dirty (record.git_state takes rev-parse HEAD:plant2), and guard() does not check p['git']['plant2_dirty']. The exploration-equals-gating tree rule is therefore not enforced in code. Wrong part of the fix: 'contract digest' in this project means record.digest(CONTRACT) (see P2-E3 line 38), which the guard does check. The contract also requires 'Predictions from the real driver will be appended below them' in the same contract file. Requiring sha256(contract) to equal power_reference.contract_sha256 or the predict-time hash would make the guard refuse after that mandated append. A correct text check verifies that the frozen cd17cde text is unchanged except for the appended predictions section, for example with `git diff cd17cde HEAD -- contract` adding lines only.

### H-1 [minor] The reported McNemar on 'L >= 8' is degenerate: its second cell is always 0

- where: plant2/experiments/p2_e4_online.py:645-647
- evidence: `b` and `cc` are counted over `el`, the eligible items, which by definition have L_ctl >= 8. So `cc = #(L_ctl < 8 <= L_rep)` is 0 by construction, and the contract's reported 'McNemar on "L >= 8"' cannot detect anything.
- fix: Count the discordant pairs over the scored items, or all 50, not over eligible items.
- independent verifier: **confirmed** (severity should be minor): Lines 645-647: b and cc are counted over `el`, whose items all have L_ctl >= 8. So cc = #(L_ctl < 8 <= L_rep) is 0 by construction, and the reported 'McNemar on "L >= 8"' degenerates to a count of b. Count the discordant pairs over the scored items, or all 50.

### R-1 [minor] Several predeclared reported quantities are missing or measured at the wrong time

- where: plant2/experiments/p2_e4_online.py:587-590 (hab_copy info), 713-715 (twin_A), 469-472 (leak), 958 (novel-duty), 961-967 (duty arm)
- evidence: Contract 'Reported' table and 'Twins':
- Twin A mismatch: the contract says 'reported as a count of differing spikes plus its effect on the joint'. Only counts are recorded.
- Habituation detail: 'per-repetition recall' is missing, only 'both'. 'rec onset v on every copy against the main line' is recorded at copy end (rec_v_end), not at slot onset, and has no main-line counterpart.
- Causality: 'cued minus blank by age' is not computed. Only blank age-0 L_A is.
- Novel-duty twin: 'records its stores'. Only fb size is recorded, with no forward or feedback digests.
- Reported-arm validity: 'A validity failure in a reported arm invalidates only that arm'. No validity check (fb union, slot checks, store identity) is run for the duty arm or the novel-duty twin.
- Efficiency: the 'inherited window widths' are absent.
- fix: Add each item:
- the replay-vs-live joint difference (re-score twin A's cues from the logged live rec);
- per-repetition recall, and rec v at each copy step's slot onset, beside the main line's last-20-step mean;
- cued-minus-blank recall by age bin, from the rolling and block logs;
- fwd and fb digests for the novel-duty twin;
- fb_union_ok and slot checks for the duty arm and the novel-duty twin;
- the constant window widths.
- independent verifier: **partly** (severity should be minor): Confirmed omissions:
- twin A records only the counts replay_only, live_only and replay_spikes, with no effect on the joint (713-715);
- hab_copy computes per-step recall but habituation() keeps only per_rep_both;
- rec v is taken at copy end (rec_v_end), not at slot onset;
- blank-by-age is not computed (retention_by_age filters to HALF), and main.log is not saved, so it cannot be derived later;
- the novel-duty twin records fb sizes only;
- the duty arm drops block_criteria's leak and slot_checks, and no fb_union_ok runs for the duty arm or the novel-duty twin;
- window widths are absent.
Overstated: 'no main-line counterpart'. The same load record carries the main line's block offset_mv and rec_onset_v, and cued recall by age exists (retention_by_age). All of these are reported-only.

### V-3 [nit] Validity 6 digests the snapshot once per arm, not the main line before and after each copy; validity 4's block-end digests are recorded but not checked

- where: plant2/experiments/p2_e4_online.py:595, 617 (habituation), 349, 886, 895
- evidence: Contract validity 6: 'Digests ... are taken before and after each copy and each habituation arm.' state_digest(S) runs once before and once after all 100 copies, on the snapshot S rather than `main`. Validity 4 asks for 'full digests at block ends'. fwd_digest and fb_digest are recorded, but only fwd is checked (against P2-E1), and fb union (validity 3) is checked only at M = 1,000. Neither can move a number, because deepcopy shares no mutable state.
- fix: Digest `main` (and S) around each hab_copy call. Check fb_union_ok at M = 500 as well.
- independent verifier: **confirmed** (severity should be nit): state_digest is taken once before and once after the whole arm, on S (lines 595, 617), not around each copy and not on main. fb_digest is recorded and never checked, and fb_union_ok runs only at M = 1,000. No number can move. S = deepcopy(main), so the copies share no mutable state with main. BinarySynapses.add/toggle only reassign keys, so the per-slot identity check works. fb is add-only, so an extra key written at or before 500 would still show in the 1,000 union check.

### N-1 [nit] Habituation copy stream keyed by list position, while the contract names item x

- where: plant2/experiments/p2_e4_online.py:568
- evidence: Contract streams table: '(seed, 16, M, x + 1, s) | every input draw of copy step s for item x'. The driver uses `stream(S.seed, HAB, M, i + 1, s)`, where i is the position of x in the 50 drawn items, not x (or x-1). This does not bias anything, but it differs from the literal key.
- fix: Use plan['x'] (equivalent to the 0-based item index + 1), or record the 'x = position' reading in the ledger before exploration.
- independent verifier: **partly** (severity should be nit): The driver keys the stream by the item's position i + 1 among the 50 drawn items (line 568), not by the item id. Items are 1-based ids and the contract's '(seed, 16, M, x + 1, s)' has a '+1' that only makes sense to avoid the selection key 0 if x is a 0-based index. The driver's reading is therefore the natural one. There is no collision with (16, M, 0) and no bias either way. A ledger note is enough.

### N-2 [nit] 'Gated seeds run once' is not enforced for a run that crashes before its record is appended

- where: plant2/experiments/p2_e4_online.py:1152-1158, 911
- evidence: `done` is read from kill_test_seed records, which are appended only at the end of the gated part. A seed that crashed mid-habituation leaves no trace, so a re-run looks like a first run, while the contract says 'A re-run needs the owner's ruling'.
- fix: Before run_seed for a gated seed, write a start marker under ~/.cache/brain-sim/plant2/p2_e4/ (not a new results kind). Refuse to start if the marker exists without a record, unless an explicit owner-ruling flag is given.
- independent verifier: **confirmed** (severity should be nit): guard() derives `done` only from kill_test_seed records (line 1123), which are appended after both habituation arms (line 911). A gated seed that crashes mid-run leaves no trace, and a second invocation proceeds as a first run. The contract says 'Gated seeds run once. A re-run needs the owner's ruling.' This is a process gap, and the console log would show the attempt. A start marker in the cache, plus a refusal without an explicit owner flag, closes it.

## Computed (exploratory; not results)

Scripts and outputs are in ~/.cache/brain-sim/review/p2e4-impl/conformance/. The repo is untouched (git status is clean). No simulation used seeds 0-43.

- verdict_crash.py: e4.verdict(load_records()) raises KeyError 'gated'. With records lacking 'gated' removed, it raises SystemExit ('have [6..20]') because the P2-E2 and P2-E3 gated kill_test_seed rows are included.
- labels_check.py: with O4 and O5 failing as estimable at 500 and as not estimable at 1000, the labels come out ['HABITUATION FAIL', 'HABITUATION NOT ESTIMABLE', 'RECOVERY FAIL'], which is asymmetric.
- pseudo.py: real schedules for seeds 90-99, 400 gated novel slots. 52 pseudo-targets were already targeted earlier in the block, 76 are targeted later, 23 are age 0 and 9 repeat another pseudo-target.
- WPS window, real Schedule(90): stress block 1500 covers steps 1261-1500. The matched-episode window 1300-1440 (at 170 writes) contains 0 rolling steps; at 120 writes it contains 11.
- numpy 2.5.3 SeedSequence treats trailing zeros as equal up to 4 words: [s,15,0] equals [s,15] equals [s,15,0,0]. I listed every key P2-E4 and its parents use and found no collision.
- Rolling cumulative shares reach exactly 1.0. The 0.9 bar holds at exactly 18/20, 90/100 and 180/200.
- P2-E4 config keys shared with e3.CONTRACT all keep e3's values, and none of the new keys (pre, post, slot, block, ...) is read by e1, e2 or e3 code.
- The contract file's sha256 a7c3f465... equals power_reference.contract_sha256, unchanged since cd17cde.
- `pytest -m 'not slow' plant2/tests/test_p2_e4.py`: 9 passed.

Sections that conform as written:
- Definitions: ages; unreserved; slot tick 0; R50 = first spike < 50; rec75 = first spike < 75; recall 0 when A is empty; strict spurious and ignition bars with mean|A| over items 1..M; joint >= 40 missing and < 10 intrusions; novel half cue drawn with its mask from (17, k).
- Streams: keys 12-18 and the rolling draw order kind, then target, then mask.
- Protocol: no quiet() and a reload after each write.
- Cohorts.
- Rolling: shares and novel fallback.
- Gated blocks, apart from pseudo-targets: counts, sub-block mix, age-0 blanks, the c500 spread, the sampler minus used items, attempt redraws.
- Habituation arm: candidate set C, collateral, the 89 controls, the copy-step structure, steps 1/2-90/91-100/101-120/121-130, scored/L_rep/L_ctl/eligible/habituated (<= L_ctl-3)/recovery/collateral, O4 (<= 10 %, >= 25 eligible), O5 (ceil(0.9n) with >= 25).
- Validity 1-9 as gated.
- Order of runs and record kinds.
