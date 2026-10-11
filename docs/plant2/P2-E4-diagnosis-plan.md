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

## Correction (appended 2026-10-11, after the P2-E4 results review; nothing above is edited)

The methodology reviewer of the P2-E4 results (`review/plant2/P2-E4/results-methodology.md`, F3 and
F9) found three places where the exploration write-up above says more than the data allow.

1. **The causal offset sentences are withdrawn.** They were written at 614246b, after the owner had
   narrowed the reading of D3 (21245c1), and they contradict that narrowing:
   - "the online state's high offset suppresses the intrusions" (D3);
   - "coupled through the threshold offset" (last section);
   - "fixing the operating point alone would be expected to expose the contamination" (last section).

   They should read as follows. The online state shows fewer intrusions than the settled state. The
   online state differs by a higher threshold offset **among other differences** (schedule, input
   stream, rhythm, learning episodes between cues). **Which variable is responsible is not
   isolated.** A regime that restores online index access (the duty arm) also exposes the
   contaminated store, but that arm changes the schedule as well as the offset (owner, 2026-10-11).
   Whether the offset alone would do so is untested. The gated D2 below does not replicate the
   offset correlate.

2. **Exploration D1 was not an independent test.** The header of this plan computed "at least 26 %
   and 19 %" from the same exploration numbers before predicting 15-30 %. "Prediction held" for D1
   on seeds 42-43 is withdrawn as a test. D1 is scored on the gated seeds only (below).

3. **D4 overstated the offset rise, and "rules out" was too strong.**
   - The habituation control copy's assembly offset also rises over the same 100 steps, by 1.1-1.2 mV.
   - Net of the control copy, the repetition-specific rise is **2.0-2.1 mV**: 2.08-2.09 at M = 500
     and 2.01 at M = 1,000 on seeds 42-43, the same on gated seeds 16-20.
   - These are medians over 50 items, computed from `info_rep` and `info_ctl` in the records.
   - "What this rules out, at the item level" should read **"what this does not support, at the
     item level"**. Equal rises in habituated and non-habituated items do not support "habituated
     items accommodate more". They do not exclude it.

## Gated results (seeds 16-20; reported, post hoc but predeclared above)

Run 2026-10-11 with `analysis/p2e4_diagnosis.py`, after the P2-E4 verdict (e756252). The records
are the `diagnosis` records with `gated: true` in `bench/results/plant2.jsonl`.

**Validity.** All five re-simulations are valid:
- 1,000 logged main-line steps were compared per seed, with 0 mismatches;
- twin B reproduced every recorded aggregate at both loads (`D3_verified` true).

### D1 (200 half cues per seed and load)

| seed | M = 500: both / content without index / index without content / neither | M = 1,000: both / content without index / index without content / neither |
|---|---|---|
| 16 | 176 / 21 (10.5 %) / 2 / 1 | 132 / 58 (29.0 %) / 5 (2.5 %) / 5 |
| 17 | 172 / 23 (11.5 %) / 2 / 3 | 140 / 52 (26.0 %) / 2 (1.0 %) / 6 |
| 18 | 185 / 14 (7.0 %) / 1 / 0 | 134 / 59 (29.5 %) / 2 (1.0 %) / 5 |
| 19 | 179 / 17 (8.5 %) / 3 / 1 | 147 / 45 (22.5 %) / 1 (0.5 %) / 7 |
| 20 | 183 / 12 (6.0 %) / 1 / 4 | 130 / 56 (28.0 %) / 6 (3.0 %) / 8 |

- **Content without index at M = 1,000: 22.5-29.5 %. Held** (predicted 15-30 %) on all five seeds.
- **Index without content: under 3 % on four seeds, exactly 3.0 % (6 of 200) on seed 20.** Held on
  four seeds and failed on one, by the boundary.

### D2: "content without index" against "both" (medians over cues)

