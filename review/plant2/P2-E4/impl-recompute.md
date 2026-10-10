# P2-E4 implementation review: recompute lens

Fresh reviewer given only the files (driver at commit d404332, contract frozen at cd17cde); each finding checked by a separate refuter. Run 2026-10-10. Recorded verbatim.

## Verdict

I re-simulated and recomputed everything my lens covers, and it all matches the driver: every slot, every block criterion, the leak statistics and positive control, the habituation statistics, O4/O5 and the validity flags. I found one blocker outside the simulation. `verdict()` crashes on the real results file, so the frozen code cannot produce the gated label. Fix it before exploration so the plant2 tree stays the same through gating. I also found two nits, both readings of ambiguous contract wording that have no measurable effect.

## Findings

### R1 [blocker] verdict() crashes on bench/results/plant2.jsonl: it does not filter by experiment and reads r["gated"] on records that have no such key

- where: plant2/experiments/p2_e4_online.py:1000 (verdict), reached from main() 'verdict' -> verdict(load_records())
- evidence: The line is `gated = [r for r in recs if r["gated"] and r["kind"] == "kill_test_seed"]`. The results file already holds 11 P2-E1 records with no 'gated' key (5 capacity_point, 5 kill_test_seed, 1 kill_test_verdict). It also holds P2-E2 kill_test_seed rows with gated=True (seeds 6-10) and P2-E3 rows (seeds 11-15). Reproduced without writing to the repo (results_path pointed at my cache): verdict(load_records()) raises KeyError: 'gated'. The same happens with 5 synthetic P2-E4 gated rows (seeds 16-20) appended. Keeping only records that have the key gives SystemExit 'verdict needs exactly the gated seeds (16, 17, 18, 19, 20); have [6, 7, ..., 20]'. With only the P2-E4 rows, verdict() works and gives the same labels as my own label code. No test calls verdict(); test_labels_* tests labels() only. The verdict is the gated label. Fixing it after gating would change the plant2 tree between the gated runs and the verdict, which the process forbids.
- fix: Filter on experiment and use .get: `gated = [r for r in recs if r.get("experiment") == "P2-E4" and r.get("kind") == "kill_test_seed" and r.get("gated") is True]`. Add a fast test that calls verdict() on e4.load_records() plus five synthetic P2-E4 gated rows, with results_path set to a tmp path under the cache. The test should assert the label and that no other experiment's seeds are included. Commit the fix before the exploration run on seeds 42-43.
- independent verifier: **confirmed** (severity should be blocker): Reproduced with results_path pointed at ~/.cache/brain-sim/review/p2e4-impl/recompute-verify/verdict_out.jsonl (script r1_check.py there). bench/results/plant2.jsonl holds 71 records. The first one (P2-E1 kill_test_seed) has no 'gated' key, and neither do the other P2-E1 rows, the P2-E2/E3 calibration and verdict rows, or the P2-E4 power_reference row. Line 1000 (`gated = [r for r in recs if r["gated"] and r["kind"] == "kill_test_seed"]`) reads r["gated"] first. Results: (A) verdict(load_records()) raises KeyError 'gated'. (B) The same records plus 5 synthetic P2-E4 gated rows (seeds 16-20) also raise KeyError. (C) Keeping only rows that have the key gives SystemExit 'verdict needs exactly the gated seeds ...; have [6, 7, ..., 20]', because the P2-E2 seeds 6-10 and P2-E3 seeds 11-15 kill_test_seed rows have gated=True. (D) The synthetic P2-E4 rows alone give PASS [16..20]. The proposed filter (experiment == 'P2-E4', kind == 'kill_test_seed', gated is True) selects exactly [16..20]. No test calls verdict(). The documented CLI path (`... verdict`, line 1162) therefore cannot produce the gated label. Fixing it after gating would change the plant2 tree. A hand-filtered one-off call would work, but it is not the committed path. The gated seed runs themselves do not crash: guard() uses r.get('experiment') first. Severity: blocker, as the brief defines it, because the gated label step crashes every time. Fix as proposed. Optionally also require r['contract_digest'] == DIGEST, and add a fast test that runs verdict() on the real load_records() plus synthetic P2-E4 rows, writing to a cache path. Commit before exploration.

### R2 [nit] Leak-baseline pseudo-targets are drawn from ages 0-20 without excluding the block's targets, so their age mix differs from the blank targets'

