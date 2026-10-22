# P2-E7: prediction-gated (error-gated) forward eligibility with a conserved flip budget — DRAFT

Draft contract, 2026-10-22, under adversarial review; not frozen. The frozen text will be
`docs/plant2/P2-E7-error-gated-eligibility.md` with `docs/plant2/P2-E7-frozen.json`, and the
commit that adds them freezes them; append only thereafter. This draft is preparation
provenance, as `P2-R2b-replication-DRAFT.md` was for P2-R2b.

Selected at the 2026-10-22 roadmap checkpoint (`docs/research/ROADMAP.md`; `DECISIONS.md`
entry of the same day) from a ten-proposal judge panel, as the merged form of its two
top-ranked proposals. Owner authority: the error-correcting write family approved as a
research direction (ruling 4, 2026-10-10) and the local-error signal named for the forward
index (ruling 3, 2026-10-12). It is one mechanism, needs no new ruling, retunes nothing, and
is scored on the index separately from content.

## Question and hypotheses

Does a write rule that refuses to index the parts of an experience the network already
regenerates from its own memory, while keeping the expected number of flips per plateau cell
unchanged, remove the forward-index cross-talk on correlated items at the canonical load
without costing recall of unrelated or old items?

Hypotheses tested (`docs/research/HYPOTHESES.md`): **H-060** (primary; B-002 graduated);
**H-055** through the owner's two required questions, whether the feedback store supplies
useful error information (the count-matched random-drop control) and whether corrections
preserve unrelated memories (the independent-input arms and the oldest cohort); and, by its
controls and predictions, H-035, H-041, H-043, H-044 and H-046. The contract names them so
that `HYPOTHESES.md` can move H-060 to `under_test` on the freezing commit.

## What is inherited unchanged

Everything the P2-E6 contract inherited from P2-E3 and P2-E5, byte-identical and hash-pinned
at run time exactly as `plant2/experiments/p2_e6.py` pins them: `plant2/engine.py`,
`plant2/btsp.py`, `plant2/readout.py`, `plant2/record.py`, `plant2/evidence.py`,
`plant2/experiments/p2_e1_btsp.py` through `p2_e6.py`, the `FamilyGen` item generator
(F = 10, s = 60: each exemplar keeps 40 of its family's 100 prototype lines and draws 60
outside), the independent generator, the E3 learner (J_mem 1.525 mV, accommodation tau
10,000 ms, 200 ms encoding at 40 Hz against 0.5 Hz, eligibility of at least 3 input spikes,
random plateau sets at f_q 0.005 from stream 2, coins from stream 3, the 50 ms continuation,
the responder feedback write R × E and the diagnostic plateau-set store A × E), the loads
500 and 1,000 as nested checkpoints of one learning run, the settled test protocol (deep
copy, 50 s settle, 200 half cues, 200 novel half cues, 200 full cues, 100 ms cue and 200 ms
gap), the 50 ms index window and its criteria (C1 recall ≥ 0.8 of A; C2 spurious < 0.5 of
|A|; C3; C4 on the oldest 100 items; joint index), the frozen 75 ms content readout at
J_fb 2.80 and g 0.3 with the joint criterion (≥ 40 of 50 missing lines regenerated, < 10
intrusions), the protocol validity checks (eligibility ≥ 0.95 of the item's lines before any
veto; mean |A| at 1,000 in [18.5, 21.5]; settle drift ≤ 0.2 mV), the sanity checks
(wrong-label raster permutation C1 < 0.10; never-trained empty store gives 0 responders),
and the feasibility bars and margins of `docs/plant2/P2-E6-frozen.json`, copied verbatim
into `P2-E7-frozen.json`: C1, C2, C3, C4_recall, C4_spurious ≥ 0.90 and joint index ≥ 0.85
at F10 and independent, both loads; F10/1,000 C2 ≥ baseline + 0.20 and ≥ random + 0.10;
joint index ≥ each + 0.10; C1 non-regression 0.03; independent C2 non-regression 0.03;
independent content joint and D4 non-regression 0.05.

The frozen deployed readout is primary; the one grid in this contract (the matched-silence
comparator) is an explicitly optimistic diagnostic and decides nothing.

## The mechanism

It changes one thing in `E3.learn_one`: which eligible lines are toggled, and with what
probability. The plateau draw, the encoding, the eligibility rule, the continuation, R(x),
the feedback write with the full E(x), the diagnostic plateau-set write and the test
protocol are untouched.

