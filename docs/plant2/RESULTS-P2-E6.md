# P2-E6: load-aware encoding improves selectivity but fails the frozen screen

Contract `6733109`; implementation `c4cc27b`; development seed101, attempt `e6-s101-v1`.
No parameter or decision threshold was changed after the contract or during this run.
This is a prospective development feasibility screen, not a five-seed gated result.

## Canonical ten-family results

All fractions are measured, with 200 half cues and an oldest cohort of 100.
Index uses 50 ms; content uses 75 ms, J_fb=2.80 and g=.3. No readout search was used.

| Items | Encoding | Index recall C1 | Specificity C2 | Joint index | Oldest recall | Oldest specificity | Inherited content joint |
|---|---|---:|---:|---:|---:|---:|---:|
| 500 | Baseline | 0.960 | 0.885 | 0.845 | 0.970 | 0.840 | 0.120 |
| 500 | Load-gated | 0.945 | 1.000 | 0.945 | 0.980 | 1.000 | 0.785 |
| 500 | Flip-count-matched random | 0.980 | 0.870 | 0.850 | 0.990 | 0.820 | 0.080 |
| 1000 | Baseline | 0.935 | 0.500 | 0.440 | 0.940 | 0.470 | 0.005 |
| 1000 | Load-gated | 0.970 | 0.895 | 0.865 | 0.970 | 0.890 | 0.065 |
| 1000 | Flip-count-matched random | 0.945 | 0.460 | 0.410 | 0.940 | 0.420 | 0.000 |

Candidate M1000 specificity is 179/200, below 180/200; oldest specificity is 89/100, below 90/100.
These are failures regardless of their proximity to the bars. The candidate is not retuned,
and the screen cannot open calibration 102 or gated 111–115. The other matched-control and
regression evidence is completed according to the predeclared stopping rule.

At 1,000, candidate specificity gains 39.5 points against baseline and 43.5 against matched random.
Paired specificity gains/losses are 79/0 and 87/0; joint-index gains/losses 86/1 and 94/3. These
are paired cues within one network, not independent seed replications or statistical confidence
intervals. The matched random arm preserves each plateau cell's realized number of flips per
episode. It does not preserve which synapses change, final density or adaptive threshold state.

## What changed in the network

The single change uses prior spike-derived input eligibility counts to redistribute a fixed
expected flip budget toward less-used sensory lines. It preserves the supplied random plateau
keys, quiet encoding schedule, feedback writes and threshold parameters. It neither reads
family labels nor receives an externally supplied input-frequency estimate.

At F10/1000, mean own-cell responders increase 18.585→18.925 and spurious responders decrease
16.970→3.145. Forward density increases .055841→.057623; the gain is not simple network
silencing or a global reduction in synapses. Mean assigned-cell threshold offset also changes
5.811→5.469mV. This is improved paired performance under frozen parameters, not isolation
of a synaptic mediator at an identical operating state.

At 500 there is a small recall cost: candidate/baseline recall discordance is 5 wins/8 losses,
and candidate/random 1/8, despite the higher joint index. This remains visible rather than being
hidden by specificity. The contract's baseline recall non-regression criterion is met.

## Content and independent inputs

For the candidate, assigned-A diagnostic feedback scores .990 at F10/500 and .425 at F10/1000.
Its deployed inherited feedback scores .785 and .065. An index improvement has therefore not
solved content reconstruction. Neither assigned-A feedback nor R3 is deployed by this mechanism.

Independent M500 candidate C1=.975 versus baseline .980; content joint1.000 versus .995.
At M1000 candidate C1=.935 versus .960 (loss .025, within the .03 tolerance), C2=.990 versus .975,
and content joint/oldest D4=.975/.960 in both arms. These are compatible with the frozen
independent regression bars on this one seed, not evidence of multi-seed robustness.

## Predictions and interpretation

Preimplementation predictions put F10/1000 C2 in .70–.95 and C1 in .85–.98; the observed
.895/.970 fall inside those intervals. The predicted oldest-item failure occurs in specificity.
Independent recall is within the predicted .05 range and the stricter required .03 regression
bar. These matches do not turn failed criteria into a PASS.

This reduces uncertainty about the usefulness of presynaptic history in the tested regime:
feature-selective encoding produces a large index gain beyond an exact flip-count control.
It does not establish autonomous key selection, abstraction, online recall, capacity growth,
graceful forgetting or Stage 1 completion. Encoding boundaries, assigned keys, input design,
verbatim sensory values and settle/test scheduling remain externally supplied.

