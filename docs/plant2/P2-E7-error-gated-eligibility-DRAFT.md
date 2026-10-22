# P2-E7: prediction-gated (error-gated) forward eligibility with a conserved flip budget

Contract, 2026-10-22. The commit that adds `docs/plant2/P2-E7-error-gated-eligibility.md`
freezes it; append only thereafter. `docs/plant2/P2-E7-frozen.json` carries that commit's
SHA and the constants below. Drafts v1 (commit af04c89) and v2 (commit 64ff692) are
preparation provenance; two independent adversarial reads preceded this text (fifteen
findings on v1 including one restructure, then nine on v2, all addressed). The freezing
commit's follow-up appends the `EXPERIMENTS.md` entry (`contracted`) and moves H-060 to
`under_test`.

Selected at the 2026-10-22 roadmap checkpoint (`docs/research/ROADMAP.md`; `DECISIONS.md`
entry of the same day) from a ten-proposal judge panel, as the merged form of its two
top-ranked proposals. Owner authority: the error-correcting write family approved as a
research direction (ruling 4, 2026-10-10, `DECISIONS.md:435-443`) and the local-error signal
named for the forward index (ruling 3, 2026-10-12, `DECISIONS.md:786-788`). One mechanism,
no new ruling needed for the conditions run here, nothing retuned, index scored separately
from content.

## Question and hypotheses

Does a write rule that refuses to index the parts of an experience the network already
regenerates from its own memory, while holding the expected number of flips per plateau
cell at the baseline's wherever its probability cap allows, remove the forward-index
cross-talk on correlated items at the canonical load without costing recall of unrelated or
old items?

Hypotheses (`docs/research/HYPOTHESES.md`): **H-060** (primary; B-002 graduated). **H-055**
through ruling 4's two required tests: (i) does the feedback store supply useful error
information (the count-matched random-drop control, which fails if it does not); (ii) do
corrections preserve unrelated memories (the mixed-stream condition, where independent items
share one store with the corrected family items, scored on the independent subset; plus the
oldest cohort for old same-store items). By controls and predictions: H-035, H-041, H-043,
H-044, H-046.

## What is inherited unchanged

Everything the P2-E6 contract inherited from P2-E3 and P2-E5: `plant2/engine.py`,
`plant2/btsp.py`, `plant2/readout.py`, `plant2/record.py`, `plant2/experiments/p2_e1_btsp.py`
through `p2_e5_structured.py` (each must equal its blob at baseline `55e16eb`), and
`plant2/experiments/p2_e6.py`, `plant2/evidence.py`, `analysis/p2r1_replay.py` (each must
equal its blob at the freezing commit). The run-time source manifest records every pinned
file's SHA-256 and the comparison it passed. The `FamilyGen` generator (F = 10, s = 60:
exemplar index k + 1 for 0-based episode k, family (k + 1) mod 10, 40 retained prototype
lines), the independent generator, the E3 learner (J_mem 1.525 mV, accommodation tau
10,000 ms, 200 ms encoding at 40 Hz against 0.5 Hz, eligibility ≥ 3 input spikes, random
plateau sets at f_q 0.005 from stream 2, coins from stream 3, 50 ms continuation, responder
feedback write R × E, diagnostic plateau-set store A × E), the loads 500 and 1,000 as a deep
copy snapshot at 500 of one learning run to 1,000, the settled test protocol (deep copy, 50 s
settle, 100 oldest plus 100 random half cues, 200 novel half cues, 200 full cues, 100 ms cue
and 200 ms gap), the 50 ms index criteria (C1 recall ≥ 0.8 of A; C2 spurious < 0.5·|A|; C3;
C4 on the oldest 100; joint index), the frozen 75 ms content readout at J_fb 2.80 and g 0.3
with the joint criterion, the protocol validity checks (eligibility ≥ 0.95 of the item's
lines before any veto; mean |A| at 1,000 in [18.5, 21.5]; settle drift ≤ 0.2 mV), the sanity
checks (wrong-label raster permutation C1 < 0.10; never-trained empty store gives 0
responders), the small-configuration `uniform_integrity` check that the baseline equals E3
learning, and the bars and margins of `docs/plant2/P2-E6-frozen.json`: C1, C2, C3,
C4_recall, C4_spurious ≥ 0.90 and joint index ≥ 0.85 (feasibility bars); F10/1,000 C2 ≥
baseline + 0.20 and ≥ random + 0.10; joint index ≥ each + 0.10; C1 non-regression 0.03 at
F10 and independent, both loads; independent C2 non-regression 0.03; independent inherited
content joint and D4 non-regression 0.05. **Two declared additions** to E6's margins:
F10/1,000 C2 ≥ history_drop + 0.05, and C4_recall non-regression 0.03 at F10/1,000. E6's
per-arm `paired` records are replaced by the evidence manifest's completeness check; the
screen's PARTIAL accounting lists every missing (condition, arm, M) key.

