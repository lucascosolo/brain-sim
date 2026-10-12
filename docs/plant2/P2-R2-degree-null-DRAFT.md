# P2-R2: an input-degree-preserving null for structured interference — CONDITIONAL DRAFT

Draft dated 2026-10-12. **Not frozen, not permission to implement or run.** The lead may select
this as the distinct third takeover pass only after P2-E6 seed101 records FEASIBILITY FAIL
with complete mandatory evidence (all12 F10/independent load records, both sanity controls,
and all8 required paired comparisons), and E6 simulation processes have finished. E6 failure does
not activate this draft automatically. Independent review and a committed final contract must
precede implementation. This is an explanation test, not a new memory mechanism or Stage 1 gate.

## Question and scope

Does substantial F10/s60 index interference remain when input-line usage is held exactly fixed
but the original grouping of lines into related episodes is randomized? P2-R1 found that the
old pooled arm changes the load on lines belonging to multiple prototypes. Its benefit cannot
cleanly distinguish preserved line frequencies from family co-occurrence.

The new contrast preserves the original binary input matrix's row sums and every column sum
within each consecutive 100-episode block. Consequently all line totals are exact at both
M=500 and M=1000, and at every intervening 100-item boundary. F10/s60 remains the canonical
condition. There is no substitute easier family count and no tuning on the resulting scores.

The estimand is performance under a finite, block-constrained randomized input intervention
versus the original input sequence. This is not an independent causal partition into a
"frequency contribution" and a "correlation contribution": temporal order within blocks,
individual episode composition, cue composition, actual spike eligibility and learned neural
state can all change. Persistent failure in the null would show that the original family
grouping is unnecessary for that observed failure; it would not prove line frequency alone
is its unique cause.

## Sources inspected and frozen substrate

- `plant2/experiments/p2_e5_structured.py`: `FamilyGen` emits episode k from stream
  `(seed,21,F,k)`, family `k % F`, retaining 40 of that family's 100 prototype lines and
  drawing 60 lines outside its prototype. The pooled arm samples 40 from the prototype union,
  which does not preserve individual line counts or their temporal trajectories.
- `plant2/experiments/p2_e3_completion.py`: use inherited E3 encoding and feedback unchanged,
  including 200 ms input, p=0.5 binary BTSP and 50 ms continuation/responder feedback.
- `p2_e1_btsp.py`, `p2_e2_accommodation.py`, `engine.py`, `btsp.py`, `readout.py`: inherited
  populations, random streams, accommodation, scoring and content replay remain unchanged.

Keep J_mem=1.525, accommodation tau=10000 ms, J_fb=2.80, g=0.3, index window 50 ms and content
window 75 ms. Do not use E6 history weighting, R3 feedback, new inhibition, recurrence, a new
threshold or a readout grid. Record source byte hashes and runtime versions in every result.

## The fixed null, specified before simulation

For each seed, generate exactly 1000 canonical F10/s60 items, in original order, as a binary
matrix X with shape 1000 by 4000. Each row contains exactly 100 distinct lines. Split rows
into ten fixed blocks: 1–100, 101–200, ..., 901–1000. Never trade between blocks.

Use the row Curveball heat-bath trade described by Carstens and Kleer (2017), section 1:

1. Select two distinct rows uniformly from the block, independent of their contents.
2. Preserve their common entries. Form the sorted union of entries exclusive to either row.
3. Uniformly select as many exclusive entries for the first row as it originally had; give
   the remainder to the second. Preserve both row sizes, including no-change outcomes.
4. Repeat for exactly **10,000 attempted trades per block**, counting null trades. Use sorted
   arrays before random selection so set-iteration order cannot affect replay.

The delivered null Y is the endpoint of chain 0, with stream `(seed,40,F,block,0)`, using
zero-based block numbers. Do not reject, redraw, lengthen or choose a chain based on neural
performance or which null looks most randomized. Chain 1, stream `(seed,40,F,block,1)`, is a
structural diagnostic only; its inputs never reach a simulated network.

This transition preserves binary entries and both margins exactly. Its uniform stationary
distribution does not mean a finite run is an exact independent uniform draw. The 10,000-trade
choice is a fixed engineering budget, not a proven mixing-time bound. The published comparison
also covers equal-row-sum matrices, but does not certify these particular endpoints.