| measure | M = 1,000, seeds 16-20 | M = 500, seeds 16-20 | prediction | outcome |
|---|---|---|---|---|
| A(x) recall at 50 ms, content without index | 0.70-0.73 (both: 0.92-0.94) | 0.71-0.75 (both: 0.95-0.96) | 0.5-0.8 | held |
| share rescued by a 75 ms window | 0.89-0.93 | 0.71-1.0 | a minority | **failed**: the large majority |
| R(x) recall at 50 ms | 0.59-0.68 | 0.68-0.74 | at least A's | **failed**: below A's |
| A(x) first spike, later than "both" by | 6.0-8.5 ms | 6.5-11 ms | >= 5 ms | held |
| assembly offset, minus "both" | +0.57, +0.27, -0.15, +0.08, +0.40 mV | +0.53, +0.29, +0.07, +0.70, -0.22 mV | higher | **not held consistently**: small and of either sign |
| global offset, minus "both" | +0.25, -0.09, +0.12, +0.07, +0.14 mV | +0.02, +0.06, +0.15, +0.14, -0.17 mV | not predicted | small, of either sign |
| median item age, content without index / both | older on 3 seeds, younger on 1, equal on 1 | older on 4 seeds, younger on 1 | older | **not held consistently** |
| regenerated missing lines with an A(x) candidate | 1.0 on every seed | 1.0 where defined | most | held |
| ... with only R(x)-not-A(x) candidates | 0 | 0 | under a quarter | held |

**Reading.** As in exploration, the online index failures are mostly slowed retrievals. The
assembly's first spikes come 6-8.5 ms later at M = 1,000, and about 90 % of those cues reach the
recall bar within 75 ms. The same late assembly carries the content. The exploration's offset
correlate (+0.2-0.4 mV) **does not replicate**: the gated differences are small and of either sign.
D2 gives no evidence that the threshold offset at slot onset distinguishes slowed cues from the
others. That is consistent with the constructive reviewer's exploratory seed-90 check (onset
offset AUC 0.49-0.60). What does distinguish them is not identified.

### D3: settled twin B, the same stored synapses

| seed | M | index failures online | pass after settle | McNemar index (online pass & settled fail / the reverse) | content failures online | pass after settle | McNemar content |
|---|---|---|---|---|---|---|---|
| 16 | 500 | 22 | 95 % | 4 / 21 | 3 | 100 % | 0 / 3 |
| 17 | 500 | 26 | 100 % | 4 / 26 | 5 | 80 % | 1 / 4 |
| 18 | 500 | 14 | 100 % | 4 / 14 | 1 | 100 % | 1 / 1 |
| 19 | 500 | 18 | 89 % | 5 / 16 | 4 | 75 % | 1 / 3 |
| 20 | 500 | 16 | 94 % | 4 / 15 | 5 | 80 % | 1 / 4 |
| 16 | 1,000 | 63 | 90 % | 5 / 57 | 10 | 80 % | **27 / 8** |
| 17 | 1,000 | 58 | 86 % | 8 / 50 | 8 | 62 % | **21 / 5** |
| 18 | 1,000 | 64 | 91 % | 3 / 58 | 7 | 71 % | **15 / 5** |
| 19 | 1,000 | 52 | 100 % | 7 / 52 | 8 | 75 % | **25 / 6** |
| 20 | 1,000 | 64 | 95 % | 2 / 61 | 14 | 64 % | **28 / 9** |

- **Index: held.** 86-100 % of online index failures pass after the settle (predicted >= 70 %).
  This is state- or protocol-dependent recovery with the synapses unchanged, per the narrowed
  reading. It does not isolate the offset.
- **Content failures mostly recover: held** (62-100 %).
- **Not predicted, and replicated from exploration:** at M = 1,000, more cues pass content online
  and fail it after the settle than the reverse, on all five seeds (15-28 against 5-9). The
  online-written store is contaminated (twin A: 0.82-0.905 against 0.985-1.0 for the plateau-set
  store on the same raster). The online regime shows fewer of those intrusions than the settled
  regime. Which difference between the two regimes is responsible is not isolated.

### D4: habituation (copies; all eligible items)