The frozen deployed readout is primary. This contract contains no grid: the matched-silence
comparator proposed by the panel is not run (it would add a cross-worker dependency and a
threshold grid; H-067 already records the owner's advice against a threshold fix, and the
H-042 matched-state diagnostics below give the per-arm own/spurious comparison it was for).

## The mechanism (one mechanism: the veto and its conserved budget together)

It changes one thing in `E3.learn_one`: which eligible lines are toggled and with what
probability. The plateau draw, the encoding, the eligibility rule, the continuation, R(x),
the feedback write with the full E(x), the diagnostic plateau-set write and the test
protocol are untouched.

1. **Prediction during encoding.** The memory layer's spikes during ticks 0-74 of the
   encoding (counted from encoding onset; the memory layer was reset by `quiet()` as in E3)
   are played through the frozen readout `plant2.readout.replay` with exactly
   `n_ticks=75, window=75, short=50, span=75, J=[2.8], g=[0.3]`, the feedback store's CSR as
   it stands before this episode's write, and one cue at onset 0 whose `item`, `cue`,
   `missing` and `other_missing` are empty int64 arrays. The rec population starts at rest
   for every episode (unlike the test phase, where one rec run spans all cues). The predicted
   set G(x) is the set of lines appearing in `replay`'s `trace` with tick ≤ 74. `trace` is
   used in production by this driver, and a unit test checks it against an independent
   lockstep implementation (an `engine.LIF` rec population with a `Projection` from the
   feedback CSR at J_fb 2.80, delay 1, and `GlobalInhibition` at g·J_fb = 0.84 mV, delay 2)
   on the same raster and store. Nothing flows back: no rec → mem path, no current into any
   memory cell; the memory dynamics and every random stream are bit-identical to E3 given
   the same forward store.
