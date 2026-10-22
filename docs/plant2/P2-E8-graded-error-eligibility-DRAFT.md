# P2-E8: graded prediction-error weighting of the conserved flip budget — DRAFT v2

Draft contract, 2026-10-22, revision 2 after an independent adversarial read of revision 1
(twelve findings; the six blocking ones and the notes are addressed below). Not frozen. The
frozen text will be `docs/plant2/P2-E8-graded-error-eligibility.md` with
`docs/plant2/P2-E8-frozen.json`; the commit that adds them freezes them, appends the
`EXPERIMENTS.md` entry (`contracted`) and adds **H-086** to `HYPOTHESES.md` as `under_test`.
The frozen text carries full commit SHAs wherever this draft shows short ones.

Selected conditionally at roadmap checkpoint 2 (`docs/research/ROADMAP.md`, checkpoint 2,
sections 5 and 7; `DECISIONS.md` entry of 2026-10-22, decision 3) and authorised for drafting
by offline screen F (`docs/plant2/OFFLINE-SCREENS-20261022c.md`, Results: AUC 0.858 over
episodes 501-1,000; counterfactual graded/binary prototype-flip ratio 0.441 over 501-1,000
and 0.750 over 1-300; no kill fired). Owner authority: the error-correcting write family
(ruling 4, 2026-10-10) and the local-error signal for the forward index (ruling 3,
2026-10-12).

**Acceptance condition (owner question (f), `DECISIONS.md`).** Both judges of the
checkpoint-2 panel admitted a graded prediction-error weight as a different rule rather than
a rescue of P2-E7 only with four conditions: no new constant, the binary rule nested and run
as a same-seed comparator, a kill-only offline screen passed, and **explicit acceptance**.
The first three hold (screen F survived). The fourth is the owner's: **development seed 123
opens only when `docs/plant2/P2-E8-acceptance.json` exists, is committed, and records the
owner's yes to question (f)** (fields `question: "f"`, `accepted: true`, `by: "owner"`,
`date`, `source`: the `DECISIONS.md` entry that records the owner's words). "Committed"
means the HEAD blob equals the working file; the guard records the file's SHA-256 in
`seed_started` and the source manifest. Without it the contract can be frozen, implemented,
tested and rehearsed at small size, and no full-size seed is spent. This replaces revision 1's opt-out veto with the judges' opt-in. P2-E7's
verdict stands and seed 122 stays closed.

## Question and hypotheses

Does the subthreshold drive of the reconstruction units, read during encoding, carry the
prototype membership that the spike criterion of P2-E7 misses, and does weighting the
conserved flip budget by that residual error raise index specificity on correlated items at
the canonical load beyond the binary rule on the same seed, without costing recall of
unrelated or old items?

Hypotheses (`docs/research/HYPOTHESES.md`): **H-086** (new, primary: "graded reconstruction
error carries the prototype membership the spike criterion misses, and a budget weighted by
it reduces the forward-index leak beyond the binary veto"); H-060 (`mixed`) as its binary
form; H-055 through ruling 4's two tests (useful error information: graded_shuffled and
history_rank; unrelated memories preserved: independent and mixed arms); H-041, H-043, H-044
(co-occurrence against load: history_rank), H-042 (matched state), H-046 (content at 1,000).

## What is inherited, what is re-implemented

