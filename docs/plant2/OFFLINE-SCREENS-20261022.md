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
