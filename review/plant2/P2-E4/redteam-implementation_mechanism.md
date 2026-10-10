# P2-E4 draft red-team: implementation and mechanism lens

Fresh reviewer given only the files (draft at commit 953851e); each finding then checked by a separate refuter. Run 2026-10-10. Recorded verbatim, before synthesis.

## Verdict

The draft cannot be frozen as written. Under the never-probed-cohort rule the M = 250 gated block cannot be built: 180 non-novel slots would have to fit into 129 steps. The implementation claims hold: the forward store stays bit-identical to P2-E1 without quiet(), the per-write rec reload and deep copies work, and the replay matches both a fresh and a continuously running live rec spike for spike. The mechanism exploration (seeds 42 and 43, exploratory only) changes what the experiment will show:
- At I = 250 ms, online C1 at M = 1,000 is 0.70-0.80.
- The online timeline inflates the continuation responders, so the feedback store fails P2-E3's content bar even after a settle (0.81 and 0.89).
- The "easier" I = 2,000 ms arm collapses content (joint 0.165).
- The habituation, control and reliability copies settle because they stop learning.

The most important fixes before freezing:
- a feasible M = 250 block;
- copies that keep the online operating point;
- a same-seed P2-E3-protocol reference line, so online cost splits into its write and readout parts;
- a no-probe twin that actually differs from the main line;
- predictions and power rewritten from these numbers, with I and every parameter left as declared.

## Findings

### B1 [blocker] The M = 250 gated block cannot be built under the never-probed-cohort rule