| imported unchanged from `plant2/experiments/p2_e7_error_gated.py` (pinned) | re-implemented in the P2-E8 driver with the same semantics |
|---|---|
| `E7` (the `binary` arm is an `E7(arm="candidate")` instance: the learner keeps `arm = "candidate"` in its own state and artifacts, and the P2-E8 driver maps it to `binary` in every record and in `screen`; `label_oracle` is `E7(arm="label_oracle")`), `Baseline`, `wrap_for_test`, `MixedGen`, `predict_set`, `structural_fields` and `structural_kills` (called for P2-E7's four fields and rules), the `snapshot` of learner states, `evaluate_load`, the evidence sink and journal pattern | the graded class's `__init__` and `learn_one` (new arm names; the per-line p is a vector, not E7's scalar), `restore` (E7's builds `E7(arm=...)` and rejects P2-E8's arm names), `graded_structural_fields` (E7's fields plus the new window means) and `graded_structural_kills` (E7's rules plus the three below), `screen` (P2-E8's rules, margins and bands; E7's hard-codes its own arms), `sanity_loads` (stream 38, on the graded arm), `cross_arm` (P2-E8's arms), `uniform_integrity` (also runs P2-E8's `gate_off` and an empty-store graded learner against E3, so P12 and the INVALID rule are exercised), `seed_guard` (P2-E8's registry, prerequisites and the acceptance file; E7's would refuse 123), `run_seed` and `learn_worker` (P2-E8's arms and stage rules; no drop controls, no `V_sequence` passing; stage-1 kills on the graded arm), `source_manifest` (P2-E8's pin groups) |

Absent by design: P2-E7's `random_drop`, `history_drop`, `no_conservation`,
`assigned_A_teacher` arms and the candidate-count artifact they read. P2-E7's seed guard is
never called; P2-E7's registry and one-attempt rule are untouched because P2-E8 writes
`bench/results/p2e8.jsonl`.

Pins (the run's source manifest records every comparison; the frozen text names full SHAs):
the E3-era files at 55e16eb; `p2_e6.py`, `evidence.py`, `p2r1_replay.py` at fede3c2;
`plant2/experiments/p2_e7_error_gated.py` and `analysis/p2e7_riders.py` at 9bc6cf3 (the
riders blob still carries P2-E7 erratum 12, which the P2-E8 rider wrapper fixes, see below);
the P2-E7 contract append-only at fede3c2; the P2-E7 frozen JSON at e38a6b0;
`analysis/offline_screens_20261022.py` at 9cf822d (the reference implementations
`lockstep_rec`, `water_fill`, `counterfactual_p`, `surplus_only_p`, `spurious_classes`);
this contract append-only at its freezing commit; `docs/plant2/P2-E8-frozen.json` at the
commit that adds it; the P2-E8 driver, its tests and `analysis/p2e8_riders.py` as a `self`
group pinned to the commit that adds them (named in a pre-run note, as P2-E7 note 5 did).

Everything else is as P2-E7: conditions (`F10`, `independent`, `mixed` with `MixedGen` on
stream 36, `F40` reported only), the frozen constants, E6's bars and margins with P2-E7's two
additions, the mixed cue-count margins, the structural fields, the record kinds and the
evidence discipline, the resource window, the riders' store definitions. No bar, margin,
window, constant or protocol changes.

## The mechanism (one mechanism: the graded weight with its conserved budget)

It changes one thing in the P2-E7 candidate's `learn_one`: the per-line flip probability.
Everything else is P2-E7 verbatim.

1. **Prediction with drive.** The 75-tick encoding raster is played through a lockstep
   reconstruction LIF population bit-identical to `plant2.readout.replay` under the frozen
   constants (tau_m 20, v_rest −70, v_th −50, v_reset −65, t_ref 2, float32; J_fb 2.80 at
   delay 1 from the feedback store as it stands before this episode's write; global
   inhibition g·J_fb = 0.84 mV per memory spike at delay 2; rec at rest at tick 0). Its spike
   set G(x) must equal P2-E7's `predict_set` output on every episode (asserted; INVALID
   otherwise). For every eligible line j it also yields d_j = max(0, peak over ticks 0-74 of
   (v_j − v_rest)) read after input integration and before any threshold reset
   (`lockstep_rec` is the reference implementation; its test against `replay`'s trace is
   reused). A line spikes iff d_j ≥ 20 mV, so w_j = 0 ⇔ j ∈ G and E′ empty ⇔ E ⊆ G.
2. **Residual error weight.** w_j = 0 if j ∈ G(x); otherwise w_j = 1 − clip(d_j / 20 mV,
   0, 1), with 20 mV = v_th − v_rest of the frozen rec layer.
3. **Conserved budget, graded.** p_j = min(1, λ·w_j) for j ∈ E(x), with λ the exact
   water-filling solution of Σ_{j∈E} p_j = 0.5·|E(x)| (sorted search, no tolerance, no
   randomness; `water_fill`). **Cap:** `p_capped` is logged when 0 < #(w > 0) ≤ 0.5·|E|
   (then every positive-w line gets p = 1; the budget is met exactly at equality and not met
   below it; E7's `p == 1` semantics); `n_p_eq_1` (lines with p = 1 from a high w on an
   episode that is not capped) is logged separately. When every w is 0, nothing toggles and
   the episode is logged `Eprime_empty` (and not `p_capped`).
4. **Coins.** Drawn exactly as `btsp_update` draws them: one flat |E|·|A| array from stream 3,
   E-major, A-minor, none when either set is empty; synapse (j, i) toggles iff u_ji < p_j.
5. **Identity.** With an empty feedback store every d_j = 0, so w = 1, λ = 0.5 exactly and
   the episode is bit-identical to E3 (float32 rest is a fixed point of the lockstep). With
   w ∈ {0, 1} only, `water_fill` computes 0.5·|E|/|E′| in E7's operation order and the rule
   equals P2-E7's binary rule exactly; the lockstep draws no RNG, so `gate_off` equals E7's
   gate_off and E3.
6. **No new constant.** The 75-tick window, J_fb, g, the rec LIF constants, the 0.5 budget
   and the cap at 1 are inherited and frozen; the normaliser 20 mV is the frozen rec
   threshold gap; peak drive (not time-averaged) is predeclared and not selectable. The
   water-filling is the same labelled non-local aggregate proxy as E6's and E7's budget.

Labelled proxy: graded mismatch- or prediction-error-scaled plasticity in the comparator view
of the hippocampal circuit (Lisman & Grace 2005; Hasselmo 2006): plasticity on a direct input
line scaled by how far the recall-driven reconstruction of that line falls short of firing.
A circuit-level proxy, not a claim about CA1 physiology.

What differs from frozen P2-E7, and why this is a new hypothesis rather than a rescue: P2-E7
redistributes the vetoed budget uniformly over E′; this rule redistributes it in proportion to
the residual error 1 − d_j/20 and vetoes exactly the lines P2-E7 vetoes. No P2-E7 constant is
changed, loosened or re-chosen; the binary rule is nested (w ∈ {0, 1}) and runs on the same
seed as the comparator the screen must beat; the hypothesis was falsifiable without a seed
and survived a screen that could only kill; and the owner's explicit acceptance is required
before a seed is spent.

## Conditions and arms (fourteen trajectories, as P2-E7)

| arm | condition(s) | rule | role |
|---|---|---|---|
| `baseline` | F10, independent, mixed, F40 | literal E3 (P2-E7's `Baseline` and test-time wrapper) | comparator; anchors gate_off |
| `binary` | F10 | `E7(arm="candidate")` imported unchanged, relabelled | the decisive same-seed comparator (on independent inputs it was identical to the baseline on seed 121; on mixed inputs P10b compares with the baseline) |
| `graded` | F10, independent, mixed, F40 | the mechanism above | the deployed rule |
| `gate_off` | F10 | the graded code path with p = 0.5 uniform on E (lockstep run, G and d computed and ignored); persists the gate fields | integrity: forward SHA-256 must equal the baseline's at 500 and 1,000, else INVALID |
| `graded_shuffled` | F10 | the arm's own lockstep gives w over E; with E′ in ascending line order and π = `stream(seed, 37, k).permutation(|E′|)`, k 1-based, w′[E′[i]] = w[E′[π[i]]], then the same water-filling (the multiset of p is preserved bit-exactly, since `water_fill` depends only on the sorted w) | fails if line-specific drive carries no information beyond the shape of the distribution |
| `history_rank` | F10 | the arm's own w multiset over E′ assigned in order of E7's eligibility count H (updated after the write): the most-used line gets the smallest w, ties broken by the lower line id taking the smaller w; then the same water-filling | fails if the graded weights are a hot-line or load marginal in disguise |
| `label_oracle` | F10 | P2-E7's oracle (`E7(arm="label_oracle")`) | diagnostic ceiling, never deployed |
| `surplus_only` | F10 | p = 0.5 on E′ plus the vetoed surplus 0.5·\|G ∩ E\| distributed over E′ in proportion to w, capped at 1 (`surplus_only_p`) | reported only; decides nothing (screen F: nearly inert) |

No control reads another arm's artifact. `binary` and `label_oracle` are unchanged E7
instances: they run `predict_set`, not the lockstep, and carry only P2-E7's fields. Every
arm of the graded class (graded, gate_off, graded_shuffled, history_rank, surplus_only, and
graded on the other conditions) carries P2-E7's per-episode fields plus: `expected_proto_flips` (Σ p over P ∩ E, P read at log time only),
`expected_nonproto_flips`, **`expected_proto_flips_binary_cf`** (Σ p over P ∩ E under
`counterfactual_p(E, G, d, "binary")` on the same episode: the within-arm counterfactual
screen F used), `w_mean_proto_unpredicted`, `w_mean_nonproto_unpredicted`,
`tv_mean_abs_dev_from_half` (mean over E of |p − 0.5|; screen F's `tv_definition`),
`lambda`, `p_capped`, `n_p_eq_1`, `Eprime_empty`; per-episode d over E is persisted once per
checkpoint through `plant2/evidence.py`.

## Execution order, seeds, streams, seed guard

As P2-E7: stage 1 the F10 `graded` arm learns first and is kill-checked before any test
phase (its own rules are within-arm, so no other arm is needed); stage 2 the other
trajectories (up to four workers), after which the coordinator applies the independent and
mixed rules from their persisted `structural_check` records, using the stage-1 F10 graded
value as the reference, before any test phase; stage 3 the coordinator (cross-arm `matching` and
gate_off-equals-baseline checks, tests from persisted states, sanity loads with stream 38,
verification, screen). After the run, `analysis/p2e8_riders.py` (new; a wrapper that calls
`analysis/p2e7_riders.py`'s store builders and readout with its own `meta`, fixing P2-E7
erratum 12) appends the riders on gate_off's persisted counts and the screen-E classes of
every F10 arm computed with `spurious_classes` from the pinned offline module on the P2-E8
evidence (`rider` and `screen_e_classes` records; reported only).

Seeds (`DECISIONS.md` 2026-10-22, checkpoint 2, decision 4): development **123**; held-out
**124** (opens only on a committed FEASIBILITY PASS on 123 with the exact source digest);
gated **151-155** (committed passes on 123 and 124 plus a `gate_ready` record, under a
separately frozen gate contract). The guard refuses every other seed, a repeat full-size
attempt on any registry seed, and any full-size seed while `docs/plant2/P2-E8-acceptance.json`
is absent or uncommitted; an INVALID screen locks the rest. Small runs use seed 123 with
explicit non-production paths and need no acceptance file. New stream ids: 37
(graded_shuffled), 38 (this driver's wrong-label permutation). In use before: 0-6, 8-18,
20-24, 30-36, 40. The graded weight uses no randomness.

## Structural kill rules (before any test phase)

P2-E7's four rules on the F10 `graded` arm over episodes 501-1,000 (no engagement: mean
|V| < 5; contamination-driven veto: precision < 0.70; saturated teacher: non-prototype
predicted > 0.25; no structure: prototype predicted < 0.25; the veto is G ∩ E as in P2-E7),
plus:

| rule | arm | field | kill if |
|---|---|---|---|
| no graded reduction | F10 graded | the ratio of window means `gate.expected_proto_flips_501_1000` / `gate.expected_proto_flips_binary_cf_501_1000` (same arm, same episodes; graded-actual over binary-counterfactual on the graded trajectory, the same form screen F measured as 0.441 on the binary trajectory, a different state) | > 0.6, or a zero denominator |
| independent perturbation | independent graded | `gate.tv_mean_501_1000` against the F10 graded arm's `gate.tv_mean_1_300` (both from this run's own trajectories; seed-121 margin 0.029 against 0.161) | greater |
| false engagement | independent graded; mixed graded | `gate.veto_episode_fraction_501_1000`; `..._independent_subset_501_1000` | > 0.05 (as P2-E7) |

The `binary` arm's own expected prototype flips are reported beside the within-arm
counterfactual (its G rebuilt by the lockstep from its persisted R and E sequence, as
`screen_f` does; E7 persists only G_size and V_size) and decide nothing.

## Screen rules (development seed, after the test phases)

E6's bars and margins with P2-E7's additions, on the `graded` arm, plus the graded
comparisons. KILL (FEASIBILITY FAIL; no retuning; no held-out seed) if any of:

- F10/1,000 graded `index.C2` < baseline + 0.20, or < binary + 0.05, or < graded_shuffled
  + 0.05, or < history_rank + 0.05.
- F10/1,000 graded `index.joint_index` < baseline + 0.10 or < binary + 0.03.
- Graded `index.C1` below the same-condition baseline's by more than 0.03 at F10 and
  independent, both loads; F10/1,000 graded `index.C4_recall` below the baseline's by more
  than 0.03.
- Independent graded at 500 or 1,000: `index.C2` below the baseline's by more than 0.03;
  `content.inherited.joint` or `.D4` below the baseline's by more than 0.05.
- Mixed graded at 500 or 1,000: independent-subset `C1_count` or `C2_count` below the
  baseline's by 4 or more cues; `content_by_subset.independent.joint_count` below by 5 or
  more cues.
- Graded `index.C3` < 0.90 at F10 or independent, either load.
- Any protocol validity check false on any F10, independent or mixed arm; any sanity check
  failed.

FEASIBILITY PASS only if, in addition, every absolute bar holds on the graded arm at F10 and
independent, both loads (C1, C2, C3, C4_recall, C4_spurious ≥ 0.90; joint index ≥ 0.85).
"No kill fired" means no structural rule and no screen KILL rule fired. **Outcome bands for
the decisive delta** ΔC2 = graded − binary at F10/1,000:

| outcome | screen outcome | H-086 |
|---|---|---|
| ΔC2 ≥ +0.05, bars met, no kill fired | FEASIBILITY PASS | supported on one development seed |
| ΔC2 ≥ +0.05, bars not met, no kill fired | FEASIBILITY FAIL, `informative` | supported on the delta; the ramp floor established |
| ΔC2 ≥ +0.05 and another KILL rule fired | FEASIBILITY FAIL | per the rule: a control kill (shuffled or history_rank within 0.05) means the drive is not line-specific or is a load marginal, which refutes H-086's "beyond the binary veto" clause; a non-regression or C3 kill leaves H-086 supported on the delta and the rule rejected on its cost |
| ΔC2 in [+0.02, +0.05) | FEASIBILITY FAIL (the +0.05 kill fires) | weakened, not refuted |
| ΔC2 < +0.02 | FEASIBILITY FAIL | refuted |
| a structural kill fired (ΔC2 never measured) | FEASIBILITY FAIL, `structural_kill` recorded | "no graded reduction" refutes H-086; the other rules classify as in P2-E7 |
| ΔC2 missing (an arm absent) | INVALID or PARTIAL as P2-E7 | undecided |

INVALID as P2-E7 (gate_off store differs from the baseline's; the lockstep spike set
differs from `predict_set` on any episode; `uniform_integrity` false; an evidence
verification fails; the window overrun without a clean PARTIAL; a `require` trips).

## Predictions (to be frozen before implementation)

Provenance labels: "screen" means a recorded value from screens F or E′; "extrapolation"
means the orchestrator's arithmetic on recorded values, exploratory; a prediction without a
label is an extrapolation. Baselines are the
P2-E7 seed-121 values (exploratory); the same-seed `binary` arm on seed 123 is the
comparator for every delta.

- **P1 (structural, F10 graded `structural_check`).** `gate.expected_proto_flips_501_1000` /
  `gate.expected_proto_flips_binary_cf_501_1000` ≤ 0.6 (screen: 0.441 as a same-state
  counterfactual on seed 121); P2-E7's four fields inside their kill envelope;
  `gate.mean_V_501_1000` within ±10 of binary's (the veto itself is unchanged).
- **P2.** F10/1,000 graded `index.C2` in [0.76, 0.88], point 0.81 (extrapolation: binary
  .745 on seed 121 plus a modest gain; E′ puts about 90 % of the residual in the onset ramp,
  where screen F's counterfactual removes a quarter of the expected missed-prototype
  flips); ΔC2 against binary in [+0.02, +0.10], point +0.06 (extrapolation). The most likely
  outcome is a second informative FEASIBILITY FAIL that establishes the ramp as the family's
  limit.
- **P3.** F10/1,000 graded `index.C1` ≥ binary − 0.02 and ≥ 0.88; `index.C4_recall` ≥ 0.90.
- **P4.** F10/1,000 graded `index.joint_index` ≥ binary + 0.03.
- **P5.** F10/1,000 graded `index.C4_spurious` ≥ binary + 0.03 (the oldest 100 items are the
  first ten per family, inside the ramp; the smallest expected gain; extrapolation).
- **P6.** F10/1,000 graded `content.inherited.joint` ≤ 0.10 (H-046 holds); `content.assigned_A.joint`
  in [0.20, 0.50].
- **P7.** Graded `index.C3` ≥ 0.98 at F10 and independent, both loads.
- **P8.** F10/500 graded: C1 ≥ 0.93, C2 ≥ 0.96, joint ≥ 0.90, C4_recall ≥ 0.94,
  C4_spurious ≥ 0.92; `content.inherited.joint` ≥ binary's at 500.
- **P9 (controls, F10/1,000).** graded ≥ graded_shuffled + 0.05 and ≥ history_rank + 0.05
  on C2; label_oracle ≥ graded − 0.05; surplus_only within ±0.03 of binary on C2 (screen F:
  nearly inert, 8.45 against 8.72 expected prototype flips per cell on the candidate
  trajectory).
- **P10 (independent).** Graded at 500 and 1,000: every `index.*` within ±0.03 of the
  baseline's and `content.inherited.joint` within ±0.05; `gate.veto_episode_fraction` = 0;
  `gate.tv_mean_501_1000` ≤ the F10 graded arm's `gate.tv_mean_1_300` (screen: 0.029 against
  0.161 on seed 121); the forward SHA-256 is **not** expected to equal the baseline's (w < 1
  on chance-driven lines).
- **P10b (mixed).** Independent-subset counts within ±3 cues of the baseline's on C1, C2 and
  joint, content joint not more than 4 cues lower; F10-subset C2 ≥ the baseline's F10-subset
  C2 + 0.10.
- **P11 (matched state).** `diagnostics.spurious50_mean` ≤ 0.85 × binary's; `own50_mean`
  within ±1.0 of the baseline's; `learning.max_prototype_out_degree` ≤ 0.9 × binary's
  (extrapolations).
- **P12 (integrity).** gate_off `forward_sha256` equals baseline at both loads; the lockstep
  spike set equals `predict_set` on every episode of every arm of the graded class;
  `uniform_integrity` true (including P2-E8's gate_off and the empty-store graded learner
  against E3); `matching` identical across gated F10 arms (items, A, E, H, sensory, coins).
- **P13 (screen-E classes on seed 123, `screen_e_classes` records from `analysis/p2e8_riders.py`).**
  Graded late class ≤ 0.85 × binary's; early class ≤ 0.9 × binary's; other-family class
  within ±0.3 per cue (extrapolations).

No prediction is revised after the run.

## Diagnostics, riders, evidence, resource, hygiene

As P2-E7 (per-episode logs once per checkpoint, H-042 diagnostics, latency split, riders on
gate_off, familiarity log, `bench/results/p2e8.jsonl` and `bench/results/p2e8/`, cache root
`~/.cache/brain-sim/plant2-research-20261022/p2e8`, per-worker journals, 3,600 s window,
four processes, `OPENBLAS_NUM_THREADS=1` recorded, no git during the window, independent
results review before any held-out seed). Record kinds and fields as P2-E7's table plus the
gate fields named above, with `structural_check` carrying their 1-300 and 501-1,000 means
(`gate.expected_proto_flips_1_300`, `..._501_1000`, `gate.expected_proto_flips_binary_cf_1_300`,
`..._501_1000`, `gate.tv_mean_1_300`, `gate.tv_mean_501_1000`, `gate.lambda_mean`,
`gate.p_capped_episodes`, `gate.n_p_eq_1_episodes`). **Feasibility note required before the
run:** a timing record from a small-M three-stage rehearsal and from the lockstep on 1,000
persisted episodes (screen F ran two arms' 1,000-episode locksteps in about 95 s), appended
as a pre-run note with the estimate for fourteen trajectories, eight of them with the
lockstep, inside the 3,600 s window on four workers.

## Tests required before any worker starts

`plant2/tests/test_p2_e8.py`, non-slow, with the rest of the suite green and the safety
lint showing no new finding: the lockstep spike set equals `predict_set` and `replay`'s
trace, and d_j is read before reset (reuse of the screen-F test with the driver's function);
empty store gives w = 1, p = 0.5 and E3's forward SHA; w ∈ {0, 1} reproduces the binary
rule's flips exactly; gate_off equals the baseline's SHA at small M; Σp = 0.5|E| whenever
uncapped and `p_capped` / `n_p_eq_1` are set as defined; spiking lines get p = 0; exactly
|E|·|A| coins; the shuffled and history-rank arms preserve the multiset of p bit-exactly,
with history_rank deterministic (tie rule) and H updated after the write; surplus_only's p;
`expected_proto_flips_binary_cf` equals `counterfactual_p(..., "binary")` on the same
episode; no rec → mem path; the seed guard refuses every seed outside {123, 124, 151-155},
a repeat full-size attempt, 124 / 151-155 without the committed prerequisites, and any
full-size seed without the committed acceptance file; artifacts through `plant2/evidence.py`;
the blob pins (every group above).

## What this cannot show

A pass is an index result on one development seed under a frozen screen; it is not a
capability. Content at F10/1,000 stays below its bar (H-046). The ramp floor is expected to
bound the gain; a second informative fail is the likeliest outcome and is itself the result
this contract is for. The rule keeps the random plateau key, episode boundaries, the write
oracle and its timing, the verbatim value and the test regime; it removes the same sliver as
P2-E7 (the selection half of eligibility, now graded) and adds no supply beyond P2-E7's
declared one (the reconstruction readout computed during learning; it now reads that
population's membrane, not only its spikes). Exact repeats are out of scope (familiarity
deferral). It changes writes on veto-free episodes, unlike P2-E7, so independent
non-regression is a live test, not a formality.

## Compliance notes

Not a retune: no P2-E7 constant changes; the binary rule is nested and runs on the same seed;
the screen could only kill and survived; a fresh seed; the owner's explicit acceptance gates
the seed; P2-E7's verdict stands. One mechanism; surplus_only and the riders decide nothing
and stack nothing. Family labels at scoring and in the oracle only. Frozen readout primary;
no grid. The 50 ms and 75 ms windows, F = 10 canonical, no LLM, no teacher current (the
drive gates plasticity and injects nothing). Frozen drivers byte-identical; no deletion;
failures kept without rescue.

## Frozen JSON (draft content of `docs/plant2/P2-E8-frozen.json`; full SHAs at freeze)

```json
{"experiment": "P2-E8", "contract_commit": "<the freezing commit>",
 "contract_path": "docs/plant2/P2-E8-graded-error-eligibility.md",
 "acceptance_path": "docs/plant2/P2-E8-acceptance.json",
 "source_baseline": "55e16ebff62a90d6402745f44fb860010741eba5",
 "pins": {"e3_era": "55e16ebff62a90d6402745f44fb860010741eba5", "contract_group": "fede3c249dad7ba6237bcedcbfe498e253c3de39",
          "p2_e7_driver_and_riders": "9bc6cf309a5472b19c889cd16444833e0d3acedb", "p2_e7_contract_append_only": "fede3c249dad7ba6237bcedcbfe498e253c3de39",
          "p2_e7_frozen_json": "<full SHA of e38a6b0>", "offline_screens": "<full SHA of 9cf822d>", "p2_e8_frozen_json": "<the commit that adds it>", "self": "<the commit that adds the driver, tests and riders>"},
 "mechanism": {"prediction_window_ticks": 75, "drive": "max(0, peak (v - v_rest) over ticks 0-74 after integration before reset)", "normaliser_mv": 20.0,
               "weight": "0 if spiked else 1 - clip(d/20, 0, 1)", "budget_per_eligible": 0.5, "p_cap": 1.0, "water_filling": "exact sorted search",
               "p_capped": "lines with w > 0 at most 0.5*|E|", "p_when_all_w_zero": 0.0},
 "streams": {"graded_shuffled": 37, "wrong_label_permutation": 38, "mixed_independent": 36, "episode_key": "1-based", "coin": 3, "plateau": 2, "rider_control": 30},
 "loads": [500, 1000],
 "conditions": {"F10": {"F": 10, "s": 60}, "independent": null, "mixed": {"F": 10, "s": 60, "interleave": "odd F10, even independent"}, "F40": {"F": 40, "s": 60}},
 "arms": {"F10": ["baseline", "binary", "graded", "gate_off", "graded_shuffled", "history_rank", "label_oracle", "surplus_only"],
          "independent": ["baseline", "graded"], "mixed": ["baseline", "graded"], "F40": ["baseline", "graded"]},
 "seeds": {"development": 123, "held_out": 124, "gated": [151, 152, 153, 154, 155]},
 "frozen": {"J_mem": 1.525, "acc_tau": 10000, "J_fb": 2.8, "g": 0.3, "window_mem": 50, "window_rec": 75, "settle": 50000},
 "bars": {"C1": 0.9, "C2": 0.9, "C3": 0.9, "C4_recall": 0.9, "C4_spurious": 0.9, "joint_index": 0.85},
 "margins": {"F10_C2_vs_baseline": 0.2, "F10_C2_vs_binary": 0.05, "F10_C2_vs_shuffled": 0.05, "F10_C2_vs_history_rank": 0.05,
             "F10_joint_vs_baseline": 0.1, "F10_joint_vs_binary": 0.03, "C1_nonregression": 0.03, "F10_M1000_C4_recall_nonregression": 0.03,
             "independent_C2_nonregression": 0.03, "independent_content_joint_nonregression": 0.05, "independent_content_D4_nonregression": 0.05,
             "mixed_independent_subset_index_nonregression_cues": 4, "mixed_independent_subset_content_nonregression_cues": 5},
 "delta_bands": {"refuted_below": 0.02, "kill_below": 0.05},
 "structural_kill": {"episodes": [501, 1000], "min_mean_V": 5, "min_veto_precision": 0.7, "max_nonproto_predicted": 0.25, "min_proto_predicted": 0.25,
                     "max_within_arm_graded_over_binary_cf": 0.6, "independent_tv_max": "F10 graded gate.tv_mean_1_300 of this run", "max_veto_episode_fraction_uncorrelated": 0.05},
 "protocol": {"eligibility_min": 0.95, "mean_A_1000": [18.5, 21.5], "drift_max_mv": 0.2},
 "sanity": {"wrong_label_C1_strict_upper": 0.1, "empty_store_responders": 0},
 "resource": {"wall_seconds": 3600, "grace_seconds": 600, "max_simulation_processes": 4},
 "predictions": {"F10_M1000_C2": [0.76, 0.88], "F10_M1000_delta_C2_vs_binary": [0.02, 0.10], "F10_M1000_C1_min": 0.88, "F10_M1000_C4_recall_min": 0.90,
                 "F10_M1000_joint_delta_vs_binary_min": 0.03, "F10_M1000_C4_spurious_delta_vs_binary_min": 0.03,
                 "F10_M1000_inherited_content_max": 0.10, "F10_M1000_assigned_A_content": [0.20, 0.50],
                 "within_arm_graded_over_binary_cf_max": 0.6, "spurious50_ratio_max": 0.85, "max_prototype_out_degree_ratio_max": 0.9,
                 "independent_delta_max": 0.03, "mixed_independent_subset_delta_cues_max": 3,
                 "most_likely_failure": "the ramp floor: a second informative FEASIBILITY FAIL with the delta over binary held"}}
```
