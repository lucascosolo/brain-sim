# Offline screens F and E′: the graded error signal, the leak counterfactuals and the write-time coverage of the residual (2026-10-22)

Contract for two zero-seed analyses on the persisted P2-E7 seed-121 evidence, selected at
roadmap checkpoint 2 (`docs/research/ROADMAP.md`; `DECISIONS.md` entry of the same day).
No simulation of a network, no seed, no frozen driver edited; nothing here is a capability
or a gate. Every output is labelled **offline, development seed 121**; screen F's
counterfactuals are additionally **proxy** (computed on the binary candidate's persisted
trajectory, not on a graded trajectory). The commit that adds this file freezes it; results
are appended below after the run. Same discipline, records and module as screens A-E
(`docs/plant2/OFFLINE-SCREENS-20261022.md`, `-20261022b.md`).

Purpose: screen F is the kill-only screen for the graded prediction-error rule (B-016, the
P2-E8 candidate) that the checkpoint selected conditionally; it can kill the rule before any
seed is spent and cannot clear it. Screen E′ re-bins screen E's late class by the write-time
coverage of the same-family items each spurious cell holds, which separates a ramp leak from
a steady-state leak. Screen F also appends the one-line record that closes B-017.

## Inputs (read-only, verified against their recorded descriptors before use)

For the F10 arms `candidate`, `gate_off` and `no_conservation`, and for the `independent`
candidate, of attempt `seed121-1792699741870086415-c573e46d`: the learned state NPZ
`F10-<arm>-M1000-state.npz` (per-episode ragged `E`, `R`, `A`, `items`; the 75-tick
encoding rasters `enc_tick` / `enc_cell` ragged by episode; `feedback_keys`; `H`;
`metadata_json` holding `gate_log` with per-episode `E_size`, `G_size`, `V_size`,
`applied_V_size`, `p`, `p_capped`, `proto_predicted`, `nonproto_predicted`,
`veto_proto_fraction`), whose descriptor is recorded in the arm's `load` record; screen E's
per-cue artifacts (`bench/results/offline-screens-20261022/E-seed121-<arm>-M1000.json`);
the F10 generator regenerated as `FamilyGen(121, 4000, 100, 60, 10)` for prototype
membership, read at scoring only (exemplar index k + 1, family (k + 1) mod 10, P_k = item_k ∩
protos[(k + 1) mod 10], 40 lines, checked).

## Screen F: subthreshold drive, counterfactual flips, the ramp

For the `candidate` and `gate_off` arms, episode by episode k = 0..999:

1. **Feedback store before the episode.** S_k = ∪_{i<k} R_i × E_i as a CSR by memory cell
   (the frozen store's add-only union); S_1000 must equal the persisted `feedback_keys`
   exactly (integrity gate; INVALID for the arm otherwise).
2. **Lockstep reconstruction readout.** The persisted encoding raster of episode k (ticks
   0-74) is played through a reconstruction LIF population bit-identical to
   `plant2.readout.replay` under the frozen constants (tau_m 20, v_rest −70, v_th −50,
   v_reset −65, t_ref 2, float32; J_fb 2.80 at delay 1 from S_k; global inhibition
   g·J_fb = 0.84 mV per memory spike at delay 2; rec at rest at tick 0). A unit test proves
   the lockstep spike set equals `replay`'s trace on a small raster and store. **Integrity
   gate:** on every episode the lockstep spike set G must satisfy |G| = `gate_log.G_size` and
   |G ∩ E_k| = `gate_log.V_size`; any mismatch makes the arm INVALID.
3. **Drive.** For each eligible line j ∈ E_k, d_j = max over ticks 0-74 of (v_j − v_rest),
   read after input integration and before any threshold reset (a line that spikes has
   d_j ≥ 20 mV by construction and is in G).
4. **Separation.** Per block of 100 episodes and over episodes 501-1,000: the AUC of d_j for
   missed prototype lines (P_k ∩ E_k \ G) against unpredicted non-prototype lines
   (E_k \ P_k \ G), pooled over the episodes of the window (ties count one half); the counts
   of both classes; the fraction of missed prototype lines with d_j ≥ 10 mV.
5. **Counterfactual expected flips per plateau cell**, on the same trajectory, for three
   rules applied to episode k's E_k, G and d (none of which changes the trajectory):
   - binary (P2-E7): p = min(1, 0.5·|E|/|E′|) on E′ = E \ G, 0 on G;
   - graded: w_j = 0 on G, else w_j = 1 − clip(d_j / 20, 0, 1); p_j = min(1, λ·w_j) with λ the
     exact water-filling solution of Σ_{j∈E} p_j = 0.5·|E| (sorted, no tolerance), p = 1 on
     every positive-w line when fewer than 0.5·|E| lines have w > 0 (flagged capped);
   - surplus-only: p_j = 0.5 on E′ plus the vetoed surplus 0.5·|G ∩ E| distributed over E′ in
     proportion to w_j, capped at 1 with the remainder redistributed by the same rule until
     the cap binds or the surplus is spent (flagged when it cannot be spent).
   Reported per rule, per block and over 501-1,000 and 1-300: the mean over episodes of
   Σ_{j∈P∩E} p_j (expected prototype flips per plateau cell) and Σ_{j∈E\P} p_j; the ratio
   graded/binary and surplus/binary of the prototype expectation; the total-variation
   distance of each rule's p vector from the uniform 0.5 vector, averaged over episodes.
6. **The ramp.** The same quantities on `gate_off` (the baseline trajectory with its own
   gate) over episodes 1-300, by block.
7. **Independent perturbation.** On the `independent` candidate's persisted rasters and
   state: the graded rule's mean total-variation distance from 0.5 over all episodes, and the
   fraction of episodes with any p_j < 0.49 (report only).
8. **B-017's line.** From `gate_off`'s gate_log, the mean prototype coverage
   (`proto_predicted`) over episodes 101-500, set beside the twin-store proposal's own kill
   value 0.595 (report only; closes B-017).

**Kill reading for P2-E8 (recorded, decides whether the P2-E8 contract is drafted):** killed
if the AUC over episodes 501-1,000 on the candidate is below 0.70; or the graded/binary
prototype-flip ratio over 501-1,000 is above 0.6; or both the ratio over episodes 1-300 on
gate_off is above 0.85 and screen E′ places more than half of the late class in the
low-coverage bin. Otherwise "survives", which authorises drafting the contract and nothing
else.

## Screen E′: write-time coverage of the residual

For the `candidate` arm, from screen E's per-cue artifact (the classification of each
spurious cell) and the gate_log: for each spurious cell in the late class, the write-time
coverage of each same-family plateau item it holds is that episode's `proto_predicted`
(the fraction of the item's eligible prototype lines the prediction covered); the cell is
binned by the minimum coverage over its same-family items into < 0.25, 0.25-0.75, ≥ 0.75.
Reported: the late class split by bin (mean per cue and share), the same split weighted by
the number of same-family items held, and the distribution of `p` on those episodes.
Reading: a late class concentrated in the ≥ 0.75 bin is a steady-state leak (the graded
rule's target); one concentrated below 0.25 is a ramp leak (onset, which a graded signal
may or may not reach).

## Outputs, records and discipline

Implemented as screens `F` and `Eprime` in `analysis/offline_screens_20261022.py`
(functions `lockstep_rec(raster75, csr, m) -> (spikes, dmax)`, `water_fill(w, budget)`,
`counterfactual_p(E, G, d, rule)`, `auc(positives, negatives)`, `rebuild_feedback_csr`,
`screen_f(...)`, `screen_eprime(...)`; `run --screen F` and `run --screen Eprime`), records
of kind `offline_screen` with `screen` "F" or "Eprime" appended to
`bench/results/offline-screens-20261022.jsonl`, per-arm artifacts under
`bench/results/offline-screens-20261022/`, a journal and an `evidence_verification` record,
as screens A-E. Tests appended to `plant2/tests/test_offline_screens.py` (non-slow,
synthetic): the lockstep against `replay`'s trace; d_j read before reset; water-filling
exactness and the cap; the surplus-only distribution and its flag; AUC with ties; the
feedback-store rebuild and both integrity gates; the E′ binning. Single process, minutes.

## What this cannot show

Screen F's counterfactuals are computed on the binary candidate's trajectory: a graded rule
would change the forward store, the responders and therefore its own teacher from the first
vetoed episode on, so the screen can kill (no separation, no flip reduction) and cannot
clear. The AUC is a separation of line classes by a proxy signal, not a C2 prediction.
Screen E′ bins by the prediction's coverage, not by what each cell carries.

## Results (appended 2026-10-22, 23:13-23:15 UTC; module feaf31f, 51 tests green)

Records: `offline_screen` E′ (candidate) COMPLETE; F gate_off and F candidate COMPLETE with
both integrity gates passed on every episode (rebuilt feedback keys equal `feedback_keys`;
lockstep |G| and |G ∩ E| equal the gate log on all 1,000 episodes); the F independent arm
recorded INVALID on a first attempt because the job asserted family prototypes that the
independent condition does not have (an implementation assumption, not an evidence
failure; the arm is rerun after the fix and its line is appended below). All numbers
**offline, development seed 121**; F's counterfactuals **proxy**.

**Screen E′ (candidate, 1,238 late-class cells over 200 cues, equal to screen E's count).**
Binned by the minimum write-time coverage (`proto_predicted`) over the same-family items
each cell holds: < 0.25: 5.52 per cue (share 0.891; items-weighted 0.909); 0.25-0.75: 0.42
(0.068); ≥ 0.75: 0.26 (0.041). On the episodes of those same-family items p had median
0.627 (10th percentile 0.50, 90th 0.99). **Reading:** the late class is a ramp leak, not a
steady-state leak: nearly nine in ten of the cells classified "after engagement" hold an
item written while the prediction still covered less than a quarter of its prototype lines.
With the early class (1.97 per cue), about 90 % of the residual was written during the onset
ramp of its family.

**Screen F (candidate).** AUC of the subthreshold drive separating missed prototype lines
from unpredicted non-prototype lines, by block of 100 episodes: 0.752 in block 1 (the first
block has 3,843 missed prototype lines against 5,979 unpredicted unique lines); over
episodes 501-1,000: **0.858**. Counterfactual expected prototype flips per plateau cell,
graded over binary: **0.441** over 501-1,000, **0.750** over episodes 1-300. Kill reading for
P2-E8: AUC ≥ 0.70 held; ratio ≤ 0.6 held; the third rule (ramp ratio > 0.85 and a late class
concentrated below 0.25) did not fire because the ramp ratio is 0.750, although E′'s
low-coverage share is 0.891. **Survives**: drafting the P2-E8 contract is authorised, and
nothing else. **Screen F (gate_off, the baseline trajectory's own gate).** Block-1 AUC 0.750
and ratio 0.884; B-017's line: mean prototype coverage over episodes 101-500 is **0.513**
against the twin-store proposal's own kill of 0.595, so B-017 closes.

**Screen F (independent candidate, rerun 23:21 UTC after the fix at 9cf822d; COMPLETE, both
integrity gates passed).** No prototypes exist on independent inputs, so only the
perturbation fields apply: the graded rule's mean TV distance from the uniform 0.5 is
0.0167 over all episodes (0.0016 over 1-300, 0.0291 over 501-1,000; the binary rule's is
0 everywhere because no line is ever predicted), and 49.5 % of episodes have some p below
0.49 (7.7 % over 1-300, 80.2 % over 501-1,000). Against the F10 candidate's graded TV of 0.161
over 1-300, the independent perturbation is an order of magnitude smaller; the P2-E8
independent-perturbation kill would not fire on this trajectory.

Counts in this document for the graded and binary rules are expected flips per plateau cell
from the recorded windows (candidate trajectory): binary 16.6 / 3.45 prototype flips over
episodes 1-300 / 501-1,000, graded 12.4 / 1.52, surplus-only 16.4 / 3.29; the "about 5.5"
quoted at checkpoint 2 from the contract's arithmetic is superseded by the measured 3.45.

Reading for the next contract (arithmetic on recorded values, exploratory): the graded rule's
counterfactual reach is largest where the residual is smallest. It removes 56 % of the
expected missed-prototype flips in the steady state, which holds about 4 % of the late
class, and 25 % during the ramp, which holds about 90 % of the residual together with the
early class. A graded rule's gain is therefore expected to be modest, and the panel's
predicted C2 point of .86 is optimistic; the contract sets its predictions from this
screen, not from the panel.