The next separately contracted pass will test the distinct input-structure explanation if
the complete mandatory screen confirms the observed failure. It will not tune this candidate.

## Evidence and review

`bench/results/p2e6.jsonl` is the append-only execution journal. Per-cue evidence is under
`bench/results/p2e6/`; compressed H/probabilities/A/E/stores/rasters are hashed in the journal
and preserved under `~/.cache/brain-sim/plant2/p2e6/e6-s101-v1/`. Large raw cache files are
reproducible local artifacts; portable criterion evidence is committed.

Independent code review reconstructed 16 tiny stores and both content replays, and closed
three evidence/execution findings before full simulation. The plant2 suite passed 76 tests
with 7 slow tests deselected. Full-size results are independently audited separately; final
closure and all remaining control measurements are appended below when the run finishes.

## Final measured closure

The run completed all16 load checkpoints and both sanity controls in 608.64 seconds
(2026-10-12,04:06:07–04:16:16 UTC), within the60-minute ceiling. The final machine screen is
**FEASIBILITY FAIL**, complete and integrity-valid, with exactly two failed parts:
F10/1000 C2 and F10/1000 oldest specificity. All other mandatory index, comparative, independent
content-regression, protocol and sanity requirements passed. Held-out102 and gated111–115
remain unrun, as required by the frozen stopping rule. This is not a five-seed gated FAIL.

The identity-permuted raster has C1=0 and preserves every tick's spike count. The never-trained
empty store has zero responders and zero raster spikes. Mandatory paired comparisons were
saved before optional transfer. No resource or implementation interruption occurred.

Additional measured conditions:

| Condition | Items | Arm | C1 | C2 | Joint index | Old recall | Old specificity | Content joint |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| independent | 500 | baseline | 0.980 | 1.000 | 0.980 | 0.980 | 1.000 | 0.995 |
| independent | 1000 | baseline | 0.960 | 0.975 | 0.935 | 0.980 | 0.960 | 0.975 |
| independent | 500 | candidate | 0.975 | 1.000 | 0.975 | 0.960 | 1.000 | 1.000 |
| independent | 1000 | candidate | 0.935 | 0.990 | 0.925 | 0.940 | 0.980 | 0.975 |
| independent | 500 | random | 0.965 | 1.000 | 0.965 | 0.960 | 1.000 | 0.990 |
| independent | 1000 | random | 0.955 | 0.975 | 0.930 | 0.970 | 0.960 | 0.965 |
| F40 | 500 | baseline | 0.950 | 1.000 | 0.950 | 0.940 | 1.000 | 0.760 |
| F40 | 1000 | baseline | 0.970 | 0.820 | 0.790 | 0.960 | 0.800 | 0.085 |
| F40 | 500 | candidate | 0.920 | 1.000 | 0.920 | 0.930 | 1.000 | 0.855 |
| F40 | 1000 | candidate | 0.940 | 0.950 | 0.890 | 0.950 | 0.950 | 0.200 |

F40 is reported transfer only. Its results neither rescue nor change the canonical F10 failure.
The final outcome supports retaining the failed mechanism and investigating a distinct
explanation with a separately frozen input-degree-preserving control, rather than tuning it.

## Independent full-size audit closure

The independent methodology reviewer verified96,108 scalar/structural checks across all16
loads,18 portable/raw pairs,9,600 index rows and13,200 content rows. Reconstructed forward
stores, matched-control streams and mandatory feedback stores agree exactly. All70 prospective
vector parts were rebuilt:68 true and precisely the two frozen specificity requirements false.
No scoring or implementation blocker was found. Full neural dynamics were not rerun by this
reviewer; encoding spike/threshold-state equality checks were inspected rather than regenerated.
See review/plant2/P2-E6/findings-results.md for scope and tradeoffs.

The learning.probability_min/max fields describe the computed candidate probabilities in
all arms; baseline actually deploys p=.5. Do not interpret these diagnostics as variable
baseline plasticity. F40 candidate passes its absolute index bars but still has inherited
content joint=.200 and oldest D4=.070 at1000; assigned-A feedback gives.935/.930. No content
repair was deployed. All unrun held-out/gated seeds remain unverified.
