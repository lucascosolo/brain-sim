# P2-E6: presynaptic-load-gated forward encoding

Contract, 2026-10-12. Independently reviewed before implementation. The commit that adds this
final text freezes it. Only append thereafter. No E6 implementation exists at freeze.
Review: review/plant2/P2-E6/findings-contract-methodology.md; all six blockers resolved below.

## Hypothesis and choice

Frequent sensory lines acquire synapses into many assigned assemblies and therefore recruit
siblings under partial cues. Redistributing a fixed encoding budget toward less frequent
eligible inputs should improve specificity without obtaining it by silencing the index.
The learned forward synapses change; threshold parameters and scoring rules do not.
Adaptive threshold states can change with neural activity and are reported.

Choose presynaptic load rather than reconstruction error for this experiment. P2-E5's inherited
feedback is already badly contaminated, so its error signal is not a reliable starting teacher.
Adding a cleaned feedback path first would stack two unproven mechanisms. The available evidence
for this choice is the existing high-load index failure, strong sibling recruitment, and the
new P2-R1 finding that hot-line multiplicity was not matched by the old pooled control.

This is a computational metaplasticity proxy, not a biological implementation claim. Prior
activity can alter subsequent plasticity at individual synapses (Lee et al., 2010,
https://pmc.ncbi.nlm.nih.gov/articles/PMC2911980/); that observation motivates history-dependent
eligibility but does not validate the equation below. The binary toggle substrate comes from
Wu and Maass (2025), https://doi.org/10.1038/s41467-024-55563-6. The present modification is our
testable engineering hypothesis. No claim that this is a novel scientific invention.

## Exactly one change

Keep per-input counts H_j of previous encoding episodes in which line j reached inherited
eligibility (>=3 spikes in 200 ms). Before episode k's write (k starts at 1):

    h_j = H_j + 1
    p_j = min(1, lambda / h_j) for j in E_k
    choose lambda so sum_j p_j = 0.5 * |E_k|

Then toggle candidate synapse j->i iff its inherited coin draw u_ji < p_j, for i in the
inherited random plateau set. Draw all |E_k|*|A_k| coins in inherited order. Only after that
write, increment H on E_k. Empty E means no write. Compute lambda deterministically with
80 iterations of bisection between zero and max(h_j); use float64. No parameter sweep.

The history is causal and uses actual spikes, never item labels, prototype membership,
future data, correct-answer assemblies from evaluation, or reconstructed content. The pseudocount of one prevents division by zero and makes the first episode uniform.
No externally supplied input-frequency estimate is needed. The normalization is an aggregate over eligible
dendritic inputs, a labelled circuit-level proxy, not a strictly pair-local rule. It preserves
the expected number of flips, not realized additions, density, firing rate, or recalled signal.
Probabilities over 0.5 increase both potentiation and depression; old memories can suffer.

Everything else stays frozen: binary synapses, assigned plateau probability, populations,
Poisson rates/streams, 200+50 ms episode, quiet learning protocol, inherited responder feedback,
J_mem=1.525, accommodation tau=10000, 50 s settle, J_fb=2.80, g=0.3, 50 ms index/75 ms content,
all cue sets and bars. No memory inhibition or recurrence. No R_3 write in the deployed arm.
Existing experiment files remain untouched; a separate subclass/driver implements the rule.

## Arms and controls

At M=500 and 1000 on each mandatory seed:
1. Inherited uniform-p=0.5 encoding (matched baseline).
2. Load-gated encoding above (candidate).
3. Realized flip-count-matched random encoding: for each plateau cell, compute the candidate
   flip count from the identical inherited coin array and probabilities, then select that many
   eligible inputs uniformly with stream `(seed,31,k,plateau_cell_id)`. This preserves each
   cell/episode's number of flip attempts, not additions, depressions or final density.

Run F=10/s=60 canonical inputs and independent P2-E3 inputs for all three arms.
F=40/s=60 is additional transfer: candidate and baseline, reported only.
The same seed gives the same items, sensory spikes, plateaus, and coin array across arms;
controls do not consume those streams. Counts H also match, since eligibility is presynaptic.
Freeze all arms' neural states while testing copies; testing never updates histories or weights.

At M=1000 canonical, also apply one global postsynaptic permutation to the candidate raster
(stream `(seed,32,M)`) while retaining original A for scoring. This is equivalent to permuting
forward columns AND complete memory-cell state, preserves total activity exactly, and changes
identity only. It is a label/leak sanity check, not a difficult learning comparator.
A never-trained empty-store twin, with otherwise inherited initial state and presentation
protocol, is a silence/leak check. It never receives training writes.

Read content through inherited feedback and assigned-A feedback on the candidate's own raster,
both at the frozen readout. The assigned store is a diagnostic reference, not a deployed fix or
mathematical upper bound. Structured content does not decide index success. Independent content non-regression is an
additional requirement for the combined experiment, reported separately from the pure index verdict.
Report no joint capability
unless that joint was actually measured.

## Seeds, calibration, and resource stop

- Exploration/development: 101 only; no other seed may inform tuning. The equation and constants
  are fixed now; exploration may find implementation defects, not change the mechanism.
- Held-out calibration/feasibility: 102, run only after code and exploration findings committed.
  No parameter choice is made. It is a prospective go/no-go check of the frozen mechanism.
- Fresh gated seeds: 111,112,113,114,115, none used for development or calibration.
- Before gated runs, commit calibration, numerical predictions and exact code-tree hashes.
- If the candidate fails the core index requirements on seed101 or102, record a failed
  feasibility screen, do not spend the five-seed gate, and do not rescue by retuning. Complete
  matched controls at both loads and independent regression on the failed seed. A failure in
  exploration is not a five-seed gated FAIL. Seed102 need not be spent after seed101 failure.
- Compute ceiling for this experiment: 60 wall minutes elapsed from the first full-size E6
  process start, at most four simultaneous simulation processes across all takeover work.
  The ceiling overrides missing-arm completion: start no new load after it, finish an in-flight
  load within an additional10-minute grace; otherwise interrupt cleanly and retain PARTIAL.
  Always retain completed load evidence. Record start/end times; no unrun gate is interpreted.

## Core requirements, unchanged when results arrive

The CANDIDATE, separately on F10 and independent inputs at both loads and each evaluated
seed, must meet inherited C1,C2,C3,C4: at least 90% of cues recall
>=80% of A within 50 ms; at least 90% have spurious <0.5|A|; novel ignition <0.5 mean|A| on
at least 90%; the oldest 100 meet recall and specificity as separate 90% marginal bars. Also report the paired
fraction meeting recall AND specificity; require >=0.85 for the candidate.

For F10/M1000, candidate C2 must exceed baseline by >=0.20 and the flip-count-matched random
control by >=0.10; candidate joint index fraction must exceed each by >=0.10. Failure of
these comparisons means no demonstrated feature-selective learning benefit, even if absolute
bars pass. Use same cues, item-wise discordance counts, and descriptive paired fractions. No cue-level confidence interval or independent-cue p-value
is claimed; each seed is the replication unit. Every relative margin applies separately on
every seed, never after pooling.

Independent-input regression: all C1..C4 bars, candidate C1 and C2 no more than 0.03 below
baseline at either load. Candidate content joint and oldest D4 no more than 0.05 below baseline;
report absolute content bars separately. F40 cannot rescue F10 failure.

Integrity checks: identical
item/A/eligibility digests across arms; weights, H, learning RNGs, episode counter and main neural state unchanged by tests; p in[0,1] and per-episode expected budget within1e-9;
uniform subclass reproduces frozen E3 small-network forward and feedback stores and state;
Wrong-label raster C1<0.10 and exactly zero responders from never-trained empty-store
cues are additional capability/sanity requirements. Excessive firing is a failure, not an
integrity-invalid excuse. Keep inherited learning/protocol checks: eligible fraction >=0.95,
mean |A| within18.5..21.5 at1000, and settle mean absolute vbar drift <=0.2mV over its final10s.
A drift failure is a measured protocol failure, preserved without replacement or exclusion.
An integrity defect records INVALID and stops gating. A repair may be tested on development
seed101 with a new versioned attempt, never by erasing an old result. A gated integrity failure
stops the five-seed experiment; replacement or rerun of that seed needs an explicit owner ruling.
Lack of required data is PARTIAL. An overall E6 PASS requires all five fresh seeds and every
core/regression/control requirement. Report the pure index vector separately from this combined verdict. It is neither Stage1 completion nor a content PASS.

## Predictions, prior to implementation

Simple stationary rationale: a once-member prototype line occurs with probability about0.054
and a cold line about0.0154. Ignoring history noise/capping, normalizing over roughly40 hot and
60 cold inputs yields flip probabilities around0.20 and0.70, retaining50 expected flips while
reducing shared-feature writes. These are analytic approximations, not observations.

Predict F10/M1000 candidate C2=0.70..0.95 (baseline about0.45..0.55), C1=0.85..0.98,
and the oldest-item bar as the most likely failure. Thus a complete PASS is uncertain and
feasibility rejection is plausible. Predict independent C1 within0.05 of baseline but not
guaranteed within the regression bar. Predict content can still fail despite index gains.
Do not revise these intervals after exploration; append measured deviations.

## Interpretation and next decision

The only prospective new capability is learned feature-selective encoding that recalls related
experiences more specifically at unchanged latency. No assigned-key, write-timing, verbatim-value
or test-protocol supply is removed. A success would reduce dependence on uniformly independent
input statistics, not demonstrate autonomous representation, abstraction or reasoning.

If rejected, preserve it. The distinct next investigation is the exact-degree input null from
P2-R1, or another separately contracted mechanism; do not tune this candidate repeatedly.


## Freeze details and executable decision order

The preimplementation review changed the prior from0.8 to1, deliberately, not algebraically.
A common frequency denominator cancels under normalization; the pseudocount itself does not.
Source baseline is55e16ebff62a90d6402745f44fb860010741eba5. Pin the byte hashes of inherited
engine.py, btsp.py, readout.py and experiments/p2_e1..p2_e5 modules in every result. New E6
code gets its own hash and commit. The uniform wrapper must match frozen E3 on a small
network; the candidate must not be required to have the unchanged baseline forward store.

Evaluation copies use inherited E3.run_phase phase=1 at each nested500→1000 checkpoint, with
50s settle,200 half cues,200 novel half cues,200 full cues,100ms cue/200ms gap, and inherited
e1.test_sets/TEST_IN keys. Never-trained is a freshly initialized inherited E3 with the same
items/A copied only for scoring, zero forward/feedback stores, no training and fresh H=0; it
is settled and presented by that same function. The shuffled-raster comparator changes only
IDs through a permutation and preserves every tick's spike count. Related novel exemplars
are not tested by inherited C3; this limitation stays visible.

Mandatory order per development/calibration seed:
1. F10 baseline, candidate, exact flip-count-matched random: both loads.
2. Independent baseline, candidate, random: both loads.
3. Cheap canonical M1000 wrong-label and empty-store sanity checks.
4. F40 baseline/candidate both loads, reported; this may be deferred at the resource ceiling.

The prospective screen vector is all candidate F10 absolute bars, joint>=0.85, relative C2
and joint margins at1000, F10 C1 >= baseline - 0.03 at both loads, independent absolute/index/content non-regression, sanity conditions,
and protocol checks. Any false part gives FEASIBILITY FAIL; an incomplete required part gives
PARTIAL in addition to any already-observed failed part. Only a complete passing screen on101
and102 opens111–115. Continue mandatory evidence on the failed101 within the resource ceiling;
102 and gated seeds remain untouched. No comparator is required to satisfy candidate bars.
F40 never vetoes or rescues the canonical screen; report transfer failures distinctly.

For F10 also require candidate C1 no more than0.03 below baseline at both loads, to rule out
a large recall-for-specificity trade. Record paired recall gains/losses, own/spurious/total
response counts, cue-onset threshold offsets, realized potentiation/depression, final store
density and age strata. A success demonstrates improved paired performance under frozen
parameters, not an isolated causal mediator: changed operating state may contribute.

Append one result per seed/arm/condition/load and preserve failed/partial attempts. Retain
portable per-cue index/content counts and latency sufficient to recompute reported aggregates
in Git; preserve compressed learned stores, H, A/items/E and test raster in the cache with
sha256. Commit a machine-readable frozen contract, verdict function and small integrity tests.
Do not modify mechanism or criteria during calibration or gated runs. Before gates record the
committed source tree and measured feasibility/predictions. User approval is required only for
a gated rerun or an owner decision outside these already authorized rules.
