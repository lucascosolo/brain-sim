# P2-E5 draft red-team: completeness critic

Given the three lenses' findings and verdicts; asked only what is still missing. Run 2026-10-10 to 2026-10-11. Recorded verbatim.

## Verdict

The draft cannot be frozen as written. Beyond the listed findings, I found one blocker and three majors. The other lenses missed them, mostly because the draft predates the owner's guidance of 2026-10-11 (DECISIONS.md lines 472-503, commit 21245c1, after the draft's e736e81) and none of them read it. That guidance (1) makes P2-E5 the instrument that decides which mechanism contract comes next ("whichever failure remains most consequential under the structured-input tests"), (2) calls the plateau-set store an upper-bound diagnostic, not a solution, and (3) sets the research target that the network must find its own active cells without being handed A(x).

Four exploratory checks bear on this. All used seeds 44 and 45, replayed P2-E3's own readout through each store on the same test raster, and are not results.
- At M = 500 the plateau-set "upper bound" is limited by the readout operating point. At J_fb* = 2.8 and g = 0.3 it gives joint 0.925 with S4 at 0.88, but 24 of 72 (J_fb, g) points pass, with a best joint of 1.000.
- The main store has no passing point at either load. Its best joint is 0.555-0.565 at M = 500 and 0.025 at M = 1,000.
- At M = 1,000 the upper bound fails at every point, with a best joint of 0.585-0.600, not the 0.16 measured at the frozen point.
- The network's own continuation spike count separates A(x) from sibling responders almost perfectly (AUC 0.996-0.9996). A store written only from cells with at least 3 continuation spikes reproduces the plateau-set store's content numbers exactly at both loads.
- The attribution rules the lenses propose (B1, FID5-1, M3) would read the M = 500 failure as 'index-limited' with probability 0.93-0.97. On the same raster, the write alone accounts for about 0.8 of the joint.
- Learning order (cyclic or random) changes nothing.

Also missing are a recomputed cost and a pinned order of runs.

## Findings

### C1 [blocker] The draft does not implement the owner's 2026-10-11 guidance: P2-E5 must rank the failures that decide the next contract, and it cannot

- where: DECISIONS.md 472-503 (2026-10-11, commit 21245c1, after draft commit e736e81). Draft lines 9 and 149-156 ('against the plateau-set baseline'), 41-50 (settled protocol only), 112-130. Owner_intent FID5-1/FID5-3 and methodology B1 do not cite this entry.
- evidence: 1. The guidance names two distinct problems: learning-time contamination of the responder write, and operating-point instability under continuous input. It orders: 'put first whichever failure remains most consequential under the structured-input tests (P2-E5)'.
2. The draft tests only settled frozen copies. That removes operating-point instability by design, so P2-E5 cannot measure the second problem on structured input at all.
3. FID5-3's online arm learns online but tests on settled copies. The fidelity lens logs show settled C1 0.945-0.97 (log_online_s60_seed4*.txt), so it measures contamination only.
4. The exploration also shows a third failure outside the owner's two-problem taxonomy: forward-index cross-talk. At M = 1,000, C2 is 0.47-0.52, and the plateau-set store fails at all 72 readout operating points (best joint 0.585-0.600; grid_44_*.log).
5. The guidance calls the plateau-set store 'an upper-bound diagnostic, not an acceptable solution'. The draft still frames the next step as a mechanism tested 'against the plateau-set baseline'.
6. No predeclared reading turns P2-E5's numbers into the ranking the owner asked for. Without one, the order of the next contracts would be decided after the fact, or would need fresh seeds.
- recommendation: 1. Add a predeclared section 'Which failure is most consequential'. Per seed and load, on the 200 gated half cues, compute three paired losses:
   - (a) contamination = joint(upper-bound store at its own operating point, see C2) - joint(own store), on the same settled raster;
   - (b) index = max(0, 0.90 - joint(upper bound at its own operating point)), with C2 and C4-spurious named;
   - (c) operating point = joint(own store, settled twin) - joint(own store, online test).
