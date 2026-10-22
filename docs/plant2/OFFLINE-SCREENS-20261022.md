# Offline screens on persisted evidence, 2026-10-22

Contract for four zero-seed analyses that the 2026-10-22 judge panel asked for before any
contract cites their numbers (`docs/research/ROADMAP.md`, priority 2; `DECISIONS.md`
2026-10-22 checkpoint entry, decision 5). No simulation runs, no seed is spent, no frozen
driver is edited, and nothing here is a capability or a gate. Every output is labelled
**offline** and, where a stand-in replaces the real quantity, **proxy**. The commit that adds
this file freezes it; results are appended below after the run.

Inputs, all read-only and verified (size and SHA-256 against the recorded descriptor) before
use: the P2-R2b combined artifacts `bench/results/p2r2b/seed{105,106}-{ORIGINAL,DEGREE_NULL}-M{500,1000}.json`
(per-cue `index_cues` rows with `first_spikes100`, content tables, `raw.learned` and
`raw.raster` descriptors) and the raw learned checkpoints they point to under
`~/.cache/brain-sim/plant2-research-20261022/p2r2b/plant2/p2r2/` (per-episode `items`, `A`,
`E`, `R` as ragged arrays; `forward_keys`, `feedback_keys`, `assigned_feedback_keys`); and the
P2-E6 seed-101 evidence files `bench/results/p2e6/e6-s101-v1-*.json`. Family structure is
recovered from the frozen generator: `FamilyGen(seed, 4000, 100, 60, 10)`, exemplar index
k + 1 for 0-based episode k, family (k + 1) mod 10, retained prototype set
P_k = item_k ∩ protos[(k + 1) mod 10], which must have exactly 40 lines for every episode
(checked; a mismatch is INVALID for that seed). Checked 2026-10-22 on seed 105: the generator
reproduces the persisted items and every P_k has 40 lines.

## Screen A: error-gate pre-screen (proxy, advisory)

Purpose: warn, before development seed 121 is spent, if P2-E7's teacher (the responder-written
feedback store) is already saturated on the baseline trajectory. It cannot pass P2-E7's
structural kill, because the baseline trajectory never sees the veto engage and because two
stand-ins replace quantities P2-E7 measures exactly.

For seeds 105 and 106, arm ORIGINAL, from the M = 1,000 learned checkpoint, for each episode
k = 0..999:

- the feedback store before episode k is S_k = ∪_{i<k} R_i × E_i, kept as writer sets per
  line; the episode's own write R_k × E_k is excluded;
- the encoding-responder proxy is Q_k = R_k \ A_k (continuation responders that are not the
  item's plateau cells; the plateau cells have no synapses for item k before the write);
- the predicted set under a count rule is G_θ(k) = { j : |writers_j(S_k) ∩ Q_k| ≥ θ }, with
  the primary threshold θ_k = ceil(0.3·|Q_k| + 7.14) (the frozen readout's inhibition-aware
  coincidence requirement, 20 mV / 2.80 mV = 7.14 writers plus 0.3 per active memory cell)
  and a sensitivity sweep over fixed θ ∈ {8, 12, 16, 19, 24};
- per episode: |V| = |G ∩ E_k|; prototype predicted fraction |G ∩ P_k ∩ E_k| / |P_k ∩ E_k|;
  non-prototype predicted fraction |G ∩ (E_k \ P_k)| / |E_k \ P_k|; veto precision
  |G ∩ P_k ∩ E_k| / |G ∩ E_k| (None when |G ∩ E_k| = 0).

Reported per seed: the per-episode rows (artifact), block means over episodes 1-100, ...,
901-1,000, and the means over episodes 501-1,000 at the primary threshold, set beside
P2-E7's structural-kill thresholds (mean |V| ≥ 5, veto precision ≥ 0.70, non-prototype
predicted fraction ≤ 0.25, prototype predicted fraction ≥ 0.25). Reading: a non-prototype
predicted fraction above 0.25 on the baseline trajectory is a warning that P2-E7's kill (d)
may fire; it decides nothing.