Primary methodological sources:

- Carstens and Kleer, *Comparing the Switch and Curveball Markov Chains for Sampling Binary
  Matrices with Fixed Marginals*, revised 2017: https://arxiv.org/html/1709.07290v3
- Strona et al., *A fast and unbiased procedure to randomize ecological binary matrices with
  fixed row and column totals*, 2014: https://doi.org/10.1038/ncomms5114
  (the publisher lists subsequent corrections; use the explicit trade above, not uninspected
  supplementary scripts).

## Structural checks and limitations before LIF expenditure

Retain X, chain-0 Y and their SHA256 digests. Check exact binary membership, every row sum of
100, all 4000 column sums in every block, and prefix column sums at 500 and 1000. Check that
the first 500 rows used at M=1000 are the identical rows previously used at M=500.

For both chains save structural diagnostics at 0, 2500, 5000 and 10000 attempted trades per
block. Define O_kl as the intersection size of episode rows k and l, and report at each load:

- D: mean O for pairs bearing the same original family label minus mean O for different labels;
- Q: mean squared O over distinct episode pairs;
- R: mean retained fraction |X_k intersect Y_k| / 100;
- the overlap distribution and lag-conditioned means for lags 1, 10, 50 and 100;
- total attempted and changed trades, changed-row fraction and changed-entry fraction.

Original family labels are diagnostic annotations only; the null generator and training
never use them. The overall mean pairwise overlap is fixed by the column totals, so its
agreement is an integrity check, not evidence that mixing succeeded. Per-load Q must be
computed without integer overflow.

Flag the perturbation as **STRUCTURAL CONTRAST UNCERTAIN** at a load if any of these fixed
diagnostics fails: on each chain's endpoint, |D_null| <= max(1 line, 0.1*|D_original|);
separately within each chain between5000 and10000 trades, relative Q change <=5%,
absolute R change <=0.03 and absolute D change <=0.5 lines; and the same Q/R/D tolerances
between the two chain endpoints. Relative Q difference divides by the
mean of the two positive values. Do not extend the chain to repair a flag. Exact-margin
failure is INVALID. If either mandatory load is structurally uncertain, retain the matrices
and diagnostics and stop before full LIF runs. These heuristic checks detect conspicuous
failure; passing them does not establish uniform sampling or eliminate residual dependence.

Block constraints preserve coarse learning-age marginals, including the oldest 100 as a
group. They do not preserve individual-line interarrival times, within-block cumulative
counts, higher-order co-occurrence, or which lines coincide with a given plateau. Report
maximum and RMS within-block deviations in cumulative per-line item counts. Later, also
report actual eligibility column-count differences per block: item degrees are exact, actual
spike-derived eligibility degrees need not be. This experiment deliberately changes inputs;
it is not a post hoc synaptic shuffle.

## Seeds, arms and the original/sham control

Proposed fresh simulation seeds are **103 and 104**. A draft-time audit found no use as seeds
in recognized seed fields of `bench/results/plant2.jsonl`, relevant source/contracts/reviews,
or accessible cache filenames. Incidental occurrences as cue counts or line numbers are not
seed use. Recheck at freeze and record the audit; if a collision is found, revise this draft
to name two unused seeds before implementation, never substitute silently during a run.

There are exactly four mandatory full-LIF trajectories: each seed's ORIGINAL and DEGREE_NULL,
each learned once to 1000 with nested checkpoints at 500 and 1000. Both use the same precomputed
item adapter and inherited E3 learner. ORIGINAL passes through the preprocessing wrapper but
delivers an untouched copy of X; trades operate on scratch copies only. Its input digest must
match direct `FamilyGen` output exactly. Record preprocessing, learning, settling, evaluation
and replay wall times separately. ORIGINAL is also the full-size runtime reference.