2. Get (c) from one reported structured arm on P2-E4's frozen online driver. Replace only `_pat`, and gate nothing online.
3. The largest loss on at least 4 of 5 seeds at a load names that load's most consequential failure. Split or tied outcomes go to the owner. Give each outcome's probability in the power section.
4. Replace 'against the plateau-set baseline' with 'with the plateau-set store as an upper-bound diagnostic (owner, 2026-10-11)'. State that no correction may read A(x).
5. State that an index-dominant outcome at M = 1,000 is outside both of the owner's named problems, and goes to the owner before any mechanism contract.

Exploratory predictions: at M = 500 contamination dominates (about 0.8; index about 0). At M = 1,000 the index dominates (about 0.3, with contamination about 0.6 at the best readout point). Operating point under structure is unmeasured. P2-E4's exploration on independent items had online C1 0.69-0.79 against settled C1 of about 0.95, and content 0.95-0.98.

### C2 [major] The plateau-set 'upper bound' is evaluated at a readout operating point calibrated for the responder store on independent items, so it is not an upper bound

- where: Draft lines 91 ('No calibration'), 115-116 (plateau-set arm), 142 (prediction 'about 0.94'), 151 (next contract 'against the plateau-set baseline'). Methodology M1 ('oracle passes 0.08-0.15 at M = 500'; 'the gate cannot recognise a successful correction'). B1/FID5-1 attribution through the plateau-set store passing S2 and S4.
- evidence: Exploratory, seed 44: P2-E3's readout() over J_fb {1.5..6.0} x g {0..1.0} (72 arms) on the same raster. Values are given as cyclic order / random order.
- **Plateau-set store, M = 500.**
  - At the frozen point (2.8, 0.3): joint 0.925 / 0.920, D4 0.88 / 0.88. S4 fails at the frozen point.
  - 24 / 18 of 72 arms pass. Best joint 1.000 / 0.995, D4 1.000. Passing window g 0.4-0.8, and (2.8, 0.4) passes.
- **Main store.** 0 of 72 arms pass at either load. Best joint is 0.565 / 0.555 at M = 500 (D1 falls to 0.77-0.89 as g rises) and 0.025 at M = 1,000. So the main store's FAIL is not an artefact of J_fb*.
- **Plateau-set store, M = 1,000.** Frozen point 0.16 / 0.15. Best 0.600 / 0.585 (J 5, g 0.8). 0 of 72 arms pass.

