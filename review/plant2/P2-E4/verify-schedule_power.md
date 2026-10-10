# P2-E4 contract verification: schedule and power

Fresh checker given only the files (revised contract at commit b1ec05a). Run 2026-10-10. Recorded verbatim, before synthesis.

## Verdict

The contract should not be frozen yet, but it needs only small fixes. The gated blocks themselves are buildable. On seeds 90-99 my own builder built both blocks at M = 500 and 1,000 on the first attempt. That builder picks each target from those still unused in the block. Every gated rule was met: exact counts, 10 sub-blocks of 5/5/8/3/2/1, no repeats (blank targets included), ages, and cohort items never probed before their block. Under that sampling the redraw rule is never needed, because age 0 and the uniform pool of 80 or more items are always free. Under the literal reading (draw ages independently, then check, then redraw) the redraw rule would never terminate.

One rule cannot be satisfied: the rolling uniform and oldest-probed slots in steps 162-181 have no legal target. This happens on all 10 seeds, 4-9 slots each, and no redraw rule covers stream 14.

A second problem is the scope of the cohort reservation. It names habituation duty, which exists only on copies. Yet settled twin A at M = 500 must run P2-E3's test, which cues items 1-100. That probes 51-64 of the 80 cohort-1,000 items on every seed. If validity check 7's audit covers copies, every seed would be INVALID.

Power: every number in the Power section reproduces with my own code except one. O1-O3 at P = 0.83 with M = 1,000 values O1 0.914 and O3 0.912, the draft's 0.646, the O4/O5 table to Monte Carlo precision, and the habituated share of 21-24 % all match. The exception is the draft-rule figure of 0.62. Under the stated model that figure is 0.17 over both loads, or 0.415 for one load.

The reference rates are taken inconsistently. C1 pools P2-E2 and P2-E3, while C2, C3 and oldest recall come from P2-E3 alone, and recorded 1.000 values are entered as 0.999 without saying so. With the P2-E3 system's own C1, the reference P falls to 0.75.

plant2/power.py implements the stated rules exactly:
- O4: habituated if L_rep <= L_ctl - 3, coded as not habituated if L_rep >= L_ctl - 2. Items are scored on repetition 1, eligible at L_ctl >= 8, the minimum is 25 eligible, and the rule is ceil(0.9 x eligible).
- O5: majority of 3, paired on the control copy, with a minimum of 25.

All counts are internally consistent:
- the block: 50 + 50 + 80 + 30 + 20 + 10 = 240, and 10 sub-blocks of 5/5/8/3/2/1 = 24;
- the 180 half cues = 50 + 50 + 80;
- the control copy: steps 2-90 = 89 other items;
- the stress blocks: 240;
- the probe-write arm: 170 = 200 x 0.85, and 1,370 = 1,000 + 200 + 170;
- the counts in power.py.

I made no edits under /home/user/brain-sim. Its bytecode caches predate my runs.

## Findings

### SP-1 [blocker] Rolling uniform and oldest-probed slots in steps 162-181 have no legal target; the builder fails on every seed

- where: docs/plant2/P2-E4-online-memory.md lines 146-147 ('Before step 162, no unreserved stored item of age >= 1 exists'), 152-161 (rolling shares from step 162: uniform 'unreserved, ages >= 21' 20 %, oldest-probed 'otherwise uniform' 10 %), 180-182 (builder asserts every rule; redraw only with stream (seed, 15, attempt))
- evidence: Item 160 is the last reserved item, so the first unreserved item of age >= 21 is item 161 at step 182. Steps 162-181 therefore cannot hold a uniform target, and before step 500 oldest-probed falls back to uniform. My builder (schedule.py / run_schedule.out) found 4-9 infeasible rolling slots on each of seeds 90-99, all of them uniform slots in 162-181. P(a stream-14 draw puts no uniform or oldest-probed slot in those 20 steps) = 0.7^20 = 0.0008. The redraw rule redraws stream 15 only, so it cannot help. The recent and blank slots ('ages 0-20') in 162-181 also reach only ages 0..k-161; any older age hits a reserved pool item. The step-162 rationale is also stale: recent and blank now include age 0, so item 161 could be targeted at step 161. The same class of defect as red-team M1: a rule the mandated builder cannot satisfy on any seed. It touches no gated count.
- fix: Add one sentence before freezing. For example: 'In steps 162-181, uniform and oldest-probed slots are recent slots, and recent and blank ages are drawn uniformly among the unreserved ages available.' Alternatively, give rolling stored-item kinds a start at step 182, with novel or untargeted blank slots before it. Extend the builder's assertion and the deterministic redraw to stream 14, or make the rolling rule feasible by construction.