- where: Draft lines 127-139 (gated blocks: the 240 steps ending at M; exact counts), 141-146 (pool items 1-120, three disjoint cohorts of 40, no probe of any kind before the cohort's own slots), 115-125 (rolling slots from step 1)
- evidence: - Three cohorts of 40 take up the whole 120-item pool, so every item 1-120 is reserved until its own block.
- The draft's own ages (31-249 at M = 250) fix age = s - i. Block 250 is steps 11-250, so no non-reserved stored item exists before step 122.
- The block still needs 40 recent + 40 uniform + 20 full + 40 blank + 40 cohort = 180 non-novel slots. Only steps 122-250 can hold them: 129 slots.
- Steps 11-121 give 111 slots that only a novel cue can fill, and only 60 novel cues are planned.
- Rolling slots 1-10 likewise have no placeable target except a novel cue.
- Blocks 500 and 1,000 are feasible.
- Script: ~/.cache/brain-sim/review/p2e4-redteam/implementation/schedule_feasibility.py.
- recommendation: - Redesign block 250 before freezing. Options: start it at step 131, with counts scaled and power recomputed; or shrink or re-time the pool so that some non-reserved items exist early.
- Define which kinds may fill slots before any eligible target exists (novel only).
- Make the stream-15 schedule builder assert, at seed start, that every slot can be filled under all exclusion rules, and include that check in the contract digest tests.
- independent verifier: **confirmed** (severity should be blocker): I re-derived this from the draft text and re-ran schedule_feasibility.py (arithmetic only, no seed). Three disjoint cohorts of 40 use up the whole pool, items 1-120 (lines 142-143). Line 144 bars every probe kind before a cohort's own slots, blank targets included. The ages on line 146 (31-249 at M = 250) only work if age = s - i, with cohort slots in steps 151-250. So in block 11-250 the first non-reserved stored item (item 121) can be targeted only from step 122. That leaves 129 steps for 180 non-novel slots (recent, uniform, full and blank need non-reserved targets, and the cohort slots also fall in 151-250). The other 111 steps can hold only novel cues, and only 60 are planned. The '(or on 1..k-1 early on)' clause on line 132 shows the author expected recent probes of items 1-10, which the reservation rule forbids. Rolling steps 1-10 likewise can hold only novel cues. Blocks 500 and 1,000 are feasible. The schedule is internally inconsistent and cannot be built, so it must be redesigned before freezing. The recommendations are sound: re-time or shrink block 250 or the pool, and have the stream-15 builder assert feasibility.

### M1 [major] The online timeline changes the feedback write itself (responders inflate); the settled twin does not measure online cost, and I = 2,000 ms is not the easier setting

- where: Draft lines 151-154 (settled twin 'measures the cost of online operation'), 90 and 257-258 (I = 2,000 ms called 'the easier setting'), 38-41 and 247 (hypothesis and online cost), 33-34
- evidence: Exploratory, full contract config, M = 1,000, diag_fb.py and duty.py. P2-E3's own protocol (quiet() and back-to-back encodings) against the online line (I = 250 ms), seed 42 / 43:

| measure, items 751-1,000 | P2-E3 protocol | online |
|---|---|---|
| continuation offset (mV) | 8.47 / 8.47 | 6.85 / 6.84 |
| \|R(x)\| | 28.7 / 28.5 | 45.2 / 44.7 |
| R - A | 8.6 / 8.6 | 25.1 / 24.9 |
| Jaccard(R, A) | 0.73 / 0.73 | 0.49 / 0.50 |
| feedback store | 2.12 M / 2.12 M | 2.50 M / 2.49 M |

Settled test, through each line's own feedback store:
- online line: joint 0.81 / 0.89 (D2 0.815 / 0.895, D4 0.76 / 0.86), with memory C1 0.97 / 0.925;
- P2-E3-protocol line, same seed: joint 0.98 / 0.99.

The online line's raster read through the same-seed P2-E3-protocol store gives 0.98 / 0.99, and through the plateau-set store 0.995 / 0.995. So the content loss comes entirely from the online-written store. Forward store, A(x) and E(x) are identical between the two lines.

Duty arm, I = 2,000 ms (seed 42, M = 1,000):
- continuation offset 4.08 mV;
- \|R\| 133, Jaccard 0.18;
- feedback store 3.99 M;
- settled joint 0.165 (D2 0.17);
- online memory C1 0.956 / 0.978 (recent / uniform).

Conclusions:
- P2-E3's content PASS depended on back-to-back learning holding the continuation offset near 8.5 mV.
- Both the main line and its settled twin read the same online-written store, so 'online minus settled twin' cannot see the write-side cost.
- recommendation: - Add a same-seed P2-E3-protocol reference line (E3.learn plus run_phase, about 2 min per seed) at each gated load.
- Add store-swap readouts: the online raster read through the reference store, and through the plateau-set store. Online cost then splits into a write part and a readout part.
- Report \|R(x)\|, R - A, Jaccard and the continuation offset by age bin, for the main line, the no-probe twin and the duty arm.
- Reword the settled-twin sentence and the duty arm's 'easier' label, and predict content collapse in the duty arm.
- State in the hypothesis or limitations that the responder write's specificity depends on the operating point at write time.
- Flag the protocol dependence for an append-only P2-E3 addendum.
- Change no parameter or interval in response.
- independent verifier: **partly** (severity should be major): The core holds. I checked diag_fb.py: it runs the same seed under E3.learn (quiet() plus back-to-back encodings) and under Online (no quiet, 250 ms interval). The plateau set A, eligible set E and forward store are identical by construction (the same _plat, _learn_in and _coin streams). The saved outputs match the finding: in items 751-1,000, |R| is 28.7 against 45.2, Jaccard 0.73 against 0.49, continuation offset 8.47 against 6.85 mV, and the feedback store 2.12 M against 2.50 M. In the store swap, the online line's settled raster gives joint 0.81 / 0.89 through its own store, but 0.98 / 0.99 through the P2-E3-protocol store and 0.995 through the plateau-set store. The settled twin is a deep copy of the online line, so it shares the online-written store, and 'online minus settled twin' (lines 151-154, 247) cannot see the write-side cost. Worse, it will show online content (0.94-0.96) ABOVE settled (0.81-0.89), which reads as a negative online cost. The draft does anticipate on lines 32-34 that vbar changes later writes, but it blames probes and never connects this to the twin. The overstated part: 'I = 2,000 ms is not the easier setting' is true for content (settled joint 0.165, |R| 133, Jaccard 0.18) but false for online memory recall, which is easier at I = 2,000 (C1 0.956 / 0.978 against about 0.76 at I = 250). Online content at I = 2,000 was not measured (no live rec), so content collapse there is a prediction, as the finding itself says. The recommendations (a same-seed P2-E3-protocol reference line, store-swap readouts, reporting |R|, Jaccard and offset by age bin, rewording without any parameter change) are appropriate.

### M2 [major] Online memory recall at I = 250 ms fails far below the bar at M = 1,000; the I = 250 argument ignores accommodation of the 50 % encoding duty

- where: Draft lines 83-90 (why I = 250 ms: membrane decay only), 284 and 290 (O1 predicted 0.88-0.95; most likely HABITUATION FAIL; P(PASS) 10-20 %), 47-50 (limitation scoped to O4)
- evidence: Exploratory: main_run.py and residual.py, seeds 42 / 43, I = 250 ms (50 / 100 / 100 ms), live rec, a rolling-style probe mix.

| load (steps) | recent C1 | uniform C1 |
|---|---|---|
| M = 1,000 (761-1,000) | 0.765 / 0.803 (n = 68 / 66) | 0.761 / 0.700 (n = 46 / 50) |
| M = 500 (261-500) | 0.964 / 0.955 | 0.938 / 0.889 |
| M = 250 (11-250) | 1.0 / 1.0 | 0.957 / 0.924 |

- Ages >= 281 at M = 1,000, an O3 proxy: C1 0.80 / 0.70. At M = 500 (ages >= 150): 0.89 / 0.86.
- C2 = 1.0 and novel ignition < 10 cells for every novel cue.
- Online content joint at M = 1,000: 0.935-0.956.
- The threshold offset (vbar - rest) at probe time averages 6.8 mV over block 1,000 and reaches 7.6-7.7 mV at step 1,000. The same-seed settled twins reach C1 0.970 / 0.925.
- Paired check, same 30 half cues (habit_settle.py, seed 43, M = 1,000): C1 0.767 online against 1.000 after 40 s of background, as the offset fell from 7.62 to 3.73 mV.
- recommendation: - Keep I = 250 ms. It was fixed by argument before any run, and moving it now would be outcome-informed.
- Replace the predictions with these numbers: ONLINE FAIL at M = 1,000 is near certain, and possible at M = 500.
- Feed them into the power Monte Carlo.
- Extend the 'frozen accommodation' limitation from O4 to O1-O3: the encoding duty raises vbar.
- Report the probe-time offset per block.
- independent verifier: **confirmed** (severity should be major): I recomputed from the saved slot logs (verify script ~/.cache/brain-sim/review/p2e4-redteam/verify_implementation/agebins.py, which reads implementation/out_seed42.json and out_seed43.json; no new simulation). Online C1 at M = 1,000: recent 0.765 / 0.803, uniform 0.761 / 0.700. Ages >= 281: 0.80 / 0.70. At M = 500, ages >= 150: 0.89 / 0.86. The blocks' mean probe-time offset is 6.84 / 6.83 mV, reaching 7.7 / 7.6 mV. Pooled half cues give C1 0.76, so the binomial P(>= 108/120) is about 1e-4 per seed: ONLINE FAIL at M = 1,000 is effectively certain. At M = 500 (seed 43: 0.925, so P about 0.88; cohort-age proxy 0.86-0.89) it is plausible. The exploratory mix had 25 % blanks, against about 15 % in the draft, so the draft's higher cue duty would, if anything, raise vbar further. The cause is supported by habit_settle.py: on the same 30 cues, C1 is 0.767 online and 1.000 after 40 s of background, as the offset falls from 7.62 to 3.73 mV. The settled twins give 0.97 / 0.925 on the same store. The draft's I = 250 justification (lines 83-88) considers only membrane decay, and the frozen-accommodation limitation (lines 49-50) and the operating-point routing (lines 206-208) cover only O4. If O1 fails for the same operating-point reason, the draft gives no matching route and would mislead the reading. The predictions are already slated for replacement (lines 278-279), but the limitation and verdict text are contract text. Keeping I = 250 unchanged is correct.

### M3 [major] Habituation, control and reliability copies stop learning, so they settle during the arm; O4, O5 and the power Monte Carlo's per-item rates come from a different operating point

- where: Draft lines 160-173 (copies with no learning; the control copy gets 39.7 s of background; scored on repetition 1), 185-186 (O4, O5), 219-222 (reliability arm 'on a copy ... in the gated rhythm')
- evidence: Exploratory, habit_arm.py (seed 42, M = 1,000, 10 items, live rec):
- The global offset falls 2.6 mV over the 30 s of repetitions and 3.9 mV over the control copy's 39.7 s. The cued assembly's own offset rises only 0.5-1.5 mV.
- Repetition 1 passes both criteria for 8 of 10 items. Among those 8, the number of repetitions 91-100 that pass is 8, 2, 5, 6, 6, 4, 3 and 7, so 1 of 8 meets O4.
- Recovery passes for 5 of 8; on the control copy, with no repetition at all, for 6 of 8.
- Repetition 1 is identical on both copies for 10 of 10 items.

habit_settle.py, same 30 half cues before and after 40 s of background:
- seed 42, M = 500: offset 3.93 to 1.93 mV, C1 0.933 to 1.000;
- seed 43, M = 1,000: offset 7.62 to 3.73 mV, C1 0.767 to 1.000.

Consequences:
- A reliability copy without encodings would estimate per-item rates near 1.0 against about 0.75 online, and greatly overstate P(PASS).
- Selecting items on a single noisy repetition 1 adds regression to the mean to O4 and O5.
- Cost: about 5 s per copy at M = 1,000, so 200 copies take about 17 min per seed.
- recommendation: - Keep the input duty on every copy. Either continue the step rhythm with sham encodings (fresh random items at encoding and continuation rates, with plateaus, BTSP and feedback writes off), or continue real learning and accept the extra load.
- Predeclare a tolerance on the copy's offset relative to the main line.
- Give the control copy the same 100 presentations, using other items' half cues, so that its global drift matches.
- Define O4 and O5 per item, relative to the paired control, or report that figure alongside the absolute bar.
- Pin the reliability arm's rhythm explicitly.
- independent verifier: **confirmed** (severity should be major): Lines 162-163 say the habituation copies run with 'no settle, no learning'. habit_arm.py implements the draft's repeated and control copies faithfully: the same stream for repetition 1, 39.7 s of background on the control, live rec. Its output matches the finding: global offset -2.6 mV over the 30 s of repetitions and -3.85 to -3.9 mV over the control's 39.7 s, against an assembly offset rise of 0.5-1.47 mV; repetition 1 identical on 10 of 10; 8 items scored, with repetitions 91-100 passing 8, 2, 5, 6, 6, 4, 3, 7 (O4 met by 1 of 8); recovery 5 of 8 against control recovery 6 of 8. The control's recovery recall was >= 0.89 on every item, so its failures were content failures at the settled operating point, consistent with M1. So O4 and O5 are measured while the copy relaxes toward a settled state, and the control measures retest at near-settled offsets. That contradicts the draft's own argument (lines 29-31) that a long test block is itself a settle. The reliability arm (lines 219-221, 'in the gated rhythm') is ambiguous. Either it continues encodings, which raises the load past M over 600+ slots, or it drops them, which settles it (habit_settle: C1 rises to 1.0 at about 3.7 mV), so the Monte Carlo's per-item rates would be too high. Under either reading it does not reproduce the gated operating point at load M, so pinning it (for example with sham encodings that keep the duty but write nothing) is needed. The cost figure checks out: 101 s for 20 copies, so about 17 min for 200.

### M4 [major] The no-probe twin differs from the main line in almost no steps at M = 250 and 500

- where: Draft lines 127 (blocks are steps 11-250, 261-500 and 761-1,000), 155-158 (the twin blanks only rolling slots; its gated blocks hold the same probes), 248-249
- evidence: - Rolling slots, the only place the twin differs, are steps 1-10, 251-260 and 501-760.
- So the twin differs in 10 of 250 steps at M = 250, 20 of 500 at M = 500, and 280 of 1,000 at M = 1,000.
- At M = 250 and 500, the reported 'probe-caused interference' is null by construction.
- Mechanism note from M1 and M2: probe input raises vbar, which shrinks R(x). A twin with fewer probes may therefore show more interference, a sign the draft does not anticipate.
- recommendation: - Blank every slot in the twin, gated blocks included.
- Measure probe-caused interference on the stores (\|R(x)\|, R - A, Jaccard, feedback-store size) and through each line's settled readout and store swap. Alternatively, keep only the cohort slots in the twin.
- State the contrast, in steps, at each load, and predict its sign.
- independent verifier: **confirmed** (severity should be minor): The arithmetic is right. The blocks are steps 11-250, 261-500 and 761-1,000 (line 127), and the twin differs only in rolling slots (lines 155-158): steps 1-10, 251-260 and 501-760. That is 10, 20 and 280 differing steps up to M = 250, 500 and 1,000. Given B1, steps 1-10 can hold only novel cues anyway, so at M = 250 the twin differs by at most about 10 novel-versus-blank slots. Line 157-158's claim that the twin 'separates interference caused by earlier probes' is therefore null by construction at two of the three loads. The sign note (fewer probes, lower vbar, larger R(x)) is consistent with M1's data but untested. I downgrade it to minor because the arm is reported, not gated. The owner's requirement to separate retention from repeated-probe effects is carried by the never-probed cohort (O3), and at M = 1,000 there is a real 260-step contrast (501-760). The fix (state the contrast in steps per load, blank all slots or keep only cohort slots, measure on the stores) is cheap and should be made before freezing.

### m1 [minor] The replay check uses a fresh rec, which shares the replay's own reset assumption; a continuous check is feasible and was exact

- where: Draft lines 98-100 and 195 (validity: replay equals a fresh live rec)
- evidence: Exploratory, main_run.py.
- Replay against a fresh live rec attached after the settle: equal spike for spike at M = 250, 500 and 1,000 on seeds 42 and 43 (467,716-683,076 rec spikes each).
- This follows from the code: the float32 operations run in the same order; the replay's dirty and since_input shortcuts are exact at t_ref 2; feedback and inhibition land in different ring slots, so projection order does not matter.
- A rec run continuously from tick 0, through learning, the settle and the test, also matched exactly at M = 250 and 1,000 (seed 42).
- Its v at test start sat at two float32 values (-70.000122 and -69.999969), not at -70.0, so exactness is not guaranteed by construction.
- Gated numbers are continuous by design, so the impact is limited to the settled twin.
- recommendation: - Verify the replay against the twin's own continuous rec, kept attached and logged during run_phase. This needs no second copy.
- Keep the fresh-rec comparison as the arithmetic check.
- Predeclare what a non-exact match means: a reported mismatch count, not INVALID for a 1-ulp flip.
- independent verifier: **confirmed** (severity should be minor): Lines 98-100 and 195 verify the replay against a fresh live rec. readout.replay starts every arm at v_rest with an empty ring, and so does a fresh rec. Because P2-E3's tests already establish that the live engine and the replay are bit-identical from rest, this check effectively cannot fail. It also does not test the reset assumption that the owner's 'matches continuous simulation' ruling targets. The logs confirm the claims. The fresh rec equals the replay at all three loads on both seeds (467,716-683,076 spikes). The continuous rec, live from tick 0 through learning, settle and test, also matched exactly (M = 250 on seeds 42 and 43, M = 1,000 on seed 42). Its v at test start took two float32 values (-70.000122 and -69.999969) with an empty ring, so exactness is empirical, not guaranteed. One detail is loosely put: feedback from tick t+1 and inhibition from tick t do share ring slot (t+2) mod 3, but the accumulation order is the same in the engine and the replay, so the arithmetic stays exact. Recommendation: keep the twin's rec attached and compare against it, and predeclare that a non-exact match is a reported mismatch count, not INVALID for a 1-ulp flip.

### m2 [minor] The blank control skips the item encoded 50 ms before the slot (age 0); and in this architecture it cannot fail

- where: Draft lines 113, 137 and 181 (blank target ages 1-20), 146 (ages imply age = s - i), 250
- evidence: - With age = s - i, the item whose encoding just ended is age 0, and it is never a blank target or a recent probe.
- Exploratory, residual.py (main_run.py data, seeds 42 / 43, with age-0 blank targets oversampled): in every age-0 blank slot at M = 250, 500 and 1,000 (85 on seed 42, 89 on seed 43), the target assembly fired 0 spikes in the slot, with recall 0, 0 missing lines and no rec line within 75 ms.
- Ages 1-20 gave the same.
- The age-0 assembly fires 2-3 spikes on average in the pre-gap (maximum 18 at M = 250), all before the slot.
- The memory threshold sits 20 mV above vbar, with no recurrent excitation.
- recommendation: - Include age 0 in the blank targets and recent probes, and report it separately.
- Define age explicitly.
- Either add a reported positive control showing that O0 can detect persistence, for example blank scoring over the continuation's last 50 ms, or state that O0 is a sanity check that cannot fail here.
- independent verifier: **partly** (severity should be minor): The facts hold. Blank targets and recent probes are both ages 1-20 (lines 107, 113, 132, 137), so the item learned in the current step (age 0) is never a target. Its input, via the continuation, ends 50 ms before the slot; its encoding ends 100 ms before. residual.py on the saved logs gives 85 and 89 age-0 blank slots with 0 assembly spikes in the slot, 0 missing lines and 0 rec lines, and pre-gap age-0 assembly spikes averaging 2-3 (max 18). The 'cannot fail' claim is right by architecture: the memory layer has only inp-to-mem projections and no recurrence, and rec is driven only by memory. That matches the P2-E3 addendum item 8 concern about controls that cannot fail. The overstated part: no scored probe targets age 0, so excluding age 0 from the blank control leaves no gap in the causality claim for any gated probe. Adding age 0 is an extension, not a repair. Defining age explicitly and stating that O0 is a sanity check (or adding a positive control) are the useful parts.

### m3 [minor] rec is 2-4 mV below rest at probe onset (no floor on v), so the pre-gap argument holds for mem but not rec

- where: Draft lines 84-86 (a 50 ms pre-gap so activity 'has decayed'); 94-97 (rec live through encodings)
- evidence: Exploratory, online.py fields (seed 42; seed 43 within 0.1 mV):

| load | rec v at end of continuation (mean) | rec v at slot onset: mean (p5) |
|---|---|---|
| M = 250 | -109.8 mV | -73.9 (-74.1) mV |
| M = 500 | -102.1 mV | -73.1 (-73.7) mV |
| M = 1,000 | -89.8 mV | -72.0 (-73.3) mV |

- That is about one J_fb below rest at the first tick.
- J_fb was calibrated with rec at rest.
- It suppresses intrusions online, and is one reason online content (joint 0.94-0.96) exceeds the settled twin's (0.81-0.89).
- recommendation: - Report rec v at slot onset.
- Predict its direction: fewer intrusions, later regeneration.
- Name it as part of the online-versus-settled content difference.
- No parameter change.
- independent verifier: **partly** (severity should be minor): The numbers check out from the saved logs (residual.py). Mean rec v at the end of the continuation is -109.8, -102.1 and -89.8 mV, and at slot onset -73.9 (p5 -74.1), -73.1 (-73.7) and -72.0 (-73.3) mV, at M = 250, 500 and 1,000. LIF.step has no lower floor on v, and GlobalInhibition subtracts g*J_fb per memory spike. So the online content readout starts 2-4 mV (about 0.7-1.4 J_fb) below the at-rest initial condition that the replay and settled twin use. Reporting this is worthwhile, since it may be helping online D2. Overstated: the draft's pre-gap argument (lines 84-86) is about decay of input-driven activity, and that does hold for rec, which is silent. The memory layer is not at equilibrium either: its v - vbar at slot onset is about -2 to -3 mV at M = 1,000. The claim that rec hyperpolarisation is 'one reason' online content (0.94-0.96) exceeds settled content (0.81-0.89) is untested; the memory operating point (fewer memory spikes at high vbar, M1/M2) is at least as likely a driver. Report it, name it as a candidate, change no parameter.

### m4 [minor] O5's collateral clause covers almost no copies

- where: Draft lines 168-173 and 186 ('copies whose collateral item is itself scored')
- evidence: - If 'scored' means one of the 50 habituation items, the next item i+1 is among them with probability about 50 / M.
- That leaves about 2-5 qualifying copies per load, so a 90 % bar on them carries almost no information.
- In habit_arm.py the collateral cue often failed on the control copy too, on content.
- recommendation: - Score the collateral item's baseline from the control copy's collateral cue, as a paired comparison.
- Apply the bar to copies whose collateral passes on the control copy.
- Recompute power for the clause.
- independent verifier: **confirmed** (severity should be minor): 'Scored items' are defined (lines 172-173) as the habituation items that pass both criteria at repetition 1. So 'copies whose collateral item is itself scored' (line 186) requires item i+1 to be among the 50 drawn items. Expected qualifying copies are about 49/459 x 50, roughly 5, at M = 500 (cohort 1,000 is still reserved) and about 49/999 x 50, roughly 2.5, at M = 1,000, both before the repetition-1 pass filter. That leaves about 2-5 copies, where the 90 % bar means all must pass, and at M = 1,000 there is roughly a 10-15 % chance that no copy qualifies, leaving the clause undefined. habit_arm.py's control-copy collateral passed only 4 of 10, mostly failing on content. Two further edge cases the finding missed: at M = 500, i+1 can be a still-reserved cohort-1,000 item, which line 144-145 forbids even as habituation duty; and i = M has no learned next item. The recommended paired baseline from the control copy's collateral cue fixes all three.

### n1 [nit] Cost figures and per-slot digests; novel items have no stream

- where: Draft lines 192, 304-305 and 111
- evidence: - Speed falls with load: 0.078 s per 500 ms step at M = 250 (6.4 simulated s per wall s) against 0.195-0.208 s at M = 1,000 (about 2.4). Store upkeep (feedback add, csr and reload) dominates.
- Four sha256 digests at M = 1,000 take 0.085-0.16 s. Before and after 720 slots on two lines, that is several minutes per seed.
- P2-E1's e.novel holds only 200 items, but the draft needs at least 250 never-reused novel items.
- recommendation: - Detect writes with an O(1) check: BinarySynapses.add and toggle rebind keys, so test identity or a write counter per slot. Run full digests at block ends.
- Restate the cost estimate.
- Assign novel items a dedicated stream from ids 12-19.
- independent verifier: **confirmed** (severity should be nit): The logs show wall time per 500 ms step of 0.078 / 0.083 s at M = 250 (about 6 simulated s per wall s) against 0.195-0.212 s at M = 1,000 (about 2.4), so the draft's '6-10 s simulated per wall s' (line 304) holds only at low load. The attribution to store upkeep is plausible but was not separately timed. Four digests take 0.04-0.16 s; only the two store digests are needed per slot, so the per-slot cost is a few minutes per seed, not more. The O(1) write detection works: BinarySynapses.add and toggle rebind self.keys via np.insert, and add returns early without rebinding when nothing is new, so an identity check or write counter detects writes. Novel items needed to M = 1,000: 70 rolling (25 % of 280 steps) plus 180 gated, so 250, against e.novel's 200. The draft only says 'fresh random item' (line 111) and assigns no stream from ids 12-19 to novel items. The total gated cost estimate of 25 min is roughly plausible once habituation (about 17 min) is counted; the reported arms, especially M = 3,000 and the I = 2,000 duty arm (271 s to M = 1,000 without rec), will cost more than stated.

## Exploratory runs (labelled; not results)

- `~/.cache/brain-sim/review/p2e4-redteam/implementation/schedule_feasibility.py` (seed none (arithmetic); draft schedule rules: pool 1-120, 3 cohorts x 40, blocks of 240 steps ending at 250 / 500 / 1,000): - M = 250: non-reserved items only from step 122, so 129 usable steps for 180 non-novel slots, and 111 slots only novel cues can fill.
- M = 500 and 1,000 are feasible.
- `~/.cache/brain-sim/review/p2e4-redteam/implementation/smoke.py (and online.py)` (seed 42; SMALL: m = n = 800, a = 40, f_q 0.03, acc_tau 300; 60 online steps, no quiet()): - Forward store equal to P2-E1 and P2-E3.
- A(x) and E(x) are identical.
- The feedback store differs (38,385 against 37,610).
- `~/.cache/brain-sim/review/p2e4-redteam/implementation/timing.py` (seed 43; full contract config, 40 steps): - Online with live rec: 10.4 simulated s per wall s; 12.7 without rec.
- Forward store equal to P2-E3.
- `~/.cache/brain-sim/review/p2e4-redteam/implementation/main_run.py 42 (and residual.py)` (seed 42; - Full contract config (e3.CONTRACT, J_fb 2.80, g 0.3), I = 250 ms (50 / 100 / 100), live rec reloaded after each write.
- Probe mix: recent 25 %, uniform 25 %, novel 15 %, blank 25 % (half of them age 0), full 10 %.
- Settled twins at 250 / 500 / 1,000.): Online C1, recent / uniform:
- M = 250: 1.0 / 0.957;
- M = 500: 0.964 / 0.938;
- M = 1,000: 0.765 / 0.761.

Online content joint 1.0 / 1.0 / 0.935-0.956. Blank slots: all 0. Threshold offset at step 1,000: 7.7 mV.

Settled twins (C1, joint): 0.98 and 1.0; 0.97 and 0.995; 0.97 and 0.81.

Replay equals the fresh live rec at every load. The continuous rec equals the replay at M = 250. Forward store equals P2-E1. Deep copy takes about 0.1 s.
- `~/.cache/brain-sim/review/p2e4-redteam/implementation/main_run.py 43` (seed 43; as for seed 42): Online C1, recent / uniform:
- M = 250: 1.0 / 0.924;
- M = 500: 0.955 / 0.889;
- M = 1,000: 0.803 / 0.700.

Online joint at M = 1,000: 0.94-0.955. Blank slots: all 0.

Settled twins (C1, joint): 0.965 and 1.0; 0.965 and 0.995; 0.925 and 0.89. Replay equals the fresh live rec at every load.
- `~/.cache/brain-sim/review/p2e4-redteam/implementation/main_run.py 42 1000` (seed 42; as above, first load 1,000: P2-E1 check, fresh and continuous rec): - Results reproduce the first seed-42 run exactly.
- The continuous rec, live from tick 0, equals the replay spike for spike at M = 1,000 (683,076 spikes).
- rec v at test start took 2 float32 values near -70.
- `~/.cache/brain-sim/review/p2e4-redteam/implementation/diag_fb.py` (seed 42, 43; full config, M = 1,000: P2-E3 protocol line against the online line; settled tests; store swap): Seed 42 / 43, items 751-1,000:
- \|R\|: 28.7 / 28.5 (P2-E3 protocol) against 45.2 / 44.7 (online);
- Jaccard: 0.73 against 0.49 / 0.50;
- continuation offset: 8.47 against 6.85 mV;
- feedback store: 2.12 M against 2.50 M.

Settled joint:
- P2-E3 protocol: 0.98 / 0.99;
- online, own store: 0.81 / 0.89;
- online raster, P2-E3-protocol store: 0.98 / 0.99;
- online raster, plateau-set store: 0.995 / 0.995.
- `~/.cache/brain-sim/review/p2e4-redteam/implementation/duty.py` (seed 42; full config, I = 2,000 ms (post-gap 1,850 ms), no live rec, M = 1,000, then settled twin): - Online memory C1: 0.956 recent, 0.978 uniform.
- \|R\| 133 and Jaccard 0.18 in items 751-1,000.
- Continuation offset 4.08 mV; feedback store 3.99 M.
- Settled joint 0.165 (D2 0.17).
- `~/.cache/brain-sim/review/p2e4-redteam/implementation/habit_settle.py` (seed 42 (M = 500), 43 (M = 1,000); full config, online state, same 30 half cues before and after 40 s of background; one habituation copy, timed): - Seed 42, M = 500: offset 3.93 to 1.93 mV; C1 0.933 to 1.000.
- Seed 43, M = 1,000: offset 7.62 to 3.73 mV; C1 0.767 to 1.000; both criteria 0.733 to 0.70.
- One copy takes 4.3-7.5 s of wall time.
- `~/.cache/brain-sim/review/p2e4-redteam/implementation/habit_arm.py` (seed 42; full config, M = 1,000, 10 items, the draft's repeated and control copies, live rec): - Repetition 1 identical on both copies for 10 of 10; 8 of 10 items scored.
- O4 met by 1 of 8 (repetitions 91-100 passing: 8, 2, 5, 6, 6, 4, 3, 7).
- Recovery 5 of 8; control-copy recovery 6 of 8.
- Global offset -2.6 mV over 30 s and -3.9 mV over 39.7 s; assembly offset +0.5 to +1.5 mV.
- 101 s wall for 20 copies.

## Reviewer's predictions

For the draft run as written, once B1 is fixed so that it can run at all. Basis: seeds 42 and 43, exploratory only.

- **O0: holds** on every seed and load. 0 target spikes and 0 regenerated lines in every blank slot, including age 0. There is no persistence mechanism: the threshold is 20 mV above vbar, there is no recurrence, and the pre-gap is 50 ms.
- **O1: FAILS** at M = 1,000 on essentially every seed. Online C1 is 0.70-0.80 for both recent and uniform cues, from a threshold offset of about 7.7 mV under the 50 % encoding duty. It is at risk at M = 500 (uniform 0.889-0.938) and passes at M = 250 (0.92-1.0). C2 and C3 hold (1.0).
- **O2: borderline.** The online joint is 0.935-0.956 at M = 1,000 and >= 0.97 at M <= 500, so holding on 5 of 5 seeds at M = 1,000 is roughly a coin flip. D3 holds (1.0). The online figure is helped by the high probe-time offset and by rec starting about 3 mV below rest. The online-written store itself is degraded: the settled-twin joint is 0.81-0.89, and the reported 'online cost' for content will come out negative.
- **O3: FAILS** at M = 1,000. Memory C1 for items aged >= 281 is 0.70-0.80. It is likely to fail at M = 500 as well (0.86-0.89 for ages >= 150). The content part is about 0.93-0.94 at M = 1,000.
- **O4: FAILS.** At M = 1,000, 1 of 8 scored items met the bar, though the result is confounded by a 2.6 mV global settle during the arm.
- **O5: FAILS.** Recovery 5 of 8; even the no-repetition control reached only 6 of 8.

Expected verdict: **ONLINE FAIL**, not the draft's HABITUATION FAIL. P(PASS) is near 0.

Reported arms:
- **Duty arm (I = 2,000 ms):** memory passes (C1 about 0.96-0.98), but the content store collapses (settled joint about 0.17).
- **No-probe twin, as drafted:** about equal to the main line at 250 and 500.