- where: plant2/experiments/p2_e4_online.py:130-136 (Schedule._build, novel branch)
- evidence: The contract says 'Each novel slot also gets a pseudo-target by the blank-target rule'. The sampler rule is 'minus every item already targeted in the block, cued or blank'. The driver draws `r.choice(self.eligible("blank", k))`, which covers ages 0-20, and never subtracts `used`. Over full-config schedules for seeds 90-99, pseudo-target ages are about uniform: age 0 is 23 of 400. Blank targets are 100 of 400 at age 0. Per block, 5-12 of the 20 pseudo-targets are also targets in the same block, and some were cued a few steps earlier (seed 95: steps 278 and 384). In practice this has no effect: L_A, L_C, B_A and B_C were exactly 0.0 on TINY seeds 93 and 94 and on the full config seed 95 at M=500 and 1000.
- fix: Either subtract `used` (and optionally match the blank age split) when drawing the pseudo-target, or state the reading in a comment and record it, so a later reader does not count it as a deviation. Either change must be committed before exploration.
- independent verifier: **partly** (severity should be nit): The code fact holds. Lines 130-135 draw the pseudo-target with r.choice(self.eligible('blank', k)), which covers unreserved items of age 0-20, and never subtract `used`. I recomputed the full-config schedules for seeds 90-99 (r2_sched.py). Pseudo-target age 0 is 23/400 against 100/400 for blank targets, and the pseudo ages are roughly uniform over 0-20. 3-12 pseudo-targets per block (mean 6.4) are also targets in the same block, so the reviewer's '5-12' should read '3-12'. 34 of them were cued earlier in the same block, including seed 95 at steps 278 (cued at 276), 384 (cued at 377) and 766 (cued at 761). Whether this is a deviation is a matter of reading. The contract applies 'minus every item already targeted' to 'each targeted slot', and says a pseudo-target is 'never cued'. 'By the blank-target rule' can fairly be read as the blank eligible set alone, and the 5 age-0 blanks are a designation, not part of the rule. Impact is nil, because the novel and blank slots are completely silent. On full config seed 96, n_R50 and n_rec are 0 in all 20 novel and all 20 blank slots at M=500 and at M=1000; L_A = L_C = B_A = B_C = 0, and rolling blanks with R50 > 0 are 0 of 78. TINY seeds 92 and 93 behave the same at both loads. Any pseudo-target choice therefore scores 0. Severity: nit. The fix should be a comment or a recorded statement of the reading. If `used` is subtracted instead, do it before exploration: it changes the stream-15 draws of the later slots.

### R3 [nit] Habituation input streams are keyed by plan index (i + 1), whereas the contract writes (seed, 16, M, x + 1, s) with x the item

- where: plant2/experiments/p2_e4_online.py:568 (hab_copy: stream(S.seed, HAB, M, i + 1, s))
- evidence: In the contract's habituation text, x names the item ('Each item x gets a collateral item y'). The verification reviewer proposed '(seed, 16, M, item, s)', and the ledger row for SHAM-1 accepted 'stream keys (seed, 16, M, x + 1, s)'. The driver passes the 0-based position of the item in hab_selection's list. Both readings are statistically valid, and my re-simulation reproduces the driver under the index reading. But a re-implementation that follows the contract literally (item id) would not reproduce the copies spike for spike.
- fix: Add a one-line comment, or a field in the hab record, saying 'x + 1 = 1-based position of x in the selection order'. That way, replaying the copies from the record is unambiguous.
- independent verifier: **confirmed** (severity should be nit): Line 568 is `stream(S.seed, HAB, M, i + 1, s)`, with i the 0-based position in hab_selection's plans (enumerate at line 599). The contract (line 141) says '(seed, 16, M, x + 1, s) | every input draw of copy step s for item x', and at lines 240 and 247 x names the item ('Each item x gets a collateral item y'). verify-ambiguity.md:109 proposed '(seed, 16, M, item, s)', and ledger row 200 (SHAM-1) accepted 'stream keys (seed, 16, M, x + 1, s)'. Taken literally, the driver departs from the text. The '+1' would be pointless for item ids, which are already 1-based, so the author may have meant an index, which makes the contract itself ambiguous. Neither reading has a key collision: selection is (seed, 16, M, 0), copies use 5-element keys, and both copies share the key, so validity 8 holds either way. Statistically the two readings are equivalent. hab_items is stored in plan order, so i can be recovered from the record. Severity: nit. Fix: a comment, or store the copy key or index in each hab_items entry.

## Computed (exploratory; not results)

All my scripts and outputs are in ~/.cache/brain-sim/review/p2e4-impl/recompute/: run_tiny.py, resim.py, spike_check.py, fuzz.py, sched_audit.py, full500.py, full_check.py, plus their logs, r93.jsonl and r94.jsonl. Nothing inside the repo was written.