### SP-2 [major] The cohort reservation is declared to cover copies, but settled twin A at M = 500 must probe most of cohort 1,000

- where: lines 144-145 ('no probe of any kind before its own block. That includes ... habituation duty and collateral duty'), 220-224 (twin A runs P2-E3's run_phase after step M), 272-275 (validity 7 audit), 303 (INVALID if a gated validity check fails); code: p2_e3_completion.run_phase -> p2_e2.evaluate -> p2_e1_btsp.test_sets (items 0-99 plus 100 random, half and full cues)
- evidence: Habituation and collateral duty happen only on copies after step M, so the rule as written counts copy-side probes. Twin A at M = 500 is also a copy after step M, before block 1,000. It runs P2-E3's test set, which always cues items 1-100 (1-indexed) plus 100 random items from 101-500. With the real TEST_PICK draws and my stream-15 cohorts, that probes 51-64 of the 80 cohort-1,000 items on seeds 90-99 (run_schedule.out, field twinA_M500_cohort1000_probed). The novel-duty twin runs the same readout at M = 500. If validity 7's 'realised probe log' covers copies, as the habituation clause implies, every seed is INVALID. If it does not, the rule text misstates its own scope.
- fix: State that the reservation and audit 7 apply to the main timeline only (validity 6 already guarantees that copies never feed back). Keep the exclusion of cohorts from the habituation and collateral pools as a declared design choice. Alternatively, explicitly exempt twin A's and the novel-duty twin's P2-E3 readouts at M = 500.

### SP-3 [minor] Reference rates are taken inconsistently; with the P2-E3 system's own C1 the zero-cost reference P is 0.75, not 0.83

- where: lines 323-339 (rates table, 'recorded settled rates of P2-E2 and P2-E3's gated seeds'; P = 0.83); plant2/power.py P2E4_RATES
- evidence: Recomputed from bench/results/plant2.jsonl (rates.py):
- C1 at M = 1,000: 0.944 is the mean over 10 gated seeds (P2-E2 seeds 6-10 at 0.949, P2-E3 seeds 11-15 at 0.938).
- C1 at M = 500: the same pooling gives 0.969, not 0.970.
- C2 0.989, C3 0.994 and oldest recall 0.954 / 0.972 are P2-E3 alone. The pooled values would be C2 0.986 and oldest 0.953 / 0.969; P2-E2's gated values are 0.983, 0.997 and 0.952 / 0.966.
- The recorded 1.000 values (C2, C3 and D3 at M = 500) are entered as 0.999 with no note.

P2-E4 runs the P2-E3 system. With P2-E3's own C1 (0.972 / 0.938), my exact-binomial code gives P(O1-O3 on all seeds and loads) = 0.747. Pooling every memory rate gives 0.821. The contract states 0.83. The O1 and O3 headroom at M = 1,000 rests on this choice. No power_reference row is in bench/results/plant2.jsonl yet.
- fix: State a single source rule: P2-E3 alone (the system under test), or P2-E2 + P2-E3 pooled for every memory measure. State the 0.999 cap. Report P under both rules, and note that the reference falls below 0.8 under P2-E3's own rates. Then append the power_reference record in the freezing commit.

### SP-4 [minor] The draft-rule figure '0.62 at 0.93' cannot be reproduced; under the stated model it is 0.17

- where: lines 354-355 ('The draft's unpaired rule passed with only 0.62 at 0.93 with no habituation (M3)')
- evidence: Setup: the draft rule (>= 8 of 10 late repetitions for >= 90 % of scored items, no control, no minimum), ICC 0.09, 50 items, per-cue rate 0.93, 40,000 sims (myhab.py, unpaired_probe.py). Results:
- one seed-load: 0.84;
- 5 seeds x 1 load: 0.415 (red-team M3 reported 0.396);
- 5 seeds x 2 loads: 0.170;
- 5 seeds x 3 loads (the draft's loads): 0.068.

A value of 0.62 appears only with ICC about 0.05 and one load. p2e4_reference() does not compute this number, so the power_reference record will not contain it.
- fix: Replace it with '0.17 over both loads and all seeds (0.40 for one load, M3)', and add the computation to plant2/power.py so the record carries it.

### SP-5 [minor] 'Ages uniform on 0-20' plus 'no item cued twice' plus 'redraw if infeasible' only works with a sequential sampler, and the realised ages are then not uniform

- where: lines 168 (recent: ages uniform on 0-20), 172 (blank target ages 0-20), 177 (no repeats), 180-182 (assert, then redraw with (seed, 15, attempt))
- evidence: Literal reading: draw recent and blank ages i.i.d. on 0-20 (uniform and full items distinct within their kind), then check no-repeat. Seed 90 gave 0 feasible blocks out of 1,500 attempts at M = 500 and 0 out of 1,500 at M = 1,000 (redraw_indep.out), so the redraw loop would not terminate.

Sequential exclusion: drawing each age among those whose item is still unused is feasible on the first attempt for all 10 seeds, and always by construction. Under it, the realised recent ages pooled over 1,000 cues (seeds 90-99) have mean 9.17 against 10.0 for uniform. Age 0 occurs 64 times and age 20 only 31 times, against 47.6 expected (chi2 30.3 on 20 df). The contract also does not say whether blank targets count as uses under 'no stored item is cued twice'. Validity 7 says 'nothing repeats'.
- fix: Declare the sampler: 'each recent or blank age is drawn uniformly among ages 0-20 whose item is not yet used in the block'. Say whether blank targets count as uses. Report the realised age distribution. The redraw rule then remains only as a guard.

### SP-6 [minor] Collateral selection: max-overlap ties are the norm, the lowest-index tie-break picks old items, and the collateral is often among the control copy's 89 cues

- where: lines 196-205 (control copy: 89 other unreserved stored items outside the 50; collateral = max overlap with A, ties to the lowest index); power table at lines 344-348 (collateral modelled at the recovery rate)
- evidence: I took A(x) from P2-E1's plateau stream (stream 2, 4,000 uniforms per item; collateral_alt.out), seeds 90-99.
- Overlap: the maximum overlap with any candidate is 2 cells for most items. At M = 500 it is only 1 cell for 10-18 of the 50 items.
- Ties: the number of items tied at the maximum has a median of 2-4 and reaches 98.
- Age: the tie-break therefore yields old items. Median collateral age is 266 at M = 500 against 185 for the habituation items, and 831 against 448 at M = 1,000. At M = 1,000, 22-30 of the 50 collaterals are pool items (1-160).
- Pairing: with the 89 others drawn from the same pool, x's collateral is itself one of the control copy's 89 cues for 10-20 of 50 items at M = 500 (mean 13.4) and 0-9 at M = 1,000. In those items, y gets one cue on the control copy, 15.5-60 s before its collateral cue, and none on the repeated copy.
- The O5 power model assumes the collateral's per-cue rate equals the recovery rate.
- fix: Exclude x's collateral item from x's 89 control cues. Break ties at random on stream 16, or by the age closest to x, rather than by lowest index. Define the pools: whether a cohort counts as 'unreserved' after its block, whether the 89 are drawn per item, and their age range. Report collateral overlap and age.

### SP-7 [minor] The 'probed vs never-probed retention at M = 1,000' comparison has no cohort-500 measurement at that load

- where: line 158 (oldest-probed: cohort 500 items after step 500, rolling only), lines 166-173 (block mix has no oldest-probed kind), line 384 (reported comparison at M = 1,000)
- evidence: Oldest-probed slots exist only in rolling steps (501-760, and 1,001 onwards on the continuing line). On seeds 90-99 there were 21-35 such slots in 501-760, reaching 19-28 distinct cohort-500 items (ages 365-757). That means loads 501-760, not 1,000, against cohort 1,000 measured at loads 761-1,000. The selection rule within cohort 500 is not stated (random with replacement, or least-recently probed). Whether block-1,000 uniform cues may draw cohort-500 items is undefined, because 'unreserved' after a cohort's block is not defined.
- fix: Define the comparison at matched load or matched age bins without changing the gated block counts. For example, compare at matched ages from rolling slots, or cue the 80 cohort-500 items in the online rhythm on a copy after step 1,000. State the oldest-probed selection rule, and state whether cohorts are 'unreserved' after their block.

### SP-8 [nit] The novel-duty twin does not have 'the same input duty'

- where: lines 229-231 ('every slot, gated blocks included, holds a fresh novel cue ... It has the same input duty')
- evidence: Mean active input lines per main-line slot:
- 42.5 in steps 1-161 (85 % novel half cues, 15 % blank);
- 47.5 in rolling slots from step 162 (75 % half cues of 50 lines, 10 % full cues of 100 lines, 15 % blank);
- 47.9 in blocks (210 half, 10 full and 20 blank per 240).

A novel half cue in every slot gives 50 lines, which is 18 %, 5 % and 4 % more.
- fix: In the twin, leave the main line's blank slots blank and give full-cue slots a novel full pattern. Alternatively, say 'about the same input duty'.

### SP-9 [nit] 'Recovers within 10 s' does not match when the recovery cues are scheduled

- where: lines 56-57 (hypothesis), 199-200 (blank steps 101-120, then recovery cues at steps 121, 123 and 125)
- evidence: The last repetition is in step 100's slot. The recovery cues sit 21, 23 and 25 steps later: 10.5, 11.5 and 12.5 s, not within 10 s.
- fix: Write 'recovers 10.5-12.5 s after the last repetition', or 'after a 10 s pause'.

### SP-10 [minor] Other target and stream choices the builder had to make that the contract leaves open

- where: lines 160 and 173 (full cues: no target rule), 158 and 169 ('unreserved' after a cohort's block), 178-179 (masks drawn on stream 15 only for block cues), 181 (redraw scope), 186-198 (stream-16 keys per load)
- evidence: Implementing the builder required these undeclared choices:
- the target rule for full cues in blocks and rolling slots (any age, recent, or old; I used any unreserved item);
- whether uniform cues in block 1,000 and in rolling slots after 500 may use cohort-500 items;
- the mask streams for rolling and novel half cues;
- whether a redraw (seed, 15, attempt) also redraws the cohorts and masks, which come from the same stream;
- how stream 16 is keyed per load, given that the 50 items, the 89 controls, the sham patterns and the collateral masks all draw from it.

Each choice is deterministic once stated, but none is stated.
- fix: Add one sentence for each choice to the schedule rules before freezing, so the unit test on seeds 90+ checks declared rules rather than the implementer's choices.

## Computed (exploratory; not results)

All scripts and outputs are in /root/.cache/brain-sim/review/p2e4-verify/schedule_power/. Seeds used: 90-99, plus seed 90 for the redraw estimate. Monte Carlo generator seeds: 42 and 43.

- **rates.py**: recomputes the reference rates from bench/results/plant2.jsonl.
  - P2-E2 gated seeds 6-10 against P2-E3 seeds 11-15.
  - C1 at M = 500: 0.966 / 0.972, pooled 0.969 (contract 0.970).
  - C1 at M = 1,000: 0.949 / 0.938, pooled 0.9435 (contract 0.944).
  - C2, C3, oldest recall, joint, D3 and D4 equal P2-E3 alone; recorded 1.000 values are entered as 0.999.
- **run_powerpy.py (.out)**: plant2/power.py's p2e4_reference() output. O1-O3 = 0.830; at M = 1,000, O1 0.914 and O3 0.912. The O4/O5 table matches the contract.
- **mypower.py (.out)**: my own exact binomial with a 1,200-point normal grid for the seed effect.
  - Bars: 162 of 180, 27 of 30, 72 of 80.
  - P(O1-O3) = 0.830; the draft's 120/60/40 gives 0.646; with seed SD 0, 0.9125.
  - Alternative pooling: 0.821. P2-E3's own C1: 0.747. One shared seed effect per seed-load (Monte Carlo): 0.832.
- **myhab.py (.out)**: my own beta-item Monte Carlo, 40,000 sims, ICC 0.09, 50 items, 5 seeds x 2 loads.

  | per-cue rate | O4 | O5 recovery | O5 collateral | O5 both |
  |---|---|---|---|---|
  | 0.95 | 0.998 | 0.995 | 0.994 | 0.988 |
  | 0.93 | 0.986 | 0.952 | 0.948 | 0.903 |
  | 0.92 | 0.967 | | | 0.80 |
  | 0.90 | 0.865 | 0.683 | 0.684 | 0.467 |

  - With the late rate x 0.85, O4 = 0 and 20-24 % of eligible items habituated.
  - Draft unpaired rule at 0.93: 0.84 per seed-load, 0.415 over one load, 0.170 over two, 0.068 over three.
  - Mean eligible count: 24.9 at a per-cue rate of 0.77.
- **unpaired_probe.py**: shows 0.62 arises only at ICC about 0.05 with one load.
- **schedule.py + run_schedule.py (.out, .json)**: my builder and audit, seeds 90-99.
  - Both gated blocks feasible on the first attempt on every seed; the main-line audit found no errors.
  - Rolling slots: 4-9 infeasible uniform slots per seed, all in steps 162-181.
  - Oldest-probed: 21-35 slots in 501-760, reaching 19-28 distinct cohort-500 items.
  - M = 250 report: 18-28 stored-item cues in steps 201-250.
  - Twin A at M = 500 probes 51-64 cohort-1,000 items.
  - Recent ages: mean 9.17, chi2 30.3 on 20 df.
- **redraw_indep.py (.out)**: under independent draws, 0 of 1,500 block attempts are feasible at either load.
- **collateral_alt.py (.out)**:
  - Maximum overlap is 2 cells for most items, 1 cell for 10-18 of 50 at M = 500.
  - Ties at the maximum: median 2-4, up to 98.
  - Median collateral age: 266 against 185 for habituation items (M = 500), and 831 against 448 (M = 1,000).
  - At M = 1,000, 22-30 of 50 collaterals are cohort items.
  - The collateral is among the control copy's 89 cues for 10-20 of 50 items at M = 500 and 0-9 at M = 1,000.