Consequences:
- M1's conclusion that an item-specific write cannot pass at M = 500 is mainly an operating-point artefact.
- The index-attributable loss at M = 1,000 is about 0.3, not about 0.74.
- A correction contract that reproduced the upper-bound store at P2-E3's frozen J_fb*/g could fail S4 at M = 500 from the readout alone. The plateau-set store's density is 20 cells per item, against 50-87 for the main store.
- recommendation: 1. Report every same-raster store (main, plateau-set, and C4's activity-gated stores) over a predeclared J_fb x g grid. Readout replay is free. Report:
   - the value at the frozen point;
   - the best point, labelled optimistic because it is selected on the same data;
   - the passing-window size.
2. Define 'upper bound' as the best grid value, and use it in C1's ranking and in the power section (M1).
3. State in the 'If it fails' section that a later correction changes store density. Its readout must therefore be recalibrated on a held-out seed by P2-E3's calibration rule (P2-E3 calibrated J_fb on seed 0), or its frozen readout must be argued, before gating.
4. Add to the predictions: no main-store window at either load; the plateau-set store has a window at M = 500 and none at M = 1,000.

### C3 [major] The attribution readings the lenses recommend are not mutually exclusive, and at M = 500 they would almost surely misattribute the failure to the index

- where: Methodology B1 item 3 ('index-limited where the plateau-set store also fails or S1's C2 fails'). Owner_intent FID5-1(b) ('write-attributable' requires S1 to hold and the plateau-set arm to meet S2 and S4 on every gated seed). Methodology M3 labels.
- evidence: Exploratory per-cue rates at M = 500 (4 runs, seeds 44-45, methodology and implementation lenses): C2 0.895-0.92; plateau-set joint 0.925-0.94; plateau-set D4 0.88-0.95.

Using plant2.power over 5 seeds, with logit seed SD 0 / 0.18 (attr_power.log):
- P(S1 holds on every seed) = 0.22 / 0.16.
- P(plateau-set S2 and S4 on every seed) = 0.30 / 0.21.
- P(FID5-1 'write-attributable') = 0.065 / 0.033.
- P(B1 'index-limited' fires) = 0.935 / 0.967.
- P(both of B1's readings fire on the same load) = 0.23 / 0.18.

Yet on the same raster, swapping the store moves the joint from 0.10-0.15 to 0.92-0.94, and median intrusions from 69-78 to 1. P2-E3 addendum item 5 already requires future contracts to make readings mutually exclusive. The P2-E4 exploration also shows that index and content can dissociate (P2-E4-diagnosis-plan: 19-26 % of cues show content without index), so C2 alone cannot override a store contrast.
- recommendation: 1. Replace absolute-bar attribution with graded, paired, exclusive and exhaustive readings per load, built on the upper bound at its own operating point (C2). For example:
   - CONTAMINATION-DOMINANT: upper bound >= 0.75 and upper bound - own >= 0.5, on >= 4 of 5 seeds;
   - INDEX-DOMINANT: upper bound < 0.5 on >= 4 of 5 seeds;
   - MIXED: otherwise.
2. Report S1 and C2 beside the readings, never as an override.
3. Put each reading's probability at the exploratory rates in the power section. Expected: CONTAMINATION-DOMINANT at M = 500 with P near 1, and INDEX-DOMINANT at M = 1,000.
4. At M = 1,000, also report the own-store/upper-bound intrusion ratio (median 1,759-1,874 against 81-100). INDEX-DOMINANT must not be read as 'the write is fine'.

### C4 [major] The draft does not measure whether the network's own activity identifies its own cells, the owner's stated research target; exploration says it does almost perfectly

- where: DECISIONS.md 2026-10-11 ('A correction mechanism must let the network find which of its own active cells represent the current experience, without being handed that identity'). Draft lines 124-130 (per-load diagnostics) and 149-156 (only the error-correcting write is named). FID5-2 covers where contamination lands and the error at write time, not own-cell identification.
- evidence: Exploratory (rk.py). It copies E3.learn_one statement for statement and adds logging of continuation spike counts and first-spike ticks per cell. Its main store equals P2-E3's bit for bit ('k1 store equals main store: True'). The rk runs reproduce the implementation lens's numbers (main joint 0.130 / 0.100, plateau-set 0.925 / 0.935).
- **Continuation spike counts, last 200 items.** A(x) cells fire a mean of 5.1 / 5.0 spikes in 50 ms at M = 500, and 3.9 at M = 1,000. The extra responders fire 1.06 / 1.05, and 94 % of them fire exactly once. Count AUC is 0.9995 / 0.9996 at M = 500 and 0.996 at M = 1,000. First-spike latency separates them less well (AUC 0.78-0.80).
- **Store written only from cells with >= 3 continuation spikes,** at the frozen readout:
  - M = 500: joint 0.925 / 0.935 and D4 0.88 / 0.95. This is identical to the plateau-set store, with Jaccard 0.98 against A(x).
  - M = 1,000: joint 0.165 against the plateau-set store's 0.160.
- **Store from >= 4 spikes:** joint 0.935 / 0.940 at M = 500.

So, on this protocol, the information the owner wants the network to find is already in its own activity. A write gated by activity, with no error signal, reaches the upper bound at both loads. Its ceiling is the index-limited upper bound at M = 1,000. This changes which mechanism the next contract should test first, and it is unmeasured in the draft.
- recommendation: 1. Add reported, untuned write-time diagnostics at both loads, and in the online arm, since the responder write depends on the protocol (P2-E3 addendum 2):
   - per-item continuation spike-count and first-spike distributions for R(x)∩A(x) against R(x)\A(x), with the AUC;
   - stores written from R_k(x) for a predeclared k in {2, 3, 4, 6}, replayed through the same raster and scored as in C2.
2. Implement this as logging only. Bit-identity of the main store is a validity check.
3. Predeclare the reading 'own-cell identity is available from activity': AUC >= 0.95, and the best R_k store within 0.05 of the upper bound on every seed.
4. In 'If it fails', list the activity-gated write beside the error-correcting write as candidates for ruling 4.
5. State that adopting any k is a new mechanism contract, with k fixed by argument or held-out calibration and fresh seeds. It is never a P2-E5 rescue.
6. State that its ceiling at M = 1,000 is the index-limited upper bound.

### C5 [minor] The cost line and the order of runs no longer fit the arms now recommended, on a machine running P2-E4's gated lanes

- where: Draft lines 158-162 ('about 20 min per seed'). P2-E4 contract 'Order of runs on one seed' and 'Cost'. HANDOFF.md step 5 (P2-E4 gated seeds 16-20, two lanes, 80-120 min each).
- evidence: 1. The lenses' recommended additions are:
   - a plain-E1 equality run;
   - pooled and constant-family-size or F = 40 arms;
   - an F = 20 arm;
   - an online-learning arm;
   - C1's online-test arm (P2-E4's driver costs about 35 min per seed for its gated part);
   - write-time replays (fidelity's where.py took 560 s at M = 1,000);
   - readout grids (my runs took 90-370 s per store per load for 72 arms, under load).
2. Together that is about 1.5-2 h per seed unloaded, against the draft's 20 min.
3. P2-E4 gated seeds 16 and 17 are now running (gated_seed16.started and gated_seed17.started). The 1-minute load average was 5.5-5.8 during my runs.
4. The draft does not say whether the gated record is appended before the reported arms. Under P2-E4's run-once rule, a crash in a reported arm could leave a gated seed half-recorded.
- recommendation: 1. Recompute the cost per seed and in total.
2. Pin the order of runs per seed, as P2-E4 does: learn; test the gated copies; append the kill_test_seed record; then the reported arms, each in its own record, where a failure invalidates only that arm.
3. Schedule the gated seeds after P2-E4's gated lanes finish.
4. Keep the grid sizes in C2 and C4 small: a published P2-E3 J_GRID subset, and four values of k.

## Exploratory runs (labelled; not results)

- `/root/.cache/brain-sim/review/p2e5-redteam/completeness/grid.py` (seed 44; Full P2-E3 contract; F = 10, s = 60, cyclic family order (same generator streams as the implementation lens); M = 500 and 1,000. P2-E3 run_phase on a deep copy, then P2-E3's readout() over J_fb {1.5, 2.0, 2.4, 2.8, 3.2, 3.6, 4.0, 5.0, 6.0} x g {0, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0}, for the main and plateau-set stores.): EXPLORATORY.
- **M = 500, main:** frozen point 0.130 (reproduces the implementation lens); 0 of 72 arms pass; best 0.565 (J 2.8, g 0.7; D1 0.765).
- **M = 500, plateau-set:** frozen point 0.925 with D4 0.88; 24 of 72 arms pass (g 0.4-0.8); best 1.000.
- **M = 1,000, main:** best 0.025; 0 of 72 pass.
- **M = 1,000, plateau-set:** frozen point 0.160; best 0.600 (J 5, g 0.8); 0 of 72 pass.
- C2 0.895 at M = 500, 0.495 at M = 1,000.
- Outputs: grid_44_cyclic.log, grid_s60_seed44_cyclic.json.
- `/root/.cache/brain-sim/review/p2e5-redteam/completeness/grid.py` (seed 44; As above, but each item's family drawn at random (exploratory stream 26) instead of k mod 10.): EXPLORATORY. Learning order does not matter.
- **M = 500:** main frozen 0.140, best 0.555, 0 of 72 pass. Plateau-set frozen 0.920 (D4 0.88), best 0.995, 18 of 72 pass. C2 0.900.
- **M = 1,000:** main best 0.025. Plateau-set frozen 0.150, best 0.585, 0 of 72 pass. C2 0.520.
- Outputs: grid_44_random.log, grid_s60_seed44_random.json.
- `/root/.cache/brain-sim/review/p2e5-redteam/completeness/attr_power.py` (seed none (closed-form, plant2.power); Five seeds; logit seed SD 0 and 0.18. M = 500 exploratory rates averaged over 4 runs: C1 0.96, C2 0.91, C3 about 1, plateau-set joint 0.934, plateau-set D4 0.918.): EXPLORATORY.
- P(S1 holds on all seeds) = 0.22 / 0.16.
- P(plateau-set S2 and S4 on all seeds) = 0.30 / 0.21.
- P(FID5-1 'write-attributable') = 0.065 / 0.033.
- P(B1 'index-limited' fires) = 0.935 / 0.967.
- P(B1's two readings both fire) = 0.23 / 0.18.
- Output: attr_power.log.
- `/root/.cache/brain-sim/review/p2e5-redteam/completeness/rk.py` (seed 44; Full contract; F = 10, s = 60, cyclic order; M = 500 and 1,000. E3.learn_one copied statement for statement, plus logging of continuation spike counts and first-spike ticks per cell (k = 1 store bit-identical to main: True). Stores from R_k (k = 2, 3, 4, 6) and from first spike before tick 5, 10 or 20, replayed through the same raster at J 2.8, g 0.3.): EXPLORATORY.
- **M = 500.** A cells fire a mean of 5.10 continuation spikes, other responders 1.06; count AUC 0.9995; first-spike AUC 0.78. Joints: main 0.130, plateau-set 0.925 (D4 0.88), R_>=3 0.925 (D4 0.88; Jaccard with A 0.98), R_>=4 0.935, R_>=2 0.885, R_>=6 0.600, first<10 0.465.
- **M = 1,000.** Count AUC 0.996 (A 3.92 against 1.05). Joints: main 0.000, plateau-set 0.160, R_>=3 0.165 (Jaccard 0.91), R_>=4 0.240, R_>=6 0.350 (D1 0.355).
- Outputs: rk_44.log, rk_s60_seed44.json.
- `/root/.cache/brain-sim/review/p2e5-redteam/completeness/rk.py` (seed 45; As above, M = 500 only.): EXPLORATORY.
- Count AUC 0.9996 (A 5.02 against 1.06 spikes).
- Joints: main 0.100, plateau-set 0.935 (D4 0.95), R_>=3 0.935 (D4 0.95; Jaccard 0.98), R_>=4 0.940 (D4 0.96), R_>=2 0.885.
- C2 0.910.
- Outputs: rk_45.log, rk_s60_seed45.json.

## Reviewer's predictions

As drafted, I expect the verdict FAIL, as the other lenses do. S2 and S4 fail at both loads. S1 fails at M = 1,000 through C2 (about 0.5) and is a coin flip at M = 500. The draft's own signed-drift validity bar makes INVALID a real risk (B2).

Beyond the listed findings, from my exploratory runs on seeds 44-45:
1. No readout operating point rescues the main store at either load. In a 72-point J_fb x g grid, its best joint is 0.555-0.565 at M = 500 and 0.025 at M = 1,000.
2. The plateau-set reference is at the edge of the bar at the frozen J_fb*/g at M = 500 (joint 0.92-0.94, S4 0.88-0.95). At its own operating point it passes (best joint 0.995-1.000; 18-24 of 72 arms pass). At M = 1,000 it fails at every operating point (best 0.585-0.600).
3. The network's own continuation spike count identifies A(x) among the responders almost perfectly (AUC 0.996-0.9996). A store written only from cells with at least 3 continuation spikes reproduces the plateau-set numbers at both loads (0.925 / 0.935 at M = 500; 0.165 at M = 1,000).
4. So under the settled protocol, the most consequential failure is the responder write at M = 500 and the forward index at M = 1,000. The write is fixable in principle from the network's own activity, without an error signal. The index is outside both of the owner's named problems. Operating-point instability under structured input remains unmeasured until an online-test arm is added.
5. Learning order (cyclic or random) changes nothing (frozen-point joint 0.130 against 0.140).

All of these are exploratory, from two seeds, and are not results.