## Screen B: branch static screen (offline static count)

Purpose: reproduce and record the panel's static count behind B-013, with the integrity
gate the contrarian proposer required, and with the threshold sensitivity the constructive
judge showed.

For seeds 105 and 106, arm ORIGINAL, M = 1,000:

1. **Integrity gate.** Rebuild the forward store from the persisted A_k and E_k, episode by
   episode, with coins from stream (seed, 3) drawn as `btsp_update` draws them (one flat
   array of |E_k|·|A_k| uniforms, E-major, A-minor, p = 0.5, toggle semantics of
   `BinarySynapses`). The rebuilt keys must equal the persisted `forward_keys` exactly;
   otherwise the screen is INVALID for that seed and stage 2 is not run.
2. **Branch store.** Replaying the same toggles, assign each episode's toggles on cell i to
   branch b = (number of plateaus cell i had before this episode) mod K, K = 8 (B-013's
   round-robin rule), toggling within the branch; also K = 4 as a dose arm.
3. **Cue counts.** For each of the 200 half cues of the M = 1,000 index test (cue lines
   reproduced from the frozen `test_sets` and cue construction for seed and M; the
   reproduced cue items must match the artifact's `index_0based` per row), per memory cell:
   the point count (cue lines with w = 1) and the branch-max count (max over branches of cue
   lines with w = 1 on that branch). Own cells are A(cue item).
4. **Report**, per cue and averaged over cues, for T = 9..14: non-own cells with point
   count ≥ T; non-own cells with branch-max ≥ T (K = 8 and K = 4); own cells with point
   count ≥ T and with branch-max ≥ T; mean own point count and mean own branch-max.

Label: a count on synapses, not a firing probability; per-branch accommodation cancels each
branch's background mean, so branches differ from point cells in noise, not in offset, and
the branch firing point is unmeasured. The numbers the panel quoted (point 91.89/86.94
non-own cells at ≥ 12 against branch 0.76/0.58; own 18.94 → 18.77) are reproduced or
contradicted here, and only this record is citable.

## Screen C: own-versus-spurious first-spike latency split (B-008's cheapest test)

For seeds 105 and 106, arms ORIGINAL and DEGREE_NULL, M = 500 and 1,000, from the half-cue
rows' `first_spikes100` ([cell, tick] pairs within 100 ms of cue onset) and A(index) from the
learned checkpoint:

- per cue: own cells' and spurious cells' first-spike ticks; medians and 10th/90th
  percentiles; pooled distributions per seed/arm/load;
- a latency-cut bound: for t_c ∈ {20, 25, 30, 35, 40, 45, 50} ms, treating every cell whose
  first spike is later than t_c as silenced, recompute per cue recall (own cells with first
  spike ≤ t_c, over |A|), spurious count, C1 (recall ≥ 0.8), C2 (spurious < 0.5·|A|) and the
  joint fraction, and report them against the recorded C1/C2 at 50 ms.

Label: descriptive. A latency cut is not a mechanism: an inhibitory brake would change the
raster it is cut from. The bound is optimistic for a timing brake's selectivity and
pessimistic for own-cell loss; it says whether B-008 deserves a contract, nothing more.

## Screen D: regeneration saturation of the responder-written store

From the content tables (`content.inherited.rows`, column `total`: lines with at least one
rec spike in the 75 ms window) of: P2-R2b seeds 105/106, both arms, both loads; P2-E6
seed-101 baseline and candidate at F10 M = 500 and 1,000 and independent M = 1,000 (fields
absent in a file are reported as absent, never substituted). Per file: median and quartiles
of `total` for full cues, half cues and novel cues; the feedback store density
|feedback_keys| / (4,000 × 4,000) where the learned checkpoint is available (P2-R2b) and the
forward density from `learning.forward_density`.

Label: descriptive, test-time, settled, full or half cues; not the encoding-time quantity
P2-E7 gates on. The judges' quoted 743.5 / 3,643 / 133 medians are reproduced or contradicted
here.

## Outputs, records and discipline

Script `analysis/offline_screens_20261022.py` (new; imports frozen modules read-only), CLI
`run --screen {A,B,C,D} [--seed ...]` and `summary`. Results append to
`bench/results/offline-screens-20261022.jsonl` as records of kind `offline_screen` (fields:
`screen`, `seed`, `arm`, `M`, `label`, `summary`, `artifact` descriptor, `inputs` with each
input's verified descriptor, `source` with the script's and the frozen modules' SHA-256, the
git commit and runtime) and `evidence_verification`; per-screen artifacts under
`bench/results/offline-screens-20261022/` through `plant2.evidence.write_json_artifact`,
with a `Journal` per run and `Manifest.verify_all` at the end. A failed input verification
or integrity gate records INVALID with the reason and writes no success. Single process,
minutes; no git command while it runs. Tests `plant2/tests/test_offline_screens.py`
(non-slow, synthetic inputs under the `run_dir` fixture, never real paths) cover: the
incremental store rebuild and count rule; the forward-store rebuild equality and its
INVALID path on a mismatch; the round-robin branch assignment and in-branch toggle; the
cue-count arithmetic on a tiny store; the latency-cut arithmetic; the absent-field handling
of screen D; and that artifacts go through `plant2/evidence.py`.

## What this cannot show

Nothing here is a memory capability, a replication, or a decision. Screen A's stand-ins
(continuation responders for encoding responders; a count rule for the LIF readout) can
warn and cannot clear P2-E7's kill rules. Screen B counts synapses, not spikes. Screen C's
cut is not a brake. Screen D measures test-time saturation, not encoding-time prediction.
Each result enters the ledger with the label `offline`.

## Results (appended 2026-10-22, 19:38-19:39 UTC; commit 5c7199b)

Module `analysis/offline_screens_20261022.py` (dadc62e, D extended in 5c7199b; 27 tests).
Records: `bench/results/offline-screens-20261022.jsonl` (26 `offline_screen` records, all
COMPLETE, and 9 `evidence_verification` records, all passed); artifacts under
`bench/results/offline-screens-20261022/`. Every input descriptor verified before reading.
All numbers below are **offline**; screen A is additionally a **proxy**.

**Screen A (gate pre-screen, proxy).** Baseline trajectory, ORIGINAL arm, primary
inhibition-aware threshold, episodes 501-1,000: seed 105 mean |V| 56.48, prototype
predicted 0.988, non-prototype predicted 0.292, veto precision 0.720; seed 106: 56.87, 0.994,
0.295, 0.717. By block of 100 episodes (seed 105; seed 106 alike): |V| 2.4, 13.1, 27.1,
36.2, 39.2, 43.1, 50.1, 55.3, 62.9, 70.9; prototype predicted 0.06, 0.33, 0.68, 0.89, 0.93,
0.97, 0.99, 1.00, 0.99, 0.99; non-prototype predicted 0.001, 0.002, 0.006, 0.015, 0.038,
0.084, 0.181, 0.266, 0.393, 0.532; veto precision 0.98, 0.99, 0.99, 0.98, 0.95, 0.89, 0.79,
0.73, 0.64, 0.56. Sensitivity: at fixed θ = 8 the non-prototype fraction is 0.87 and at
θ = 24 it is 0.53, so the proxy's level depends on the count rule and only its time course
is robust. **Reading:** on the baseline trajectory the prediction engages early (prototype
lines are predicted for most of a family by block 3-4) and the teacher saturates late (the
non-prototype fraction crosses P2-E7's 0.25 kill threshold in block 8 and the precision
falls below 0.70 in block 9). This is the warning the skeptic judge asked for: P2-E7's
saturated-teacher and contamination-driven-veto kill rules are at risk if the veto does not
reduce responder contamination as learning proceeds. The candidate trajectory is not the
baseline trajectory (fewer sibling synapses means fewer spurious responders writing the
store), so the proxy cannot decide; the structural check on seed 121 does.

**Screen B (branch static screen).** The integrity gate passed on both seeds: the forward
store rebuilt from the persisted A and E with stream-(seed, 3) coins equals the persisted
`forward_keys` exactly (a mismatch records INVALID; both records are COMPLETE). Mean over the
200 half cues of non-own cells at or above T cue synapses, point versus branch-max (K = 8;
K = 4): seed 105: T9 426.1 / 31.5 / 61.0; T10 270.9 / 10.0 / 23.8; T11 162.3 / 2.8 / 8.7;
T12 91.9 / 0.76 / 3.0; T13 49.5 / 0.18 / 1.1; T14 25.0 / 0.08 / 0.37. Seed 106: T9 411.0 /
29.7 / 58.5; T10 257.2 / 9.3 / 22.8; T11 153.2 / 2.5 / 8.5; T12 86.9 / 0.62 / 2.9; T13 46.9 /
0.12 / 0.87; T14 23.6 / 0.02 / 0.25. Own cells at or above T: 20.3 of about 20 at every T on
both seeds, point and branch alike (own mean cue-synapse count 24.8 / 24.6 point, 24.7 / 24.5
branch-max at K = 8). The panel's point numbers (91.89 / 86.94 at T12) reproduce; its branch
number for seed 106 (0.58) was drawn with a non-stream coin generator and is replaced by
0.62. **Reading:** branch segregation shrinks the above-threshold non-own tail by about two
orders of magnitude at T12 and by about fourteen times at T9 while leaving own cells
untouched; the static separation is real at every T from 9 to 14, but a count is not a
firing probability and the branch firing point is unmeasured. B-013 keeps this record as
its cheapest test, done.

**Screen C (own-versus-spurious first-spike latency).** Half cues, first spikes within
100 ms. Own cells: median 22-24 ms, 10th percentile 13-15 ms, 90th 40-44 ms (every arm and
load, both seeds). Spurious cells: median 66-69 ms, 10th percentile 36-41 ms, 90th 93-94 ms.
Latency-cut bound at M = 1,000, ORIGINAL arm (seed 105; seed 106): cut 40 ms gives C1 0.775
(0.790), C2 0.690 (0.670), joint 0.470 (0.480); cut 45 ms gives C1 0.870 (0.885), C2 0.575
(0.535); cut 50 ms recovers the recorded C1 0.930 (0.925) and C2 0.450 (0.445). No cut
reaches C1 ≥ 0.90 and C2 ≥ 0.90 together on either seed at either load. **Reading:** the
spurious cells' early tail (10th percentile 36 ms) overlaps the own cells' late tail (90th
percentile 40-44 ms), so a timing brake alone trades recall for specificity along H-067's
curve and cannot clear both bars. B-008's cheapest test is done and the answer is no for a
standalone timing mechanism; it stays a possible component of a recurrence contract only.

**Screen D (regeneration saturation, test-time, settled).** Median lines with at least one
rec spike in the 75 ms window (quartiles in brackets, 200 cues each). P2-R2b ORIGINAL at
M = 1,000: full cues 3,640 [3,551, 3,713] (105) and 3,638 [3,548, 3,721] (106); half cues 1,962
[1,122, 2,709] and 2,004 [1,144, 2,626]; novel 0. At M = 500: full 814 and 787; half 190 and
166. DEGREE_NULL at 1,000: full 1,147 and 1,117; half 275 and 298. Feedback store density:
ORIGINAL 0.123 / 0.120 at 500 and 0.313 / 0.318 at 1,000; DEGREE_NULL 0.065 and 0.153 / 0.154.
P2-E6 seed 101 (exploratory): F10 baseline full 744 at 500 and 3,643 at 1,000; F10 candidate
155 and 1,140; independent baseline 133 and candidate 126 at 1,000 (feedback density absent:
no learned checkpoint on this host). The judges' quoted 743.5 / 3,643 / 133 reproduce.
**Reading:** at the canonical load a learned F10 cue regenerates most of the 4,000 lines
through the responder-written store, and the E6 history budget cut that three-fold; the
quantity P2-E7 gates on is the encoding-time prediction, which screen A approximates and the
structural check measures.