Before those trajectories, one small original/sham identity check must compare direct inherited
E3 with the precomputed original adapter on the same synthetic small network and seed 103.
Use the inherited E3 configuration except m=n=256, a=64 and f_q=0.05, for 20 encoding episodes.
Prepare the adapter's independent items from a separate identically seeded inherited PATTERNS
stream. Keep all timing, rates, synapse and membrane constants inherited; no scoring or tuning.
Require byte-identical items, A, eligibility, forward/feedback stores, neural state and equal post-learning
learning-input/plateau/coin RNG states; the replaced item adapter instead matches the episode
counter and emitted-item sequence. This is an implementation check, not full-size calibration. The finalized contract
must retain an exact small configuration before code. No second full-size sham simulation.

Both experimental arms start with the same seed and inherited stream keys. Plateaus A and
episode/test schedules must be identical. Poisson uniform variates remain aligned tick by
tick because every tick draws the full input population. **Actual sensory spikes are not
identical**, since active lines change. Keep inherited BTSP coin generation unchanged: when
eligibility-array sizes differ, its variable-size draws can desynchronize later candidate
coins. Log draw counts and this limitation; do not silently change the baseline to a new
per-episode coin scheme. This is paired common-seed sampling, not exact spike/coin matching.

The input adapter contains the randomized matrix, but no downstream learner sees the original
family identity, prototype sets, future input rows, or other arm's state. Assigned plateau
sets remain the supplied random memory keys.

## Checkpoint evaluation and content diagnostics

Keep the learning trajectory untouched by evaluation: deep-copy each checkpoint and use
inherited E3.run_phase with phase=1, 50 s settle, 200 half cues, 200 independent novel half
cues and 200 full cues, each lasting 100 ms followed by 200 ms background. Use inherited
e1.test_sets and TEST_IN keys. Apply each arm's identical positional half masks to its own
learned items. Thus age and mask sampling match, while cue-line identities differ. Novel
items and novel masks are identical across arms. Neither test changes the learning copy.

At both loads, independently report C1, C2, C3, C4-recall and C4-spurious, together with the
paired fraction meeting recall AND specificity. Preserve every per-cue count, A size, target
recall, spurious count, first-spike time and target/spurious total response. Report target
and total activity, cue-onset threshold offsets, store size/degrees, eligibility rate and
age strata, so specificity changes accompanied by lost recall remain visible.

On each arm's own memory raster, replay two feedback stores at the frozen readout:

- inherited responder-written feedback;
- the existing assigned-A-written diagnostic store, using that arm's own eligible inputs.

Keep these as separate S2 joint-content, S3 novel-content and S4 oldest-content readings,
with missing recovery and intrusion distributions. Assigned-A feedback is a supplied reference,
not a deployed mechanism or guaranteed upper bound. It may itself fail. Report C1/C2 and
content jointly only from actually paired per-cue outcomes. No best-over-grid result is needed.

Inherited validity: mean eligible true-input fraction >=0.95; mean |A| at 1000 in 18.5..21.5;
settle mean absolute vbar drift <=0.2 mV over its final 10 s; unchanged learning state/RNGs
after evaluation. A protocol failure is reported and bars are not relaxed. A programming
integrity failure records INVALID, preserving the attempt; no seed replacement under this draft.

## Predeclared effects and descriptive interpretation

M=1000 is the primary effect-size contrast; M=500 is mandatory and reported independently.
The replication unit is the seed. Report seed-specific paired discordance counts, not
independent-cue p-values or a pooled confidence interval. Two seeds are explanatory screening,
not a five-seed capability gate.

For a score Z, Delta Z = Z_null - Z_original on the matched episode indices. Use the following
ordered labels at M=1000, separately per seed, only if structural and protocol checks hold:

1. **RECALL TRADE-OFF:** Delta C1 < -0.03 or Delta C4-recall < -0.03. Specificity gains then
   do not count as preservation of accessible memory, regardless of C2 improvement.
2. **MATERIAL STRUCTURE SENSITIVITY:** Delta C2 >=0.15 and Delta joint-index >=0.10, with
   neither recall-loss condition above. Report whether null C2 reaches 0.90 and every inherited
   index bar separately; an easier-input success is not a new memory capability.
3. **FAILURE PERSISTS WITH SMALL MEASURED BENEFIT:** original C2 <0.90, null C2 <0.90, |Delta C2| <=0.05 and
   |Delta joint-index| <=0.05, with neither recall-loss condition above. This does not identify
   frequency as the sole cause or rule out a benefit smaller than the declared margins.
