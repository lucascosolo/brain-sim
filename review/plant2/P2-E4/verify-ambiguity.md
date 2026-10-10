# P2-E4 contract verification: ambiguity

Fresh checker given only the files (revised contract at commit b1ec05a). Run 2026-10-10. Recorded verbatim, before synthesis.

## Verdict

The contract cannot be frozen as written. It has one blocker: the positive control in validity check 9 fails by construction under its most literal reading. Under the "mean of both parts" reading it sits exactly on its 0.5 bar (exploration on seed 42). Whether a seed is labelled INVALID therefore depends on a reading the contract does not state. Beyond that, the driver can be written, but the implementer must make about a dozen choices. Six of them can move a gated number or label and are not fixed by the text:
- where the score windows start relative to slot onset;
- which mean |A| C3 uses, and whether novel cues are half cues;
- the leak statistic and its novel-slot baseline;
- how the collateral item is chosen (metric, ties, candidate set, overlap with the control's 89 cues);
- what "unreserved" means after a cohort's block;
- the schedule sampler: as written it cannot satisfy the no-repeat rule.

P2-E1's recall, spurious and ignition measures carry over to single online probes once onset and mean |A| are pinned. Sham encodings hold vbar, but the live rec sits 1.5-3 mV nearer rest at slot onset than on the main line. In an n = 60 check at M = 1,000 this made no measurable difference to "both", so it is minor. Nothing is infeasible at m = n = 4,000. The gated estimate (about 35 min) is plausible; the reported arms cost about 2x the stated 20 min.

## Findings

### PC-1 [blocker] Validity 9's positive control cannot pass its content part, and the 'mean' reading sits exactly on the 0.5 bar

- where: docs/plant2/P2-E4-online-memory.md lines 280-288; plant2/experiments/p2_e3_completion.py:76-82 (feedback written after the continuation)
- evidence: Contract: 'the positive control: the same measure over the last 50 ms of the age-0 item's own continuation ... the positive-control mean is >= 0.5'. The measure has two parts: the share of the assembly active within 50 ms, and the share of 'designated missing lines regenerated within 75 ms'. Item k's feedback is written only after its 50 continuation ticks, and the live projection is reloaded 'right after each write'. So during its own continuation no rec line can be driven by item k's own synapses. Exploratory run (posctl.py, seed 42, online timeline with live rec, J_fb 2.80, g 0.3, interval 50/100/100):
- the assembly part is 1.000 in every step of both blocks (0 of 480 steps below 1);
- the missing-line part is 0.0000 over steps 261-500 and 0.014 over steps 761-1,000 (0.0001 and 0.017 if the 75 ms window runs 25 ms into the pre-gap).
How each reading comes out:
- **Each part >= 0.5:** INVALID on every seed, by construction.
- **Mean of the two parts:** 0.5000 at M = 500, passing only by exact float equality.
- **Assembly part only:** passes.
The contract also leaves open which steps are averaged (all 240 steps, or the 20 blank-slot steps).
- fix: Replace with: 'Positive control, two parts, each must hold:
(a) memory: over the block's 20 blank-slot steps, the mean fraction of that step's age-0 item's assembly A with >= 1 spike in its 50 ms continuation is >= 0.5;
(b) content: over the block's 50 recent half-cue slots, the mean fraction of the target's 50 missing lines with >= 1 rec spike at slot ticks k = 0..74 is >= 0.5.
The continuation cannot serve as a content control, because an item's feedback is written after it.' Alternatively, drop the content part and say why.

### COLL-1 [major] The collateral item is underdetermined (metric, ties, candidates), and the control copy may already have cued it

- where: lines 198 and 203-205; O5 collateral at line 247
- evidence: Text: 'the unreserved stored item (outside the 50) whose assembly A overlaps the repeated item's assembly most, with ties going to the lowest index'. Arithmetic on random plateau sets (collateral_ties.py, numpy seeds 90-99), M = 500 / 1,000:
- the maximum overlap is a median of 2 cells (out of about 20);
- the maximum is tied for 63 % / 77 % of items;
- count overlap and Jaccard pick different items 46 % / 54 % of the time;
- breaking ties by lowest index makes the collateral older than the pool (median age 271 against 170; 672 against 420).
The age range is not restricted (ages 0-20 allowed?), and 'unreserved' after a cohort's block is undefined. The control copy's 89 other items need not exclude x's collateral: P(it is among them) is about 0.31 / 0.11. In those cases the control copy has cued the collateral before steps 122-126 and the repeated copy has not, which breaks the pairing O5 relies on. These are gated choices that exploration could steer: older collaterals mean fewer eligible items, and fewer than 25 makes O5 fail.
- fix: 'The candidate set C for item x is the stored items in neither cohort, of age >= 21, not among the 50. The collateral maximises |A(x) ∩ A(y)| (cells), with ties broken uniformly by stream 16, not by index. The control copy's 89 other items are drawn from C minus x's collateral. The overlap of every collateral is reported.' Also state that with a median overlap of 2 cells, the collateral cue tests little spread to overlapping assemblies.

### WIN-1 [minor] The score windows are never anchored to the slot

- where: lines 84-95, 206, 243-245, 280-281
- evidence: The contract gives only '(50 ms)' and '(75 ms)'. P2-E1's present()/responders count k from the first tick with cue rates (p2_e1_btsp.py:108-117, 129-131: first spike < 50). P2-E3 defines k = 0..74 from that tick. The earliest cue-caused memory spike is at k = 1, and rec at k = 2. Open choices: k = 0..49, a causal 1..50, the whole 100 ms slot, and what onset means for blank slots, which have no cue rates. A later or longer window raises online C1, which exploration puts near the bar.
- fix: 'Every score window starts at slot tick k = 0, the first tick of the 100 ms slot, when the slot's rates are set (blank slots included). Memory responders R50 are the cells with >= 1 spike at k = 0..49. Regenerated rec lines are those with >= 1 spike at k = 0..74. This follows P2-E1 present() and P2-E3's Window, unchanged.'

### C3-1 [minor] How P2-E1's C1-C3 carry over to single probes: mean |A| for C3, and the form of a novel cue

- where: line 243 (C3), lines 159, 171 and 244 (novel cues); p2_e1_btsp.py:199-208
- evidence: Recall and spurious carry over unchanged: recall = |A ∩ R50| / |A|, which is 0 when A is empty (p2_e1_btsp.py:167), and spurious = |R50 \ A| < 0.5|A|. Ignition uses mean_A = the mean over all of e.A at evaluate time, with a strict bar. Online, the learned set grows across the 240-step block. Because ignition is an integer, the bar moves from 'at most 9' to 'at most 10' as mean |A| crosses 20.0 (P2-E3's gated mean |A| was 19.83-20.20). The contract also never says that a novel cue is a half cue: P2-E1 and P2-E3 use 50-line half cues of 100-line items (p2_e1_btsp.py:141, 150). A full novel item doubles the drive (raising ignition and D3) and changes the input duty, both on the main line and on the novel-duty twin.
- fix: 'C1-C3 are P2-E1's per-cue measures applied to one slot. Ignition = |R50| < 0.5 mean|A|, where mean|A| is the mean plateau-set size over items 1..M of the gated load (one value per block). A novel cue is the 50-line half cue (mask drawn with the item) of a fresh 100-line item: stream 17 on the main line, stream 18 on the novel-duty twin.'

### LEAK-1 [minor] The leak statistic and its novel-slot baseline are undefined

- where: lines 279-288
- evidence: Open points:
- 'Designated missing lines' of an uncued blank target: no mask source is given.
- 'The leak statistic' is either one number (the mean of two fractions) or two.
- 'The same-block novel-slot baseline' has no target assembly: a novel item has none. One plausible reading, ignition / mean|A|, gives about 0.1-0.5 and would make the check vacuous.
The exploratory values are 0 either way. For blank targets, and for pseudo-targets drawn by the blank rule in novel slots, both fractions were 0.000 (seed 42: 24 blank and 57 novel slots at steps 261-500; 40 and 54 at steps 761-1,000). But this is a gated INVALID check.
- fix: 'L_A = the mean over the 20 blank slots of |A_t ∩ R50| / |A_t|. L_C = the mean of |miss_t ∩ rec75| / 50, where miss_t is the 50 lines outside a mask drawn for target t at seed start (stream 15). Each of the block's 30 novel slots gets a pseudo-target, drawn at seed start by the blank-target rule; the baselines B_A and B_C are the same means over those slots. Pass: L_A <= B_A + 0.05 and L_C <= B_C + 0.05.'

### SCHED-1 [minor] Followed literally, the schedule redraw rule never finishes; the full-cue target rule is missing

- where: lines 152-161, 163-182
- evidence: Arithmetic (schedule_collisions.py, seeds 90-99): drawing block targets i.i.d. per slot gives 16-22 within-block repeats at M = 500 and 8-13 at M = 1,000. P(no repeat) is at most 1e-4, so 'redraws with stream (seed, 15, attempt)' applied to the whole schedule needs about 10^4 to more than 10^9 attempts. A per-slot sampler without replacement works, but it skews recent ages (mean 9.46 instead of 10; share at age 0 0.055, at age 20 0.041). Also unstated:
- the target rule for 'full' cues (block and rolling);
- whether blank targets count toward the no-repeat rule;
- the rolling fallbacks at steps 162-181, where the uniform kind has no item of age >= 21 and some recent/blank ages point at reserved items.
- fix: 'The builder fills slots in step order. Each targeted slot draws uniformly from its kind's eligible set, minus every item already targeted (cued or blank) in the block:
- recent and blank: unreserved items of age 0-20;
- uniform: unreserved items of age >= 21;
- full: unreserved stored items of any age.
An attempt fails only when an eligible set is empty. A rolling kind whose eligible set is empty becomes a novel cue. Rolling kinds are drawn i.i.d. per step from stream 14.'

### RES-1 [minor] 'Unreserved' is undefined after a cohort's block

- where: lines 144-145, 157, 169, 186, 198, 203
- evidence: The rule bars probes only 'before its own block'. If cohort-500 items become unreserved after step 500:
- they join block 1,000's gated uniform candidates (about 80 of 900, roughly 9 %, all aged 500 or more);
- they join the control copy's 89 others and the collateral pool;
- rolling uniform slots in steps 501-760 probe them as well as the oldest-probed slots, which changes the probed against never-probed contrast.
- fix: 'Unreserved means in neither cohort, at every step. After its block, a cohort-500 item is cued only in oldest-probed rolling slots; a cohort-1,000 item only in block 1,000.'

### ORDER-1 [minor] The order of runs on one seed conflicts with the record-order rule

- where: line 442 against lines 219-228, 269-271
- evidence: 'The gated record per seed is written before any reported arm runs.' But twins A and B (reported) branch 'after step M' at M = 500, before the gated block 761-1,000. The implementer must either run them mid-timeline, which breaks line 442 and makes validity check 6 load-bearing for gated numbers, or hold a snapshot. Neither is stated.
- fix: 'Per seed:
1. Run the main line to step 500 and keep S500 (a deep copy); run the M = 500 habituation arm from S500.
2. Run the main line to step 1,000 and keep S1000; run the habituation arm from S1000; run the P2-E1 forward-store check.
3. Append kill_test_seed.
4. Run the reported arms from S500 and S1000 (twins A and B, writes-during-probes, out-of-distribution); then main line steps 1,001-3,000; then the reference line, the novel-duty twin and the duty arm, each from step 1.
Validity check 6 is gated for steps 1-2.' A snapshot at M = 1,000 is about 0.1-0.2 GB.

### SHAM-1 [minor] Sham encodings hold vbar but not the rec state at slot onset; the sham's streams are unpinned

- where: lines 188-194
- evidence: Lines 188-190 claim the shams 'hold the input duty and the operating point'. A real continuation fires the memory responders and drives rec far below rest; a sham does not. Exploratory (sham_check.py, seed 43, M = 500):
- rec v at slot onset is -70.07 mV on the sham copy against -72.89 mV on the main line;
- 3.7 against 25.2 memory cells fire in the continuation window;
- the vbar offset goes 3.92 -> 4.04 against 3.91 -> 4.26 mV over 40 steps.
At M = 1,000 (sham_content.py, seed 43, 60 old half cues with identical cues and draws), rec onset is -70.04 mV on the sham copy against -71.55 mV on a copy that continues real learning. 'Both' was 0.567 on both copies (2 against 2 discordant), so no measurable effect on the gated statistic at n = 60. Also unstated: which generator supplies the sham's and the copies' input spikes, and whether the pattern differs per item.
- fix: Reword: 'Sham encodings hold the input duty and the memory layer's vbar. They do not reproduce the post-write memory burst, so rec on the copies sits about 1.5-3 mV nearer rest at slot onset. Reported per copy: rec v at slot onset and the vbar offset, against the main line's last 20 steps.' Pin: 'Every input draw of copy step s (sham encoding, sham continuation, gaps, slot) comes from stream (seed, 16, M, item, s), shared by both copies; the sham pattern is the first draw of that generator.'

### HAB-1 [minor] Habituation-arm details left open

- where: lines 185-217, 247, 276
- evidence: Not stated:
- the structure of a copy step;
- which mask the control copy uses at step 1, at steps 91-100 and for the recovery cues; and whether the repeated item's fixed mask is fresh from stream 16 or the block mask from stream 15;
- the age range of the 89 other items;
- what validity check 8 compares for 'repetition 1 is identical';
- whether O5's populations are all 50 items or only scored items. plant2/power.py p_paired_majority assumes all 50; the draft's version used scored items.
- fix: 'Copy step s is: sham encoding 200 ms, sham continuation 50 ms, pre-gap 50 ms, slot 100 ms, post-gap 100 ms. Item x uses one mask from stream 16 for every cue of x on both copies (steps 1-100 and 91-100, recovery). The 89 others are of age >= 21, drawn from C minus x's collateral. Validity check 8: the memory and rec spike rasters of copy step 1 are equal on both copies. O5 recovery and collateral are taken over all 50 items.'

### TWINB-1 [minor] Twin B's rhythm, streams and content source are not pinned

- where: lines 225-228; p2_e3_completion.py:88-106, 182-188
- evidence: Not stated:
- whether 'P2-E3's cue rhythm' includes P2-E3's 200 ms lead-in;
- which settle stream and phase twin B uses: P2-E3 uses (seed, 5, M, 100 + phase), and if twin B uses phase 1 its settle is identical to twin A's;
- which cue-input stream it uses: P2-E3 uses (seed, 5, M, phase), while the contract assigns stream 18 to twins;
- whether content is scored from the carried rec or from the replay.
The arm is reported, but it is the only online-against-settled comparison.
- fix: 'Twin B: settle_drift(M, phase = 1), the same as twin A's, so B may branch from A after the settle. Then a 200 ms lead-in, then the 180 half cues in block order, 100 ms on and 200 ms off, cue input from (seed, 18, M, 2). Memory is scored as in P2-E1; content from the carried live rec at k = 0..74.'

### RET-1 [minor] No probed-cohort reading exists 'at M = 1,000'

- where: line 384, against lines 152-158 and 163-173
- evidence: 'Probed (cohort 500, via oldest-probed slots) against never-probed (cohort 1,000) retention at M = 1,000.' Oldest-probed slots exist only in rolling steps 501-760 and after step 1,000, and block 1,000 holds no cohort-500 cue. So nothing measures probed retention at M = 1,000, and an implementer must choose the window after the fact.
- fix: 'Probed retention is read from cohort-500 items in oldest-probed rolling slots of steps 1,001-1,260, against block 1,000's cohort cues. Ages and loads are reported for both.'

### WPS-1 [minor] Writes-during-probes arm: plateau and coin streams, slot schedule and the timing of the 'stored' test are open

- where: line 390
- evidence: If probe-slot plateaus and BTSP coins draw from P2-E1's _plat and _coin, items 1,001-1,200 on the copy get different A(x) than on the main line. That confounds the 'matched items (M = 1,200)' comparison. Also unstated: when the 'later presentation' happens, and which schedule fills the copy's 200 slots.
- fix: 'Probe plateaus and coins come from (seed, 18, 3, k). Item learning on the copy keeps _pat, _plat and _coin. Slots follow the main line's rolling schedule for steps 1,001-1,200. After step 1,200, each written probe is re-presented once, in write order, at the online rhythm with sham encodings.'

### STREAM-1 [nit] Stream ids are given without keys or draw order

- where: lines 113-124, 178-181
- evidence: Not stated:
- whether streams 12 and 13 are keyed per step or run as continuous generators;
- where rolling probes' masks come from (14 or 15);
- the draw order within 15 (cohort split, orders, targets, masks, blank designations);
- that 17 is shared by rolling and block novel items;
- that 18 is shared by several arms.
The guard pins the code before gated runs, so this does not steer outcomes. It is needed for the claims of 'identical' repetition 1 and a novel-duty twin that is 'identical except'.
- fix: List the keys:
- background (seed, 12, k); slot input (seed, 13, k); rolling (seed, 14, k);
- block builder (seed, 15, purpose, M, attempt); habituation (seed, 16, M, item, s);
- novel items (seed, 17, k); twins and arms (seed, 18, arm, ...).

### COST-1 [nit] The cost of the reported arms is understated; nothing is infeasible

- where: lines 443-445
- evidence: Measured:
- main line with live rec: 0.055 / 0.105 / 0.194 s per step at M = 100 / 500 / 1,000 (posctl.py);
- a sham copy step: 0.053 s at M = 500 and 0.067 s at M = 1,000. So 100 copies x 126 steps take about 11 + 14 min, consistent with '35 min gated';
- store upkeep at 10 M feedback keys: add 68 ms, csr plus reload 57 ms (upkeep_bench.py).
Estimated for the reported arms:
- main line 1,001-3,000: at least 2,000 x 0.2-0.4 s, so 7-13 min or more;
- duty arm: about 2 M ticks (271 s without rec in the red-team's run);
- novel-duty twin, reference line, 4 settled twins with replays, writes-during-probes and out-of-distribution: about 15-25 min;
- total about 35-50 min per seed against the stated 20.
- fix: Restate as 'about 35 min gated plus 35-50 min reported per seed'.

### NIT-1 [nit] Stale 'O0' in the power text

- where: line 360
- evidence: 'For O0-O3 it uses a binomial on the mean rates', but O0 is now validity check 9 and no longer a criterion.
- fix: Read 'For O1-O3'.

## Computed (exploratory; not results)

All scripts and outputs are in /root/.cache/brain-sim/review/p2e4-verify/implementation_ambiguity/. The repo is untouched. Runs used seeds 42 and 43 and numpy seeds 90-99 and 93.

- **posctl.py, seed 42** (output posctl42.out, posctl_seed42.json). Online timeline to M = 1,000 with live rec (J_fb 2.80, g 0.3), interval 50/100/100, rough probe mix (60 % recent, 25 % novel, 15 % blank).
  - Positive-control assembly part 1.000, with 0 of 480 block steps below 1.
  - Missing-line part 0.0000 over steps 261-500 and 0.014 over steps 761-1,000 (0.0001 and 0.017 with 25 ms of pre-gap).
  - Mean of the two parts 0.5000 and 0.507.
  - Blank-slot and pseudo-target novel-slot leak fractions all 0.000.
  - rec v at slot onset -73.13 and -72.04 mV; vbar offset 2.98 and 6.83 mV; |R| 22.0 and 45.3.
  - Recent C1 0.899 and 0.767; wall time 0.055-0.194 s per step.
- **sham_check.py 43 500** (sham_check43_500.out). rec v at slot onset: sham copy -70.07, main line -72.89 mV. Continuation-window memory cells 3.7 against 25.2. Offset 3.92 -> 4.04 against 3.91 -> 4.26 mV. Sham step 0.053 s.
- **sham_content.py 43 1000** (sham_content43_1000.out). 60 old half cues with identical cues and draws:
  - real-learning copy: both 0.567, rec onset -71.55 mV;
  - sham copy: both 0.567, rec onset -70.04 mV;
  - sham with a stored-item continuation: both 0.533, rec onset -71.29 mV;
  - paired real against sham: 2 / 2 discordant.
- **schedule_collisions.py** (schedule_collisions.out). i.i.d. block draws give 16.3-22.1 repeats per block at M = 500 and 8.1-12.7 at M = 1,000; P(no repeat) at most 1e-4. Per-slot rejection gives a recent-age mean of 9.46.
- **collateral_ties.py** (collateral_ties.out). Maximum overlap a median of 2 cells. Tied at the maximum for 63 % / 77 % of items; count and Jaccard picks differ 46 % / 54 %. Chosen collateral median age 271 against 170 at M = 500 and 672 against 420 at M = 1,000. P(collateral among the 89 others) about 0.31 / 0.11.
- **upkeep_bench.py** (upkeep_bench.out). At 2.5 / 6 / 10 M keys: add 46 / 47 / 68 ms, csr plus reload 15 / 36 / 57 ms, delivery of 10 spikes per tick 0.17 / 0.39 / 0.56 ms per tick.
- **plant2.power.p2e4_reference()** reproduces the contract: O1-O3 all P = 0.830, and at M = 1,000 O1 0.914 and O3 0.912.