2. **Veto.** V(x) = E(x) ∩ G(x); E'(x) = E(x) \ V(x).
3. **Conserved flip budget.** Coins are drawn exactly as `btsp_update` draws them
   (`plant2/btsp.py:68-69`): one flat array of |E|·|A| uniforms from stream 3, eligible-major,
   plateau-minor, none when either set is empty. Synapse (j, i) toggles iff j ∈ E'(x) and
   u_ji < p(x), with p(x) = min(1, 0.5·|E(x)| / |E'(x)|) when E'(x) is non-empty and p(x) := 0
   when it is empty (coins still drawn). The expected flips per plateau cell equal the
   baseline's 0.5·|E(x)| whenever p(x) < 1; when |V(x)| > |E(x)|/2 the cap binds, the
   episode is logged `p_capped`, and the shortfall is on the record. Under the toggle rule,
   conserving flips does not conserve potentiation (lines already at 1 are depressed with
   probability p); potentiated and depressed counts are recorded per arm. If V(x) is empty,
   p = 0.5 and the episode is bit-identical to E3 (0.5·n/n = 0.5 exactly). If E'(x) is empty,
   nothing toggles and the episode is logged as a familiarity event (see compliance).
4. **No new parameter.** The 75-tick window, J_fb, g, the ≥ 1-spike regeneration rule and
   the 0.5 budget factor are inherited constants; the cap at 1 is a probability bound. Nothing
   is calibrated; no seed is spent on calibration. The budget is a per-episode aggregate
   normalisation, the same labelled non-local circuit proxy P2-E6 carried; the candidate
   reads no history count, pseudocount or bisection. The veto and the conserved budget are
   declared together as the one mechanism under test; the `no_conservation` arm is reported
   and decides nothing.

Labelled proxy: mismatch- or novelty-gated plasticity in the comparator view of the
hippocampal circuit (plasticity on the direct input where the recall-driven prediction does
not already account for it; Lisman & Grace 2005; Hasselmo 2006). A circuit-level proxy, not
a claim about CA1 physiology.

## Conditions

| condition | generator | arms | purpose |
|---|---|---|---|
| `F10` | `FamilyGen(seed, 4000, 100, 60, 10)` | baseline, candidate, random_drop, history_drop, gate_off, no_conservation, label_oracle, assigned_A_teacher | the canonical hard condition (ruling 5); decides the screen |
| `independent` | the E1 independent generator | baseline, candidate | false engagement on uncorrelated input (the veto must stay near-silent) |
| `mixed` | a `MixedGen(seed, m, a, s, F)` generator with the same `choice(m, a, replace=False)` entry as `FamilyGen`: episode k (1-based) is the F10 exemplar `FamilyGen.exemplar((k + 1)/2)` when k is odd (family cycling as in `FamilyGen`) and, when k is even, the sorted draw `stream(seed, 36, k).choice(m, a, replace=False)` (one stream per episode, k 1-based); `subset(k)` returns the label and every episode's label is persisted | baseline, candidate | ruling 4 test (ii): do corrections on family items damage unrelated items in the same store; scored on the independent subset |
| `F40` | `FamilyGen(seed, 4000, 100, 60, 40)` | baseline, candidate | transfer diagnostic, reported only, never a rescue (ruling 5) |

Family labels and prototype membership are read by `label_oracle` and the scoring
diagnostics only; the candidate never reads them.

## Arms

| arm | rule | role |
|---|---|---|
| `baseline` | a literal `e3.E3` learner with the condition's generator and no gate code; it records items, A, E, R and its learned state only, and persists no gate fields, encoding rasters or continuation counts; its `matching` digest is formed from items, A and E plus H recomputed from E; its deep copies are tested through a test-time wrapper that adds only the onset-offset capture and the learning statistics E6's `evaluate_load` reads, changing no learning code (a unit test proves the wrapper's learning path gives the literal E3's forward store SHA at small M) | comparator; once the `gate_off` SHA check passes, `gate_off`'s persisted gate fields, encoding rasters and continuation counts stand for the baseline trajectory's, and the riders read them |
| `candidate` | the mechanism above | the deployed rule |
| `gate_off` | the candidate code path with G(x) computed every episode and ignored (p = 0.5 on E(x)); persists the gate fields | integrity: its forward-store SHA-256 must equal the baseline's at 500 and 1,000 (else INVALID); its persisted gate fields are the baseline trajectory's prediction time course |
| `random_drop` | drop exactly \|V_cand(k)\| lines from E(x), where V_cand(k) is the candidate's persisted, digest-verified per-episode veto count for episode k; chosen by `Generator.choice(len(E), count, replace=False)` on stream (seed, 33, k), k 1-based; p conserved on the reduced set as in the candidate | count-matched to the candidate (ruling 4 test (i)); fails if the error signal carries no information |
| `history_drop` | drop exactly \|V_cand(k)\| lines from E(x) by `Generator.choice(len(E), count, replace=False, p=(H+1)/sum(H+1))` on stream (seed, 34, k), where H_j is the number of previous episodes in which line j was eligible (E6's history, pseudocount 1, updated only after the write; H is identical across arms because E depends on input only); p conserved | separates a co-occurrence-sensitive prediction from a hot-line filter in disguise |
| `no_conservation` | candidate veto with p = 0.5 on E'(x) | reported only; decides nothing |
| `label_oracle` | V(x) = E(x) ∩ P(x), P(x) the item's 40 retained prototype lines from the generator; p conserved | diagnostic comparator only, never deployed |
| `assigned_A_teacher` | candidate rule with G(x) read from the arm's own diagnostic plateau-set store A × E (`fb_plateau`) instead of the responder store | reported only; splits "the error signal is informative" from "the responder-written teacher is too contaminated" |

Each arm's own-gate statistics are persisted as diagnostics whether or not the arm applies
them; the control arms therefore also record their own |V| beside the candidate's count they
matched.

## Execution order

1. **Stage 1.** The F10 `candidate` learns to 1,000 (deep-copy snapshot at 500), persisting
   per-episode gate fields and the 75-tick encoding raster, and emits its `structural_check`
   record. If any structural kill rule fires, a `structural_kill` record is emitted and the
   attempt ends: no other arm learns and no test phase runs.
2. **Stage 2.** Every other trajectory learns (up to four workers; the drop controls read the
   candidate's persisted veto counts after verifying their descriptor). The `mixed` and
   `independent` candidates emit their `structural_check`; the independent-veto kill rule is
   applied to both before stage 3. Every gated arm persists its gate fields, encoding
   rasters and continuation counts; the baseline persists items, A, E, R and its learned
   state. Learned states and the 500 snapshots are persisted as NPZ through
   `plant2/evidence.py` and reloaded, never kept only in worker memory.
3. **Stage 3.** A coordinator process starts the test phases only after it has read every
   stage-2 `structural_check` and found no kill; it also runs the cross-arm checks (the
   `matching` digests and the `gate_off`-equals-`baseline` `forward_sha256`) that E6 ran
   in-process. Test phases on every arm and load; `load` records; sanity loads on the F10
   candidate at 1,000; evidence verification; the screen.
4. **After the run**, from persisted evidence only: the riders (`analysis/p2e7_riders.py`,
   pinned at the freezing commit) and the independent results review.

## Seeds, streams and the seed guard

Seeds from the registry (`ROADMAP.md`; `DECISIONS.md` 2026-10-22): development **121**;
held-out **122**; gated **131-135**. The guard: any seed outside {121, 122, 131, 132, 133,
134, 135} is refused; a full-size attempt on any of these seeds is refused if the results file
already holds a `seed_started` record with `full_size` for that seed (one attempt per seed;
a rerun needs an explicit owner ruling); 122 opens only on a committed `seed_screen` with
verdict FEASIBILITY PASS on 121 whose source digest equals the running code's; 131-135 open
only on committed passing screens on 121 and 122 and a committed `gate_ready` record with the
same source digest and the frozen predictions; an INVALID screen on any of 121, 122 or
131-135 locks every remaining seed. Small integrity runs use seed 121 with explicit
non-production output paths, as E6's do.

Stream ids in use before this contract: 0-6, 8-18, 20-24, 30 (P2-R1 rider control stream,
consumed by the riders on seed 121), 31, 32, 40. New: 33 (random drop), 34 (history drop),
35 (this driver's wrong-label permutation), 36 (mixed-condition independent items). The gate
itself uses no randomness.

## Structural kill rules (before any test phase)

From the `structural_check` record's fields, computed over episodes 501-1,000 of the
condition named:

| rule | condition / arm | field | kill if |
|---|---|---|---|
| no engagement | F10 candidate | `gate.mean_V_501_1000` | < 5 |
| contamination-driven veto | F10 candidate | `gate.veto_precision_501_1000` (vetoed lines that are retained prototype lines, over vetoed lines; None if no vetoes, which the first rule already kills) | < 0.70 |
| saturated teacher | F10 candidate | `gate.nonproto_predicted_501_1000` (mean of \|G ∩ (E \ P)\| / \|E \ P\|) | > 0.25 |
| no structure | F10 candidate | `gate.proto_predicted_501_1000` (mean of \|G ∩ P ∩ E\| / \|P ∩ E\|) | < 0.25 |
| false engagement | independent candidate | `gate.veto_episode_fraction` (episodes with non-empty V) | > 0.05 |
| false engagement, mixed | mixed candidate | `gate.veto_episode_fraction_independent_subset` | > 0.05 |

A fired rule classifies the failure: no engagement or no structure, failed hypothesis as
stated; saturated teacher or contamination-driven veto, the H-055 evidence against stands
(the responder-written teacher is too contaminated); false engagement, failed hypothesis.

## Screen rules (development seed, after the test phases)

Decided by the driver's frozen `screen` from `load` records. KILL (FEASIBILITY FAIL; no
retuning; no held-out seed) if any of:

- F10/1,000 candidate `index.C2` < baseline + 0.20, or < random_drop + 0.10, or <
  history_drop + 0.05.
- F10/1,000 candidate `index.joint_index` < baseline + 0.10 or < random_drop + 0.10.
- Candidate `index.C1` below the same-condition baseline's by more than 0.03 at F10 and
  independent, both loads; F10/1,000 candidate `index.C4_recall` below the baseline's by
  more than 0.03.
- Independent candidate at 500 or 1,000: `index.C2` below the baseline's by more than 0.03;
  `content.inherited.joint` or `content.inherited.D4` below the baseline's by more than 0.05.
- Mixed candidate at 500 or 1,000, on the independent subset of the half cues (the same
  cues in both arms: exactly 50 of the 100 oldest cues and a binomial share, about 50, of
  the 100 random cues, so about 100 cues for C1, C2 and the joint index and 50 for the C4
  halves): `index_by_subset.independent.C1_count` or `.C2_count` below the baseline's by 4
  or more cues; `content_by_subset.independent.joint_count` below the baseline's by 5 or more
  cues. Expressed in cues because 0.03 of about 100 cues is three cues on one seed.
- Candidate `index.C3` < 0.90 at F10 or independent, either load (F40 is reported only).
- Any protocol validity check false on any arm of F10, independent or mixed; any sanity
  check failed.

FEASIBILITY PASS only if, in addition, every absolute bar holds on the candidate at F10 and
independent, both loads: C1, C2, C3, C4_recall, C4_spurious ≥ 0.90 and joint index ≥ 0.85.
A candidate F10/1,000 C2 in [0.70, 0.90) with no kill rule fired is an informative
FEASIBILITY FAIL. INVALID (numbers descriptive only; no replacement seed) if the gate_off
store differs from the baseline's at either checkpoint, if `uniform_integrity` fails, if any
evidence verification fails, if the resource window is overrun without a clean PARTIAL, or if
any `require` trips.

## Record fields (every prediction and rule reads one of these)

| record kind | key | definition |
|---|---|---|
| `structural_check` (one per gated arm and condition, after its learning; the literal baseline has none) | `gate.mean_V_1_500`, `gate.mean_V_501_1000` | mean \|V(x)\| over the episode range |
| | `gate.max_V` | maximum \|V(x)\| |
| | `gate.veto_precision_501_1000` | as above |
| | `gate.proto_predicted_501_1000`, `gate.nonproto_predicted_501_1000` | as above (F10 and the F10 subset of mixed; None for independent) |
| | `gate.veto_episode_fraction` | fraction of episodes with non-empty V |
| | `gate.veto_episode_fraction_independent_subset` | mixed condition only |
| | `gate.empty_Eprime_episodes` | list of episode indices with E' empty |
| | `gate.p_capped_episodes` | count of episodes with p = 1 |
| | `gate.first_engagement_by_family` | per family, the first episode with non-empty V (None if never) |
| | `gate.V_sequence` | descriptor of the persisted per-episode \|V\| array (read by the drop controls) |
| `load` (one per condition, arm, M) | `index.C1`, `index.C2`, `index.C3`, `index.C4_recall`, `index.C4_spurious`, `index.joint_index` | as E6 |
| | `index_by_subset.{F10,independent}.{C1,C2,C4_recall,C4_spurious,joint_index}` and the matching `*_count` and `n_cues`, `n_oldest_cues` | mixed condition only, recomputed from the per-cue rows over the half cues whose item belongs to the subset; C3 is not subset-scored (novel cues have no subset); a unit test proves the same recompute over the full cue set equals `out["criteria"]` and `e3.score` |
| | `content.inherited.{joint,D3,D4}`, `content.assigned_A.{joint,D3,D4}` | the responder store and the diagnostic A × E content store read at test (not the `assigned_A_teacher` arm) |
| | `content_by_subset.independent.joint` | mixed condition only |
| | `diagnostics.own50_mean`, `diagnostics.spurious50_mean`, `diagnostics.total50_mean` | means over half cues of the per-cue own50, spurious50, total50 |
| | `diagnostics.latency_split` | own and spurious first-spike medians and 10th/90th percentiles over half cues (B-008) |
| | `learning.forward_density`, `learning.max_prototype_out_degree` | forward keys over m·n; the maximum over the union of the condition's prototype lines of the number of forward keys with pre = j (None for independent) |
| | `learning.potentiated`, `learning.depressed` | sums over episodes |
| | `forward_sha256`, `feedback_sha256` | SHA-256 of the sorted key arrays |
| | `matching` | gated arms: digests of items, A, E, H, sensory and coins (identical across gated arms by construction; `candidate_counts` is not included because it differs by arm); the literal baseline: digests of items, A and E plus H recomputed from E, compared on those keys |
| | `protocol.{eligibility,mean_A_1000,settled}` | as E6 |
| `sanity_load` | `wrong_label.C1`, `empty_store.responders` | as E6 (stream 35 for the permutation) |
| `uniform_integrity` | `baseline_equals_e3` | the small-configuration check |
| `rider` | per rider store, the index and content summaries | reported only |

## Predictions (frozen before implementation; development seed 121)

Baselines: P2-E6 baseline arm, seed 101, exploratory (`RESULTS-P2-E6.md`); P2-R2b original
arm, seeds 105/106, reported-only (`RESULTS-P2-R2b.md:26-31`); P2-E5 gated seeds 21-25.

- **P1 (structural, F10 candidate `structural_check`).** `gate.mean_V_501_1000` ≥ 20;
  `gate.veto_precision_501_1000` ≥ 0.80; `gate.proto_predicted_501_1000` ≥ 0.50;
  `gate.nonproto_predicted_501_1000` ≤ 0.10.
- **P2.** F10/1,000 candidate `index.C2` in [0.82, 0.97] (point 0.90), against .500
  (exploratory), .485/.455 (reported-only), .435-.515 (gated).
- **P3.** F10/1,000 candidate `index.C1` ≥ 0.91 and `index.C4_recall` ≥ 0.90 (baselines
  .935/.940 exploratory; .925/.915 and .930/.930 reported-only).
- **P4.** F10/1,000 candidate `index.joint_index` in [0.75, 0.93] (.440 exploratory;
  .420/.390 reported-only).
- **P5.** F10/1,000 candidate `index.C4_spurious` in [0.70, 0.97], the weakest criterion
  (the oldest 100 items are the first ten per family, written before the veto engages;
  baseline .470 exploratory, .500/.420 reported-only). Most likely failure: this bar, or a
  late veto onset read in `gate.first_engagement_by_family`.
- **P6.** F10/1,000 candidate `content.inherited.joint` in [0.02, 0.40], still below 0.90
  (H-046); `content.assigned_A.joint` in [0.30, 0.60] (E6 candidate .425 exploratory).
- **P7.** Candidate `index.C3` ≥ 0.98 at F10 and independent, both loads.
- **P8.** F10/500 candidate: `index.C1` ≥ 0.93, `index.C2` ≥ 0.97, `index.joint_index` ≥
  0.90, `index.C4_recall` ≥ 0.94, `index.C4_spurious` ≥ 0.92, `content.inherited.joint` in
  [0.50, 0.97] (comparators: E6 candidate .785 exploratory; R2b null .960/.965 reported-only).
- **P9 (controls, F10/1,000).** `random_drop` `index.C2` ≤ 0.55; candidate `index.C2` ≥
  `history_drop` + 0.10; `label_oracle` `index.C2` ≥ candidate − 0.05; `no_conservation`
  `index.C1` ≤ candidate `index.C1`.
- **P10 (false engagement).** Independent candidate `structural_check`:
  `gate.veto_episode_fraction` ≤ 0.05 and `gate.max_V` ≤ 2; independent candidate `load` at
  500 and 1,000: every `index.*` measure and `content.inherited.joint` within ±0.02 of the
  baseline's; if `gate.veto_episode_fraction` = 0, candidate `forward_sha256` equals the
  baseline's.
- **P10b (unrelated memories, mixed).** Mixed candidate at 500 and 1,000:
  `index_by_subset.independent.{C1_count,C2_count,joint_index_count}` and
  `content_by_subset.independent.joint_count` within ±2 cues of the baseline's, and the
  C4 halves (`C4_recall_count`, `C4_spurious_count`, 50 cues) within ±1 cue; reported, not
  predicted as a bar: `index_by_subset.F10.C2` at 1,000 ≥ the baseline's F10-subset C2 + 0.10.
- **P11 (matched state, F10/1,000 candidate `load`).** `diagnostics.spurious50_mean` ≤ 6;
  `diagnostics.own50_mean` within ±1.0 of the baseline's; `learning.max_prototype_out_degree`
  ≤ 0.5 × the baseline's.
- **P12 (integrity).** `gate_off` `forward_sha256` equals `baseline` at 500 and 1,000;
  `uniform_integrity.baseline_equals_e3` true; `matching` digests identical across all gated
  F10 arms, and the baseline's items, A, E and recomputed-H digests equal theirs.

No prediction is revised after the run.

## Diagnostics and riders (reported only, never scored as outcomes)

- Per-episode, every arm, persisted once per checkpoint (not per episode) through
  `plant2/evidence.py`: |E|, |G|, |V|, p, p-capped flag, E'-empty flag, veto prototype
  fraction, prototype and non-prototype predicted fractions, subset label (mixed),
  continuation spike counts per memory cell, R(x), A(x), E(x), the 75-tick encoding raster,
  and the forward and feedback store sizes.
- H-042 matched-state diagnostics per arm and load: own50, spurious50, forward density,
  assigned-cell threshold offset at cue onset.
- The own-versus-spurious first-spike latency split on every arm's half cues (B-008).
- Riders on the baseline trajectory, computed after the run from persisted evidence by
  `analysis/p2e7_riders.py`: the R_3, R_1, size-matched-random and anti-selected feedback
  stores written from `gate_off`'s persisted per-episode continuation spike counts and read
  through the frozen readout on `gate_off`'s persisted test rasters (identical to the
  baseline's, because memory dynamics depend only on the forward store, which the SHA check
  proves equal; if that check fails the riders are void). A fresh-seed replication of
  P2-R1's contrasts at no simulation cost; stream 30 as in P2-R1; ruling 1 keeps R_3
  reported. They never run on the candidate arm and are never stacked.
- Familiarity log: `gate.empty_Eprime_episodes` with family and index.

## Evidence and records

Results append to `bench/results/p2e7.jsonl`; portable evidence under `bench/results/p2e7/`;
raw NPZ checkpoints and the attempt directory under `BRAINSIM_CACHE` (this PC:
`~/.cache/brain-sim/plant2-research-20261022/p2e7`). Every artifact is written through
`plant2.evidence.write_artifact` (exclusive create, fsync, readback, SHA-256), recorded in a
`Manifest`, and journaled per worker (`bench/results/p2e7/seed<seed>-<worker>.journal.jsonl`);
`Manifest.verify_all` and `verify_journal` run after the last stage and emit one
`evidence_verification` record per worker; the screen is read only if every verification
passed. Record kinds: `seed_started`, `resource_window`, `uniform_integrity`, `load_started`,
`structural_check`, `structural_kill`, `load`, `sanity_load`, `evidence_verification`,
`seed_screen`, `rider`, `gate_ready`, `gated_verdict`, `interrupted`. Each record carries the
source manifest, git commit, runtime versions, contract commit, attempt id and the
predictions block.

## Resource stop and execution hygiene

Sixty wall minutes from the first process with a ten-minute grace (E6's window), at most four
simulation processes machine-wide, `OPENBLAS_NUM_THREADS=1`. Estimate from E6's 608.64 s for
16 checkpoints on the takeover host (about 76 s per trajectory to 1,000 with both tests):
14 trajectories plus 14,000 75-tick replays, staged as above, well inside the window on four
workers. No new load starts after the window; an in-flight load is checkpointed; PARTIAL is
retained with every missing stage listed. No git command, commit, fetch, push or publication
runs on this machine while a worker runs; commits happen after all workers exit with
verification records. The independent results review follows before any held-out seed opens.

## Tests required before any worker starts

`plant2/tests/test_p2_e7.py`, non-slow, must pass with the rest of the suite, and the safety
lint must show no new finding:

- G(x) from `replay` with the pinned call equals an independent lockstep `engine.LIF`
  implementation's spiking lines on the same small raster and store, bit for bit, including
  the delays, and the pinned call raises nothing on a 75-tick raster;
- `gate_off` reproduces the literal E3 learner's forward store SHA-256 at small M, and so does
  the candidate with an empty feedback store;
- exactly |E|·|A| coins are drawn every episode, E-major, A-minor, and a candidate with an
  empty veto flips the same keys as `btsp_update`;
- V ⊆ E; 0.5·|E| = p·|E'| whenever p < 1; p = 1 is flagged; E' empty flips nothing and is
  logged;
- `random_drop` and `history_drop` remove exactly the candidate's persisted count per episode
  from the named streams with 1-based keys, `history_drop` with weights H + 1 and H updated
  only after the write; a tampered count artifact is refused by the digest check;
- `label_oracle` vetoes exactly the retained prototype lines in E;
- the mixed generator alternates subsets as specified, keys stream 36 per episode, and
  persists the labels; subset scoring partitions the half cues, and the same recompute over
  the full cue set equals `out["criteria"]` and `e3.score`;
- the baseline test-time wrapper's learning path gives the literal E3's forward store SHA at
  small M, and the baseline's `matching` (items, A, E, recomputed H) equals a gated arm's on
  those keys;
- no rec → mem path and no change to any memory-cell state from the gate;
- the seed guard refuses every seed outside the registry, a repeat full-size attempt on any
  registry seed, and 122/131-135 without the committed prerequisites;
- artifacts go through `plant2/evidence.py`, the journal verifies, and per-episode logs are
  written once per checkpoint;
- the blob check that every reused file equals its pinned blob.

## What this cannot show

A pass is an index result on one development seed under a frozen screen; it is not a
capability until the gated seeds pass under their own frozen contract. Content at F10/1,000
is expected to stay below its bar whatever the index does (H-046); a pass closes the index
half of the correlated-items clause only. The mechanism keeps the random plateau key, the
episode boundaries, the write oracle and its timing, the verbatim feedback value, the input
code and the settled test regime; it removes only the selection half of eligibility. It adds
one declared protocol supply: the reconstruction readout is now computed during learning,
which the P2-E3 protocol did not do. The mixed condition's F10 subset holds 50 exemplars per
family at M = 1,000, so its correction pressure is that of F10 at M = 500: ruling 4's test
(ii) is real but milder than the canonical load. **Scope of any pass: streams without exact
repeats.** On
an exact repeat the rule would suppress the whole forward write of the repeated item, which
is the familiarity-dependent allocation the owner deferred (ruling 4, 2026-10-10:
familiarity must not erase distinct episode identities); the F10, independent and mixed
streams contain no exact repeats, the behaviour on repeats is neither tested nor claimed, and
deploying the rule on streams with repeats requires an owner ruling on that deferral.

## Compliance notes

- Not an E6 retune: the candidate reads no history count, pseudocount or bisection; E6's
  counts appear only inside the `history_drop` control; the E6 candidate is cited from the
  record as a comparator, never rerun.
- No teacher current: the prediction gates plasticity eligibility and injects nothing.
- The 50 ms index window is untouched; the 75 ms content window is reused as the prediction
  window, a reuse of the invariant, not a relaxation.
- Frozen deployed readout primary; no grid in this contract.
- One mechanism (the veto with its conserved budget); the riders change no raster and score
  nothing; no second mechanism is stacked.
- Family labels are read for scoring and the oracle comparator only.
- Frozen drivers, the recovered plant and every committed contract stay byte-identical; no
  deletion anywhere; failures are kept without rescue.

## Frozen JSON (draft content of `docs/plant2/P2-E7-frozen.json`)

```json
{"experiment": "P2-E7", "contract_commit": "<the freezing commit>",
 "contract_path": "docs/plant2/P2-E7-error-gated-eligibility.md",
 "source_baseline": "55e16ebff62a90d6402745f44fb860010741eba5",
 "mechanism": {"prediction_window_ticks": 75, "replay_call": {"n_ticks": 75, "window": 75, "short": 50, "span": 75, "J": [2.8], "g": [0.3]},
               "regeneration_rule": ">=1 rec spike at tick <= 74", "budget_per_eligible": 0.5, "p_cap": 1.0, "p_when_Eprime_empty": 0.0},
 "streams": {"random_drop": 33, "history_drop": 34, "wrong_label_permutation": 35, "mixed_independent": 36, "episode_key": "1-based (streams 33, 34 and 36 are keyed (seed, id, k))", "coin": 3, "plateau": 2, "rider_control": 30},
 "loads": [500, 1000],
 "conditions": {"F10": {"F": 10, "s": 60}, "independent": null, "mixed": {"F": 10, "s": 60, "interleave": "odd F10, even independent"}, "F40": {"F": 40, "s": 60}},
 "arms": {"F10": ["baseline", "candidate", "random_drop", "history_drop", "gate_off", "no_conservation", "label_oracle", "assigned_A_teacher"],
          "independent": ["baseline", "candidate"], "mixed": ["baseline", "candidate"], "F40": ["baseline", "candidate"]},
 "stages": ["F10 candidate learns and structural_check", "other arms learn", "tests", "riders after the run"],
 "seeds": {"development": 121, "held_out": 122, "gated": [131, 132, 133, 134, 135]},
 "frozen": {"J_mem": 1.525, "acc_tau": 10000, "J_fb": 2.8, "g": 0.3, "window_mem": 50, "window_rec": 75, "settle": 50000},
 "bars": {"C1": 0.9, "C2": 0.9, "C3": 0.9, "C4_recall": 0.9, "C4_spurious": 0.9, "joint_index": 0.85},
 "margins": {"F10_C2_vs_baseline": 0.2, "F10_C2_vs_random": 0.1, "F10_C2_vs_history": 0.05, "F10_joint_vs_each": 0.1,
             "C1_nonregression": 0.03, "F10_M1000_C4_recall_nonregression": 0.03, "independent_C2_nonregression": 0.03,
             "independent_content_joint_nonregression": 0.05, "independent_content_D4_nonregression": 0.05,
             "mixed_independent_subset_index_nonregression_cues": 4, "mixed_independent_subset_content_nonregression_cues": 5},
 "structural_kill": {"episodes": [501, 1000], "min_mean_V": 5, "min_veto_precision": 0.7, "max_nonproto_predicted": 0.25,
                     "min_proto_predicted": 0.25, "max_veto_episode_fraction_uncorrelated": 0.05},
 "protocol": {"eligibility_min": 0.95, "mean_A_1000": [18.5, 21.5], "drift_max_mv": 0.2},
 "sanity": {"wrong_label_C1_strict_upper": 0.1, "empty_store_responders": 0},
 "resource": {"wall_seconds": 3600, "grace_seconds": 600, "max_simulation_processes": 4},
 "predictions": {"F10_M1000_C2": [0.82, 0.97], "F10_M1000_C1_min": 0.91, "F10_M1000_C4_recall_min": 0.90,
                 "F10_M1000_joint": [0.75, 0.93], "F10_M1000_C4_spurious": [0.70, 0.97],
                 "F10_M1000_inherited_content": [0.02, 0.40], "F10_M1000_assigned_A_content": [0.30, 0.60],
                 "mean_V_501_1000_min": 20, "veto_precision_min": 0.8, "proto_predicted_min": 0.5, "nonproto_predicted_max": 0.1,
                 "random_drop_C2_max": 0.55, "candidate_minus_history_min": 0.10,
                 "uncorrelated_delta_max": 0.02, "uncorrelated_veto_episode_fraction_max": 0.05, "uncorrelated_max_V": 2,
                 "mixed_independent_subset_delta_cues_max": 2, "mixed_independent_subset_C4_delta_cues_max": 1,
                 "spurious50_mean_max": 6, "own50_mean_tolerance": 1.0, "max_prototype_out_degree_ratio_max": 0.5,
                 "most_likely_failure": "oldest-item specificity bar or late veto onset"}}
```
