# P2-E4 post-run diagnosis plan (predeclared, reported, not a gate)

Written 2026-10-10, before any P2-E4 gated seed (16-20) has run, following the owner's comments
on the exploration results of seeds 42-43. P2-E4's frozen contract (cd17cde) and its frozen
driver are not changed. Nothing here can alter a gated number, label or validity check.

## What exploration suggests (seeds 42-43; exploratory, not results)

| seed | load | online C1 (index) | content joint | cohort memory | cohort content | threshold offset |
|---|---|---|---|---|---|---|
| 42 | M = 1,000 | 0.690 | 0.950 | 0.670 | 0.920 | 6.9 mV |
| 43 | M = 1,000 | 0.790 | 0.980 | 0.810 | 0.990 | 6.9 mV |

So at least 26 % (seed 42) and 19 % (seed 43) of half cues regenerate the missing content while
failing index recall.

Habituation at M = 500:
- seed 42: 22 of 31 eligible items habituated, with recovery and collateral passing;
- seed 43: 10 of 22 eligible items habituated (O4 not estimable), with recovery passing.

This points to two separable vulnerabilities:
1. access to the assigned memory code under continuous activity;
2. suppression of recall under repetition, which reverses when the repetition stops.

The diagnosis tests whether they are in fact separate, and where each one sits.

## How it is computed

- **Deterministic re-simulation.** The main timeline of a seed is deterministic given its
  streams. An analysis script outside `plant2/` (`analysis/p2e4_diagnosis.py`) re-runs it with
  extra read-only measurements taken at slot time. It wraps the driver's per-slot scoring at
  runtime and consumes no random draws. The gated code tree therefore stays exactly as frozen.
- **Validity of the re-simulation.** Every gated-block slot outcome that the run logged must be
  reproduced exactly: recall, spurious, missing, intrusions, joint, |R50| and |rec|, all compared
  with the per-slot log referenced by the seed's record. If any slot differs, that seed's diagnosis
  is void and reported as such.
- **Where it runs.**
  - Exploration seeds 42-43 as soon as their records exist (labelled exploratory).
  - The gated seeds after the P2-E4 verdict is recorded (labelled reported, post hoc but
    predeclared here).

## Measures

**D1. Index against content, per cue.**
- For every gated-block half cue, the 2 x 2 of index pass (recall of A(x) >= 0.8 within 50 ms)
  against content pass (the joint).
- Counts per seed, load and kind (recent, uniform, cohort).

**D2. What distinguishes "content without index" cues.** For each cell of D1:
- A(x) recall at 50 ms and at 75 ms. Does a longer window rescue the index?
- R(x) recall at 50 ms: the fraction of the continuation responders, from which x's feedback was
  written, that spike.
- |R(x)| and |R(x) ∩ A(x)|.
- The median first-spike tick of x's A cells, and of x's R cells, that fire within 75 ms.
- The share of x's regenerated missing lines whose feedback came only from cells outside A(x).
  These are lines that receive a written synapse from a spiking R-but-not-A cell and from no
  spiking A cell.
- The item's age.
- At slot onset: the global `vbar` offset, and the mean `vbar` offset of A(x)'s cells (the
  assembly offset).

**D3. State, not erasure (settled twin B, re-simulated per cue).**
- For cues that fail index recall online, the fraction that pass after the 50 s settle on the same
  stored synapses.
- The same for content failures.
- McNemar per seed and load.

**D4. Habituation as a separate phenomenon.**
- Per habituation item: the rise in the assembly offset over the repetitions against
  L_rep - L_ctl.
- Whether items that fail index recall online in the block habituate more, less or equally
  (cross-tabulated by item).
- Recovery among habituated items.

## Predictions (written before the analysis runs)

**D1.** At M = 1,000, "content without index" is 15-30 % of half cues. "Index without content" is
under 3 %.