4. **MIXED/INTERMEDIATE:** any other complete result, including worsening beyond those margins.

When original C2<0.90, additionally report the raw bar-deficit fraction removed:
`(C2_null-C2_original)/(0.90-C2_original)`. Do not clip it. Values >=0.5 mean at least half of
that measured C2 bar deficit was removed, not half of a biological causal mechanism. Do not
compute it when the denominator is zero or negative. Describe that observation as replicated
only if it holds on both seeds; otherwise report disagreement.

At M=500 report the same raw deltas and inherited bars without forcing the M=1000 labels onto
a near-ceiling baseline. A Delta C2 or joint-index of >=0.05 is a material low-load gain for
reporting only, provided recall losses stay within 0.03. Content is classified separately:
for each store/load, Delta S2>=0.10 is a material content gain, Delta S2<=-0.10 a material
loss, otherwise an intermediate/small change. Always display absolute content bars.

Predictions, hypotheses before implementation: the exact-degree null will remove most of the
original-label overlap contrast; at M=1000 C2 will improve by at least 0.15 and joint index by
at least 0.10 without losing more than 0.03 C1. We expect some interference to remain and do not
predict that both seeds meet all inherited index bars. Inherited content is expected to stay
below 0.90 at M=1000, even if assigned-A feedback improves. M=500 is expected to show smaller
index gains because original specificity is already near its bar. Record contradictions;
do not revise predictions using E6 or R2 outcomes after freezing.

## Supplemental F40 and resource stop

Generate F40/s60 matrices on the same two seeds and apply the same block trade only as a cheap
structural transfer diagnostic after mandatory F10 input checks. Report exact margins and
D/Q/R, without claiming a neural transfer result. No F40 full-LIF trajectory is authorized
by this draft; a later extension would need a separate allocation and predeclaration. F40
never replaces, rescues or changes interpretation of F10.

Once selected and frozen, R2 has **20 wall minutes total**, measured from the first R2
preprocessing/validation process, and **at most four simultaneous simulation processes across
all takeover work**. Begin only after E6 simulations finish. No paid calls. Run the two
original/null pairs concurrently only within measured memory limits; reduce concurrency if
needed without enlarging the wall budget. Do not launch speculative extra arms.

At each completed load, save the per-cue results and available state before continuing.
Start no new learning/evaluation/replay stage after minute 18; checkpoint an in-flight stage
and stop by minute 20, with no grace extension or shortened substitute protocol. Retain
completed evidence as PARTIAL and list every missing mandatory seed/arm/load/readout. A
resource-limited result is not an absence-of-effect finding. Preserve all started attempts,
failures and structural flags; never delete or overwrite an earlier attempt.

Before launch, estimate trajectory time from E6's inherited-baseline runtime records and
use a conservative memory bound from stored-array dimensions. A measured peak is unavailable
when execution sessions isolate process namespaces; do not label a bound as measured RSS.
Use at most two R2 simulation processes, each running its original/null pair sequentially,
within the global maximum of four. Do not run a fresh full-size benchmark. If they cannot plausibly fit four
trajectories plus fixed replays inside the ceiling, either keep this as an unexecuted draft
or explicitly select a partial-evidence run; do not lower cue counts, omit 1000 or relabel a
partial run complete. The lead must choose that status before starting.

## Evidence to retain and next decision

Append result records to the established results stream only after this contract is finalized.
Persist exact original/null matrices, block marginals, structural snapshots, seeds/stream keys,
input/source digests, A/E/stores and evaluation rasters in the allowed cache. Commit portable
per-cue counts and enough structural summaries to recompute every reported label. No deletions,
historical-file modifications or experiment implementation are part of this draft task.

The lead chooses whether to freeze this proposal only after E6 evidence. A replicated material
contrast would justify investigating co-occurrence-sensitive encoding in a future mechanism
contract; persistent null failure would motivate a narrower load/operating-state investigation.
Neither outcome authorizes Stage 2, another mechanism, parameter rescue, or main-branch merge.

## Preparation closure

This preparation draft is superseded by docs/plant2/P2-R2-degree-null.md, frozen at2454f06
after the complete E6 feasibility failure. It is retained for provenance and is not an
additional experiment contract.