| seed | M | eligible | habituated | raw offset rise, habituated / not | corr(drop, rise) | recovery among habituated | matched online items (habituated / not) |
|---|---|---|---|---|---|---|---|
| 16 | 500 | 21 | 12 | 3.17 / 3.27 mV | -0.33 | 1.00 | 5 / 3 |
| 17 | 500 | 28 | 14 | 3.26 / 3.25 mV | -0.09 | 1.00 | 6 / 5 |
| 18 | 500 | 33 | 21 | 3.27 / 3.29 mV | 0.21 | 0.90 | 8 / 6 |
| 19 | 500 | 27 | 14 | 3.33 / 3.34 mV | 0.29 | 0.93 | 6 / 5 |
| 20 | 500 | 20 | 10 | 3.33 / 3.30 mV | -0.01 | 0.80 | 5 / 4 |
| 16 | 1,000 | 13 | 10 | 3.18 / 3.02 mV | 0.59 | 0.80 | 3 / 0 |
| 17 | 1,000 | 6 | 5 | 3.06 / 3.25 mV | -0.64 | 0.80 | 1 / 0 |
| 18 | 1,000 | 12 | 8 | 3.22 / 3.13 mV | 0.14 | 0.88 | 0 / 0 |
| 19 | 1,000 | 9 | 5 | 3.07 / 3.27 mV | -0.53 | 0.80 | 2 / 2 |
| 20 | 1,000 | 6 | 4 | 3.27 / 3.37 mV | -0.04 | 0.75 | 1 / 1 |

The raw rise includes 1.1-1.2 mV that the control copy also shows. Net of it, the
repetition-specific rise is 2.01-2.09 mV, with item ranges 1.92-2.19 mV on every seed and load.

- **The offset rises with repetition: held.**
- **Habituated items rise more: failed.** Both groups rise equally on every seed (within 0.2 mV,
  in either direction). Correlations are small at M = 500 (|r| <= 0.33). At M = 1,000 they rest on
  6-13 items and go either way. So this does not support "habituated items accommodate more".
- **Association with online index failure: not estimable.** The median habituation item had 0
  online probes, and the matched groups have 0-8 items.

**A graded reading** (post hoc, from the constructive reviewer, NS6; recomputed here from the
habituation logs, whose sha256 matched the records):
- On every gated seed and load, **all 50 items** recall less in the repeated copy's last 10
  repetitions than in the control copy's.
- The mean drop in A(x) recall is 0.107-0.119 at M = 500 and 0.124-0.134 at M = 1,000 (SD about
  0.03; the smallest per item is 0.018-0.070).
- So every repeatedly driven assembly accommodates. O4's binary label counts the items whose
  margin was thin enough for the drop to cross the bar.
- This is a reading, not a gate. Later contracts should report the continuous drop beside O4.

### Predictions scored on the gated seeds

| prediction | outcome |
|---|---|
| D1: content without index 15-30 % at M = 1,000 | held (22.5-29.5 %) |
| D1: index without content under 3 % | held on 4 seeds; 3.0 % on seed 20 |
| D2: A(x) recall 0.5-0.8 | held |
| D2: a 75 ms window rescues a minority | failed (0.89-0.93 rescued) |
| D2: R(x) recall at least A(x)'s | failed |
| D2: A(x) first spikes later by >= 5 ms | held (6.0-8.5 ms) |
| D2: higher assembly offset | not held consistently (-0.15 to +0.57 mV) |
| D2: older items | not held consistently |
| D2: most regenerated lines driven by spiking A(x) cells | held (all) |
| D3: >= 70 % of index failures pass after the settle | held (86-100 %) |
| D3: content failures mostly recover | held (62-100 %); content worse after the settle on balance at M = 1,000 (not predicted) |
| D4: the offset rises with repetition | held (2.0-2.1 mV net of control) |
| D4: habituated items show the larger rise | failed |
| D4: index failure only weakly associated with habituation | not estimable |

### What the gated diagnosis says (reading, not a result)

- **Access.** The online index failure is mostly slowed retrieval of an intact assembly. It is not
  erasure. Its cue-level cause is not identified. The onset threshold offset does not distinguish
  slowed cues in the gated data.
- **Content.** At M = 1,000 the online-written store is contaminated. The settled regime exposes
  that contamination more than the online regime does. P2-E4's content pass therefore depends on
  the online regime.
- **Habituation.** It is accommodation of every repeatedly driven assembly, about 2 mV beyond the
  control copy, and graded across items. The O4 label reflects where items sit relative to the bar.
- **The two problems.** P2-E4 gives no evidence that one variable couples them. Their separation
  is now P2-E5's question (Part D, under continuous learning), as the owner ordered.
