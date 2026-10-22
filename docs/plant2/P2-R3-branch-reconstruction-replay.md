# P2-R3: episode-clustered reconstruction store with bounded line-local branches, as an exact reported replay (B-015)

Contract, 2026-10-22, selected at roadmap checkpoint 2 (`docs/research/ROADMAP.md`;
`DECISIONS.md` entry of the same day; ranked first by both judges of the checkpoint-2 panel).
The commit that adds this file freezes it; append only thereafter. A reported replay on the
persisted P2-E7 seed-121 evidence: no seed, no simulation of a network during learning, no
frozen driver edited. It is not a capability, not a gate, and it credits nothing; it
decides whether the content wall at F10/1,000 is cross-episode writer summation on the
reconstruction lines, and what a bounded branch store buys at F10/500 on the deployable
trajectory. Hypotheses: a new one, **H-085** ("at F10 the content failure is cross-episode
writer summation on reconstruction lines, which a bounded episode-clustered store removes
without changing the writers"), graduating B-015; bearing on H-036, H-046, H-049, H-052 and
H-057.

## What is inherited unchanged

Learning is the persisted literal-E3 trajectory of seed 121 (and the other persisted arms):
nothing about the plateau draw, eligibility, coins, forward store, continuation or R(x) is
touched. The frozen readout constants (tau_m 20, v_rest −70, v_th −50, v_reset −65, t_ref 2,
float32 arithmetic; J_fb 2.80 at delay 1; global inhibition g·J_fb = 0.84 mV per memory spike
at delay 2; 75 ms window, short 50, span 75), the content criteria (joint: ≥ 40 of 50 missing
lines regenerated and < 10 intrusions; D1, D2, D3, D4 as `e3.score` defines them), the
persisted test rasters, cue sets and per-cue rows of P2-E7, and the index values (which never
read the feedback store and are identical by construction).

## The mechanism (replayed, not deployed)

1. **Store.** Each reconstruction line j holds K binary writer sets W[j, b], b = 0..K−1, and a
   line-local counter n_j = the number of earlier write events in which j was eligible.
   Episode k's write puts R(k) into W[j, n_j mod K] for every j ∈ E(k) (add-only union
   within the branch, as the frozen store is add-only), then increments n_j. The plateau-set
   diagnostic store A × E gets the same structure with A(k) as the writer set.
2. **Readout.** Each (j, b) is an LIF compartment with the frozen rec constants, receiving
   J_fb per spike of a memory cell in W[j, b] at delay 1 and the frozen global inhibition term
   at delay 2, applied identically to every branch as it is applied to the point line. Line j
   spikes at tick t if any of its branches spikes at t (OR); each branch resets independently.
   The window, short window, span and criteria are unchanged.
3. **Constants.** K = 32, fixed from frozen constants and not from data, by the rule B-013
   used for its K = 8: the smallest power of two at or above the expected eligible episodes
   per line at the largest load, M·a/m = 1,000 × 100 / 4,000 = 25. Dose arms K = 8 (B-013's
   number) and unbounded (one branch per episode; conflicts with bounded forgetting, never
   deployable) are reported only. No J, g, window or threshold changes, and no grid.
4. **Parity.** At K = 1 the rule is the frozen readout: the K = 1 replay must reproduce every
   persisted `content.inherited` row and the rebuilt point store's SHA-256 must equal each
   load's `feedback_sha256`; otherwise the replay is INVALID.

Labelled proxy: branch-clustered (dendritic-subunit) plasticity on the reconstruction side,
synapses co-written in one episode clustering on one branch that acts as an independent
nonlinear unit (Govindarajan, Kelleher & Tonegawa 2006; Poirazi & Mel 2001); a circuit-level
proxy, not a claim about entorhinal or CA1 dendrites.

What differs from P2-E7 and why this is a new hypothesis, not a rescue: it touches neither
the forward write nor any selection, inherits no P2-E7 constant, needs no prediction and no
veto, and acts on the other store; P2-E7's failed index bars stay failed. Because the
feedback store never feeds back into memory dynamics on the gate_off, label_oracle and
independent trajectories, the replay on their persisted rasters is the exact deployed
computation for those trajectories, not an approximation. On the candidate trajectory the
learning read the point store as its teacher, so that replay is a stacking diagnostic,
reported only, never credited.

## Substrates, loads and arms

| substrate (persisted rasters, attempt seed121-1792699741870086415-c573e46d) | role |
|---|---|
| F10 `gate_off` at 500 and 1,000 (= the baseline trajectory, SHA-equal) | deployable; exact |
| F10 `label_oracle` at 500 and 1,000 | clean-index diagnostic; exact; never credited |
| F10 `candidate` at 1,000 | stacking diagnostic; reported only |
| `independent` candidate (= baseline) at 500 and 1,000 | non-regression; exact |
| `mixed` baseline at 1,000 | non-regression on the independent subset; exact |

Arms on every substrate and load: K = 1 (parity), K = 32 (the rule), per-synapse scramble
(same K, each line's writer multiset preserved, the branch of every (j, writer) synapse drawn
from stream (121, 37, j) instead of by episode: separates episode clustering from merely
splitting writers into K parts), assigned-A branch store (A × E under the same rule:
separates writer contamination, H-036, from cross-episode summation), dose K = 8 and
unbounded (reported). The persisted riders (R_3, R_1, size-matched random, anti-selected on
gate_off) are quoted as the point-store references and not rerun.