**D2.** Compared with cues that pass both, "content without index" cues have:
- A(x) recall at 50 ms typically 0.5-0.8, with a 75 ms window rescuing a minority;
- R(x) recall at least as high as A(x) recall;
- later A-cell first spikes, by 5 ms or more;
- a higher assembly offset at onset;
- older items on average.

Most regenerated missing lines are still driven by spiking A cells. Under a quarter come only from
R-but-not-A cells.

**D3.** Most online index failures, at least 70 %, pass after the settle, which would point to
network state rather than erased memories. Content failures also mostly recover. The P2-E3
addendum 2 caveat applies: the online-written store is itself degraded, so some failures may not
recover.

**D4.** The assembly offset rises with repetition, and habituated items show the larger rise.
Index failure in the block is only weakly associated with habituation (the two vulnerabilities are
separable).

## What it does not do

- It gates nothing and changes nothing frozen.
- It does not test a mechanism.
- Any mechanism suggested by it needs its own contract, one at a time, with the owner's ruling
  where the mechanism belongs to a gated family. Accommodation, the operating-point mechanism,
  is in such a family.

## Corrections after the owner's code review (2026-10-11; before the analysis was run on any seed)

The owner reviewed commit e6c5385. Four corrections were made to `analysis/` only; nothing under
`plant2/` changed.