1. **TINY run_seed, seeds 93 and 94.**
   - I ran run_seed with gated=False and reported arms on, and captured the main line, the snapshots and every habituation copy.
   - I then re-simulated each main line independently: E3.learn_one with net.quiet() disabled, the feedback projection rebuilt with set_synapses, my own slot loop on streams (seed,12,k), (seed,13,k) and (seed,17,k), and my own scoring.
   - **Slots:** all 200 slots per seed agree with the driver's log on n_R50, n_rec, recall, spurious, missing, intrusions, joint, both, ignition, lines, leak_A, leak_C, kind, target and age.
   - **Learning and state:** items, A, R, E and cont_frac are identical. mem.v, vbar, rec.v, both rings, net.t, the store and the feedback keys at M=120 and M=200 are bitwise equal to the driver's snapshots.
   - **Block criteria, seed 93 (my code = record):**
     - M=120: C1 0.700, C2 1.000, C3 1.000, joint 0.900, D3 1.000, O3 memory 0.55, O3 content 0.90, both 0.675.
     - M=200: C1 0.275, joint 0.825, O3 0.25/0.85.
     - Per kind at M=200: recent 0.2, uniform 0.4, cohort 0.25; cohort-500 uniform C1 0.333 (n=3).
     - Leak: recalled 0, L_A = L_C = B_A = B_C = 0, positive control 1.0, ok True.
   - **Block criteria, seed 94:** M=120: C1 0.6, joint 0.95, O3 0.7/0.95. M=200: C1 0.325, joint 0.875, O3 0.4/0.85.
   - **Validity (my code = record):** forward store = plain P2-E1 at both loads; mean eligible fraction 0.98665 and mean |A| 20.085 (seed 93); feedback union holds; no store change in any slot; my schedule audit finds 0 violations.
   - **Habituation:** I re-ran all copies with my own sham-step code. Per-step 'both', scored, L_rep, L_ctl, rec_rep, rec_ctl, col_rep, col_ctl and per_rep_both all match, and repetition-1 rasters are identical on both copies.
     - Seed 93: n_scored 2/1, eligible 0/0, O4 False and not estimable. Recovery False with n [0,0], p0 0.065/0.018. Collateral True with n [2,2] and [1,1], p0 0.276/0.210.
     - Seed 94: recovery n [1,0], collateral [3,3] at M=120.
   - **Labels (mine = driver):** ONLINE INDEX FAIL, ONLINE CONTENT FAIL, HABITUATION NOT ESTIMABLE, RECOVERY NOT ESTIMABLE.

2. **Spike-for-spike check from deep copies.** From the seed-93 S120 snapshot, run to step 152, I took two deep copies per step. One ran the driver's step_k, the other my learn plus slot code. Steps 153-176 (block-200 recent, uniform, cohort, novel and blank slots), 500 ticks each: the inp, mem and rec rasters and the final states are identical.

3. **Full config, seed 95, main line only to M=1000** (about 2 min per pass) **plus 2 habituation items at M=500.**
   - All 1000 slots agree. The only reported mismatches were the field 'recall', which the driver also stores for blank slots and my script did not; that is my artefact.
   - M=500: C1 0.88, C2 1, C3 1, joint 0.995, D3 1, O3 0.85/0.99.
   - M=1000: C1 0.72, joint 0.945, O3 0.71/0.97; per kind recent 0.80, uniform 0.66, cohort 0.71; cohort-500 uniform C1 0.733 (n=15).
   - Every leak statistic is 0.0, positive control 1.0, forward store = P2-E1, mean eligible fraction 0.98757, mean |A| 19.93, feedback union holds.
   - The habituation plans follow the contract rules (collateral overlaps 1-3 cells). The driver's hab_copy and my copy give identical per-step 'both' for items 0 and 1 on both copies. Item 1 shows clear habituation on the repeated copy.

4. **Synthetic checks.**
   - score_slot and block_criteria on 3 synthetic blocks with non-zero leaks (L_A 0.17-0.29, B_A 0.27-0.37) agree with my code.
   - hab_criteria and _hab_fast agree with my O4/O5 rules on 300 random 50-item sets under the full contract.
   - labels() agrees with my label rules on 3000 random 5-seed, 2-load record sets.

5. **Full-config schedules, seeds 90-99.** All built on attempt 0. My audit found 0 violations of the cohort rules, sub-block mix, age-0 blanks, the cohort-500 spread (2,2,2,2,2,1,1,1,1,1), target ages, uniqueness within a block, or masks.

6. **verdict() on the real results file:** KeyError 'gated'; reproduced as described in R1.