1. **Prediction during encoding.** The memory layer's spikes during the first 75 ticks of
   the encoding (ticks 0-74, counted from encoding onset, the memory layer having been
   reset by `quiet()` as in E3) are played through the frozen readout arithmetic
   (`plant2/readout.py: replay`: feedback J_fb 2.80 mV at delay 1 from the feedback store as
   it stands before this episode's write, global inhibition g·J_fb = 0.84 mV per memory spike
   at delay 2, the rec constants, rec starting at rest). The predicted set G(x) is the set of
   lines whose rec cell spikes at least once in ticks 0-74. This is the frozen 75 ms content
   window and its frozen "regenerated" rule, reused at encoding time. Nothing flows back:
   there is no rec → mem path and no current is injected into any memory cell, so the memory
   dynamics and every random stream are bit-identical to E3 given the same forward store.
   Implementation may step a side rec population in lockstep or replay the recorded 75-tick
   raster after the encoding; either way a unit test proves bit-equality with `replay`'s
   trace on the same raster and store.
2. **Veto.** E(x) is the inherited eligible set (≥ 3 input spikes in the 200 ms). The veto is
   V(x) = E(x) ∩ G(x) and the written set is E'(x) = E(x) \ V(x).
3. **Conserved flip budget.** Coins are drawn exactly as `btsp_update` draws them: one flat
   array of |E|·|A| uniforms from stream 3 in eligible-major, plateau-minor order, so the
   coin stream stays aligned across arms and episodes. Synapse (j, i) toggles iff j ∈ E'(x)
   and u_ji < p(x), with p(x) = min(1, 0.5·|E(x)| / |E'(x)|). The expected number of flips per
   plateau cell is therefore 0.5·|E(x)|, as in E3, whenever p(x) < 1. If V(x) is empty,
   p = 0.5 and the episode is bit-identical to E3. If E'(x) is empty, nothing toggles and
   the episode is logged as a familiarity event (see compliance).
4. **No new parameter.** The 75-tick window, J_fb, g, the ≥ 1-spike regeneration rule and
   the 0.5 budget factor are inherited constants. The cap at 1 is a probability bound.
   Nothing is calibrated and no seed is spent on calibration. The budget is a per-episode
   aggregate normalisation, the same labelled non-local circuit proxy P2-E6 carried; no
   history count, pseudocount or bisection is read by the candidate.

Labelled proxy: mismatch- or novelty-gated plasticity in the comparator view of the
hippocampal circuit (plasticity on the direct input where the recall-driven prediction does
not already account for it; Lisman & Grace 2005; Hasselmo 2006). A circuit-level proxy, not
a claim about CA1 physiology. The write still uses the supplied random key and the supplied
eligibility window; what the network now decides is which presented lines are indexed.

## Arms and conditions

Every arm is a separate learning trajectory from the same seed with identical plateau, input
and coin streams. Control arms compute their own gate each episode with the same arithmetic
on their own state, and use only its count.

| arm | condition(s) | rule | role |
|---|---|---|---|
| `baseline` | F10, independent, F40 | unchanged E3 learning; its forward store must equal plain E3 learning on the same seed (P2-E5 validity 1) | comparator; its raster carries the riders |
| `candidate` | F10, independent, F40 | the mechanism above | the deployed rule |
| `random_drop` | F10 | drop exactly \|V(x)\| lines from E(x), chosen uniformly without replacement from stream (seed, 33, episode); same p conservation on the reduced set | fails if the error signal carries no information (owner question 1) |
| `history_drop` | F10 | drop exactly \|V(x)\| lines from E(x), sampled without replacement with probability proportional to H_j + 1, where H_j is the number of previous episodes in which line j was eligible (E6's history and pseudocount, read only here); stream (seed, 34, episode); same p conservation | separates a co-occurrence-sensitive prediction from a hot-line filter in disguise (the question P2-R2b erratum 1 left open) |
| `gate_off` | F10 | G(x) computed and ignored; p = 0.5 on E(x) | integrity: its forward store's SHA-256 must equal the baseline's at every checkpoint, else the seed is INVALID |
| `no_conservation` | F10 | candidate veto with p = 0.5 on E'(x) | reported only: whether the budget rather than the error carries the gain |
| `label_oracle` | F10 | V(x) = E(x) ∩ (the item's retained prototype lines, read from the generator); same p conservation | diagnostic comparator only, never deployed: what removing the true hot lines can buy |
| `assigned_A_teacher` | F10 | candidate rule with G(x) read through the diagnostic plateau-set store A × E instead of the responder store | reported only: splits "the error signal is informative" from "the responder-written teacher is too contaminated" (H-055 evidence against) |

Independent-input baseline and candidate decide non-regression. F40 baseline and candidate
are transfer diagnostics, reported only, never a rescue (ruling 5). Family labels and
prototype membership are read by `label_oracle` and by the scoring diagnostics only; the
candidate never reads them.

## Seeds, streams and the seed guard

Seeds from the registry in `ROADMAP.md` and the 2026-10-22 `DECISIONS.md` entry: development
**121**; held-out **122**, opened only by a committed FEASIBILITY PASS screen on 121 with the
exact source digest; gated **131-135**, opened only by a committed passing held-out screen and
a committed `gate_ready` record, under a separately frozen gate contract. The driver's seed
guard refuses every other seed, refuses a second full-size attempt on any seed, and stops
gating after any INVALID screen, exactly as E6's guard does. No seed is shared with another
contract.

New stream ids: 33 (random drop), 34 (history drop), 35 (wrong-label permutation for this
driver's sanity check). Existing ids in use (0-6, 8-18, 20-24, 31, 32, 40) are not reused.
The gate itself uses no randomness.

## Structural kill, before any test phase

Computed at the end of F10 learning on the candidate arm, from persisted per-episode gate
fields, before any deep copy is tested. Any one of these ends the attempt with
`structural_kill` recorded and no test phase run; the development seed is then spent and the
idea is not retuned.

- **No engagement.** Mean |V(x)| over episodes 501-1,000 is below 5 lines.
- **Contamination-driven veto.** Over episodes 501-1,000, the fraction of vetoed lines that
  are the item's retained prototype lines is below 0.70.
- **Saturated teacher.** Over episodes 501-1,000, the non-prototype predicted fraction,
  mean over episodes of |G(x) ∩ (E(x) \ P(x))| / |E(x) \ P(x)| where P(x) is the item's
  retained prototype set, exceeds 0.25.
- **No structure.** Over episodes 501-1,000, the prototype predicted fraction, mean of
  |G(x) ∩ P(x) ∩ E(x)| / |P(x) ∩ E(x)|, is below 0.25.
- **Independent-input veto.** On the independent candidate arm, more than 5 % of episodes
  have a non-empty V(x).

The same fields are reported for episodes 1-500 and for every arm, including the baseline
(whose gate is computed but never applied), so the time course of the prediction is on the
record either way.

## Screen rules after the test phases (development seed)

Decided by the frozen `screen` of the driver from `load` records, as E6's screen is. KILL
(recorded as FEASIBILITY FAIL, no retuning, no held-out seed) if any of:

- F10/1,000 candidate C2 < baseline C2 + 0.20, or < random_drop C2 + 0.10 (E6 margins).
- F10/1,000 candidate C2 < history_drop C2 + 0.05 (kill e: a hot-line filter in disguise).
- F10/1,000 candidate joint index < baseline + 0.10 or < random_drop + 0.10.
- F10/1,000 candidate C1 or C4_recall below the baseline's by more than 0.03.
- Independent/500 or /1,000 candidate C1 or C2 below the baseline's by more than 0.03, or
  inherited content joint or D4 below the baseline's by more than 0.05.
- C3 < 0.90 on any candidate load.
- Any protocol validity check false on any arm; any sanity check failed.

FEASIBILITY PASS only if, in addition, every absolute bar holds on the candidate at F10 and
independent, both loads: C1, C2, C3, C4_recall, C4_spurious ≥ 0.90 and joint index ≥ 0.85.
A candidate C2 between 0.70 and 0.90 at F10/1,000 with no kill rule fired is an informative
FEASIBILITY FAIL and is recorded as such.

INVALID (numbers descriptive only, no replacement seed) if the gate-off store differs from
the baseline store at any checkpoint, if any evidence verification fails, if the resource
window is overrun without a clean PARTIAL, or if any `require` in the driver trips.

## Predictions (to be frozen before implementation; each names the deciding record and field)

Baselines quoted: P2-E6 baseline arm, seed 101, exploratory (`RESULTS-P2-E6.md`); P2-R2b
original arm, seeds 105/106, reported-only (`RESULTS-P2-R2b.md:26-31`); P2-E5 gated seeds
21-25. All predictions are read from `load` records of the development seed.

- **P1 (structural).** Candidate F10: mean |V| over episodes 501-1,000 ≥ 20 lines; veto
  precision (prototype fraction of vetoed lines) ≥ 0.80; prototype predicted fraction ≥ 0.50;
  non-prototype predicted fraction ≤ 0.10. Fields: `gate.mean_V_501_1000`,
  `gate.veto_precision_501_1000`, `gate.proto_predicted_501_1000`,
  `gate.nonproto_predicted_501_1000` on the F10/1,000 candidate `load` record.
- **P2.** F10/1,000 candidate `index.C2` in [0.82, 0.97] (point 0.90), against baselines
  .500 (exploratory), .485/.455 (reported-only), .435-.515 (gated).
- **P3.** F10/1,000 candidate `index.C1` ≥ 0.91 and `index.C4_recall` ≥ 0.90, against
  baselines .935 and .940 (exploratory), .925/.915 and .930/.930 (reported-only).
- **P4.** F10/1,000 candidate `index.joint_index` in [0.75, 0.93], against .440
  (exploratory), .420/.390 (reported-only).
- **P5.** F10/1,000 candidate `index.C4_spurious` in [0.70, 0.97], the weakest criterion:
  the oldest 100 items are the first ten per family, written before the veto engages
  (baseline .470 exploratory, .500/.420 reported-only). Most likely failure: this bar.
- **P6.** F10/1,000 candidate `content.inherited.joint` in [0.02, 0.40], still below 0.90
  (H-046); `content.assigned_A.joint` in [0.30, 0.60] (E6 candidate .425 exploratory).
- **P7.** Candidate `index.C3` ≥ 0.98 at F10 and independent, both loads.
- **P8.** F10/500 candidate: C1 ≥ 0.93, C2 ≥ 0.97, joint index ≥ 0.90, C4_recall ≥ 0.94,
  C4_spurious ≥ 0.92, `content.inherited.joint` in [0.50, 0.97] (index gains carry content
  at this load, H-046's counter-evidence; comparators E6 candidate .785 exploratory, R2b null
  .960/.965 reported-only).
- **P9 (controls).** F10/1,000 `random_drop` C2 ≤ 0.55; candidate C2 ≥ `history_drop` C2 +
  0.10; `label_oracle` C2 ≥ candidate C2 − 0.05 (the oracle bounds the candidate from above
  or near it); `no_conservation` C1 ≤ candidate C1 (unconserved writes lose recall).
- **P10 (non-regression).** Independent candidate at 500 and 1,000: every index measure and
  inherited content joint within ±0.02 of the same-seed baseline; V(x) non-empty on ≤ 5 % of
  episodes with |V| ≤ 2 where present; if no episode is vetoed, the candidate's forward store
  SHA-256 equals the baseline's.
- **P11 (matched state).** F10/1,000 candidate `diagnostics.spurious50_mean` ≤ 6 and
  `diagnostics.own50_mean` within ±1.0 of the baseline's (H-042); maximum prototype-line
  forward out-degree at 1,000 ≤ 0.5 × baseline (`learning.max_prototype_out_degree`).
- **P12 (integrity).** `gate_off` forward SHA-256 equals `baseline` at 500 and 1,000; the
  baseline's forward store equals plain E3 learning (`matching` digests).

No prediction is revised after the run. A contradiction of P2 with a FEASIBILITY FAIL is a
failed hypothesis; a structural kill is classified by which rule fired (no engagement or
saturation: failed hypothesis in its stated form; contamination-driven veto: the H-055
evidence against stands).

## Diagnostics and riders (reported only, never scored as outcomes)

- Per-episode, every arm: |E|, |G|, |V|, p, E' empty flag, veto prototype fraction,
  prototype and non-prototype predicted fractions, the episode index at which each family's
  veto first engages, continuation spike counts per memory cell, R(x), A(x), E(x), and the
  forward and feedback store sizes, persisted through `plant2/evidence.py`.
- Matched-state diagnostics per arm and load (H-042): own50, spurious50, forward density,
  assigned-cell threshold offset at cue onset.
- The own-versus-spurious first-spike latency split on every arm's half cues (B-008's
  cheapest test), from the per-cue rows.
- Matched-silence comparator (H-067): on the baseline deep copy at F10/1,000 only, a second
  index test with the memory threshold raised uniformly by the smallest δ in 0.25 mV steps
  (≤ 5 mV) whose own50 mean lies within ±1.0 of the candidate's; its C1/C2 are reported
  beside the candidate's. Explicitly optimistic diagnostic; decides nothing.
- Riders on the baseline arm's F10 rasters, which the baseline does not change: the R_3,
  R_1, size-matched-random and anti-selected feedback stores written from the same
  continuation spikes and read through the frozen readout (a fresh-seed replication of
  P2-R1's contrasts at no simulation cost; ruling 1 keeps R_3 reported). They are computed
  after the run from persisted evidence by a separate script and recorded as `rider`
  records; they never run on the candidate arm and are never stacked.
- Familiarity log: every episode with E'(x) empty is recorded with its family and index.
  The F10 and independent streams contain no exact repeats; no repeat, lure or re-exposure
  arm is run without an owner ruling.

## Evidence and records

Results append to `bench/results/p2e7.jsonl`; portable evidence under `bench/results/p2e7/`;
raw NPZ checkpoints and the attempt directory under `BRAINSIM_CACHE` (this PC:
`~/.cache/brain-sim/plant2-research-20261022/p2e7`). Every artifact is written through
`plant2.evidence.write_artifact` (exclusive create, fsync, readback, SHA-256), recorded in a
`Manifest`, and journaled per worker (`bench/results/p2e7/seed<seed>-<worker>.journal.jsonl`);
`Manifest.verify_all` and `verify_journal` run after the last stage and emit one
`evidence_verification` record per worker; a seed's screen is read only if every
verification passed. Record kinds: `seed_started`, `resource_window`, `load_started`, `load`,
`structural_kill`, `sanity_load`, `rider`, `evidence_verification`, `seed_screen`,
`gate_ready`, `gated_verdict`, `interrupted`. Each record carries the source manifest
(every pinned file's SHA-256, the inherited-baseline check against `55e16eb`), the git
commit, runtime versions, the contract commit, the attempt id and the predictions block.

## Resource stop and execution hygiene

Sixty wall minutes from the first process with a ten-minute grace (E6's window), at most
four simulation processes machine-wide, `OPENBLAS_NUM_THREADS=1`. Arms are independent
trajectories and may run in up to four workers; no new load starts after the window, an
in-flight load is checkpointed, and PARTIAL is retained with every missing stage listed. No
git command, commit, fetch, push or publication runs on this machine while a worker runs;
commits happen after all workers exit with verification records. The independent results
review follows before any held-out seed is opened.

## Tests required before any worker starts

`plant2/tests/test_p2_e7.py`, non-slow, must pass with the rest of the suite, and the safety
lint must show no new finding:

- the gate's G(x) equals `plant2.readout.replay`'s trace on the same small raster and store,
  bit for bit, including the inhibition delay;
- `gate_off` reproduces E3's forward store SHA-256 at small M, and so does the candidate when
  the feedback store is empty;
- exactly |E|·|A| coins are drawn every episode in E-major, A-minor order, and the candidate
  with an empty veto flips the same keys as `btsp_update`;
- V ⊆ E; the expected-flip identity 0.5·|E| = p·|E'| holds whenever p < 1; E' empty flips
  nothing and logs;
- `random_drop` and `history_drop` remove exactly |V| lines, from the named streams, with
  `history_drop` weights H_j + 1 and H updated only after the write;
- `label_oracle` vetoes exactly the retained prototype lines in E;
- there is no rec → mem path and no change to any memory-cell state from the gate;
- the seed guard refuses every seed but 121, and 122/131-135 without the committed
  prerequisites;
- artifacts go through `plant2/evidence.py` and the journal verifies;
- the blob check that every reused file equals its pinned baseline.

## What this cannot show

A pass is an index result on one development seed under a frozen screen; it is not a
capability until the gated seeds pass under their own frozen contract. Content at F10/1,000
is expected to stay below its bar whatever the index does (H-046); a pass closes the index
half of the correlated-items clause only. The mechanism keeps the random plateau key, the
episode boundaries, the write oracle and its timing, the verbatim feedback value, the input
code and the settled test regime; it removes only the selection half of eligibility. It adds
one declared protocol supply: the reconstruction population is now computed during learning,
which the P2-E3 protocol did not do. The F10 generator contains no exact repeats, so the rule's
behaviour on a re-exposed item (a familiarity-dependent write) is not tested and not claimed.

## Compliance notes

- Not an E6 retune: the candidate reads no history count, pseudocount or bisection; E6's
  counts appear only inside the `history_drop` control, and the E6 candidate is cited from
  the record as a comparator, never rerun.
- No teacher current: the prediction gates plasticity eligibility and injects nothing.
- The 50 ms index window is untouched; the 75 ms content window is reused as the prediction
  window, a reuse of the invariant, not a relaxation.
- Frozen deployed readout primary; the matched-silence grid is diagnostic only.
- One mechanism; the riders change no raster and score nothing.
- Family labels are read for scoring and the oracle comparator only.
- Frozen drivers, the recovered plant and every committed contract stay byte-identical; no
  deletion anywhere; failures are kept without rescue.

## Frozen JSON (draft content of `docs/plant2/P2-E7-frozen.json`)

```json
{"experiment": "P2-E7", "contract_commit": "<the freezing commit>",
 "contract_path": "docs/plant2/P2-E7-error-gated-eligibility.md",
 "source_baseline": "55e16ebff62a90d6402745f44fb860010741eba5",
 "mechanism": {"prediction_window_ticks": 75, "regeneration_rule": ">=1 rec spike in the window",
               "J_fb": 2.8, "g": 0.3, "budget_per_eligible": 0.5, "p_cap": 1.0},
 "streams": {"random_drop": 33, "history_drop": 34, "wrong_label_permutation": 35, "coin": 3, "plateau": 2},
 "loads": [500, 1000],
 "conditions": {"F10": {"F": 10, "s": 60}, "independent": null, "F40": {"F": 40, "s": 60}},
 "arms": ["baseline", "candidate", "random_drop", "history_drop", "gate_off", "no_conservation", "label_oracle", "assigned_A_teacher"],
 "independent_arms": ["baseline", "candidate"], "transfer_arms": ["baseline", "candidate"],
 "seeds": {"development": 121, "held_out": 122, "gated": [131, 132, 133, 134, 135]},
 "frozen": {"J_mem": 1.525, "acc_tau": 10000, "J_fb": 2.8, "g": 0.3, "window_mem": 50, "window_rec": 75, "settle": 50000},
 "bars": {"C1": 0.9, "C2": 0.9, "C3": 0.9, "C4_recall": 0.9, "C4_spurious": 0.9, "joint_index": 0.85},
 "margins": {"F10_C2_vs_baseline": 0.2, "F10_C2_vs_random": 0.1, "F10_C2_vs_history": 0.05, "F10_joint_vs_each": 0.1,
             "C1_nonregression": 0.03, "C4_recall_nonregression": 0.03, "independent_C2_nonregression": 0.03,
             "independent_content_joint_nonregression": 0.05, "independent_content_D4_nonregression": 0.05},
 "structural_kill": {"episodes": [501, 1000], "min_mean_V": 5, "min_veto_precision": 0.7,
                     "max_nonproto_predicted": 0.25, "min_proto_predicted": 0.25, "max_independent_veto_episode_fraction": 0.05},
 "protocol": {"eligibility_min": 0.95, "mean_A_1000": [18.5, 21.5], "drift_max_mv": 0.2},
 "sanity": {"wrong_label_C1_strict_upper": 0.1, "empty_store_responders": 0},
 "matched_silence": {"step_mv": 0.25, "max_mv": 5.0, "own50_tolerance": 1.0},
 "resource": {"wall_seconds": 3600, "grace_seconds": 600, "max_simulation_processes": 4},
 "predictions": {"F10_M1000_C2": [0.82, 0.97], "F10_M1000_C1_min": 0.91, "F10_M1000_joint": [0.75, 0.93],
                 "F10_M1000_C4_spurious": [0.70, 0.97], "F10_M1000_inherited_content": [0.02, 0.40],
                 "mean_V_501_1000_min": 20, "veto_precision_min": 0.8,
                 "independent_delta_max": 0.02, "most_likely_failure": "oldest-item specificity bar or late veto onset"}}
```