## Step 0: decomposition (recorded before the replay; decides whether the replay runs)

On the `gate_off` and `label_oracle` rasters at 500 and 1,000, with the point store: classify
each half cue that fails inherited or assigned-A content as a D1 failure (missing lines
recovered < 40) or an intrusion failure (intrusions ≥ 10) or both; count the memory cells
active in ticks 0-49 and 50-74 of the window; for each intrusion line, from the persisted R
and E, count its active writers per contributing episode (the episodes whose write put those
writers on the line) and whether any single episode's active writers reach
ceil(0.3·N_active + 7.14), the frozen readout's coincidence requirement. The recorded D1
fields (≥ .955 on every F10 arm and load) already show that failures are intrusions; step 0
records it and adds the span structure. **Kill before the replay** if, on the oracle raster
at 1,000, fewer than half of the failing cues fail by intrusions whose active writers span
at least two episodes with no single episode reaching the coincidence requirement: content
at 1,000 would then not be limited by cross-episode summation, B-015 closes, and the next
checkpoint goes to the memory side.

## Predictions (frozen before implementation; each names its field)

- **P1 parity.** K = 1 reproduces every persisted `content.inherited` row and
  `feedback_sha256` on every substrate and load; the index fields are identical.
- **P2.** label_oracle, F10/1,000, `content.inherited.joint` under K = 32 in [0.60, 0.95]
  (point .310); kill if < 0.46 (point + 0.15).
- **P3.** label_oracle, F10/1,000, assigned-A branch store joint in [0.70, 0.98] (point .500).
- **P4.** gate_off, F10/500, inherited joint under K = 32 in [0.50, 0.95] (point .145; R_3
  rider .925, R_1 .145, random .310 reported-only); kill if < 0.345 (point + 0.20).
- **P5.** gate_off, F10/1,000, inherited joint in [0.00, 0.30]: predicted to stay below the
  bar because the index is C2 .500 there; not a bar.
- **P6.** candidate raster, F10/1,000, inherited joint in [0.05, 0.50] (point .005); reported.
- **P7.** independent at 500 and 1,000, inherited joint ≥ .975 and ≥ .940 (drop ≤ 0.02 from
  .995 / .960); kill if a drop > 0.05 at either load.
- **P8.** mixed baseline at 1,000, `content_by_subset.independent.joint_count` in [32, 80]
  cues (point 34 of 95; non-regression within 2 cues, improvement expected).
- **P9 scramble.** On the oracle raster at 1,000 the per-synapse scramble's inherited joint
  ≤ 0.41; kill if it lands within 0.05 of the K = 32 episode-branch store (plain dilution).
- **P10 novel cues.** Median rec lines with ≥ 1 spike in 75 ms on novel half cues ≤ the point
  store's median on the same raster, every substrate.
- **P11 dose.** Inherited joint non-decreasing in K over 8, 32, unbounded on the oracle and
  gate_off rasters (reported).
- **P12 D1.** D1 under K = 32 within 0.05 of the point store's on every substrate (branches
  remove some cross-episode support for own missing lines; a larger drop is recorded as the
  cost of clustering).

No prediction is revised after the run. A contradiction of P2 on the oracle raster, or of P9,
closes B-015 as a failed hypothesis; a split (P2 held, P4 failed) is recorded as such.

## Outputs, records and discipline

Contract first; then `analysis/p2r3_branch_rec.py` (new; imports `plant2.readout`,
`plant2.evidence`, `plant2.experiments.p2_e3_completion` for `score`, the frozen generators
read-only): `build_branch_store(E_seq, R_seq, K, mode)` for the episode, per-synapse-scramble
and unbounded modes with the per-line counter; `branch_replay(raster, n_ticks, branch_csr, m,
J, g, cues, K, window=75, short=50, span=75)` beside the frozen `replay` with the same cue
contract and return shape, event-driven over branches; the step-0 decomposition; scoring
through the frozen `e3.score`; CLI `step0`, `run`, `summary`. Records append to
`bench/results/p2r3.jsonl` (kinds `step0`, `parity`, `replay`, `evidence_verification`,
`summary`), portable per-cue tables under `bench/results/p2r3/` through `plant2/evidence.py`
with a journal and `Manifest.verify_all`; every input verified against its descriptor;
absent inputs reported absent, never substituted. Tests `plant2/tests/test_p2r3.py`
(non-slow, synthetic inputs under `run_dir`): K = 1 equals `readout.replay` bit for bit
including delays and inhibition; round-robin assignment and the per-line counter; the
scramble preserves each line's writer multiset; the OR rule with independent resets; the
step-0 classification on hand-built cues; artifacts through `evidence.py`. Single process;
time measured on a small configuration first; no git command while it runs.

## What this cannot show

A reported replay on one development seed's persisted rasters: not a capability, not a
gate, no fresh seed. Its deployable gain can only be at F10/500; at F10/1,000 on the
deployable trajectory the index swamps content. The oracle raster uses experimenter labels
and is a diagnostic substrate only. Deploying a branch reconstruction readout would be a
change to the frozen readout's integration (ruling 6) and would need the owner's ruling on
dendritic subunits extended to reconstruction lines (question (a)); a gated content contract
before an index pass needs the owner to accept the reordering against ruling 3 (question (g)).
Nothing is removed from the experimenter's supply.