1. **D2 claimed too much.** The old measure ("lines whose feedback came only from cells outside
   A(x)") counted inputs from any spiking cell. It did not require that cell to belong to R(x),
   nor that it fired before the line.
   - **Replaced by candidate-input fractions.** A candidate input is a feedback synapse from a
     memory cell whose first spike within 75 ms came at least one tick (the feedback delay) before
     the line's first spike. Each regenerated missing line is classed as having:
     - an A(x) candidate;
     - only R(x)-not-A(x) candidates;
     - only candidates outside both;
     - no earlier candidate.
   - **A candidate is a possible contributor, not a proven one.** No causal claim rests on D2. A
     causal claim would need a separately contracted ablation.
2. **D3's check was weaker than stated.**
   - **What the record allows.** The reported-arms record holds twin B only as aggregates per kind,
     not per-cue pairs. So the strongest available check is to reproduce every recorded
     aggregate per kind: n, the four pass fractions, and both McNemar discordant counts, which
     pin the discordant pairs.
   - **A missing record** now leaves D3 "not verified" (`D3_verified` false). It is no longer
     counted as valid.
3. **D4 now reports its matched sample sizes:**
   - the number of habituated and non-habituated items that have an online index measurement;
   - the median number of online probes per item.
4. **The replay check now covers every logged main-line step.** It runs from step 1 to the second
   gated load. Each step must exist, and must match kind, target, block and age as well as every
   scoring field. A missing step counts as a mismatch.

**What reproduction establishes.** Deterministic reproduction shows consistency with the recorded
simulation, not proof of a causal explanation. D3 can give strong evidence that network state
matters. D2 and D4 narrow the explanation; they do not establish it.

**Further correction (owner review of 737e8b1, 2026-10-11; before any run of the analysis).** The
D2 classes were not exhaustive: a line with both an R(x)-not-A(x) candidate and a candidate
outside both sets, and no A(x) candidate, fell in none of them. A fifth class,
`mixed_non_A_candidates`, was added. The classes are now exclusive and exhaustive, so their
fractions sum to 1 (tested in `analysis/tests/test_p2e4_diagnosis.py`).

**Reading of D3, narrowed (owner review, 2026-10-11; before any run of the analysis).** Twin B keeps
the stored synapses, the cue identities, the masks and the order. It also changes the presentation
regime:
- the cues come after a 50 s settle;
- on a separate input stream;
- at P2-E3's rhythm (100 ms on, 200 ms off);
- with no learning episodes between them.

So recovery in twin B shows that recall is **state- or protocol-dependent recovery with the
synapses unchanged**. It does not show that the threshold offset alone caused the online failure.
Wherever the predictions above say "network state rather than erased memories", read
"state- or protocol-dependent, not erasure". Isolating accommodation would need a separately
contracted intervention.

## Exploration results (seeds 42-43; exploratory, not gated results)

Run 2026-10-11 with `analysis/p2e4_diagnosis.py --seed 42` and `--seed 43`, after the
exploration records were committed. The `diagnosis` records are in `bench/results/plant2.jsonl`
(commits ba97fcc and 78b9251).

**Validity.** Both re-simulations are valid:
- 1,000 logged main-line steps were compared per seed, with 0 mismatches;
- twin B reproduced every recorded aggregate at both loads (`D3_verified` true).

The gated diagnosis (seeds 16-20) runs only after the P2-E4 verdict.

### D1: index against content (200 half cues per seed and load)

| seed | load | both | content without index | index without content | neither |
|---|---|---|---|---|---|
| 42 | 500 | 178 | 20 (10 %) | 1 | 1 |
| 43 | 500 | 183 | 16 (8 %) | 0 | 1 |
| 42 | 1,000 | 136 | 54 (27 %) | 2 | 8 |
| 43 | 1,000 | 156 | 40 (20 %) | 2 | 2 |

**Prediction held.** At M = 1,000, content without index is 20-27 % (predicted 15-30 %), and
index without content is 1 % (predicted under 3 %).

### D2: "content without index" against "both" at M = 1,000 (medians over cues)

| measure | both (42 / 43) | content without index (42 / 43) | prediction | outcome |
|---|---|---|---|---|
| A(x) recall at 50 ms | 0.94 / 0.93 | 0.68 / 0.73 | 0.5-0.8 | held |
| share rescued by a 75 ms window (A recall >= 0.8) | - | **0.93 / 0.98** | a minority | **failed**: the large majority |
| R(x) recall at 50 ms | 0.88 / 0.86 | 0.60 / 0.59 | at least A's | **failed**: below A's |
| median first-spike tick of A(x) cells | 25 / 26 | 33.5 / 34 | later by >= 5 ms | held (+8 ms) |
| assembly offset at slot onset | 8.13 / 8.09 mV | 8.42 / 8.49 mV | higher | held (+0.3-0.4 mV) |
| global offset at slot onset | 6.86 / 6.89 mV | 7.09 / 7.14 mV | not predicted | higher (+0.23-0.25 mV) |
| item age | 649 / 685 | 729 / 660 | older | **not held** (older on 42, younger on 43) |
| \|R(x)\|, \|R(x) ∩ A(x)\| | 23, 20 / 22, 19 | 22.5, 20 / 23, 20 | - | no difference |
| regenerated missing lines with an A(x) candidate (median share) | 1.0 / 1.0 | 1.0 / 1.0 | most | held |
| ... with only R(x)-not-A(x) candidates | 0 / 0 | 0 / 0 | under a quarter | held |

The M = 500 cells show the same pattern on a smaller count (A recall 0.72-0.74, +7-10 ms later,
75 ms rescue 0.94-1.0).

**Why the A and R latencies are identical.** At recall, the few R(x)-not-A(x) cells (about 3 per
item) are almost silent; this is why R recall is below A recall. So the spiking R cells are
essentially the spiking A cells, and the medians coincide. It is not a bug.

**Reading (narrowed, no causal claim):**
- **Slower, not absent.** The online index failures are mostly slowed retrievals. The
  assembly's first spikes come about 8 ms later, and more than 90 % of those cues reach the
  recall bar within 75 ms.
- **The same cells carry the content.** The content readout counts reconstruction lines within
  75 ms. Every regenerated missing line has an earlier-spiking A(x) candidate, so the same late
  assembly carries the content.
- **Most of the D1 dissociation is a timing difference between the 50 ms index window and the
  75 ms content window,** not two separately failing memories.
- **These cues start at a slightly higher threshold offset,** both global and assembly
  (+0.2-0.4 mV), consistent with the operating-point account. D2 is correlational. Nothing here
  changes a criterion: C1's 50 ms window is frozen, and the O1 failure stands.

### D3: settled twin B, the same stored synapses

| seed | load | index failures online | pass after settle | McNemar index (online pass, settled fail / the reverse) | content failures online | pass after settle | McNemar content |
|---|---|---|---|---|---|---|---|
| 42 | 500 | 21 | 100 % | 7 / 21 | 2 | 50 % | 1 / 1 |
| 43 | 500 | 17 | 100 % | 4 / 17 | 1 | 100 % | 0 / 1 |
| 42 | 1,000 | 62 | 95 % | 7 / 59 | 10 | 80 % | **22 / 8** |
| 43 | 1,000 | 42 | 95 % | 8 / 40 | 4 | 100 % | **27 / 4** |

**Prediction held for the index.** 95-100 % of online index failures pass after the settle
(predicted >= 70 %). Per the narrowed reading, this is state- or protocol-dependent recovery
with the synapses unchanged, not erasure. It does not isolate the threshold offset.

**Not predicted: content at M = 1,000 is worse after the settle.**
- 22 and 27 cues pass content online but fail after the settle, against 8 and 4 the reverse.
- This matches twin A, where the online-written store reads 0.815 and 0.89 under P2-E3's
  protocol, against 0.995 for the plateau-set store on the same raster.
- **The reading:** the online-written store is contaminated. The online state's high offset
  suppresses the intrusions, and the settled state does not.

### D4: habituation (copies; all eligible items)

| seed | load | eligible | habituated | offset rise, habituated / not | corr(drop, rise) | recovery among habituated | matched online items (habituated / not) |
|---|---|---|---|---|---|---|---|
| 42 | 500 | 31 | 22 | 3.28 / 3.29 mV | -0.03 | 0.86 | 10 / 1 |
| 43 | 500 | 22 | 10 | 3.29 / 3.24 mV | 0.05 | 1.00 | 3 / 5 |
| 42 | 1,000 | 4 | 3 | 3.24 / 3.34 mV | -0.37 | 1.00 | 0 / 0 |
| 43 | 1,000 | 6 | 6 | 3.03 / - mV | 0.20 | 0.83 | 1 / 0 |

- **Prediction partly failed.** The assembly offset does rise with repetition, by about 3.3 mV,
  but **habituated and non-habituated items rise equally**. The size of an item's drop does
  not track its offset rise (|r| <= 0.05 at M = 500).
- **The association with online index failure is not estimable.** The median habituation item
  was never probed online (0 probes), and the matched groups have 0-10 items.
- **What this rules out, at the item level:** "habituated items accommodate more" as the
  explanation. Whatever separates habituating items from the rest lies elsewhere, for example
  in each item's drive margin. That margin was not measured here and needs its own predeclared
  measure.

### What the diagnosis says about the two problems

The owner's guidance separates two problems:
1. learning-time contamination of the content store;
2. operating-point instability of index access.

In exploration they are coupled through the threshold offset:
- **The main line** runs at a high offset (6.9 mV at M = 1,000). Index retrieval is slowed
  (D2), but intrusions from the contaminated store are held down (D3 content).
- **The duty arm** (`reported_arms`; predeclared unable to satisfy the online clause) runs at a
  lower offset (about 4.1 mV at M = 1,000). It restores online index recall (C1 0.935-0.965).
  But the store it writes is contaminated: |R| grows to about 58 at ages 501-750 on seed 43,
  and its settled joint is 0.24 on seed 43.

**Implication.** Fixing the operating point alone would be expected to expose the
contamination. That is a reason to settle the contamination question first, under structured
input (P2-E5), as the owner ordered.

This is a reading of exploratory, correlational data on two seeds. It is not a result.
